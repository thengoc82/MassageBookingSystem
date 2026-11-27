"""Conservative evidence selection for customer FAQ answers."""

import re

from chatbot.models import FAQItem


_COMMON = {
    "a", "about", "an", "and", "are", "at", "can", "could", "do", "does",
    "for", "from", "have", "how", "i", "in", "is", "it", "me", "my", "of",
    "on", "our", "please", "the", "their", "there", "these", "to", "us",
    "what", "when", "where", "which", "who", "why", "with", "would", "you",
    "your", "massage", "service", "services", "offer", "need", "tell",
}


def _normalized_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold())
    normalized: set[str] = set()
    for word in words:
        if word in _COMMON or len(word) < 3:
            continue
        if word.startswith("cancel"):
            word = "cancel"
        elif word.startswith("book"):
            word = "book"
        elif word.startswith("therapist"):
            word = "therapist"
        elif word.startswith("couple"):
            word = "couple"
        elif word.startswith("room"):
            word = "room"
        elif word.startswith("addon"):
            word = "addon"
        elif word == "policies":
            word = "policy"
        normalized.add(word)
    return normalized


def answerable_items(question: str, items: list[FAQItem], limit: int = 2) -> list[FAQItem]:
    """Keep only excerpts that share the question's specific terms.

    Vector similarity finds candidates; this gate prevents a nearby but unrelated
    excerpt from being presented as an answer when the LLM is unavailable.
    """
    terms = _normalized_tokens(question)
    if not terms:
        return []
    selected: list[FAQItem] = []
    for item in items:
        evidence = _normalized_tokens(f"{item.citation.heading or ''} {item.content}")
        matches = len(terms & evidence)
        if matches >= min(2, len(terms)) and matches / len(terms) >= 0.5:
            selected.append(item)
            if len(selected) == limit:
                break
    return selected
