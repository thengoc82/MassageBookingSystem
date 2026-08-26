# chatbot/tests/test_regression.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.nlu.models import NLUResult, Entity, EntityType, Intent
from chatbot.tests.test_chat_endpoint import initialized_endpoint

@pytest.mark.asyncio
async def test_regression_set_known_items_not_awaited(initialized_endpoint: ChatEndpoint) -> None:
    """
    Regression test for the bug where `set_known_items` was awaited.
    """
    endpoint = await initialized_endpoint
    session_id = "regression-test"

    # Mock the stateful session store behavior for this test
    state_box: dict = {}
    async def get_session(_sid: str):
        from chatbot.conversation.state import ConversationState
        if "state" not in state_box:
            state_box["state"] = ConversationState()
        return MagicMock(session_id=session_id, conversation_state=state_box["state"])

    async def save_session(session) -> None:
        state_box["state"] = session.conversation_state

    endpoint._session_store.get_session.side_effect = get_session
    endpoint._session_store.save_session.side_effect = save_session
    
    # 1. User provides all information in one message.
    #    The NLU should correctly extract everything.
    response = await endpoint.process_message(
        ChatRequest(
            message="I want to book a 60-minute Full Body Massage for 2 people tomorrow in Shinjuku.",
            session_id=session_id,
        )
    )

    # The bug was a `TypeError` because `set_known_items` was awaited.
    # If the fix is correct, the server should not crash, and the bot should
    # proceed to the next step in the conversation, which is to ask for the
    # course, since the shop is now known.
    assert response.success is True
    assert "which massage course" in response.message.lower()
