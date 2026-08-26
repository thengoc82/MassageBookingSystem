from chatbot.conversation.policy import DialoguePolicyManager, Action
from chatbot.conversation.state import ConversationState, ConversationPhase, BookingContext
from chatbot.conversation.goals import Goal

def test_select_therapist_by_index():
    policy = DialoguePolicyManager()
    state = ConversationState()
    state.current_goal = Goal.BOOK_APPOINTMENT
    state.phase = ConversationPhase.SELECTING_THERAPIST
    
    # Mock therapist list
    state.recent_tool_results.last_therapist_search = {
        "data": [
            {"therapistId": 1, "name": "Tanaka Yuki"},
            {"therapistId": 2, "name": "Suzuki Kenji"},
            {"therapistId": 3, "name": "Sato Mei"}
        ]
    }
    
    # Test "1" -> selects Tanaka Yuki
    decision = policy.decide(state, "provide_information", "1")
    
    # Check if correct therapist is selected
    assert state.booking_context.therapist_id == 1
    # Assuming the flow continues
    assert decision.action != Action.REQUEST_CLARIFICATION

def test_select_therapist_by_invalid_index():
    policy = DialoguePolicyManager()
    state = ConversationState()
    state.current_goal = Goal.BOOK_APPOINTMENT
    state.phase = ConversationPhase.SELECTING_THERAPIST
    
    state.recent_tool_results.last_therapist_search = {
        "data": [
            {"therapistId": 1, "name": "Tanaka Yuki"}
        ]
    }
    
    # Test "99" -> invalid index
    decision = policy.decide(state, "provide_information", "99")
    
    # Should not select
    assert state.booking_context.therapist_id is None
    assert decision.action == Action.REQUEST_CLARIFICATION
