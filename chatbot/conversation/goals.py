# chatbot/conversation/goals.py
"""High-level conversation goals. The dialogue policy uses these to decide
which flow to drive (book, cancel, modify, lookup, FAQ, browse).
"""
from __future__ import annotations

from enum import Enum


class Goal(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    MODIFY_BOOKING = "modify_booking"
    CANCEL_BOOKING = "cancel_booking"
    LOOKUP_BOOKING = "lookup_booking"
    ASK_FAQ = "ask_faq"
    BROWSE_SHOPS = "browse_shops"
    BROWSE_COURSES = "browse_courses"
    BROWSE_THERAPISTS = "browse_therapists"
    NONE = "none"