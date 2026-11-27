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
    COLLECTING_PHONE = "collecting_phone"
    SELECTING_THERAPIST = "selecting_therapist"
    CHECKING_ELIGIBILITY = "checking_eligibility"
    CONFIRMING_ACTION = "confirming_action"  # Generic for any write action
    ACTION_COMPLETE = "action_complete"  # Generic for any write action
    BOOKING_COMPLETE = "booking_complete" # specific for booking
    BOOKING_UNCERTAIN = "booking_uncertain"
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
    course_duration_options: list[int] = Field(default_factory=list)
    addon_ids: list[int] = Field(default_factory=list)
    catalog_courses: list[dict[str, Any]] = Field(default_factory=list)
    selected_course_options: list[dict[str, Any]] = Field(default_factory=list)
    primary_price: int | None = None
    date: str | None = None
    start_time: str | None = None
    time_preference: str | None = None
    duration: int | None = None
    number_of_people: int | None = None
    therapist_id: int | None = None
    therapist_preference_type: str | None = None
    therapist_preference_value: int | str | None = None
    phone_number: str | None = None
    booking_code: str | None = None


class ConversationState(BaseModel):
    """Conversation state for deterministic flow."""

    phase: ConversationPhase = ConversationPhase.GREETING
    booking_context: BookingContext = Field(default_factory=BookingContext)
    pending_action: PendingAction | None = None  # Updated to store structured PendingAction
    lookup_code: str | None = None
    lookup_phone: str | None = None
    lookup_awaiting_phone: bool = False
    lookup_pending_phone: str | None = None
    lookup_access_token: str | None = None
    management_action: str | None = None
    management_booking_id: int | None = None
    management_booking_code: str | None = None
    last_tool_result: dict | None = None
    offered_slot_time: str | None = None
    slot_confirmed: bool = False
    suggested_slot_times: list[str] = Field(default_factory=list)
    error_message: str | None = None
    step_count: int = 0

    def booking_progress(self) -> dict[str, Any]:
        """Return the customer-facing progress from the saved draft."""
        if self.pending_action and self.pending_action.tool_name in {"modifyBooking", "cancelBooking"}:
            return {
                "active": True,
                "stage": "confirmation",
                "details": {"booking_code": self.management_booking_code} if self.management_booking_code else {},
                "missing": [],
                "requires_confirmation": self.pending_action.status == "pending",
            }
        stages = {
            ConversationPhase.SEARCHING_SHOPS: "shop",
            ConversationPhase.SEARCHING_COURSES: "service",
            ConversationPhase.COLLECTING_INFO: "details",
            ConversationPhase.SEARCHING_SLOTS: "time",
            ConversationPhase.SELECTING_THERAPIST: "therapist",
            ConversationPhase.COLLECTING_PHONE: "contact",
            ConversationPhase.CONFIRMING_ACTION: "confirmation",
            ConversationPhase.BOOKING_COMPLETE: "complete",
            ConversationPhase.BOOKING_UNCERTAIN: "verification",
        }
        stage = stages.get(self.phase)
        ctx = self.booking_context
        fields = {
            "shop": ctx.shop_name,
            "service": ctx.course_name,
            "date": ctx.date,
            "duration": ctx.duration,
            "people": ctx.number_of_people,
            "time": ctx.start_time if stage in {"therapist", "contact", "confirmation", "complete", "verification"} else None,
            "time_preference": ctx.time_preference,
            "phone": ctx.phone_number,
            "booking_code": ctx.booking_code,
        }
        missing = [
            label for label, value in (
                ("shop", ctx.shop_id), ("service", ctx.course_id),
                ("duration", ctx.duration), ("date", ctx.date),
                ("people", ctx.number_of_people),
                ("time", ctx.start_time if stage in {"therapist", "contact", "confirmation", "complete", "verification"} else None),
                ("phone", ctx.phone_number),
            ) if value is None
        ]
        return {
            "active": stage is not None,
            "stage": stage,
            "details": {key: value for key, value in fields.items() if value is not None},
            "missing": missing,
            "requires_confirmation": (
                self.phase == ConversationPhase.CONFIRMING_ACTION
                and self.pending_action is not None
                and self.pending_action.status == "pending"
            ),
        }



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
        from_phase=ConversationPhase.SEARCHING_COURSES,
        action="choose_course",
        to_phase=ConversationPhase.COLLECTING_INFO,
        required_context=["course_id"],
    ),
    StateTransition(
        from_phase=ConversationPhase.COLLECTING_INFO,
        action="search_slots",
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
        from_phase=ConversationPhase.SEARCHING_SLOTS,
        action="confirm_slot",
        to_phase=ConversationPhase.COLLECTING_PHONE,
        required_context=["start_time"],
    ),
    StateTransition(
        from_phase=ConversationPhase.SEARCHING_SLOTS,
        action="change_booking_date",
        to_phase=ConversationPhase.COLLECTING_INFO,
        required_context=["course_id"],
    ),
    StateTransition(
        from_phase=ConversationPhase.COLLECTING_PHONE,
        action="prepare_booking",
        to_phase=ConversationPhase.CONFIRMING_ACTION,
        required_context=[
            "shop_id", "course_id", "date", "start_time", "duration",
            "number_of_people", "phone_number",
        ],
    ),
    StateTransition(
        from_phase=ConversationPhase.CONFIRMING_ACTION,
        action="booking_created",
        to_phase=ConversationPhase.BOOKING_COMPLETE,
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
            previous_phase = state.phase
            state.phase = ConversationPhase.ERROR
            state.error_message = f"Invalid transition: {action} from {previous_phase}"
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
        state.lookup_code = None
        state.lookup_phone = None
        state.lookup_awaiting_phone = False
        state.lookup_pending_phone = None
        state.lookup_access_token = None
        state.management_action = None
        state.management_booking_id = None
        state.management_booking_code = None
        state.last_tool_result = None
        state.offered_slot_time = None
        state.slot_confirmed = False
        state.suggested_slot_times = []
        state.error_message = None
        state.step_count = 0
        return state

    def clear_pending_action(self, state: ConversationState) -> None:
        """Clear pending action."""
        state.pending_action = None

