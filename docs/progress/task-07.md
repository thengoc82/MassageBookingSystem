# Task 07 — Service discovery and booking options

**Status:** Completed on 2026-11-27.

## Implementation

- The public Flask course route returns active main courses and add-ons at open shops with only duration and price pairs accepted by booking creation. It rejects unsupported type filters. Booking validation uses the same Course option helper, including zero-price choices.
- `/shops` displays each shop's bookable main courses and add-ons and links into the selected shop's schedule. The dashboard derives offered durations from valid course combinations rather than a fixed list. Shops without a bookable main course have no booking link or schedule options.
- BookingForm retains the selected duration and price pair, including same-duration price variants. It supports one or more main courses and optional add-ons, shows per-guest and group totals, checks that the selection fills the reserved duration, and sends `services`, `addOns`, and `selectedCourses` for the selected options and every guest.
- Chatbot service discovery uses Flask's course API, distinguishes main courses from optional add-ons, rejects add-on-only selection, and retains selected catalog options through confirmation. Explicit `add <course name> <duration> min <price> VND` replies can add another main course or an add-on; a changed selection requires a fresh slot choice. The create tool still posts to Flask.
- Corrected the public course API specification and chatbot JSON schemas to describe the actual `durations` response and selected booking options.

## Verification

- Flask API suite: **73 passed**. New request-level tests cover public filtering, invalid options, closed shops, invalid type filters, and creating a group booking from discovered main and add-on options with persisted per-guest rows.
- Frontend Jest suite: **34 passed**; TypeScript check passed. New tests cover the shop catalog and link, catalog-derived durations, add-on and same-duration price selection, totals, and per-guest payloads.
- **134 focused chatbot tests passed**, including new service discovery and gateway-payload tests. The installed `pytest-asyncio` is incompatible with pytest in this environment, so the tests used a temporary asyncio pytest runner under `/private/tmp` without changing chatbot runtime dependencies.
- The Playwright reservation journey passed in Chromium against the existing local Next.js server, using mocked Flask responses. It selected a main course plus add-on for two guests and asserted the submitted `services`, `addOns`, and `selectedCourses` payload.

## Boundaries

- No database migration or new service data. The Course model has no description field; descriptions require real catalog copy and a separate schema/content change. Zero-minute add-ons in `seed_dev.py` remain unbookable under the existing booking rule and are not advertised.
- Slot availability remains optimistic until booking creation. Task 8's gender choice, nearby-slot recovery, and local-date correction remain separate. Task 10's chatbot therapist-preference flow remains separate.
- No deployed-service journey was run. The browser journey used mocked API responses; the Flask request-level test separately verified persisted per-guest rows. Existing local workspace changes outside Task 7 were left untouched.
