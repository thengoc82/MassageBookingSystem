import pytest
from chatbot.conversation.state import (
    BookingContext,
    ConversationManager,
    ConversationPhase,
    ConversationState,
    PendingAction,
)
from chatbot.recovery.handler import RecoveryHandler
from chatbot.session.store import SessionData


@pytest.fixture
def session() -> SessionData:
    return SessionData(session_id="s1", user_id="u1")


def test_recovery_resets_state_on_unexpected_error(session: SessionData) -> None:
    state = ConversationState(
        phase=ConversationPhase.CONFIRMING_ACTION,
        booking_context=BookingContext(shop_id=1, course_id=2),
        pending_action=PendingAction(tool_name="createBooking", arguments={}),
    )
    handler = RecoveryHandler(ConversationManager())

    new_state, msg = handler.handle_failure(RuntimeError("boom"), state, session)

    assert new_state.phase == ConversationPhase.GREETING
    assert new_state.pending_action is None
    assert "start over" in msg.lower()


def test_recovery_clears_booking_context(session: SessionData) -> None:
    state = ConversationState(
        phase=ConversationPhase.SEARCHING_SLOTS,
        booking_context=BookingContext(shop_id=1, date="2026-01-01"),
    )
    handler = RecoveryHandler(ConversationManager())
    new_state, _ = handler.handle_failure(ValueError("bad"), state, session)
    assert new_state.booking_context.shop_id is None
