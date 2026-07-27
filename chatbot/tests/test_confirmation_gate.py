from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from chatbot.app.chat_endpoint import ChatEndpoint
from chatbot.conversation.state import ConversationPhase, ConversationState, PendingAction
from chatbot.gateway.client import HTTPClient
from chatbot.tools.registry import ToolRegistry
from chatbot.tools.write_tools import CreateBookingTool


@pytest.mark.asyncio
async def test_confirmation_gate_execution():
    # Setup
    mock_client = AsyncMock(spec=HTTPClient)
    mock_registry = MagicMock(spec=ToolRegistry)

    # Mock createBooking tool
    mock_tool = AsyncMock(spec=CreateBookingTool)
    mock_tool.is_write = True
    mock_tool.RequestModel = MagicMock()
    mock_registry.get.return_value = mock_tool


    endpoint = ChatEndpoint(http_client=mock_client, tool_registry=mock_registry)

    state = ConversationState()
    state.phase = ConversationPhase.CONFIRMING_ACTION
    state.pending_action = PendingAction(
        tool_name="createBooking",
        arguments={"shopId": 1, "phoneNumber": "0901234567"},
        status="pending",
        timestamp=datetime.now(),
    )

    # Simulate "confirm" intent
    response = await endpoint._handle_intent(
        "confirm_action", "confirm", state, "session1"
    )

    assert response.success is True
    assert state.pending_action is None
    assert state.phase == ConversationPhase.ACTION_COMPLETE


@pytest.mark.asyncio
async def test_confirmation_gate_cancellation():
    # Setup
    state = ConversationState()
    state.phase = ConversationPhase.CONFIRMING_ACTION
    state.pending_action = PendingAction(
        tool_name="createBooking",
        arguments={"shopId": 1},
        status="pending",
        timestamp=datetime.now(),
    )

    endpoint = ChatEndpoint(
        http_client=AsyncMock(spec=HTTPClient),
        tool_registry=MagicMock(spec=ToolRegistry)
    )


    # Simulate "cancel" intent
    response = await endpoint._handle_intent(
        "cancel_action", "cancel", state, "session1"
    )

    assert response.success is True
    assert state.pending_action is None
    assert state.phase == ConversationPhase.GREETING

