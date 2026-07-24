# chatbot/conversation/tool_orchestrator.py
from datetime import datetime, timedelta
from typing import Any, Dict

from chatbot.conversation.state import ConversationState, PendingAction
from chatbot.models.plan import Plan
from chatbot.tools.registry import ToolRegistry


class ToolOrchestrator:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    async def propose_write_action(self, state: ConversationState, plan: Plan) -> None:
        """Propose a write action and store it in pending_action."""
        if not plan.tool_name:
            raise ValueError("No tool specified in the plan")

        tool = self.tool_registry.get_tool(plan.tool_name)
        if not tool or not tool.is_write:
            raise ValueError(f"Tool '{plan.tool_name}' is not a write tool or not found")

        # Validate arguments using the tool's request_model
        validated_args = tool.RequestModel(**plan.tool_args).model_dump()

        state.pending_action = PendingAction(
            tool_name=plan.tool_name,
            arguments=validated_args,
            status="pending",
            timestamp=datetime.now(),
        )

    async def execute_pending_action(self, state: ConversationState) -> Dict[str, Any]:
        """
        Executes the pending write action after confirmation.
        """
        if not state.pending_action:
            raise ValueError("No pending action to execute.")

        # Check for expiration
        if datetime.now() - state.pending_action.timestamp > timedelta(minutes=5):  # 5 minute timeout
            state.pending_action.status = "expired"
            state.pending_action = None  # Clear expired action
            raise ValueError("Pending action expired.")

        if state.pending_action.status == "executing":
            raise ValueError("Pending action is already executing.")

        state.pending_action.status = "executing"

        tool = self.tool_registry.get_tool(state.pending_action.tool_name)
        if not tool:
            state.pending_action.status = "cancelled"
            raise ValueError(f"Tool '{state.pending_action.tool_name}' not found.")

        try:
            # Execute the tool and return the result
            request_model_instance = tool.RequestModel(**state.pending_action.arguments)
            result = await tool.execute(request_model_instance)
            state.pending_action.status = "completed"
            state.pending_action = None  # Clear action after completion
            return result.model_dump()
        except Exception as e:
            state.pending_action.status = "cancelled"
            state.pending_action = None  # Clear action on failure
            raise e

    async def execute_tool(self, plan: Plan) -> Dict[str, Any]:
        """
        Executes the tool specified in the plan.
        """
        if not plan.tool_name:
            raise ValueError("No tool specified in the plan")

        tool = self.tool_registry.get_tool(plan.tool_name)
        if not tool:
            raise ValueError(f"Tool '{plan.tool_name}' not found")
        
        if tool.is_write:
            # For write tools, we don't execute directly. Planner proposes it.
            # This method should only be called for read tools.
            raise ValueError(f"Write tool '{plan.tool_name}' cannot be executed directly. Use propose_write_action.")

        # Validate arguments using the tool's request_model
        request_model_instance = tool.RequestModel(**plan.tool_args)

        # Execute the tool and return the result
        result = await tool.execute(request_model_instance)
        return result.model_dump()
