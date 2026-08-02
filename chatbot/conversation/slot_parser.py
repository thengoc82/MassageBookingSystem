from typing import Any, List, Optional
import re
from chatbot.conversation.state import ConversationState
from chatbot.conversation.reference_parser import resolve_by_ordinal, resolve_by_index, parse_relative_date

def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get an attribute from an object or a key from a dictionary."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)

def parse_date(text: str, base_date_str: str | None = None) -> Optional[str]:
    # Try parsing relative dates first, as they are more specific
    relative_date = parse_relative_date(text, base_date_str=base_date_str)
    if relative_date:
        return relative_date
    
    # Fallback to regex for absolute dates
    match = re.search(r'\b(202\d-\d{1,2}-\d{1,2})\b', text)
    if match:
        return match.group(1)
        
    return None

def parse_phone_number(text: str) -> Optional[str]:
    match = re.search(r'\+?\d[\d\s-]{8,}\d', text)
    if match:
        return match.group(0)
    return None

def parse_number_of_people(text: str) -> Optional[int]:
    import re
    text = text.strip()
    if text.isdigit():
        return int(text)
    match = re.search(r'\b(\d+)\s*(people|person|pax)\b', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def parse_shop(text: str, shops: List[Any]) -> Optional[Any]:
    text_lower = text.lower()
    for shop in shops:
        shop_name = _get_attr(shop, 'shopName')
        if shop_name and text_lower in shop_name.lower():
            return shop
    return None

def parse_course(text: str, courses: List[Any]) -> Optional[Any]:
    text_lower = text.lower()
    for course in courses:
        course_name = _get_attr(course, 'courseName')
        if course_name and course_name.lower() in text_lower:
            return course
    return None

def get_options_from_result(result):
    if isinstance(result, dict):
        return result.get("data")
    elif isinstance(result, list):
        return result
    return None

async def _handle_ordinal_selection(message: str, state: "ConversationState") -> bool:
    last_options = []
    target_slot = None

    if state.recent_tool_results.last_shop_search and (options := get_options_from_result(state.recent_tool_results.last_shop_search)):
        last_options = options
        target_slot = "shop_id"
    elif state.recent_tool_results.last_course_search and (options := get_options_from_result(state.recent_tool_results.last_course_search)):
        last_options = options
        target_slot = "course_id"
    elif state.recent_tool_results.last_slot_search and (options := get_options_from_result(state.recent_tool_results.last_slot_search)):
        last_options = options
        target_slot = "start_time"

    if not last_options or not target_slot:
        return False

    for resolver in (resolve_by_ordinal, resolve_by_index):
        matched, idx = resolver(message, last_options)
        if matched:
            selected_item = last_options[idx]
            if target_slot == "shop_id":
                state.booking_context.shop_id = _get_attr(selected_item, 'shopId')
                state.booking_context.shop_name = _get_attr(selected_item, 'shopName')
                return True
            elif target_slot == "course_id":
                state.booking_context.course_id = _get_attr(selected_item, 'courseId')
                state.booking_context.course_name = _get_attr(selected_item, 'courseName')
                if state.booking_context.duration is None:
                    durations = _get_attr(selected_item, 'durations', [])
                    if durations:
                        state.booking_context.duration = _get_attr(durations[0], 'duration')
                return True
            elif target_slot == "start_time":
                state.booking_context.start_time = _get_attr(selected_item, 'startTime')
                return True
    return False

async def parse_and_fill_slots(
    message: str,
    state: "ConversationState",
    nlu: "NLU",
    conversation_manager: "ConversationManager",
    focused_slot: Optional[str] = None,
    nlu_result: Optional["NLUResult"] = None,
) -> bool:
    filled_any = False

    if await _handle_ordinal_selection(message, state):
        return True

    local_nlu_result = nlu_result or (await nlu.understand(message) if message.strip() else None)

    # First, try to fill the focused slot directly from the message if no entities are found for it
    if focused_slot:
        entity_for_focused_slot_exists = False
        if local_nlu_result and hasattr(local_nlu_result, 'entities'):
            for e in local_nlu_result.entities:
                try:
                    # Attempt to access e.type.value, but fall back to e.type if it's just a string
                    entity_type_str = e.type.value if hasattr(e.type, 'value') else e.type
                    if entity_type_str == focused_slot:
                        entity_for_focused_slot_exists = True
                        break
                except AttributeError:
                    # This handles cases where e.type might not be what we expect
                    continue
        
        if not entity_for_focused_slot_exists:
            if focused_slot == "number_of_people":
                if num_people := parse_number_of_people(message):
                    state.booking_context.number_of_people = num_people
                    filled_any = True
            elif focused_slot == "date":
                if date := parse_date(message):
                    state.booking_context.date = date
                    filled_any = True
            elif focused_slot == "phone_number":
                if phone := parse_phone_number(message):
                    state.booking_context.phone_number = phone
                    filled_any = True

    if local_nlu_result and hasattr(local_nlu_result, 'entities'):
        sorted_entities = sorted(local_nlu_result.entities, key=lambda e: e.is_correction, reverse=True)
        
        for entity in sorted_entities:
            slot_name = entity.type.value if not isinstance(entity.type, str) else entity.type
            value = entity.value

            # Skip filling if the slot is already filled and the entity is not a correction
            if not entity.is_correction and getattr(state.booking_context, slot_name, None) is not None:
                continue

            if slot_name == "number_of_people":
                try:
                    num_people = int(value)
                    state.booking_context.number_of_people = num_people
                    filled_any = True
                except (ValueError, TypeError):
                    pass
            elif slot_name == "date":
                base_date = state.booking_context.date if entity.is_correction and state.booking_context.date else None
                parsed_date = parse_date(str(value), base_date_str=base_date)
                if parsed_date:
                    state.booking_context.date = parsed_date
                    filled_any = True
                print(f"date: {state.booking_context.date}")
            elif slot_name == "phone_number":
                if phone := parse_phone_number(str(value)):
                    state.booking_context.phone_number = phone
                    filled_any = True
            elif slot_name in ["shop_name", "shop_id"]:
                if shops := get_options_from_result(state.recent_tool_results.last_shop_search):
                    if selected_shop := parse_shop(str(value), shops):
                        state.booking_context.shop_id = _get_attr(selected_shop, 'shopId')
                        state.booking_context.shop_name = _get_attr(selected_shop, 'shopName')
                        filled_any = True
            elif slot_name in ["course_name", "course_id"]:
                 if courses := get_options_from_result(state.recent_tool_results.last_course_search):
                    if selected_course := parse_course(str(value), courses):
                        state.booking_context.course_id = _get_attr(selected_course, 'courseId')
                        state.booking_context.course_name = _get_attr(selected_course, 'courseName')
                        if not state.booking_context.duration:
                            durations = _get_attr(selected_course, 'durations', [])
                            if durations:
                                state.booking_context.duration = _get_attr(durations[0], 'duration')
                        filled_any = True

    return filled_any
