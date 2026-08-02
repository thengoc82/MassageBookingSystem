# chatbot/nlu/__init__.py
"""Phase 9 — Natural Language Understanding package.

The NLU layer turns a raw user message into a structured `NLUResult` that
downstream layers (Dialogue State Tracking, Slot Filling, Dialogue Policy)
consume. The NLU layer itself does NOT do slot filling or policy work; it
only recognises intent, extracts entities, detects ambiguity, and reports
confidence.

Public API:
    - `NLUResult`: structured output of the NLU pipeline.
    - `Intent`: the canonical intent enum.
    - `EntityType`: the canonical entity types.
    - `Entity`: a single extracted entity.
    - `Ambiguity`: a flagged ambiguous entity.
    - `NLU`: the facade that runs the pipeline.
"""
from chatbot.nlu.models import (
    Ambiguity,
    Entity,
    EntityType,
    Intent,
    NLUResult,
)
from chatbot.nlu.nlu import NLU

__all__ = [
    "Ambiguity",
    "Entity",
    "EntityType",
    "Intent",
    "NLU",
    "NLUResult",
]