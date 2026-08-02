# chatbot/nlu/synonym_resolver.py
"""Synonym → canonical mapping. Keeps dialogue policy and slot filling
decoupled from how the user phrases things.
"""
from __future__ import annotations

from typing import Iterable


# action synonyms → intent name
ACTION_SYNONYMS: dict[str, str] = {
    # create_booking
    "book": "create_booking",
    "booking": "create_booking",
    "reserve": "create_booking",
    "reservation": "create_booking",
    "schedule": "create_booking",
    "appointment": "create_booking",
    "appointments": "create_booking",
    "massage": "create_booking",
    "massages": "create_booking",
    "treatment": "create_booking",
    "treatments": "create_booking",
    "service": "create_booking",
    "services": "create_booking",
    "session": "create_booking",
    "sessions": "create_booking",
    # confirm
    "confirm": "confirmation",
    "yes": "confirmation",
    "yep": "confirmation",
    "yup": "confirmation",
    "yeah": "confirmation",
    "ok": "confirmation",
    "okay": "confirmation",
    "sure": "confirmation",
    "go": "confirmation",
    "do it": "confirmation",
    "go ahead": "confirmation",
    # deny
    "no": "denial",
    "nope": "denial",
    "nah": "denial",
    "cancel": "denial",
    "stop": "denial",
    "don't": "denial",
    "dont": "denial",
    # reset
    "reset": "reset",
    "restart": "reset",
    "start over": "reset",
    "begin again": "reset",
    # goodbye
    "bye": "goodbye",
    "goodbye": "goodbye",
    "see you": "goodbye",
    "thanks": "goodbye",
    "thank you": "goodbye",
    # greeting
    "hi": "greeting",
    "hello": "greeting",
    "hey": "greeting",
    "good morning": "greeting",
    "good afternoon": "greeting",
    "good evening": "greeting",
    # modify
    "modify": "modify_booking",
    "change": "modify_booking",
    "update": "modify_booking",
    "reschedule": "modify_booking",
    "move": "modify_booking",
    # cancel booking
    "cancel my booking": "cancel_booking",
    "cancel booking": "cancel_booking",
    "cancel reservation": "cancel_booking",
    "cancel my reservation": "cancel_booking",
    # lookup
    "lookup": "lookup_booking",
    "find my booking": "lookup_booking",
    "check my booking": "lookup_booking",
    "view my booking": "lookup_booking",
    "my bookings": "lookup_booking",
    "my reservation": "lookup_booking",
    "my reservations": "lookup_booking",
}


# Entity label synonyms (used by the entity extractor for type detection).
SHOP_SYNONYMS = {"shop", "shops", "branch", "branches", "location", "store", "stores", "place", "venue"}
COURSE_SYNONYMS = {"course", "courses", "massage", "treatment", "service", "package", "type"}
THERAPIST_SYNONYMS = {"therapist", "therapists", "staff", "person", "employee"}
DURATION_SYNONYMS = {"duration", "long", "length", "time", "session"}
DATE_SYNONYMS = {"date", "day", "when"}
TIME_SYNONYMS = {"time", "hour", "o'clock", "oclock", "schedule"}


def synonym_for_shop(word: str) -> bool:
    return word.lower() in SHOP_SYNONYMS


def synonym_for_course(word: str) -> bool:
    return word.lower() in COURSE_SYNONYMS


def synonym_for_therapist(word: str) -> bool:
    return word.lower() in THERAPIST_SYNONYMS


def synonym_for_duration(word: str) -> bool:
    return word.lower() in DURATION_SYNONYMS


def synonym_for_date(word: str) -> bool:
    return word.lower() in DATE_SYNONYMS


def synonym_for_time(word: str) -> bool:
    return word.lower() in TIME_SYNONYMS


def normalize_action_token(token: str) -> str | None:
    """Return the mapped intent name for a token, or None."""
    return ACTION_SYNONYMS.get(token.lower())


def iter_action_synonyms() -> Iterable[tuple[str, str]]:
    """Iterate over (synonym, canonical_intent) pairs."""
    return ACTION_SYNONYMS.items()