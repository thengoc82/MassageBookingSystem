from typing import Any
from datetime import datetime, timedelta

from chatbot.conversation.state import ConversationState, BookingContext, RecentToolResults, ConversationPhase
from chatbot.session.store import RedisSessionStore

class DialogueStateTracker:
    def __init__(self, session_store: RedisSessionStore, session_id: str):
        self._session_store = session_store
        self._session_id = session_id
        self._state: ConversationState | None = None

    async def load_state(self) -> ConversationState:
        session = await self._session_store.get_session(self._session_id)
        if session:
            self._state = session.conversation_state
        else:
            # Initialize a new conversation state if no session exists
            self._state = ConversationState()
            await self._session_store.create_session(self._session_id)
            await self._session_store.update_conversation_state(self._session_id, self._state)
        return self._state

    async def save_state(self) -> None:
        if self._state:
            await self._session_store.update_conversation_state(self._session_id, self._state)

    def get_state(self) -> ConversationState:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        return self._state

    def update_booking_context(self, updates: dict) -> None:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        
        # Only update fields that are explicitly provided and are part of BookingContext
        for key, value in updates.items():
            if hasattr(self._state.booking_context, key):
                setattr(self._state.booking_context, key, value)

    def update_recent_tool_results(self, tool_name: str, results: Any) -> None:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        
        # Store raw tool result
        self._state.last_tool_result = {
            "tool_name": tool_name,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

        # Update structured recent tool results
        if tool_name == "search_shops":
            self._state.recent_tool_results.last_shop_search = results
        elif tool_name == "search_slots":
            self._state.recent_tool_results.last_slot_search = results
        elif tool_name == "search_therapists":
            self._state.recent_tool_results.last_therapist_search = results
        elif tool_name == "lookup_booking":
            self._state.recent_tool_results.last_booking_lookup = results
        elif tool_name == "faq_search":
            self._state.recent_tool_results.faq_search_results = results
        # Add other tool result mappings as needed

    def update_conversation_attributes(self, **kwargs) -> None:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                # Only update previous_intent if current_intent is being changed and was already set
                if key == "current_intent" and self._state.current_intent != value and self._state.current_intent is not None:
                    self._state.previous_intent = self._state.current_intent
                setattr(self._state, key, value)
                if key == "current_intent":
                    self._state.previous_intent = self._state.current_intent # This assignment was before the update

    def update_extracted_entities(self, entities: dict) -> None:
        """Merge newly extracted entities into the recent_extracted_entities."""
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        self._state.recent_extracted_entities.update(entities)

    def resolve_reference(self, reference: str, context_field: str | None = None) -> Any:
        """
        Resolves conversational references like "that one", "the second one", "tomorrow".
        This is a placeholder for actual reference resolution logic.
        """
        # This will be more complex and likely involve LLM for interpretation
        # For now, it's a stub to show where it would go.
        # It needs to consider booking_context, recent_tool_results, and recent_extracted_entities.
        if reference == "tomorrow":
            # Example: resolve 'tomorrow' to a date
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Add logic for "that one", "the first one", etc. using recent_tool_results
        # e.g., if context_field is "shop", try to resolve against last_shop_search
        return None

    def reset_state(self) -> None:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        self._state = ConversationState() # Resets to initial state
        # Note: This will not clear the session in Redis, only the in-memory state.
        # A separate method would be needed to delete the session from Redis.

    async def clear_booking_context(self) -> None:
        """Clears only the booking-related context."""
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        self._state.booking_context = BookingContext()
        await self.save_state()

    def set_phase(self, phase: ConversationPhase) -> None:
        if not self._state:
            raise ValueError("State not loaded. Call load_state first.")
        self._state.phase = phase
