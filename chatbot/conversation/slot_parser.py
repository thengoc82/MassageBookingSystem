import logging
import re
from typing import Any, List, Optional

from chatbot.conversation.reference_parser import parse_relative_date, resolve_by_ordinal, resolve_by_index
from chatbot.nlu.models import NLUResult
from chatbot.models import ShopInfo
from chatbot.conversation.parser_result import ParseResult, ParsedSlot

logger = logging.getLogger(__name__)

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
    # Prioritize exact matches
    for shop in shops:
        shop_name = _get_attr(shop, 'shopName')
        if shop_name and text_lower == shop_name.lower():
            return shop
    # Fallback to partial matches
    for shop in shops:
        shop_name = _get_attr(shop, 'shopName')
        if shop_name and text_lower in shop_name.lower():
            return shop
    return None

def parse_course(text: str, courses: List[Any]) -> Optional[Any]:
    text_lower = text.lower()
    # Prioritize exact matches
    for course in courses:
        course_name = _get_attr(course, 'courseName')
        if course_name and course_name.lower() == text_lower:
            return course
    # Fallback to partial matches
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

def _handle_ordinal_selection(message: str, recent_tool_results: Any) -> Optional[ParsedSlot]:
    last_options = []
    target_slot = None
    source = "ordinal"

    if recent_tool_results.last_shop_search and (options := get_options_from_result(recent_tool_results.last_shop_search)):
        last_options = options
        target_slot = "shop"
    elif recent_tool_results.last_course_search and (options := get_options_from_result(recent_tool_results.last_course_search)):
        last_options = options
        target_slot = "course"
    elif recent_tool_results.last_slot_search and (options := get_options_from_result(recent_tool_results.last_slot_search)):
        last_options = options
        target_slot = "start_time"

    if not last_options or not target_slot:
        return None

    for resolver in (resolve_by_ordinal, resolve_by_index):
        matched, idx = resolver(message, last_options)
        if matched:
            selected_item = last_options[idx]
            if target_slot == "shop":
                return ParsedSlot(name="shop", value=selected_item, source=source)
            elif target_slot == "course":
                return ParsedSlot(name="course", value=selected_item, source=source)
            elif target_slot == "start_time":
                return ParsedSlot(name="start_time", value=_get_attr(selected_item, 'startTime'), source=source)
    return None

async def parse_message(
    message: str,
    nlu: "NLU",
    recent_tool_results: Any,
    focused_slot: Optional[str] = None,
    nlu_result: Optional["NLUResult"] = None,
    base_date: Optional[str] = None
) -> ParseResult:
    result = ParseResult()

    # 1. Ordinal/Index-based parsing (highest priority)
    if ordinal_result := _handle_ordinal_selection(message, recent_tool_results):
        result.add_slot(ordinal_result.name, ordinal_result.value, ordinal_result.source)
        # If we found an ordinal match, we can often stop here as it's a very specific intent.
        return result

    # 2. Focused, simple parsers
    if focused_slot:
        val = None
        if focused_slot == "number_of_people":
            val = parse_number_of_people(message)
        elif focused_slot == "date":
            val = parse_date(message, base_date_str=base_date)
        elif focused_slot == "phone_number":
            val = parse_phone_number(message)
        
        if val is not None:
            result.add_slot(focused_slot, val, "focused_regex")

    # 3. General NLU entity parsing
    local_nlu_result = nlu_result or (await nlu.understand(message) if message.strip() else None)
    if not (local_nlu_result and hasattr(local_nlu_result, 'entities')):
        return result

    sorted_entities = sorted(local_nlu_result.entities, key=lambda e: e.is_correction, reverse=True)
    
    for entity in sorted_entities:
        slot_name = entity.type.value if hasattr(entity.type, 'value') else entity.type
        value = entity.value

        parsed_value: Any = None
        source = "nlu"

        if slot_name == "number_of_people":
            try:
                parsed_value = int(value)
            except (ValueError, TypeError):
                continue
        elif slot_name == "date":
            parsed_value = parse_date(str(value), base_date_str=base_date if entity.is_correction else None)
        elif slot_name == "phone_number":
            parsed_value = parse_phone_number(str(value))
        elif slot_name in ["shop_name", "shop_id"]:
            if shops := get_options_from_result(recent_tool_results.last_shop_search):
                if selected_shop := parse_shop(str(value), shops):
                    parsed_value = selected_shop
                    slot_name = "shop" # Normalize to 'shop'
        elif slot_name == "area":
            parsed_value = str(value)
        elif slot_name in ["course_name", "course_id"]:
            if courses := get_options_from_result(recent_tool_results.last_course_search):
                if selected_course := parse_course(str(value), courses):
                    parsed_value = selected_course
                    slot_name = "course" # Normalize to 'course'

        if parsed_value is not None:
            result.add_slot(slot_name, parsed_value, source, confidence=0.9 if entity.is_correction else 0.7)

    return result


