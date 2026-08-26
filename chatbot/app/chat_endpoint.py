import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
from chatbot.conversation.state import (
    ConversationManager,
    ConversationPhase,
    ConversationState,
    BookingContext,
    RecentToolResults,
)
from chatbot.nlu.models import NLUResult, Intent, EntityType
from chatbot.nlu.nlu import NLU
from chatbot.app.package_generator import generate_packages


logger = logging.getLogger(__name__)


class PackageSelection(BaseModel):
    """Payload for a pre-selected package from the frontend."""
    display_name: str = Field(..., alias="displayName")
    main_course_id: int = Field(..., alias="mainCourseId")
    addon_ids: list[int] = Field(default_factory=list, alias="addonIds")
    total_duration: int = Field(..., alias="totalDuration")
    total_price: int = Field(..., alias="totalPrice")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: str
    user_id: str | None = None
    start_conversation: bool = False
    package_selection: PackageSelection | None = Field(default=None, alias="packageSelection")



class ChatResponse(BaseModel):
    """Chat response model."""
    success: bool
    message: str
    session_id: str
    phase: ConversationPhase
    booking_state: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
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

import traceback

def _extract_answer_from_faq(faq_content: str) -> str:
    """
    Extracts the answer from a FAQ string that contains both question and answer.
    Assumes the first '?' or ':' separates the question from the answer.
    """
    # Find the position of the first question mark
    question_mark_pos = faq_content.find("?")
    # Find the position of the first colon
    colon_pos = faq_content.find(":")

    # Determine the split position
    split_pos = -1
    if question_mark_pos != -1 and colon_pos != -1:
        split_pos = min(question_mark_pos, colon_pos)
    elif question_mark_pos != -1:
        split_pos = question_mark_pos
    elif colon_pos != -1:
        split_pos = colon_pos

    # If a separator is found, extract the answer part
    if split_pos != -1:
        return faq_content[split_pos + 1 :].lstrip()

    # If no separator is found, return the original content
    return faq_content


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

        # This is commented out because courses are shop-specific and cannot be
        # pre-fetched globally at startup. The NLU's course knowledge is
        # dynamically updated after the `search_courses` tool is run for a
        # specific shop.
        courses = []
        # try:
        #     course_tool = SearchCoursesTool(self._http_client)
        #     # This call is invalid as SearchCoursesRequest requires a shopId.
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
                model_name="all-MiniLM-L6-v2"
            )
            self._settings.embedding_dim = embedding_service.embedding_dim
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

        if request.start_conversation:
            return await self._start_conversation(request)

        session_store = self._session_store
        assert session_store is not None
        session = await session_store.get_session(request.session_id)
        if session is None:
            session = await session_store.create_session(request.session_id, request.user_id)

        state = session.conversation_state
        logger.info(f"State at start of turn: {state}")

        # If a package is selected, apply it to the context FIRST.
        if request.package_selection:
            pkg = request.package_selection
            logger.info(f"Received packageSelection payload: {pkg}")
            
            # Apply package data to the booking context
            state.booking_context.course_id = pkg.main_course_id
            state.booking_context.addon_ids = pkg.addon_ids
            state.booking_context.duration = pkg.total_duration

            # Resolve and set course and add-on names
            course_name, addon_names = self._resolve_package_names(
                state, pkg.main_course_id, pkg.addon_ids
            )
            state.booking_context.course_name = course_name
            state.booking_context.addon_names = addon_names

            logger.info(f"Received packageSelection: main_course_id={pkg.main_course_id}, addon_ids={pkg.addon_ids}, total_duration={pkg.total_duration}")
            logger.info(f"Resolved package names: course_name='{course_name}', addon_names={addon_names}")
            logger.info(f"Final BookingContext: {state.booking_context.model_dump()}")

        # 1. NLU understands the message
        focused_slot = state.pending_slot_to_fill
        nlu_result = await self._nlu.understand(request.message, state, focused_slot=focused_slot)
        
        if nlu_result and nlu_result.entities:
            logger.info(f"NLU extracted entities: {nlu_result.entities}")
            nlu_duration = nlu_result.entity_value(EntityType.DURATION)
            logger.info(f"NLU extracted duration: {nlu_duration}")
        else:
            logger.info("NLU extracted no entities.")


        logger.info(f"[MULTI_PASS_NLU] First pass entities: {nlu_result.entities if nlu_result else 'None'}")


        # 2. Multi-pass NLU for course extraction
        if (
            nlu_result and nlu_result.intent == Intent.CREATE_BOOKING
            and nlu_result.entity_value(EntityType.SHOP_ID)
            and not nlu_result.entity_value(EntityType.COURSE_ID)
        ):
            shop_id = nlu_result.entity_value(EntityType.SHOP_ID)
            logger.info(f"[MULTI_PASS_NLU] Running search_courses for shop_id {shop_id} to enrich NLU knowledge")
            
            try:
                course_tool = self._tool_registry.get("searchCourses")
                course_result = await course_tool.execute(SearchCoursesRequest(shopId=int(shop_id)))

                if course_result.success:
                    courses = course_result.data
                    self._nlu.set_known_items(courses=courses)
                    logger.info(f"[MULTI_PASS_NLU] Known courses updated: {[c.courseName for c in courses]}")

                    # Run NLU again with the enriched knowledge
                    second_nlu_result = await self._nlu.understand(request.message, state)
                    logger.info(f"[MULTI_PASS_NLU] Second pass entities: {second_nlu_result.entities if second_nlu_result else 'None'}")

                    if second_nlu_result and second_nlu_result.entities:
                        # Merge entities, giving preference to the second pass for duplicates.
                        first_pass_entities = {e.type: e for e in nlu_result.entities}
                        second_pass_entities = {e.type: e for e in second_nlu_result.entities}
                        merged_entities_map = {**first_pass_entities, **second_pass_entities}
                        nlu_result.entities = list(merged_entities_map.values())
                        logger.info(f"[MULTI_PASS_NLU] Final merged entities: {nlu_result.entities}")

            except Exception as e:
                logger.error(f"[MULTI_PASS_NLU] Error during second pass: {e}", exc_info=True)


        state.nlu_result = nlu_result
        logger.info(f"NLU result: {nlu_result}")

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
            # CRITICAL FIX: Apply NLU entities directly to the context before
            # the policy decides the next move. This handles cases where the user
                        # provides information outside of an active slot-filling loop.
            if nlu_result and nlu_result.entities:
                package_selected = request.package_selection is not None
                logger.info(f"booking_context.duration before NLU merge: {state.booking_context.duration}")
                self._conversation_manager.apply_nlu_entities_to_booking_context(
                    state, nlu_result.entities, package_selected=package_selected
                )
                logger.info(f"booking_context.duration after NLU merge: {state.booking_context.duration}")

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
            booking_state=response.state.to_frontend_booking_state(),
            data=response.data,
            payload=decision.payload,
            error=str(response.error) if response.error else None,
        )



    async def _start_conversation(self, request: ChatRequest) -> ChatResponse:
        """Handles the very first turn of a new conversation."""
        logger.info(f"Starting new conversation for session: {request.session_id}")
        session_store = self._session_store
        assert session_store is not None

        # Create a new session and initial state
        session = await session_store.create_session(request.session_id, request.user_id)
        state = session.conversation_state

        # Get the initial action from the policy (e.g., greet and ask area)
        decision = self._policy.decide(state, Intent.GREETING, message="", nlu_result=None)
        logger.info(f"Initial policy decision: {decision}")
        
        # Execute the decision
        response = await self._execute_decision(state, decision, "")

        # Save state and return the response
        try:
            session.conversation_state = response.state
            await session_store.save_session(session)
        except AttributeError:
            if isinstance(response, ChatResponse):
                await session_store.save_session(session)
                return response
            raise

        return ChatResponse(
            success=response.success,
            message=str(response.message or ""),
            session_id=session.session_id,
            phase=response.state.phase,
            booking_state=response.state.to_frontend_booking_state(),
            data=response.data,
            payload=decision.payload,
            error=str(response.error) if response.error else None,
        )





    # ------------------------------------------------------------------
    # Action dispatcher — one handler per Action enum value
    # ------------------------------------------------------------------
    def _resolve_package_names(
        self,
        state: ConversationState,
        main_course_id: int,
        addon_ids: list[int],
    ) -> tuple[str | None, list[str]]:
        """Finds course and add-on names from the last course search result."""
        course_name = None
        addon_names = []
        
        last_search = state.recent_tool_results.last_course_search
        if not last_search or not last_search.get("data"):
            logger.warning("Cannot resolve package names: last_course_search is empty.")
            return None, []

        all_courses = last_search["data"]
        
        # Create a lookup map for faster access
        course_map = {course['courseId']: course['courseName'] for course in all_courses if 'courseId' in course and 'courseName' in course}

        # Find main course name
        course_name = course_map.get(main_course_id)
        if not course_name:
            logger.warning(f"Could not resolve main course name for ID: {main_course_id}")

        # Find add-on names
        if addon_ids:
            resolved_names = []
            for addon_id in addon_ids:
                name = course_map.get(addon_id)
                if name:
                    resolved_names.append(name)
                else:
                    logger.warning(f"Could not resolve addon name for ID: {addon_id}")
            addon_names = resolved_names
            
        return course_name, addon_names

    async def _execute_decision(
        self,
        state: ConversationState,
         decision: PolicyDecision,
         message: str,
     ) -> IntentResponse:
        logger.info(f"Received decision: {decision}")
        if self._slot_manager is None:
            self._ensure_slot_manager()
        assert self._slot_manager is not None

        action = decision.action
        tool = decision.tool or ''

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
            return await self._faq_search(state, message)

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
       logger.info(f"Setting pending_confirm: {state.pending_confirm}")
       msg = decision.message or "Please confirm to continue. Reply 'yes' or 'no'."
       return IntentResponse(True, msg, state)

    async def _execute_write(
        self, state: ConversationState, decision: PolicyDecision
    ) -> IntentResponse:
        pending = state.pending_confirm or {}
        tool_name = pending.get("tool") or decision.tool or ""
        payload = pending.get("arguments") or decision.payload or {}

        tool = self._tool_registry.get(tool_name)
        
        if tool is None:
            logger.error(f"Tool '{tool_name}' not found in registry.")
            state.pending_confirm = None
            state.tool_failure_count += 1
            state.last_failed_tool = tool_name
            return IntentResponse(
                True, "I'm sorry, I couldn't complete that. Let's try again.", state
            )
        
        try:
            request_model = self._build_write_request(tool_name, payload, state)
            result = await tool.execute(request_model)
        except Exception as exc:
            logger.error(f"Error executing write tool {tool_name}: {exc}", exc_info=True)
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
        
        # After a successful booking, reset the booking context for the next turn.
        if tool_name == "createBooking" and getattr(result, "success", True):
            logger.info("Booking successful. Resetting booking context and setting phase to BOOKING_COMPLETE.")
            state.phase = ConversationPhase.BOOKING_COMPLETE
            state.booking_context = BookingContext()
            state.recent_tool_results = RecentToolResults()
            state.pending_slot_to_fill = None

        return IntentResponse(True, msg, state, state.last_tool_result)

    @staticmethod
    def _default_write_success(tool_name: str) -> str:
        return {
            "createBooking": "Booking created.",
            "modifyBooking": "Booking updated.",
            "cancelBooking": "Booking cancelled.",
        }.get(tool_name, "Done.")

    def _build_write_request(self, tool_name: str, payload: dict[str, Any], state: ConversationState):
        """Translate policy payload into the tool's request model."""
        context_data = state.booking_context.model_dump(exclude_none=True)
        final_payload = {**context_data, **(payload or {})}

        if tool_name == "createBooking":
            services = []
            if final_payload.get("course_id"):
                services.append(
                    {
                        "courseId": final_payload["course_id"],
                        "personIndex": 1,  # Assuming 1 for now
                    }
                )

            create_booking_payload = {
                "shopId": final_payload.get("shop_id"),
                "userName": final_payload.get("user_name"),
                "phoneNumber": final_payload.get("phone_number"),
                "bookingDate": final_payload.get("date"),
                "startTime": final_payload.get("start_time"),
                "duration": final_payload.get("duration"),
                "numberOfPeople": final_payload.get("number_of_people"),
                "services": services,
                 "addOns": final_payload.get("addOns", []),
                "therapistId": final_payload.get("therapist_id"),
            }
            logger.info(f"Final createBooking payload: {create_booking_payload}")

            return CreateBookingRequest(**create_booking_payload)
        if tool_name == "modifyBooking":
            return ModifyBookingRequest(**final_payload)
        if tool_name == "cancelBooking":
            cancel_payload = {
                "bookingCode": final_payload.get("booking_code"),
                "phoneNumber": final_payload.get("phone_number")
            }
            return CancelBookingRequest(**{k: v for k, v in cancel_payload.items() if v is not None})
            
        raise ValueError(f"unknown write tool: {tool_name}")

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
        logger.info("BookingContext: %s", state.booking_context)

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
        logger.info("Saved last_shop_search:")
        logger.info(state.recent_tool_results.last_shop_search)

        if not result.success:
            return IntentResponse(False, _safe_tool_message(result.message), state, state.last_tool_result)

        all_shops = result.data
        if not all_shops:
            return IntentResponse(True, "I'm sorry, no shops are available right now. Please try again later.", state)

        # If an area has been specified, filter the shops.
        shops_to_show = all_shops
        
        # Show the list AND prompt for selection.
        self._nlu.set_known_items(shops=shops_to_show)
        state.phase = ConversationPhase.SEARCHING_SHOPS
        msg = "Which shop would you like to visit?"
        data = {"shops": [s.model_dump() for s in shops_to_show]}
        return IntentResponse(True, msg, state, data)

    async def _search_courses(
        self,
        state: ConversationState,
    ) -> IntentResponse:
        assert self._tool_registry is not None
        shop_id = state.booking_context.shop_id
        assert shop_id is not None, "shop_id must be populated before searching for courses"
        
        tool = self._tool_registry.get("searchCourses")
        # Fetch main courses
        main_courses_result = await tool.execute(SearchCoursesRequest(shopId=int(shop_id), type="main"))
        main_courses = main_courses_result.data if main_courses_result.success else []

        # Fetch add-on courses
        addon_courses_result = await tool.execute(SearchCoursesRequest(shopId=int(shop_id), type="addon"))
        addon_courses = addon_courses_result.data if addon_courses_result.success else []

        # Combine and store both main and addon courses for future lookups
        all_courses = main_courses + addon_courses
        combined_result = {
            "success": main_courses_result.success or addon_courses_result.success,
            "message": main_courses_result.message,
            "data": [c.model_dump() for c in all_courses]
        }
        state.last_tool_result = combined_result
        state.recent_tool_results.last_course_search = combined_result
        
        logger.info(f"Saved last_course_search with {len(all_courses)} total courses.")

        if not main_courses_result.success:
            return IntentResponse(False, _safe_tool_message(main_courses_result.message), state, state.last_tool_result)
        
        if not main_courses and not addon_courses:
            state.phase = ConversationPhase.SEARCHING_SHOPS
            return IntentResponse(
                True,
                "I'm sorry, no courses are available at this shop. Please choose another shop.",
                state,
                state.last_tool_result,
            )

        self._nlu.set_known_items(courses=main_courses) # Only main courses for NLU for now
        
        # Generate packages from both main and addon courses
        generated_packages = generate_packages(main_courses, addon_courses, state.booking_context.duration)

        state.phase = ConversationPhase.SELECTING_PACKAGE

        course_lines = []
        for c in main_courses:
            duration_prices = [f"{d.duration}min ({d.price:,}đ)" for d in c.durations]
            course_lines.append(f"- {c.courseName}: {', '.join(duration_prices)}")
        
        msg = "Here are the available courses:\n" + "\n".join(course_lines) + "\n\nWhich massage course would you like?"
        data = {
            "options": [ # Keep options for backward compatibility and general display
                c.model_dump() if hasattr(c, "model_dump") else c for c in main_courses
            ],
            "packages": generated_packages, # Add packages to the data payload for the frontend
            "confirmed": False, # Add confirmed flag for frontend UI state
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
        available_times = [s.startTime for s in slots]
        msg = "Here are the available appointment times. Please choose a start time."
        data = {"available_times": available_times}
        
        return IntentResponse(True, msg, state, data)

    async def _get_therapists(
        self,
        state: ConversationState,
    ) -> IntentResponse:


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
        self._nlu.set_known_items(therapists=therapists)
        state.phase = ConversationPhase.SELECTING_THERAPIST
        msg = "Choose a therapist (Optional)."
        data = {
            "options": [
                t.model_dump() if hasattr(t, "model_dump") else t for t in therapists
            ]
        }
        return IntentResponse(True, msg, state, data)

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
        tool = self._tool_registry.get("faqSearch")
        result = await tool.execute(FAQSearchRequest(query=message))
        state.last_tool_result = (
            result.model_dump() if hasattr(result, "model_dump") else None
        )

        logger.info(f"FAQ query: '{message}'")
        if result.success and result.data:
            # Sort by score, highest first
            sorted_results = sorted(result.data, key=lambda x: x.score, reverse=True)
            for r in sorted_results:
                logger.info(f"Retrieved chunk score: {r.score:.4f}, content: \"{r.content[:80]}...\"")

            top_result = sorted_results[0]
            
            # This is the fix: reject results below a reasonable similarity threshold.
            # The score is cosine similarity, so it's in the [0, 1] range.
            # 0.7 is a common threshold for good semantic similarity.
            SIMILARITY_THRESHOLD = 0.7
            if top_result.score >= SIMILARITY_THRESHOLD:
                response_message = _extract_answer_from_faq(top_result.content)
                logger.info(f"FAQ answer found with score {top_result.score:.4f}.")
            else:
                logger.info(f"Top result score {top_result.score:.4f} is below threshold {SIMILARITY_THRESHOLD}. Rejecting.")
                response_message = (
                    "I couldn't find a specific answer to your question. "
                    "I can help with bookings — what would you like to do?"
                )
        else:
            logger.info("No FAQ results returned from knowledge service.")
            response_message = (
                "I couldn't find a specific answer to your question. "
                "I can help with bookings — what would you like to do?"
            )

        return IntentResponse(
            True, response_message, state, state.last_tool_result
        )



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
