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


def _detect_period(text: str, consumed_spans: list[tuple[int, int]]) -> Optional[tuple[str, str, tuple[int, int]]]:
    """Return the (canonical tag, raw text, span) if present and not consumed, else None."""
    lowered = text.lower()
    
    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    # Longer phrases first.
    for phrase in ("after lunch", "before lunch", "after work", "before work"):
        for match in re.finditer(phrase, lowered):
            if not is_consumed(match.span()):
                return phrase.replace(" ", "_"), match.group(0), match.span()
                
    for tag in ("morning", "afternoon", "evening", "tonight", "noon", "midnight"):
        for match in re.finditer(rf"\b{tag}\b", lowered):
            if not is_consumed(match.span()):
                return tag, match.group(0), match.span()
                
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


def parse_time(text: str, consumed_spans: list[tuple[int, int]]) -> tuple[Optional[str], Optional[str], Optional[tuple[int, int]]]:
    if text is None:
        return None, None, None
    t = text.strip().lower()
    if not t:
        return None, None, None

    def is_consumed(span):
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    # 1) Explicit am/pm with clock: "3pm" / "3 pm" / "3:30 p.m." / "three pm".
    for ampm_match in re.finditer(
        r"(\b(?:\d{1,2}|(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
        r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
        r"nineteen|twenty|thirty|forty|fifty))(?::(\d{2}))?\s*(?:am|pm|a\.m\.|p\.m\.))\b",
        t,
    ):
        if not is_consumed(ampm_match.span()):
            raw_match_text = ampm_match.group(0)
            raw_hour = ampm_match.group(1)
            minute = int(ampm_match.group(2) or 0)
            suffix = "pm" if "p" in raw_match_text else "am"
            try:
                hour = w2n.word_to_num(raw_hour.replace(" and", ""))
            except ValueError:
                hour = int(re.findall(r'\d+', raw_hour)[0])

            if "p" in suffix and hour < 12:
                hour += 12
            if "a" in suffix and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}", raw_match_text, ampm_match.span()

    # 2) "15:00" / "15:30" — 24-hour explicit.
    for hms in re.finditer(r"\b(\d{1,2}):(\d{2})\b", t):
        if not is_consumed(hms.span()):
            hour = int(hms.group(1))
            minute = int(hms.group(2))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}", hms.group(0), hms.span()

    # --- Period-based parsing (less specific) ---

    period_match = _detect_period(t, consumed_spans)
    if period_match:
        period_tag, period_raw, period_span = period_match
        
        # 3) Bare hour + period: "3 in the afternoon" → 15:00.
        # Check for an hour token near the period.
        search_window = t[max(0, period_span[0]-20):min(len(t), period_span[1]+20)]
        hour_token_match = _extract_hour_token(search_window, consumed_spans, period_span)
        
        if hour_token_match:
            bare_hour, hour_raw, hour_span_rel = hour_token_match
            # Adjust hour_span to be absolute to the original text 't'
            hour_span_abs = (hour_span_rel[0] + max(0, period_span[0]-20), hour_span_rel[1] + max(0, period_span[0]-20))

            if not is_consumed(hour_span_abs):
                 hour = _hour_to_24(bare_hour, _period_to_suffix(period_tag))
                 combined_raw = f"{hour_raw} {period_raw}"
                 combined_span = (min(hour_span_abs[0], period_span[0]), max(hour_span_abs[1], period_span[1]))
                 return f"{hour:02d}:00", combined_raw, combined_span

    # 4) Bare hour "3" / "15" without period.
    hour_token_match = _extract_hour_token(t, consumed_spans)
    if hour_token_match:
        bare_hour, hour_raw, hour_span = hour_token_match
        return f"{bare_hour:02d}:00", hour_raw, hour_span

    # 5) Period tag alone if nothing else matched.
    if period_match:
        period_tag, period_raw, period_span = period_match
        return period_tag, period_raw, period_span

    return None, None, None


def _extract_hour_token(text: str, consumed_spans: list[tuple[int, int]], relative_to_span: Optional[tuple[int,int]] = None) -> Optional[tuple[int, str, tuple[int, int]]]:
    """Find any hour-like token, checking against consumed spans.
    Now requires a keyword immediately adjacent to the number.
    """

    def is_consumed(span, is_relative=False):
        if is_relative:
            return False
        return any(s < span[1] and e > span[0] for s, e in consumed_spans)

    is_relative_search = relative_to_span is not None

    # Stricter regex: require a time keyword directly before or after the number.
    # The keyword is not part of the main group.
    for m in re.finditer(r"\b(?:at|by|around|for)\s+(\d{1,2})\b|\b(\d{1,2})\s*(?:o'clock|oclock)\b", text):
        span = m.span()
        if not is_consumed(span, is_relative_search):
            hour_str = m.group(1) or m.group(2)
            h = int(hour_str)
            if 1 <= h <= 23:
                return h, m.group(0), span

    # Word-based hours with keywords
    for m in re.finditer(r"\b(?:at|by|around|for)\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b", text):
        span = m.span()
        if not is_consumed(span, is_relative_search):
            try:
                h = w2n.word_to_num(m.group(1))
                if 1 <= h <= 12:
                    return h, m.group(0), span
            except ValueError:
                pass
                
    return None


def _period_to_suffix(period: str) -> str:
    if period in {"morning"}:
        return "am"
    if period in {"afternoon", "evening", "tonight", "after_lunch", "after_work", "noon"}:
        return "pm"
    if period in {"before_lunch", "before_work"}:
        return "am"
    return ""