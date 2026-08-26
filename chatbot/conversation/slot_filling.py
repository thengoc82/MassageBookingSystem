# chatbot/conversation/slot_filling.py
from __future__ import annotations
import logging
from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime
import re

from chatbot.conversation.parser_result import ParseResult
if TYPE_CHECKING:
    from chatbot.conversation.state import ConversationManager, ConversationState
    from chatbot.nlu.nlu import NLU
    from chatbot.nlu.models import NLUResult

from chatbot.conversation.slot_parser import parse_message
from chatbot.conversation.slot_prompts import get_prompt
from chatbot.tools.search_tools import SearchCoursesTool, SearchCoursesRequest

logger = logging.getLogger(__name__)

def _invalid_input_message(slot: str | None) -> str:
    if slot is None:
        return "I'm sorry, I didn't quite catch that. Could you rephrase?"
    return f"I'm sorry, the value you provided for {slot.replace('_', ' ')} seems invalid. Please try again."

class SlotFillingManager:
    MAX_RETRIES = 2

    REQUIRED_SLOTS: dict[str, list[str]] = {
        "provide_people": ["number_of_people"],
        "provide_duration": ["duration"],
        "search_shops": [], # No longer requires area
        "select_package": ["course_id"],
        "search_courses": ["shop_id"],
        "search_slots": [
            "shop_id", "date", "number_of_people", "duration", "course_id"
        ],
        "get_therapists": ["shop_id", "date", "start_time", "duration"],
        "check_eligibility": ["phone_number"],
        "create_booking": [
            "shop_id",
            "date",
            "number_of_people",
            "course_id",
            "start_time",
            "phone_number",
            # therapist_id is optional
        ],
    }

    SLOT_DEPENDENCIES: dict[str, list[str]] = {
        "shop_id": ["course_id", "therapist_id", "start_time"],
        "date": ["start_time", "therapist_id"],
        "course_id": ["duration", "therapist_id"],
    }

    def __init__(self, conversation_manager: "ConversationManager", nlu: "NLU"):
        self._conversation_manager = conversation_manager
        self._nlu = nlu

    async def start(self, state: ConversationState, tool_name: str) -> tuple[bool, str, dict | None]:
        state.pending_read_action = tool_name
        state.slot_fill_retries = 0
        is_complete, message, data = await self.continue_filling(state, "")
        return not is_complete, message, data

    async def continue_filling(
        self, state: ConversationState, message: str, nlu_result: Optional["NLUResult"] = None
    ) -> tuple[bool, str, dict | None]:
        action = state.pending_read_action
        if not action:
            return True, "No action pending.", None

        if state.pending_slot_to_fill and getattr(state.booking_context, state.pending_slot_to_fill, None) is not None:
            logger.debug(f"Slot '{state.pending_slot_to_fill}' was filled externally. Re-evaluating.")
            state.pending_slot_to_fill = None
            state.slot_fill_retries = 0
            return await self.continue_filling(state, message, nlu_result=nlu_result)

        required = self.REQUIRED_SLOTS.get(action, [])
        if not required:
            return True, "", None

        # 1. Parse message without mutating state
        parse_result = await parse_message(
            message, self._nlu, state.recent_tool_results,
            focused_slot=state.pending_slot_to_fill,
            nlu_result=nlu_result,
            base_date=state.booking_context.date
        )

        # 2. Apply parse results to context, with validation and dependency invalidation
        filled_any_valid_slot = self._apply_parse_result(parse_result, state)

        # 3. Handle invalid input and retries
        if state.pending_slot_to_fill and not filled_any_valid_slot and message:
            state.slot_fill_retries += 1
            logger.warning(
                f"Invalid input '{message}' for slot '{state.pending_slot_to_fill}'. "
                f"Retry {state.slot_fill_retries}/{self.MAX_RETRIES}."
            )
            if state.slot_fill_retries >= self.MAX_RETRIES:
                state.pending_slot_to_fill = None
                state.slot_fill_retries = 0
                return False, "I'm having trouble understanding. Let's try that step again.", None
            
            prompt = _invalid_input_message(state.pending_slot_to_fill)
            return False, prompt, None
        
        # If a valid slot was filled, reset the retry counter
        if filled_any_valid_slot:
            state.slot_fill_retries = 0

        # 4. Check for the next missing slot
        next_missing = await self._find_first_missing_slot(state, required)

        # 5. Decide next step
        if not next_missing:
            logger.info(f"All slots for action '{action}' are filled.")
            state.pending_slot_to_fill = None
            # The caller is responsible for clearing pending_read_action after execution.
            return True, "I have all the information I need.", None
        else:
            logger.info(f"Next missing slot for '{action}': {next_missing}")
            state.pending_slot_to_fill = next_missing
            prompt, data = self._get_prompt_and_data(state, next_missing)
            return False, prompt, data

    def _apply_parse_result(self, result: ParseResult, state: ConversationState) -> bool:
        if not result.has_results:
            return False

        any_slot_filled = False
        sorted_slots = sorted(result.parsed_slots.values(), key=lambda s: s.confidence, reverse=True)

        for slot in sorted_slots:
            # --- Validation Step ---
            is_valid, clean_value = self._validate_slot(slot.name, slot.value)
            if not is_valid:
                logger.warning(f"Validation failed for slot '{slot.name}' with value '{slot.value}'.")
                continue

            # --- State Mutation Step ---
            old_value = getattr(state.booking_context, slot.name, None)
            
            # Special handling for complex objects
            if slot.name == "shop":
                setattr(state.booking_context, "shop_id", self._get_attr(clean_value, 'shopId'))
                setattr(state.booking_context, "shop_name", self._get_attr(clean_value, 'shopName'))
                any_slot_filled = True
            elif slot.name == "area":
                setattr(state.booking_context, "area", clean_value)
                any_slot_filled = True
            elif slot.name == "add_on":
                # Ensure addon_ids and addon_names are lists
                if not isinstance(getattr(state.booking_context, "addon_ids", None), list):
                    state.booking_context.addon_ids = []
                if not isinstance(getattr(state.booking_context, "addon_names", None), list):
                    state.booking_context.addon_names = []

                # Extract ID and Name and avoid duplicates
                add_on_id = self._get_attr(clean_value, 'courseId')
                add_on_name = self._get_attr(clean_value, 'courseName')

                if add_on_id and add_on_id not in state.booking_context.addon_ids:
                    state.booking_context.addon_ids.append(add_on_id)
                    if add_on_name:
                        state.booking_context.addon_names.append(add_on_name)
                
                any_slot_filled = True
            elif slot.name == "course":
                setattr(state.booking_context, "course_id", self._get_attr(clean_value, 'courseId'))
                setattr(state.booking_context, "course_name", self._get_attr(clean_value, 'courseName'))
                if state.booking_context.duration is None:
                    durations = self._get_attr(clean_value, 'durations', [])
                    if durations:
                        setattr(state.booking_context, "duration", self._get_attr(durations[0], 'duration'))
                any_slot_filled = True
            else:
                 # Standard attribute
                setattr(state.booking_context, slot.name, clean_value)
                any_slot_filled = True
            
            logger.info(
                f"Applied slot '{slot.name}'. Previous: '{old_value}', "
                f"New: '{clean_value}', Source: '{slot.source}'"
            )

            # --- Dependency Invalidation ---
            self._invalidate_dependencies(slot.name, state)

        return any_slot_filled

    def _validate_slot(self, name: str, value: Any) -> tuple[bool, Any]:
        if value is None:
            return False, None
        
        if name == "date":
            try:
                # Dates in the past are invalid
                parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
                if parsed_date < datetime.now().date():
                    logger.warning(f"Validation failed: Date '{value}' is in the past.")
                    return False, None
            except ValueError:
                return False, None
        
        if name == "number_of_people":
            try:
                num = int(value)
                if not 1 <= num <= 10: # Example business rule
                    logger.warning(f"Validation failed: Number of people '{num}' is not between 1 and 10.")
                    return False, None
            except (ValueError, TypeError):
                return False, None

        if name == "phone_number":
             # Basic regex for phone format, can be improved
            if not re.match(r'^\+?\d[\d\s-]{8,}\d$', str(value)):
                logger.warning(f"Validation failed: Invalid phone number format for '{value}'.")
                return False, None

        return True, value
    
    def _invalidate_dependencies(self, changed_slot: str, state: ConversationState):
        """When a slot is changed, invalidate others that depend on it."""
        slots_to_reset = []
        if changed_slot == "shop": # from parser
            slots_to_reset = self.SLOT_DEPENDENCIES.get("shop_id", [])
        else:
            slots_to_reset = self.SLOT_DEPENDENCIES.get(changed_slot, [])

        for slot_to_reset in slots_to_reset:
            if hasattr(state.booking_context, slot_to_reset):
                old_value = getattr(state.booking_context, slot_to_reset)
                if old_value is not None:
                    setattr(state.booking_context, slot_to_reset, None)
                    logger.info(f"Invalidated dependent slot '{slot_to_reset}' (was '{old_value}') due to change in '{changed_slot}'.")

    async def _find_first_missing_slot(self, state: "ConversationState", required: list[str]) -> Optional[str]:
        if "course_id" in required and not state.booking_context.course_id and state.booking_context.course_name:
            await self._resolve_course_by_name(state)

        for slot in required:
            if getattr(state.booking_context, slot, None) is None:
                return slot
        return None

    def _get_prompt_and_data(self, state: ConversationState, slot_name: str) -> tuple[str, dict | None]:
        # (This method remains largely the same, but with cleaner data access)
        message = get_prompt(slot_name)
        data: dict[str, Any] = {}
        options_data = None

        if slot_name == "shop_id":
            shops_result = state.recent_tool_results.last_shop_search or {}
            shops = self._get_attr(shops_result, "data", [])
            if shops:
                names = [s.shopName for s in shops]
                message += "\n\nAvailable shops:\n" + "\n".join(f"- {n}" for n in names if n)
                options_data = [s for s in shops]

        if slot_name == "course_id":
            courses_result = state.recent_tool_results.last_course_search or {}
            courses = self._get_attr(courses_result, "data", [])
            if courses:
                names = [self._get_attr(c, 'courseName') for c in courses]
                message += "\n\nAvailable courses:\n" + "\n".join(f"- {n}" for n in names if n)
                options_data = [c for c in courses]

        if options_data:
            data["options"] = options_data
        
        return message, data or None
    
    def _get_attr(self, obj: Any, attr: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    async def _resolve_course_by_name(self, state: ConversationState) -> None:
        # (This method remains largely the same)
        bc = state.booking_context
        if not (bc.course_name and bc.course_id is None and bc.shop_id is not None):
            return

        courses = self._get_attr(state.recent_tool_results.last_course_search, "data", [])
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
            if self._get_attr(course, 'courseName', '').lower() == bc.course_name.lower():
                bc.course_id = self._get_attr(course, 'courseId')
                if bc.duration is None:
                    durations = self._get_attr(course, 'durations', [])
                    if durations:
                        bc.duration = self._get_attr(durations[0], 'duration')
                break
