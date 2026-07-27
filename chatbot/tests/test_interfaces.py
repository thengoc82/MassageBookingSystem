"""Tests for Phase 0 — Interfaces"""
import pytest
from chatbot.tools.base import BaseTool
from pydantic import BaseModel


class TestTool(BaseTool):
    def __init__(self):
        super().__init__("test_tool", BaseModel, BaseModel)

    async def execute(self, request: BaseModel) -> BaseModel:
        return BaseModel()


def test_tool_interface_protocol():
    tool = TestTool()
    assert isinstance(tool, BaseTool)
    assert hasattr(tool, 'execute')


def test_base_tool_is_abstract():
    with pytest.raises(TypeError):
        BaseTool()
