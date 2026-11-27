# Task 08 — Slot choices and recovery

**Status:** Completed on 2026-11-27.

## Implementation

- The existing slot service validates date, start time, duration, guest count, and gender. Its 15-minute grid starts no earlier than shop opening, and a closed shop returns no slots. A one-guest gender filter counts only eligible therapists of that gender in capacity and therapist IDs. Public slot responses are marked `Cache-Control: no-store`.
- The customer dashboard offers any therapist, Female, Male, or a named therapist for one guest. Groups retain capacity-based selection without a therapist preference. The grid disables elapsed local times and past dates, explains empty and failed availability requests, and offers retry. Dashboard requests and reservation URLs use `localDateStr` rather than UTC `toISOString()`.
- BookingForm rechecks the selected time before POST and sends the chosen preference to the existing booking API. If precheck or POST finds the time unavailable, it offers up to eight nearby matching choices on the same date. A booking lock conflict prompts refresh or retry. Selecting another time retains the shop, date, courses and prices, guest count, phone, notes, and therapist preference. Each retry rechecks availability; booking creation remains authoritative.
- The existing `GET /api/shops/{id}/available-slots` and `POST /api/bookings` endpoints and booking transaction remain in use. No reservation hold, schema change, or migration was added.

## Verification

- Flask API suite: **83 passed**. New request-level tests cover gender-filtered capacity matching creation, occupied therapists, closed shops, pre-opening and grid-aligned starts, malformed slot queries, and the public no-store header. Existing shift, group-capacity, and SQLite concurrency tests still pass.
- Frontend Jest suite: **44 passed**; TypeScript check passed. New tests cover group and named-therapist cells, gender query and payload, empty/error/retry states, local date routing, in-form recovery after precheck and repeated POST losses, and a booking lock conflict. Focused dashboard, Gantt, and form tests also passed with `TZ=Asia/Ho_Chi_Minh`.
- Chromium browser journey: **2 passed**, including a mocked-Flask POST capacity loss followed by another time choice and a successful request carrying the original courses, guests, phone, and notes.
- `git diff --check` passed. Targeted ESLint passed for BookingForm, reservation, and browser test files. The dashboard and Gantt files still have pre-existing lint errors for synchronous state updates in effects and `any` types; the dashboard also has an unused variable warning.

## Boundary

Slots remain snapshots; a suggested slot can disappear before confirmation. The backend still compares booking dates with UTC because the Shop model has no timezone. The customer UI uses the viewer's local date and clock for past-time display, so a shop in another timezone needs an explicit timezone policy before that behavior can be made shop-local. The browser tests use mocked Flask responses; the Flask suite separately verifies real service behavior. A live non-SQLite concurrency test remains outside this task.
