# Task 10 — Chatbot booking contract

**Status:** Completed on 2026-11-27.

## Implementation

- The existing deterministic chat flow, tools, gateway client, Redis session state, and pending-action confirmation remain in use. The chatbot discovers open shops, bookable main courses and add-ons, duration/price options, and slots through Flask; it does not access the booking database.
- A one-guest booking offers only therapist genders and named therapists returned as available by Flask for the chosen slot. The selected preference is checked against fresh Flask availability and sent as `therapistPreferenceType` and `therapistPreferenceValue`. Groups retain automatic assignment without a preference. The final prompt includes the chosen courses, add-ons, duration, group size, time, phone, price when known, and therapist choice.
- A duration correction cannot silently discard a multi-course selection or leave an old pending write confirmable. Material changes clear and rebuild the pending action. Flask remains authoritative for course validation, eligibility, shop hours, availability, and assignment.
- The create tool retains Flask's booking ID, code, status, and therapist assignments for the customer response. Known validation, blocked-customer, shop-closed, and slot errors never claim success. A booking lock conflict now reaches the slot recovery path. A failed refresh preserves the draft. Timeout or an incomplete success response leaves the outcome uncertain; a similar booking found by lookup is not represented as proof that the timed-out write succeeded.
- Chat modification of date or exact start time and cancellation now use the existing phone-code challenge and token, verified booking lookup, pending-action confirmation, and protected Flask PATCH routes. Other edit choices are directed to the verified web edit form. The chatbot does not use a phone number, booking code, or frontend user ID alone as authorization.
- Updated the chatbot request/response schemas for these exposed fields. The frontend confirmation button uses a generic label for creation and existing-booking writes. No Flask API, database schema, migration, or new infrastructure was added.

## Verification

- The cross-service tests drive chatbot messages through the real Flask routes with an in-process HTTP transport. They cover named and gender therapist selection, group main courses plus an add-on, blocked-customer rejection, verified edit and cancel, and rejection of another phone's booking. The Flask suite passed **90 tests**.
- Focused chatbot tests cover the booking confirmation gate, pending-action cancellation, API validation rejection, busy-write recovery including a failed refresh, timeout uncertainty, and preserving the draft. The chatbot suite passed **286 tests**. Frontend Jest passed **53 tests**; the TypeScript check and `git diff --check` passed.

## Boundaries

- The Task 4 development terminal code provider is still local-only; deployed customer lookup and changes require an out-of-band delivery provider. Public booking creation remains account-free.
- Chat modifications expose date and exact start-time changes. Course, duration, and therapist edits remain available in the verified web editor. A public availability response is provisional and can include the booking being edited; Flask PATCH remains the final edit decision.
- The Shop model still has no timezone. Relative chat dates use the project local zone, while Flask creation compares against UTC, matching the existing project boundary.
