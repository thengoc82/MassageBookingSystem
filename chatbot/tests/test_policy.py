# chatbot/tests/test_policy.py
"""Unit tests for the Dialogue Policy layer (Phase 8)."""
from __future__ import annotations

import pytest

from chatbot.conversation.goals import Goal
from chatbot.conversation.policy import (
    Action,
    DialoguePolicyManager,
    PolicyDecision,
)
from chatbot.conversation.state import (
    BookingContext,
    ConversationState,
)


def fresh_state() -> ConversationState:
    s = ConversationState()
    s.recent_tool_results.last_shop_search = {"data": [{"shopId": 1, "shopName": "Shinjuku"}]}
    return s


# ---------------------------------------------------------------------------
# Basic decisions
# ---------------------------------------------------------------------------
def test_reset_returns_clear_pending():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(state, "reset", "reset")
    assert decision.action == Action.CLEAR_PENDING_ACTION


def test_cancel_action_returns_clear():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(state, "cancel_action", "cancel that")
    assert decision.action == Action.CLEAR_PENDING_ACTION
    assert "cancel" in (decision.message or "").lower()


def test_book_intent_starts_booking_chain():
    policy = DialoguePolicyManager()
    state = ConversationState()  # pristine, no shop search yet
    decision = policy.decide(state, "book", "I want a massage")
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "area"
    assert state.current_goal == Goal.BOOK_APPOINTMENT


def test_book_with_shop_selected_advances_to_courses():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.booking_context.shop_id = 1
    decision = policy.decide(state, "book", "anything")
    assert decision.action == Action.RUN_TOOL
    assert decision.tool == "search_courses"


def test_book_with_shop_and_courses_loaded_advances_to_slots():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.booking_context.shop_id = 1
    state.booking_context.course_id = 5
    state.booking_context.duration = 60
    state.recent_tool_results.last_course_search = {"data": [{"courseId": 5}]}
    decision = policy.decide(state, "book", "anything")
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "date"


# ---------------------------------------------------------------------------
# Slot filling
# ---------------------------------------------------------------------------
def test_ask_slot_decision_returns_missing_field():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.booking_context.shop_id = 1
    state.booking_context.course_id = 5
    state.recent_tool_results.last_course_search = {"data": [{"courseId": 5}]}
    decision = policy.decide(state, "book", "anything")
    # search_courses already done; search_slots missing duration.
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "duration"


def test_mid_slot_filling_continues_with_run_tool():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.pending_read_action = "search_slots"
    decision = policy.decide(state, "book", "tomorrow")
    assert decision.action == Action.RUN_TOOL
    assert decision.tool == "__continue_slot_filling__"


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
def test_goal_set_on_first_book_intent():
    policy = DialoguePolicyManager()
    state = fresh_state()
    policy.decide(state, "book", "I want a massage")
    assert state.current_goal == Goal.BOOK_APPOINTMENT


def test_goal_switch_to_cancel_when_user_requests_cancel():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.current_goal = Goal.BOOK_APPOINTMENT
    state.booking_context.shop_id = 1
    decision = policy.decide(
        state, "cancel_booking", "actually cancel my reservation"
    )
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "booking_code"
    assert decision.goal == Goal.CANCEL_BOOKING


def test_goal_switch_does_not_lose_previous_goal():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.current_goal = Goal.BOOK_APPOINTMENT
    policy.decide(state, "faq_search", "what time do you close?")
    assert state.current_goal == Goal.ASK_FAQ
    assert state.previous_goal == Goal.BOOK_APPOINTMENT


def test_resume_booking_after_faq():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.current_goal = Goal.ASK_FAQ
    state.previous_goal = Goal.BOOK_APPOINTMENT
    decision = policy.decide(state, "book", "back to booking")
    assert decision.action == Action.RESUME_BOOKING
    assert decision.goal == Goal.BOOK_APPOINTMENT
    assert state.current_goal == Goal.BOOK_APPOINTMENT
    assert state.previous_goal is None


# ---------------------------------------------------------------------------
# FAQ interruption mid-slot-filling
# ---------------------------------------------------------------------------
def test_faq_during_slot_filling_returns_answer_faq_then_saves_goal():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.pending_read_action = "search_slots"
    state.current_goal = Goal.BOOK_APPOINTMENT
    decision = policy.decide(state, "faq_search", "what time do you close?")
    assert decision.action == Action.ANSWER_FAQ
    assert decision.goal == Goal.BOOK_APPOINTMENT  # saved


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------
def test_lookup_without_code_asks_for_it():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(state, "lookup_booking", "check my booking")
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "booking_code"
    assert decision.goal == Goal.LOOKUP_BOOKING


def test_lookup_with_code_in_message_runs_tool():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(
        state, "lookup_booking", "check my booking BK202512250001"
    )
    assert decision.action == Action.RUN_TOOL
    assert decision.tool == "lookup_booking"
    assert state.booking_context.booking_code == "BK202512250001"


# ---------------------------------------------------------------------------
# Confirmation gate
# ---------------------------------------------------------------------------
def test_cancel_with_code_requires_confirmation():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(
        state, "cancel_booking", "cancel BK202512250001"
    )
    assert decision.action == Action.CONFIRM_ACTION
    assert decision.tool == "cancelBooking"


def test_modify_with_code_requires_confirmation():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(
        state, "modify_booking", "modify BK202512250001"
    )
    assert decision.action == Action.CONFIRM_ACTION
    assert decision.tool == "modifyBooking"


def test_confirmation_yes_executes_write():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.pending_confirm = {
        "tool": "cancelBooking",
        "intent": "cancel_booking",
        "arguments": {"bookingCode": "BK202512250001"},
    }
    decision = policy.decide(state, "book", "yes")
    assert decision.action == Action.EXECUTE_WRITE_ACTION
    assert decision.tool == "cancelBooking"


def test_confirmation_no_clears_pending():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.pending_confirm = {"tool": "cancelBooking"}
    decision = policy.decide(state, "book", "no")
    assert decision.action == Action.CLEAR_PENDING_ACTION


def test_confirmation_unrelated_message_reprompts():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.pending_confirm = {"tool": "cancelBooking"}
    decision = policy.decide(state, "book", "what time do you open?")
    assert decision.action == Action.CONFIRM_ACTION


# ---------------------------------------------------------------------------
# Browse intents
# ---------------------------------------------------------------------------
def test_browse_shops_runs_search_shops():
    policy = DialoguePolicyManager()
    state = fresh_state()
    decision = policy.decide(state, "browse_shops", "show me shops")
    assert decision.action == Action.RUN_TOOL
    assert decision.tool == "search_shops"


def test_browse_courses_without_shop_asks_for_shop():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.recent_tool_results.last_shop_search = None
    decision = policy.decide(state, "browse_courses", "show me courses")
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "shop_id"


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------
def test_recovery_after_repeated_tool_failures():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.tool_failure_count = 2
    state.last_failed_tool = "lookupBooking"
    decision = policy.decide(state, "book", "anything")
    assert decision.action == Action.END_CONVERSATION
    assert "reset" in (decision.message or "").lower()


def test_recovery_not_triggered_below_threshold():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.tool_failure_count = 1
    state.last_failed_tool = "lookupBooking"
    decision = policy.decide(state, "book", "anything")
    assert decision.action != Action.END_CONVERSATION


# ---------------------------------------------------------------------------
# Booking tool chain — slots not asked twice
# ---------------------------------------------------------------------------
def test_same_slot_not_asked_twice():
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.booking_context.shop_id = 1
    state.booking_context.course_id = 5
    state.booking_context.duration = 60
    state.booking_context.date = "2026-08-01"
    state.recent_tool_results.last_course_search = {"data": [{"courseId": 5}]}
    decision = policy.decide(state, "book", "anything")
    assert decision.action == Action.ASK_SLOT
    assert decision.slot == "number_of_people"


def test_search_shops_not_rerun_after_already_loaded():
    policy = DialoguePolicyManager()
    state = fresh_state()
    # last_shop_search is set in fresh_state(); shop_id also set.
    state.booking_context.shop_id = 1
    decision = policy.decide(state, "book", "anything")
    # Should advance to search_courses, not re-run search_shops.
    assert decision.tool == "search_courses"


# ---------------------------------------------------------------------------
# No business logic in policy — NLU and slots separate
# ---------------------------------------------------------------------------
def test_policy_does_not_parse_dates():
    """The policy must NOT extract dates. That's slot filling's job."""
    policy = DialoguePolicyManager()
    state = fresh_state()
    state.booking_context.shop_id = 1
    decision = policy.decide(state, "book", "tomorrow for 2")
    # No date was extracted; the policy just returns the next ask.
    assert state.booking_context.date is None
    # Returns ASK_SLOT or RUN_TOOL — never parses entities.
    assert decision.action in {Action.ASK_SLOT, Action.RUN_TOOL}


# ---------------------------------------------------------------------------
# PolicyDecision dataclass
# ---------------------------------------------------------------------------
def test_policy_decision_goal_coercion():
    pd = PolicyDecision(action=Action.ASK_SLOT, goal="book_appointment")
    assert pd.goal == Goal.BOOK_APPOINTMENT


def test_policy_decision_defaults():
    pd = PolicyDecision(action=Action.NO_ACTION)
    assert pd.tool is None
    assert pd.slot is None
    assert pd.payload == {}