# Task 12 — Full scenario tests and documentation

**Status:** Completed for local development on 2026-11-27 (Asia/Ho_Chi_Minh).
This record distinguishes executed tests from earlier claims and from untested
deployment paths.

## Implementation and defect

- Added opt-in HTTP tests in `spa-booking-api/tests/test_task12_live.py` and
  Chromium tests in `spa-booking-frontend/e2e/task12-live.spec.ts`. They use
  actual running Flask and chatbot processes, Redis, a migrated SQLite file,
  and the running Next.js frontend. The browser forwards its compiled API
  requests to the isolated Flask process because an existing Next dev server
  held Next's build lock. The responses and persisted changes are from Flask,
  not hand-built mocks.
- Removed the anonymous `/api/setup-demo-data` registration and route. It
  could create known admin credentials on an empty database. The local
  command-line `seed_dev.py` remains available for an empty development
  database; its use is documented separately from public API access.
- Added a request-level regression that the setup route is 404 and cannot
  create the known admin login. Added a checked-in pytest coroutine runner
  because this environment's pytest-asyncio version is incompatible with
  the system pytest version. Added the missing Flask runtime packages to its
  requirements manifest so the documented setup can install the services.
  No authorization rule was weakened.
- Reconciled the REST API specification and running instructions with the
  registered admin course, therapist, schedule, booking, shift, and NG List
  routes and the actual customer access rule. Corrected the report's TC-02
  and TC-03 expectations and filled its measured-result column.

## Test environment

- Fresh isolated SQLite database under `/private/tmp`, migrated from base to
  `20261126_customer_restrictions`, then populated with `seed_dev.py` (2 shops,
  5 courses, 5 therapists with weekly shifts). Existing `instance/dev.db` and
  `instance/prod.db` were not used for scenario writes.
- Flask development server on port 5001 with debug mode, terminal code
  delivery, and a dedicated Redis database. FastAPI chatbot on port 8002 with
  a separate Redis database and its Flask gateway set to port 5001.
- The existing Next.js dev server on port 3000 served the UI. Playwright
  forwarded its browser API requests to port 5001. The chatbot used the
  configured PostgreSQL pgvector FAQ index. The cached embedding model ran
  offline. No paid external service was called.
- Local ports 3000, 5000, and 8001 were also checked read-only: frontend,
  Flask shop API, and chatbot health all responded. This confirms the
  documented default service origins were reachable from the host, while
  scenario writes stayed in the isolated services.

## Measured results

| Test | Final result | What it verifies |
| --- | --- | --- |
| Flask request-level suite | **91 passed, 7 skipped** | Existing booking/security rules and disabled setup route. The seven opt-in live tests skip unless `TASK12_BASE_URL` is set. |
| Chatbot suite | **300 passed** | Conversation, confirmation, retrieval, timeout/error recovery; many use test doubles. |
| Frontend Jest | **53 passed** | UI components and API-client behavior, mainly with mocked requests. |
| Frontend TypeScript | **Passed** | `tsc --noEmit`. |
| Existing Playwright booking-flow tests | **2 passed** | Catalog payload and alternative-slot recovery in Chromium with mocked Flask responses. |
| Task 12 live HTTP scenarios | **7 passed** | Real Flask/Redis/chatbot requests and persisted database state, including a SQLite capacity race. |
| Task 12 live Chromium journeys | **2 passed** | Real customer booking/view/edit/cancel, plus admin and assigned-therapist status operations through their pages and Flask. |

The initial local test setup returned 503 for verification because the Flask
CLI was started without debug mode; the development terminal provider is
intentionally disabled in that mode. After enabling debug, the scenario
passed. Early Playwright failures were selector and login-navigation races in
the new test, then passed after correction. An early changed-availability
assertion expected a rejection while spare therapists were still available;
Flask correctly reassigned the booking. The final test occupies every
therapist and verifies a 422 rejection with the original time unchanged.
These were test setup or expectation corrections, not production defects.

## Scenario matrix

| Scenario | Verified result | Boundary |
| --- | --- | --- |
| TC-01, named therapist | **Passed:** real POST returned 201, `Booked`, code, and requested therapist assignment. | Local SQLite and seeded shifts. |
| TC-02, group preference | **Passed:** specific-therapist group request returned 400 without creation; a separate no-preference request returned 201 with two distinct assignments. | The two outcomes require separate requests. |
| TC-03, NG List | **Passed:** admin block caused `CUSTOMER_BLOCKED`; public responses omitted the private reason; admin saw the reason and removal allowed a new booking. | The report's former expectation to reveal the reason publicly was corrected. |
| TC-04, capacity race | **Passed:** concurrent HTTP submissions for one specific therapist produced one 201 and one 422. A real chat write lost its named therapist and did not claim success. | Browser alternative-slot selection passed only with a mocked Flask loss; no concurrent browser race was run. |
| TC-05, cancellation | **Passed:** a verified customer cancelled through Chromium, Flask stored `Cancelled`, and later PATCH was rejected. | Development terminal verification only. |
| TC-06, status transitions | **Passed:** admin checked in through the UI, the assigned therapist checked out through the UI, and Flask stored `CheckedOut`; an unrelated therapist was denied and a repeat checkout failed. | Seeded staff accounts. |
| TC-07, chatbot booking | **Passed:** live `/chat` collected shop, course, date, time, guest count and phone; no write occurred before final confirmation; Flask then stored `Booked`. | The report's example named a course absent from seed data, so a real seeded course was used. |
| TC-08, RAG answer | **Passed:** live `/chat` answered a new cancellation FAQ question from pgvector with a source citation. | No live paid LLM generation call. |

Additional executed cases: missing/invalid/expired JWTs; invalid verification
code; another customer's list, detail, edit and cancel; anonymous and
therapist access to admin routes; assigned versus unassigned therapist access;
public slot and eligibility privacy; invalid booking duration; shift CRUD,
overlap and slot-capacity change; invalid group preference; and a rejected
booking edit after all capacity at the new time became occupied. The edit
left its original start time intact. Expired verification codes and other
gateway failures are covered by request-level or chatbot tests with test
doubles, not by a five-minute live wait or a stopped live Flask process.

## Reproduce the checks

Use a **new** isolated SQLite path for each live run; the live tests create
bookings and staff data and are not designed to be rerun against the same
seeded file. Run migrations and `seed_dev.py` with that `DATABASE_URL`, then
start Flask in development debug mode with a dedicated `REDIS_URL` and send
its terminal output to a temporary log. Start the chatbot with
`CHATBOT_GATEWAY_FLASK_BASE_URL` pointing to that Flask process,
`CHATBOT_REDIS_URL` pointing to a separate Redis database, and the configured
`CHATBOT_PG_DSN`. Start the frontend with the corresponding public URLs or
use the Playwright forwarding in the live spec when an existing Next dev
server holds its build lock.

From `spa-booking-api`:

```sh
PYTHONPATH=.. ../venv/bin/python -m pytest -q --disable-warnings -p no:asyncio -p scripts.pytest_asyncio_compat tests
TASK12_BASE_URL=http://127.0.0.1:5001/api TASK12_CHAT_URL=http://127.0.0.1:8002 TASK12_FLASK_LOG=/private/tmp/task12_flask.log PYTHONPATH=.. ../venv/bin/python -m pytest -q -p no:asyncio -p scripts.pytest_asyncio_compat tests/test_task12_live.py
```

From the repository root and `spa-booking-frontend`, respectively:

```sh
venv/bin/python -m pytest -q --disable-warnings -p no:asyncio -p scripts.pytest_asyncio_compat chatbot/tests
```

```sh
npm test -- --runInBand --silent
./node_modules/.bin/tsc --noEmit
./node_modules/.bin/playwright test e2e/booking-flow.spec.ts --browser=chromium --workers=1
TASK12_LIVE=1 PLAYWRIGHT_BASE_URL=http://localhost:3000 TASK12_API_URL=http://127.0.0.1:5001/api TASK12_FLASK_LOG=/private/tmp/task12_flask.log ./node_modules/.bin/playwright test e2e/task12-live.spec.ts --browser=chromium --workers=1
```

## Not verified

- Production customer-code delivery is unconfigured. Terminal delivery is
  local-only and does not prove phone ownership.
- Flask's non-SQLite shop/customer row-lock paths were not raced on a live
  database. The concurrency result applies to file-backed SQLite.
- The optional external LLM generation path was tested with doubles in Task
  11; Task 12 made no paid LLM call. The live FAQ test used cited retrieval.
- Large-load performance, real customer phone delivery, browser-level
  simultaneous booking, and a live Flask outage during chatbot submission
  were not tested. The chatbot suite covers API error handling with doubles.
- The seed's zero-minute add-ons are intentionally unbookable. The existing
  mocked browser test covers a positive-duration add-on; the live seeded
  browser journey used a main course.
