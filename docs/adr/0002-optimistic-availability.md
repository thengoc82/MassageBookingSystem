# Optimistic availability — no reservation holds

Reservations have been removed entirely. The booking flow no longer creates a time-limited hold on capacity. Instead, availability is treated as **optimistic**: it's shown as it was at query time, and the actual check happens atomically at booking creation under row-level locks (`FOR UPDATE SKIP LOCKED`).

## Context

Previously, the system had a two-phase flow: select → reserve (5-min hold) → confirm → booking created → reservation released. This required a `reservations` table, a Celery beat task to clean up expired holds, and a `reserved_until` field that needed constant maintenance. Despite this, the hold did not guarantee a successful booking — capacity could still change between reservation and confirmation.

## Decision

- Remove the `Reservation` model, service, blueprint, and cleanup task.
- `POST /api/bookings` now accepts all booking data directly (shopId, bookingDate, startTime, duration, numberOfPeople, services, phoneNumber, therapistPreference).
- The service method atomically selects available therapists using `FOR UPDATE SKIP LOCKED`, preventing double-booking at the database level.
- If no therapist is available at confirm time, the system returns `SLOT_UNAVAILABLE` or `INSUFFICIENT_THERAPISTS` errors. The frontend then refreshes availability and suggests nearby slots.

## Consequences

- **Positive**: Simpler architecture — no reservations table, no expiry cleanup, no Redis/Celery dependency for capacity management. Fewer states to reason about.
- **Positive**: No phantom "held but not booked" capacity — unavailable slots are detected immediately.
- **Negative**: The user experience is slightly worse in the race-condition case — if two customers pick the same slot, the second one will get an error and have to pick again. Mitigated by the short duration between slot selection and confirmation.
- **Migration**: The `reservations` table can be dropped. Existing active reservations are abandoned (they were only 5-minute holds, so all have expired by the time this ships).

## Supersedes

ADR 0001 (Reservation decoupled from Booking; Time Slots are dynamic) — the reservation concept it described no longer exists.
