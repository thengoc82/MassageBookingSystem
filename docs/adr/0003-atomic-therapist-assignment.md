# Atomic therapist assignment on SQLite

**Status:** Accepted on 2026-11-26

## Context

ADR 0002 established optimistic availability, but its `FOR UPDATE SKIP LOCKED` assumption does not hold for the project's default SQLite database. Single-guest creation queried therapists with that clause; group creation selected from an unlocked list. The slot endpoint also counted booking and shift rows instead of distinct therapists.

## Decision

- `POST /api/bookings` acquires a SQLite `BEGIN IMMEDIATE` write transaction before reading the shop, courses, eligibility, or therapist availability. It rechecks availability, chooses therapists, writes the booking and per-guest assignments, and commits in that transaction. A competing SQLite writer waits, then observes the committed assignment before choosing.
- When configured with a database other than SQLite, creation locks the Shop row with `FOR UPDATE` before the same checks. This path is not covered by the SQLite concurrency test and requires database-specific verification before claiming the same deployment guarantee.
- A therapist is eligible only when active, assigned to the shop, covered by a shift for the entire booking, and free of overlapping `Booked` or `CheckedIn` bookings. Capacity is the number of distinct eligible therapists. Occupancy uses the union of `BookingTherapist` rows and the legacy `Booking.therapist_id` pointer, without counting a therapist twice.
- Specific requests keep their exact therapist. Gender, no-preference, and group requests choose eligible therapists by the fewest booked minutes on that date, breaking ties by therapist ID. Group bookings assign distinct therapists, one per guest.
- A SQLite lock timeout returns HTTP 409 `BOOKING_CONFLICT`. A completed competing booking that fills the slot returns the existing `SLOT_UNAVAILABLE` or `INSUFFICIENT_THERAPISTS` error after the waiting request rechecks capacity.

## Consequences and limits

- Slot responses remain snapshots; only creation makes the final assignment decision.
- SQLite serializes writers to the database, including bookings at different shops. The current POS call runs inside the transaction, so a future slow external POS implementation would extend lock duration.
- The guarantee covers concurrent creation through `BookingService.create`. The existing booking modification path can alter `Booking.therapist_id` without rechecking capacity; modification remains a separate task.
- A file-backed SQLite test uses separate connections and competing HTTP requests to verify that only one request can take the final therapist. The in-memory test database alone cannot establish that concurrency property.

## Supersedes

The locking mechanism assumed in ADR 0002. Its decision to use optimistic availability and no reservation holds remains in effect.
