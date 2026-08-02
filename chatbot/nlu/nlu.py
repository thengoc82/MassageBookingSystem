# chatbot/nlu/nlu.py
"""NLU facade. Single entry point for the rest of the chatbot.

`nlu = NLU()` then `nlu.understand("Book a 60 min massage tomorrow at Shinjuku for two people", state)`
returns an `NLUResult`.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from chatbot.conversation.state import ConversationState

logger = logging.getLogger(__name__)

from chatbot.nlu.ambiguity_detector import (
    detect_course_ambiguity,
    detect_shop_ambiguity,
    detect_therapist_ambiguity,
)
from chatbot.nlu.confidence import overall_confidence
from chatbot.nlu.entity_extractor import EntityExtractor, detect_correction
from chatbot.nlu.intent_classifier import break_tie, classify_intent
from chatbot.nlu.models import Ambiguity, Entity, EntityType, Intent, NLUResult


class NLU:
    """Stateless (mostly) NLU pipeline."""

    def __init__(
        self,
        known_shops: Optional[Iterable[Any]] = None,
        known_courses: Optional[Iterable[Any]] = None,
        known_therapists: Optional[Iterable[Any]] = None,
    ) -> None:
        self._extractor = EntityExtractor(
            known_shops=known_shops,
            known_courses=known_courses,
            known_therapists=known_therapists,
        )

    # ------------------------------------------------------------------
    # Known items registration (drives the ambiguity detector).
    # ------------------------------------------------------------------
    def set_known_items(
        self,
        shops: Optional[Iterable[Any]] = None,
        courses: Optional[Iterable[Any]] = None,
        therapists: Optional[Iterable[Any]] = None,
    ) -> None:
        self._extractor.set_known_items(shops, courses, therapists)

    # ------------------------------------------------------------------
    # Main entry point.
    # ------------------------------------------------------------------
    async def understand(
        self,
        message: str,
        state: Optional["ConversationState"] = None,
        focused_slot: Optional[str] = None,
    ) -> NLUResult:
        logger.info(f"Understanding message: {message}")
        state = state or None
        text = message or ""
        stripped = text.strip()

        # 1. Intent.
        intent, confidence = classify_intent(stripped)
        logger.info(f"Initial intent: {intent} with confidence {confidence}")

        # 2. Detect correction.
        is_correction = detect_correction(stripped)
        logger.info(f"Is correction: {is_correction}")

        # 3. Extract entities.
        entities = self._extractor.extract(text, is_correction=is_correction, focused_slot=focused_slot)
        logger.info(f"Extracted entities: {entities}")

        # 4. Try to resolve shop / course / therapist references against
        #    the most recent tool results stored in state.
        if state is not None:
            # This is where we would resolve entities if needed, but the new
            # extractor should already be returning IDs.
            # self._resolve_entities_against_state(entities, state)
            pass
            
        # 5. Break ties for intent.
        if confidence < 0.7:  # Only break ties for low-confidence classifications.
            candidate_intents = [intent] if intent != Intent.UNKNOWN else []
            # Pass the NLU-detected intent to break_tie, allowing it to re-evaluate with entities
            intent, confidence = break_tie(stripped, entities, candidate_intents, confidence)



        # 6. If intent is PROVIDE_INFORMATION but no entities were
        #    extracted, upgrade confidence via fallback. Likewise, if
        #    we got entities but the intent is still UNKNOWN, infer
        #    PROVIDE_INFORMATION.
        if intent == Intent.UNKNOWN and entities:
            intent = Intent.PROVIDE_INFORMATION
            confidence = max(confidence, 0.7)

        # 7. Detect ambiguities (placeholder, as resolution now happens in extractor)
        ambiguities = [] # self._detect_ambiguities(entities, state)

        nlu_result = NLUResult(
            intent=intent,
            intent_confidence=confidence,
            entities=entities,
            ambiguities=ambiguities,
            raw_message=text,
        )

        # 8. Apply penalties for ambiguities and low-confidence entities.
        nlu_result.intent_confidence = overall_confidence(nlu_result)
        
        print("========== NLU ==========")
        print(f"Intent: {nlu_result.intent}")
        print(f"Confidence: {nlu_result.intent_confidence}")
        print("Entities:")
        for e in nlu_result.entities:
            print(f"  {e.type}: {e.value} (Raw: '{e.raw_text}', Span: {e.span})")
        print("=========================")

        return nlu_result

    # ------------------------------------------------------------------
    # Resolution + ambiguity (these methods might become obsolete)
    # ------------------------------------------------------------------
    def _resolve_entities_against_state(self, entities: list[Entity], state: "ConversationState") -> None:
        """
        This method is now less important as the extractor should return IDs directly.
        It can serve as a fallback or for complex resolution logic in the future.
        """
        pass # For now, the new extractor handles this.

    def _detect_ambiguities(
        self,
        entities: list[Entity],
        state: Optional["ConversationState"],
    ) -> list[Ambiguity]:
        """
        Ambiguity detection may also move closer to the extraction phase.
        Placeholder for now.
        """
        return []