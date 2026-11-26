# Project status

Updated: 2026-11-26

This file tracks the implementation checklist for the AI massage booking specification. Existing project features outside these tasks are not marked complete by this checklist.

| Task | Status | Evidence |
| --- | --- | --- |
| 01 — Define and enforce booking creation rules | **Completed** | Code commit `5d9a027` on `origin/main`; Flask API suite: 27 passed. |
| 02 — Make therapist assignment and slot capacity consistent under concurrent requests | **Completed** | [Task 02 record](progress/task-02.md); Flask API suite: 33 passed, including a file-backed SQLite race test. |

## Task 2 implementation and scope

1. The Task 1 booking contract remains: multiple main courses, add-ons, optional `selectedCourses` when unambiguous, the `courseId` fallback, and the existing success envelope.
2. Availability remains optimistic. Slots and Gantt views derive capacity and therapist IDs from the same eligible set. Creation rechecks under a transaction; there is no reservation hold.
3. Capacity counts distinct active therapists with covering shifts and excludes overlapping `Booked` or `CheckedIn` assignments from both `BookingTherapist` and the legacy `Booking.therapist_id` pointer.
4. SQLite creation uses `BEGIN IMMEDIATE` before availability reads. A separate-connection race test verifies that only one request can take the final therapist. Other database dialects use a Shop row lock, but that path has not been tested against a live non-SQLite database.
5. Group and automatic assignments select distinct available therapists by daily booked minutes, then therapist ID. Booking modification still has no equivalent capacity recheck and remains outside this task.

Other checklist items, including booking modification, public access control, shift and NG List management, frontend flow, and chatbot alignment, remain outside Task 2 until separately implemented.
