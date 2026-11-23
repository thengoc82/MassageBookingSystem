"""Deterministic extraction and validation of optional LLM candidates."""

from datetime import timedelta

from chatbot.conversation.booking_details import (
    extract_booking_details,
    local_today,
    matches_preference,
    preference_rank,
    validated_llm_details,
)


def test_extracts_multiple_details_and_relative_local_date() -> None:
    details = extract_booking_details(
        "Book for a couple tomorrow evening for 60 minutes. Call 0901234567"
    )
    assert details == {
        "date": (local_today() + timedelta(days=1)).isoformat(),
        "number_of_people": 2,
        "duration": 60,
        "phone_number": "0901234567",
        "time_preference": "evening",
    }


def test_flexible_time_only_matches_backend_slot_times() -> None:
    assert extract_booking_details("around 5pm")["time_preference"] == "around:17:00"
    assert extract_booking_details("around 23")["time_preference"] == "around:23:00"
    assert extract_booking_details("tomorrow at 23")["start_time"] == "23:00"
    assert "start_time" not in extract_booking_details("23pm")
    assert matches_preference("17:15", "around:17:00")
    assert not matches_preference("19:00", "around:17:00")
    assert matches_preference("18:00", "evening")
    assert not matches_preference("11:00", "evening")
    assert sorted(["16:00", "17:15", "16:45"], key=lambda value: preference_rank(value, "around:17:00")) == [
        "16:45", "17:15", "16:00",
    ]


def test_llm_candidate_cannot_invent_unstated_booking_details() -> None:
    candidate = {
        "date": "2099-01-01", "start_time": "17:00",
        "number_of_people": 3, "phone_number": "0901234567",
    }
    assert validated_llm_details("I would like a massage", candidate) == {}


def test_llm_candidate_accepts_supported_worded_time() -> None:
    assert validated_llm_details(
        "Could we do five in the afternoon?", {"start_time": "17:00"}
    ) == {"start_time": "17:00"}


def test_llm_candidate_time_must_match_customer_time() -> None:
    assert validated_llm_details(
        "Could we do 5pm?", {"start_time": "20:00"}
    ) == {}
    assert validated_llm_details(
        "Could we do 5pm?", {"start_time": "17:00"}
    ) == {"start_time": "17:00"}
    assert validated_llm_details(
        "Could we do 25:00?", {"start_time": "17:00"}
    ) == {}
