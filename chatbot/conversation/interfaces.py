# chatbot/conversation/interfaces.py
from dataclasses import dataclass
from enum import Enum
from typing import Any

from chatbot.conversation.state import ConversationState


class MessageType(str, Enum):
    TEXT = "text"
    TOOL_RESULT = "tool_result"
    CONFIRMATION = "confirmation"
    ERROR = "error"


@dataclass
class IntentResponse:
    """Internal response from intent handler."""

    success: bool = True
    message: str = ""
    state: ConversationState | None = None
    data: Any = None
    error: str | None = None