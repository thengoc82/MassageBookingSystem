# chatbot/prompts/response.py
RESPONSE_PROMPT = """
Your task is to generate a natural language response to the user.

Plan: {{ plan.model_dump_json() }}
Tool result: {{ result }}

Generate a friendly, conversational response.
"""
