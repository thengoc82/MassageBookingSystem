# chatbot/conversation/intent_extractor.py
from chatbot.app.llm import LLMService
from chatbot.models.conversation import Conversation
from chatbot.models.intent import Intent, IntentType
from chatbot.prompts.intent import INTENT_EXTRACTION_PROMPT


class IntentExtractor:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def extract(self, conversation: Conversation) -> Intent:
        """
        Extracts the user's intent from the conversation.
        """
        if conversation.is_empty():
            return Intent(intent=IntentType.UNKNOWN)

        return await self.llm_service.json_completion(
            prompt=INTENT_EXTRACTION_PROMPT,
            conversation=conversation,
            response_model=Intent,
        )

    async def extract_details(self, message: str, context: dict) -> dict:
        """Ask the LLM for candidate fields; callers validate before applying them."""
        result = await self.llm_service.extract_intent(message, context)
        slots = result.get("slots") if isinstance(result, dict) else None
        return slots if isinstance(slots, dict) else {}
