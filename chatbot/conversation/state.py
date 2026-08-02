import logging
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from chatbot.nlu.models import Entity, NLUResult, Intent, EntityType

logger = logging.getLogger(__name__)


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

    area: str | None = None
    shop_id: int | None = None
    shop_name: str | None = None
    course_id: int | None = None
    course_name: str | None = None
    therapist_name: str | None = None
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



class RecentToolResults(BaseModel):
    """Stores results from recent tool calls for reference resolution."""
    last_shop_search: dict | None = None
    last_course_search: dict | None = None
    last_slot_search: dict | None = None
    last_therapist_search: dict | None = None
    last_booking_lookup: dict | None = None
    faq_search_results: dict | None = None


class ConversationState(BaseModel):
    """Conversation state for deterministic flow."""

    phase: ConversationPhase = ConversationPhase.GREETING
    booking_context: BookingContext = Field(default_factory=BookingContext)
    pending_action: PendingAction | None = None
    last_tool_result: dict | Any = None # Raw output of the last executed tool
    recent_tool_results: RecentToolResults = Field(default_factory=RecentToolResults) # Structured tool results for reference
    error_message: str | None = None
    step_count: int = 0
    current_intent: Intent | None = None
    previous_intent: Intent | None = None
    current_goal: str | None = None
    previous_goal: str | None = None
    last_planner_decision: str | None = None
    recent_extracted_entities: dict | None = None
    pending_read_action: str | None = None
    pending_confirm: dict | None = None
    tool_failure_count: int = 0
    last_failed_tool: str | None = None
    pending_slot_to_fill: str | None = None

    nlu_result: NLUResult | None = None








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
        action="create_booking",
        to_phase=ConversationPhase.SEARCHING_COURSES,
    ),
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
        required_context=["course_id"],
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
            state.error_message = "Let's start over — how can I help you?"
            return state, False

        next_phase = self.get_next_phase(state.phase, action)
        if next_phase is None:
            state.phase = ConversationPhase.ERROR
            state.error_message = "Let's start over — how can I help you?"
            return state, False

        valid, missing = self.validate_context(action, state.booking_context)
        if not valid:
            state.phase = ConversationPhase.ERROR
            state.error_message = "I'm missing some information. Let's try again."
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
        state.recent_tool_results = RecentToolResults()
        state.recent_extracted_entities = None
        state.pending_read_action = None
        state.pending_confirm = None
        state.tool_failure_count = 0
        state.last_failed_tool = None
        state.error_message = None
        state.step_count = 0
        state.current_intent = None
        state.previous_intent = None
        state.current_goal = None
        state.previous_goal = None
        return state

    def clear_pending_action(self, state: ConversationState) -> None:
        """Clear pending action."""
        state.pending_action = None
        state.pending_read_action = None

    def apply_nlu_entities_to_booking_context(self, state: ConversationState, entities: list[Entity],) -> bool:
        logger.critical(f"Applying NLU entities: {entities}")
        bc = state.booking_context
        updated_fields = False

        def _get_field_value(item: Any, field_name: str, default: Any = None) -> Any:
            """Helper to get value from dict or object."""
            if isinstance(item, dict):
                return item.get(field_name, default)
            return getattr(item, field_name, default)

        for entity in entities:
            logger.info(f"Processing entity: {entity.type} = {entity.value}")
            original_context = bc.model_copy(deep=True)

            if entity.type == EntityType.SHOP_ID:
                entity_value = entity.value
                if isinstance(entity_value, dict):
                    bc.shop_id = int(_get_field_value(entity_value, "shopId")) if _get_field_value(entity_value, "shopId") is not None else bc.shop_id
                    bc.shop_name = _get_field_value(entity_value, "shopName") or bc.shop_name
                else:
                    try:
                        bc.shop_id = int(entity_value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert shop_id '{entity_value}' to int.")
                        bc.shop_id = None
                
                if bc.shop_name is None and state.recent_tool_results.last_shop_search:
                    shops = state.recent_tool_results.last_shop_search
                    if isinstance(shops, dict):
                        shops = shops.get("data", [])
                    
                    for shop_item in shops:
                        shop_id_val = _get_field_value(shop_item, 'shopId')
                        if shop_id_val is not None and int(shop_id_val) == bc.shop_id:
                            bc.shop_name = _get_field_value(shop_item, 'shopName')
                            break
            
            elif entity.type == EntityType.SHOP_NAME:
                bc.shop_name = entity.value
                if state.recent_tool_results.last_shop_search:
                    shops = state.recent_tool_results.last_shop_search
                    if isinstance(shops, dict):
                        shops = shops.get("data", [])
                    
                    for shop_item in shops:
                        shop_id_val = _get_field_value(shop_item, 'shopId')
                        shop_name_val = _get_field_value(shop_item, 'shopName')

                        if shop_name_val and entity.value.lower() in shop_name_val.lower():
                            if shop_id_val is not None:
                                bc.shop_id = int(shop_id_val)
                            bc.shop_name = shop_name_val
                            break

            elif entity.type == EntityType.COURSE:
                course_value = entity.value
                
                bc.course_id = int(_get_field_value(course_value, "courseId")) if _get_field_value(course_value, "courseId") is not None else bc.course_id
                bc.course_name = _get_field_value(course_value, "courseName") or bc.course_name
                durations = _get_field_value(course_value, "durations")

                if bc.duration is None and durations:
                    nlu_duration_entity = next((e for e in entities if e.type == EntityType.DURATION), None)
                    if nlu_duration_entity:
                        bc.duration = nlu_duration_entity.value
                    else:
                        first_duration = durations[0]
                        bc.duration = _get_field_value(first_duration, "duration")
                logger.info(f"Setting course for course entity: ID={bc.course_id}, Name={bc.course_name}, Duration={bc.duration}")


            elif entity.type == EntityType.COURSE_ID:
                bc.course_id = int(entity.value) if isinstance(entity.value, str) else entity.value
                logger.info(f"Setting course ID from COURSE_ID entity: ID={bc.course_id}")
            
            elif entity.type == EntityType.COURSE_NAME:
                bc.course_name = entity.value
                if state.recent_tool_results.last_course_search and state.recent_tool_results.last_course_search.get("data"):
                    courses = state.recent_tool_results.last_course_search["data"]
                    for course_item in courses:
                        course_id_val = _get_field_value(course_item, "courseId")
                        course_name_val = _get_field_value(course_item, "courseName")
                        course_durations = _get_field_value(course_item, "durations", [])

                        if course_name_val and entity.value.lower() in course_name_val.lower():
                            if course_id_val is not None:
                                bc.course_id = int(course_id_val)
                            bc.course_name = course_name_val
                            if bc.duration is None and course_durations:
                                bc.duration = _get_field_value(course_durations[0], "duration")
                            break
            elif entity.type == EntityType.THERAPIST:
                therapist_value = entity.value
                bc.therapist_id = _get_field_value(therapist_value, "therapistId", bc.therapist_id)
                bc.therapist_name = _get_field_value(therapist_value, "name", bc.therapist_name)

            elif entity.type == EntityType.DATE:
                bc.date = entity.value

            elif entity.type == EntityType.DURATION:
                bc.duration = entity.value

            elif entity.type == EntityType.NUMBER_OF_PEOPLE:
                bc.number_of_people = entity.value

            elif entity.type == EntityType.TIME:
                bc.start_time = entity.value

            elif entity.type == EntityType.PHONE_NUMBER:
                bc.phone_number = entity.value

            elif entity.type == EntityType.BOOKING_CODE:
                bc.booking_code = entity.value

            elif entity.type == EntityType.AREA:
                bc.area = entity.value
                updated_fields = True
                logger.debug(f"Booking context updated by entity {entity.type}. New context: {bc}")
        
        logger.info(f"Booking context after applying entities: {bc}")
        
        if bc.duration is not None:
            try:
                bc.duration = int(bc.duration)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert duration '{bc.duration}' to int.")
                bc.duration = None
                updated_fields = False
        if bc.number_of_people is not None:
            try:
                bc.number_of_people = int(bc.number_of_people)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert number_of_people '{bc.number_of_people}' to int.")
                bc.number_of_people = None
                updated_fields = False
                
        return updated_fields

    def update_booking_context(self, state: ConversationState, updates: dict[str, Any]) -> bool:
        """Update booking context and return True if any value was changed."""
        logger.info(f"Updating booking context with: {updates}")
        updated = False
        for key, value in updates.items():
            if hasattr(state.booking_context, key):
                if getattr(state.booking_context, key) != value:
                    setattr(state.booking_context, key, value)
                    updated = True
        return updated


