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
    COLLECTING_PEOPLE = "collecting_people"
    COLLECTING_DURATION = "collecting_duration"
    SELECTING_DATE = "selecting_date"
    SEARCHING_SHOPS = "searching_shops"
    SELECTING_PACKAGE = "selecting_package"
    SEARCHING_COURSES = "searching_courses"
    SEARCHING_SLOTS = "searching_slots"
    SELECTING_THERAPIST = "selecting_therapist"
    CHECKING_ELIGIBILITY = "checking_eligibility"
    CONFIRMING_BOOKING = "confirming_booking"
    ACTION_COMPLETE = "action_complete"  # Generic for any write action
    BOOKING_COMPLETE = "booking_complete" # specific for booking
    LOOKING_UP_BOOKING = "looking_up_booking"
    FAQ_PROMPT = "faq_prompt"
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
    therapist_name: str | None = None
    addon_ids: list[int] = Field(default_factory=list)
    addon_names: list[str] = Field(default_factory=list)
    date: str | None = None
    start_time: str | None = None
    duration: int | None = None
    number_of_people: int | None = None
    therapist_id: int | None = None
    therapist_preference_type: str | None = None
    therapist_preference_value: str | None = None
    phone_number: str | None = None
    user_name: str | None = None
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
    slot_fill_retries: int = 0

    nlu_result: NLUResult | None = None

    def to_frontend_booking_state(self) -> dict[str, Any]:
        """Converts the internal ConversationState to the frontend's BookingState format."""
        state = {}
        if self.booking_context.shop_id:
            state["shopId"] = self.booking_context.shop_id
        if self.booking_context.shop_name:
            state["shopName"] = self.booking_context.shop_name
        if self.booking_context.course_id:
            state["courseId"] = self.booking_context.course_id
        if self.booking_context.course_name:
            state["courseName"] = self.booking_context.course_name
        if self.booking_context.addon_ids:
            state["addonIds"] = self.booking_context.addon_ids
        if self.booking_context.addon_names:
            state["addonNames"] = self.booking_context.addon_names
        if self.booking_context.date:
            state["date"] = self.booking_context.date
        if self.booking_context.start_time:
            state["time"] = self.booking_context.start_time
        if self.booking_context.duration:
            state["duration"] = self.booking_context.duration
        if self.booking_context.number_of_people:
            state["guests"] = self.booking_context.number_of_people
        if self.booking_context.therapist_id:
            state["therapistId"] = self.booking_context.therapist_id
        if self.booking_context.therapist_name:
            state["therapistName"] = self.booking_context.therapist_name
        if self.booking_context.phone_number:
            state["phone"] = self.booking_context.phone_number
        if self.booking_context.booking_code:
            state["bookingCode"] = self.booking_context.booking_code

        # Add review/confirm flags based on current phase and pending_confirm
        if self.phase == ConversationPhase.CONFIRMING_BOOKING:
            state["review"] = True
            state["confirm"] = True

        return state






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
        to_phase=ConversationPhase.COLLECTING_PEOPLE,
    ),
    StateTransition(
        from_phase=ConversationPhase.COLLECTING_PEOPLE,
        action="provide_people",
        to_phase=ConversationPhase.COLLECTING_DURATION,
        required_context=["number_of_people"],
    ),
    StateTransition(
        from_phase=ConversationPhase.COLLECTING_DURATION,
        action="provide_duration",
        to_phase=ConversationPhase.SELECTING_PACKAGE,
        required_context=["duration"],
    ),
    StateTransition(
        from_phase=ConversationPhase.SELECTING_PACKAGE,
        action="select_package",
        to_phase=ConversationPhase.SEARCHING_SLOTS,
        required_context=["course_id"], # A package selection implies a course_id
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
        to_phase=ConversationPhase.CONFIRMING_BOOKING,
        required_context=["therapist_preference_type"],
    ),
    StateTransition(
        from_phase=ConversationPhase.CONFIRMING_BOOKING,
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

    def apply_nlu_entities_to_booking_context(self, state: ConversationState, entities: list[Entity], package_selected: bool = False) -> bool:
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
                     logger.info(f"SHOP_ID entity received: {entity_value}")
                     bc.shop_id = int(_get_field_value(entity_value, "shopId")) if _get_field_value(entity_value, "shopId") is not None else bc.shop_id
                     bc.shop_name = _get_field_value(entity_value, "shopName") or bc.shop_name
                     if bc.shop_id and bc.shop_name:
                         logger.info(f"Resolved shop_id={bc.shop_id} to shop_name='{bc.shop_name}' from NLU entity.")
                else:
                    try:
                        bc.shop_id = int(entity_value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert shop_id '{entity_value}' to int.")
                        bc.shop_id = None
                
                if bc.shop_name:
                    logger.info(f"Shop name '{bc.shop_name}' is already present.")
                elif state.recent_tool_results.last_shop_search:
                    logger.info(f"Attempting to find shop name for shop_id={bc.shop_id} in last_shop_search.")
                    shops = state.recent_tool_results.last_shop_search
                    if isinstance(shops, dict):
                        shops = shops.get("data", [])
                    
                    for shop_item in shops:
                        shop_id_val = _get_field_value(shop_item, 'id')
                        if shop_id_val is not None and int(shop_id_val) == bc.shop_id:
                            bc.shop_name = _get_field_value(shop_item, 'name')
                            logger.info(f"Resolved shop_id={bc.shop_id} to shop_name='{bc.shop_name}' from recent shop search.")
                            break
                
                if not bc.shop_name:
                     logger.warning(f"Could not resolve shop name for shop_id={bc.shop_id}. Name remains missing.")

                if state.pending_slot_to_fill in ["shop_id"]:
                    state.pending_slot_to_fill = None
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
                    if nlu_duration_entity and not package_selected:
                        bc.duration = nlu_duration_entity.value
                    else:
                        first_duration = durations[0]
                        bc.duration = _get_field_value(first_duration, "duration")
                logger.info(f"Setting course for course entity: ID={bc.course_id}, Name={bc.course_name}, Duration={bc.duration}")


            elif entity.type == EntityType.COURSE_ID:
                # This is a simplified check. A more robust implementation might be needed.
                if isinstance(entity.value, dict) and "courseType" in entity.value:
                    if entity.value["courseType"] == "main":
                        bc.course_id = int(entity.value["courseId"])
                    else:
                        if bc.addon_ids is None:
                            bc.addon_ids = []
                        bc.addon_ids.append(int(entity.value["courseId"]))
                elif isinstance(entity.value, (int, str)):
                    # Fallback for when courseType is not specified
                    if bc.course_id is None:
                        bc.course_id = int(entity.value)
                    else:
                        if bc.addon_ids is None:
                            bc.addon_ids = []
                        bc.addon_ids.append(int(entity.value))
                
                if bc.course_name is None and state.recent_tool_results.last_course_search and state.recent_tool_results.last_course_search.get("data"):
                    logger.info(f"Found last_course_search results: {state.recent_tool_results.last_course_search}")
                    courses = state.recent_tool_results.last_course_search["data"]
                    for course_item in courses:
                        course_id_val = _get_field_value(course_item, "id")
                        if course_id_val is not None and int(course_id_val) == bc.course_id:
                            bc.course_name = _get_field_value(course_item, "name")
                            logger.info(f"Found and set course_name: {bc.course_name}")
                            break
                else:
                    logger.warning("last_course_search results not found.")
            
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
            elif entity.type == EntityType.THERAPIST_ID:
                therapist_value = entity.value
                if isinstance(therapist_value, dict):
                    bc.therapist_id = _get_field_value(
                        therapist_value, "therapistId", bc.therapist_id
                    )
                    bc.therapist_name = _get_field_value(
                        therapist_value, "name", bc.therapist_name
                    )
                else:
                    try:
                        bc.therapist_id = int(therapist_value)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Could not convert therapist_id '{therapist_value}' to int."
                        )
                        bc.therapist_id = None

                if (
                    bc.therapist_name is None
                    and state.recent_tool_results.last_therapist_search
                ):
                    therapists = state.recent_tool_results.last_therapist_search.get(
                        "data", []
                    )
                    for t in therapists:
                        therapist_id_val = _get_field_value(t, "therapistId")
                        if (
                            therapist_id_val is not None
                            and int(therapist_id_val) == bc.therapist_id
                        ):
                            bc.therapist_name = _get_field_value(t, "name")
                            break
                if state.phase == ConversationPhase.SELECTING_THERAPIST:
                    state.phase = ConversationPhase.CONFIRMING_BOOKING
                    state.pending_slot_to_fill = "phone_number"
                if state.pending_slot_to_fill == "therapist_id":
                    state.pending_slot_to_fill = None
                    
            elif entity.type == EntityType.THERAPIST_NAME:
                bc.therapist_name = entity.value
                if state.recent_tool_results.last_therapist_search:
                    therapists = state.recent_tool_results.last_therapist_search.get(
                        "data", []
                    )
                    for t in therapists:
                        therapist_id_val = _get_field_value(t, "therapistId")
                        therapist_name_val = _get_field_value(t, "name")

                        if (
                            therapist_name_val
                            and entity.value.lower() in therapist_name_val.lower()
                        ):
                            if therapist_id_val is not None:
                                bc.therapist_id = int(therapist_id_val)
                            bc.therapist_name = therapist_name_val
                            break
                if state.phase == ConversationPhase.SELECTING_THERAPIST:
                    state.phase = ConversationPhase.CONFIRMING_BOOKING
                    state.pending_slot_to_fill = "phone_number"
                if state.pending_slot_to_fill == "therapist_name":
                    state.pending_slot_to_fill = None

            elif entity.type == EntityType.DATE:
                bc.date = entity.value
                if state.pending_slot_to_fill == "date":
                    state.pending_slot_to_fill = None

            elif entity.type == EntityType.DURATION:
                if not package_selected:
                    bc.duration = entity.value
                    if state.pending_slot_to_fill == "duration":
                        state.pending_slot_to_fill = None
                else:
                    logger.info("Ignoring NLU duration because a package was selected.")

            elif entity.type == EntityType.NUMBER_OF_PEOPLE:
                bc.number_of_people = entity.value
                if state.pending_slot_to_fill == "number_of_people":
                    state.pending_slot_to_fill = None

            elif entity.type == EntityType.TIME:
                bc.start_time = entity.value
                if state.pending_slot_to_fill == "start_time":
                    state.pending_slot_to_fill = None

            elif entity.type == EntityType.PHONE_NUMBER:
                logger.critical(
                    f"BUGTRACE: Assigning phone_number. "
                    f"entity.type={entity.type}, "
                    f"entity.value='{entity.value}', "
                    f"entity.raw_text='{entity.raw_text}', "
                    f"current.phone_number='{bc.phone_number}', "
                    f"current.date='{bc.date}'"
                )
                bc.phone_number = entity.value
                if state.pending_slot_to_fill == "phone_number":
                    state.pending_slot_to_fill = None

            elif entity.type == EntityType.BOOKING_CODE:
                bc.booking_code = entity.value
                if state.pending_slot_to_fill == "booking_code":
                    state.pending_slot_to_fill = None
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



