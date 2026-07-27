"""Tests for Phase 0 — Tool Registry"""
import pytest
from chatbot.tools.base import BaseTool
from chatbot.tools.registry import ToolRegistry
from pydantic import BaseModel


class TestTool(BaseTool):
    def __init__(self):
        super().__init__("test_tool", BaseModel, BaseModel)

    async def execute(self, request: BaseModel) -> BaseModel:
        return BaseModel()


class AnotherTestTool(BaseTool):
    def __init__(self):
        super().__init__("another_test_tool", BaseModel, BaseModel)

    async def execute(self, request: BaseModel) -> BaseModel:
        return BaseModel()


def test_registry_register_and_get():
    registry = ToolRegistry()
    tool = TestTool()
    registry.register("test_tool", tool)

    assert registry.get("test_tool") is tool


def test_registry_list():
    registry = ToolRegistry()
    registry.register("tool1", TestTool())
    registry.register("tool2", AnotherTestTool())

    assert set(registry.list()) == {"tool1", "tool2"}


def test_registry_get_missing_raises():
    registry = ToolRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")
