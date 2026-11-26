# Task 03 — Repair booking modification

**Status:** Completed on 2026-11-26

## Implementation

- `BookingService.update` now accepts partial changes to date, start time, duration, services, add-ons, selected course options, and therapist preference. It preserves the existing `therapistId` PATCH field and the `{success, data: {bookingId, status}, message}` response.
- The proposed booking interval is calculated before mutation. The service applies Task 1's date, shop-hours, course ownership/type/status, catalog option, and per-guest selection rules. Guest count, shop, phone number, and status are immutable through this endpoint.
- Modification acquires the same SQLite `BEGIN IMMEDIATE` or non-SQLite Shop row lock used by creation. It checks `Booked` status under that lock and rechecks shifts and overlapping `Booked` / `CheckedIn` assignments. The availability query excludes the edited booking from both its legacy pointer and per-guest rows.
- Existing eligible therapist assignments are kept. An explicit single-guest request requires the selected therapist; gender requests and necessary automatic replacements use Task 2's booked-minutes-then-ID order. Groups retain distinct assignments. The legacy pointer is synchronized with the first per-guest assignment.
- The booking row, course rows, preferences, and therapist rows are committed together. Invalid input, unavailable capacity, or a failed write rolls back. The PATCH route returns structured validation errors for malformed JSON.

## Verification

Ran `venv/bin/python -m pytest -q -p no:cacheprovider tests` from `spa-booking-api`: **48 passed, 14 warnings**. Fifteen new request-level tests cover interval recalculation, date and course edits, explicit/gender/group assignments, occupied capacity, missing shifts, legacy pointers, non-`Booked` statuses, malformed input, and full persisted-state comparisons after rejection. A file-backed SQLite test races creation against modification for the final therapist. `git diff --check` passed.

## Boundaries

- The route remains public pending Task 4's customer ownership and staff access rules.
- POS modification synchronization is not represented by an existing adapter. Task 3 rechecks local booking availability; it does not claim an external POS update.
- The non-SQLite lock path has not been verified against a live database, matching Task 2's boundary. SQLite concurrency is verified for the tested create-versus-modify path.
- `numberOfPeople` and `shopId` changes are outside the supported partial-update contract. Existing PATCH callers using `startTime` or `therapistId` remain supported.
