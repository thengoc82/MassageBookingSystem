"""Parse customer-stated booking preferences without changing booking state."""

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def local_today() -> date:
    """Use the shop-facing local date for relative customer requests."""
    return datetime.now(LOCAL_ZONE).date()


def _clock(hour_text: str, minute_text: str | None, meridiem: str | None) -> str | None:
    hour = int(hour_text)
    minute = int(minute_text or 0)
    if minute > 59 or (meridiem and not 1 <= hour <= 12) or hour > 23:
        return None
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    return time(hour, minute).strftime("%H:%M")


def extract_booking_details(message: str) -> dict[str, str | int]:
    """Extract only values that appear in the customer's current message."""
    text = message.casefold()
    details: dict[str, str | int] = {}
    today = local_today()

    if re.search(r"\btomorrow\b", text):
        details["date"] = (today + timedelta(days=1)).isoformat()
    elif re.search(r"\btoday\b", text):
        details["date"] = today.isoformat()
    iso_date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if iso_date:
        try:
            details["date"] = date.fromisoformat(iso_date.group()).isoformat()
        except ValueError:
            pass

    people = re.search(r"\b(\d+)\s*(?:people|persons?|ppl|guests?)\b", text)
    if people and int(people.group(1)) > 0:
        details["number_of_people"] = int(people.group(1))
    elif re.search(r"\b(?:couple|couples|both of us|two of us)\b", text):
        details["number_of_people"] = 2
    elif re.search(r"\b(?:just me|only me|myself)\b", text):
        details["number_of_people"] = 1
    else:
        of_us = re.search(r"\b(one|two|three|four)\s+of us\b", text)
        word_people = re.search(
            r"\b(?:for|make it|to)\s+(one|two|three|four)\s*(?:people|persons?|guests?)?\b",
            text,
        )
        if of_us or word_people:
            details["number_of_people"] = {
                "one": 1, "two": 2, "three": 3, "four": 4,
            }[(of_us or word_people).group(1)]

    duration = re.search(r"\b(\d+)\s*(min(?:ute)?s?|m|hours?|hrs?)\b", text)
    if duration and int(duration.group(1)) > 0:
        amount = int(duration.group(1))
        unit = duration.group(2)
        details["duration"] = amount * 60 if unit.startswith(("hour", "hr")) else amount

    phone = re.search(r"(?<!\d)\d{9,11}(?!\d)", text)
    if phone:
        details["phone_number"] = phone.group()

    clock_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if clock_match is None:
        clock_match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if clock_match is None:
        clock_match = re.search(
            r"\b(?:at|around|about|after|before)\s+(\d{1,2})(?::(\d{2}))?\b(?!\s*(?::|am\b|pm\b|minutes?\b))",
            text,
        )
    if clock_match:
        meridiem = clock_match.group(3) if clock_match.lastindex == 3 else None
        clock = _clock(clock_match.group(1), clock_match.group(2), meridiem)
        if clock:
            prefix = text[max(0, clock_match.start() - 12):clock_match.start()]
            modifier = re.search(
                r"\b(around|about|after|before)\s*$", prefix
            ) or re.match(r"(around|about|after|before)\b", clock_match.group(0))
            if modifier:
                details["time_preference"] = f"{modifier.group(1)}:{clock}"
            else:
                details["start_time"] = clock
    if "start_time" not in details and "time_preference" not in details:
        for label in ("morning", "afternoon", "evening", "tonight"):
            if re.search(rf"\b{label}\b", text):
                details["time_preference"] = label
                break
    return details


def contextual_number(message: str, field: str) -> tuple[str | int | None, bool]:
    """Interpret a bare number only as the detail currently being requested."""
    stripped = message.strip()
    if not re.fullmatch(r"\d{1,3}", stripped):
        return None, False
    value = int(stripped)
    if field == "time":
        return (f"{value:02d}:00" if value <= 23 else None), True
    if field in {"duration", "number_of_people"}:
        return (value if value > 0 else None), True
    return None, False


def matches_preference(value: str, preference: str) -> bool:
    """Rank only slots already returned as available by Flask."""
    minutes = time.fromisoformat(value).hour * 60 + time.fromisoformat(value).minute
    windows = {
        "morning": (8 * 60, 12 * 60),
        "afternoon": (12 * 60, 17 * 60),
        "evening": (17 * 60, 22 * 60),
        "tonight": (18 * 60, 22 * 60),
    }
    if preference in windows:
        start, end = windows[preference]
        return start <= minutes < end
    modifier, _, anchor = preference.partition(":")
    try:
        anchor_time = time.fromisoformat(anchor)
    except ValueError:
        return False
    anchor_minutes = anchor_time.hour * 60 + anchor_time.minute
    if modifier in {"around", "about"}:
        return abs(minutes - anchor_minutes) <= 60
    if modifier == "after":
        return minutes >= anchor_minutes
    if modifier == "before":
        return minutes <= anchor_minutes
    return False


def preference_rank(value: str, preference: str) -> tuple[int, str]:
    """Order Flask-returned slots by closeness to the stated preference."""
    slot = time.fromisoformat(value)
    minutes = slot.hour * 60 + slot.minute
    named_targets = {
        "morning": 10 * 60, "afternoon": 14 * 60 + 30,
        "evening": 18 * 60, "tonight": 19 * 60,
    }
    if preference in named_targets:
        return abs(minutes - named_targets[preference]), value
    modifier, _, anchor = preference.partition(":")
    try:
        anchor_time = time.fromisoformat(anchor)
        target = anchor_time.hour * 60 + anchor_time.minute
    except ValueError:
        return minutes, value
    return abs(minutes - target), value


def validated_llm_details(message: str, candidate: dict) -> dict[str, str | int]:
    """Keep only well-formed candidate values supported by words in this turn."""
    text = message.casefold()
    accepted: dict[str, str | int] = {}
    candidate_date = candidate.get("date")
    if isinstance(candidate_date, str):
        try:
            normalized = date.fromisoformat(candidate_date).isoformat()
            today = local_today()
            if (
                normalized in text
                or (re.search(r"\btoday\b", text) and normalized == today.isoformat())
                or (re.search(r"\btomorrow\b", text) and normalized == (today + timedelta(days=1)).isoformat())
            ):
                accepted["date"] = normalized
        except ValueError:
            pass
    candidate_time = candidate.get("start_time")
    if isinstance(candidate_time, str):
        try:
            parsed = time.fromisoformat(candidate_time)
            hour_word = {
                1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
            }[parsed.hour % 12 or 12]
            period = (
                r"\b(?:afternoon|evening|night)\b" if parsed.hour >= 12
                else r"\bmorning\b"
            )
            numeric = re.search(
                r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})\b",
                text,
            )
            numeric_time = None
            if numeric:
                if numeric.group(1):
                    numeric_time = _clock(numeric.group(1), numeric.group(2), numeric.group(3))
                else:
                    numeric_time = _clock(numeric.group(4), numeric.group(5), None)
            spelled = (
                parsed.minute == 0
                and re.search(rf"\b{hour_word}\b", text)
                and re.search(period, text)
            )
            if numeric_time == parsed.strftime("%H:%M") or spelled:
                accepted["start_time"] = parsed.strftime("%H:%M")
        except ValueError:
            pass
    candidate_preference = candidate.get("time_preference")
    if isinstance(candidate_preference, str):
        label = candidate_preference.split(":", 1)[0]
        if label in {"morning", "afternoon", "evening", "tonight", "around", "after", "before"}:
            if re.search(rf"\b{label}\b", text):
                if candidate_preference in {"morning", "afternoon", "evening", "tonight"}:
                    accepted["time_preference"] = candidate_preference
                elif ":" in candidate_preference:
                    try:
                        anchor = time.fromisoformat(candidate_preference.split(":", 1)[1])
                        if re.search(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b\d{1,2}:\d{2}\b", text):
                            accepted["time_preference"] = f"{label}:{anchor.strftime('%H:%M')}"
                    except ValueError:
                        pass
    stated = extract_booking_details(message)
    for field in ("duration", "number_of_people"):
        value = candidate.get(field)
        if type(value) is int and value == stated.get(field):
            accepted[field] = value
    phone = candidate.get("phone_number")
    if isinstance(phone, str) and re.fullmatch(r"\d{9,11}", phone) and phone in message:
        accepted["phone_number"] = phone
    return accepted
