# Project status

Updated: 2026-11-26

This file tracks the implementation checklist for the AI massage booking specification. Existing project features outside these tasks are not marked complete by this checklist.

| Task | Status | Evidence |
| --- | --- | --- |
| 01 — Define and enforce booking creation rules | **Completed** | Code commit `5d9a027` on `origin/main`; Flask API suite: 27 passed. |
| 02 — Make therapist assignment and slot capacity consistent under concurrent requests | **Completed** | [Task 02 record](progress/task-02.md); Flask API suite: 33 passed, including a file-backed SQLite race test. |
| 03 — Repair booking modification | **Completed** | [Task 03 record](progress/task-03.md); Flask API suite: 48 passed, including a file-backed create-versus-modify race test. |
| 04 — Public booking access and staff-only transitions | **Implemented for local development; deployed delivery deferred** | [Task 04 record](progress/task-04.md); Flask API suite: 58 passed. Frontend type check and focused chatbot tests passed. |

## Task 2 implementation and scope

1. The Task 1 booking contract remains: multiple main courses, add-ons, optional `selectedCourses` when unambiguous, the `courseId` fallback, and the existing success envelope.
2. Availability remains optimistic. Slots and Gantt views derive capacity and therapist IDs from the same eligible set. Creation rechecks under a transaction; there is no reservation hold.
3. Capacity counts distinct active therapists with covering shifts and excludes overlapping `Booked` or `CheckedIn` assignments from both `BookingTherapist` and the legacy `Booking.therapist_id` pointer.
4. SQLite creation uses `BEGIN IMMEDIATE` before availability reads. A separate-connection race test verifies that only one request can take the final therapist. Other database dialects use a Shop row lock, but that path has not been tested against a live non-SQLite database.
5. Group and automatic assignments select distinct available therapists by daily booked minutes, then therapist ID. Booking modification still has no equivalent capacity recheck and remains outside this task.

At Task 2 completion, booking modification, public access control, shift and NG List management, frontend flow, and chatbot alignment remained outside its scope. Booking modification was subsequently completed in Task 3.

## Task 3 implementation and scope

1. `PATCH /api/bookings/{id}` validates the proposed date, time, duration, courses, shop hours, and therapist assignment before changing the booking. Only `Booked` bookings may be edited.
2. Modification uses the same shop-level lock and shift/overlap rules as creation. Its availability check excludes the booking being edited from both legacy and per-guest occupancy; existing eligible assignments remain stable, and replacements follow the Task 2 workload ranking.
3. The booking interval, course rows, per-guest therapist rows, and legacy therapist pointer commit together. A rejected edit rolls back without changing persisted booking state. The PATCH success envelope is unchanged.
4. Guest count and shop changes are not supported by this PATCH contract. Public access control remains Task 4; POS modification synchronization has no existing adapter.
