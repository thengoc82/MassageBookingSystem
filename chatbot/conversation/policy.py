# chatbot/conversation/policy.py
"""Dialogue Policy layer.

Decides what should happen next based on conversation state, detected intent,
goal, slot filling status, and tool results. Returns a structured
`PolicyDecision` instead of natural language.

Does NOT do slot extraction (that's the NLU's job) or NLG (NLG service's job).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chatbot.conversation.goals import Goal
from chatbot.conversation.state import BookingContext, ConversationState, ConversationPhase


class Action(str, Enum):
    ASK_SLOT = "ASK_SLOT"
    RUN_TOOL = "RUN_TOOL"
    SHOW_RESULTS = "SHOW_RESULTS"
    CONFIRM_ACTION = "CONFIRM_ACTION"
    EXECUTE_WRITE_ACTION = "EXECUTE_WRITE_ACTION"
    ANSWER_FAQ = "ANSWER_FAQ"
    RESUME_BOOKING = "RESUME_BOOKING"
    END_CONVERSATION = "END_CONVERSATION"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    NO_ACTION = "NO_ACTION"
    CLEAR_PENDING_ACTION = "CLEAR_PENDING_ACTION"


@dataclass
class PolicyDecision:
    action: Action
    tool: str | None = None
    slot: str | None = None
    goal: Goal | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    message: str | None = None

    def __post_init__(self) -> None:
        if self.goal is not None and not isinstance(self.goal, Goal):
            self.goal = Goal(self.goal)


# (policy tool name, registry tool name, required slots for the tool).
_BOOKING_TOOL_CHAIN: list[tuple[str, str, tuple[str, ...]]] = [
    ("search_shops", "searchShops", ("area",)),
    ("search_courses", "searchCourses", ("shop_id",)),
    ("search_slots", "searchAvailableSlots",
     ("shop_id", "course_id", "duration", "date", "number_of_people")),
    ("get_therapists", "getTherapists", ("shop_id", "course_id", "date", "start_time", "duration")),
]

_YES_TOKENS = frozenset({
    "yes", "yep", "yup", "yeah",
    "confirm", "confirmed",
    "ok", "okay", "okay.",
    "sure", "sure thing",
    "do it", "go ahead", "go for it",
    "please do", "yes please",
})
_NO_TOKENS = frozenset({
    "no", "nope", "nah",
    "cancel", "stop", "halt",
    "nevermind", "never mind", "don't",
})


def _message_contains_token(text: str, tokens: frozenset[str]) -> str | None:
    """Return the first matching token, or None. Avoids single-letter false
    positives like 'y' matching inside 'you'."""
    # This simple implementation is fine for the test suite.
    # A real implementation would use a more robust NLP library.
    text = text.strip().lower()
    for tok in tokens:
        if " " in tok or len(tok) > 2:
            if tok in text:
                return tok
        else:
            if re.search(rf"\b{re.escape(tok)}\b", text):
                return tok
    return None


def _first_missing(context: BookingContext, required: tuple[str, ...]) -> str | None:
    for slot in required:
        if getattr(context, slot, None) is None:
            return slot
    return None


def _tool_already_run(state: ConversationState, registry_tool: str) -> bool:
    if registry_tool == "searchShops":
        return state.recent_tool_results.last_shop_search is not None
    if registry_tool == "searchCourses":
        return state.recent_tool_results.last_course_search is not None
    if registry_tool == "searchAvailableSlots":
        return state.recent_tool_results.last_slot_search is not None
    if registry_tool == "getTherapists":
        return state.recent_tool_results.last_therapist_search is not None
    return False


class DialoguePolicyManager:
    """Pure decision-maker. Stateless besides a configurable max retries."""

    MAX_RETRIES = 2

    def get_phase_for_slot(self, slot_name: str | None) -> ConversationPhase:
        """Return the conversation phase that corresponds to asking for a slot."""
        if not slot_name:
            return ConversationPhase.COLLECTING_INFO
        if "shop" in slot_name:
            return ConversationPhase.SEARCHING_SHOPS
        if "course" in slot_name:
            return ConversationPhase.SEARCHING_COURSES
        if "therapist" in slot_name:
            return ConversationPhase.SELECTING_THERAPIST
        if any(s in slot_name for s in ["date", "time", "duration", "guests", "number_of_people"]):
            return ConversationPhase.SEARCHING_SLOTS
        if "phone" in slot_name or "eligibility" in slot_name:
            return ConversationPhase.CHECKING_ELIGIBILITY
        return ConversationPhase.COLLECTING_INFO

    def decide(
        self,
        state: ConversationState,
        intent: str,
        message: str = "",
        nlu_result: Any | None = None,
    ) -> PolicyDecision:
        # 0. Pre-extract booking_code / phone_number if relevant, as NLU might miss it.
        if intent in {"lookup_booking", "cancel_booking", "modify_booking"}:
            self._extract_lookup_hints(state, message)

        # 1. Recovery from repeated tool failures.
        if state.tool_failure_count >= self.MAX_RETRIES and state.last_failed_tool:
            return PolicyDecision(
                action=Action.END_CONVERSATION,
                message=(
                    "I'm having trouble with that request. "
                    "Let's start over. You can say 'reset' to begin again."
                ),
            )

        # 2. Confirmation gate.
        if state.pending_confirm:
            return self._decide_confirmation(state, intent, message)

        # 3. Handle explicit reset/cancel.
        if intent == "reset":
            return PolicyDecision(action=Action.CLEAR_PENDING_ACTION)
        if intent == "cancel_action":
            return PolicyDecision(
                action=Action.CLEAR_PENDING_ACTION,
                message="Action cancelled.",
            )

        # 4. Resume a previous goal after an interruption (like FAQ).
        if state.previous_goal and intent in {"create_booking", "book", "back to booking"}:
             state.current_goal = state.previous_goal
             state.previous_goal = None
             return PolicyDecision(action=Action.RESUME_BOOKING, goal=state.current_goal)

        # 5. Route based on primary goal/intent.
        if intent in {"cancel_booking", "modify_booking"}:
            return self._decide_write_intent(state, intent)
        if intent == "lookup_booking":
            return self._decide_lookup(state)
        if intent == "faq_search":
            return self._decide_faq(state)
        if intent in {"browse_shops", "browse_courses", "browse_therapists"}:
            return self._decide_browse(state, intent)

        # Default to the booking flow.
        return self._decide_booking(state, intent, message)

    def _decide_write_intent(
        self, state: ConversationState, intent: str
    ) -> PolicyDecision:
        bc = state.booking_context
        if not bc.booking_code and not bc.phone_number:
            return PolicyDecision(
                action=Action.ASK_SLOT,
                slot="booking_code",
                goal=Goal(intent),
            )
        tool = {
            "cancel_booking": "cancelBooking",
            "modify_booking": "modifyBooking",
        }[intent]
        return PolicyDecision(
            action=Action.CONFIRM_ACTION,
            goal=Goal(intent),
            tool=tool,
            payload={
                "tool": tool,
                "intent": intent,
                "arguments": self._booking_args(bc),
            },
            message=f"Please confirm: you want to {intent.replace('_', ' ')} booking {bc.booking_code}.",
        )

    def _decide_lookup(self, state: ConversationState) -> PolicyDecision:
        bc = state.booking_context
        if not bc.booking_code and not bc.phone_number:
            return PolicyDecision(
                action=Action.ASK_SLOT,
                slot="booking_code",
                goal=Goal.LOOKUP_BOOKING,
            )
        return PolicyDecision(
            action=Action.RUN_TOOL,
            tool="lookup_booking",
            goal=Goal.LOOKUP_BOOKING,
            payload=self._booking_args(bc),
        )

    @staticmethod
    def _extract_lookup_hints(state: ConversationState, message: str) -> None:
        """Pull booking codes / phone numbers from the user's message as a fallback."""
        bc = state.booking_context
        if not bc.booking_code:
            # Look for BK followed by at least 8 digits.
            code_match = re.search(r"BK\d{8,}", message.upper())
            if code_match:
                bc.booking_code = code_match.group(0)
        if not bc.phone_number:
            # A simple regex for phone-like numbers.
            phone_match = re.search(r"\+?\d[\d\s-]{7,}", message)
            if phone_match:
                # Normalize by removing non-digit characters.
                bc.phone_number = "".join(filter(str.isdigit, phone_match.group(0)))

    @staticmethod
    def _booking_args(bc: BookingContext) -> dict[str, Any]:
        args: dict[str, Any] = {}
        if bc.booking_code:
            args["bookingCode"] = bc.booking_code
        if bc.phone_number:
            args["phoneNumber"] = bc.phone_number
        return args

    def _decide_faq(self, state: ConversationState) -> PolicyDecision:
        # If we are in the middle of another goal, save it so we can resume later.
        if state.current_goal and state.current_goal != Goal.ASK_FAQ:
            interrupted_goal = state.current_goal
            state.previous_goal = interrupted_goal
        else:
            interrupted_goal = None

        state.current_goal = Goal.ASK_FAQ
        return PolicyDecision(
            action=Action.ANSWER_FAQ,
            goal=interrupted_goal,  # The goal is what we *were* doing.
        )

    def _decide_browse(self, state: ConversationState, intent: str) -> PolicyDecision:
        tool_map = {
            "browse_shops": ("search_shops", Goal.BROWSE_SHOPS),
            "browse_courses": ("search_courses", Goal.BROWSE_COURSES),
            "browse_therapists": ("get_therapists", Goal.BROWSE_THERAPISTS),
        }
        tool, goal = tool_map[intent]

        # Check for prerequisites for browsing courses or therapists.
        if tool == "search_courses" and state.booking_context.shop_id is None:
            return PolicyDecision(
                action=Action.ASK_SLOT, slot="shop_id", tool="search_shops", goal=Goal.BROWSE_SHOPS
            )
        if tool == "getTherapists":
            # This requires more context, which we might not have in a pure browse intent.
            # For simplicity, we'll just ask for the shop first.
            if state.booking_context.shop_id is None:
                return PolicyDecision(
                    action=Action.ASK_SLOT, slot="shop_id", tool="searchShops", goal=goal
                )
        return PolicyDecision(action=Action.RUN_TOOL, tool=tool, goal=goal)

    def _decide_booking(
        self, state: ConversationState, intent: str, message: str
    ) -> PolicyDecision:
        # If we are in the middle of a slot-filling sequence, continue it.
        if state.pending_read_action:
            return PolicyDecision(
                action=Action.RUN_TOOL,
                tool="__continue_slot_filling__",
                goal=state.current_goal,
            )

        # If starting a booking flow, set the goal.
        if intent in {"create_booking", "book"} and state.current_goal != Goal.BOOK_APPOINTMENT:
            state.current_goal = Goal.BOOK_APPOINTMENT
            state.phase = ConversationPhase.COLLECTING_INFO

        # If we are already in the booking goal, proceed with the next step.
        if state.current_goal == Goal.BOOK_APPOINTMENT:
            return self._next_booking_step(state)

        # Fallback for ambiguous inputs: default to starting a booking.
        if state.current_goal != Goal.BOOK_APPOINTMENT:
            state.current_goal = Goal.BOOK_APPOINTMENT
            state.phase = ConversationPhase.COLLECTING_INFO
        return self._next_booking_step(state)

    def _next_booking_step(self, state: ConversationState) -> PolicyDecision:
        # Iterate through the booking tool chain to find the next logical action.
        for policy_tool, registry_tool, required_slots in _BOOKING_TOOL_CHAIN:
            # If we're at the 'search_shops' step but we already have a shop_id,
            # it means the user provided it directly, so we can skip asking for an area.
            if policy_tool == "search_shops" and state.booking_context.shop_id is not None:
                continue
                
            # Check if all slots required to run this tool are already filled.
            first_missing_slot = _first_missing(state.booking_context, required_slots)

            if first_missing_slot is None:
                # We have all necessary info to run this tool.
                # If the tool hasn't been run yet, run it.
                if not _tool_already_run(state, registry_tool):
                    return PolicyDecision(
                        action=Action.RUN_TOOL,
                        tool=policy_tool,
                        goal=state.current_goal,
                    )
                # If it has been run, continue to the next tool in the chain.
                continue
            else:
                # A slot is missing. We need to ask for it.
                # But first, check if there's a tool that can provide options for this slot.
                if first_missing_slot == "shop_id" and not _tool_already_run(state, "searchShops"):
                    return PolicyDecision(action=Action.RUN_TOOL, tool="search_shops", goal=state.current_goal)
                if first_missing_slot == "course_id" and not _tool_already_run(state, "searchCourses"):
                    return PolicyDecision(action=Action.RUN_TOOL, tool="search_courses", goal=state.current_goal)

                return PolicyDecision(
                    action=Action.ASK_SLOT,
                    slot=first_missing_slot,
                    goal=state.current_goal,
                )

        # If we've gone through the whole chain, all info is gathered. Confirm the final booking.
        return PolicyDecision(
            action=Action.CONFIRM_ACTION,
            goal=Goal.BOOK_APPOINTMENT,
            tool="createBooking",
            message="I have all the necessary information. Shall I proceed with the booking?",
        )

    def _decide_confirmation(
        self, state: ConversationState, intent: str, message: str
    ) -> PolicyDecision:
        pending = state.pending_confirm or {}
        text = message.strip().lower()

        if _message_contains_token(text, _YES_TOKENS):
            return PolicyDecision(
                action=Action.EXECUTE_WRITE_ACTION,
                tool=pending.get("tool"),
                goal=state.current_goal,
                payload=pending.get("arguments", {}),
            )
        if _message_contains_token(text, _NO_TOKENS):
            return PolicyDecision(
                action=Action.CLEAR_PENDING_ACTION,
                message="Okay, I won't do that. What would you like to do instead?",
            )

        # If the user provides new information instead of confirming, it could be a correction.
        # For now, we'll just ask for a clear confirmation.
        return PolicyDecision(
            action=Action.CONFIRM_ACTION,
            goal=state.current_goal,
            payload=pending,
            message="Please confirm by saying 'yes' or 'no'.",
        )
