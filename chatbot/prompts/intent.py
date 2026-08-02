# chatbot/prompts/intent.py
INTENT_EXTRACTION_PROMPT = """
Your task is to extract the user's intent and any associated slots from the conversation.

Available intents are:
- GREETING: User says hello, hi, etc.
- GOODBYE: User says bye, see you, etc.
- HELP: User asks for help.
- BOOK_MASSAGE: User wants to book a massage.
- SEARCH_SHOPS: User wants to find a shop.
- SEARCH_COURSES: User wants to find a course/service.
- SEARCH_SLOTS: User wants to find available times.
- LOOKUP_BOOKING: User wants to check their booking.
- CANCEL_BOOKING: User wants to cancel their booking.
- MODIFY_BOOKING: User wants to modify their booking.
- CHECK_ELIGIBILITY: User wants to check their eligibility.
- FAQ: User has a general question.
- UNKNOWN: The user's intent is unclear.

Conversation history (most recent message is last):
{{ conversation.format() }}

Analyze the last user message in the context of the conversation and respond in JSON format with the extracted intent and slots.

Example:
User: "I want a 60 minute massage for 2 people tomorrow at 3pm"
{
  "intent": "BOOK_MASSAGE",
  "slots": {
    "duration": 60,
    "number_of_people": 2,
    "date": "tomorrow",
    "start_time": "3pm"
  },
  "confidence": 0.95
}
"""
