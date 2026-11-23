# chatbot/conversation/response_generator.py
from chatbot.app.llm import LLMService
from chatbot.models.conversation import Conversation
from chatbot.prompts.response import RESPONSE_PROMPT


class ResponseGenerator:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def generate_response(self, conversation: Conversation) -> str:
        """
        Generates a response to the user.
        """
        return await self.llm_service.generate_response(
            f"{RESPONSE_PROMPT}\n\nConversation:\n{conversation.format()}", {}
        )
