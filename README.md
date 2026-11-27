# AI Massage Booking System

A three-service booking application: Next.js 16 frontend, Flask booking API,
and FastAPI chatbot. SQLite stores bookings in local development. Redis
supports phone-code verification and chatbot sessions. PostgreSQL with
pgvector stores indexed FAQ evidence.

## Current flows

- Customers browse shops and active courses, choose a date, guest count and
  available time, then submit a booking. Availability is optimistic; Flask
  checks capacity again during the write. There are no reservation holds.
- Customers view, edit, or cancel their own `Booked` bookings after phone-code
  verification. The development code is printed in the Flask terminal.
- Admins manage therapist shifts and NG List entries and can check bookings
  in and out. Assigned therapists can view and check in/out their own bookings.
  Staff actions require role JWTs.
- The chatbot discovers shops, catalog options and slots through Flask, shows
  a final draft before any write, and answers supported FAQ questions with
  citations from the knowledge index.

See [RUNNING.md](RUNNING.md) for local setup, required configuration, migration
and seed commands, and test commands. The implemented API contract is in
[docs/REST_API_Specification.md](docs/REST_API_Specification.md). The final
local scenario results and limitations are in
[docs/progress/task-12.md](docs/progress/task-12.md).

Production phone-code delivery, payments, voice booking, notifications, and
Socket.IO updates in the UI are outside the verified Task 12 flows.
