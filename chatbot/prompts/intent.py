INTENT_EXTRACTION_PROMPT = (
    "Extract only booking details explicitly stated or unambiguously implied by the latest "
    "customer message. Return a JSON object with a 'slots' object. Allowed slots are "
    "date (YYYY-MM-DD), start_time (HH:MM), time_preference (morning, afternoon, "
    "evening, tonight, around:HH:MM, after:HH:MM, before:HH:MM), duration "
    "(minutes), number_of_people (integer), and phone_number (digits). "
    "Use the supplied local date for relative dates. Never copy old values into slots, "
    "invent a value, or propose a booking action. Omit anything uncertain."
)
