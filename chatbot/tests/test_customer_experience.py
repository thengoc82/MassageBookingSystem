"""Customer journeys through the same chat and Flask tool path."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from chatbot.app.chat_endpoint import ChatRequest
from chatbot.conversation.booking_details import local_today
from chatbot.conversation.state import ConversationPhase, ConversationState
from chatbot.gateway.errors import GatewayTimeoutError
from chatbot.models import (
    CreateBookingRequest,
    CreateBookingResponse,
    FAQCitation,
    FAQItem,
    FAQSearchResponse,
    LookupBookingResponse,
    SearchAvailableSlotsResponse,
)
from chatbot.tests.test_shop_selection_flow import COURSES, make_endpoint


def setup_journey(slots: list[tuple[str, int]]):
    sessions = {}
    endpoint, registry = make_endpoint(sessions, courses=COURSES)
    endpoint._settings.openai_api_key = None
    shops_tool = registry.get("searchShops")
    courses_tool = registry.get("searchCourses")
    slots_tool = registry.get("searchAvailableSlots")
    slots_tool.execute = AsyncMock(return_value=SearchAvailableSlotsResponse(
        success=True, message="Success",
        data=[
            {"startTime": start, "endTime": "21:00", "availableCapacity": capacity}
            for start, capacity in slots
        ],
    ))
    create_tool = MagicMock()
    create_tool.RequestModel = CreateBookingRequest
    create_tool.execute = AsyncMock(return_value=CreateBookingResponse(
        success=True, bookingId=91, bookingCode="BK202611230001"
    ))
    faq_tool = MagicMock()
    faq_tool.execute = AsyncMock(return_value=FAQSearchResponse(
        success=True, message="Found", data=[FAQItem(
            content="Couples may book together.", score=0.9,
            citation=FAQCitation(source_file="faq.md", document_title="FAQ"),
        )],
    ))
    registry.get.side_effect = lambda name: {
        "searchShops": shops_tool, "searchCourses": courses_tool,
        "searchAvailableSlots": slots_tool, "createBooking": create_tool,
        "faqSearch": faq_tool,
    }.get(name)
    registry.has.side_effect = lambda name: name == "faqSearch"
    return endpoint, sessions, slots_tool, create_tool


async def send(endpoint, message: str):
    return await endpoint.process_message(ChatRequest(message=message, session_id="s1"))


def saved(sessions):
    return ConversationState(**sessions["s1"].conversation_state)


@pytest.mark.asyncio
async def test_combined_details_skip_known_questions_and_confirm_once() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([
        ("17:00", 2), ("18:00", 2), ("11:00", 2),
    ])
    first = await send(
        endpoint,
        "Book Full Body Massage at Shinjuku Store for a couple tomorrow evening "
        "for 15m, phone 0901234567",
    )
    assert first.phase == ConversationPhase.SEARCHING_SLOTS
    assert "17:00" in first.message and "18:00" in first.message
    assert "11:00" not in first.message
    assert first.booking_progress["details"]["phone"] == "0901234567"
    assert first.booking_progress["missing"] == ["time"]
    assert slots_tool.execute.await_args.args[0].numberOfPeople == 2

    offered = await send(endpoint, "18:00")
    assert offered.phase == ConversationPhase.SEARCHING_SLOTS
    final = await send(endpoint, "yes")
    assert final.phase == ConversationPhase.CONFIRMING_ACTION
    assert final.booking_progress["requires_confirmation"] is True
    create_tool.execute.assert_not_awaited()

    booked = await send(endpoint, "yes")
    assert booked.phase == ConversationPhase.BOOKING_COMPLETE
    assert booked.booking_progress["details"]["booking_code"] == "BK202611230001"
    assert create_tool.execute.await_count == 1
    request = create_tool.execute.await_args.args[0]
    assert request.phoneNumber == "0901234567"
    assert request.numberOfPeople == 2
    assert request.startTime.strftime("%H:%M") == "18:00"
    assert saved(sessions).pending_action is None


@pytest.mark.asyncio
async def test_corrections_replace_pending_booking_and_recheck_slots() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([
        ("17:00", 3), ("18:00", 3),
    ])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    assert saved(sessions).pending_action is not None

    changed = await send(endpoint, "Actually make it 3 people")
    assert changed.phase == ConversationPhase.SEARCHING_SLOTS
    assert changed.booking_progress["details"]["people"] == 3
    assert saved(sessions).pending_action is None
    assert slots_tool.execute.await_args.args[0].numberOfPeople == 3
    create_tool.execute.assert_not_awaited()

    await send(endpoint, "yes")
    revised = await send(endpoint, "Actually use 0987654321")
    assert revised.phase == ConversationPhase.CONFIRMING_ACTION
    assert "0987654321" in revised.message
    create_tool.execute.assert_not_awaited()
    await send(endpoint, "yes")
    request = create_tool.execute.await_args.args[0]
    assert request.numberOfPeople == 3
    assert request.phoneNumber == "0987654321"
    assert create_tool.execute.await_count == 1


@pytest.mark.asyncio
async def test_faq_preserves_offered_slot_and_resumes_exact_question() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    faq = await send(endpoint, "Do you offer services for couples?")
    assert faq.phase == ConversationPhase.SEARCHING_SLOTS
    assert "Would you like 17:00?" in faq.message
    assert saved(sessions).offered_slot_time == "17:00"
    assert saved(sessions).booking_context.number_of_people == 2
    create_tool.execute.assert_not_awaited()
    resumed = await send(endpoint, "yes")
    assert resumed.phase == ConversationPhase.COLLECTING_PHONE


@pytest.mark.asyncio
async def test_faq_at_final_confirmation_preserves_write_gate() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    faq = await send(endpoint, "Do you offer services for couples?")
    assert faq.phase == ConversationPhase.CONFIRMING_ACTION
    assert faq.booking_progress["requires_confirmation"] is True
    assert "tell me what to change" in faq.message
    create_tool.execute.assert_not_awaited()
    confirmed = await send(endpoint, "yes")
    assert confirmed.phase == ConversationPhase.BOOKING_COMPLETE
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_shop_keeps_other_preferences() -> None:
    endpoint, sessions, _, _ = setup_journey([])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm")
    await send(endpoint, "Shinjuku Store")
    changed = await send(endpoint, "change shop to Shibuya Store")
    state = saved(sessions)
    assert changed.phase == ConversationPhase.SEARCHING_COURSES
    assert state.booking_context.shop_name == "Shibuya Store"
    assert state.booking_context.number_of_people == 2
    assert state.booking_context.start_time == "17:00"
    assert state.booking_context.course_id is None


@pytest.mark.asyncio
async def test_invalid_party_size_keeps_question_pending() -> None:
    endpoint, sessions, _, create_tool = setup_journey([])
    await send(endpoint, "Book a massage tomorrow at 5pm")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage 15m")
    reply = await send(endpoint, "0")
    assert reply.phase == ConversationPhase.COLLECTING_INFO
    assert "greater than zero" in reply.message
    assert saved(sessions).booking_context.number_of_people is None
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_start_over_clears_pending_action_without_booking() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    reset = await send(endpoint, "start over")
    assert reset.phase == ConversationPhase.GREETING
    assert reset.booking_progress["active"] is False
    assert saved(sessions).pending_action is None
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_go_back_to_correct_phone_does_not_repeat_slot_question() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    slot_queries = slots_tool.execute.await_count
    back = await send(endpoint, "go back")
    assert back.phase == ConversationPhase.COLLECTING_INFO
    assert saved(sessions).slot_confirmed is True

    changed = await send(endpoint, "Use 0987654321 instead")
    assert changed.phase == ConversationPhase.CONFIRMING_ACTION
    assert "0987654321" in changed.message
    assert slots_tool.execute.await_count == slot_queries
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_two_simultaneous_confirmations_execute_once() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")

    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_create(request):
        started.set()
        await release.wait()
        return CreateBookingResponse(
            success=True, bookingId=91, bookingCode="BK202611230001"
        )

    create_tool.execute.side_effect = slow_create
    first = asyncio.create_task(send(endpoint, "yes"))
    await started.wait()
    second = asyncio.create_task(send(endpoint, "yes"))
    await asyncio.sleep(0)
    release.set()
    replies = await asyncio.gather(first, second)
    assert sum(reply.phase == ConversationPhase.BOOKING_COMPLETE for reply in replies) == 2
    assert create_tool.execute.await_count == 1
    assert saved(sessions).pending_action is None


@pytest.mark.asyncio
async def test_uncertain_backend_write_requires_lookup_before_retry() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    create_tool.execute.side_effect = GatewayTimeoutError()

    unknown = await send(endpoint, "yes")
    assert unknown.phase == ConversationPhase.BOOKING_UNCERTAIN
    assert unknown.booking_progress["requires_confirmation"] is False
    assert "couldn't verify" in unknown.message
    assert saved(sessions).pending_action is None
    again = await send(endpoint, "yes")
    assert again.phase == ConversationPhase.BOOKING_UNCERTAIN
    create_tool.execute.assert_awaited_once()

    lookup = MagicMock()
    lookup.execute = AsyncMock(return_value=LookupBookingResponse(
        success=True, message="Success", data=[{
            "bookingId": 91, "bookingCode": "BK202611230001",
            "shopId": 1, "shopName": "Shinjuku Store", "phoneNumber": "0901234567",
            "bookingDate": saved(sessions).booking_context.date,
            "startTime": "17:00", "numberOfPeople": 2, "status": "Booked",
        }],
    ))
    previous_get = endpoint._tool_registry.get.side_effect
    endpoint._tool_registry.get.side_effect = lambda name: (
        lookup if name == "lookupBooking" else previous_get(name)
    )
    challenge = await send(endpoint, "check my booking")
    assert "verification code" in challenge.message
    assert "Flask API terminal" in challenge.message
    verified = await send(endpoint, "123456")
    assert verified.phase == ConversationPhase.BOOKING_COMPLETE
    assert "BK202611230001" in verified.message
    assert lookup.execute.await_args.args[0].accessToken == 'verified-token'
    assert ['user', '[verification code]'] in sessions['s1'].conversation_history
    assert ['user', '123456'] not in sessions['s1'].conversation_history
    another = await endpoint.process_message(ChatRequest(message='check my booking 0901234568', session_id='s2'))
    assert 'verification code' in another.message
    assert ConversationState(**sessions['s2'].conversation_state).lookup_access_token is None
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_availability_timeout_keeps_details_and_retries() -> None:
    endpoint, sessions, slots_tool, _ = setup_journey([("17:00", 2)])
    slots_tool.execute.side_effect = GatewayTimeoutError()

    failed = await send(
        endpoint,
        "Book Full Body Massage at Shinjuku Store for 2 people tomorrow "
        "at 5pm for 15m, phone 0901234567",
    )
    assert failed.success is False
    assert failed.phase == ConversationPhase.SEARCHING_SLOTS
    assert "details are saved" in failed.message
    assert failed.booking_progress["details"]["phone"] == "0901234567"
    assert saved(sessions).booking_context.course_name == "Full Body Massage"

    slots_tool.execute.side_effect = None
    retried = await send(endpoint, "retry")
    assert retried.success is True
    assert retried.phase == ConversationPhase.SEARCHING_SLOTS
    assert "17:00" in retried.message
    assert slots_tool.execute.await_count == 2


@pytest.mark.asyncio
async def test_lookup_timeout_during_booking_preserves_draft() -> None:
    endpoint, sessions, _, _ = setup_journey([("17:00", 2)])
    await send(
        endpoint,
        "Book Full Body Massage at Shinjuku Store for 2 people tomorrow "
        "at 5pm for 15m, phone 0901234567",
    )
    lookup = MagicMock()
    lookup.execute = AsyncMock(side_effect=GatewayTimeoutError())
    previous_get = endpoint._tool_registry.get.side_effect
    endpoint._tool_registry.get.side_effect = lambda name: (
        lookup if name == "lookupBooking" else previous_get(name)
    )

    challenge = await send(endpoint, "check my booking BK202611230001")
    assert "verification code" in challenge.message
    failed = await send(endpoint, "123456")
    assert failed.success is False
    assert failed.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved(sessions).booking_context.course_name == "Full Body Massage"
    assert saved(sessions).lookup_code == "BK202611230001"
    assert "17:00" in failed.message


@pytest.mark.asyncio
async def test_transcript_duration_time_and_repeated_date_replay() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([])
    endpoint._rate_limiter = MagicMock()
    tomorrow = (local_today() + timedelta(days=1)).isoformat()

    async def availability(request):
        if request.date.isoformat() == tomorrow:
            return SearchAvailableSlotsResponse(
                success=True, message="Success",
                data=[{"startTime": "12:00", "endTime": "12:15", "availableCapacity": 1}],
            )
        return SearchAvailableSlotsResponse(success=True, message="Success", data=[])

    slots_tool.execute.side_effect = availability
    await send(endpoint, "book a massage")
    await send(endpoint, "1")
    service = await send(endpoint, "full body")
    assert "duration" in service.message.lower()
    duration = await send(endpoint, "15")
    assert "what date" in duration.message.lower()
    assert saved(sessions).booking_context.duration == 15
    await send(endpoint, "today")
    invalid = await send(endpoint, "23pm")
    assert "valid time" in invalid.message.lower()
    assert slots_tool.execute.await_count == 0
    time_reply = await send(endpoint, "23")
    assert "how many people" in time_reply.message.lower()
    assert saved(sessions).booking_context.start_time == "23:00"
    no_slots = await send(endpoint, "1 person")
    assert "no slots" in no_slots.message.lower()
    assert slots_tool.execute.await_count == 1

    changed = await send(endpoint, "tomorrow")
    assert saved(sessions).booking_context.date == tomorrow
    assert "12:00" in changed.message
    assert slots_tool.execute.await_count == 2
    repeated = await send(endpoint, "tomorrow")
    assert "12:00" in repeated.message
    assert "confirm the offered slot" not in repeated.message.lower()
    assert slots_tool.execute.await_count == 3

    noon = await send(endpoint, "12pm")
    assert "12:00" in noon.message and tomorrow in noon.message
    assert saved(sessions).offered_slot_time == "12:00"
    await send(endpoint, "yes")
    assert saved(sessions).slot_confirmed is True
    assert saved(sessions).booking_context.date == tomorrow
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_correction_at_final_confirmation_rechecks_and_preserves_phone() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([
        ("17:00", 2), ("18:00", 2),
    ])
    await send(
        endpoint,
        "Book Full Body Massage at Shinjuku Store for 2 people tomorrow "
        "at 5pm for 15m, phone 0901234567",
    )
    await send(endpoint, "yes")
    assert saved(sessions).phase == ConversationPhase.CONFIRMING_ACTION

    new_date = (local_today() + timedelta(days=2)).isoformat()
    revised = await send(endpoint, f"Actually {new_date} at 6pm")
    state = saved(sessions)
    assert revised.phase == ConversationPhase.SEARCHING_SLOTS
    assert state.booking_context.date == new_date
    assert state.booking_context.start_time == "18:00"
    assert state.booking_context.phone_number == "0901234567"
    assert state.pending_action is None
    assert state.offered_slot_time == "18:00"
    assert slots_tool.execute.await_count == 2
    assert slots_tool.execute.await_args.args[0].date.isoformat() == new_date
    create_tool.execute.assert_not_awaited()

    await send(endpoint, "yes")
    assert saved(sessions).phase == ConversationPhase.CONFIRMING_ACTION
    assert slots_tool.execute.await_count == 2
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_duration_correction_refreshes_availability() -> None:
    endpoint, sessions, slots_tool, create_tool = setup_journey([("17:00", 2)])
    await send(
        endpoint,
        "Book Full Body Massage at Shinjuku Store for 2 people tomorrow "
        "at 5pm for 15m, phone 0901234567",
    )

    revised = await send(endpoint, "Actually 30 minutes")

    assert revised.phase == ConversationPhase.SEARCHING_SLOTS
    assert saved(sessions).booking_context.duration == 30
    assert saved(sessions).booking_context.phone_number == "0901234567"
    assert saved(sessions).offered_slot_time == "17:00"
    assert slots_tool.execute.await_count == 2
    assert slots_tool.execute.await_args.args[0].duration == 30
    create_tool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_unexpected_write_error_does_not_offer_duplicate_submission() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await send(endpoint, "Book a massage for 2 people tomorrow at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")
    create_tool.execute.side_effect = RuntimeError("response lost")

    unknown = await send(endpoint, "yes")
    assert unknown.phase == ConversationPhase.BOOKING_UNCERTAIN
    assert unknown.booking_progress["requires_confirmation"] is False
    assert saved(sessions).booking_context.phone_number == "0901234567"
    await send(endpoint, "yes")
    create_tool.execute.assert_awaited_once()
