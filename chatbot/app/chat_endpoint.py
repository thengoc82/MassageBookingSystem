from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot.app.config import Settings
from chatbot.app.llm import LLMService, OpenAILLMService
from chatbot.conversation.intent_extractor import IntentExtractor
from chatbot.conversation.planner import Planner
from chatbot.conversation.response_generator import ResponseGenerator
from chatbot.conversation.state import (
    BookingContext,
    ConversationManager,
    ConversationPhase,
    ConversationState,
)
from chatbot.conversation.tool_orchestrator import ToolOrchestrator
from chatbot.gateway.client import HTTPClient, create_client
from chatbot.knowledge import (
    KnowledgeService,
    PgVectorStore,
    SentenceTransformerEmbeddingService,
)
from chatbot.models import (
    CheckEligibilityRequest,
    FAQSearchRequest,
    GetTherapistsRequest,
    LookupBookingRequest,
    SearchAvailableSlotsRequest,
    SearchCoursesRequest,
    SearchShopsRequest,
    SearchShopsResponse,
    ShopInfo,
)
from chatbot.models.conversation import Conversation
from chatbot.models.intent import Intent, IntentType
from chatbot.observability.logging import configure_logging, get_logger
from chatbot.observability.metrics import get_metrics, tracing_middleware
from chatbot.observability.rate_limit import RateLimitExceeded, TokenBucketRateLimiter
from chatbot.recovery.handler import RecoveryHandler
from chatbot.session.store import RedisSessionStore, SessionData
from chatbot.tools.registry import ToolRegistry
from chatbot.tools.search_tools import (
    CheckEligibilityTool,
    FAQSearchTool,
    GetTherapistsTool,
    LookupBookingTool,
    SearchAvailableSlotsTool,
    SearchCoursesTool,
    SearchShopsTool,
)
from chatbot.tools.write_tools import (
    CancelBookingTool,
    CreateBookingTool,
    ModifyBookingTool,
)


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    session_id: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    success: bool
    message: str
    session_id: str
    phase: ConversationPhase
    data: Any = None
    error: str | None = None


@dataclass
class IntentResponse:
    """Internal response from intent handler."""

    success: bool
    message: str
    state: ConversationState
    conversation: Conversation
    data: Any = None
    error: str | None = None


def _is_greeting(message: str) -> bool:
    """Detect greeting words."""
    msg = message.lower().strip()
    return msg in {
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "morning",
        "afternoon",
        "evening",
    } or msg.startswith(("hello", "hi ", "hey ", "good morning", "good afternoon", "good evening"))


def _is_goodbye(message: str) -> bool:
    """Detect goodbye words."""
    msg = message.lower().strip()
    return msg in {"bye", "goodbye", "see you", "see ya", "cya", "exit", "quit"} or msg.startswith(
        ("bye", "goodbye")
    )


def _is_help(message: str) -> bool:
    """Detect help requests, but not 'help me book' style booking intents."""
    msg = message.lower().strip()
    if msg in {"help", "what can you do", "options", "menu", "?"}:
        return True
    return msg.startswith("help me") and "book" not in msg and "find" not in msg


def _is_booking_intent(message: str) -> bool:
    """Detect booking intent in natural language."""
    msg = message.lower()
    booking_keywords = ["book", "booking", "reserve", "reservation", "appointment", "schedule"]
    massage_keywords = ["massage", "service", "course", "treatment", "session"]
    has_booking = any(k in msg for k in booking_keywords)
    has_massage = any(k in msg for k in massage_keywords)
    if has_booking and has_massage:
        return True
    if has_massage and any(t in msg for t in ["tomorrow", "today", "tonight", "next week", "this weekend"]):
        return True
    return False


def _slots_from_message(message: str) -> dict:
    """Extract simple slots (date, time, people) from message text."""
    import re
    slots: dict = {}
    msg = message.lower()
    if "tomorrow" in msg:
        slots["date"] = "tomorrow"
    if "today" in msg:
        slots["date"] = "today"
    m = re.search(r"(\d+)\s*(?:people|person|ppl|guests?)", msg)
    if m:
        slots["number_of_people"] = int(m.group(1))
    m = re.search(r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", msg)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        slots["start_time"] = f"{hour:02d}:{minute:02d}"
    m = re.search(r"(\d+)\s*(?:min|minute|minutes|hour|hr|hours)", msg)
    if m:
        n = int(m.group(1))
        slots["duration"] = n * 60 if "hour" in m.group(0) or "hr" in m.group(0) else n
    return slots


def _shop_label(shop: Any) -> str:
    """Format a shop for display."""
    return f"{shop.shopName} (id: {shop.shopId}, {shop.address})"


def _welcome_message() -> str:
    return (
        "Welcome! I'm your AI massage booking assistant. I can help you book a massage, "
        "check your booking, or answer questions. What would you like to do today?"
    )


def _help_message() -> str:
    return (
        "Here's what I can do:\n"
        "- Book a massage (just tell me when and how many people)\n"
        "- Look up a booking (share your booking code or phone number)\n"
        "- Cancel or modify a booking\n"
        "- Answer questions about our services\n"
        "What would you like to do?"
    )


def _goodbye_message() -> str:
    return "Goodbye! Have a relaxing day." + ("" if True else "")


def _unknown_message() -> str:
    return (
        "I'm not sure I understand. You can ask me things like:\n"
        "- 'Book a massage for 2 people tomorrow at 3pm'\n"
        "- 'Show me shops'\n"
        "- 'Help'\n"
        "- 'Goodbye'\n"
        "What would you like to do?"
    )


class ChatEndpoint:
    """Web chat endpoint handler."""

    def __init__(
        self,
        settings: Settings | None = None,
        http_client: HTTPClient | None = None,
        session_store: RedisSessionStore | None = None,
        conversation_manager: ConversationManager | None = None,
        tool_registry: ToolRegistry | None = None,
        knowledge_service: KnowledgeService | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
        recovery_handler: RecoveryHandler | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._http_client = http_client
        self._session_store = session_store
        self._conversation_manager = conversation_manager or ConversationManager()
        self._tool_registry = tool_registry
        self._knowledge_service = knowledge_service
        self._rate_limiter = rate_limiter or TokenBucketRateLimiter()
        self._recovery_handler = recovery_handler or RecoveryHandler(self._conversation_manager)
        self._logger = get_logger("chatbot.app.chat_endpoint")
        self._llm_service = llm_service or OpenAILLMService(
            self._settings.openai_api_key or "no-key", self._settings.openai_model
        )
        self._intent_extractor = IntentExtractor(self._llm_service)
        self._planner = Planner(self._llm_service, self._tool_registry or ToolRegistry())
        self._response_generator = ResponseGenerator(self._llm_service)
        self._tool_orchestrator: ToolOrchestrator | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        self._http_client = await create_client()
        self._session_store = RedisSessionStore(self._settings)
        self._tool_registry = ToolRegistry()

        self._tool_registry.register("searchShops", SearchShopsTool(self._http_client))
        self._tool_registry.register("searchCourses", SearchCoursesTool(self._http_client))
        self._tool_registry.register(
            "searchAvailableSlots", SearchAvailableSlotsTool(self._http_client)
        )
        self._tool_registry.register("getTherapists", GetTherapistsTool(self._http_client))
        self._tool_registry.register("lookupBooking", LookupBookingTool(self._http_client))
        self._tool_registry.register("checkEligibility", CheckEligibilityTool(self._http_client))

        if self._knowledge_service is None:
            if not self._settings.pg_dsn:
                self._logger.warning(
                    "CHATBOT_PG_DSN is not set. FAQ search is disabled. "
                    "Set CHATBOT_PG_DSN to enable knowledge base features."
                )
            else:
                embedding_service = SentenceTransformerEmbeddingService(
                    model_name=self._settings.embedding_model,
                    embedding_dim=self._settings.embedding_dim,
                )
                vector_store = PgVectorStore(
                    dsn=self._settings.pg_dsn,
                    embedding_dim=self._settings.embedding_dim,
                    embedding_service=embedding_service,
                )
                self._knowledge_service = KnowledgeService(vector_store, embedding_service)

        if self._knowledge_service is not None:
            self._tool_registry.register("faqSearch", FAQSearchTool(self._knowledge_service))
        self._tool_registry.register("createBooking", CreateBookingTool(self._http_client))
        self._tool_registry.register("modifyBooking", ModifyBookingTool(self._http_client))
        self._tool_registry.register("cancelBooking", CancelBookingTool(self._http_client))

        self._tool_orchestrator = ToolOrchestrator(self._tool_registry)
        self._planner = Planner(self._llm_service, self._tool_registry)
        self._initialized = True

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.close()
        if self._session_store:
            await self._session_store.close()
        if self._knowledge_service:
            self._knowledge_service.vector_store.close()
        self._initialized = False

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """Process a chat message."""
        await self.initialize()

        metrics = get_metrics()
        metrics.incr("chat_requests_total")

        state: ConversationState | None = None
        session: SessionData | None = None
        try:
            assert self._rate_limiter is not None
            self._rate_limiter.check(request.session_id, request.user_id)

            session_store = self._session_store
            assert session_store is not None
            session = await session_store.get_session(request.session_id)
            if session is None:
                session = await session_store.create_session(request.session_id, request.user_id)
                metrics.incr("sessions_created_total")

            state_dict = session.conversation_state or {}
            state = ConversationState(**state_dict)
            history = session.conversation_history or []
            conversation = Conversation(history=list(history))

            conversation.add_message("user", request.message)

            if self._is_start_over(request.message):
                if state.pending_action is not None:
                    metrics.incr("reset_blocked_by_pending_action_total")
                    return ChatResponse(
                        success=False,
                        message=(
                            "You have a pending action that requires confirmation. "
                            "Please confirm or cancel before starting over."
                        ),
                        session_id=request.session_id,
                        phase=state.phase,
                        error="PENDING_ACTION_REQUIRES_CONFIRMATION",
                    )
                state = self._conversation_manager.reset(state)
                conversation = Conversation()
                conversation.add_message("user", request.message)
                conversation.add_message(
                    "assistant",
                    "Sure, let's start over. " + _welcome_message(),
                )
                metrics.incr("conversation_resets_total")
                response_message = "Sure, let's start over. " + _welcome_message()
            elif self._is_go_back(request.message):
                if state.phase == ConversationPhase.GREETING:
                    response_message = _welcome_message()
                else:
                    state = self._conversation_manager.reset(state)
                    response_message = "Going back. " + _welcome_message()
                conversation.add_message("assistant", response_message)
                metrics.incr("go_back_total")
            else:
                intent = self._classify_intent(request.message)
                response = await self._handle_intent(
                    intent, request.message, state, session.session_id, conversation
                )
                state = response.state
                response_message = response.message

            session.conversation_state = state.model_dump()
            session.conversation_history = conversation.history
            await session_store.save_session(session)

            return ChatResponse(
                success=True,
                message=response_message,
                session_id=session.session_id,
                phase=state.phase,
                data=None,
                error=None,
            )
        except RateLimitExceeded as e:
            metrics.incr("rate_limit_exceeded_total")
            self._logger.warning("Rate limit exceeded", extra={"session_id": request.session_id})
            return ChatResponse(
                success=False,
                message=str(e),
                session_id=request.session_id,
                phase=state.phase if state else ConversationPhase.GREETING,
                error="RATE_LIMIT_EXCEEDED",
            )
        except Exception as e:
            metrics.incr("chat_errors_total", labels={"error_type": type(e).__name__})
            if self._recovery_handler and state and session:
                new_state, user_message = self._recovery_handler.handle_failure(e, state, session)
                session.conversation_state = new_state.model_dump()
                assert self._session_store is not None
                await self._session_store.save_session(session)
                return ChatResponse(
                    success=False,
                    message=user_message,
                    session_id=session.session_id,
                    phase=new_state.phase,
                    error="RECOVERY_ACTIVATED",
                )
            self._logger.error("Unhandled exception in chat processing", exc_info=e)
            return ChatResponse(
                success=False,
                message="An unexpected error occurred. Please try again later.",
                session_id=request.session_id,
                phase=ConversationPhase.ERROR,
                error="UNHANDLED_EXCEPTION",
            )

    def _is_start_over(self, message: str) -> bool:
        """Check for 'start over' keywords."""
        return message.lower().strip() in ("start over", "restart", "reset")

    def _is_go_back(self, message: str) -> bool:
        """Check for 'go back' keywords."""
        return message.lower().strip() in ("go back", "back")

    def _classify_intent(self, message: str) -> Intent:
        """Classify user intent with deterministic, conversation-first rules."""
        msg = message.strip()
        lower = msg.lower()

        if state_pending_action_yes_no(self, msg):
            return Intent(intent=IntentType.UNKNOWN, response="Please confirm or cancel the pending action.")

        if _is_greeting(msg):
            return Intent(intent=IntentType.GREETING, response=_welcome_message())
        if _is_goodbye(msg):
            return Intent(intent=IntentType.GOODBYE, response=_goodbye_message())
        if _is_help(msg):
            return Intent(intent=IntentType.HELP, response=_help_message())

        if _is_booking_intent(msg):
            slots = _slots_from_message(msg)
            return Intent(intent=IntentType.BOOK_MASSAGE, slots=slots)

        if any(k in lower for k in ["shop", "branch", "location", "near me"]):
            return Intent(intent=IntentType.SEARCH_SHOPS)
        if any(k in lower for k in ["course", "service", "menu"]):
            return Intent(intent=IntentType.SEARCH_COURSES)
        if any(k in lower for k in ["slot", "time", "available", "when can"]):
            return Intent(intent=IntentType.SEARCH_SLOTS)
        if "therapist" in lower:
            return Intent(intent=IntentType.SEARCH_SLOTS)
        if any(k in lower for k in ["eligibility", "eligible", "blocked"]):
            return Intent(intent=IntentType.CHECK_ELIGIBILITY)
        if "lookup" in lower or "find my booking" in lower or "check my booking" in lower:
            return Intent(intent=IntentType.LOOKUP_BOOKING)
        if "cancel" in lower:
            return Intent(intent=IntentType.CANCEL_BOOKING)
        if "modify" in lower or "change" in lower or "reschedule" in lower:
            return Intent(intent=IntentType.MODIFY_BOOKING)
        if any(k in lower for k in ["faq", "question", "tell me about", "what is", "how does"]):
            return Intent(intent=IntentType.FAQ)

        return Intent(intent=IntentType.UNKNOWN, response=_unknown_message())

    async def _handle_intent(
        self,
        intent: Intent,
        message: str,
        state: ConversationState,
        session_id: str,
        conversation: Conversation,
    ) -> IntentResponse:
        """Handle parsed intent and return a natural conversational response."""
        metrics = get_metrics()
        metrics.incr("intents_handled_total", labels={"intent": intent.intent.value})

        if intent.intent in {IntentType.GREETING, IntentType.GOODBYE, IntentType.HELP}:
            response_message = intent.response or _welcome_message()
            if intent.intent == IntentType.GOODBYE:
                state = self._conversation_manager.reset(state)
            conversation.add_message("assistant", response_message)
            return IntentResponse(True, response_message, state, conversation)

        if intent.intent == IntentType.BOOK_MASSAGE:
            return await self._handle_booking_intent(intent, state, conversation, metrics)

        if intent.intent == IntentType.UNKNOWN:
            response_message = intent.response or _unknown_message()
            conversation.add_message("assistant", response_message)
            return IntentResponse(False, response_message, state, conversation)

        if intent.intent == IntentType.SEARCH_SHOPS:
            return await self._run_search_shops(state, conversation, metrics)
        if intent.intent == IntentType.SEARCH_COURSES:
            return await self._run_search_courses(state, conversation, metrics)
        if intent.intent == IntentType.SEARCH_SLOTS:
            return await self._run_search_slots(state, conversation, metrics)
        if intent.intent == IntentType.CHECK_ELIGIBILITY:
            return await self._run_check_eligibility(state, conversation, metrics)
        if intent.intent == IntentType.LOOKUP_BOOKING:
            return await self._run_lookup_booking(message, state, conversation, metrics)
        if intent.intent == IntentType.FAQ:
            return await self._run_faq(message, state, conversation, metrics)

        response_message = _unknown_message()
        conversation.add_message("assistant", response_message)
        return IntentResponse(False, response_message, state, conversation)

    async def _handle_booking_intent(
        self,
        intent: Intent,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
    ) -> IntentResponse:
        """Handle BOOK_MASSAGE intent with auto slot-filling."""
        # Update context with extracted slots
        slots = intent.slots or {}
        ctx = state.booking_context
        if slots.get("date"):
            ctx.date = slots["date"]
        if slots.get("start_time"):
            ctx.start_time = slots["start_time"]
        if slots.get("duration"):
            ctx.duration = int(slots["duration"])
        if slots.get("number_of_people"):
            ctx.number_of_people = int(slots["number_of_people"])

        # No shop yet — auto search shops
        if ctx.shop_id is None:
            metrics.incr("slot_filling_auto_search_shops_total")
            return await self._run_search_shops(
                state, conversation, metrics, intro="Great, let's find you a shop first. "
            )

        # Have shop but no course — search courses
        if ctx.course_id is None:
            metrics.incr("slot_filling_auto_search_courses_total")
            return await self._run_search_courses(
                state, conversation, metrics, intro="Which service would you like? "
            )

        # Have course+date but no slot — search slots
        if not (ctx.start_time and ctx.duration and ctx.number_of_people):
            metrics.incr("slot_filling_auto_search_slots_total")
            return await self._run_search_slots(
                state,
                conversation,
                metrics,
                intro="Let's find a time. ",
                missing_hint=self._missing_slot_hint(ctx),
            )

        # Have everything — summarise and ask for confirmation
        summary = (
            f"To confirm: shop {ctx.shop_name or ctx.shop_id}, "
            f"{ctx.course_name or ctx.course_id} on {ctx.date} at {ctx.start_time} "
            f"for {ctx.number_of_people} people. Shall I book it?"
        )
        conversation.add_message("assistant", summary)
        return IntentResponse(True, summary, state, conversation)

    def _missing_slot_hint(self, ctx: BookingContext) -> str:
        missing = []
        if not ctx.date:
            missing.append("date")
        if not ctx.start_time:
            missing.append("time")
        if not ctx.duration:
            missing.append("duration")
        if not ctx.number_of_people:
            missing.append("number of people")
        return "I still need: " + ", ".join(missing) + ". "

    async def _run_search_shops(
        self,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
        intro: str = "",
    ) -> IntentResponse:
        assert self._tool_registry is not None
        state, ok = self._conversation_manager.transition(state, "search_shops")
        if not ok and state.phase != ConversationPhase.SEARCHING_SHOPS:
            return IntentResponse(False, state.error_message or "Invalid state", state, conversation)

        tool = self._tool_registry.get("searchShops")
        result = await tool.execute(SearchShopsRequest())
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "searchShops"})
        if not result.success:
            msg = f"Sorry, I couldn't fetch the shops right now. {result.message}"
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)
        shops: list[ShopInfo] = result.data or []
        if not shops:
            msg = (intro + "I couldn't find any shops available right now.").strip()
            conversation.add_message("assistant", msg)
            return IntentResponse(True, msg, state, conversation)
        body = "\n".join(f"- {_shop_label(s)}" for s in shops)
        msg = f"{intro}Here are our shops:\n{body}\nWhich one would you like?"
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation, data={"shops": [s.model_dump() for s in shops]})

    async def _run_search_courses(
        self,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
        intro: str = "",
    ) -> IntentResponse:
        assert self._tool_registry is not None
        if state.booking_context.shop_id is None:
            return await self._run_search_shops(
                state, conversation, metrics, intro="I need a shop first. "
            )
        state, ok = self._conversation_manager.transition(state, "select_shop")
        if not ok and state.phase != ConversationPhase.SEARCHING_COURSES:
            return IntentResponse(False, state.error_message or "Invalid state", state, conversation)

        tool = self._tool_registry.get("searchCourses")
        result = await tool.execute(SearchCoursesRequest(shopId=state.booking_context.shop_id))
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "searchCourses"})
        if not result.success:
            msg = f"Sorry, I couldn't fetch the courses. {result.message}"
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)
        courses = result.data or []
        if not courses:
            msg = f"{intro}No services are available at that shop right now."
            conversation.add_message("assistant", msg)
            return IntentResponse(True, msg, state, conversation)
        body = "\n".join(
            f"- {c.courseName} (id: {c.courseId}, {c.duration}min, {c.price:,}đ)" for c in courses
        )
        msg = f"{intro}Here are the services:\n{body}\nWhich one would you like?"
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation, data={"courses": [c.model_dump() for c in courses]})

    async def _run_search_slots(
        self,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
        intro: str = "",
        missing_hint: str = "",
    ) -> IntentResponse:
        assert self._tool_registry is not None
        ctx = state.booking_context
        if ctx.shop_id is None:
            return await self._run_search_shops(
                state, conversation, metrics, intro="I need a shop first. "
            )
        if ctx.course_id is None:
            return await self._run_search_courses(
                state, conversation, metrics, intro="I need a service first. "
            )

        missing = []
        if not ctx.date:
            missing.append("date")
        if not ctx.start_time:
            missing.append("time")
        if not ctx.duration:
            missing.append("duration")
        if not ctx.number_of_people:
            missing.append("number of people")
        if missing:
            msg = (
                f"{intro}{missing_hint}To find a slot, I need: " + ", ".join(missing) + "."
            )
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)

        state, ok = self._conversation_manager.transition(state, "select_course")
        if not ok and state.phase != ConversationPhase.SEARCHING_SLOTS:
            return IntentResponse(False, state.error_message or "Invalid state", state, conversation)

        from datetime import date as date_type
        from datetime import time as time_type

        tool = self._tool_registry.get("searchAvailableSlots")
        slots_request = SearchAvailableSlotsRequest(
            shopId=ctx.shop_id,
            date=date_type.fromisoformat(ctx.date) if ctx.date else date_type.today(),
            duration=ctx.duration or 60,
            numberOfPeople=ctx.number_of_people or 1,
            startTime=time_type.fromisoformat(ctx.start_time) if ctx.start_time else None,
            courseIds=str(ctx.course_id),
        )
        result = await tool.execute(slots_request)
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "searchAvailableSlots"})
        if not result.success:
            msg = f"Sorry, I couldn't find slots. {result.message}"
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)
        slots = result.data or []
        if not slots:
            msg = f"{intro}No slots available for those criteria. Try a different time?"
            conversation.add_message("assistant", msg)
            return IntentResponse(True, msg, state, conversation)
        body = "\n".join(
            f"- {s.startTime}-{s.endTime} (capacity: {s.availableCapacity})" for s in slots
        )
        msg = f"{intro}Here are the available slots:\n{body}\nWhich time works for you?"
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation, data={"slots": [s.model_dump() for s in slots]})

    async def _run_check_eligibility(
        self,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        phone = state.booking_context.phone_number
        if not phone:
            msg = "I just need your phone number to check eligibility."
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)

        state, ok = self._conversation_manager.transition(state, "select_therapist")
        if not ok and state.phase != ConversationPhase.CHECKING_ELIGIBILITY:
            return IntentResponse(False, state.error_message or "Invalid state", state, conversation)

        tool = self._tool_registry.get("checkEligibility")
        result = await tool.execute(CheckEligibilityRequest(phoneNumber=phone))
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "checkEligibility"})
        if not result.success:
            msg = f"Sorry, I couldn't check eligibility. {result.message}"
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)
        data = result.data
        if data.isEligible:
            msg = (
                f"You're eligible! Member rank: {data.memberRank or 'N/A'}, "
                f"visits: {data.visitCount}."
            )
        else:
            msg = f"Sorry, you're not eligible: {data.blockReason or 'blocked'}."
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation)

    async def _run_lookup_booking(
        self,
        message: str,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        import re
        m = re.search(r"BK\d{12}", message.upper())
        booking_code = m.group(0) if m else None
        if not booking_code and state.booking_context.booking_code:
            booking_code = state.booking_context.booking_code
        if not booking_code:
            msg = "Please share your booking code (it looks like BK20250101XXXX) or your phone number."
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)

        state, ok = self._conversation_manager.transition(state, "lookup_booking")
        if not ok and state.phase != ConversationPhase.LOOKING_UP_BOOKING:
            return IntentResponse(False, state.error_message or "Invalid state", state, conversation)

        tool = self._tool_registry.get("lookupBooking")
        result = await tool.execute(LookupBookingRequest(bookingCode=booking_code))
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "lookupBooking"})
        if not result.success:
            msg = f"Sorry, I couldn't look that up. {result.message}"
            conversation.add_message("assistant", msg)
            return IntentResponse(False, msg, state, conversation)
        bookings = result.data or []
        if not bookings:
            msg = "I couldn't find a booking with that code."
            conversation.add_message("assistant", msg)
            return IntentResponse(True, msg, state, conversation)
        b = bookings[0]
        msg = (
            f"Found it! Booking {b.bookingCode} at {b.shopName} on {b.bookingDate} "
            f"at {b.startTime} — status: {b.status}."
        )
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation)

    async def _run_faq(
        self,
        message: str,
        state: ConversationState,
        conversation: Conversation,
        metrics: Any,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        if not self._tool_registry.has("faqSearch"):
            msg = "I don't have a knowledge base configured, so I can't answer that yet."
            conversation.add_message("assistant", msg)
            return IntentResponse(True, msg, state, conversation)
        tool = self._tool_registry.get("faqSearch")
        result = await tool.execute(FAQSearchRequest(query=message))
        state.last_tool_result = result.model_dump(mode="json")
        metrics.incr("tools_executed_total", labels={"tool": "faqSearch"})
        msg = result.message or "I couldn't find a clear answer."
        conversation.add_message("assistant", msg)
        return IntentResponse(True, msg, state, conversation)


def state_pending_action_yes_no(endpoint: Any, message: str) -> bool:
    """Helper kept for clarity in _classify_intent; not used as a hot path."""
    return False


def create_app() -> FastAPI:
    """Create FastAPI application."""
    configure_logging()
    app = FastAPI(title="Chatbot Service", version="1.0.0")

    # Ponytail: explicit origin list so browser accepts the response with credentials.
    # Wildcard origins + credentials are rejected by browsers; add prod origins here.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    chat_endpoint = ChatEndpoint()

    @app.on_event("startup")
    async def startup() -> None:
        await chat_endpoint.initialize()

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await chat_endpoint.close()

    @app.middleware("http")
    async def trace_middleware(request: Request, call_next: Any) -> Any:
        return await tracing_middleware(request, call_next)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        return await chat_endpoint.process_message(request)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> dict:
        return get_metrics().render()

    return app
