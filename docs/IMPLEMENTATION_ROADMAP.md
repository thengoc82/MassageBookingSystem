# Implementation roadmap

Updated: 2026-11-26

This roadmap preserves the order, dependencies, risks, and verification criteria of the 12-task implementation review. Status and scope have been checked against the current source and project documents. It is a plan for the remaining work, not a claim that unrun scenarios have passed. No tests were run while preparing this document.

## Decisions and corrections to the review

- **Tasks 1–3 are complete.** Task 1 added authoritative creation validation in commit `5d9a027`; Task 2 made SQLite creation atomic and aligned therapist capacity in commit `46f4151`; Task 3 repaired booking modification. The latest Flask API run was **63 passed** after Task 5. See [project status](PROJECT_STATUS.md), [Task 3 record](progress/task-03.md), and [ADR 0003](adr/0003-atomic-therapist-assignment.md). Earlier progress records describe later tasks as unfinished because they are historical records.
- **Keep the accepted course rule.** A guest receives the same sequence of **one or more** main courses and zero or more add-ons as every other guest. Selected durations must total the reserved duration. [CONTEXT.md](CONTEXT.md) and [the API specification](REST_API_Specification.md) are the current contract; report §3.5's “exactly one main course” statement is outdated. `selectedCourses` is needed when catalog options are ambiguous.
- **Keep optimistic availability.** Slots are snapshots; creation makes the final decision. SQLite uses `BEGIN IMMEDIATE`, not the row-level lock assumed in the report and the original ADR 0002 wording. The file-backed concurrency test covers creation through `BookingService.create`; a live non-SQLite concurrency result is still missing.
- **Reconcile two scenario expectations.** Under the accepted API rule, a group request with a specific therapist is rejected without creating a booking; a separate request without that preference can receive automatic assignments. Report TC-02 combines those outcomes as if they occur in one request. TC-04's one-confirmed-booking condition has a backend test, while offering alternative slots remains Task 8.
- **Existing UI and docs differ from the review in places.** The admin courses page already edits courses, but shops and therapists pages only create/list them. The [REST API specification](REST_API_Specification.md) lists shift and NG List routes absent from the Flask code and includes some admin route shapes that differ from the code. Task 12 must reconcile those contracts against measured behavior.

Voice booking, payments, notifications, loyalty features, and Socket.IO UI updates remain outside these 12 tasks, as in the review.

## Ordered implementation checklist

### 1. Settle the main-course rule and validate booking creation — completed

**Dependency:** Foundation for assignment, web, and chatbot booking.

**Implemented:** [BookingService.create](../spa-booking-api/app/services/booking_service.py) validates request fields, shop hours, shift coverage, course shop/type/status, catalog duration and price options, per-guest selection, and group preferences. It retains `POST /api/bookings` fields, the `courseId` fallback, and the success response. The accepted multi-main rule is recorded in [CONTEXT.md](CONTEXT.md).

**Risk retained:** Stricter checks reject formerly accepted invalid payloads. The backend's current-date check uses UTC rather than a shop-local timezone.

**Verification:** The Task 1 API tests cover shop hours, shifts, course ownership/type, duration, guest count, group preference, and valid multi-main/add-on requests. Retain a valid web payload regression when later tasks change the form.

### 2. Make therapist assignment and slot capacity consistent under concurrency — completed for SQLite creation

**Depends on:** Task 1's validated booking interval and course contract.

**Implemented:** [BookingService](../spa-booking-api/app/services/booking_service.py) locks before the create-time availability read, assigns distinct therapists by daily booked minutes and ID, and commits assignments with the booking. [TherapistService](../spa-booking-api/app/services/therapist_service.py) and [SlotService](../spa-booking-api/app/services/slot_service.py) use distinct eligible therapists for capacity, counting group and legacy assignments without duplication.

**Risk retained:** SQLite serializes database writers; a future slow POS call inside the transaction can increase contention. The non-SQLite Shop row-lock path has not had a live concurrency test. Booking modification can still bypass capacity checks until Task 3.

**Verification:** The recorded file-backed SQLite race test confirms one success for two requests competing for the final therapist. Group, duplicate-shift, legacy-assignment, occupancy, and slot-capacity tests are included in the recorded 33-test Flask suite. Verify any non-SQLite deployment separately before claiming its atomic guarantee.

### 3. Repair booking modification — completed

**Depends on:** Tasks 1 and 2; rescheduling must use their validation, availability, assignment, and transaction rules.

**Implemented:** [BookingService.update](../spa-booking-api/app/services/booking_service.py) and the PATCH route now validate the proposed interval and courses, recompute `end_time`, recheck shifts and overlapping assignments under the creation lock, and keep per-guest assignments and the legacy therapist pointer consistent. Existing `startTime` / `therapistId` PATCH fields and the response envelope remain supported. See [Task 3 record](progress/task-03.md).

**Risk retained:** The route remains public until Task 4, so modification and access control should be released together if needed. The non-SQLite lock path has not been verified against a live database; no POS modification adapter exists.

**Verification:** The Flask suite passed 48 tests, including valid reschedule, occupied therapist/slot rejection, non-`Booked` rejection, group assignment consistency, unchanged persisted state after rejection, and a file-backed SQLite create-versus-modify race.

### 4. Scope public booking access and staff-only transitions — implemented for local development; deployed delivery deferred

**Depends on:** Task 3's modification behavior and the existing JWT-protected admin/therapist routes.

**Work:** Apply a concrete customer ownership rule to public list, detail, modify, and cancel operations. Remove or protect `/api/bookings/all`; restrict check-in/out to staff routes using the existing role checks. Adjust [frontend API calls](../spa-booking-frontend/lib/api.ts) and chatbot lookup/write tools only as required by the chosen rule.

**Risk:** A phone number is an identifier, not proof of ownership. Define a usable verification mechanism before exposing customer data or writes, while preserving phone-based lookup without accounts and compatible response shapes where possible.

**Verify:** Unauthenticated callers cannot list unrelated bookings or check in/out; verified customer lookup, detail, edit, and cancel work only for their booking; admin and therapist workflows still work.

**Implementation:** Development terminal code delivery grants a short-lived customer token for local booking lookup and writes. Admin and assigned therapist JWTs retain staff access. The public availability endpoint no longer returns booking details; the admin Gantt uses a protected route. See [ADR 0004](adr/0004-phone-verified-booking-access.md) and [Task 4 record](progress/task-04.md). Terminal delivery cannot prove phone ownership; deployed customer access remains disabled until an out-of-band provider is added.

### 5. Add weekly therapist shift management — completed

**Depends on:** Task 2's shift-aware availability and Task 4's staff access boundary.

**Work:** Add JWT-protected list/create/edit/delete shift routes around [TherapistShift](../spa-booking-api/app/models/therapist_shift.py), then add controls to [admin schedules](../spa-booking-frontend/app/admin/schedules/page.tsx) via `lib/api.ts`. Keep the existing therapist schedule endpoint, which returns bookings, intact.

**Risk:** Editing a shift can affect future capacity and existing bookings. Validate overlapping shifts, effective dates, and the effect of edits on affected bookings rather than treating the current booking schedule as shift management.

**Verify:** Create, edit, list, and delete weekly shifts; reject invalid overlaps and changes that uncover future bookings; confirm that affected dates change slot availability while the existing booking schedule response remains compatible.

**Implementation:** Admin JWT protected shift list, detail, create, edit, and delete routes use the existing `TherapistShift` model. The admin schedules page manages shifts and still shows bookings. Shift writes share booking's shop lock, and edits or deletion that uncover future assigned bookings are rejected. See [Task 5 record](progress/task-05.md). No migration was needed.

### 6. Add NG List management — planned

**Depends on:** Task 1's booking eligibility check and Task 4's protected admin operations.

**Work:** Add JWT-protected restriction list/create/detail/update routes around [CustomerRestriction](../spa-booking-api/app/models/customer_restriction.py) and controls on [admin customers](../spa-booking-frontend/app/admin/customers/page.tsx). Reuse `CustomerService.check_eligibility`.

**Risk:** `Customer.is_blocked` and active restriction records can disagree. Define which state is authoritative and how reasons and unblock actions appear to the API and UI.

**Verify:** Block with a reason, reject creation for that customer, show the reason, unblock, and then permit a valid booking. Check authorization for every management route.

### 7. Complete service discovery and booking options — planned

**Depends on:** Task 1's multi-main/add-on and catalog-option rules; Task 6 is independent but remains earlier in the ordered checklist.

**Work:** Show shop courses with duration and price on [/shops](../spa-booking-frontend/app/shops/page.tsx). Extend [BookingForm](../spa-booking-frontend/components/booking/BookingForm.tsx) to select add-ons and send per-guest `addOns` and correct `selectedCourses`; reuse `api.shops.getCourses`. Route the `/shops` booking link through a valid slot-selection context instead of opening `/booking` without `pending_booking`.

**Risk:** The chosen main courses and add-ons must total the reserved duration and use active catalog prices. The UI currently filters out add-ons, although the API returns them.

**Verify:** Choose main course(s) plus an add-on, display the correct per-guest and group totals, submit one valid booking, and inspect persisted per-person services and add-ons.

### 8. Complete customer slot choices and recovery — planned

**Depends on:** Tasks 2 and 7, so displayed choices match create-time capacity and selected course duration.

**Work:** Add a gender choice for one guest, preserve specific-therapist and group paths, and show selectable nearby slots after a slot disappears at precheck or POST. Reuse `getAvailableSlots` and `localDateStr`; fix the [dashboard](../spa-booking-frontend/app/dashboard/page.tsx) UTC `toISOString()` conversion for local booking dates. Ensure gender-filtered slot suggestions reflect therapist eligibility; the current slot service accepts `gender` but does not use it.

**Risk:** Suggested slots are also snapshots and can disappear before submission. Keep the final server-side recheck and submit only the customer's final choice.

**Verify:** Specific, gender, and group paths submit the intended preference; a lost slot offers selectable alternatives; a second loss is handled cleanly; dates remain correct near local midnight.

### 9. Add customer booking edits — planned

**Depends on:** Task 3's safe PATCH behavior, Task 4's ownership rule, and Tasks 7–8's customer booking context.

**Work:** Add edit controls to [/my-bookings](../spa-booking-frontend/app/my-bookings/page.tsx) and [/bookings/[id]](../spa-booking-frontend/app/bookings/[id]/page.tsx), using the repaired PATCH API and existing detail view.

**Risk:** Only `Booked` bookings may change. The UI must not assume that knowing a booking ID or phone number grants edit permission.

**Verify:** An authorized customer edits an eligible booking and sees updated time and assignments; occupied slots and edits after check-in or cancellation are rejected without changing data.

### 10. Align the chatbot booking contract — planned

**Depends on:** Tasks 1, 3, 4, and 8; chatbot writes must use the same validated contract and access rules as the web flow.

**Work:** Update [CreateBookingRequest](../chatbot/models/__init__.py), [confirmation payload construction](../chatbot/app/chat_endpoint.py), and [write tools](../chatbot/tools/write_tools.py) to send Flask's `therapistPreferenceType`/`therapistPreferenceValue` fields and accepted course selections. The current chat path builds one course per guest and still models `therapistId`/`therapistGender`. Reuse pending-action confirmation and slot recovery; align modify/cancel tools with Task 4's access rule.

**Risk:** Existing chatbot tests and schemas encode the older request model. Course duration options and guest count must survive confirmation without silently dropping the user's choices.

**Verify:** A confirmed chat booking sends intended service selection, therapist preference, duration, and guest count; cancellation or rejection before confirmation never writes; a lost slot offers recovery.

### 11. Verify RAG configuration and customer advice — planned verification

**Depends on:** Task 10 for a complete customer chat flow; retrieval code and indexing can be checked independently.

**Work:** Use existing [knowledge ingestion guidance](../chatbot/knowledge/README.md), `KnowledgeService`, and `faqSearch` to confirm configured pgvector data and customer-facing answers. Check the running chatbot, Redis session store, and configured knowledge index.

**Risk:** Without `CHATBOT_PG_DSN`, FAQ retrieval is disabled. Redis is required for normal session handling. The knowledge docs say `CHATBOT_OPENAI_API_KEY` is optional for concise grounded answers: without it, a matching excerpt and source can still be returned. Natural-language behavior may additionally depend on the configured LLM path.

**Verify:** Index a known FAQ, ask a question absent from the conversation, and confirm the answer matches and cites the indexed source. Record the actual service configuration and result.

### 12. Run the complete scenario suite and reconcile documentation — planned

**Depends on:** Tasks 1–11 and a runnable frontend, booking API, chatbot, Redis, and configured knowledge store for the scenarios that use them.

**Work:** Extend backend, frontend, chatbot, and browser tests for report TC-01–TC-08. Record measured results in the report and update the REST API specification to match implemented routes, payloads, authorization, and responses. Include admin course-route differences and shift/NG List endpoints in that audit.

**Risk:** The report describes some routes and outcomes as complete without a recorded live result. TC-02's combined reject-and-assign wording conflicts with the accepted group rule; test the rejection and valid automatic assignment as separate requests. TC-04 needs both the backend race result and the customer alternative-slot result.

**Verify:** Record actual pass/fail evidence for all eight scenarios, including booking status transitions, chatbot confirmation, and grounded FAQ retrieval. Inspect the final diff and confirm API response compatibility before marking the roadmap complete.
