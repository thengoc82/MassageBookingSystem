# chatbot/prompts/plan.py
PLANNER_PROMPT = """
Your task is to plan the next step for the conversation based on the dialogue state, user intent, slots, and last message.

Current phase: {{ state.phase }}
Booking context: {{ state.booking_context.model_dump_json() }}
Recent tool results: {{ recent_tool_results }}
Extracted entities: {{ recent_extracted_entities }}

Current intent: {{ current_intent }}
Previous intent: {{ previous_intent }}
Current goal: {{ current_goal }}
Last planner decision: {{ last_planner_decision }}

User input: {{ user_input }}
User intent (extracted): {{ intent }}
User slots (extracted): {{ slots }}

You can use the following tools:
- searchShops
- searchCourses
- searchAvailableSlots
- getTherapists
- checkEligibility
- lookupBooking
- faqSearch

Your response should be a JSON object with the plan.

Example 1:
{
  "tool_name": "searchShops",
  "tool_args": {},
  "response": "Let me find some shops for you."
}

Example 2:
{
  "tool_name": null,
  "tool_args": {},
  "response": "Hello! How can I help you today?"
}
"""
