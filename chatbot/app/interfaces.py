from typing import Protocol


class ToolInterface(Protocol):
    async def execute(self, request: dict) -> dict:
        ...