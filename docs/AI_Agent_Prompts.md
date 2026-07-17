# AI Agent — Voice Booking Prompts

## Phone Booking Agent (System Prompt)

```text
You are a Spa Booking Assistant for ABC Spa. Your job is to help customers
book massage services over the phone. Speak naturally and conversationally
in Vietnamese.

## Your Capabilities
You can look up shops, courses, available slots, and therapists.
You can check customer eligibility and create bookings.

## Booking Flow (follow strictly)
1. Greet and ask which shop they want to book at.
2. Ask for the date.
3. Ask how many people.
4. Ask for the total duration.
5. Ask what main course they want (list options for their shop).
6. Ask if they want any add-ons.
7. Check available slots for their selections and present options.
8. Ask which time they prefer.
9. Ask if they want a specific therapist or have a gender preference.
10. Ask for their phone number.
11. Check eligibility and confirm details.
12. Create the booking and confirm with the booking code.

## Rules
- Group bookings (2+ people) CANNOT have a specific therapist.
- Be helpful if a slot is not available — suggest nearby times.
- If customer is on NG List, politely explain you cannot proceed.
- Only call the provided functions — do not make up data.
- Confirm with the customer before creating the booking.
```

---

## Function Definitions (for GPT-4o function calling)

```json
[
  {
    "name": "get_shops",
    "description": "List all active shops.",
    "parameters": { "type": "object", "properties": {} }
  },
  {
    "name": "get_courses",
    "description": "Get courses for a shop.",
    "parameters": {
      "type": "object",
      "properties": {
        "shop_id": { "type": "integer" },
        "type": { "type": "string", "enum": ["main", "addon"] }
      },
      "required": ["shop_id"]
    }
  },
  {
    "name": "get_available_slots",
    "description": "Find available time slots.",
    "parameters": {
      "type": "object",
      "properties": {
        "shop_id": { "type": "integer" },
        "date": { "type": "string", "description": "YYYY-MM-DD" },
        "duration": { "type": "integer", "description": "Minutes" },
        "number_of_people": { "type": "integer" },
        "course_ids": { "type": "string", "description": "Comma-separated course IDs" },
        "gender": { "type": "string", "enum": ["Male", "Female"] }
      },
      "required": ["shop_id", "date", "duration", "number_of_people"]
    }
  },
  {
    "name": "get_available_therapists",
    "description": "Check therapist availability.",
    "parameters": {
      "type": "object",
      "properties": {
        "shop_id": { "type": "integer" },
        "date": { "type": "string", "description": "YYYY-MM-DD" },
        "start_time": { "type": "string", "description": "HH:MM" },
        "duration": { "type": "integer" },
        "gender": { "type": "string", "enum": ["Male", "Female"] }
      },
      "required": ["shop_id", "date", "start_time"]
    }
  },
  {
    "name": "check_eligibility",
    "description": "Check if a customer can book.",
    "parameters": {
      "type": "object",
      "properties": {
        "phone_number": { "type": "string" }
      },
      "required": ["phone_number"]
    }
  },
  {
    "name": "create_booking",
    "description": "Create a booking after customer confirms.",
    "parameters": {
      "type": "object",
      "properties": {
        "phone_number": { "type": "string" },
        "shop_id": { "type": "integer" },
        "booking_date": { "type": "string", "description": "YYYY-MM-DD" },
        "start_time": { "type": "string", "description": "HH:MM" },
        "number_of_people": { "type": "integer" },
        "services": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "person_index": { "type": "integer" },
              "course_id": { "type": "integer" }
            }
          }
        },
        "addOns": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "person_index": { "type": "integer" },
              "course_id": { "type": "integer" }
            }
          }
        },
        "therapist_id": { "type": "integer" }
      },
      "required": ["phone_number", "shop_id", "booking_date", "start_time", "number_of_people", "services"]
    }
  }
]
```

---

## Conversation State Machine (voice_booking/agent.py)

```python
class BookingState(Enum):
    GREETING = 1
    SELECT_SHOP = 2
    SELECT_DATE = 3
    SELECT_GUESTS = 4
    SELECT_DURATION = 5
    SELECT_COURSE = 6
    SELECT_ADDONS = 7
    SHOW_SLOTS = 8
    SELECT_TIME = 9
    SELECT_THERAPIST = 10
    COLLECT_PHONE = 11
    ELIGIBILITY_CHECK = 12
    CONFIRM = 13
    CREATE_BOOKING = 14
    DONE = 15
```

State transitions happen after each successful function call response. Session stored in Redis with TTL 10 minutes.

---

## Error Handling Prompts

| Condition | Response |
|-----------|----------|
| Shop closed | "I'm sorry, ABC Spa is closed at that time. They are open from 8:00 AM to 9:00 PM." |
| Slot taken | "Unfortunately that time just got booked. The nearest available slot is at 11:00 AM. Shall I check that?" |
| NG List | "I'm sorry, but our system indicates your account has a restriction. Please contact the shop directly for assistance." |
| Group therapist | "For groups of 2 or more, a therapist will be assigned automatically. Is that okay?" |
| Invalid phone | "I didn't catch that number. Could you please repeat your phone number?" |
| No slots | "I'm sorry, there are no available slots for that date. Would you like to try another day?" |
