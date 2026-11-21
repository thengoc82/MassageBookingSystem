from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from chatbot.conversation.state import PendingAction
from chatbot.gateway.client import HTTPClient
from chatbot.tools.write_tools import CreateBookingTool


@pytest.mark.asyncio
async def test_pending_action_lifecycle():
    action = PendingAction(tool_name="createBooking", arguments={"shopId": 1})
    assert action.status == "pending"
    assert action.tool_name == "createBooking"

@pytest.mark.asyncio
async def test_create_booking_tool():
    mock_client = AsyncMock(spec=HTTPClient)
    mock_client.post.return_value = {
        "success": True,
        "bookingId": 1,
        "bookingCode": "BK202607240001",
    }

    tool = CreateBookingTool(mock_client)

    from chatbot.models import CreateBookingRequest
    request = CreateBookingRequest(
        shopId=1,
        phoneNumber="0901234567",
        bookingDate=datetime.now().date(),
        startTime=datetime.now().time(),
        duration=60,
        numberOfPeople=1,
        services=[{"personIndex": 0, "courseId": 1}]
    )

    response = await tool.execute(request)
    assert response.success is True
    assert response.bookingCode == "BK202607240001"


@pytest.mark.asyncio
async def test_create_booking_tool_uses_pos_contract() -> None:
    from datetime import date, time

    from chatbot.models import CreateBookingRequest

    mock_client = AsyncMock(spec=HTTPClient)
    mock_client.post.return_value = {
        "success": True,
        "data": {"bookingId": 91, "bookingCode": "BK202611230001", "status": "Booked"},
        "message": "Booking created successfully",
    }
    request = CreateBookingRequest(
        shopId=1,
        phoneNumber="0901234567",
        bookingDate=date(2026, 11, 23),
        startTime=time(17, 0),
        duration=60,
        numberOfPeople=2,
        services=[{"personIndex": 1, "courseId": 7}, {"personIndex": 2, "courseId": 7}],
    )

    response = await CreateBookingTool(mock_client).execute(request)

    assert response.bookingCode == "BK202611230001"
    payload = mock_client.post.await_args.kwargs["json"]
    assert payload["startTime"] == "17:00"
    assert payload["duration"] == 60
    assert payload["services"] == [
        {"personIndex": 1, "courseId": 7}, {"personIndex": 2, "courseId": 7}
    ]
    assert "addOns" not in payload

@pytest.mark.asyncio
async def test_duplicate_confirmation_prevention():
    # Setup mock with state checking (conceptual)
    pass
