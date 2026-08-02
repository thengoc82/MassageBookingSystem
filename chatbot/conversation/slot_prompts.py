# chatbot/conversation/slot_prompts.py

SLOT_PROMPTS: dict[str, str] = {
    "area": "Which area are you interested in? e.g. Shinjuku, Shibuya, etc.",
    "date": "What date would you like?",
    "number_of_people": "How many guests?",
    "phone_number": "May I have your phone number?",
    "start_time": "Which time would you prefer?",
    "therapist_id": "Do you have a preferred therapist?",
    "shop_id": "Which shop would you like to visit?",
    "course_id": "Which massage course would you like?",
    "duration": "How long would you like the session to be?",
    "booking_code": "May I have your booking code, please?",
}


def get_prompt(slot_name: str) -> str:
    return SLOT_PROMPTS.get(
        slot_name, "Could you please provide that information?"
    )