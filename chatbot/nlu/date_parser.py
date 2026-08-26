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


def parse_date(text: str, consumed_spans: list[tuple[int, int]], today: Optional[date] = None) -> tuple[Optional[str], Optional[str]]:
    """Parse a string into an ISO date, a relative tag, or None.

    Returns a tuple of (value, raw_text_matched) or (None, None).
    Checks against consumed_spans to avoid re-matching consumed text.

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
        return None, None
    t = text.strip().lower()
    if not t:
        return None, None

    today = today or datetime.now().date()

    # Helper to check for span overlaps
    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    # ISO format YYYY-MM-DD.
    for iso_match in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", t):
        if not is_consumed(iso_match.span()):
            try:
                dt = datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
                return dt.isoformat(), iso_match.group(0)
            except ValueError:
                pass

    # Slash format DD/MM/YYYY or MM/DD/YYYY.
    for slash_match in re.finditer(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", t):
        if not is_consumed(slash_match.span()):
            try:
                dt = datetime.strptime(slash_match.group(0), "%d/%m/%Y").date()
                return dt.isoformat(), slash_match.group(0)
            except ValueError:
                try:
                    dt = datetime.strptime(slash_match.group(0), "%m/%d/%Y").date()
                    return dt.isoformat(), slash_match.group(0)
                except ValueError:
                    pass

    # "3 Aug" / "3 Aug 2026" / "August 3" / "August 3 2026".
    dmy, raw = _parse_day_month_year(t, today, consumed_spans)
    if dmy:
        return dmy.isoformat(), raw

    # --- Relative dates ---
    # NOTE: These are less specific and should come after absolute formats.
    
    # Special-token exact match first (whole input is a tag/date).
    if t in SPECIAL_TOKENS:
        span = (0, len(t))
        if not is_consumed(span):
            if t in {"earliest", "latest"}:
                return t, t
            if t == "today":
                return today.isoformat(), t
            if t == "tomorrow":
                return (today + timedelta(days=1)).isoformat(), t

    # Substring detection for relative dates inside a longer message.
    # Order matters: more specific patterns first.
    patterns = {
        "earliest": "earliest",
        "latest": "latest",
        "yesterday": (today - timedelta(days=1)).isoformat(),
        "this weekend": (today + timedelta(days=(5 - today.weekday()) % 7 if (5 - today.weekday()) % 7 != 0 else 7)).isoformat(),
        "the weekend": (today + timedelta(days=(5 - today.weekday()) % 7 if (5 - today.weekday()) % 7 != 0 else 7)).isoformat(),
        "weekend": (today + timedelta(days=(5 - today.weekday()) % 7 if (5 - today.weekday()) % 7 != 0 else 7)).isoformat(),
        "tomorrow": (today + timedelta(days=1)).isoformat(),
        "today": today.isoformat(),
        "tonight": "tonight"
    }
    for keyword, value in patterns.items():
        for match in re.finditer(rf"\b{keyword}\b", t):
            if not is_consumed(match.span()):
                return value, keyword
    
    # "next week" → next Monday.
    for match in re.finditer(r"\bnext week\b", t):
        if not is_consumed(match.span()):
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + timedelta(days=days_ahead)).isoformat(), "next week"

    # "next <weekday>" / "this <weekday>" / "<weekday>"
    for idx, day_name in enumerate(WEEKDAYS):
        for match in re.finditer(rf"\b(next\s+|this\s+)?{day_name}\b", t):
            if not is_consumed(match.span()):
                is_next = match.group(1) and "next" in match.group(1)
                days_ahead = (idx - today.weekday() + 7) % 7
                if days_ahead == 0 and not is_next: # Today
                    days_ahead = 7 
                if is_next:
                    days_ahead += 7
                return (today + timedelta(days=days_ahead)).isoformat(), match.group(0)

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


def _parse_day_month_year(text: str, today: date, consumed_spans: list[tuple[int, int]]) -> tuple[Optional[date], Optional[str]]:
    """Accepts '3 Aug', '3 Aug 2026', 'August 3', 'August 3 2026', 'Aug 3rd'.
    Returns (date, raw_text) or (None, None).
    """
    
    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    # Day + month.
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?\b", text):
        if m.group(2) in MONTHS and not is_consumed(m.span()):
            day = int(m.group(1))
            month_num = MONTHS[m.group(2)]
            year = int(m.group(3)) if m.group(3) else today.year
            try:
                return date(year, month_num, day), m.group(0)
            except ValueError:
                pass

    # Month + day.
    for m in re.finditer(r"\b([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\b", text):
        if m.group(1) in MONTHS and not is_consumed(m.span()):
            day = int(m.group(2))
            month_num = MONTHS[m.group(1)]
            year = int(m.group(3)) if m.group(3) else today.year
            try:
                return date(year, month_num, day), m.group(0)
            except ValueError:
                pass

    return None, None