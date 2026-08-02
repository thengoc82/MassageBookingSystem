# chatbot/models/conversation.py
from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """
    Represents a conversation between a user and the chatbot.
    """

    history: list[tuple[str, str]] = Field(default_factory=list)

    def add_message(self, role: str, content: str):
        self.history.append((role, content))

    @property
    def is_empty(self) -> bool:
        return not self.history

    def format(self) -> str:
        return "\n".join([f"{role}: {content}" for role, content in self.history])
