# chatbot/nlu/date_parser.py
"""Natural-language date parsing. Returns either:
    - an ISO date string ("2026-08-01")
    - a tagged relative ("earliest", "latest")
    - None if not parseable.

The parser never throws — it returns None on garbage input.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Special tokens we expose as tags (not ISO dates).
SPECIAL_TOKENS = {"earliest", "latest", "today", "tomorrow"}


def parse_date(text: str, today: Optional[date] = None) -> tuple[Optional[str], Optional[str]]:
    """Parse a string into an ISO date, a relative tag, or None.

    Returns a tuple of (value, raw_text_matched) or (None, None).

    Examples:
        "today"           -> "2026-07-29"
        "tomorrow"        -> "2026-07-30"
        "yesterday"       -> "2026-07-28"
        "Friday"          -> "2026-07-31"
        "next Friday"     -> "2026-08-07"
        "this Saturday"   -> "2026-08-01"
        "this weekend"    -> "2026-08-01" (Sat)
        "next week"       -> "2026-08-03" (Mon)
        "earliest"        -> "earliest"
        "latest"          -> "latest"
        "3 Aug"           -> "2026-08-03"
        "August 3"        -> "2026-08-03"
        "2026-08-03"      -> "2026-08-03"
        "3 Aug 2026"      -> "2026-08-03"
    """
    if text is None:
        return None
    t = text.strip().lower()
    if not t:
        return None, None

    today = today or datetime.now().date()

    # Special-token exact match first (whole input is a tag/date).
    if t in SPECIAL_TOKENS:
        if t in {"earliest", "latest"}:
            return t, t
        if t == "today":
            return today.isoformat(), t
        if t == "tomorrow":
            return (today + timedelta(days=1)).isoformat(), t

    # Substring detection for relative dates inside a longer message.
    # Order matters: more specific patterns first.
    if "earliest" in t:
        return "earliest", "earliest"
    if "latest" in t:
        return "latest", "latest"
    if "yesterday" in t:
        return (today - timedelta(days=1)).isoformat(), "yesterday"
    if t in {"this weekend", "the weekend", "weekend"}:
        days_ahead = (5 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat(), "weekend"
    if "tomorrow" in t:
        return (today + timedelta(days=1)).isoformat(), "tomorrow"
    if "today" in t:
        return today.isoformat(), "today"
    if "tonight" in t:
        return "tonight", "tonight"

    # "next week" → next Monday.
    if t == "next week":
        days_ahead = (0 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat(), "next week"

    # "next <weekday>" / "next <month> <day>".
    next_match = re.match(r"^next\s+(\w+)(?:\s+(\d+))?$", t)
    if next_match:
        word = next_match.group(1)
        if word in WEEKDAYS:
            target = WEEKDAYS.index(word)
            days_ahead = (target - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat(), next_match.group(0)
        if word in MONTHS:
            day = int(next_match.group(2) or 1)
            resolved_date = _resolve_month_day(word, day, today)
            if resolved_date:
                return resolved_date.isoformat(), next_match.group(0)

    # "this <weekday>".
    this_match = re.match(r"^this\s+(\w+)$", t)
    if this_match:
        word = this_match.group(1)
        if word in WEEKDAYS:
            target = WEEKDAYS.index(word)
            days_ahead = (target - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat(), this_match.group(0)

    # Plain weekday (anywhere in text).
    for idx, day_name in enumerate(WEEKDAYS):
        if day_name in t:
            days_ahead = (idx - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat(), day_name

    # ISO format YYYY-MM-DD.
    iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t)
    if iso_match:
        try:
            dt = datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
            return dt.isoformat(), iso_match.group(0)
        except ValueError:
            pass

    # Slash format DD/MM/YYYY or MM/DD/YYYY.
    slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", t)
    if slash_match:
        try:
            dt = datetime.strptime(slash_match.group(0), "%d/%m/%Y").date()
            return dt.isoformat(), slash_match.group(0)
        except ValueError:
            pass

    # "3 Aug" / "3 Aug 2026" / "August 3" / "August 3 2026".
    dmy, raw = _parse_day_month_year(t, today)
    if dmy:
        return dmy.isoformat(), raw

    return None, None


def _resolve_month_day(month: str, day: int, today: date) -> Optional[date]:
    if day < 1 or day > 31:
        return None
    month_num = MONTHS[month]
    year = today.year
    try:
        candidate = date(year, month_num, day)
    except ValueError:
        return None
    if candidate < today:
        try:
            return date(year + 1, month_num, day)
        except ValueError:
            return None
    return candidate


def _parse_day_month_year(text: str, today: date) -> tuple[Optional[date], Optional[str]]:
    """Accepts '3 Aug', '3 Aug 2026', 'August 3', 'August 3 2026', 'Aug 3rd'.
    Returns (date, raw_text) or (None, None).
    """
    # Day + month.
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?\b", text)
    if m and m.group(2) in MONTHS:
        day = int(m.group(1))
        month_num = MONTHS[m.group(2)]
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, month_num, day), m.group(0)
        except ValueError:
            pass

    # Month + day.
    m = re.search(r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\b", text)
    if m and m.group(1) in MONTHS:
        day = int(m.group(2))
        month_num = MONTHS[m.group(1)]
        year = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, month_num, day), m.group(0)
        except ValueError:
            pass

    return None, None