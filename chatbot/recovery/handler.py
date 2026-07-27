from logging import Logger

from chatbot.conversation.state import ConversationManager, ConversationState
from chatbot.observability.logging import get_logger
from chatbot.observability.metrics import get_metrics
from chatbot.session.store import SessionData


class RecoveryHandler:
    """Handles conversation recovery from various failure modes."""

    def __init__(
        self,
        manager: ConversationManager | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._manager = manager or ConversationManager()
        self._logger = logger or get_logger(__name__)

    def handle_failure(
        self,
        error: Exception,
        state: ConversationState,
        session: SessionData,
    ) -> tuple[ConversationState, str]:
        """Recovers from an error, returning a safe state and user message."""
        get_metrics().incr("recovery_triggered", labels={"error_type": type(error).__name__})

        self._logger.error(
            "Conversation failure",
            exc_info=error,
            extra={
                "session_id": session.session_id,
                "user_id": session.user_id,
                "current_phase": state.phase.value,
            },
        )

        # ponytail: simple reset-on-error strategy.
        # Add more granular recovery when specific states can be salvaged, e.g.,
        # by re-prompting for confirmation if a tool failed intermittently.
        new_state = self._manager.reset(state)
        message = (
            "I'm sorry, I ran into an unexpected issue. Let's start over. "
            "How can I help you?"
        )

        return new_state, message
