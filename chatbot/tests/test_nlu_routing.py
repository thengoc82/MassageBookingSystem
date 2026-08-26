import pytest
from chatbot.conversation.state import ConversationState
from chatbot.nlu.nlu import NLU

@pytest.mark.asyncio
async def test_faq_question_routing():
    """Test that FAQ questions are routed correctly."""
    nlu = NLU()
    state = ConversationState()
    
    # A typical FAQ question
    message = "What is your cancellation policy?"
    
    nlu_result = await nlu.understand(message, state)
    
    assert nlu_result is not None
    assert nlu_result.intent.name == 'FAQ'
