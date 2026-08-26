# chatbot/nlu/entity_extractor.py
"""Multi-entity extraction from a single user message.

Returns a list of `Entity` objects. The extractor is independent of intent
recognition — it runs regardless of what the user is trying to do.

Things extracted:
    shop, course, duration, date, time, number_of_people, therapist,
    therapist_gender, booking_code, phone_number, member_id, preference.

The extractor also returns ambiguities: a list of `Ambiguity` objects
describing entities whose text matched multiple known items without a clear
winner.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from word2number import w2n


from chatbot.nlu.models import Ambiguity, Entity, EntityType


# ---------------------------------------------------------------------------
# Number-of-people parsing
# ---------------------------------------------------------------------------
_PEOPLE_PHRASES = {
    "just me": 1, "only me": 1, "myself": 1,
    "two of us": 2, "the two of us": 2,
    "three of us": 3, "four of us": 4,
    "a couple": 2,
}


def _parse_word_number(text: str) -> Optional[int]:
    cleaned = re.sub(r"(?:st|nd|rd|th)\b", "", text).strip()
    try:
        # Avoid common false positives.
        if cleaned in {"a", "an", "do", "you"}:
            return None
        return w2n.word_to_num(cleaned)
    except ValueError:
        return None


def _extract_people(text: str, consumed_spans: list[tuple[int, int]]) -> tuple[Optional[int], Optional[str]]:
    lowered = text.lower()
    
    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    if "no one" in lowered or "none" in lowered or "nobody" in lowered:
        return 0, "no one"

    # Direct phrases.
    for phrase, value in _PEOPLE_PHRASES.items():
        for m in re.finditer(rf"\b{phrase}\b", lowered):
            if not is_consumed(m.span()):
                return value, phrase

    # "2 people" / "two people" / "2 pax" / "2 persons" / "for two".
    m = re.search(
        r"(?:for\s+)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\s+(people|persons?|pax|guests?|of\s+us)",
        lowered,
    )
    if m and not is_consumed(m.span()):
        num_str = m.group(1)
        try:
            num = int(num_str)
        except ValueError:
            num = _parse_word_number(num_str)
        if num is not None and 1 <= num <= 20:
            return num, m.group(0)

    return None, None


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------
def _extract_duration(text: str, consumed_spans: list[tuple[int, int]]) -> tuple[Optional[int], Optional[str]]:
    """Returns (minutes, raw_text) or (None, None)."""
    lowered = text.lower()
    
    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    # "60 minutes" / "60 min" / "60m".
    m = re.search(r"\b(\d+)\s*(?:minutes?|mins?|m)\b", lowered)
    if m and not is_consumed(m.span()):
        return int(m.group(1)), m.group(0)
        
    # "60 minutes" word-style.
    m = re.search(
        r"\b((?:one|two|three|four|five|six|seven|eight|nine|ten|"
        r"fifteen|twenty|thirty|forty|fifty|sixty|ninety|hundred|"
        r"one\s+hundred\s+twenty|one\s+hundred\s+eighty|one\s+hundred\s+fifty))\s+minutes?\b",
        lowered,
    )
    if m and not is_consumed(m.span()):
        try:
            return w2n.word_to_num(m.group(1)), m.group(0)
        except ValueError:
            pass
            
    # "an hour" / "one hour" / "1 hour" / "half hour".
    m = re.search(r"\b(?:an|one|1)\s+hour\b", lowered)
    if m and not is_consumed(m.span()):
        return 60, m.group(0)
        
    if "half hour" in lowered and not is_consumed(lowered.find("half hour")):
        return 30, "half hour"
    if "half an hour" in lowered and not is_consumed(lowered.find("half an hour")):
        return 30, "half an hour"
        
    if "hour" in lowered:
        m = re.search(r"\b(\d+)\s+hours?\b", lowered)
        if m and not is_consumed(m.span()):
            return int(m.group(1)) * 60, m.group(0)
            
    return None, None


# ---------------------------------------------------------------------------
# Phone & booking code
# ---------------------------------------------------------------------------
def _extract_phone(text: str, consumed_spans: list[tuple[int, int]]) -> tuple[Optional[str], Optional[tuple[int, int]]]:
    # This regex is a bit more specific to avoid false positives on date-like numbers.
    # It looks for sequences that are more likely to be phone numbers.
    patterns = [
        r"\b0\d{9,10}\b", # Common local format (10-11 digits starting with 0)
    ]

    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    for pattern in patterns:
        for m in re.finditer(pattern, text):
            if not is_consumed(m.span()):
                digits = "".join(filter(str.isdigit, m.group(0)))
                # Basic length check to filter out unlikely numbers
                if 10 <= len(digits) <= 13:
                    return digits, m.span()
    return None, None


def _extract_booking_code(text: str) -> Optional[str]:
    m = re.search(r"\bBK\d{8,}\b", text.upper())
    return m.group(0) if m else None


def _extract_member_id(text: str) -> Optional[str]:
    m = re.search(r"\b(?:M|m)ember\s*(?:id|number|#)?\s*[:=#]?\s*([A-Z0-9-]{4,})\b", text)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Therapist gender
# ---------------------------------------------------------------------------
_GENDER_TOKENS = {
    "female": "female", "woman": "female", "women": "female", "lady": "female", "ladies": "female",
    "male": "male", "man": "male", "men": "male", "gentleman": "male", "guy": "male",
    "non-binary": "non-binary", "nonbinary": "non-binary", "nb": "non-binary",
}


def _extract_gender(text: str) -> tuple[Optional[str], Optional[str]]:
    lowered = text.lower()
    for tok, value in _GENDER_TOKENS.items():
        if re.search(rf"\b{re.escape(tok)}\b", lowered):
            return value, tok
    return None, None


# ---------------------------------------------------------------------------
# Shop / course / therapist name (passed to ambiguity detector)
# ---------------------------------------------------------------------------
def _extract_text_token(text: str) -> Optional[str]:
    """Strip filler, return the salient noun-like word. The full NLU
    passes a hint of what noun to look for. This stub just returns the
    original text — strategy for synonym resolution lives in the
    classifier."""
    return text.strip() or None


# ---------------------------------------------------------------------------
# Correction detection
# ---------------------------------------------------------------------------
_CORRECTION_MARKERS = (
    "actually", "instead", "no,", "no ", "change to", "make it",
    "update to", "switch to", "rather", "prefer", "no wait",
)


def detect_correction(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _CORRECTION_MARKERS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class EntityExtractor:
    """Extract entities from a single message, independent of intent."""

    def __init__(
        self,
        known_shops: Optional[Iterable[dict]] = None,
        known_courses: Optional[Iterable[dict]] = None,
        known_therapists: Optional[Iterable[dict]] = None,
    ) -> None:
        self._known_shops = list(known_shops or [])
        self._known_courses = list(known_courses or [])
        self._known_therapists = list(known_therapists or [])

    def set_known_items(
        self,
        shops: Optional[Iterable[dict]] = None,
        courses: Optional[Iterable[dict]] = None,
        therapists: Optional[Iterable[dict]] = None,
    ) -> None:
        if shops is not None:
            self._known_shops = list(shops)
        if courses is not None:
            self._known_courses = list(courses)
        if therapists is not None:
            self._known_therapists = list(therapists)

    def extract(
        self,
        text: str,
        is_correction: bool = False,
        focused_slot: Optional[str] = None,
        allowed_types: Optional[set[EntityType]] = None,
    ) -> list[Entity]:
        from chatbot.nlu.date_parser import parse_date
        from chatbot.nlu.time_parser import parse_time

        entities: list[Entity] = []
        
        def maybe_add(entity: Optional[Entity]) -> None:
            if entity is None:
                return
            if allowed_types is not None and entity.type not in allowed_types:
                return
            # Avoid adding duplicate entity types, except for courses
            if any(e.type == entity.type for e in entities) and entity.type != EntityType.COURSE_ID:
                return
            entity.is_correction = is_correction
            entities.append(entity)

        current_text_for_parsing = text.lower()
        
        # This will hold spans of text that have already been claimed by an entity
        consumed_spans = []

        def mark_consumed(span: tuple[int, int]):
            if span:
                consumed_spans.append(span)

        # Helper to create an entity and mark its text as consumed
        def create_entity(ent_type, value, raw_text, confidence, span):
            entity = Entity(type=ent_type, value=value, raw_text=raw_text, confidence=confidence, span=span)
            mark_consumed(span)
            return entity

        # --- Extraction Functions ---
        
        # Each extractor function will now return a tuple (value, raw_text, span)
        
        def extract_booking_code_entity(t):
            raw = _extract_booking_code(t)
            if raw:
                m = re.search(re.escape(raw), t, re.IGNORECASE)
                return raw, raw, m.span() if m else None
            return None, None, None

        def extract_phone_entity(t):
            raw, span = _extract_phone(t, consumed_spans)
            if raw and span:
                return raw, raw, span
            return None, None, None
            
        def extract_member_id_entity(t):
            raw = _extract_member_id(t)
            if raw:
                # This is tricky because the regex has groups. We need the full match span.
                m = re.search(r"\b(?:M|m)ember\s*(?:id|number|#)?\s*[:=#]?\s*([A-Z0-9-]{4,})\b", t)
                if m:
                    return m.group(1), m.group(0), m.span()
            return None, None, None

        def extract_date_entity(t):
            from chatbot.nlu.date_parser import parse_date
            value, raw_text = parse_date(t, consumed_spans)
            if value and raw_text:
                try:
                    start_index = t.lower().find(raw_text.lower())
                    if start_index != -1:
                        span = (start_index, start_index + len(raw_text))
                        if not any(s < span[1] and e > span[0] for s, e in consumed_spans):
                            return value, raw_text, span
                except Exception as e:
                    print(f"Error finding span for date entity: {e}")
            return None, None, None

        def extract_time_entity(t):
            from chatbot.nlu.time_parser import parse_time
            value, raw_text, span = parse_time(t, consumed_spans)
            if value and raw_text and span:
                if not any(s < span[1] and e > span[0] for s, e in consumed_spans):
                    return value, raw_text, span
            return None, None, None

        def extract_duration_entity(t):
            value, raw_text = _extract_duration(t, consumed_spans)
            if value and raw_text:
                m = re.search(re.escape(raw_text), t, re.IGNORECASE)
                if m and not any(s < m.span()[1] and e > m.span()[0] for s, e in consumed_spans):
                    return value, raw_text, m.span()
            return None, None, None
            
        def extract_people_entity(t):
            value, raw_text = _extract_people(t, consumed_spans)
            if value is not None and raw_text:
                m = re.search(re.escape(raw_text), t, re.IGNORECASE)
                if m and not any(s < m.span()[1] and e > m.span()[0] for s, e in consumed_spans):
                    return value, raw_text, m.span()
            return None, None, None

        def extract_named_entity_wrapper(label, known_items):
            # This now gets the consumed spans directly from the outer scope
            matches = _extract_named_entity(text, label, known_items, consumed_spans)
            return matches

        # Mapping from slot names to entity types and their extractors
        EXTRACTOR_MAP = {
            "booking_code": (EntityType.BOOKING_CODE, extract_booking_code_entity),
            "date": (EntityType.DATE, extract_date_entity),
            "phone_number": (EntityType.PHONE_NUMBER, extract_phone_entity),
            "member_id": (EntityType.MEMBER_ID, extract_member_id_entity),
            "start_time": (EntityType.TIME, extract_time_entity),
            "duration": (EntityType.DURATION, extract_duration_entity),
            "number_of_people": (EntityType.NUMBER_OF_PEOPLE, extract_people_entity),
            "shop_id": (EntityType.SHOP_ID, lambda t: extract_named_entity_wrapper("shop", self._known_shops)),
            "course_id": (EntityType.COURSE_ID, lambda t: extract_named_entity_wrapper("course", self._known_courses)),
            "therapist_id": (EntityType.THERAPIST_ID, lambda t: extract_named_entity_wrapper("therapist", self._known_therapists)),
        }

        # If there's a focused slot, run its extractor first
        if focused_slot and focused_slot in EXTRACTOR_MAP:
            ent_type, extractor = EXTRACTOR_MAP[focused_slot]
            if ent_type in [EntityType.COURSE_ID, EntityType.SHOP_ID, EntityType.THERAPIST_ID]:
                matches = extractor(current_text_for_parsing)
                for value, raw_text, span in matches:
                    if value is not None and raw_text is not None:
                        entity = create_entity(ent_type, value, raw_text, 0.98, span)
                        maybe_add(entity)
            else:
                value, raw_text, span = extractor(current_text_for_parsing)
                if value is not None and raw_text is not None:
                    entity = create_entity(ent_type, value, raw_text, 0.98, span)
                    maybe_add(entity)

        # Run all other extractors
        for slot_name, (ent_type, extractor) in EXTRACTOR_MAP.items():
            if any(e.type == ent_type for e in entities) and ent_type not in [EntityType.COURSE_ID, EntityType.ADDON_ID]:
                continue
            
            if ent_type in [EntityType.COURSE_ID, EntityType.SHOP_ID, EntityType.THERAPIST_ID]:
                matches = extractor(current_text_for_parsing)
                for value, raw_text, span in matches:
                    if value is not None and raw_text is not None:
                        entity = create_entity(ent_type, value, raw_text, 0.9, span)
                        maybe_add(entity)
            else:
                extractor_result = extractor(current_text_for_parsing)
                if extractor_result is not None:
                    value, raw_text, span = extractor_result
                    if value is not None and raw_text is not None:
                        entity = create_entity(ent_type, value, raw_text, 0.9, span)
                        maybe_add(entity)
        
        # Gender is special, as it's a preference
        gender, gender_raw_text = _extract_gender(current_text_for_parsing)
        if gender and gender_raw_text:
            m = re.search(re.escape(gender_raw_text), current_text_for_parsing, re.IGNORECASE)
            span = m.span() if m else None
            if not any(s < (span[1] if span else -1) and e > (span[0] if span else -1) for s, e in consumed_spans):
                 entity = create_entity(EntityType.THERAPIST_GENDER, gender, gender_raw_text, 0.9, span)
                 maybe_add(entity)
        return entities


def _is_booking_code_already(entities: list[Entity]) -> bool:
    return any(e.type == EntityType.BOOKING_CODE for e in entities)


def _extract_named_entity(
    text: str,
    entity_label: str,
    known_items: list[dict],
    consumed_text_spans: list[tuple[int, int]],
) -> list[tuple[Optional[Any], Optional[str], Optional[tuple[int, int]]]]:
    """Find all known entities (shop, course, therapist) in the text.
    Avoids consumed text spans.
    Returns a list of (value, raw_text_matched, span) tuples.
    """
    lowered_text = text.lower()
    matches = []
    
    for item in known_items:
        # Correctly get attributes from a dict or object
        name = ""
        aliases = []
        if isinstance(item, dict):
            if entity_label == "shop":
                name = item.get("shopName", "")
            elif entity_label == "course":
                name = item.get("courseName", "")
            elif entity_label == "therapist":
                name = item.get("name", "")
            aliases = item.get("aliases", [])
        else: # It's an object
            if entity_label == "shop":
                name = getattr(item, "shopName", "")
            elif entity_label == "course":
                name = getattr(item, "courseName", "")
            elif entity_label == "therapist":
                name = getattr(item, "name", "")
            aliases = getattr(item, "aliases", [])

        names_to_check = [name] + aliases
        if name:
             names_to_check.append(name.replace(" Store", ""))
             names_to_check.append(name.replace(" store", ""))

        names_to_check = list(dict.fromkeys(filter(None, names_to_check)))

        for alias in names_to_check:
            pattern = re.compile(rf"\b{re.escape(alias.lower())}\b")
            for m in pattern.finditer(lowered_text):
                start, end = m.span()
                # Check for overlap with consumed spans.
                if any((s < end and e > start) for s, e in consumed_text_spans):
                    continue # Overlaps, skip.

                value = None
                if isinstance(item, dict):
                    if entity_label == "shop":
                        value = {"shopId": item.get("shopId"), "shopName": item.get("shopName")}
                    elif entity_label == "course":
                        value = {"courseId": item.get("courseId"), "courseType": item.get("courseType")}
                    elif entity_label == "therapist":
                        value = item.get("therapistId")
                    else:
                        value = item.get("id")
                else: # It's an object
                    if entity_label == "shop":
                        value = {"shopId": getattr(item, "shopId", None), "shopName": getattr(item, "shopName", None)}
                    elif entity_label == "course":
                        value = {"courseId": getattr(item, "courseId", None), "courseType": getattr(item, "courseType", None)}
                    elif entity_label == "therapist":
                        value = getattr(item, "therapistId", None)
                    else:
                        value = getattr(item, "id", None)
                
                if value:
                    matches.append((value, text[start:end], (start, end)))

    return matches