from typing import Any, Protocol


class ToolInterface(Protocol):
    async def execute(self, request: dict) -> dict:
        ...


class LLMService(Protocol):
    async def generate_response(self, prompt: str, context: dict[str, Any]) -> str:
        ...

    async def extract_intent(self, text: str, context: dict[str, Any]) -> dict[str, Any]:
        ...
