# Task 04 — Public booking access and staff-only transitions

**Status:** Implemented for local development on 2026-11-26; deployed code delivery and browser journey pending.

## Implementation

- Booking access uses a random six-digit, five-minute code, Redis attempt and request limits, and a 30-minute customer JWT scoped to a normalized phone. Redis stores only a keyed hash of the code. In Flask development mode a terminal delivery provider prints the phone and code; production has no delivery provider and fails closed. No customer account or booking schema migration was added.
- `GET /api/bookings` requires a verified matching phone; `/api/bookings/all` is removed. Detail, update, and cancel authorize against the booking phone. Admins retain access; assigned therapists may view, but may not edit or cancel, a booking. Public check-in and check-out require an admin JWT. The existing admin and therapist staff routes remain available.
- Group therapists are recognized through per-guest assignments for their booking list, schedule, detail, and transition routes. Booking status transitions now use a conditional update against the expected status.
- Public availability no longer includes `therapistBookingDetails`; a protected admin slot route supplies it to the admin Gantt. Anonymous eligibility responses omit customer ID, member rank, visit count, and restriction reason.
- Booking and verification responses are marked `Cache-Control: no-store`.
- The frontend requests and verifies a code before phone lookup, shows a Flask terminal hint in development, stores the customer token for the current browser tab, and sends it with customer requests. The admin Gantt uses protected booking and slot data. The chatbot requests and verifies a code for lookup, points local users to the Flask terminal, passes the token per call, and redacts the code from saved chat history. Chatbot modify/cancel tools require a verified token, though their conversational intents are not wired into the existing handler.

## Verification

- Flask API suite: **58 passed**. Request-level tests cover terminal delivery, production non-disclosure, hash-only Redis storage, expiry configuration, replay, attempt and request limits, failed delivery, customer ownership, staff transitions, group therapist membership, and public metadata exposure. The prior booking update tests now authenticate as admin.
- Frontend TypeScript type check and two focused API client tests passed.
- **69** focused chatbot tool and customer journey tests, plus **38** gateway client and error tests, passed using a temporary asyncio test runner because the installed `pytest-asyncio` 0.21.1 is incompatible with pytest 9.2.0 in this environment. No runtime chatbot package was changed for this workaround.

## Boundaries

- Terminal delivery does not prove phone ownership and is restricted to development. Production customer lookup remains unavailable until a real out-of-band delivery provider is added. Live Redis expiry behavior and a complete browser run were not verified in this workspace.
- Legacy bookings with invalid or undeliverable phone numbers require staff assistance. Public booking creation still accepts a supplied phone and remains outside this access-control change.

## Development delivery

The local `.env` has only Twilio sample credentials, so paid SMS was deliberately removed from the Task 4 development workflow. `python run.py` uses the terminal provider; Docker Compose uses production mode and cannot print codes. A new provider can replace terminal delivery later without changing code hashing, rate limits, verification, or booking authorization.
