# Application overview

This document describes the locally verified Task 12 application. The
canonical business rules are in [CONTEXT.md](CONTEXT.md), the registered Flask
routes are in [REST_API_Specification.md](REST_API_Specification.md), and the
measured scenario results are in [progress/task-12.md](progress/task-12.md).

## Services and data

| Service | Responsibility | Local origin |
| --- | --- | --- |
| Next.js 16 / React 19 frontend | Shop catalog, availability schedule, booking forms, customer access, admin and therapist pages, chat widget | `http://localhost:3000` |
| Flask booking API | Catalog, shifts, restrictions, capacity, booking writes and authorization | `http://localhost:5000/api` |
| FastAPI chatbot | Conversation, confirmation gate, Flask tool calls and FAQ retrieval | `http://localhost:8001` |

Flask uses SQLAlchemy and SQLite by default. Its booking writes recheck
availability under a SQLite write transaction; other database dialects use a
shop row lock, which has not had a live concurrency test. Redis is required
for phone-code challenges and chatbot sessions. PostgreSQL with pgvector
stores FAQ chunks and embeddings. The optional LLM key affects wording of
grounded FAQ answers; the local no-key path returns cited excerpts.

The frontend's `lib/api.ts` uses browser `fetch` for Flask requests. The
chat widget sends messages to FastAPI. Socket.IO packages and voice booking
scaffolding exist, but live UI updates and voice booking are outside the
verified customer flows.

## Customer flow

1. Browse open shops and their active, bookable main courses and add-ons.
2. Choose a shop, local date, guest count, catalog-backed duration, therapist
   preference when booking one guest, and an available time.
3. Select courses whose durations fill the reserved interval, enter a phone
   number and optional notes, and submit. Flask rechecks shop hours, courses,
   customer restrictions, shifts and capacity before returning a booking code.
4. If the slot disappears, the web form offers nearby choices while keeping
   the entered information. These choices are provisional until a new POST
   succeeds.
5. To view, edit or cancel an existing `Booked` booking, request a short-lived
   phone code. The development server prints it in its terminal; production
   has no configured delivery provider. A verified token grants access only
   to that phone's bookings. Booking code or phone number alone is insufficient.

The chatbot discovers shops, courses, slots and therapists through Flask and
shows the full draft before any booking write. Its confirmed write uses the
same Flask rules as the website. Verified chat lookup, date/time edits and
cancellation use the same phone-scoped token. Supported FAQ answers cite
indexed knowledge; current prices, hours and availability come from Flask.

## Staff flow

Admins authenticate with a role JWT and manage shops, courses, therapists,
weekly shifts, NG List restrictions and booking status. Assigned therapists
can view their own bookings and check them in or out. Only
`Booked → CheckedIn → CheckedOut` and `Booked → Cancelled` transitions are
supported. Staff role and assignment checks are enforced by Flask, including
when browser state is altered.

## Local operation

See [RUNNING.md](../RUNNING.md) for environment variables, migrations,
command-line seed data, service startup and test commands. The anonymous
demo-setup endpoint has been removed because it could create known admin
credentials on an empty database.
