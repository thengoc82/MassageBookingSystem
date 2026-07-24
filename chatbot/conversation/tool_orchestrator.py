# chatbot/conversation/tool_orchestrator.py
from typing import Any, Dict

from chatbot.models.plan import Plan

from chatbot.tools.registry import ToolRegistry


class ToolOrchestrator:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def execute_tool(self, plan: Plan) -> Dict[str, Any]:
        """
        Executes the tool specified in the plan.
        """
        if not plan.tool_name:
            raise ValueError("No tool specified in the plan")

        tool = self.tool_registry.get_tool(plan.tool_name)
        if not tool:
            raise ValueError(f"Tool '{plan.tool_name}' not found")

        # Validate arguments using the tool's request_model
        validated_args = tool.request_model(**plan.tool_args)

        # Execute the tool and return the result
        return tool.execute(**validated_args.dict())
