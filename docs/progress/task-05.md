# Task 05 — Weekly therapist shift management

**Status:** Completed on 2026-11-26

## Implementation

- Added admin JWT protected list, detail, create, update, and delete routes for the existing `TherapistShift` model. List supports shop, therapist, and weekday filters. Shift responses use the existing success envelope.
- Validated weekday, 24-hour times, date, required fields, and nonoverlapping intervals. Because shifts have no end date, different `effectiveFrom` values do not permit overlapping rules for the same therapist and weekday. Adjacent shifts are valid.
- Shift writes use the same shop lock as booking creation and modification. Edits and deletion are rejected with `SHIFT_BOOKING_CONFLICT` if future `Booked` or `CheckedIn` bookings assigned through per-guest rows or the legacy pointer would lose coverage.
- Extended `/admin/schedules` with weekly shift list and create, edit, and delete controls. The existing booking schedule view and endpoint remain unchanged. Frontend calls use the shared authenticated API utility.
- Slot availability reads shifts dynamically, so successful changes affect the next availability request. No model change or migration was needed.

## Verification

- Flask API suite: **63 passed**. New request-level tests cover role authorization, CRUD and filtering, invalid input and overlaps, effective-date and slot-capacity changes, booking conflict rollback, per-guest assignments, and the booking schedule response.
- Frontend Jest suite: **25 passed**. New tests cover authenticated shift API calls, management controls, conflict display, successful deletion, and continued booking display.
- Frontend TypeScript type check passed.

## Boundary

`effectiveFrom` is only a lower bound; the model has no end date or version history. Replacing an existing shift on a future date while retaining its earlier schedule would require a separate schema decision. The non-SQLite shop-lock path has not been verified against a live database, matching the booking write path's existing boundary.
