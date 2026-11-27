# Run the local booking system

The application has a Flask booking API (port 5000), a Next.js frontend
(port 3000), and a FastAPI chatbot (port 8001). Redis is required for phone
verification and chat sessions. PostgreSQL with pgvector is required for FAQ
retrieval. Booking data uses SQLite by default.

## Configuration

Use the existing `spa-booking-api/.env`, `chatbot/.env`, and
`spa-booking-frontend/.env.local` templates without committing secrets.
The essential settings are:

| Component | Setting | Local value or purpose |
| --- | --- | --- |
| Flask | `FLASK_ENV=development` | Enables the development terminal code provider. Run `python run.py`, which sets debug mode. |
| Flask | `DATABASE_URL` | Optional. Default is `sqlite:///dev.db`, stored in `spa-booking-api/instance/dev.db`. |
| Flask | `REDIS_URL` | Default `redis://localhost:6379/0`. Required for customer access codes. |
| Flask | `SECRET_KEY`, `JWT_SECRET_KEY` | Set strong, private values for a deployment. |
| Frontend | `NEXT_PUBLIC_API_URL` | `http://localhost:5000/api`. |
| Frontend | `NEXT_PUBLIC_CHATBOT_URL` | `http://localhost:8001`. |
| Chatbot | `CHATBOT_GATEWAY_FLASK_BASE_URL` | Default `http://localhost:5000/api`. |
| Chatbot | `CHATBOT_REDIS_URL` | Default `redis://localhost:6379/0`. |
| Chatbot | `CHATBOT_PG_DSN` | PostgreSQL connection for indexed FAQ retrieval. |
| Chatbot | `CHATBOT_OPENAI_API_KEY` | Optional. Without it, supported FAQs return cited excerpts. |

Twilio, payment, voice, and other external service credentials are not needed
for the local web and chat booking journeys. The production Flask configuration
has no customer code delivery provider, so verified customer lookup and edits
are unavailable there until a provider is added.

## Start

1. Start Redis and PostgreSQL with the vector extension. Create a repository
   root Python environment with `python3 -m venv venv`, then install both
   service manifests with
   `venv/bin/python -m pip install -r spa-booking-api/requirements.txt -r chatbot/requirements.txt`.
   From `spa-booking-frontend`, install Node dependencies with `npm install`.
2. From `spa-booking-api`, run
   `../venv/bin/python -m flask --app run:app db upgrade`. On an empty
   development database, run `../venv/bin/python seed_dev.py` for local
   shops, courses, therapists, shifts, and staff accounts. Seed data is for
   development only. The public `/api/setup-demo-data` route is disabled.
3. From `spa-booking-api`, run `../venv/bin/python run.py`. Confirm
   `GET http://localhost:5000/api/shops`.
4. From the repository root, run
   `venv/bin/python -m chatbot.scripts.index_knowledge_base` to index
   `docs/knowledge`, then `venv/bin/python -m chatbot.main`. Confirm
   `GET http://localhost:8001/health`.
5. From `spa-booking-frontend`, run `npm run dev`, then open
   `http://localhost:3000/shops`.

The development seed's zero-minute add-ons are excluded from the public
bookable catalog. Create positive-duration add-ons with an admin JWT if that
scenario is needed.

## Customer and staff access

Public booking creation does not require login. To see, edit, or cancel a
booking, request a code on **My Bookings** and read it from the Flask terminal.
The code lasts five minutes and is never returned by the API. A verified token
lasts 30 minutes and only grants access to bookings for that phone. The
development terminal provider is a local test mechanism; it does not prove
control of a phone.

Admin and therapist pages use `POST /api/auth/login` and their role JWTs.
Admins manage shifts and NG List records and may check bookings in and out.
Assigned therapists may view and check in/out their own bookings. Staff
endpoints are not public.

## Tests

From the repository root, run chatbot tests with:

```sh
venv/bin/python -m pytest -q -p no:asyncio -p scripts.pytest_asyncio_compat chatbot/tests
```

From `spa-booking-api`, run Flask tests with:

```sh
PYTHONPATH=.. ../venv/bin/python -m pytest -q -p no:asyncio -p scripts.pytest_asyncio_compat tests
```

From `spa-booking-frontend`, run `npm test -- --runInBand` and
`./node_modules/.bin/playwright test e2e/booking-flow.spec.ts --browser=chromium`.
The existing booking-flow browser tests mock Flask. Opt-in live HTTP and
browser commands, their isolated database setup, and results are recorded in
[Task 12](docs/progress/task-12.md).
