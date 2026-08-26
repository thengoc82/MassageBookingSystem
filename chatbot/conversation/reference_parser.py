"""Helper functions for resolving references from user text.

Used by ChatEndpoint to parse selections, relative dates, and corrections.
"""
import re
from datetime import date, timedelta
from typing import Any


_ORDINALS = {
    "first": 0,
    "second": 1,
    "third": 2,
    "fourth": 3,
    "fifth": 4,
    "last": -1,
    "one": 0,
    "two": 1,
    "three": 2,
    "four": 3,
    "five": 4,
}


_DAYS_OF_WEEK = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def resolve_by_index(text: str, items: list[Any]) -> tuple[bool, int]:
    """Parse "1", "2", etc. Returns (matched, index_0_based)."""
    match = re.search(r"\b\d+\b", text)
    if not match:
        return False, -1
    idx = int(match.group(0)) - 1
    if 0 <= idx < len(items):
        return True, idx
    return False, -1


def resolve_by_ordinal(text: str, items: list[Any]) -> tuple[bool, int]:
    """Parse "first", "second", "the last one". Returns (matched, index_0_based)."""
    for word, offset in _ORDINALS.items():
        if re.search(r"\b" + word + r"\b", text):
            idx = offset if offset >= 0 else len(items) - 1
            if 0 <= idx < len(items):
                return True, idx
    return False, -1


def resolve_by_name(text: str, items: list[Any], name_keys: tuple[str, ...] = ("shopName", "courseName", "name")) -> tuple[bool, int]:
    """Find best name match in items. Returns (matched, index_0_based)."""
    text_lower = text.lower()
    best_idx = -1
    best_score = 0.0
    for i, item in enumerate(items):
        for key in name_keys:
            name = ""
            if isinstance(item, dict):
                name = str(item.get(key, ""))
            else:
                name = str(getattr(item, key, "") or "")
            if not name:
                continue
            n = name.lower()
            if n in text_lower:
                score = 1.0
            elif n.split()[0] in text_lower:
                score = 0.85
            else:
                continue
            if score > best_score:
                best_score = score
                best_idx = i
    if best_idx >= 0:
        return True, best_idx
    return False, -1


def parse_relative_date(text: str, base_date_str: str | date | None = None) -> str | None:
    """Parse "tomorrow" or weekday names. Returns ISO date string or None."""
    if isinstance(base_date_str, date):
        base_date = base_date_str
    else:
        base_date = date.fromisoformat(base_date_str) if base_date_str else date.today()
    text_lower = text.lower()
    if "tomorrow" in text_lower:
        return (base_date + timedelta(days=1)).isoformat()
    if "today" in text_lower:
        return date.today().isoformat() # "today" should always be today
    for day_name, day_idx in _DAYS_OF_WEEK.items():
        if day_name in text_lower:
            days_ahead = day_idx - base_date.weekday()
            if days_ahead <= 0: # If it's today or a past day of this week, get next week's
                days_ahead += 7
            return (base_date + timedelta(days=days_ahead)).isoformat()
    return None


