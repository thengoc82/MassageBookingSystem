# chatbot/conversation/intent_extractor.py
from chatbot.app.llm import LLMService
from chatbot.models.conversation import Conversation
from chatbot.models.intent import Intent, IntentType
from chatbot.prompts.intent import INTENT_EXTRACTION_PROMPT


class IntentExtractor:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def extract(self, conversation: Conversation) -> Intent:
        """
        Extracts the user's intent from the conversation.
        """
        if conversation.is_empty():
            return Intent(intent=IntentType.UNKNOWN)

        return self.llm_service.json_completion(
            prompt=INTENT_EXTRACTION_PROMPT,
            conversation=conversation,
            response_model=Intent,
        )
