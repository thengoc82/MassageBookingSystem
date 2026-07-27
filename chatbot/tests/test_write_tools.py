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
        numberOfPeople=1,
        services=[{"personIndex": 0, "courseId": 1}]
    )

    response = await tool.execute(request)
    assert response.success is True
    assert response.bookingCode == "BK202607240001"

@pytest.mark.asyncio
async def test_duplicate_confirmation_prevention():
    # Setup mock with state checking (conceptual)
    pass
