"""Tests for Phase 0 — Interfaces"""
import pytest

from tools.base import BaseTool


class TestTool(BaseTool):
    def __init__(self):
        super().__init__("test_tool")

    async def execute(self, request: dict) -> dict:
        return {"result": "test"}


def test_tool_interface_protocol():
    tool = TestTool()
    assert isinstance(tool, BaseTool)
    assert hasattr(tool, 'execute')


def test_base_tool_is_abstract():
    with pytest.raises(TypeError):
        BaseTool()