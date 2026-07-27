# chatbot/conversation/planner.py
from chatbot.app.llm import LLMService
from chatbot.models.conversation import Conversation
from chatbot.models.plan import Plan
from chatbot.prompts.plan import PLANNER_PROMPT
from chatbot.tools.registry import ToolRegistry


class Planner:
    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry):
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    def create_plan(self, conversation: Conversation) -> Plan:
        """
        Creates a plan for the conversation.
        The planner should not execute write tools directly.
        """
        plan = self.llm_service.json_completion(
            prompt=PLANNER_PROMPT,
            conversation=conversation,
            response_model=Plan,
        )

        if plan.tool_name:
            tool = self.tool_registry.get(plan.tool_name)
            if tool and tool.is_write:

                # This is a write tool, the plan is to propose an action, not execute.
                # The orchestrator will handle this.
                pass

        return plan

