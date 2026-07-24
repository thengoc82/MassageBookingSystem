"""Tests for conversation state — transitions and validation"""
import pytest

from conversation.state import (
    BookingContext,
    ConversationManager,
    ConversationPhase,
    ConversationState,
    STATE_TRANSITIONS,
    StateTransition,
)


def test_initial_state_is_greeting() -> None:
    state = ConversationState()
    assert state.phase == ConversationPhase.GREETING
    assert state.step_count == 0
    assert state.error_message is None


def test_booking_context_defaults() -> None:
    context = BookingContext()
    assert context.shop_id is None
    assert context.course_id is None
    assert context.addon_ids == []


def test_can_transition_valid() -> None:
    manager = ConversationManager()
    assert manager.can_transition(ConversationPhase.GREETING, "search_shops") is True


def test_can_transition_invalid_action() -> None:
    manager = ConversationManager()
    assert manager.can_transition(ConversationPhase.GREETING, "nonexistent") is False


def test_can_transition_invalid_phase() -> None:
    manager = ConversationManager()
    assert manager.can_transition(ConversationPhase.SEARCHING_SHOPS, "search_shops") is False


def test_get_next_phase_valid() -> None:
    manager = ConversationManager()
    next_phase = manager.get_next_phase(ConversationPhase.GREETING, "search_shops")
    assert next_phase == ConversationPhase.SEARCHING_SHOPS


def test_get_next_phase_invalid() -> None:
    manager = ConversationManager()
    assert manager.get_next_phase(ConversationPhase.GREETING, "nonexistent") is None


def test_validate_context_missing() -> None:
    manager = ConversationManager()
    context = BookingContext()
    valid, missing = manager.validate_context("select_shop", context)
    assert valid is False
    assert "shop_id" in missing


def test_validate_context_present() -> None:
    manager = ConversationManager()
    context = BookingContext(shop_id=1)
    valid, missing = manager.validate_context("select_shop", context)
    assert valid is True
    assert missing == []


def test_transition_success() -> None:
    manager = ConversationManager()
    state = ConversationState()
    new_state, ok = manager.transition(state, "search_shops")
    assert ok is True
    assert new_state.phase == ConversationPhase.SEARCHING_SHOPS
    assert new_state.step_count == 1


def test_transition_invalid_action() -> None:
    manager = ConversationManager()
    state = ConversationState()
    new_state, ok = manager.transition(state, "nonexistent")
    assert ok is False
    assert new_state.phase == ConversationPhase.ERROR
    assert new_state.error_message is not None


def test_transition_invalid_phase() -> None:
    manager = ConversationManager()
    state = ConversationState()
    state.phase = ConversationPhase.BOOKING_COMPLETE
    new_state, ok = manager.transition(state, "search_shops")
    assert ok is False
    assert new_state.phase == ConversationPhase.ERROR


def test_transition_missing_context() -> None:
    manager = ConversationManager()
    state = ConversationState()
    state.phase = ConversationPhase.SEARCHING_SHOPS
    new_state, ok = manager.transition(state, "select_shop")
    assert ok is False
    assert new_state.phase == ConversationPhase.ERROR
    assert "shop_id" in (new_state.error_message or "")


def test_reset_state() -> None:
    manager = ConversationManager()
    state = ConversationState(
        phase=ConversationPhase.SEARCHING_SLOTS,
        booking_context=BookingContext(shop_id=1, course_id=2),
        step_count=5,
    )
    new_state = manager.reset(state)
    assert new_state.phase == ConversationPhase.GREETING
    assert new_state.step_count == 0
    assert new_state.booking_context.shop_id is None


def test_full_booking_flow() -> None:
    manager = ConversationManager()
    state = ConversationState()

    # Greeting -> Searching Shops
    state, ok = manager.transition(state, "search_shops")
    assert ok is True

    # Searching Shops -> Searching Courses
    state.booking_context.shop_id = 1
    state, ok = manager.transition(state, "select_shop")
    assert ok is True
    assert state.phase == ConversationPhase.SEARCHING_COURSES

    # Searching Courses -> Searching Slots
    state.booking_context.course_id = 1
    state.booking_context.date = "2026-07-15"
    state.booking_context.duration = 60
    state.booking_context.number_of_people = 2
    state, ok = manager.transition(state, "select_course")
    assert ok is True
    assert state.phase == ConversationPhase.SEARCHING_SLOTS


def test_state_transitions_list_not_empty() -> None:
    assert len(STATE_TRANSITIONS) > 0
    for t in STATE_TRANSITIONS:
        assert isinstance(t, StateTransition)
        assert t.from_phase is not None
        assert t.to_phase is not None
        assert t.action != ""


def test_transition_increments_step_count() -> None:
    manager = ConversationManager()
    state = ConversationState()
    initial_steps = state.step_count
    state, _ = manager.transition(state, "search_shops")
    assert state.step_count == initial_steps + 1


def test_transition_clears_error_on_success() -> None:
    manager = ConversationManager()
    state = ConversationState()
    state.error_message = "Old error"
    state, ok = manager.transition(state, "search_shops")
    assert ok is True
    assert state.error_message is None


def test_lookup_booking_flow() -> None:
    manager = ConversationManager()
    state = ConversationState()
    state.booking_context.booking_code = "BK20260715001"
    state, ok = manager.transition(state, "lookup_booking")
    assert ok is True
    assert state.phase == ConversationPhase.LOOKING_UP_BOOKING


def test_faq_search_flow() -> None:
    manager = ConversationManager()
    state = ConversationState()
    state, ok = manager.transition(state, "faq_search")
    assert ok is True
    assert state.phase == ConversationPhase.FAQ_SEARCH