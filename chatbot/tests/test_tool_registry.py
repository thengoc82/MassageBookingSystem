"""Tests for Phase 0 — Tool Registry"""
import pytest

from tools.base import BaseTool
from tools.registry import ToolRegistry


class TestTool(BaseTool):
    def __init__(self):
        super().__init__("test_tool")

    async def execute(self, request: dict) -> dict:
        return {"result": "test"}


class AnotherTestTool(BaseTool):
    def __init__(self):
        super().__init__("another_test_tool")

    async def execute(self, request: dict) -> dict:
        return {"result": "another"}


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