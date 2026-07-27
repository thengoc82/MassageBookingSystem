
from .base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, name: str, tool: BaseTool) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def get_tool(self, name: str) -> BaseTool | None:
        """Return tool by name or None if not registered."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> list[str]:
        return list(self._tools.keys())
