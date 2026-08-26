# chatbot/conversation/parser_result.py
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class ParsedSlot:
    """Represents a single piece of information extracted from user input."""
    name: str
    value: Any
    confidence: float = 1.0
    source: str = "unknown"  # e.g., 'nlu', 'regex', 'ordinal'

@dataclass
class ParseResult:
    """The structured output of the slot parsing process."""
    parsed_slots: Dict[str, ParsedSlot] = field(default_factory=dict)

    def add_slot(self, name: str, value: Any, source: str, confidence: float = 1.0):
        # Do not overwrite a slot that has been filled with higher confidence
        if name in self.parsed_slots and self.parsed_slots[name].confidence > confidence:
            return
        self.parsed_slots[name] = ParsedSlot(name=name, value=value, source=source, confidence=confidence)

    @property
    def has_results(self) -> bool:
        return bool(self.parsed_slots)

