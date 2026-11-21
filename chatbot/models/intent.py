from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    UNKNOWN = "unknown"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    HELP = "help"
    BOOK_MASSAGE = "book_massage"
    SEARCH_SHOPS = "search_shops"
    SEARCH_COURSES = "search_courses"
    SEARCH_SLOTS = "search_slots"
    CHECK_ELIGIBILITY = "check_eligibility"
    LOOKUP_BOOKING = "lookup_booking"
    CANCEL_BOOKING = "cancel_booking"
    MODIFY_BOOKING = "modify_booking"
    FAQ = "faq"


class Intent(BaseModel):
    intent: IntentType
    slots: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
