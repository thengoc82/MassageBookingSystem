# chatbot/conversation/slot_filling.py
"""Slot-filling manager. Decides what to ask next, parses user replies,
updates BookingContext, resumes interrupted flows, and fires the callback
when every required slot is filled.
"""
from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
import inspect
import logging
import re
from chatbot.nlu.nlu import NLU

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from chatbot.conversation.state import ConversationManager

from chatbot.conversation.slot_parser import parse_and_fill_slots
from chatbot.conversation.interfaces import IntentResponse
from chatbot.conversation.slot_prompts import get_prompt
from chatbot.conversation.state import BookingContext, ConversationState, ConversationPhase
from chatbot.tools.search_tools import SearchCoursesTool, SearchCoursesRequest


def _invalid_input_message(slot: str | None) -> str:
    if slot is None:
        return "I'm sorry, I didn't quite catch that. Could you rephrase?"
    return f"I'm sorry, I didn't understand that for {slot.replace('_', ' ')}. Please try again."


class SlotFillingManager:
    REQUIRED_SLOTS: dict[str, list[str]] = {
        "search_shops": ["area"],
        "search_courses": ["shop_id"],
        "search_slots": [
            "shop_id",
            "course_id",
            "duration",
            "date",
            "number_of_people",
        ],
        "get_therapists": ["shop_id", "date", "start_time", "duration"],
        "check_eligibility": ["phone_number"],
        "create_booking": [
            "shop_id",
            "course_id",
            "duration",
            "date",
            "start_time",
            "number_of_people",
            "phone_number",
        ],
    }

    def __init__(
        self,
        conversation_manager: "ConversationManager",
        nlu: "NLU",
    ):
        self._conversation_manager = conversation_manager
        self._nlu = nlu

    async def start(
        self, state: ConversationState, tool_name: str
    ) -> tuple[bool, str, dict | None]:
        """
        Starts the slot-filling process for a given tool.
        Returns:
            - A boolean indicating if slot-filling is needed.
            - A message to send to the user (either a prompt or a confirmation).
            - Optional data payload (e.g., list of options).
        """
        state.pending_read_action = tool_name
        # Immediately try to fill from existing context
        is_complete, message, data = await self.continue_filling(state, "")
        return not is_complete, message, data

    async def continue_filling(
        self,
        state: ConversationState,
        message: str,
        nlu_result: Optional["NLUResult"] = None,
    ) -> tuple[bool, str, dict | None]:
        """
        Continues the slot-filling process.
        Returns:
            - completion_status:
                - True: All slots for the action are filled.
                - False: More slots are needed.
            - A message to send to the user.
            - Optional data payload.
        """
        action = state.pending_read_action
        if not action:
            return True, "No action pending.", None

        # If a slot was pending but is now filled (e.g., by multi-intent),
        # clear the pending status and re-evaluate from the top.
        if state.pending_slot_to_fill and getattr(state.booking_context, state.pending_slot_to_fill, None) is not None:
            logger.debug(f"Slot '{state.pending_slot_to_fill}' was already filled. Skipping focused parsing.")
            state.pending_slot_to_fill = None
            # Re-run to find the *next* missing slot.
            return await self.continue_filling(state, "", nlu_result=nlu_result)

        required = self.REQUIRED_SLOTS.get(action, [])
        if not required:
            # No slots required for this action, so it's "complete"
            return True, "", None

        # 1. Parse the incoming message and update the booking context.
        logger.debug(f"Parsing message '{message}' for slots. Pending slot: {state.pending_slot_to_fill}")
        was_any_slot_filled = await parse_and_fill_slots(
            message, state, self._nlu, self._conversation_manager,
            focused_slot=state.pending_slot_to_fill, nlu_result=nlu_result
        )

        # If we were expecting a specific slot, but it wasn't filled by any parser,
        # then the input was likely invalid.
        if state.pending_slot_to_fill and not was_any_slot_filled and message:
            logger.warning(f"Invalid input '{message}' for slot '{state.pending_slot_to_fill}'")
            prompt = _invalid_input_message(state.pending_slot_to_fill)
            # Don't clear the pending slot, just return the error message
            return False, prompt, None
        logger.debug(f"Booking context after parsing: {state.booking_context}")

        # 2. Check for the next missing slot.
        next_missing = await self._find_first_missing_slot(state, required)

        # 3. Decide what to do next.
        if not next_missing:
            logger.info(f"All slots for action '{action}' are filled.")
            state.pending_slot_to_fill = None
            state.pending_read_action = None  # Clear the action, as it's ready to run
            return True, "I have all the information I need.", None  # Signal completion
        else:
            logger.info(f"Next missing slot for '{action}': {next_missing}")
            state.pending_slot_to_fill = next_missing
            prompt, data = self._get_prompt_and_data(state, next_missing)
            return False, prompt, data

    async def _find_first_missing_slot(
        self, state: "ConversationState", required: list[str]
    ) -> Optional[str]:
        # Before checking for missing slots, try to resolve course by name if possible.
        if "course_id" in required and not state.booking_context.course_id and state.booking_context.course_name:
            await self._resolve_course_by_name(state)

        for slot in required:
            if getattr(state.booking_context, slot, None) is None:
                return slot
        return None

    def _get_prompt_and_data(
        self, state: ConversationState, slot_name: str
    ) -> tuple[str, dict | None]:
        message = get_prompt(slot_name)
        data: dict[str, Any] = {}
        options_data = None

        if slot_name == "shop_id":
            shops_result = state.recent_tool_results.last_shop_search or {}
            shops = shops_result.get("data", [])
            if shops:
                names = [s.shopName for s in shops]
                message += "\n\nAvailable shops:\n" + "\n".join(f"- {n}" for n in names if n)
                options_data = [s for s in shops]

        if slot_name == "course_id":
            courses_result = state.recent_tool_results.last_course_search or {}
            courses = courses_result.get("data", [])
            if courses:
                # Handle both dict and object for courses
                names = [c.courseName if hasattr(c, 'courseName') else c['courseName'] for c in courses]
                message += "\n\nAvailable courses:\n" + "\n".join(f"- {n}" for n in names if n)
                options_data = [c for c in courses]

        if options_data:
            data["options"] = options_data

        return message, data or None

    async def _resolve_course_by_name(self, state: ConversationState) -> None:
        bc = state.booking_context
        if not (bc.course_name and bc.course_id is None and bc.shop_id is not None):
            return

        # Use recent tool results if available, otherwise call the tool.
        courses = state.recent_tool_results.last_course_search
        if not courses:
            from chatbot.gateway.client import create_client
            http_client = await create_client()
            try:
                search_tool = SearchCoursesTool(http_client)
                result = await search_tool.execute(SearchCoursesRequest(shopId=bc.shop_id))
                if result.success:
                    courses = result.data
            finally:
                await http_client.close()

        if not courses:
            return

        for course in courses:
            if course.courseName.lower() == bc.course_name.lower():
                bc.course_id = course.courseId
                if bc.duration is None and course.durations:
                    # Default to the first available duration
                    bc.duration = course.durations[0].duration
                break
