import json

import openai

from app.interfaces import LLMService


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
                {"role": "system", "content": "Analyze the message and context, extract intent and parameters as JSON."},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content or "{}")
