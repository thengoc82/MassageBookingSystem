# chatbot/conversation/multi_entity_parser.py
# This file is deprecated. Its functionality is replaced by the NLU module.

# from typing import Any, Callable, Dict, List, Optional
# import re
# from datetime import datetime, timedelta
# from word2number import w2n

# from chatbot.conversation.state import ConversationState
# from chatbot.conversation.reference_parser import (
#     resolve_by_index,
#     resolve_by_ordinal,
#     resolve_by_name,
# )

# # Type alias for a parser function
# EntityParser = Callable[[str, ConversationState], Optional[Any]]


# class MultiEntityParser:
#     """
#     Parses multiple entities from a single user message.
#     """

#     def __init__(self) -> None:
#         self.parsers: Dict[str, EntityParser] = {
#             "date": self._parse_date,
#             "number_of_people": self._parse_number_of_people,
#             "start_time": self._parse_time,
#             "phone_number": self._parse_phone_number,
#             "shop_id": self._parse_shop,
#             "course_id": self._parse_course,
#             "therapist_id": self._parse_therapist,
#         }

#     def parse(self, message: str, state: ConversationState, corrected_fields: List[str]) -> Dict[str, Any]:
#         """
#         Parse all supported entities from a message.
#         Do not re-parse fields that have just been corrected.
#         """
#         extracted_entities = {}
#         for slot_name, parser_func in self.parsers.items():
#             if slot_name in corrected_fields:
#                 continue

#             value = parser_func(message, state)
#             if value is not None:
#                 extracted_entities[slot_name] = value
#         return extracted_entities

#     def _parse_date(self, text: str, state: ConversationState) -> Optional[str]:
#         text = text.lower().strip()
#         today = datetime.now().date()

#         if "tomorrow" in text:
#             return (today + timedelta(days=1)).isoformat()
#         if "today" in text:
#             return today.isoformat()

#         weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
#         for i, day_name in enumerate(weekdays):
#             if day_name in text:
#                 days_ahead = (i - today.weekday() + 7) % 7
#                 if days_ahead == 0:
#                     days_ahead = 7
#                 return (today + timedelta(days=days_ahead)).isoformat()
        
#         match = re.search(r"\d{4}-\d{2}-\d{2}", text)
#         if match:
#             dt = datetime.strptime(match.group(0), "%Y-%m-%d").date()
#             if dt >= today:
#                 return dt.isoformat()

#         return None

#     def _parse_number_of_people(self, text: str, state: ConversationState) -> Optional[int]:
#         text = text.lower().strip()
#         try:
#             num = w2n.word_to_num(text)
#             if 1 <= num <= 10:
#                 return num
#         except ValueError:
#             pass

#         match = re.search(r"(\d+)\s*(people|person|pax)", text)
#         if match:
#             num = int(match.group(1))
#             if 1 <= num <= 10:
#                 return num
#         return None

#     def _parse_time(self, text: str, state: ConversationState) -> Optional[str]:
#         text = text.lower().strip()
#         formats = ["%H:%M", "%I:%M%p", "%I%p"]
#         for fmt in formats:
#             try:
#                 dt = datetime.strptime(text, fmt)
#                 return dt.strftime("%H:%M")
#             except ValueError:
#                 continue
#         return None

#     def _parse_phone_number(self, text: str, state: ConversationState) -> Optional[str]:
#         match = re.search(r"\+?\d[\d\s-]{7,}", text)
#         if match:
#             return "".join(filter(str.isdigit, match.group(0)))
#         return None
    
#     def _to_dicts(self, items: List[Any]) -> List[Dict[str, Any]]:
#         result = []
#         for it in items:
#             if isinstance(it, dict):
#                 result.append(it)
#             elif hasattr(it, "model_dump"):
#                 result.append(it.model_dump())
#         return result

#     def _parse_shop(self, text: str, state: ConversationState) -> Optional[Any]:
#         shops = (state.recent_tool_results.last_shop_search or {}).get("data")
#         if not shops:
#             return None
        
#         dicts = self._to_dicts(shops)
#         matched, idx = self._resolve_item(text, dicts, ("shopName",))
#         if matched:
#             return shops[idx]
#         return None

#     def _parse_course(self, text: str, state: ConversationState) -> Optional[Any]:
#         courses = (state.last_tool_result or {}).get("data")
#         if not courses or not (isinstance(courses[0], dict) and "courseName" in courses[0]):
#              return None

#         dicts = self._to_dicts(courses)
#         matched, idx = self._resolve_item(text, dicts, ("courseName",))
#         if matched:
#             return courses[idx]
#         return None

#     def _parse_therapist(self, text: str, state: ConversationState) -> Optional[Any]:
#         therapists = (state.recent_tool_results.last_therapist_search or {}).get("data")
#         if not therapists:
#             return None
        
#         dicts = self._to_dicts(therapists)
#         matched, idx = self._resolve_item(text, dicts, ("name",))
#         if matched:
#             return therapists[idx]
#         return None

#     def _resolve_item(self, text: str, items: List[Dict[str, Any]], name_keys: tuple[str, ...]) -> tuple[bool, int]:
#         """Wrapper for different resolution strategies."""
#         strategies = [
#             (resolve_by_index, (text, items)),
#             (resolve_by_ordinal, (text, items)),
#             (resolve_by_name, (text, items, name_keys)),
#         ]
#         for strategy, args in strategies:
#             matched, idx = strategy(*args)
#             if matched:
#                 return True, idx
#         return False, -1
