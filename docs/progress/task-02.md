# Task 02 — Therapist assignment and capacity consistency

**Status:** Completed on 2026-11-26

## Implementation

- `BookingService.create` now acquires a SQLite `BEGIN IMMEDIATE` transaction before database-dependent validation and availability reads. For non-SQLite databases, it locks the Shop row with `FOR UPDATE`. The availability decision, assignment rows, and booking insert remain in one transaction.
- Specific preferences take the requested eligible therapist. Gender and automatic single-guest requests, and groups, rank eligible therapists by booked minutes for the day, then ID. Group selection is distinct and creates one `BookingTherapist` row per guest.
- `TherapistService` computes availability from distinct active therapists with a covering shift, minus therapists occupied by overlapping `Booked` or `CheckedIn` bookings. It unions `BookingTherapist` assignments and `Booking.therapist_id` so legacy bookings count without double-counting.
- `SlotService` uses that same set for `availableCapacity` and `availableTherapistIds`. The Gantt booking detail map also includes legacy pointers and per-guest assignments without duplicate therapist entries.
- A SQLite lock timeout returns HTTP 409 `BOOKING_CONFLICT`; a competing request that waits and then finds no therapist receives the existing slot or group unavailable error.

## Verification

Ran `venv/bin/python -m pytest -q -p no:cacheprovider tests` from `spa-booking-api`: **33 passed, 14 warnings**. Six new API tests cover group capacity and cancellation, duplicate shifts and legacy assignments, workload ranking, specific/gender preferences, booking statuses and overlap boundaries, and a file-backed SQLite race with two competing requests. The warnings are the environment LibreSSL warning and existing SQLAlchemy `Query.get()` warnings in `slot_service.py` and `booking_service.py`.

## Boundaries

- The atomic assignment guarantee applies to booking creation through `BookingService.create` on the tested SQLite path. The non-SQLite Shop row-lock path still needs live database concurrency verification.
- `PATCH /api/bookings/{id}` can change the legacy therapist pointer without rechecking availability. Booking modification is a separate task.
- SQLite serializes all writers. The POS call currently runs inside the write transaction, so a future slow external POS call would increase lock contention.
- No database migration, frontend, or chatbot changes were required. Task 1's booking request and success response shapes remain intact.
