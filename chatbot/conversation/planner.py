# chatbot/conversation/planner.py
from chatbot.app.llm import LLMService
from chatbot.models.plan import Plan
from chatbot.prompts.plan import PLANNER_PROMPT
from chatbot.tools.registry import ToolRegistry
from chatbot.conversation.state import ConversationState


class Planner:
    def __init__(self, llm_service: LLMService, tool_registry: ToolRegistry):
        self.llm_service = llm_service
        self.tool_registry = tool_registry

    def create_plan(self, state: ConversationState, user_input: str, intent_data: dict) -> Plan:
        """
        Creates a plan for the conversation based on the current dialogue state.
        The planner should not execute write tools directly.
        """
        # Prepare the data for the prompt
        prompt_data = {
            "state": state,
            "user_input": user_input,
            "intent": intent_data.get("intent"),
            "slots": intent_data.get("slots", {}),
            "recent_extracted_entities": state.recent_extracted_entities,
            "recent_tool_results": state.recent_tool_results.model_dump_json(), # Pass as JSON string
            "current_intent": state.current_intent,
            "previous_intent": state.previous_intent,
            "current_goal": state.current_goal,
            "last_planner_decision": state.last_planner_decision,
        }

        plan = self.llm_service.json_completion(
            prompt=PLANNER_PROMPT,
            **prompt_data,
            response_model=Plan,
        )

        if plan.tool_name:
            tool = self.tool_registry.get(plan.tool_name)
            if tool and tool.is_write:

                # This is a write tool, the plan is to propose an action, not execute.
                # The orchestrator will handle this.
                pass

        return plan

