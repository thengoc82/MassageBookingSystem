# chatbot/conversation/planner.py
from chatbot.models.conversation import Conversation
from chatbot.models.plan import Plan
from chatbot.prompts.plan import PLANNER_PROMPT

from chatbot.app.llm import LLMService


class Planner:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def create_plan(self, conversation: Conversation) -> Plan:
        """
        Creates a plan for the conversation.
        """
        return self.llm_service.json_completion(
            prompt=PLANNER_PROMPT,
            conversation=conversation,
            response_model=Plan,
        )
