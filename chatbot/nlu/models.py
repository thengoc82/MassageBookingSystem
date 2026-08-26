# chatbot/nlu/models.py
"""Canonical NLU types. Phase 9 contract.

`NLUResult` is the single structured output the rest of the chatbot
consumes. Everything in `DialoguePolicy` and `SlotFillingManager` is
fed from this — they do not look at the raw user text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Intent(str, Enum):
    # Booking flow.
    CREATE_BOOKING = "create_booking"
    MODIFY_BOOKING = "modify_booking"
    CANCEL_BOOKING = "cancel_booking"
    LOOKUP_BOOKING = "lookup_booking"

    # Search / selection.
    SEARCH_SHOP = "search_shop"
    SELECT_SHOP = "select_shop"
    SEARCH_COURSE = "search_course"
    SELECT_COURSE = "select_course"
    SEARCH_SLOT = "search_slot"
    SELECT_SLOT = "select_slot"
    SEARCH_THERAPIST = "search_therapist"
    SELECT_THERAPIST = "select_therapist"

    # Information delivery.
    PROVIDE_INFORMATION = "provide_information"
    FAQ = "faq"

    # Confirmation / denial / correction.
    CONFIRMATION = "confirmation"
    DENIAL = "denial"
    CORRECTION = "correction"

    # Meta.
    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    GOODBYE = "goodbye"
    RESET = "reset"
    UNKNOWN = "unknown"



class EntityType(str, Enum):
    AREA = "area"
    SHOP_ID = "shop_id"
    SHOP_NAME = "shop_name"
    COURSE = "course"
    COURSE_ID = "course_id"
    ADDON_ID = "addon_id"
    COURSE_NAME = "course_name"
    DURATION = "duration"
    DATE = "date"
    TIME = "time"
    NUMBER_OF_PEOPLE = "number_of_people"
    THERAPIST = "therapist"
    THERAPIST_ID = "therapist_id"
    THERAPIST_NAME = "therapist_name"
    THERAPIST_GENDER = "therapist_gender"
    BOOKING_CODE = "booking_code"
    PHONE_NUMBER = "phone_number"
    MEMBER_ID = "member_id"
    PREFERENCE = "preference"



@dataclass
class Entity:
    type: EntityType
    value: Any
    raw_text: str = ""
    confidence: float = 1.0
    is_correction: bool = False
    span: Optional[tuple[int, int]] = None  # (start_offset, end_offset) of the entity in the raw_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value if hasattr(self.type, 'value') else self.type,
            "value": self.value,
            "raw_text": self.raw_text,
            "confidence": self.confidence,
            "is_correction": self.is_correction,
        }


@dataclass
class Ambiguity:
    """A piece of text matched multiple known items without a clear winner.

    `candidates` is the list of matching item names/IDs (strings)."""
    entity_type: EntityType
    raw_text: str
    candidates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type.value,
            "raw_text": self.raw_text,
            "candidates": list(self.candidates),
        }


@dataclass
class NLUResult:
    intent: Intent
    intent_confidence: float = 1.0
    entities: list[Entity] = field(default_factory=list)
    ambiguities: list[Ambiguity] = field(default_factory=list)
    raw_message: str = ""
    notes: list[str] = field(default_factory=list)

    # Convenience accessors.
    def entity_value(self, entity_type: EntityType) -> Any:
        for e in self.entities:
            if e.type == entity_type and not e.is_correction:
                return e.value
        return None

    def corrected_entity(self, entity_type: EntityType) -> Any:
        for e in self.entities:
            if e.type == entity_type and e.is_correction:
                return e.value
        return None

    def has_correction(self) -> bool:
        return any(e.is_correction for e in self.entities)

    def entity_dict(self) -> dict[str, Any]:
        return {e.type.value: e.value for e in self.entities if not e.is_correction}

    def correction_dict(self) -> dict[str, Any]:
        return {e.type.value: e.value for e in self.entities if e.is_correction}

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.intent_confidence,
            "entities": [e.to_dict() for e in self.entities],
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "notes": list(self.notes),
        }