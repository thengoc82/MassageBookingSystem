from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

RequestT = TypeVar("RequestT", bound=BaseModel)
ResponseT = TypeVar("ResponseT", bound=BaseModel)


class BaseTool(ABC, Generic[RequestT, ResponseT]):
    """Base class for all tools with typed request/response."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def execute(self, request: RequestT) -> ResponseT:
        """Execute the tool with typed request and return typed response."""
        ...

    async def execute_dict(self, request: dict[str, Any]) -> dict[str, Any]:
        """Execute with dict input/output for registry compatibility."""
        raise NotImplementedError("Subclasses must implement execute_dict or use adapter")