# chatbot/nlu/confidence.py
"""Confidence scoring helpers."""
from __future__ import annotations

from typing import Iterable

from chatbot.nlu.models import Ambiguity, Entity, EntityType, NLUResult


def combine_entity_confidence(entities: Iterable[Entity]) -> float:
    """Average entity confidence. Returns 1.0 for empty input."""
    ents = list(entities)
    if not ents:
        return 1.0
    return sum(e.confidence for e in ents) / len(ents)


def penalise_for_ambiguity(nlu: NLUResult) -> float:
    """Reduce overall confidence if there are ambiguous entities."""
    if not nlu.ambiguities:
        return nlu.intent_confidence
    penalty = 0.05 * len(nlu.ambiguities)
    return max(0.0, nlu.intent_confidence - penalty)


def penalise_for_unknown_entities(nlu: NLUResult) -> float:
    """Reduce confidence if entities have very low scores."""
    low = [e for e in nlu.entities if e.confidence < 0.6]
    if not low:
        return nlu.intent_confidence
    penalty = 0.05 * len(low)
    return max(0.0, nlu.intent_confidence - penalty)


def overall_confidence(nlu: NLUResult) -> float:
    """Final NLU confidence after penalties."""
    base = nlu.intent_confidence
    base = penalise_for_ambiguity(_clone_with_intent_confidence(nlu, base))
    base = penalise_for_unknown_entities(_clone_with_intent_confidence(nlu, base))
    return round(base, 3)


def _clone_with_intent_confidence(nlu: NLUResult, conf: float) -> NLUResult:
    """Return a shallow copy of `nlu` with intent_confidence replaced."""
    return NLUResult(
        intent=nlu.intent,
        intent_confidence=conf,
        entities=nlu.entities,
        ambiguities=nlu.ambiguities,
        raw_message=nlu.raw_message,
        notes=nlu.notes,
    )