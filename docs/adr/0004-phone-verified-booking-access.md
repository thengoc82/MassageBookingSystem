# ADR 0004 — Phone-scoped booking access

## Context

Customers do not have accounts. A booking stores a phone number, but anyone can enter or learn that number. The original public list, detail, update, cancel, check-in, and check-out routes therefore exposed other customers' information and staff operations. Booking codes have only four random digits and are not proof of ownership.

## Decision

- A customer requests a random six-digit code for a phone number and exchanges it for a 30-minute JWT with `role=customer`, `type=customer_access`, and a normalized phone. The code expires after five minutes, is single use, and permits five attempts. Redis limits challenges to three per phone per 15 minutes and 20 per source IP per hour. Only a keyed hash of the code is stored in Redis.
- Code delivery is a replaceable provider. Development prints the phone and code in the Flask terminal and never includes the code in the HTTP response. The terminal provider is blocked outside the Flask development configuration. Production has no delivery provider yet and returns 503; a real out-of-band provider can be added later without changing the verification or booking authorization rules.
- Customer list access requires `phone` plus the matching customer token. Detail, modification, and cancellation check the booking's phone against that token before exposing or changing data. A wrong owner receives the same 404 as a missing booking. Existing phone lookup remains available after phone verification; no customer account is created.
- Admin JWTs can view, modify, and cancel any booking. Therapist JWTs can view and check in/out only bookings assigned to them, including per-guest group assignments. Existing `role_required` guards protect staff routes. Public check-in/out URLs now require an admin JWT. Status changes use conditional writes to enforce lifecycle state at commit time.
- Public availability keeps therapist and capacity information but omits booking metadata. The admin Gantt fetches that metadata from a protected admin route. Public eligibility returns the decision without member rank, visit count, customer ID, or restriction reason.
- Booking and verification responses use `Cache-Control: no-store` so browser and shared caches do not retain customer tokens or booking details.

## Consequences

- Redis is required for local testing. Terminal delivery is free but provides no proof that the requester controls the phone, so it must never be used for deployed customer access. Production needs a real delivery provider and strong `SECRET_KEY` / `JWT_SECRET_KEY` values. The code is not returned by the API and is not stored in chatbot history.
- Customer access tokens are scoped to a phone, not to a booking ID, so a verified customer can see all bookings recorded under that phone. A booking entered with another person's phone remains inaccessible to the person who submitted it unless they control that phone.
- The API keeps booking request and successful response shapes. Authentication errors and the reduced public eligibility payload are deliberate contract changes.
