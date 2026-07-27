from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConversationPhase(str, Enum):
    """Conversation phases for deterministic flow."""

    GREETING = "greeting"
    COLLECTING_INFO = "collecting_info"
    SEARCHING_SHOPS = "searching_shops"
    SEARCHING_COURSES = "searching_courses"
    SEARCHING_SLOTS = "searching_slots"
    SELECTING_THERAPIST = "selecting_therapist"
    CHECKING_ELIGIBILITY = "checking_eligibility"
    CONFIRMING_ACTION = "confirming_action"  # Generic for any write action
    ACTION_COMPLETE = "action_complete"  # Generic for any write action
    BOOKING_COMPLETE = "booking_complete" # specific for booking
    LOOKING_UP_BOOKING = "looking_up_booking"
    FAQ_SEARCH = "faq_search"
    ERROR = "error"


class PendingAction(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "pending"  # pending, executing, completed, cancelled, expired


class BookingContext(BaseModel):
    """Context for booking flow."""

    shop_id: int | None = None
    shop_name: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    addon_ids: list[int] = Field(default_factory=list)
    date: str | None = None
    start_time: str | None = None
    duration: int | None = None
    number_of_people: int | None = None
    therapist_id: int | None = None
    therapist_preference_type: str | None = None
    therapist_preference_value: str | None = None
    phone_number: str | None = None
    booking_code: str | None = None


class ConversationState(BaseModel):
    """Conversation state for deterministic flow."""

    phase: ConversationPhase = ConversationPhase.GREETING
    booking_context: BookingContext = Field(default_factory=BookingContext)
    pending_action: PendingAction | None = None  # Updated to store structured PendingAction
    last_tool_result: dict | None = None
    error_message: str | None = None
    step_count: int = 0



class StateTransition(BaseModel):
    """State transition definition."""
    from_phase: ConversationPhase
    action: str
    to_phase: ConversationPhase
    required_context: list[str] = Field(default_factory=list)


# Deterministic state transitions for read-only flow
STATE_TRANSITIONS: list[StateTransition] = [
    StateTransition(
        from_phase=ConversationPhase.GREETING,
        action="search_shops",
        to_phase=ConversationPhase.SEARCHING_SHOPS,
    ),
    StateTransition(
        from_phase=ConversationPhase.SEARCHING_SHOPS,
        action="select_shop",
        to_phase=ConversationPhase.SEARCHING_COURSES,
        required_context=["shop_id"],
    ),
    StateTransition(
        from_phase=ConversationPhase.SEARCHING_COURSES,
        action="select_course",
        to_phase=ConversationPhase.SEARCHING_SLOTS,
        required_context=["course_id", "date", "duration", "number_of_people"],
    ),
    StateTransition(
        from_phase=ConversationPhase.SEARCHING_SLOTS,
        action="select_slot",
        to_phase=ConversationPhase.SELECTING_THERAPIST,
        required_context=["start_time"],
    ),
    StateTransition(
        from_phase=ConversationPhase.SELECTING_THERAPIST,
        action="select_therapist",
        to_phase=ConversationPhase.CHECKING_ELIGIBILITY,
        required_context=["phone_number"],
    ),
    StateTransition(
        from_phase=ConversationPhase.CHECKING_ELIGIBILITY,
        action="confirm_booking",
        to_phase=ConversationPhase.CONFIRMING_ACTION,
        required_context=["therapist_preference_type"],
    ),
    StateTransition(
        from_phase=ConversationPhase.CONFIRMING_ACTION,
        action="execute_write",
        to_phase=ConversationPhase.ACTION_COMPLETE,
    ),
    StateTransition(
        from_phase=ConversationPhase.GREETING,
        action="lookup_booking",
        to_phase=ConversationPhase.LOOKING_UP_BOOKING,
        required_context=["booking_code"],
    ),
    StateTransition(
        from_phase=ConversationPhase.GREETING,
        action="faq_search",
        to_phase=ConversationPhase.FAQ_SEARCH,
    ),
]


class ConversationManager:
    """Manages deterministic conversation flow."""

    def __init__(self) -> None:
        self._transitions = {t.action: t for t in STATE_TRANSITIONS}

    def can_transition(self, current_phase: ConversationPhase, action: str) -> bool:
        """Check if transition is valid."""
        if action not in self._transitions:
            return False
        transition = self._transitions[action]
        return transition.from_phase == current_phase

    def get_next_phase(
        self, current_phase: ConversationPhase, action: str
    ) -> ConversationPhase | None:
        """Get next phase for action."""
        if action not in self._transitions:
            return None
        transition = self._transitions[action]
        if transition.from_phase != current_phase:
            return None
        return transition.to_phase

    def validate_context(self, action: str, context: BookingContext) -> tuple[bool, list[str]]:
        """Validate required context for action."""
        if action not in self._transitions:
            return False, ["Unknown action"]
        transition = self._transitions[action]
        missing = [
            key for key in transition.required_context if getattr(context, key, None) is None
        ]
        return len(missing) == 0, missing

    def transition(self, state: ConversationState, action: str) -> tuple[ConversationState, bool]:
        """Execute state transition."""
        if not self.can_transition(state.phase, action):
            state.phase = ConversationPhase.ERROR
            state.error_message = f"Invalid transition: {action} from {state.phase}"
            return state, False

        next_phase = self.get_next_phase(state.phase, action)
        if next_phase is None:
            state.phase = ConversationPhase.ERROR
            state.error_message = f"Invalid transition: {action} from {state.phase}"
            return state, False

        valid, missing = self.validate_context(action, state.booking_context)
        if not valid:
            state.phase = ConversationPhase.ERROR
            state.error_message = f"Missing context for {action}: {missing}"
            return state, False

        state.phase = next_phase
        state.step_count += 1
        state.error_message = None
        return state, True

    def reset(self, state: ConversationState) -> ConversationState:
        """Reset conversation to greeting."""
        state.phase = ConversationPhase.GREETING
        state.booking_context = BookingContext()
        state.pending_action = None
        state.last_tool_result = None
        state.error_message = None
        state.step_count = 0
        return state

    def clear_pending_action(self, state: ConversationState) -> None:
        """Clear pending action."""
        state.pending_action = None

