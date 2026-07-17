# Therapist Availability Gantt — Implementation Summary

Feature: a dashboard grid showing each therapist as a row (name on the left) and time slots as
columns, where a green cell means that therapist is available at that time. Clicking a green cell
books that specific therapist at that time.

## Backend (spa-booking-api)

### `app/services/slot_service.py`
- `SlotService.get_available_slots(...)` gained a `show_therapists: bool` parameter (default `False`).
- When `show_therapists=True` it loads all `active` therapists for the shop once, then for every
  shop time slot (15-min steps) computes which therapists are free at that exact time via
  `TherapistService.is_available(...)`.
- Returns a dict `{ "therapists": [...], "slots": [...] }` instead of a flat slot list. Each slot
  carries `availableTherapistIds: number[]`.
- **All** shop slots are always returned (not just those meeting `number_of_people`), so the grid
  stays stable after a booking — a booked slot simply drops the therapist's id from the list.
- When `show_therapists=False` the response is unchanged (backward compatible).

### `app/blueprints/public/slots.py`
- `/shops/<id>/available-slots` now reads `show_therapists` query flag.
- If true, responds with both top-level `data` (slots) and `therapists` arrays:
  ```json
  { "success": true, "data": [...slots], "therapists": [...], "message": "Success" }
  ```
- If false, original `success_response(slots)` shape preserved.

### Tests (`tests/test_booking_flow.py`)
- Added `test_get_available_slots_with_therapists` asserting all slots returned, each with
  `availableTherapistIds` referencing valid therapist ids.

## Frontend (spa-booking-frontend)

### `types/index.ts`
- `TimeSlot.availableTherapistIds?: number[]` added.
- New `TherapistInfo { therapistId, name, gender }`.

### `components/TherapistGantt.tsx` (new)
- Client component. Fetches `/available-slots?show_therapists=true`.
- Renders: sticky left column of therapist names + horizontally scrollable grid of time-slot
  columns. Green = available, white = unavailable.
- Cell click fires `onSelectSlot(startTime, therapistId)`.

### `app/dashboard/page.tsx`
- Replaced the old single-row 24h grid with `<TherapistGantt>`.
- `handleSlotClick(time, therapistId)` routes to
  `/reservation?shopId=&date=&time=&therapistId=<id>`.

### `app/reservation/page.tsx`
- Reads `therapistId` from query. If present, sets `therapistPref='specific'` and injects
  `therapistPreferenceType='specific'` + `therapistPreferenceValue=<id>` into the booking payload
  (backend locks that exact therapist). Shows a "Locked to selected therapist" badge.

## Flow
Dashboard cell click → `/reservation?...&therapistId=X` → booking created with that therapist
locked → dashboard Gantt updates (cell turns white) while the time column remains visible.

## Notes / not yet done
- `TherapistGantt` `duration` is hardcoded to 60 on the dashboard call (no duration selector yet).
- Multi-person (`number_of_people > 1`) not considered — grid is built for single-therapist booking.
- Removed the temporary `/debug` test page; dashboard is now the home for the Gantt.
