# chatbot/nlu/time_parser.py
"""Time parsing. Returns either:
    - "HH:MM" 24-hour clock (e.g. "15:00")
    - a period tag ("morning", "afternoon", "evening", "after_lunch", "before_lunch", "after_work")
    - None if not parseable.

Priority order:
    1. Explicit clock: "3pm", "15:00", "3:30pm"
    2. Word hour + period: "three in the afternoon" → 15:00
    3. Bare/word hour with no period → "HH:00"
    4. Period tag only when no explicit hour exists.
"""
from __future__ import annotations

import re
from typing import Optional

from word2number import w2n


PERIODS = {
    "morning": ("morning", "am"),
    "afternoon": ("afternoon", "pm"),
    "evening": ("evening", "pm"),
    "tonight": ("tonight", "pm"),
    "after lunch": ("after_lunch", "pm"),
    "after_lunch": ("after_lunch", "pm"),
    "before lunch": ("before_lunch", "am"),
    "before_lunch": ("before_lunch", "am"),
    "after work": ("after_work", "pm"),
    "after_work": ("after_work", "pm"),
    "before work": ("before_work", "am"),
    "before_work": ("before_work", "am"),
    "noon": ("noon", "pm"),
    "midnight": ("midnight", "am"),
}


def _detect_period(text: str) -> Optional[str]:
    """Return the canonical period tag if present, else None."""
    lowered = text.lower()
    # Longer phrases first.
    for phrase in ("after lunch", "before lunch", "after work", "before work"):
        if phrase in lowered:
            return phrase.replace(" ", "_")
    for tag in ("morning", "afternoon", "evening", "tonight", "noon", "midnight"):
        if re.search(rf"\b{tag}\b", lowered):
            return tag
    return None


def _hour_to_24(hour: int, period: Optional[str]) -> int:
    """Adjust a 12-hour hour for the given period (am/pm) and return 24-hour."""
    if period in {"pm", "afternoon", "evening", "tonight"}:
        if hour < 12:
            return hour + 12
        return hour
    if period in {"am", "morning"}:
        if hour == 12:
            return 0
        return hour
    return hour


def parse_time(text: str) -> tuple[Optional[str], Optional[str]]:
    if text is None:
        return None, None
    t = text.strip().lower()
    if not t:
        return None, None

    # If the input contains no time-like signal at all, refuse.
    has_clock_signal = bool(
        re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b", t)
        or re.search(r"\b\d{1,2}:\d{2}\b", t)
    )
    period = _detect_period(t)
    if not has_clock_signal and not period:
        return None, None
    
    # 1) Explicit am/pm with clock: "3pm" / "3 pm" / "3:30 p.m." / "three pm".
    ampm_match = re.search(
        r"(\b(?:\d{1,2}|(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty|forty|fifty))(?::(\d{2}))?\s*(?:am|pm|a\.m\.|p\.m\.))\b",
        t,
    )
    if ampm_match:
        raw_match_text = ampm_match.group(0)
        raw_hour = ampm_match.group(1)
        minute = int(ampm_match.group(2) or 0)
        suffix = "pm" if "p" in raw_match_text else "am"
        try:
            hour = w2n.word_to_num(raw_hour.replace(" and", ""))
        except ValueError:
            hour = int(raw_hour)
        if "p" in suffix and hour < 12:
            hour += 12
        if "a" in suffix and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}", raw_match_text

    # 2) "15:00" / "15:30" — 24-hour explicit.
    hms = re.search(r"\b(\d{1,2}):(\d{2})\b", t)
    if hms:
        hour = int(hms.group(1))
        minute = int(hms.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}", hms.group(0)

    # 3) Bare hour + period: "3 in the afternoon" → 15:00.
    if period:
        # Strip "around / about / approximately / in the / in" etc.
        cleaned = re.sub(
            r"\b(around|about|approximately|near|close to|roughly|at|by|in\s+the|in)\b\s*",
            "", t,
        ).strip()
        bare_hour, hour_raw = _extract_hour_token(cleaned)
        if bare_hour is not None:
            hour = _hour_to_24(bare_hour, _period_to_suffix(period))
            return f"{hour:02d}:00", f"{hour_raw} in the {period}"

    # 4) Bare hour "3" / "15" without period.
    bare_hour, hour_raw = _extract_hour_token(t)
    if bare_hour is not None:
        return f"{bare_hour:02d}:00", hour_raw

    # 5) Period tag alone.
    if period:
        return period, period

    return None, None


def _extract_hour_token(text: str) -> tuple[Optional[int], Optional[str]]:
    """Find any hour-like token (digit 1-23 or word number 1-23) in text."""
    # Numeric.
    m = re.search(r"\b(\d{1,2})\b", text)
    if m:
        h = int(m.group(1))
        if 1 <= h <= 23:
            return h, m.group(0)
    # Word.
    m = re.search(
        r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty)(?:\s+(?:thirty|forty|fifty))?\b",
        text,
    )
    if m:
        try:
            h = w2n.word_to_num(m.group(1).replace(" and", ""))
            if 1 <= h <= 23:
                return h, m.group(0)
        except ValueError:
            pass
    return None, None


def _period_to_suffix(period: str) -> str:
    if period in {"morning"}:
        return "am"
    if period in {"afternoon", "evening", "tonight", "after_lunch", "after_work", "noon"}:
        return "pm"
    if period in {"before_lunch", "before_work"}:
        return "am"
    return ""