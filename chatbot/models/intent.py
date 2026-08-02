# chatbot/models/intent.py
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    GREETING = "greeting"
    GOODBYE = "goodbye"
    HELP = "help"
    BOOK_MASSAGE = "book_massage"
    SEARCH_SHOPS = "search_shops"
    SEARCH_COURSES = "search_courses"
    SEARCH_SLOTS = "search_slots"
    LOOKUP_BOOKING = "lookup_booking"
    CANCEL_BOOKING = "cancel_booking"
    MODIFY_BOOKING = "modify_booking"
    CHECK_ELIGIBILITY = "check_eligibility"
    FAQ = "faq"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    intent: IntentType
    slots: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0
    response: str | None = None
