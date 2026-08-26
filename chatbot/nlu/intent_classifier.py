# chatbot/nlu/intent_classifier.py
"""Intent classification. Combines multiple signals:

    - phrase patterns (matched with priority)
    - synonym resolution
    - contextual signals (e.g. "reset" anywhere → reset)
    - negation / denial patterns
    - correction markers

The classifier never relies on a single keyword.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from chatbot.nlu.models import Intent
from chatbot.nlu.synonym_resolver import (
    ACTION_SYNONYMS,
    iter_action_synonyms,
)


@dataclass
class _Signal:
    intent: Intent
    weight: float
    reason: str


_PHRASE_PATTERNS: list[tuple[re.Pattern[str], Intent, float]] = [
    # Confirmations.
    (re.compile(r"\b(yes|yep|yup|yeah|confirm|confirmed|ok(ay)?|sure|do it|go ahead|that'?s right)\b", re.I), Intent.CONFIRMATION, 0.95),
    # Denials.
    (re.compile(r"\b(no|nope|nah|cancel|stop|never ?mind|don'?t)\b", re.I), Intent.DENIAL, 0.9),
    # Goodbye.
    (re.compile(r"\b(bye|goodbye|see you|thanks|thank you|cheers|cya)\b", re.I), Intent.GOODBYE, 0.85),
    # Greeting.
    (re.compile(r"^(hi|hello|hey|good (morning|afternoon|evening))\b", re.I), Intent.GREETING, 0.85),
    # Reset.
    (re.compile(r"\b(reset|restart|start over|begin again|from scratch|new conversation)\b", re.I), Intent.RESET, 0.95),
    # Modify booking.
    (re.compile(r"\b(modify|change|update|reschedule|move)\b.*\b(booking|reservation|appointment|my)\b", re.I), Intent.MODIFY_BOOKING, 0.85),
    (re.compile(r"\b(can\s+i\s+change|can\s+you\s+change|change\s+my)\b", re.I), Intent.MODIFY_BOOKING, 0.9),
    # Cancel booking.
    (re.compile(r"\b(cancel|delete|drop)\b.*\b(booking|reservation|appointment|my)\b", re.I), Intent.CANCEL_BOOKING, 0.85),
    (re.compile(r"\b(cancel\s+my|please\s+cancel)\b", re.I), Intent.CANCEL_BOOKING, 0.9),
    # Lookup.
    (re.compile(r"\b(lookup|check|find|view|show)\b.*\b(my\s+)?(booking|reservation|appointment)\b", re.I), Intent.LOOKUP_BOOKING, 0.85),
    (re.compile(r"\b(what\s+are\s+my|where\s+is\s+my)\b.*\b(bookings?|reservations?)\b", re.I), Intent.LOOKUP_BOOKING, 0.9),
    # FAQ.
    (re.compile(r"\b(i have a question)\b", re.I), Intent.FAQ, 0.95),
     (re.compile(r"\b(what\s+time|when\s+do\s+you|hours|opening|closing|open\b|close\b|how much|price|cost|fee|payment|policy|refund|cancel\s+policy)\b", re.I), Intent.FAQ, 0.85),
    # Create booking.
    (re.compile(r"\b(i\s+want|i\s+need|i'?d\s+like|i\s+would\s+like|need|want|get\s+me|let'?s|please)\b.*\b(massage|booking|appointment|reservation|schedule|session|treatment)\b", re.I), Intent.CREATE_BOOKING, 0.9),
    (re.compile(r"\b(book|reserve|schedule)\b.*\b(me|for\s+me|a|massage|appointment|reservation|session|treatment)\b", re.I), Intent.CREATE_BOOKING, 0.9),
    (re.compile(r"\b(can\s+i\s+(book|reserve|get|schedule))\b", re.I), Intent.CREATE_BOOKING, 0.85),
    (re.compile(r"\b(make\s+(a|an)\s+(booking|reservation|appointment))\b", re.I), Intent.CREATE_BOOKING, 0.9),
    # Search variants.
    (re.compile(r"\b(show|list|browse|find)\b.*\b(shops?|branches?|stores?)\b", re.I), Intent.SEARCH_SHOP, 0.85),
    (re.compile(r"\b(show|list|browse|find)\b.*\b(courses?|massages?|treatments?|services?)\b", re.I), Intent.SEARCH_COURSE, 0.85),
    (re.compile(r"\b(show|list|browse|find)\b.*\b(slots?|times?|availability|available)\b", re.I), Intent.SEARCH_SLOT, 0.85),
    (re.compile(r"\b(show|list|browse|find)\b.*\b(therapists?|staff)\b", re.I), Intent.SEARCH_THERAPIST, 0.85),
    # Selection from a list.
    (re.compile(r"^\s*(?:the\s+)?(\d+)(?:st|nd|rd|th)?\s*(?:one|please)?\s*$", re.I), Intent.SELECT_SHOP, 0.5),
    (re.compile(r"\b(first|second|third|fourth|fifth|the\s+last)\s+(one|please)?\b", re.I), Intent.SELECT_SHOP, 0.5),
    # Correction.
    (re.compile(r"\b(actually|instead|change\s+to|make\s+it|no,|no\s+wait|rather|switch\s+to)\b", re.I), Intent.CORRECTION, 0.85),
    # Small talk.
    (re.compile(r"\b(cool|nice|awesome|great|sounds\s+good|ok(ay)\b|alright)\b", re.I), Intent.SMALL_TALK, 0.7),
    # Provide information (just a value, no action).
    (re.compile(r"^\s*(today|tomorrow|yesterday|tonight|next\s+\w+|this\s+\w+)\s*$", re.I), Intent.PROVIDE_INFORMATION, 0.85),
    (re.compile(r"^\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*(people|persons?|pax|guests?)?\s*$", re.I), Intent.PROVIDE_INFORMATION, 0.7),
    (re.compile(r"^\s*(morning|afternoon|evening|tonight|after\s+lunch|before\s+lunch|after\s+work|before\s+work)\s*$", re.I), Intent.PROVIDE_INFORMATION, 0.7),
    (re.compile(r"^\s*(earliest|latest)\s*$", re.I), Intent.PROVIDE_INFORMATION, 0.8),
]


def classify_intent(text: str) -> tuple[Intent, float]:
    """Return the best (intent, confidence) for the given text.

    Always returns SOMETHING — falls back to UNKNOWN with low confidence.
    """
    stripped = text.strip()
    if not stripped:
        return Intent.UNKNOWN, 0.0

    signals: list[_Signal] = []

    # Synonym-based whole-message match.
    lowered = " ".join(stripped.lower().split())
    if lowered in ACTION_SYNONYMS:
        signals.append(_Signal(Intent(ACTION_SYNONYMS[lowered]), 0.95, "synonym:exact"))

    # Pattern matches.
    for pat, intent, weight in _PHRASE_PATTERNS:
        if pat.search(stripped):
            signals.append(_Signal(intent, weight, f"pattern:{pat.pattern}"))

    # If no signals, try a fuzzy synonym — single-token matches.
    if not signals:
        tokens = re.findall(r"\w+", lowered)
        for tok in tokens:
            if tok in ACTION_SYNONYMS:
                signals.append(_Signal(Intent(ACTION_SYNONYMS[tok]), 0.7, f"synonym:token:{tok}"))

    # Aggregate: the intent with most weighted votes wins.
    if not signals:
        return Intent.UNKNOWN, 0.4

    scores: dict[Intent, float] = {}
    for sig in signals:
        scores[sig.intent] = scores.get(sig.intent, 0.0) + sig.weight

    best_intent, raw_score = max(scores.items(), key=lambda kv: kv[1])
    # Normalize confidence: max raw score capped at 1.0.
    confidence = min(1.0, raw_score / 1.5)
    return best_intent, confidence


# ---------------------------------------------------------------------------
# Intent priority — when multiple intents tie, this breaks the tie.
# (Higher wins.)
# ---------------------------------------------------------------------------
_INTENT_PRIORITY = {
    Intent.RESET: 100,
    Intent.GOODBYE: 90,
    Intent.GREETING: 90,
    Intent.SMALL_TALK: 80,
    Intent.CONFIRMATION: 70,
    Intent.DENIAL: 70,
    Intent.CANCEL_BOOKING: 60,
    Intent.MODIFY_BOOKING: 60,
    Intent.LOOKUP_BOOKING: 55,
    Intent.FAQ: 50,
    Intent.CORRECTION: 45,
    Intent.SEARCH_SHOP: 40,
    Intent.SEARCH_COURSE: 40,
    Intent.SEARCH_SLOT: 40,
    Intent.SEARCH_THERAPIST: 40,
    Intent.SELECT_SHOP: 35,
    Intent.SELECT_COURSE: 35,
    Intent.SELECT_SLOT: 35,
    Intent.SELECT_THERAPIST: 35,
    Intent.CREATE_BOOKING: 30,
    Intent.PROVIDE_INFORMATION: 20,
    Intent.UNKNOWN: 0,
}


def break_tie(text: str, entities: list, candidate_intents: list[Intent], current_confidence: float) -> tuple[Intent, float]:
    """Break ties when multiple intents have similar confidence or when intent is UNKNOWN.

    Args:
        text: The raw user message.
        entities: List of extracted entities.
        candidate_intents: List of candidate intents.
        current_confidence: The current confidence score of the top intent.

    Returns:
        A tuple of (winning_intent, new_confidence).
    """
    if not candidate_intents:
        return Intent.UNKNOWN, 0.0

    # If only one intent, return it.
    if len(candidate_intents) == 1:
        return candidate_intents[0], current_confidence

    # Special case: if PROVIDE_INFORMATION is among the intents and there are entities,
    # it likely means the user is providing information, even if no explicit intent phrase.
    if Intent.PROVIDE_INFORMATION in candidate_intents and entities:
        return Intent.PROVIDE_INFORMATION, max(current_confidence, 0.7)

    # Fallback to highest priority.
    highest_priority_intent = max(candidate_intents, key=lambda i: _INTENT_PRIORITY.get(i, 0))
    return highest_priority_intent, current_confidence