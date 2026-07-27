from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

from chatbot.app.config import Settings
from chatbot.conversation.state import (
    ConversationManager,
    ConversationPhase,
    ConversationState,
)
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
)
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
    data: Any = None
    error: str | None = None


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
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        self._http_client = await create_client()
        self._session_store = RedisSessionStore(self._settings)
        self._tool_registry = ToolRegistry()

        self._tool_registry.register(
            "searchShops", SearchShopsTool(self._http_client)
        )
        self._tool_registry.register(
            "searchCourses", SearchCoursesTool(self._http_client)
        )
        self._tool_registry.register(
            "searchAvailableSlots", SearchAvailableSlotsTool(self._http_client)
        )
        self._tool_registry.register(
            "getTherapists", GetTherapistsTool(self._http_client)
        )
        self._tool_registry.register(
            "lookupBooking", LookupBookingTool(self._http_client)
        )

        self._tool_registry.register("checkEligibility", CheckEligibilityTool(self._http_client))

        if self._knowledge_service is None:
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

        self._tool_registry.register("faqSearch", FAQSearchTool(self._knowledge_service))
        self._tool_registry.register("createBooking", CreateBookingTool(self._http_client))
        self._tool_registry.register("modifyBooking", ModifyBookingTool(self._http_client))
        self._tool_registry.register("cancelBooking", CancelBookingTool(self._http_client))

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
            # Rate limit before any costly operations
            assert self._rate_limiter is not None
            self._rate_limiter.check(request.session_id, request.user_id)

            # Get or create session
            session_store = self._session_store
            assert session_store is not None
            session = await session_store.get_session(request.session_id)
            if session is None:
                session = await session_store.create_session(request.session_id, request.user_id)
                metrics.incr("sessions_created_total")

            # Get conversation state
            state_dict = session.conversation_state
            if not state_dict:
                state = ConversationState()
            else:
                state = ConversationState(**state_dict)

            # Handle ambiguous input and "start over"
            if self._is_start_over(request.message) or self._is_go_back(request.message):
                if state.pending_action is not None:
                    # ponytail: pending action present, cannot safely reset.
                    # Force user to confirm or cancel the pending action first.
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
                metrics.incr("conversation_resets_total")
                response = IntentResponse(True, "Let's start over. How can I help?", state)
            else:
                # Main conversation logic
                intent = self._parse_intent(request.message, state)
                response = await self._handle_intent(
                    intent, request.message, state, session.session_id
                )

            # Save updated state
            session.conversation_state = response.state.model_dump()
            await session_store.save_session(session)

            # Final response
            return ChatResponse(
                success=response.success,
                message=response.message,
                session_id=session.session_id,
                phase=response.state.phase,
                data=response.data,
                error=response.error,
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
            # Fallback if recovery handler fails or isn't available
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
        return message.lower().strip() in ("start over", "restart")

    def _is_go_back(self, message: str) -> bool:
        """Check for 'go back' keywords."""
        return message.lower().strip() in ("go back", "back")

    def _parse_intent(self, message: str, state: ConversationState) -> str:
        """Parse user intent from message (deterministic keyword matching for Phase 1)."""
        message_lower = message.lower()

        if state.pending_action:
            if "confirm" in message_lower or "yes" in message_lower:
                return "confirm_action"
            if "cancel" in message_lower or "no" in message_lower:
                return "cancel_action"
        if any(
            keyword in message_lower for keyword in ["shop", "branch", "location"]

        ) and state.phase == ConversationPhase.GREETING:
            return "search_shops"
        if (
            "course" in message_lower
            or "service" in message_lower
            or "massage" in message_lower
        ) and state.phase in (
            ConversationPhase.GREETING,
            ConversationPhase.SEARCHING_SHOPS,
        ):
            return "search_courses"
        if (
            "slot" in message_lower
            or "time" in message_lower
            or "available" in message_lower
        ) and state.phase in (
            ConversationPhase.SEARCHING_COURSES,
            ConversationPhase.SEARCHING_SLOTS,
        ):
            return "search_slots"

        if "therapist" in message_lower and state.phase in (
            ConversationPhase.SEARCHING_SLOTS,
            ConversationPhase.SELECTING_THERAPIST,
        ):
            return "get_therapists"
        if (
            "eligibility" in message_lower
            or "blocked" in message_lower
            or "phone" in message_lower
        ) and state.phase == ConversationPhase.SELECTING_THERAPIST:
            return "check_eligibility"

        if (
            "booking" in message_lower
            and ("lookup" in message_lower or "check" in message_lower)
            and state.phase == ConversationPhase.GREETING
        ):
            return "lookup_booking"
        if "faq" in message_lower or "question" in message_lower or "help" in message_lower:
            return "faq_search"

        if "reset" in message_lower or "start over" in message_lower:
            return "reset"

        return "unknown"

    async def _handle_intent(
        self,
        intent: str,
        message: str,
        state: ConversationState,
        session_id: str,
    ) -> IntentResponse:
        """Handle parsed intent."""
        assert self._tool_registry is not None

        if intent == "confirm_action":
            from chatbot.conversation.tool_orchestrator import ToolOrchestrator
            orchestrator = ToolOrchestrator(self._tool_registry)
            try:
                result = await orchestrator.execute_pending_action(state)
                state, _ = self._conversation_manager.transition(state, "execute_write")
                return IntentResponse(True, "Action completed successfully.", state, result)
            except Exception as e:
                self._conversation_manager.clear_pending_action(state)
                return IntentResponse(False, f"Error: {str(e)}", state)

        if intent == "cancel_action":
            self._conversation_manager.clear_pending_action(state)
            state = self._conversation_manager.reset(state)
            return IntentResponse(True, "Action cancelled.", state)

        if intent == "reset":
            state = self._conversation_manager.reset(state)
            get_metrics().incr("conversation_resets_total")
            return IntentResponse(True, "Conversation reset. How can I help you?", state)

        if intent == "search_shops":
            state, ok = self._conversation_manager.transition(state, "search_shops")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchShops")
            shops_request = SearchShopsRequest()
            result = await tool.execute(shops_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                shops = result.data
                msg = f"Found {len(shops)} shops:\n" + "\n".join(
                    f"- {s.shopName} ({s.address})" for s in shops
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "search_courses":
            # Need shop_id from context
            shop_id = state.booking_context.shop_id
            if not shop_id:
                return IntentResponse(False, "Please select a shop first", state)

            state, ok = self._conversation_manager.transition(state, "select_shop")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchCourses")
            courses_request = SearchCoursesRequest(shopId=shop_id)
            result = await tool.execute(courses_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                courses = result.data
                msg = f"Found {len(courses)} courses:\n" + "\n".join(
                    f"- {c.courseName} ({c.duration}min, {c.price:,}đ)" for c in courses
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "search_slots":
            context = state.booking_context
            required = ["shop_id", "course_id", "date", "duration", "number_of_people"]
            missing = [k for k in required if getattr(context, k) is None]
            if missing:
                return IntentResponse(False, f"Missing: {', '.join(missing)}", state)

            state, ok = self._conversation_manager.transition(state, "select_course")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("searchAvailableSlots")
            from datetime import date as date_type
            from datetime import time as time_type
            slots_request = SearchAvailableSlotsRequest(
                shopId=context.shop_id or 0,
                date=date_type.fromisoformat(context.date)
                if context.date
                else date_type.today(),
                duration=context.duration or 60,
                numberOfPeople=context.number_of_people or 1,
                courseIds=str(context.course_id),
            )

            result = await tool.execute(slots_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                slots = result.data
                msg = f"Found {len(slots)} available slots:\n" + "\n".join(
                    f"- {s.startTime}-{s.endTime} (capacity: {s.availableCapacity})" for s in slots
                )
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "get_therapists":
            context = state.booking_context
            required = ["shop_id", "date", "start_time"]
            missing = [k for k in required if getattr(context, k) is None]
            if missing:
                return IntentResponse(False, f"Missing: {', '.join(missing)}", state)

            state, ok = self._conversation_manager.transition(state, "select_slot")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("getTherapists")
            from datetime import date as date_type
            from datetime import time as time_type
            therapists_request = GetTherapistsRequest(
                shopId=context.shop_id or 0,
                date=date_type.fromisoformat(context.date)
                if context.date
                else date_type.today(),
                startTime=time_type.fromisoformat(context.start_time)
                if context.start_time
                else time_type(9, 0),
                duration=context.duration or 60,
            )

            result = await tool.execute(therapists_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                therapists = result.data
                msg = "Available therapists:\n" + "\n".join(
                    f"- {t.name} ({t.gender}) - "
                    f"{'Available' if t.isAvailable else 'Busy'}"
                    for t in therapists
                )

            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "check_eligibility":
            phone = state.booking_context.phone_number
            if not phone:
                return IntentResponse(False, "Please provide your phone number", state)

            state, ok = self._conversation_manager.transition(state, "select_therapist")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("checkEligibility")
            eligibility_request = CheckEligibilityRequest(phoneNumber=phone)
            result = await tool.execute(eligibility_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                data = result.data
                if data.isEligible:
                    msg = (
                    f"Eligible! Member rank: {data.memberRank or 'N/A'}, "
                    f"Visits: {data.visitCount}"
                )

                else:
                    msg = f"Not eligible: {data.blockReason or 'Blocked'}"
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "lookup_booking":
            # Extract booking code from message
            import re
            booking_code_match = re.search(r"BK\d{12}", message.upper())
            if not booking_code_match:
                return IntentResponse(
                    False,
                    "Please provide a booking code (format: BKYYYYMMDDXXXX)",
                    state,
                )


            booking_code = booking_code_match.group(0)
            state, ok = self._conversation_manager.transition(state, "lookup_booking")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("lookupBooking")
            lookup_request = LookupBookingRequest(bookingCode=booking_code)
            result = await tool.execute(lookup_request)
            state.last_tool_result = result.model_dump(mode="json")
            if result.success:
                bookings = result.data
                if bookings:
                    b = bookings[0]
                    msg = (
                        f"Booking {b.bookingCode}: {b.shopName} on {b.bookingDate} at "
                        f"{b.startTime} - {b.status}"
                    )

                else:
                    msg = "No booking found with that code"
            else:
                msg = f"Error: {result.message}"
            return IntentResponse(True, msg, state, state.last_tool_result)

        if intent == "faq_search":
            state, ok = self._conversation_manager.transition(state, "faq_search")
            if not ok:
                return IntentResponse(False, state.error_message or "Invalid state", state)

            tool = self._tool_registry.get("faqSearch")
            faq_request = FAQSearchRequest(query=message)
            result = await tool.execute(faq_request)
            state.last_tool_result = result.model_dump(mode="json")
            msg = result.message
            return IntentResponse(True, msg, state, state.last_tool_result)

        return IntentResponse(
            False,
            "I didn't understand that. Try: search shops, search courses, search slots, "
            "get therapists, check eligibility, lookup booking, or faq search.",
            state,
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    configure_logging()
    app = FastAPI(title="Chatbot Service", version="1.0.0")
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
