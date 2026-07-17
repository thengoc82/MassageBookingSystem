# File Purpose Reference

Per-file description of every source file in the backend (`spa-booking-api`) and frontend
(`spa-booking-frontend`). Generated to match the current code.

---

## Backend — `spa-booking-api/`

### App factory & config
| File | Purpose |
|------|---------|
| `run.py` | Entry point. Calls `create_app()` and starts the Flask/SocketIO server. |
| `app/__init__.py` | `create_app()` — builds the Flask app, inits extensions (db, migrate, jwt, socketio, cors, redis), imports models, registers all blueprints under `/api/...`, and wires error handlers. |
| `app/config.py` | Config classes (dev/prod). Reads env vars: secrets, Redis, Celery broker, Twilio, OpenAI keys, JWT expiry. |
| `app/extensions.py` | Declares shared extension instances (`db`, `migrate`, `jwt`, `socketio`, `cors`, `redis_client`) and `init_redis()`. |
| `app/celery_app.py` | Builds the Celery instance (broker/backend from env). Currently unused by running app. |
| `app/tasks.py` | Celery task stub — creates an app context. No tasks defined yet. |

### Blueprints (routes)
| File | Purpose |
|------|---------|
| `app/blueprints/auth/__init__.py` | `POST /api/auth/login` — verifies user, returns JWT. Admin/therapist auth. |
| `app/blueprints/public/__init__.py` | Registers the public blueprint (url prefix `/api`). |
| `app/blueprints/public/shops.py` | `GET /api/shops`, `GET /api/shops/{id}` — list/open shop details. |
| `app/blueprints/public/courses.py` | `GET /api/shops/{id}/courses` — list courses (filter by type). |
| `app/blueprints/public/slots.py` | `GET /api/shops/{id}/available-slots` — availability. Supports `show_therapists=true` → returns therapist matrix. |
| `app/blueprints/public/therapists.py` | `GET /api/shops/{id}/available-therapists` — therapists free at a given datetime. |
| `app/blueprints/public/eligibility.py` | `POST /api/booking-eligibility-checks` — NG-List / membership lookup by phone. |
| `app/blueprints/bookings/__init__.py` | Registers bookings blueprint (`/api/bookings`). |
| `app/blueprints/bookings/routes.py` | Booking CRUD + status: create, list, get, update, cancel, checkin, checkout. |
| `app/blueprints/admin/__init__.py` | Registers admin blueprint (`/api/admin`, JWT-gated). |
| `app/blueprints/admin/shops.py` | Admin shop management (list/create/get/patch). |
| `app/blueprints/admin/courses.py` | Admin course management. |
| `app/blueprints/admin/therapists.py` | Admin therapist + shift management. |
| `app/blueprints/therapist/__init__.py` | Registers therapist blueprint (`/api/therapists`, JWT). |
| `app/blueprints/therapist/schedule.py` | `GET /api/therapists/me/schedule` — logged-in therapist's bookings for a date range. |
| `app/blueprints/voice_booking/__init__.py` | Registers voice blueprint (`/api/voice`). |
| `app/blueprints/voice_booking/routes.py` | Twilio webhook stubs (`/incoming-call`, `/gather`) — not yet implemented. |
| `app/blueprints/setup.py` | `POST /api/setup-demo-data` — one-shot demo seed (shop/courses/therapists). |

### Services (business logic)
| File | Purpose |
|------|---------|
| `app/services/booking_service.py` | Creates/updates bookings, assigns therapist (specific/gender/auto), NG-List + optimistic availability checks, status transitions. |
| `app/services/slot_service.py` | `get_available_slots()` — walks shop hours in 15-min steps, computes capacity and (optionally) per-therapist availability. |
| `app/services/therapist_service.py` | Shift coverage, per-therapist `is_available`, least-loaded auto-assign, schedule lookup. |
| `app/services/customer_service.py` | Phone lookup / auto-create, eligibility & NG-List checks. |

### Models
| File | Purpose |
|------|---------|
| `app/models/__init__.py` | Imports & exposes all models for `create_app()` and migrations. |
| `app/models/user.py` | `User` — admin/therapist login accounts (JWT identity, password hash). |
| `app/models/customer.py` | `Customer` — phone-identified booker; member rank, visit count, block flag. |
| `app/models/customer_restriction.py` | `CustomerRestriction` — NG-List block (reason, active flag). |
| `app/models/shop.py` | `Shop` — branch; hours, status, contact. |
| `app/models/course.py` | `Course` — service (`main`/`addon`), duration, price. |
| `app/models/therapist.py` | `Therapist` — staff; shop, name, gender, status. |
| `app/models/therapist_shift.py` | `TherapistShift` — weekly recurring work blocks. |
| `app/models/booking.py` | `Booking`, `BookingService`, `BookingAddon` — reservation + per-person services/add-ons. |

### Utils
| File | Purpose |
|------|---------|
| `app/utils/__init__.py` | `success_response()` / `paginated_response()` — standard JSON envelopes. |
| `app/utils/errors.py` | `APIError` hierarchy (`ValidationError`, `Unauthorized`, `Forbidden`, `ResourceNotFound`, `BusinessRuleViolation`, etc.) + `register_error_handlers()`. |
| `app/utils/decorators.py` | `role_required()` (JWT role gate) and `validate_json()` (required-field check). |
| `app/utils/validators.py` | Regex validators for phone / time / date formats. |
| `app/utils/pagination.py` | `paginate()` helper for list endpoints. |

### Migrations & seed
| File | Purpose |
|------|---------|
| `migrations/env.py` | Alembic env — binds Flask app / metadata to migrations. |
| `migrations/versions/23ef72500a61_initial_migration.py` | Initial schema (all tables, including unused `time_slots` + `reservations`). |
| `migrations/versions/09a2b6ba1cef_*.py` | Drops the unused `time_slots` table. |
| `seed_data.py` | Standalone seed script (shops/courses/therapists). |
| `seed_dev.py` | Dev seed script. |

### Tests & config
| File | Purpose |
|------|---------|
| `tests/conftest.py` | Pytest fixtures (app, sample shop/courses/therapists). |
| `tests/test_booking_flow.py` | Booking + availability endpoint tests (incl. `show_therapists`). |
| `requirements.txt` | Python dependencies. |
| `.env.example` | Sample environment variables. |
| `Dockerfile` / `docker-compose.yml` | Container build & orchestration. |

---

## Frontend — `spa-booking-frontend/`

### App router pages (`app/`)
| File | Purpose |
|------|---------|
| `app/layout.tsx` | Root layout — wraps all pages, global styles, `<html>/<body>`. |
| `app/globals.css` | Tailwind + global CSS. |
| `app/page.tsx` | `/` — landing / shop entry. |
| `app/shops/page.tsx` | `/shops` — shop listings. |
| `app/dashboard/page.tsx` | `/dashboard` — **therapist availability Gantt** (date + shop selectors, therapist×time grid); cell click routes to `/reservation` with `therapistId`. |
| `app/reservation/page.tsx` | `/reservation` — booking form. Reads `?therapistId=` to lock a specific therapist; time is fixed/read-only to the chosen slot. |
| `app/booking/page.tsx` | `/booking` — multi-step confirmation wizard; shows alternative slots if a slot is taken. |
| `app/my-bookings/page.tsx` | `/my-bookings` — booking lookup/management by phone. |

### Shared
| File | Purpose |
|------|---------|
| `components/TherapistGantt.tsx` | Reusable availability grid (therapist rows × time-slot columns, green = free). Used by `/dashboard`. |
| `lib/api.ts` | Axios API client (`shops`, `bookings`, `auth` groups). |
| `types/index.ts` | TypeScript interfaces: `Shop`, `Course`, `TimeSlot`, `Therapist`, `TherapistInfo`, `Booking`, etc. |

### Config & tests
| File | Purpose |
|------|---------|
| `package.json` / `package-lock.json` | Dependencies & scripts (`dev`, `build`, `start`, `lint`). |
| `tsconfig.json` | TypeScript config. |
| `next.config.ts` | Next.js config. |
| `next-env.d.ts` | Next.js TS ambient types. |
| `e2e/booking-flow.spec.ts` | Playwright end-to-end booking test. |
| `e2e/debug.spec.ts` | Playwright debug test. |

---

## Notes
- `app/celery_app.py` and `app/tasks.py` exist but are **not wired** into the running app (no Celery worker).
- `voice_booking/routes.py` is a **scaffold** — endpoints return "pending" stubs.
- `time_slots` / `reservations` tables are created by the initial migration but unused (see ADR 0002).
