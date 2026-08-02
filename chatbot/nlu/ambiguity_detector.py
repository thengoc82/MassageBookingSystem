# chatbot/nlu/ambiguity_detector.py
"""Detect ambiguous references against known items.

Used during slot filling when the user typed something like 'Massage' that
matches more than one known course. Returns a list of `Ambiguity` objects.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, Optional

from chatbot.nlu.models import Ambiguity, Entity, EntityType


_THRESHOLD = 0.55


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _score(query: str, candidate: str) -> float:
    q, c = _norm(query), _norm(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.9
    return SequenceMatcher(None, q, c).ratio()


def _matches(query: str, candidates: Iterable[str]) -> list[tuple[str, float]]:
    scored = [(_score(query, c), c) for c in candidates if c]
    scored = [(s, c) for s, c in scored if s >= _THRESHOLD]
    scored.sort(key=lambda sc: sc[0], reverse=True)
    return scored


def detect_shop_ambiguity(query: str, shops: list[dict]) -> Optional[Ambiguity]:
    if not query or not shops:
        return None
    names = [s.get("shopName") if isinstance(s, dict) else getattr(s, "shopName", "") for s in shops]
    names = [n for n in names if n]
    scored = _matches(query, names)
    if not scored:
        return None
    if len(scored) >= 2 and (scored[0][0] - scored[1][0]) < 0.1 and scored[0][0] >= 0.7:
        return Ambiguity(
            entity_type=EntityType.SHOP, raw_text=query,
            candidates=[scored[0][1], scored[1][1]],
        )
    if scored[0][0] >= 0.95:
        return None
    if 0.55 <= scored[0][0] < 0.95:
        return Ambiguity(
            entity_type=EntityType.SHOP, raw_text=query,
            candidates=[name for _, name in scored[:3]],
        )
    return None


def detect_course_ambiguity(query: str, courses: list[dict]) -> Optional[Ambiguity]:
    if not query or not courses:
        return None
    names = [c.get("courseName") if isinstance(c, dict) else getattr(c, "courseName", "") for c in courses]
    names = [n for n in names if n]
    scored = _matches(query, names)
    if not scored:
        return None
    if len(scored) >= 2 and (scored[0][0] - scored[1][0]) < 0.1 and scored[0][0] >= 0.7:
        return Ambiguity(
            entity_type=EntityType.COURSE, raw_text=query,
            candidates=[scored[0][1], scored[1][1]],
        )
    if scored[0][0] >= 0.95:
        return None
    if 0.55 <= scored[0][0] < 0.95:
        return Ambiguity(
            entity_type=EntityType.COURSE, raw_text=query,
            candidates=[name for _, name in scored[:3]],
        )
    return None


def detect_therapist_ambiguity(query: str, therapists: list[dict]) -> Optional[Ambiguity]:
    if not query or not therapists:
        return None
    names = [t.get("name") if isinstance(t, dict) else getattr(t, "name", "") for t in therapists]
    names = [n for n in names if n]
    scored = _matches(query, names)
    if not scored:
        return None
    if len(scored) >= 2 and (scored[0][0] - scored[1][0]) < 0.1 and scored[0][0] >= 0.7:
        return Ambiguity(
            entity_type=EntityType.THERAPIST, raw_text=query,
            candidates=[scored[0][1], scored[1][1]],
        )
    if scored[0][0] >= 0.95:
        return None
    if 0.55 <= scored[0][0] < 0.95:
        return Ambiguity(
            entity_type=EntityType.THERAPIST, raw_text=query,
            candidates=[name for _, name in scored[:3]],
        )
    return None


# ---------------------------------------------------------------------------
# Entity resolution: pick the best known item for an Entity of type SHOP /
# COURSE / THERAPIST given the user's text and a known list.
# ---------------------------------------------------------------------------
def resolve_entity(entity: Entity, known_items: list[dict]) -> Optional[dict]:
    """Return the best matching known item for `entity`, or None."""
    if entity.type not in {EntityType.SHOP, EntityType.COURSE, EntityType.THERAPIST}:
        return None
    if not entity.value:
        return None

    name_keys = {
        EntityType.SHOP: "shopName",
        EntityType.COURSE: "courseName",
        EntityType.THERAPIST: "name",
    }[entity.type]
    id_keys = {
        EntityType.SHOP: "shopId",
        EntityType.COURSE: "courseId",
        EntityType.THERAPIST: "therapistId",
    }[entity.type]

    scored = []
    for item in known_items:
        if isinstance(item, dict):
            name = item.get(name_keys)
            item_id = item.get(id_keys)
        else:
            name = getattr(item, name_keys, None)
            item_id = getattr(item, id_keys, None)
        s = _score(entity.value, name or "")
        if s >= _THRESHOLD:
            scored.append((s, item, item_id, name))
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    if len(scored) >= 2 and (scored[0][0] - scored[1][0]) < 0.1 and scored[0][0] >= 0.7:
        # ambiguous — caller should use detect_*_ambiguity instead.
        return None
    return {"id": scored[0][2], "name": scored[0][3], "score": scored[0][0]}