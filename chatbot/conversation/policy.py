# chatbot/conversation/policy.py
from __future__ import annotations
from chatbot.nlu.models import Intent

class DialoguePolicyManager:
    # ... (rest of the class)

    def decide(
        self,
        state: ConversationState,
        intent: str,
        message: str = "",
        nlu_result: Any | None = None,
    ) -> PolicyDecision:
        # Handle therapist skip directly
        if (
            state.phase == ConversationPhase.SELECTING_THERAPIST
            and intent == Intent.DENIAL
        ):
            state.booking_context.therapist_id = None
            state.booking_context.therapist_name = None
            state.phase = ConversationPhase.CONFIRMING_BOOKING
            state.pending_slot_to_fill = "phone_number"
            logger.info("User skipped therapist selection. Resuming booking.")
            return PolicyDecision(action=Action.RESUME_BOOKING, goal=state.current_goal)

        # ... (rest of the decide method)

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chatbot.conversation.goals import Goal
from chatbot.conversation.state import BookingContext, ConversationState, ConversationPhase

logger = logging.getLogger(__name__)



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
]

_REQUIRED_FINAL_SLOTS = ("phone_number",)


_FINAL_BOOKING_SLOTS = (
    "shop_id",
    "date",
    "number_of_people",
    "duration",
    "course_id",
    "start_time",
    "phone_number",
)


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
            # Special check for therapist_id, which is not strictly required
            if slot == "therapist_id":
                if getattr(context, "therapist_preference_type", None) == "any":
                    continue # Skip if user doesn't want a specific therapist
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
            return ConversationPhase.GREETING
        if slot_name == "number_of_people":
            return ConversationPhase.COLLECTING_PEOPLE
        if slot_name == "duration":
            return ConversationPhase.COLLECTING_DURATION
        if "shop" in slot_name:
            return ConversationPhase.SEARCHING_SHOPS
        if "course" in slot_name:
            return ConversationPhase.SELECTING_PACKAGE
        if "therapist" in slot_name:
            return ConversationPhase.SELECTING_THERAPIST
        if "date" in slot_name:
            return ConversationPhase.SELECTING_DATE
        if "time" in slot_name:
            return ConversationPhase.SEARCHING_SLOTS
        if "phone" in slot_name or "eligibility" in slot_name:
            return ConversationPhase.CHECKING_ELIGIBILITY
        return ConversationPhase.COLLECTING_INFO

    def _handle_slot_shortcut(self, state: ConversationState, message: str) -> PolicyDecision | None:
        """Handle slot-filling shortcuts before main policy logic."""
        # Shortcut for number_of_people
        if (state.phase == ConversationPhase.COLLECTING_PEOPLE or state.pending_slot_to_fill == "number_of_people"):
            logger.info(f"[Shortcut Check] Current phase: {state.phase}, pending_slot_to_fill: {state.pending_slot_to_fill}, Raw message: '{message}'")
            try:
                num = int(message.strip())
                logger.info(f"[Shortcut Check] Parsed number: {num}")
                if 1 <= num <= 3:
                    state.booking_context.number_of_people = num
                    state.pending_slot_to_fill = None  # Clear pending slot
                    logger.info(f"[Shortcut Check] Validation: passed, booking_context.number_of_people = {state.booking_context.number_of_people}")
                    # After filling the slot, re-evaluate the next step
                    return self._next_booking_step(state)
                else:
                    logger.warning(f"[Shortcut Check] Validation: failed, number out of range (1-3).")
                    return PolicyDecision(
                        action=Action.ASK_SLOT,
                        slot="number_of_people",
                        goal=Goal.BOOK_APPOINTMENT,
                        message="Please enter the number of people (1 to 3)."
                    )
            except ValueError:
                logger.info(f"[Shortcut Check] Shortcut matched: no (message is not an integer).")
                return None
        return None

    def decide(
        self,
        state: ConversationState,
        intent: str,
        message: str = "",
        nlu_result: Any | None = None,
    ) -> PolicyDecision:
        # 0. Pre-extract booking_code / phone_number if relevant, as NLU might miss it.
        self._extract_lookup_hints(state, message)

        # NEW: Handle slot-filling shortcuts first
        shortcut_decision = self._handle_slot_shortcut(state, message)
        if shortcut_decision:
            return shortcut_decision

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

        # Handle therapist skip directly
        if (
            state.phase == ConversationPhase.SELECTING_THERAPIST
            and intent == Intent.DENIAL
        ):
            state.booking_context.therapist_id = None
            state.booking_context.therapist_name = None
            # state.phase = ConversationPhase.CONFIRMING_BOOKING
            state.pending_slot_to_fill = "phone_number"
            logger.info("User skipped therapist selection. Resuming booking.")
            return self._next_booking_step(state)
        
        if intent == "greeting":
            return PolicyDecision(
                action=Action.NO_ACTION,
                message="Hi! How can I help you?",
            )
        
        if intent == "confirmation":
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

        if state.phase == ConversationPhase.FAQ_PROMPT:
            logger.debug("Phase is FAQ_PROMPT, moving to answer the question.")
            return PolicyDecision(action=Action.ANSWER_FAQ, goal=Goal.ASK_FAQ)

        # 5. Route based on primary goal/intent.
        if intent in {"cancel_booking", "modify_booking"}:
            return self._decide_write_intent(state, intent)
        if intent == "lookup_booking":
            return self._decide_lookup(state)
        if intent == "faq":
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
                slot="phone_number",
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
            phone_match = re.search(r"\b(0\d{9,10}|\+?\d{1,3}[\s-]?\d{7,9})\b", message)
            if phone_match:
                # Normalize by removing non-digit characters.
                bc.phone_number = "".join(filter(str.isdigit, phone_match.group(0)))

    @staticmethod
    def _booking_args(bc: BookingContext) -> dict[str, Any]:
        args = {k: v for k, v in bc.model_dump().items() if v is not None}
        
        # Convert addon_ids to the expected structure for the booking payload
        if 'addon_ids' in args and args['addon_ids']:
             unique_addon_ids = sorted(list(set(args['addon_ids'])))
             args['addOns'] = [
                 {"courseId": a_id, "personIndex": 1} for a_id in unique_addon_ids
             ]
        
        # Remove addon_ids as it's not part of the final payload
        args.pop('addon_ids', None)
        
        return args

    def _decide_faq(self, state: ConversationState) -> PolicyDecision:
        # If we are in the middle of another goal, save it so we can resume later.
        if state.current_goal and state.current_goal != Goal.ASK_FAQ:
            state.previous_goal = state.current_goal
        
        state.current_goal = Goal.ASK_FAQ
        state.phase = ConversationPhase.FAQ_PROMPT
        
        # This is the initial entry to the FAQ flow. Just ask for the user's question.
        return PolicyDecision(
            action=Action.REQUEST_CLARIFICATION,
            goal=state.previous_goal,
            message="What would you like to know?"
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
        logger.debug(
            f"Deciding booking: phase={state.phase}, pending_slot={state.pending_slot_to_fill}, intent={intent}"
        )
        if state.current_goal != Goal.BOOK_APPOINTMENT:
            state.current_goal = Goal.BOOK_APPOINTMENT
            # If shop is missing, start there. Otherwise, assume we're collecting info.
            if not state.booking_context.shop_id:
                state.phase = ConversationPhase.SEARCHING_SHOPS
            else:
                state.phase = ConversationPhase.SEARCHING_SLOTS
            logger.debug("Goal not BOOK_APPOINTMENT, setting goal and phase.")

        # If a slot was pending and is now filled, clear it.
        if state.pending_slot_to_fill and getattr(
            state.booking_context, state.pending_slot_to_fill, None
        ) is not None:
            logger.debug(
                f"Pending slot '{state.pending_slot_to_fill}' was filled. Clearing."
            )
            state.pending_slot_to_fill = None

        # If a slot is explicitly pending, ask for it.
        if state.pending_slot_to_fill:
            logger.debug(f"Asking for pending slot: {state.pending_slot_to_fill}")
            return PolicyDecision(
                action=Action.ASK_SLOT,
                slot=state.pending_slot_to_fill,
                goal=Goal.BOOK_APPOINTMENT,
            )

        # Determine the next step in the booking flow.
        return self._next_booking_step(state)

    def _next_booking_step(self, state: ConversationState) -> PolicyDecision:
        bc = state.booking_context
        
        # Define the exact sequence of the conversation
        sequence = [
            "shop_id",
            "date",
            "number_of_people",
            "duration",
            "course_id", # This now covers main course and add-ons conceptually
            "start_time",
            "therapist_id", # Optional step
            "phone_number",
        ]

        # Find the first missing piece of information in the sequence
        next_missing_slot = None
        for slot in sequence:
            # Therapist selection is optional and conditional
            if slot == "therapist_id":
                if bc.number_of_people == 1 and bc.therapist_id is None and getattr(bc, "therapist_preference_type", None) != "any":
                    # Only ask if not already skipped
                    if state.phase != ConversationPhase.SELECTING_THERAPIST or Intent != Intent.DENIAL:
                         next_missing_slot = "therapist_id"
                         break
                continue

            if getattr(bc, slot, None) is None:
                next_missing_slot = slot
                break
        
        logger.debug(f"Next missing slot in sequence: {next_missing_slot}")

        # If a slot is explicitly pending from a previous turn, prioritize it
        if state.pending_slot_to_fill:
            logger.debug(f"Prioritizing explicitly pending slot: {state.pending_slot_to_fill}")
            next_missing_slot = state.pending_slot_to_fill


        # --- Step-by-step logic based on the missing slot ---

        # 1. Handle prerequisites for tools
        if next_missing_slot == "shop_id" and not _tool_already_run(state, "searchShops"):
             logger.debug("Prerequisite: Running search_shops tool.")
             state.phase = ConversationPhase.SEARCHING_SHOPS
             return PolicyDecision(
                 action=Action.RUN_TOOL, tool="search_shops", goal=Goal.BOOK_APPOINTMENT
             )

        if next_missing_slot == "course_id" and bc.shop_id and not _tool_already_run(state, "searchCourses"):
            logger.debug("Prerequisite: Running searchCourses tool.")
            state.phase = ConversationPhase.SELECTING_PACKAGE
            return PolicyDecision(
                action=Action.RUN_TOOL,
                tool="search_courses",
                goal=Goal.BOOK_APPOINTMENT,
                payload={"shopId": bc.shop_id, "duration": bc.duration},
            )

        if next_missing_slot == "start_time":
            # Check if all prerequisites for searching slots are met
            slot_search_prereqs = ["shop_id", "date", "number_of_people", "duration", "course_id"]
            if all(getattr(bc, p, None) is not None for p in slot_search_prereqs):
                 if not _tool_already_run(state, "searchAvailableSlots"):
                    logger.debug("Prerequisite: Running searchAvailableSlots tool.")
                    state.phase = ConversationPhase.SEARCHING_SLOTS
                    return PolicyDecision(
                        action=Action.RUN_TOOL,
                        tool="search_available_slots",
                        goal=Goal.BOOK_APPOINTMENT,
                        payload=self._booking_args(bc)
                    )
            else:
                 # If prerequisites are not met, find the first one that's missing and ask for it
                 for prereq in slot_search_prereqs:
                     if getattr(bc, prereq, None) is None:
                         next_missing_slot = prereq
                         break


        if next_missing_slot == "therapist_id" and bc.number_of_people == 1 and not _tool_already_run(state, "getTherapists"):
            therapist_search_prereqs = ["shop_id", "date", "start_time", "duration"]
            if all(getattr(bc, p, None) is not None for p in therapist_search_prereqs):
                logger.debug("Prerequisite: Running getTherapists tool.")
                state.phase = ConversationPhase.SELECTING_THERAPIST
                return PolicyDecision(
                    action=Action.RUN_TOOL,
                    tool="get_therapists",
                    goal=Goal.BOOK_APPOINTMENT,
                    payload=self._booking_args(bc)
                )

        # 2. If a slot is missing, ask for it
        if next_missing_slot:
            logger.debug(f"Asking for slot: {next_missing_slot}")
            state.phase = self.get_phase_for_slot(next_missing_slot)
            return PolicyDecision(
                action=Action.ASK_SLOT,
                slot=next_missing_slot,
                goal=Goal.BOOK_APPOINTMENT,
            )

        # 3. If all slots are filled, move to confirmation
        if not next_missing_slot and bc.phone_number:
            logger.info("All information gathered. Moving to final confirmation.")
            state.phase = ConversationPhase.CONFIRMING_BOOKING
            booking_summary = self._generate_booking_summary(bc)
            state.pending_confirm = {
                "tool": "createBooking",
                "intent": "create_booking",
                "arguments": self._booking_args(bc),
            }
            return PolicyDecision(
                action=Action.CONFIRM_ACTION,
                goal=Goal.BOOK_APPOINTMENT,
                tool="createBooking",
                payload=self._booking_args(bc),
                message=f"Please review your booking details:\n{booking_summary}\n\nShall I proceed with the booking?",
            )

        # 4. Fallback: This should ideally not be reached.
        logger.error(
            f"Fallback reached in booking step. Context: {self._booking_args(bc)}"
        )
        return PolicyDecision(
            action=Action.REQUEST_CLARIFICATION,
            message="I'm not sure what to do next. Could you clarify?",
        )
    
    def _generate_booking_summary(self, context: BookingContext) -> str:
        """Generates a human-readable summary of the booking."""
        summary = [
            f"- Shop: {context.shop_name or context.shop_id}",
            f"- Date: {context.date}",
            f"- Time: {context.start_time}",
            f"- Guests: {context.number_of_people}",
            f"- Main Course: {context.course_name or context.course_id}",
        ]
        if context.addon_names:
            summary.append(f"- Add-ons: {', '.join(context.addon_names)}")
        
        summary.append(f"- Total Duration: {context.duration} minutes")

        if context.therapist_name:
            summary.append(f"- Therapist: {context.therapist_name}")
        
        summary.append(f"- Phone Number: {context.phone_number}")
        
        return "\n".join(summary)


    def _is_booking_complete(self, context: BookingContext) -> bool:
        """Legacy check, the new sequence-based check is primary."""
        # This can be simplified or removed, but we'll keep it for now
        # to avoid breaking other parts of the system that might use it.
        required = ["shop_id", "date", "number_of_people", "course_id", "start_time", "phone_number"]
        return all(getattr(context, slot, None) is not None for slot in required)


    def _decide_confirmation(
        self, state: ConversationState, intent: str, message: str
    ) -> PolicyDecision:
        pending = state.pending_confirm or {}
        
        if not pending:
            logger.warning("Confirmation intent received, but nothing is pending confirmation.")
            return PolicyDecision(
                action=Action.REQUEST_CLARIFICATION,
                message="Sorry, I don't have anything to confirm right now. What would you like to do?",
            )

        text = message.strip().lower()

        if intent == "confirmation" or _message_contains_token(text, _YES_TOKENS):
            logger.info("Confirmation matched YES token or confirmation intent.")
            tool_to_execute = pending.get("tool")
            tool_payload = pending.get("arguments", {})
            logger.info(f"Executing write action for tool: {tool_to_execute} with payload: {tool_payload}")
            decision = PolicyDecision(
                action=Action.EXECUTE_WRITE_ACTION,
                tool=tool_to_execute,
                goal=state.current_goal,
                payload=tool_payload,
            )
            logger.info(f"Returning decision to execute write: {decision}")
            return decision

        if _message_contains_token(text, _NO_TOKENS):
            logger.info("Confirmation matched NO token.")
            state.pending_confirm = None
            return PolicyDecision(
                action=Action.CLEAR_PENDING_ACTION,
                message="Okay, I won't do that. What would you like to do instead?",
            )

        logger.warning(f"Confirmation did not match YES/NO tokens. Text: '{text}'")

        # If the user provides new information instead of confirming, it could be a correction.
        # For now, we'll just ask for a clear confirmation.
        return PolicyDecision(
            action=Action.CONFIRM_ACTION,
            tool=pending.get("tool"), # Pass the tool again
            goal=state.current_goal,
            payload=pending,
            message="Please confirm by saying 'yes' or 'no'.",
        )
