# Task 09 — Customer booking edits

**Status:** Completed on 2026-11-27.

## Implementation

- `/my-bookings` restores the current tab's verified phone lookup, links `Booked` bookings directly to an edit form, and refreshes the list after cancellation or a late status rejection. `/bookings/[id]` keeps customer detail under the Task 4 token and provides edit and cancel actions only for `Booked` bookings.
- The edit form starts from the saved booking. It changes date/time, valid current course options and the resulting duration, or a one-guest therapist preference. Shop, guest count, phone, and saved notes are shown read-only. An unknown historical course option is never guessed. A date/time-only edit sends only changed fields, preserving saved services and preferences.
- Customer PATCH calls explicitly use the phone-scoped token even when a staff token is also present. The existing backend PATCH and cancel routes enforce ownership, status, course rules, shop hours, shifts, and availability. Public slot choices are guidance because they count the edited booking as occupied; PATCH excludes it and remains the final decision.
- Edit and cancel errors explain expired access, unavailable capacity, closed-shop requests, invalid course choices, busy writes, and status changes. Successful writes refetch booking detail or list status.
- Corrected the customer list and detail response examples in the API specification to match the existing serializer. No new endpoint, schema, delivery provider, or backend modification logic was added.

## Verification

- Flask API suite: **84 passed**. The new request-level customer journey verifies code delivery and exchange, detail access, rejection of another phone, occupied-therapist rollback, a partial time edit, a course/duration edit preserving notes, cancellation, and rejected writes after cancellation.
- Frontend Jest suite: **53 passed**. New tests cover customer PATCH token selection, form prefill and partial payload, course selection payload, legacy option ambiguity, unavailable-time feedback, late status rejection, direct list-to-edit navigation, list cancellation refresh, customer detail mode, and detail cancellation refresh.
- TypeScript type check, targeted ESLint on the new editor and customer pages, and the Next.js production build passed. `git diff --check` passed.

## Boundaries

- Production customer access still requires the out-of-band code delivery provider deferred in Task 4. The development terminal provider is only for local testing.
- Legacy bookings may lack saved duration/price options. The edit form requires an explicit current catalog choice before changing their services. Backend validation can also reject a date/time-only edit if a retained course is no longer active or bookable.
- The Shop model still lacks a timezone. The customer UI uses the viewer's local clock for past-time display, while the backend compares booking dates with UTC, matching Task 8's existing boundary.
