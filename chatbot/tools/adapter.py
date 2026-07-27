from typing import Any

from chatbot.tools.base import BaseTool


class ToolAdapter(BaseTool):
    """Adapter to wrap typed tools for registry compatibility."""

    def __init__(self, tool: BaseTool) -> None:
        super().__init__(
            tool.name, tool.RequestModel, tool.ResponseModel, tool.is_write
        )
        self._tool = tool

    async def execute(self, request: Any) -> Any:
        """Execute the tool with typed request and return typed response."""
        return await self._tool.execute(request)

    async def execute_dict(self, request: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._tool.execute(request)
            return {"success": True, "data": response}
        except Exception as e:  # noqa: BLE001
            return {"success": False, "error": {"code": "TOOL_ERROR", "message": str(e)}}
