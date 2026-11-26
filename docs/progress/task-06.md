# Task 06 — NG List management

**Status:** Completed on 2026-11-26

## Implementation

- Added admin JWT protected list, detail, create, update, and soft-remove routes for the existing `CustomerRestriction` model. List supports phone prefix, active/inactive/all status, and pagination. Reasons, history, and actor names remain admin-only.
- Active restriction records determine managed blocks. `Customer.is_blocked` is synchronized for existing customer displays and remains an eligibility fallback if code starts before the data migration runs. The migration converts legacy flag-only blocks to reasoned records with an explicit legacy attribution, then reconciles the flag; no schema change was needed.
- Booking creation checks eligibility while holding its existing SQLite write transaction or, on other databases, a customer row lock. Restriction writes take the same customer lock. Local, `+84`, and `84` variants of the same phone share eligibility while legacy noncanonical phones retain exact matching.
- Extended `/admin/customers` with active and historical restriction lists, phone search, pagination, add, edit reason, and remove controls. Removal deactivates the entry; a later block creates a new record. Existing bookings are not altered.

## Verification

- Flask API suite: **70 passed**. New request-level tests cover admin authorization for all routes, CRUD and history, pagination, validation and missing customers, block → booking rejection → unblock → successful booking, public non-disclosure, phone aliases, multiple active records, and legacy migration idempotence.
- Frontend Jest suite: **30 passed**. New tests cover authenticated API calls, reason and status display, add/edit/remove, history search, refreshes, API error display, and booking form handling of a blocked response.
- Frontend TypeScript type check passed.

## Boundaries

- The non-SQLite customer row-lock path has not been tested against a live non-SQLite database, matching the existing booking concurrency boundary.
- The legacy migration has no safe rollback of generated history; its downgrade deliberately preserves those records.
