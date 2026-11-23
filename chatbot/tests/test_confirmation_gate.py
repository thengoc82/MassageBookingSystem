"""The final booking confirmation remains a server-side write gate."""

from datetime import date, timedelta

import pytest
from chatbot.app.chat_endpoint import ChatRequest
from chatbot.conversation.state import ConversationPhase, ConversationState
from chatbot.tests.test_customer_experience import setup_journey


async def send(endpoint, message: str):
    return await endpoint.process_message(ChatRequest(message=message, session_id="s1"))


async def ready_to_confirm(endpoint) -> None:
    booking_date = (date.today() + timedelta(days=2)).isoformat()
    await send(endpoint, f"Book a massage for 2 people on {booking_date} at 5pm for 15m")
    await send(endpoint, "Shinjuku Store")
    await send(endpoint, "Full Body Massage")
    await send(endpoint, "yes")
    await send(endpoint, "0901234567")


@pytest.mark.asyncio
async def test_confirmation_gate_execution() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await ready_to_confirm(endpoint)
    state = ConversationState(**sessions["s1"].conversation_state)
    assert state.phase == ConversationPhase.CONFIRMING_ACTION
    assert state.pending_action is not None
    create_tool.execute.assert_not_awaited()

    confirmed = await send(endpoint, "yes")
    assert confirmed.phase == ConversationPhase.BOOKING_COMPLETE
    create_tool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmation_gate_cancellation() -> None:
    endpoint, sessions, _, create_tool = setup_journey([("17:00", 2)])
    await ready_to_confirm(endpoint)
    cancelled = await send(endpoint, "no")
    assert cancelled.phase == ConversationPhase.SEARCHING_SLOTS
    assert ConversationState(**sessions["s1"].conversation_state).pending_action is None
    create_tool.execute.assert_not_awaited()
