"""Preferred-time selection and explicit booking confirmation through the chat endpoint."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.conversation.booking_details import local_today
from chatbot.conversation.state import BookingContext, ConversationPhase, ConversationState
from chatbot.gateway.errors import TimeSlotUnavailableError
from chatbot.models import CreateBookingRequest, CreateBookingResponse, SearchAvailableSlotsResponse
from chatbot.session.store import SessionData
from chatbot.tools.write_tools import CreateBookingTool

BOOKING_DATE = (local_today() + timedelta(days=2)).isoformat()


def slot_response(*entries: tuple[str, int]) -> SearchAvailableSlotsResponse:
    return SearchAvailableSlotsResponse(
        success=True,
        data=[
            {"startTime": start, "endTime": "20:00", "availableCapacity": capacity}
            for start, capacity in entries
        ],
        message="Success",
    )


def make_endpoint(
    initial: SearchAvailableSlotsResponse,
    refreshed: SearchAvailableSlotsResponse | None = None,
) -> tuple[ChatEndpoint, dict[str, SessionData], MagicMock, MagicMock]:
    state = ConversationState(
        phase=ConversationPhase.COLLECTING_INFO,
        booking_context=BookingContext(
            shop_id=1,
            shop_name="Shinjuku Store",
            course_id=7,
            course_name="Full Body Massage",
            duration=60,
            date=BOOKING_DATE,
            number_of_people=2,
        ),
    )
    sessions = {"s1": SessionData(session_id="s1", conversation_state=state.model_dump())}
    store = MagicMock()

    async def get_session(session_id: str) -> SessionData | None:
        return SessionData.model_validate_json(sessions[session_id].model_dump_json())

    async def save_session(session: SessionData) -> None:
        sessions[session.session_id] = SessionData.model_validate_json(session.model_dump_json())

    store.get_session = AsyncMock(side_effect=get_session)
    store.save_session = AsyncMock(side_effect=save_session)

    slots_tool = MagicMock()
    calls = 0

    async def availability(_request):
        nonlocal calls
        calls += 1
        return initial if calls == 1 else (refreshed or initial)

    slots_tool.execute = AsyncMock(side_effect=availability)
    create_tool = MagicMock()
    create_tool.RequestModel = CreateBookingRequest
    create_tool.execute = AsyncMock(return_value=CreateBookingResponse(
        success=True, bookingId=91, bookingCode="BK202611230001", message="Booked"
    ))
    registry = MagicMock()
    registry.get.side_effect = lambda name: {
        "searchAvailableSlots": slots_tool,
        "createBooking": create_tool,
    }.get(name)
    endpoint = ChatEndpoint(session_store=store, tool_registry=registry)
    endpoint._initialized = True
    return endpoint, sessions, slots_tool, create_tool


async def send(endpoint: ChatEndpoint, message: str):
    return await endpoint.process_message(ChatRequest(message=message, session_id="s1"))


def saved_state(sessions: dict[str, SessionData]) -> ConversationState:
    return ConversationState(**sessions["s1"].conversation_state)


@pytest.mark.asyncio
async def test_exact_preferred_time_is_offered_once() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("16:45", 2), ("17:00", 2), ("17:15", 2))
    )

    response = await send(endpoint, "5pm")

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert "17:00" in response.message
    assert "confirm" in response.message.lower()
    assert "which time works" not in response.message.lower()
    assert saved_state(sessions).offered_slot_time == "17:00"
    assert slots_tool.execute.await_count == 1
    assert slots_tool.execute.await_args.args[0].startTime is None
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("reply,normalized", [
    ("12pm", "12:00"), ("12 pm", "12:00"), ("12:00", "12:00"),
    ("23", "23:00"), ("23:00", "23:00"),
])
async def test_time_reply_normalizes_and_checks_flask(reply: str, normalized: str) -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response((normalized, 2)))

    response = await send(endpoint, reply)

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved_state(sessions).booking_context.start_time == normalized
    assert saved_state(sessions).offered_slot_time == normalized
    assert normalized in response.message
    assert slots_tool.execute.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["15", "15m", "15 minutes"])
async def test_duration_reply_advances_without_repeating_question(reply: str) -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response())
    state = saved_state(sessions)
    state.booking_context.duration = None
    state.booking_context.date = None
    state.booking_context.course_duration_options = [15, 30]
    sessions["s1"].conversation_state = state.model_dump()

    response = await send(endpoint, reply)

    assert saved_state(sessions).booking_context.duration == 15
    assert "what date" in response.message.lower()
    slots_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_date_and_bare_time_correction_rechecks_new_date_and_time() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response(("17:00", 2)))
    new_date = (date.fromisoformat(BOOKING_DATE) + timedelta(days=1)).isoformat()
    slots_tool.execute.side_effect = [
        slot_response(("17:00", 2)), slot_response(("23:00", 2)),
    ]
    await send(endpoint, "5pm")

    changed = await send(endpoint, f"Actually {new_date} at 23")

    assert saved_state(sessions).booking_context.date == new_date
    assert saved_state(sessions).booking_context.start_time == "23:00"
    assert saved_state(sessions).offered_slot_time == "23:00"
    assert "23:00" in changed.message and new_date in changed.message
    assert slots_tool.execute.await_count == 2
    request = slots_tool.execute.await_args.args[0]
    assert request.date.isoformat() == new_date
    assert request.shopId == 1
    assert request.courseIds == "7"
    assert request.duration == 60
    assert request.numberOfPeople == 2


@pytest.mark.asyncio
async def test_invalid_bare_time_clarifies_without_search() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response())

    response = await send(endpoint, "25")

    assert "valid time" in response.message.lower()
    assert saved_state(sessions).booking_context.start_time is None
    slots_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_date_clarifies_without_search() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response())
    state = saved_state(sessions)
    state.booking_context.date = None
    state.booking_context.start_time = None
    sessions["s1"].conversation_state = state.model_dump()

    response = await send(endpoint, "2026-13-40")

    assert "valid date" in response.message.lower()
    assert saved_state(sessions).booking_context.date is None
    slots_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_malformed_time_after_no_slots_clarifies_without_false_availability() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response())
    await send(endpoint, "23:00")
    queries = slots_tool.execute.await_count

    response = await send(endpoint, "12;00")

    assert "valid time" in response.message.lower()
    assert "unavailable" not in response.message.lower()
    assert slots_tool.execute.await_count == queries


@pytest.mark.asyncio
async def test_unavailable_preference_suggests_nearby_available_slots() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("15:00", 2), ("16:45", 2), ("17:15", 2), ("18:00", 2),
                      ("17:00", 1))
    )

    response = await send(endpoint, "5pm")

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert "17:00" in response.message
    assert "unavailable" in response.message.lower()
    assert "16:45" in response.message
    assert "17:15" in response.message
    assert "18:00" in response.message
    assert "15:00" not in response.message
    assert saved_state(sessions).offered_slot_time is None
    assert slots_tool.execute.await_count == 1
    create_tool.execute.assert_not_awaited()

    ambiguous_yes = await send(endpoint, "yes")
    assert ambiguous_yes.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved_state(sessions).offered_slot_time is None
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_rechecks_explicit_alternative_before_offering_it() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("16:45", 2), ("17:15", 2))
    )
    await send(endpoint, "5pm")

    offered = await send(endpoint, "17:15")
    assert "confirm" in offered.message.lower()
    assert saved_state(sessions).offered_slot_time == "17:15"
    assert slots_tool.execute.await_count == 2

    accepted = await send(endpoint, "yes")
    assert accepted.phase == ConversationPhase.COLLECTING_PHONE
    assert "phone" in accepted.message.lower()
    assert saved_state(sessions).booking_context.start_time == "17:15"
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_yes_offers_the_only_suggested_alternative_for_confirmation() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(slot_response(("17:15", 2)))
    suggestion = await send(endpoint, "5pm")
    assert "17:15" in suggestion.message
    assert saved_state(sessions).offered_slot_time is None

    offered = await send(endpoint, "yes")
    assert offered.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved_state(sessions).offered_slot_time == "17:15"
    accepted = await send(endpoint, "yes")
    assert accepted.phase == ConversationPhase.COLLECTING_PHONE
    assert saved_state(sessions).booking_context.start_time == "17:15"
    assert slots_tool.execute.await_count == 2
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_single_suggestion_is_rechecked_before_it_is_offered() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("17:15", 2)), slot_response()
    )
    await send(endpoint, "5pm")

    response = await send(endpoint, "yes")

    assert slots_tool.execute.await_count == 2
    assert saved_state(sessions).offered_slot_time is None
    assert "17:15 is unavailable" in response.message
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["yes please", "that time works", "sounds good"])
async def test_natural_slot_confirmation(reply: str) -> None:
    endpoint, sessions, _, create_tool = make_endpoint(slot_response(("17:00", 2)))
    await send(endpoint, "5pm")

    accepted = await send(endpoint, reply)

    assert accepted.phase == ConversationPhase.COLLECTING_PHONE
    assert saved_state(sessions).slot_confirmed is True
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_natural_final_confirmation_still_uses_write_gate() -> None:
    endpoint, sessions, _, create_tool = make_endpoint(slot_response(("17:00", 2)))
    await send(endpoint, "5pm")
    await send(endpoint, "yes please")
    await send(endpoint, "0901234567")
    create_tool.execute.assert_not_awaited()

    confirmed = await send(endpoint, "yes please")

    assert confirmed.phase == ConversationPhase.BOOKING_COMPLETE
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_unlisted_time_is_not_offered_as_an_available_slot() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("16:45", 2), ("17:15", 2))
    )
    await send(endpoint, "5pm")

    response = await send(endpoint, "17:20")

    assert "17:20 is unavailable" in response.message
    assert saved_state(sessions).offered_slot_time is None
    assert slots_tool.execute.await_count == 2
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_slots_can_change_date_without_losing_booking_details() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response())
    slots_tool.execute.side_effect = [slot_response(), slot_response(("17:00", 2))]
    unavailable = await send(endpoint, "5pm")
    assert "choose another date" in unavailable.message.lower()

    next_date = (date.fromisoformat(BOOKING_DATE) + timedelta(days=1)).isoformat()
    response = await send(endpoint, next_date)

    assert "17:00" in response.message
    assert "confirm" in response.message.lower()
    assert saved_state(sessions).booking_context.date == next_date
    assert saved_state(sessions).booking_context.shop_id == 1
    assert saved_state(sessions).booking_context.course_id == 7
    assert slots_tool.execute.await_count == 2


@pytest.mark.asyncio
async def test_rejection_can_choose_another_slot() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(
        slot_response(("16:45", 2), ("17:15", 2), ("18:00", 2))
    )
    await send(endpoint, "5pm")
    await send(endpoint, "17:15")

    rejected = await send(endpoint, "no")
    assert rejected.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved_state(sessions).offered_slot_time is None
    assert "16:45" in rejected.message

    alternative = await send(endpoint, "16:45")
    assert saved_state(sessions).offered_slot_time == "16:45"
    assert "confirm" in alternative.message.lower()
    assert slots_tool.execute.await_count == 3


@pytest.mark.asyncio
async def test_reject_and_choose_another_slot_in_one_reply() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(
        slot_response(("17:00", 2), ("17:15", 2))
    )
    await send(endpoint, "5pm")

    response = await send(endpoint, "no, 17:15")

    assert "17:15" in response.message
    assert "confirm" in response.message.lower()
    assert saved_state(sessions).offered_slot_time == "17:15"
    assert slots_tool.execute.await_count == 2


@pytest.mark.asyncio
async def test_changes_preference_with_fresh_availability() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(
        slot_response(("16:45", 2), ("17:15", 2), ("17:30", 2), ("18:00", 2))
    )
    await send(endpoint, "5pm")

    response = await send(endpoint, "try 6pm")

    assert "18:00" in response.message
    assert saved_state(sessions).booking_context.start_time == "18:00"
    assert saved_state(sessions).offered_slot_time == "18:00"
    assert slots_tool.execute.await_count == 2


@pytest.mark.asyncio
async def test_availability_change_blocks_creation_and_preserves_booking_context() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("17:00", 2), ("17:15", 2)),
        slot_response(("17:15", 2)),
    )
    await send(endpoint, "5pm")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")

    response = await send(endpoint, "yes")

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert "no longer available" in response.message.lower()
    assert "17:15" in response.message
    assert slots_tool.execute.await_count == 2
    assert saved_state(sessions).booking_context.phone_number == "0901234567"
    assert saved_state(sessions).booking_context.shop_id == 1
    assert saved_state(sessions).pending_action is None
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_booking_is_created_only_after_final_confirmation() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(slot_response(("17:00", 2)))
    await send(endpoint, "5pm")
    await send(endpoint, "yes")
    confirmation = await send(endpoint, "0901234567")

    assert confirmation.phase == ConversationPhase.CONFIRMING_ACTION
    assert "confirm" in confirmation.message.lower()
    assert saved_state(sessions).pending_action is not None
    create_tool.execute.assert_not_awaited()
    assert slots_tool.execute.await_count == 1

    booked = await send(endpoint, "yes")

    assert booked.phase == ConversationPhase.BOOKING_COMPLETE
    assert "BK202611230001" in booked.message
    request = create_tool.execute.await_args.args[0]
    assert request.shopId == 1
    assert request.bookingDate.isoformat() == BOOKING_DATE
    assert request.startTime.strftime("%H:%M") == "17:00"
    assert request.duration == 60
    assert request.numberOfPeople == 2
    assert [(item.personIndex, item.courseId) for item in request.services] == [(1, 7), (2, 7)]
    assert saved_state(sessions).pending_action is None
    assert slots_tool.execute.await_count == 2

    await send(endpoint, "yes")
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_final_rejection_does_not_create_booking() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(slot_response(("17:00", 2)))
    await send(endpoint, "5pm")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")

    response = await send(endpoint, "no")

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved_state(sessions).pending_action is None
    assert slots_tool.execute.await_count == 1
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_pos_race_returns_to_slot_choices_without_booking() -> None:
    endpoint, sessions, slots_tool, create_tool = make_endpoint(
        slot_response(("17:00", 2), ("17:15", 2))
    )
    slots_tool.execute.side_effect = [
        slot_response(("17:00", 2), ("17:15", 2)),
        slot_response(("17:00", 2), ("17:15", 2)),
        slot_response(("17:15", 2)),
    ]
    create_tool.execute.side_effect = TimeSlotUnavailableError()
    await send(endpoint, "5pm")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")

    response = await send(endpoint, "yes")

    assert response.phase == ConversationPhase.SEARCHING_SLOTS
    assert "17:15" in response.message
    assert saved_state(sessions).pending_action is None
    assert saved_state(sessions).booking_context.course_id == 7
    assert slots_tool.execute.await_count == 3
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_booking_uses_existing_pos_tool() -> None:
    endpoint, sessions, slots_tool, _ = make_endpoint(slot_response(("17:00", 2)))
    http_client = MagicMock()
    http_client.post = AsyncMock(return_value={
        "success": True,
        "data": {"bookingId": 91, "bookingCode": "BK202611230001"},
        "message": "Booking created successfully",
    })
    create_tool = CreateBookingTool(http_client)
    registry = endpoint._tool_registry
    registry.get.side_effect = lambda name: {
        "searchAvailableSlots": slots_tool,
        "createBooking": create_tool,
    }.get(name)

    await send(endpoint, "5pm")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    response = await send(endpoint, "yes")

    assert response.phase == ConversationPhase.BOOKING_COMPLETE
    assert "BK202611230001" in response.message
    http_client.post.assert_awaited_once()
    assert http_client.post.await_args.args[0] == "/bookings"
    payload = http_client.post.await_args.kwargs["json"]
    assert payload["startTime"] == "17:00"
    assert payload["duration"] == 60
    assert payload["numberOfPeople"] == 2
    assert payload["services"] == [
        {"personIndex": 1, "courseId": 7},
        {"personIndex": 2, "courseId": 7},
    ]
    assert saved_state(sessions).booking_context.shop_id == 1
