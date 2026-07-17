# AI Massage Booking — Application Overview

Full-stack massage booking platform: a Flask REST API backed by SQLite, and a Next.js
(TypeScript) frontend. Customers book massage sessions by phone-number identity; staff/therapist
availability is computed from shift schedules plus existing bookings.

> This document reflects the **current** code (supersedes the stale `PROJECT_SUMMARY.md`).
> Domain terms follow `docs/CONTEXT.md`.

---

## 1. Architecture

```
Next.js 16 (React 19, TS)  ──HTTP/REST──▶  Flask API  ──▶  SQLAlchemy  ──▶  SQLite
app/ pages + components/                     blueprints/                    (+optional Redis)
                                        services/ (business logic)
```

- **Frontend** is a client-rendered SPA using the App Router. No SSR data fetching — pages call the
  API directly from the browser via a thin axios client (`lib/api.ts`).
- **Backend** is a Flask app split into blueprints (route groups) over a service layer. Availability
  is computed on demand (no stored "slots" entity — see `docs/CONTEXT.md` "Terms NOT in Use").

### Tech stack (actual)
| Layer | Tech |
|-------|------|
| Frontend | Next.js 16.2, React 19, TypeScript 5, Tailwind CSS 4 |
| API client | axios, socket.io-client (installed, live updates not yet wired) |
| Backend | Flask 3, Flask-JWT-Extended, Flask-SocketIO (scaffolded) |
| ORM / DB | SQLAlchemy + Alembic migrations, SQLite (Redis optional) |
| AI / Voice | Twilio + OpenAI + Deepgram + ElevenLabs — scaffolded in `voice_booking/` blueprint, not active |
| Infra | Docker + docker-compose, deployable to Vercel (FE) / Railway / Fly.io (BE) |

---

## 2. Backend (`spa-booking-api`)

### Models (`app/models/`)
`User`, `Customer`, `CustomerRestriction` (NG List), `Shop`, `Course`, `Therapist`,
`TherapistShift`, `Booking`. (`time_slot.py.deprecated` is dead — availability is computed, not stored.)

### Blueprints (`app/blueprints/`) — route groups
| Blueprint | Base | Purpose |
|-----------|------|---------|
| `public` | `/api` | Shops, courses, available-slots, available-therapists, eligibility checks, create/list bookings, cancel |
| `bookings` | `/api/bookings` | Booking create/read/cancel, check-in, check-out |
| `admin` | `/api/admin` | JWT-gated: manage shops, courses, therapists, list bookings |
| `therapist` | `/api/therapists` | Therapist schedule view |
| `auth` | `/api/auth` | Admin/therapist login (JWT) |
| `voice_booking` | — | Twilio/WebSocket scaffolding for phone booking (not active) |

### Services (`app/services/`) — business logic
- **`SlotService`** — `get_available_slots(...)`: walks shop open→close in 15-min steps, computes
  capacity = active therapists on shift − overlapping bookings. With `show_therapists=True` also
  returns the therapist list and per-slot `availableTherapistIds`.
- **`TherapistService`** — shift coverage, per-therapist `is_available`, least-loaded auto-assign.
- **`BookingService`** — creates bookings, assigns therapist (specific / gender / auto for groups),
  applies NG-List and optimistic-availability checks under a row lock.
- **`CustomerService`** — phone-based lookup / auto-create, eligibility checks.

### Key API endpoints
- `GET /api/shops`, `GET /api/shops/{id}/courses`
- `GET /api/shops/{id}/available-slots` (`?show_therapists=true` → includes therapist matrix)
- `GET /api/shops/{id}/available-therapists`
- `POST /api/booking-eligibility-checks`, `POST /api/bookings`, `GET /api/bookings`,
  `PATCH /api/bookings/{id}/cancel`
- `POST /api/auth/login`, `GET /api/therapists/{id}/schedule`
- Admin: `POST /api/admin/shops|courses|therapists`, `GET /api/admin/bookings`,
  `PATCH /api/bookings/{id}/checkin|checkout`

### Booking flow (optimistic availability)
1. Browse shops → pick date / guests / duration / course / add-ons.
2. API returns available slots (capacity-based).
3. Customer picks a time (and optionally a specific therapist).
4. Confirm → `POST /api/bookings` immediately (no reservation hold).
5. Real check happens at creation; if the slot vanished, UI re-queries and offers nearest slots.

---

## 3. Frontend (`spa-booking-frontend`)

### Pages (`app/`)
| Route | File | Purpose |
|-------|------|---------|
| `/` | `page.tsx` | Landing / shop entry |
| `/shops` | `shops/page.tsx` | Shop listings |
| `/dashboard` | `dashboard/page.tsx` | **Therapist availability Gantt** — date + shop selectors, grid of therapists (rows) × time slots (cols); green = available, white = not. Click a cell to book that therapist. |
| `/reservation` | `reservation/page.tsx` | Booking form. Reads `?therapistId=` to **lock a specific therapist**; otherwise free preference. |
| `/booking` | `booking/page.tsx` | Multi-step confirmation wizard (date/time, customer info, services, preferences, review). Shows alternative slots if a slot is taken. |
| `/my-bookings` | `my-bookings/page.tsx` | Booking lookup/management by phone |

### Shared
- `lib/api.ts` — axios wrapper (`shops`, `bookings`, `auth` groups).
- `types/index.ts` — `Shop`, `Course`, `TimeSlot`, `Therapist`, `TherapistInfo`, `Booking`, etc.
- `components/TherapistGantt.tsx` — reusable availability grid used by `/dashboard`.

### Dashboard → Reservation → Booking flow
1. `/dashboard` Gantt cell click → `/reservation?shopId=&date=&time=&therapistId=<id>`.
2. `/reservation` injects `therapistPreferenceType:'specific'`, `therapistPreferenceValue:<id>` into
   the booking payload (backend locks that exact therapist).
3. On success, booking is recorded to `localStorage.recentBookings` so the dashboard grid reflects it
   (that therapist's cell at that time turns white) while the time column stays visible.

---

## 4. Domain at a glance
- **Customer** = phone-identified person; auto-created on first booking; can be NG-List blocked.
- **Therapist** = shop staff on weekly **Shifts**; requestable by name for 1-person bookings only.
- **Booking** = confirmed reservation, status `Booked → CheckedIn → CheckedOut` (or `Cancelled`).
- **Course** = service (`main` or `addon`), duration + price (VND).
- Capacity = active therapists on shift − overlapping bookings (computed live).

See `docs/CONTEXT.md` for the full glossary, lifecycle, and business rules.

---

## 5. Run it
```bash
# Backend
cd spa-booking-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask db upgrade            # Alembic migrations
python run.py               # http://localhost:5000

# Frontend
cd spa-booking-frontend
npm install
npm run dev                 # http://localhost:3000  (set NEXT_PUBLIC_API_URL=http://localhost:5000/api)
```
Tests: `cd spa-booking-api && pytest` · E2E: `cd spa-booking-frontend && npx playwright test`

---

## 6. Status & open areas
- ✅ Core booking API + optimistic availability + therapist locking.
- ✅ Dashboard Gantt for therapist-level availability.
- ⚠️ `duration` on the dashboard Gantt is hardcoded to 60 min (no duration selector yet).
- ⚠️ Multi-person (`number_of_people > 1`) not handled by the Gantt (single-therapist booking only).
- 🔲 Voice booking (`voice_booking/`) scaffolded, not active.
- 🔲 Admin UI, payments, notifications, auth-gated frontend pages — API-ready, no UI yet.
- 🔲 Socket.IO live updates present in deps but not wired to the UI.
