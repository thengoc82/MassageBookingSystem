from dataclasses import dataclass, field


@dataclass
class Conversation:
    """Ordered chat messages stored with a session."""

    history: list[list[str]] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.history.append([role, content])

    def is_empty(self) -> bool:
        return not self.history

    def format(self) -> str:
        return "\n".join(f"{role}: {content}" for role, content in self.history)
