import json

import openai

from chatbot.app.interfaces import LLMService


class OpenAILLMService(LLMService):
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(self, prompt: str, context: dict) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful massage booking assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content or ""

    async def extract_intent(self, text: str, context: dict) -> dict:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze the message and context, extract intent and parameters "
                        "as JSON."
                    ),
                },
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")

    async def json_completion(
        self,
        prompt: str,
        conversation: Any,
        response_model: type,
    ) -> Any:
        """Generic JSON completion: send prompt + conversation, parse into pydantic model."""
        from chatbot.models.intent import IntentType

        history_text = conversation.format() if hasattr(conversation, "format") else str(conversation)
        system_msg = (
            "You are a helpful massage booking assistant. "
            "Respond in JSON matching the requested schema."
        )
        user_msg = f"{prompt}\n\nConversation:\n{history_text}\n\nRespond in JSON."
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        # Coerce intent strings to enum
        if "intent" in data and isinstance(data["intent"], str):
            try:
                data["intent"] = IntentType(data["intent"])
            except ValueError:
                data["intent"] = IntentType.UNKNOWN
        return response_model(**data)
