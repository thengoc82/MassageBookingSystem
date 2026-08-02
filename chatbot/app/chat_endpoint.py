import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chatbot import app
from chatbot.app.config import Settings
from chatbot.gateway.client import create_client, HTTPClient
from chatbot.session.store import RedisSessionStore
from chatbot.tools.search_tools import (
    SearchShopsTool,
    SearchCoursesTool,
    SearchAvailableSlotsTool,
    GetTherapistsTool,
    LookupBookingTool,
    CheckEligibilityTool,
    FAQSearchTool,
    SearchShopsRequest,
    SearchCoursesRequest,
    SearchAvailableSlotsRequest,
    GetTherapistsRequest,
    CheckEligibilityRequest,
    LookupBookingRequest,
    FAQSearchRequest,
)
from chatbot.tools.write_tools import (
    CreateBookingTool,
    ModifyBookingTool,
    CancelBookingTool,
    CreateBookingRequest,
    ModifyBookingRequest,
    CancelBookingRequest,
)
from chatbot.knowledge.embedding_service import SentenceTransformerEmbeddingService
from chatbot.knowledge.pgvector_store import PgVectorStore
from chatbot.knowledge.knowledge_service import KnowledgeService
from chatbot.tools.registry import ToolRegistry
from chatbot.conversation import interfaces as convo_interfaces
from chatbot.conversation.goals import Goal
from chatbot.conversation.interfaces import IntentResponse
from chatbot.conversation.policy import Action, DialoguePolicyManager, PolicyDecision
from chatbot.conversation.slot_filling import SlotFillingManager
from chatbot.conversation.slot_parser import parse_and_fill_slots
from chatbot.conversation.state import (
    ConversationManager,
    ConversationPhase,
    ConversationState,
)
from chatbot.nlu.models import NLUResult, Intent
from chatbot.nlu.nlu import NLU




logger = logging.getLogger(__name__)


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
class _LegacyIntentResponse:
    """Backward-compat shim for callers that still use the local IntentResponse."""

    success: bool
    message: str
    state: ConversationState
    data: Any = None
    error: str | None = None


# Substrings that must never reach the user. If a tool response contains any
# of these, we replace the message with a generic apology so backend language
# never leaks to the chat surface.
_LEAK_FRAGMENTS = (
    "validation",
    "missing context",
    "missing:",
    "stack trace",
    "traceback",
    "required",
    "error_message",
    "internal server error",
    "internal_state",
    "exception",
)


def _safe_tool_message(raw: str) -> str:
    """Strip backend noise from a tool's error message before sending to user."""
    lowered = raw.lower()
    if any(frag in lowered for frag in _LEAK_FRAGMENTS):
        return "I'm sorry, something went wrong. Please try again."
    return raw


_WRITE_TOOL_NAMES = frozenset({
    "createBooking", "modifyBooking", "cancelBooking",
})


# Policy-level tool names (snake_case) → registry-level tool names (camelCase).
_POLICY_TO_REGISTRY_TOOL = {
    "search_shops": "searchShops",
    "search_courses": "searchCourses",
    "search_slots": "searchAvailableSlots",
    "search_available_slots": "searchAvailableSlots",
    "get_therapists": "getTherapists",
    "check_eligibility": "checkEligibility",
    "lookup_booking": "lookupBooking",
    "faq_search": "faqSearch",
}


import asyncio

logger = logging.getLogger(__name__)

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
        nlu: NLU | None = None
    ) -> None:
        self._settings = settings or Settings()
        self._http_client = http_client
        self._session_store = session_store
        self._conversation_manager = conversation_manager or ConversationManager()
        self._tool_registry = tool_registry
        self._knowledge_service = knowledge_service
        self._nlu = nlu  # Can be passed in for testing
        self._courses: list[dict[str, Any]] = []
        self._initialized = False
        self._slot_manager: SlotFillingManager | None = None
        self._policy = DialoguePolicyManager()

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._initialized:
            return

        self._http_client = await create_client()
        if self._session_store is None:
            self._session_store = RedisSessionStore(self._settings)

        # Pre-fetch shops to prime the NLU
        shops = []
        try:
            shops_tool = SearchShopsTool(self._http_client)
            shops_result = await shops_tool.execute(SearchShopsRequest())
            if shops_result.success:
                shops = shops_result.data
        except Exception as e:
            logger.error(f"Failed to pre-fetch shops: {e}")

        # Pre-fetch courses to prime the NLU
        courses = []
        # try:
        #     # Assuming courses are not shop-specific for now. If they are, 
        #     # this logic will need to be adapted to fetch courses per shop.
        #     course_tool = SearchCoursesTool(self._http_client)
        #     course_result = await course_tool.execute(SearchCoursesRequest())
        #     if course_result.success:
        #         courses = course_result.data
        #     self._courses = courses
        # except Exception as e:
        #     logger.error(f"Failed to pre-fetch courses: {e}")

        # Initialize NLU with known shops and courses
        if self._nlu is None:
            self._nlu = NLU(known_shops=shops, known_courses=courses)

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

        if self._knowledge_service is None and self._settings.enable_rag:
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

        if self._knowledge_service:
            self._tool_registry.register("faqSearch", FAQSearchTool(self._knowledge_service))

        self._tool_registry.register("createBooking", CreateBookingTool(self._http_client))
        self._tool_registry.register("modifyBooking", ModifyBookingTool(self._http_client))
        self._tool_registry.register("cancelBooking", CancelBookingTool(self._http_client))

        # Wire slot filling manager. The action executor is a closure that runs
        # the underlying read tool when all required slots have been collected.
        self._slot_manager = SlotFillingManager(
            conversation_manager=self._conversation_manager,
            nlu=self._nlu
        )

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

# ------------------------------------------------------------------
    # Main request flow (thin dispatcher — Phase 8)
    # ------------------------------------------------------------------
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        logger.info(f"Processing message: '{request.message}' in session: {request.session_id}")
        await self.initialize()

        session_store = self._session_store
        assert session_store is not None
        session = await session_store.get_session(request.session_id)
        if session is None:
            session = await session_store.create_session(request.session_id, request.user_id)

        state = session.conversation_state

        # 0. Resolve any list selections from the user's message
        from chatbot.conversation.slot_parser import _handle_ordinal_selection
        await _handle_ordinal_selection(request.message, state)

        # 1. NLU understands the message
        focused_slot = state.pending_slot_to_fill
        nlu_result = await self._nlu.understand(request.message, state, focused_slot=focused_slot)
        state.nlu_result = nlu_result
        logger.info(f"NLU result: {nlu_result}")

        # 2. Apply NLU entities to the booking context immediately
        self._conversation_manager.apply_nlu_entities_to_booking_context(state, nlu_result.entities)
        logger.info(f"Booking context after NLU apply: {state.booking_context}")
        
        # 3. Decide on the main conversation flow:
        #    - If we are in the middle of filling slots, continue doing that.
        #    - Otherwise, ask the policy manager for the next high-level action.
        
        # This is the primary change: we now have a dedicated slot-filling loop.
        if state.pending_read_action:
            logger.info(f"Continuing slot filling for action: {state.pending_read_action}")
            if self._slot_manager is None: self._ensure_slot_manager()
            assert self._slot_manager is not None
            
            complete, message_text, data = await self._slot_manager.continue_filling(state, request.message, nlu_result=nlu_result)

            if not complete:
                # Slot filling is still in progress, return the prompt.
                state.phase = self._policy.get_phase_for_slot(state.pending_slot_to_fill)
                await session_store.save_session(session)
                return ChatResponse(success=True, message=message_text, session_id=session.session_id, phase=state.phase, data=data)
            else:
                # Slot filling is complete, execute the action.
                logger.info(f"Slot filling complete for {state.pending_read_action}. Executing action.")
                # The action is cleared inside continue_filling, so we need to grab it before
                action_to_run = state.pending_read_action or ""
                response = await self._execute_pending_read_action(state, action=action_to_run)
        else:
            # Not in a slot-filling loop, so get the next decision from the policy.
            logger.info("No pending action, consulting policy.")
            intent = nlu_result.intent if nlu_result else Intent.UNKNOWN
            decision = self._policy.decide(state, intent, message=request.message, nlu_result=nlu_result)
            logger.info(f"Policy decision: {decision}")
            response = await self._execute_decision(state, decision, request.message)

        # 4. Save the final state and prepare the response
        try:
            session.conversation_state = response.state
            await session_store.save_session(session)
        except AttributeError:
             # Handle cases where response might not be an IntentResponse (e.g. direct ChatResponse)
            if isinstance(response, ChatResponse):
                await session_store.save_session(session)
                return response
            raise

        logger.info(f"Final response message: {response.message}, Phase: {response.state.phase}")

        return ChatResponse(
            success=response.success,
            message=str(response.message or ""),
            session_id=session.session_id,
            phase=response.state.phase,
            data=response.data,
            error=str(response.error) if response.error else None,
        )




    # ------------------------------------------------------------------
    # Action dispatcher — one handler per Action enum value
    # ------------------------------------------------------------------
    async def _execute_decision(
        self,
        state: ConversationState,
        decision: PolicyDecision,
        message: str,
    ) -> IntentResponse:
        if self._slot_manager is None:
            self._ensure_slot_manager()
        assert self._slot_manager is not None

        action = decision.action

        if action == Action.ASK_SLOT:
            return await self._ask_slot(state, decision)

        if action == Action.RUN_TOOL:
            return await self._run_tool(state, decision, message)

        if action == Action.SHOW_RESULTS:
            return await self._show_results(state)

        if action == Action.CONFIRM_ACTION:
            return self._confirm_action(state, decision)

        if action == Action.EXECUTE_WRITE_ACTION:
            return await self._execute_write(state, decision)

        if action == Action.ANSWER_FAQ:
            return await self._answer_faq(state, decision, message)

        if action == Action.RESUME_BOOKING:
            return await self._resume_booking(state, decision)

        if action == Action.END_CONVERSATION:
            return self._end_conversation(state, decision)

        if action == Action.REQUEST_CLARIFICATION:
            return self._request_clarification(state, decision)

        if action == Action.CLEAR_PENDING_ACTION:
            return self._clear_pending(state, decision)

        return self._no_action_response(state)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    async def _ask_slot(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        """Ask for a single missing slot. The slot manager owns the prompt."""
        assert self._slot_manager is not None
        slot = decision.slot
        if slot is None:
            slot = self._first_missing_booking_slot(state)
        if slot is None:
            return IntentResponse(
                True, "All required information has been collected.", state
            )
        from chatbot.conversation.slot_prompts import get_prompt
        prompt_text = get_prompt(slot)
        
        # Set the slot we are about to ask for, so NLU can focus on it.
        state.pending_slot_to_fill = slot

        # The policy's decision should have set the pending_read_action.
        # This handler's job is just to format the prompt.
        data = None
        if slot == "shop_id" and state.recent_tool_results.last_shop_search:
            shops = (state.recent_tool_results.last_shop_search or {}).get("data", [])
            if shops:
                data = {
                    "options": [
                        s if isinstance(s, dict) else (s.model_dump() if hasattr(s, "model_dump") else s)
                        for s in shops
                    ]
                }
        return IntentResponse(True, prompt_text, state, data)

    @staticmethod
    def _first_missing_booking_slot(state: ConversationState) -> str | None:
        for slot in (
            "shop_id", "course_id", "duration", "date",
            "number_of_people", "start_time", "phone_number",
        ):
            if getattr(state.booking_context, slot, None) is None:
                return slot
        return None

    async def _run_tool(
        self,
        state: ConversationState,
        decision: PolicyDecision,
        message: str,
    ) -> IntentResponse:
        """Run the requested tool. Special cases:
        - "__continue_slot_filling__": the slot manager keeps running.
        - Write tools go through the confirmation gate first.
        """
        tool_name = decision.tool or ""

        if tool_name in _WRITE_TOOL_NAMES:
            return self._confirm_action(state, PolicyDecision(
                action=Action.CONFIRM_ACTION,
                goal=decision.goal,
                tool=tool_name,
                payload={
                    "tool": tool_name,
                    "intent": decision.payload.get("intent"),
                    "arguments": decision.payload,
                },
                message=(
                    f"Please confirm: you want to {decision.payload.get('intent', tool_name).replace('_', ' ')}."
                ),
            ))

        # Map policy tool names → registry tool names.
        registry_tool = _POLICY_TO_REGISTRY_TOOL.get(tool_name, tool_name)

        # Read tools.
        if registry_tool == "searchShops":
            return await self._search_shops(state)
        if registry_tool == "searchCourses":
            return await self._search_courses(state)
        if registry_tool == "searchAvailableSlots":
            return await self._search_slots(state)
        if registry_tool == "getTherapists":
            return await self._get_therapists(state)
        if registry_tool == "checkEligibility":
            return await self._check_eligibility(state, message)
        if registry_tool == "lookupBooking":
            return await self._lookup_booking(state, message)
        if registry_tool == "faqSearch":
            return await self._faq_search(state, message)

        return IntentResponse(
            False, "I'm sorry, I couldn't complete that request.", state
        )

    async def _show_results(self, state: ConversationState) -> IntentResponse:
        last = state.last_tool_result
        if not last:
            return IntentResponse(True, "Nothing to show.", state)
        return IntentResponse(True, "Here are the results.", state, last)

    def _confirm_action(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        state.pending_confirm = {
            "tool": decision.tool,
            "intent": decision.payload.get("intent"),
            "arguments": decision.payload.get("arguments", decision.payload),
        }
        msg = decision.message or "Please confirm to continue. Reply 'yes' or 'no'."
        return IntentResponse(True, msg, state)

    async def _execute_write(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        assert self._tool_registry is not None
        tool_name = decision.tool or ""
        tool = self._tool_registry.get(tool_name)
        if tool is None:
            state.pending_confirm = None
            state.tool_failure_count += 1
            state.last_failed_tool = tool_name
            return IntentResponse(
                True, "I'm sorry, I couldn't complete that. Let's try again.", state
            )
        try:
            request_model = self._build_write_request(tool_name, decision.payload)
            result = await tool.execute(request_model)
        except Exception as exc:
            state.pending_confirm = None
            state.tool_failure_count += 1
            state.last_failed_tool = tool_name
            if state.tool_failure_count >= 2:
                return IntentResponse(
                    True,
                    "I'm having trouble with that. Let's start over — type 'reset'.",
                    state,
                )
            return IntentResponse(
                True, "I'm sorry, something went wrong. Please try again.", state
            )
        state.pending_confirm = None
        state.tool_failure_count = 0
        state.last_failed_tool = None
        try:
            state.last_tool_result = result.model_dump()
        except Exception:
            state.last_tool_result = None
        if not getattr(result, "success", True):
            return IntentResponse(
                True, _safe_tool_message(getattr(result, "message", "")), state
            )
        msg = getattr(result, "message", "") or self._default_write_success(tool_name)
        state.current_goal = None
        return IntentResponse(True, msg, state, state.last_tool_result)

    @staticmethod
    def _default_write_success(tool_name: str) -> str:
        return {
            "createBooking": "Booking created.",
            "modifyBooking": "Booking updated.",
            "cancelBooking": "Booking cancelled.",
        }.get(tool_name, "Done.")

    def _build_write_request(self, tool_name: str, payload: dict[str, Any]):
        """Translate policy payload into the tool's request model. Strip
        fields the request doesn't accept (e.g. bookingCode on the wire
        format becomes bookingId for the cancel endpoint)."""
        clean = dict(payload or {})
        clean.pop("intent", None)
        clean.pop("tool", None)
        if tool_name == "createBooking":
            return CreateBookingRequest(**clean) if clean else CreateBookingRequest()
        if tool_name == "modifyBooking":
            return ModifyBookingRequest(**clean) if clean else ModifyBookingRequest()
        if tool_name == "cancelBooking":
            return CancelBookingRequest(**clean) if clean else CancelBookingRequest()
        raise ValueError(f"unknown write tool: {tool_name}")

    async def _answer_faq(
        self,
        state: ConversationState,
        decision: PolicyDecision,
        message: str,
    ) -> IntentResponse:
        if not self._knowledge_service:
            return IntentResponse(
                True,
                "I don't have a knowledge base enabled right now. "
                "I can help with bookings — what would you like to do?",
                state,
            )
        assert self._tool_registry is not None
        tool = self._tool_registry.get("faqSearch")
        result = await tool.execute(FAQSearchRequest(query=message))
        state.last_tool_result = result.model_dump() if hasattr(result, "model_dump") else None
        return IntentResponse(True, getattr(result, "message", ""), state, state.last_tool_result)

    async def _resume_booking(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        """Continue booking after an interruption."""
        return await self._next_booking_step(state)

    def _end_conversation(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        msg = decision.message or "Conversation ended. Type 'reset' to start over."
        return IntentResponse(True, msg, state)

    def _request_clarification(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        msg = decision.message or "Could you clarify what you'd like to do?"
        return IntentResponse(True, msg, state)

    def _clear_pending(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        state.pending_confirm = None
        state.pending_read_action = None
        state.current_goal = None
        state.previous_goal = None
        state = self._conversation_manager.reset(state)
        msg = decision.message or "Conversation reset. How can I help you?"
        return IntentResponse(True, msg, state)

    def _no_action_response(self, state: ConversationState) -> IntentResponse:
        return IntentResponse(True, "How can I help you?", state)

    async def _next_booking_step(self, state: ConversationState) -> IntentResponse:
        """Drive the booking tool chain via the policy."""
        decision = self._policy._next_booking_step(state)
        if decision.action == Action.ASK_SLOT:
            return await self._ask_slot(state, decision)
        if decision.action == Action.RUN_TOOL:
            # Create a dummy NLUResult for steps where we don't have a new NLU result.
            dummy_nlu = NLUResult(intent="RESUME", intent_confidence=1.0, entities={}, ambiguities=[])
            return await self._run_tool(state, decision, "", dummy_nlu)
        if decision.action == Action.END_CONVERSATION:
            return self._end_conversation(state, decision)
        return IntentResponse(True, "Booking flow paused.", state)

    def _ensure_slot_manager(self) -> None:
        if self._slot_manager is None:
            self._slot_manager = SlotFillingManager(
                conversation_manager=self._conversation_manager,
                nlu=self._nlu,
            )

    # ------------------------------------------------------------------
    # Slot-filling entry points
    # ------------------------------------------------------------------
    async def _execute_pending_read_action(
        self, state: ConversationState, action: str | None = None
    ) -> IntentResponse:
        """Callback used by SlotFillingManager when all slots are filled."""
        action_to_run = action or state.pending_read_action or ""
        state.pending_read_action = None # Clear the action now that we're running it

        if action_to_run == "search_shops":
            return await self._search_shops(state)
        if action_to_run == "search_courses":
            return await self._search_courses(state)
        if action_to_run == "search_slots":
            return await self._search_slots(state)
        if action_to_run == "get_therapists":
            return await self._get_therapists(state)
        if action_to_run == "check_eligibility":
            return await self._check_eligibility(state, "")
            
        logger.warning(f"Unknown pending read action: {action_to_run}")
        return IntentResponse(
            False,
            "I'm sorry, I couldn't complete that request.",
            state,
        )

    # ------------------------------------------------------------------
    # Tool execution helpers
    # ------------------------------------------------------------------
    async def _search_shops(
        self,
        state: ConversationState,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        tool = self._tool_registry.get("searchShops")
        result = await tool.execute(SearchShopsRequest())

        state.last_tool_result = result.model_dump()
        state.recent_tool_results.last_shop_search = result.model_dump()

        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)

        all_shops = result.data
        if not all_shops:
            return IntentResponse(True, "I'm sorry, no shops are available right now. Please try again later.", state)

        # If an area has been specified, filter the shops.
        area = state.booking_context.area
        shops_to_show = all_shops
        if area:
            shops_to_show = [s for s in all_shops if area.lower() in s.address.lower() or area.lower() in s.shopName.lower()]
            if not shops_to_show:
                 return IntentResponse(
                    True,
                    f"I'm sorry, no shops are available in {area}. Please try another area.",
                    state,
                    state.last_tool_result,
                )

        # Show the list AND prompt for selection.
        self._nlu.set_known_items(shops=shops_to_show)
        state.phase = ConversationPhase.SEARCHING_SHOPS
        shop_lines = "\n".join(f"- {s.shopName} ({s.address})" for s in shops_to_show)
        msg = f"Here are the available shops:\n{shop_lines}\n\nWhich shop would you like to visit?"
        data = {
            "options": [
                s.model_dump() if hasattr(s, "model_dump") else s for s in shops_to_show
            ]
        }
        return IntentResponse(True, msg, state, data)

    async def _search_courses(
        self,
        state: ConversationState,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        shop_id = state.booking_context.shop_id
        assert shop_id is not None, "shop_id must be populated before searching for courses"
        
        tool = self._tool_registry.get("searchCourses")
        result = await tool.execute(SearchCoursesRequest(shopId=int(shop_id)))
        state.last_tool_result = result.model_dump()
        state.recent_tool_results.last_course_search = result.model_dump()

        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)
        
        courses = result.data
        if not courses:
            state.phase = ConversationPhase.SEARCHING_SHOPS
            return IntentResponse(
                True,
                "I'm sorry, no courses are available at this shop. Please choose another shop.",
                state,
                state.last_tool_result,
            )

        self._nlu.set_known_items(courses=courses)
        state.phase = ConversationPhase.SEARCHING_COURSES

        course_lines = []
        for c in courses:
            duration_prices = [f"{d.duration}min ({d.price:,}đ)" for d in c.durations]
            course_lines.append(f"- {c.courseName}: {', '.join(duration_prices)}")
        
        msg = "Here are the available courses:\n" + "\n".join(course_lines) + "\n\nWhich massage course would you like?"
        data = {
            "options": [
                c.model_dump() if hasattr(c, "model_dump") else c for c in courses
            ]
        }
        return IntentResponse(True, msg, state, data)

    async def _search_slots(
        self,
        state: ConversationState,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        context = state.booking_context
        assert context.shop_id is not None and context.course_id is not None \
            and context.duration is not None and context.date is not None \
            and context.number_of_people is not None, \
            "slot_filling must populate all required slots before search_slots runs"
        
        from datetime import date as date_type
        tool = self._tool_registry.get("searchAvailableSlots")
        slots_request = SearchAvailableSlotsRequest(
            shopId=str(context.shop_id),
            date=date_type.fromisoformat(context.date),
            duration=context.duration,
            numberOfPeople=context.number_of_people,
            courseIds=str(context.course_id),
        )
        result = await tool.execute(slots_request)
        state.last_tool_result = result.model_dump()
        state.recent_tool_results.last_slot_search = result.model_dump()

        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)
        
        slots = result.data
        if not slots:
            return IntentResponse(
                True,
                "I'm sorry, no available slots match your selection. Please adjust date or duration.",
                state,
                state.last_tool_result,
            )
        
        state.phase = ConversationPhase.SEARCHING_SLOTS
        msg = "Here are the available appointment times:\n" + "\n".join(
            f"- {s.startTime}-{s.endTime} (capacity: {s.availableCapacity})" for s in slots
        )
        return IntentResponse(True, msg, state, state.last_tool_result)

    async def _get_therapists(
        self,
        state: ConversationState,
    ) -> IntentResponse:
        assert self._slot_manager is not None
        prompt_response = await self._slot_manager.start(state, "get_therapists")
        if prompt_response is not None:
            # prompt_response is a tuple (complete, message_text, data)
            _, message_text, data = prompt_response
            return IntentResponse(True, message_text, state, data)

        assert self._tool_registry is not None
        context = state.booking_context
        assert context.shop_id is not None and context.date is not None \
            and context.start_time is not None and context.duration is not None, \
            "slot_filling must populate all required slots before get_therapists runs"
        from datetime import date as date_type
        from datetime import time as time_type
        tool = self._tool_registry.get("getTherapists")
        therapists_request = GetTherapistsRequest(
            shopId=str(context.shop_id),
            date=date_type.fromisoformat(context.date),
            startTime=time_type.fromisoformat(context.start_time),
            duration=context.duration,
        )
        result = await tool.execute(therapists_request)
        state.last_tool_result = result.model_dump()
        state.recent_tool_results.last_therapist_search = result.model_dump()
        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)
        therapists = result.data
        msg = "Available therapists:\n" + "\n".join(
            f"- {t.name} ({t.gender}) - {'Available' if t.isAvailable else 'Busy'}"
            for t in therapists
        )
        return IntentResponse(True, msg, state, state.last_tool_result)

    async def _check_eligibility(
        self,
        state: ConversationState,
        message: str,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        phone = state.booking_context.phone_number
        assert phone is not None, "slot_filling must populate phone_number before check_eligibility runs"

        state, ok = self._conversation_manager.transition(state, "select_therapist")
        if not ok:
            return IntentResponse(False, _safe_tool_message(state.error_message or "Let's start over — how can I help you?"), state)

        tool = self._tool_registry.get("checkEligibility")
        result = await tool.execute(CheckEligibilityRequest(phoneNumber=phone))
        state.last_tool_result = result.model_dump()
        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)
        data = result.data
        if data.isEligible:
            msg = f"Eligible! Member rank: {data.memberRank or 'N/A'}, Visits: {data.visitCount}"
        else:
            msg = f"Not eligible: {data.blockReason or 'Blocked'}"
        return IntentResponse(True, msg, state, state.last_tool_result)

    async def _lookup_booking(self, state: ConversationState, message: str) -> IntentResponse:
        import re
        assert self._tool_registry is not None
        # If the policy already extracted a booking code into state, use it.
        booking_code = state.booking_context.booking_code
        if not booking_code:
            booking_code_match = re.search(r"BK\d{8,}", message.upper())
            if booking_code_match:
                booking_code = booking_code_match.group(0)
        if not booking_code:
            return IntentResponse(False, "Please provide your booking code.", state)

        tool = self._tool_registry.get("lookupBooking")
        try:
            result = await tool.execute(LookupBookingRequest(bookingCode=booking_code))
        except Exception:
            state.tool_failure_count += 1
            state.last_failed_tool = "lookupBooking"
            return IntentResponse(
                True,
                "I'm sorry, I couldn't look up that booking right now. Please try again.",
                state,
            )
        try:
            state.last_tool_result = result.model_dump()
        except Exception:
            state.last_tool_result = None
        state.tool_failure_count = 0
        state.last_failed_tool = None
        if not getattr(result, "success", True):
            return IntentResponse(
                True, _safe_tool_message(getattr(result, "message", "")), state
            )
        bookings = getattr(result, "data", None) or []
        if bookings:
            b = bookings[0]
            msg = (
                f"Booking {getattr(b, 'bookingCode', '')}: "
                f"{getattr(b, 'shopName', '')} on {getattr(b, 'bookingDate', '')} "
                f"at {getattr(b, 'startTime', '')} - {getattr(b, 'status', '')}"
            )
        else:
            msg = "No booking found with that code."
        return IntentResponse(True, msg, state, state.last_tool_result)

    async def _faq_search(self, state: ConversationState, message: str) -> IntentResponse:
        if not self._knowledge_service:
            return IntentResponse(
                True,
                "I don't have a knowledge base enabled right now. "
                "I can help with bookings — what would you like to do?",
                state,
            )
        assert self._tool_registry is not None
        state, ok = self._conversation_manager.transition(state, "faq_search")
        if not ok:
            return IntentResponse(False, _safe_tool_message(state.error_message or "Let's start over — how can I help you?"), state)
        tool = self._tool_registry.get("faqSearch")
        result = await tool.execute(FAQSearchRequest(query=message))
        state.last_tool_result = result.model_dump()
        return IntentResponse(True, result.message, state, state.last_tool_result)



def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = Settings()
    chat_endpoint = ChatEndpoint(settings=settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await chat_endpoint.initialize()
        yield
        await chat_endpoint.close()

    app = FastAPI(title="Chatbot Service", version="1.0.0", lifespan=lifespan)

    origins = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        return await chat_endpoint.process_message(request)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "rag_enabled": settings.enable_rag}

    return app
