from typing import Any, Protocol

from pydantic import BaseModel


class ToolInterface(Protocol):
    async def execute(self, request: dict) -> dict:
        ...


class LLMService(Protocol):
    async def generate_response(self, prompt: str, context: dict[str, Any]) -> str:
        ...

    async def generate_grounded_answer(
        self, question: str, excerpts: list[dict[str, str]]
    ) -> str:
        ...

    async def extract_intent(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        ...

    async def json_completion(
        self,
        prompt: str,
        conversation: Any,
        response_model: type[BaseModel],
    ) -> BaseModel:
        ...
