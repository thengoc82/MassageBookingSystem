import pytest
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest
from chatbot.app.config import Settings
from chatbot.conversation.state import ConversationPhase

@pytest.mark.asyncio
async def test_booking_flow_unaffected():
    """Test that the booking flow is not affected by the RAG implementation."""
    settings = Settings()
    # Disable RAG for this test to isolate the booking flow
    settings.enable_rag = False
    
    chat_endpoint = ChatEndpoint(settings=settings)
    await chat_endpoint.initialize()

    # Start a conversation
    request = ChatRequest(
        message="I want to book a massage",
        session_id="test-session-booking",
        user_id="test-user-booking",
    )
    response = await chat_endpoint.process_message(request)

    assert response.success
    assert response.phase == ConversationPhase.SEARCHING_SHOPS

    await chat_endpoint.close()
