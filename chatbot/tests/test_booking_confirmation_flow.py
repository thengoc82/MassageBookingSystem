

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date, time

from chatbot.app.chat_endpoint import ChatEndpoint
from chatbot.conversation.state import ConversationState
from chatbot.nlu.models import NLUResult, Intent, Entity, EntityType
from chatbot.models import (
    SearchShopsResponse,
    ShopInfo,
    SearchCoursesResponse,
    CourseInfo,
    CourseDurationInfo,
    SearchAvailableSlotsResponse,
    SlotInfo,
    GetTherapistsResponse,
    TherapistInfo,
    CreateBookingResponse,
)
from chatbot.tools.write_tools import CreateBookingRequest


@pytest.mark.asyncio
async def test_full_booking_flow_with_therapist_selection():
    # Setup
    chat_endpoint = ChatEndpoint()

    # Mock dependencies
    chat_endpoint._session_store = AsyncMock()
    chat_endpoint._nlu = AsyncMock()
    chat_endpoint._tool_registry = MagicMock()

    # Mock session and state
    session = AsyncMock()
    state = ConversationState()
    session.conversation_state = state
    session.session_id = "test_session_123"
    chat_endpoint._session_store.get_session.return_value = session
    chat_endpoint._session_store.create_session.return_value = session

    # Correctly mock the async behavior of nlu.understand
    async def understand_side_effect(*args, **kwargs):
        return nlu_results.pop(0)

    chat_endpoint._nlu.understand = AsyncMock(side_effect=understand_side_effect)

    nlu_results = [
        NLUResult(intent=Intent.CREATE_BOOKING, entities=[]),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[Entity(type=EntityType.AREA, value="District 1")],
        ),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[
                Entity(type=EntityType.SHOP_ID, value=1, raw_text="Zen Garden Spa")
            ],
        ),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[
                Entity(
                    type=EntityType.COURSE_ID, value=101, raw_text="Swedish Massage"
                )
            ],
        ),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[
                Entity(type=EntityType.DATE, value="2027-08-10"),
                Entity(type=EntityType.TIME, value="14:00"),
                Entity(type=EntityType.DURATION, value=60),
                Entity(type=EntityType.NUMBER_OF_PEOPLE, value=1),
            ],
        ),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[
                Entity(type=EntityType.THERAPIST_ID, value=10, raw_text="Tanaka Yuki")
            ],
        ),
        NLUResult(
            intent=Intent.UNKNOWN,
            entities=[Entity(type=EntityType.PHONE_NUMBER, value="0909090909")],
        ),
        NLUResult(intent=Intent.CONFIRMATION, entities=[]),
    ]

    # Mock tool calls
    search_shops_tool = AsyncMock()
    search_shops_tool.execute = AsyncMock(
        return_value=SearchShopsResponse(
            success=True,
            data=[
                ShopInfo(
                    shopId=1,
                    shopName="Zen Garden Spa",
                    address="District 1",
                    phoneNumber="123-456-7890",
                    status="Open",
                    openTime=time(9, 0),
                    closeTime=time(22, 0),
                )
            ],
            message="Success",
        )
    )

    search_courses_tool = AsyncMock()
    search_courses_tool.execute = AsyncMock(
        return_value=SearchCoursesResponse(
            success=True,
            data=[
                CourseInfo(
                    courseId=101,
                    courseName="Swedish Massage",
                    courseType="main",
                    durations=[CourseDurationInfo(duration=60, price=500000)],
                )
            ],
            message="Success",
        )
    )

    search_slots_tool = AsyncMock()
    search_slots_tool.execute = AsyncMock(
        return_value=SearchAvailableSlotsResponse(
            success=True,
            data=[
                SlotInfo(
                    startTime=time(14, 0),
                    endTime=time(15, 0),
                    availableCapacity=5,
                    availableTherapistIds=[10],
                )
            ],
            message="Success",
        )
    )

    get_therapists_tool = AsyncMock()
    get_therapists_tool.execute = AsyncMock(
        return_value=GetTherapistsResponse(
            success=True,
            data=[
                TherapistInfo(
                    therapistId=10, name="Tanaka Yuki", gender="Male", isAvailable=True
                )
            ],
            message="Success",
        )
    )

    create_booking_tool = AsyncMock()
    create_booking_tool.execute.return_value = CreateBookingResponse(
        success=True,
        bookingId=123,
        bookingCode="XYZ-123",
        message="Booking confirmed!",
    )

    chat_endpoint._tool_registry.get.side_effect = lambda name: {
        "searchShops": search_shops_tool,
        "searchCourses": search_courses_tool,
        "searchAvailableSlots": search_slots_tool,
        "getTherapists": get_therapists_tool,
        "createBooking": create_booking_tool,
    }.get(name)

    chat_endpoint._initialized = True

    # Simulate conversation
    messages = [
        "book a massage",
        "District 1",
        "Zen Garden Spa",
        "Swedish Massage",
        "tomorrow at 2pm for 60 minutes, just me",
        "Tanaka Yuki",
        "my phone is 0909090909",
        "yes",
    ]

    request_mock = MagicMock()
    request_mock.session_id = "test_session_123"
    request_mock.user_id = "test_user"

    final_response = None
    for msg in messages:
        request_mock.message = msg
        final_response = await chat_endpoint.process_message(request_mock)

    # Assertions
    create_booking_tool.execute.assert_called_once()
    call_args = create_booking_tool.execute.call_args[0][0]

    assert isinstance(call_args, CreateBookingRequest)
    assert call_args.shopId == 1
    assert call_args.services[0].courseId == 101
    assert call_args.therapistId == 10
    assert call_args.phoneNumber == "0909090909"
    assert call_args.bookingDate == date(2027, 8, 10)
    assert call_args.startTime == time(14, 0)
    assert call_args.numberOfPeople == 1

    assert final_response.success is True
    assert "Booking confirmed!" in final_response.message

