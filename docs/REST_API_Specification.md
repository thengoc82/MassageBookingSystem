# Spa Booking REST API Specification

**Base URL:** `/api`

---

## Common Response Format

### Success
```json
{ "success": true, "data": {}, "message": "Success" }
```

### Error
```json
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Description" } }
```

### Paginated Success
```json
{ "success": true, "data": [], "pagination": { "page": 1, "size": 20, "total": 100, "totalPages": 5 }, "message": "Success" }
```

---

## Common Error Codes

| HTTP | Code                        | Description                              |
| ---- | --------------------------- | ---------------------------------------- |
| 400  | VALIDATION_ERROR            | Invalid or missing input data            |
| 400  | INVALID_REQUEST             | Invalid request format                   |
| 401  | UNAUTHORIZED                | Authentication required                  |
| 403  | FORBIDDEN                   | No permission                            |
| 404  | RESOURCE_NOT_FOUND          | Resource does not exist                  |
| 409  | DUPLICATE_RESOURCE          | Resource already exists                  |
| 409  | BOOKING_CONFLICT            | Booking time or resource conflict        |
| 422  | BUSINESS_RULE_VIOLATION     | Business validation failed               |
| 500  | INTERNAL_SERVER_ERROR       | Unexpected server error                  |

---

## Public Endpoints

---

### GET /api/shops

Retrieve all active shops.

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "shopId": 1,
      "shopName": "ABC Spa",
      "address": "123 Main Street",
      "phoneNumber": "0111222333",
      "status": "Open",
      "openTime": "08:00",
      "closeTime": "21:00"
    }
  ]
}
```

---

### GET /api/shops/{shop_id}

Retrieve shop detail by ID.

**Response (200):** Same shape as list item.

**Errors:** 404 SHOP_NOT_FOUND

---

### GET /api/shops/{shop_id}/courses

Retrieve active courses with bookable duration and price options at an open shop. Options with nonpositive duration or negative price are omitted; a course with no remaining options is omitted. Availability for a date and time is queried separately through `available-slots` and rechecked on booking creation. Course descriptions are not stored.

**Query Parameters:**
| Name  | Type    | Required | Description                |
| ----- | ------- | -------- | -------------------------- |
| type  | string  | No       | Filter: `main` or `addon`; any other value is rejected |

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "courseId": 1, "courseName": "Thai Massage", "durations": [{ "duration": 30, "price": 300000 }, { "duration": 60, "price": 500000 }], "courseType": "main" },
    { "courseId": 2, "courseName": "Aromatherapy", "durations": [{ "duration": 15, "price": 100000 }], "courseType": "addon" }
  ]
}
```

**Errors:** 404 `RESOURCE_NOT_FOUND` if the shop is missing or closed; 400 `VALIDATION_ERROR` for an unsupported `type`.

---

### GET /api/shops/{shop_id}/available-slots

Find available time slots for a booking at an open shop. For each 15-minute start step, capacity is the number of distinct active therapists whose shifts cover the full requested duration and who have no overlapping `Booked` or `CheckedIn` assignment. Legacy `Booking.therapist_id` and per-guest assignment rows both contribute to occupancy without double-counting a therapist. A closed shop returns an empty slot list.

**Query Parameters:**
| Name           | Type   | Required | Description                                           |
| -------------- | ------ | -------- | ----------------------------------------------------- |
| date           | string | Yes      | YYYY-MM-DD, not in the past                           |
| startTime      | string | No       | HH:MM, return grid steps at or after this time (never before opening) |
| duration       | int    | Yes      | Total minutes (main course + add-ons)                 |
| numberOfPeople | int    | Yes      | Number of guests                                      |
| courseIds      | string | No       | Comma-separated course IDs (currently unused for skill match) |
| gender         | string | No       | `Male` or `Female`, for one guest only; capacity and therapist IDs include only eligible therapists of that gender |
| show_therapists| string | No       | `"true"` → also return therapist-level availability  |

**Default response (200):**
```json
{
  "success": true,
  "data": [
    { "startTime": "09:00", "endTime": "10:00", "availableCapacity": 2 },
    { "startTime": "09:15", "endTime": "10:15", "availableCapacity": 1 }
  ]
}
```

**With `show_therapists=true` (200):** response adds a top-level `therapists` array and each slot
carries `availableTherapistIds` (therapists free at that exact time):
```json
{
  "success": true,
  "data": [
    { "startTime": "09:00", "endTime": "10:00", "availableCapacity": 2, "availableTherapistIds": [1, 2] }
  ],
  "therapists": [
    { "therapistId": 1, "name": "Anna", "gender": "Female" },
    { "therapistId": 2, "name": "Bob", "gender": "Male" }
  ]
}
```
When `show_therapists=true`, **all** shop grid steps are returned (not just those meeting capacity) so a
client grid stays stable after a booking — a booked slot simply drops the therapist id from the list. With `gender`, the top-level therapist list and per-slot IDs are filtered to that gender. Slot responses use `Cache-Control: no-store`; they remain provisional until booking creation succeeds.
The public response does not include booking IDs, codes, course names, or other booking details. Admins can request those details through `GET /api/admin/shops/{shop_id}/available-slots` with the same query parameters and an admin JWT; its response also includes `therapistBookingDetails`.

**Errors:**
| HTTP | Code                 | Condition          |
| ---- | -------------------- | ------------------ |
| 400  | VALIDATION_ERROR     | Missing or malformed date, time, duration, guest count, or gender; past date; gender with a group |
| 404  | RESOURCE_NOT_FOUND   | Shop not found     |

---

### GET /api/shops/{shop_id}/available-therapists

List therapists available at a specific date and time.

**Query Parameters:**
| Name      | Type   | Required | Description                  |
| --------- | ------ | -------- | ---------------------------- |
| date      | string | Yes      | YYYY-MM-DD                   |
| startTime | string | Yes      | HH:MM                        |
| duration  | int    | No       | Minutes, defaults to 60      |
| gender    | string | No       | Filter: `Male` or `Female`   |

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "therapistId": 2, "name": "Anna", "gender": "Female", "isAvailable": true },
    { "therapistId": 3, "name": "John", "gender": "Male", "isAvailable": false }
  ]
}
```

**Errors:**
| HTTP | Code               | Condition          |
| ---- | ------------------ | ------------------ |
| 400  | DATE_REQUIRED      | Missing date       |
| 400  | VALIDATION_ERROR   | Missing startTime  |
| 404  | SHOP_NOT_FOUND     | Shop not found     |

---

### POST /api/booking-eligibility-checks

Check if a customer is eligible to book before creating the booking.

**Request:**
```json
{
  "phoneNumber": "0123456789"
}
```

**Response (200):** `{ "success": true, "data": { "isEligible": true, "isBlocked": false } }`

If blocked:
```json
{ "success": true, "data": { "isEligible": false, "isBlocked": true } }
```

**Errors:**
| HTTP | Code                  | Condition              |
| ---- | --------------------- | ---------------------- |
| 400  | VALIDATION_ERROR      | Missing phone number   |
| 400  | INVALID_PHONE_NUMBER  | Invalid format         |

---

### POST /api/bookings

Create a new booking.

**Request:**
```json
{
  "phoneNumber": "0123456789",
  "shopId": 1,
  "bookingDate": "2026-07-15",
  "startTime": "10:00",
  "duration": 60,
  "numberOfPeople": 1,
  "services": [
    { "personIndex": 1, "courseId": 1 }
  ],
  "addOns": [
    { "personIndex": 1, "courseId": 3 }
  ],
  "therapistPreferenceType": "specific",
  "therapistPreferenceValue": 2
}
```

**Field Rules:**
| Field                      | Required | Description                                                  |
| -------------------------- | -------- | ------------------------------------------------------------ |
| phoneNumber                | Yes      | Customer lookup or auto-create                               |
| shopId                     | Yes      |                                                              |
| bookingDate                | Yes      | YYYY-MM-DD, not in the past                                  |
| startTime                  | Yes      | HH:MM                                                        |
| duration                   | Yes      | Positive total minutes (main courses + add-ons)              |
| numberOfPeople             | No       | Positive guest count; defaults to 1                          |
| services                   | Conditional | Array `{personIndex, courseId}`, main courses only; otherwise supply `courseId` for every guest |
| courseId                   | Conditional | Single main course fallback when `services` is absent    |
| addOns                     | No       | Array `{personIndex, courseId}`, addon courses only          |
| selectedCourses            | Conditional | Array `{courseId, duration, price}` for ambiguous catalog duration choices |
| therapistPreferenceType    | No       | `no_preference` \| `specific` \| `gender`                    |
| therapistPreferenceValue   | No       | `specific` → therapist id (int); `gender` → `Male`/`Female`  |

> Therapist preference is sent as `therapistPreferenceType` / `therapistPreferenceValue` (not the
> legacy `therapistId` / `therapistGender` fields). For `specific`, `therapistPreferenceValue` is the
> therapist id; the system rechecks that exact therapist in the create transaction.

**Business Rules:**
- If `phoneNumber` is new, auto-create customer
- Booking rejected if customer is on NG List
- Each guest receives the same sequence of one or more main courses and zero or more add-ons; their selected durations must sum to `duration`. Submitted duration/price options must match active courses at the selected shop.
- The shop must be open for the entire booking, and assigned therapists must have covering shifts.
- Group bookings (≥2) reject specific and gender therapist preferences; use `no_preference` or omit the preference.
- Availability is optimistic until creation. Creation rechecks and assigns distinct available therapists in one transaction; automatic and group selection prefer the fewest booked minutes on that date, then therapist ID.
- Booking code generated by the system (format `BK{YYYYMMDD}{4digits}`)

**Response (201):**
```json
{
  "success": true,
  "data": { "bookingId": 120, "bookingCode": "BK20260715001", "status": "Booked" },
  "message": "Booking created successfully."
}
```

**Errors:**
| HTTP | Code                        | Condition                     |
| ---- | --------------------------- | ----------------------------- |
| 400  | VALIDATION_ERROR            | Missing or invalid fields, course selection, or group preference |
| 404  | RESOURCE_NOT_FOUND          | Shop or course not found      |
| 422  | CUSTOMER_BLOCKED            | Customer on NG List           |
| 422  | SLOT_UNAVAILABLE            | No eligible therapist remains |
| 422  | INSUFFICIENT_THERAPISTS     | Too few therapists for a group |
| 422  | SHOP_CLOSED                 | Shop closed at selected time  |
| 409  | BOOKING_CONFLICT            | Database busy while confirming; retry the booking |

---

### POST /api/booking-access/challenges

Generate a random six-digit verification code for the supplied phone. Request JSON: `{ "phoneNumber": "0901234567" }`. In development, success returns `{ "success": true, "data": { "delivery": "terminal" }, "message": "Verification code generated" }` and prints the phone and code in the Flask terminal. The code is never returned by the API. The same response applies whether that phone has bookings. Codes expire after five minutes; requests are limited per phone and source IP. Production has no delivery provider yet and returns 503 `VERIFICATION_UNAVAILABLE` without printing a code.

### POST /api/booking-access/verifications

Exchange `{ "phoneNumber": "0901234567", "code": "123456" }` for `{ "success": true, "data": { "accessToken": "..." }, "message": "Phone verified" }`. The code is single use with at most five attempts. The token lasts 30 minutes and authorizes only that phone's bookings. Invalid or expired codes return 401 `UNAUTHORIZED`.

### GET /api/bookings

Retrieve bookings list with filters.

**Access:** Requires `Authorization: Bearer <customer access token>` and a `phone` query parameter matching the verified phone. An unverified phone number or booking code is not sufficient. Staff use `/api/admin/bookings` or `/api/therapists/bookings`; `/api/bookings/all` is removed.

**Query Parameters:**
| Name       | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| shopId     | int    | No       | Filter by shop                           |
| phone      | string | Yes      | Verified customer phone number           |
| status     | string | No       | `Booked`, `CheckedIn`, `CheckedOut`, `Cancelled` |
| dateFrom   | string | No       | YYYY-MM-DD                               |
| dateTo     | string | No       | YYYY-MM-DD                               |
| page       | int    | No       | Default 1                                |
| size       | int    | No       | Default 20, max 100                      |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "data": [
      {
        "bookingId": 120,
        "bookingCode": "BK20260715001",
        "shopId": 1,
        "shopName": "ABC Spa",
        "phoneNumber": "0123456789",
        "bookingDate": "2026-07-15",
        "startTime": "10:00",
        "numberOfPeople": 2,
        "status": "Booked",
        "therapistId": 2,
        "therapistName": "Anna"
      }
    ],
    "pagination": { "page": 1, "size": 20, "total": 30, "totalPages": 2 }
  }
}
```

---

### GET /api/bookings/{booking_id}

Retrieve full booking detail.

**Access:** Verified customer whose phone matches this booking, admin JWT, or therapist JWT assigned to this booking. An unrelated authenticated caller receives 404.

**Response (200):** Same booking fields as a list item, plus `services`, `addOns`, and saved `preferences` when present. `preferences.selectedCourses` contains chosen duration and price options when they were saved. The interval duration can be derived from `startTime` and `endTime`. Customer rank and ID are not returned.

**Errors:** 404 `RESOURCE_NOT_FOUND` for a missing booking or a booking outside the caller's scope.

---

### PATCH /api/bookings/{booking_id}

Update a `Booked` booking. The request is a nonempty JSON object containing only fields to change. Omitted fields retain their saved values.

**Access:** Verified customer whose phone matches this booking, or admin JWT. Therapists cannot modify bookings through this route.

**Request:**
```json
{
  "startTime": "11:00",
  "services": [{ "personIndex": 1, "courseId": 2 }],
  "therapistId": 3
}
```

**Supported fields:** `bookingDate` (`YYYY-MM-DD`), `startTime` (`HH:MM`), `duration` (positive minutes), `services`, `addOns`, `selectedCourses`, `courseId` (single-main-course fallback), and either legacy `therapistId` or `therapistPreferenceType` / `therapistPreferenceValue`. `therapistId: null` removes the explicit preference; an existing eligible assignment may remain. `numberOfPeople`, `shopId`, `phoneNumber`, and `status` cannot be changed through this endpoint. Group bookings cannot request a specific therapist or gender.

**Business Rules:**
- Only `Booked` status can be modified
- Changing time or duration recalculates `endTime`. The complete interval must fit within one day's shop hours.
- The effective course selection follows the same active-course, per-guest, catalog-option, and duration rules as creation.
- Every modification rechecks shift coverage and overlapping `Booked` / `CheckedIn` assignments in a transaction. The booking being edited does not conflict with itself. Existing eligible assignments are retained; replacements follow the creation workload ranking, and groups receive distinct therapists.
- A rejected modification leaves the original booking, course rows, therapist rows, and preferences unchanged.
- Public slot results include the booking being edited as occupied; the PATCH transaction excludes it. Clients may show public slots as guidance but must use the PATCH result as the final availability decision.

**Response (200):**
```json
{ "success": true, "data": { "bookingId": 120, "status": "Booked" }, "message": "Booking updated" }
```

**Errors:**
| HTTP | Code                    | Condition                                   |
| ---- | ----------------------- | ------------------------------------------- |
| 400  | VALIDATION_ERROR        | Invalid JSON, field, course selection, or duration |
| 404  | RESOURCE_NOT_FOUND      | Booking or selected course not found         |
| 422  | INVALID_MODIFY_STATUS   | Only Booked can be modified                  |
| 422  | SHOP_CLOSED             | Shop is closed or interval is outside hours  |
| 422  | SLOT_UNAVAILABLE        | No eligible therapist for a single guest    |
| 422  | INSUFFICIENT_THERAPISTS | Too few distinct therapists for a group     |
| 409  | BOOKING_CONFLICT        | SQLite write lock timed out                  |

---

## Admin Endpoints

### Shops

---

### GET /api/admin/shops

Retrieve all shops including inactive ones.

**Query Parameters:**
| Name   | Type   | Required | Description                  |
| ------ | ------ | -------- | ---------------------------- |
| status | string | No       | `Open`, `Closed`, `All`      |
| page   | int    | No       | Default 1                    |
| size   | int    | No       | Default 20                   |

**Response (200):** Same shape as public endpoint.

---

### POST /api/admin/shops

Create a new shop.

**Request:**
```json
{
  "shopName": "ABC Spa",
  "address": "123 Main Street",
  "phoneNumber": "0111222333",
  "openTime": "08:00",
  "closeTime": "21:00"
}
```

**Validation:** shopName required, address required, phoneNumber required + unique.

**Response (201):**
```json
{ "success": true, "data": { "shopId": 10 }, "message": "Shop created." }
```

**Errors:**
| HTTP | Code                | Condition           |
| ---- | ------------------- | ------------------- |
| 400  | SHOP_NAME_REQUIRED   | Missing name        |
| 400  | ADDRESS_REQUIRED     | Missing address     |
| 400  | INVALID_PHONE_NUMBER | Invalid format      |
| 409  | SHOP_ALREADY_EXISTS  | Phone or name taken |

---

### GET /api/admin/shops/{shop_id}

Retrieve shop detail.

---

### PATCH /api/admin/shops/{shop_id}

Update shop information.

**Request:**
```json
{ "shopName": "ABC Spa Premium", "status": "Open", "openTime": "09:00", "closeTime": "22:00" }
```

**Errors:** 404 SHOP_NOT_FOUND

---

### Courses

---

### GET /api/admin/shops/{shop_id}/courses

Retrieve all courses for a shop including inactive ones.

**Query Parameters:** `?type=main|addon&status=active|inactive`

---

### POST /api/admin/shops/{shop_id}/courses

Create a new course for a shop.

**Request:**
```json
{ "courseName": "Aromatherapy", "duration": 90, "price": 800000, "courseType": "main" }
```

**Validation:** courseName required, duration > 0, price >= 0, courseType must be `main` or `addon`.

**Response (201):**
```json
{ "success": true, "data": { "courseId": 10 }, "message": "Course created." }
```

**Errors:** 400 INVALID_COURSE_TYPE, 404 SHOP_NOT_FOUND

---

### GET /api/admin/courses/{course_id}

Retrieve course detail.

**Errors:** 404 COURSE_NOT_FOUND

---

### PATCH /api/admin/courses/{course_id}

Update course.

**Request:**
```json
{ "courseName": "Aromatherapy Premium", "price": 900000, "status": "inactive" }
```

**Errors:** 404 COURSE_NOT_FOUND, 400 INVALID_COURSE_TYPE

---

### Therapists

---

### GET /api/admin/shops/{shop_id}/therapists

Retrieve all therapists for a shop.

**Query Parameters:** `?gender=Male|Female&status=active|inactive`

---

### POST /api/admin/shops/{shop_id}/therapists

Create a new therapist.

**Request:**
```json
{
  "name": "Anna",
  "gender": "Female",
  "phoneNumber": "0999888777"
}
```

**Validation:** name required, gender required (Male/Female).

**Response (201):**
```json
{ "success": true, "data": { "therapistId": 5 }, "message": "Therapist created." }
```

---

### GET /api/admin/therapists/{therapist_id}

Retrieve therapist detail with shift schedule.

**Response (200):**
```json
{
  "success": true,
  "data": {
    "therapistId": 5,
    "shopId": 1,
    "name": "Anna",
    "gender": "Female",
    "phoneNumber": "0999888777",
    "status": "active",
    "shifts": [
      { "dayOfWeek": "Monday", "startTime": "08:00", "endTime": "17:00" },
      { "dayOfWeek": "Tuesday", "startTime": "08:00", "endTime": "17:00" }
    ]
  }
}
```

---

### PATCH /api/admin/therapists/{therapist_id}

Update therapist.

**Request:**
```json
{ "name": "Anna Nguyen", "phoneNumber": "0999888777", "status": "inactive" }
```

**Errors:** 404 THERAPIST_NOT_FOUND

---

### Therapist Shifts

---

All therapist shift routes require an admin JWT. Shift rows are recurring weekly rules: `effectiveFrom` is inclusive and there is no end date. A single shift must cover the entire booking interval. Shifts for one therapist and weekday cannot overlap, including when their `effectiveFrom` dates differ; adjacent shifts are valid. Edits and deletion return 409 `SHIFT_BOOKING_CONFLICT` if they would leave an assigned future `Booked` or `CheckedIn` booking uncovered. Successful changes affect subsequent slot availability queries. The existing `GET /api/admin/therapists/{therapist_id}/schedule` continues to return bookings.

SQLite shift writes that time out waiting for the database lock return 409 `SHIFT_CONFLICT` and can be retried.

### GET /api/admin/shops/{shop_id}/therapist-shifts

Retrieve all shifts for a shop.

**Query Parameters:** `?therapistId=5&dayOfWeek=Monday`

**Response (200):** `data` is an array of `{ "shiftId": 20, "therapistId": 5, "dayOfWeek": "Monday", "startTime": "08:00", "endTime": "17:00", "effectiveFrom": "2026-07-01" }` items.

**Errors:** 400 `VALIDATION_ERROR` for invalid filters, 404 `RESOURCE_NOT_FOUND` for a missing shop.

---

### POST /api/admin/therapist-shifts

Create a shift for a therapist.

**Request:**
```json
{
  "therapistId": 5,
  "dayOfWeek": "Monday",
  "startTime": "08:00",
  "endTime": "17:00",
  "effectiveFrom": "2026-07-01"
}
```

**Validation:** all five fields are required. `therapistId` is a positive integer; `dayOfWeek` is Monday–Sunday; times use 24-hour `HH:MM` and `startTime < endTime`; `effectiveFrom` is a valid `YYYY-MM-DD` date.

**Response (201):**
```json
{ "success": true, "data": { "shiftId": 20, "therapistId": 5, "dayOfWeek": "Monday", "startTime": "08:00", "endTime": "17:00", "effectiveFrom": "2026-07-01" }, "message": "Shift created" }
```

**Errors:** 400 `VALIDATION_ERROR`, 404 `RESOURCE_NOT_FOUND` for a missing therapist, 409 `SHIFT_OVERLAP`.

---

### GET /api/admin/therapist-shifts/{shift_id}

Retrieve shift detail.

**Response (200):** Same shift object as the create response. **Errors:** 404 `RESOURCE_NOT_FOUND`.

---

### PATCH /api/admin/therapist-shifts/{shift_id}

Update shift.

**Request:**
```json
{ "startTime": "09:00", "endTime": "18:00" }
```

Any nonempty subset of `dayOfWeek`, `startTime`, `endTime`, and `effectiveFrom` may be supplied. `therapistId` is immutable. The response returns the updated shift object.

**Errors:** 400 `VALIDATION_ERROR`, 404 `RESOURCE_NOT_FOUND`, 409 `SHIFT_OVERLAP` or `SHIFT_BOOKING_CONFLICT`.

---

### DELETE /api/admin/therapist-shifts/{shift_id}

Delete a weekly shift. A shift covering a future assigned booking cannot be removed unless another shift still covers the entire booking interval.

**Response (200):** `{ "success": true, "data": { "shiftId": 20 }, "message": "Shift deleted" }`

**Errors:** 404 `RESOURCE_NOT_FOUND`, 409 `SHIFT_BOOKING_CONFLICT`.

---

### Customer Restrictions (NG List)

All routes in this section require an admin JWT. Active restriction records determine managed blocks; a legacy `Customer.is_blocked` flag still blocks until the data migration converts it to a record. Removal deactivates an entry and retains its history. Public booking and eligibility responses never include a restriction reason or administrator identity.

---

### GET /api/admin/customer-restrictions

Retrieve restriction entries, active by default.

**Query Parameters:** `?phone=01234&status=active|inactive|all&page=1&size=20`. `phone` is a prefix filter; `status` defaults to `active`; `size` is at most 100.

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "restrictionId": 1, "customerId": 10, "phoneNumber": "0111222333", "reason": "No-show 3 times", "blockedAt": "2026-06-01T10:00:00", "blockedBy": "admin", "updatedAt": "2026-06-01T10:00:00", "isActive": true }
  ],
  "pagination": { "page": 1, "size": 20, "total": 5, "totalPages": 1 }
}
```

---

### POST /api/admin/customer-restrictions

Block an existing customer. The phone may be in local, `+84`, or `84` form when it matches an existing customer; an active restriction for any matching phone alias causes a conflict. `reason` must be nonblank. A new block after removal creates a new record.

**Request:**
```json
{ "phoneNumber": "0111222333", "reason": "No-show 3 times" }
```

**Response (201):**
```json
{ "success": true, "data": { "restrictionId": 1, "customerId": 10, "phoneNumber": "0111222333", "reason": "No-show 3 times", "blockedAt": "2026-06-01T10:00:00", "blockedBy": "admin", "updatedAt": "2026-06-01T10:00:00", "isActive": true }, "message": "Customer blocked" }
```

**Errors:** 400 `VALIDATION_ERROR`, 404 `RESOURCE_NOT_FOUND`, 409 `CUSTOMER_ALREADY_BLOCKED` or `RESTRICTION_CONFLICT` (database busy).

---

### GET /api/admin/customer-restrictions/{restriction_id}

Retrieve restriction detail.

**Response (200):** The same entry shape as the list. **Errors:** 404 `RESOURCE_NOT_FOUND`.

---

### PATCH /api/admin/customer-restrictions/{restriction_id}

Update the reason or unblock. `isActive` may only be set to `false`; reblocking creates a new entry. An inactive entry remains available in history.

**Request:**
```json
{ "reason": "Resolved after payment", "isActive": false }
```

**Response (200):** The updated entry. **Errors:** 400 `VALIDATION_ERROR`, 404 `RESOURCE_NOT_FOUND`, 409 `RESTRICTION_CONFLICT`.

---

### DELETE /api/admin/customer-restrictions/{restriction_id}

Remove an entry from the active NG List by setting `isActive` to `false`. The record remains in history. Repeating the request for an inactive entry succeeds.

**Response (200):** `{ "success": true, "data": { "restrictionId": 1 }, "message": "Customer unblocked" }`

**Errors:** 404 `RESOURCE_NOT_FOUND`, 409 `RESTRICTION_CONFLICT`.

---

### Bookings

---

### GET /api/admin/bookings

Retrieve all bookings with extended admin filters.

**Query Parameters:**
| Name       | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| shopId     | int    | No       | Filter by shop                           |
| customerId | int    | No       | Filter by customer                       |
| phone      | string | No       | Search by phone                          |
| status     | string | No       | `Booked`, `CheckedIn`, `CheckedOut`, `Cancelled` |
| dateFrom   | string | No       | YYYY-MM-DD                               |
| dateTo     | string | No       | YYYY-MM-DD                               |
| therapistId| int    | No       | Filter by therapist                      |
| page       | int    | No       | Default 1                                |
| size       | int    | No       | Default 20, max 100                      |

**Response (200):** Paginated list (same shape as public + internal notes).

---

### GET /api/admin/bookings/{booking_id}

Retrieve full booking detail including internal notes.

**Response (200):** Same as public + `"internalNotes": "VIP customer"`, `"createdBy": "admin"`, `"createdAt": "..."`.

**Errors:** 404 BOOKING_NOT_FOUND

---

### Booking Status Transitions

```
Booked ──► CheckedIn ──► CheckedOut
  │
  └──► Cancelled
```

**Status Management (Admin):**
- `PATCH /api/bookings/{booking_id}/cancel` — Verified booking phone or admin JWT; only `Booked`.
- A cancellation after check-in or an earlier cancellation returns HTTP 422 `INVALID_CANCEL_STATUS` and does not change the booking.
- `PATCH /api/bookings/{booking_id}/checkin` — Admin JWT only; only `Booked`.
- `PATCH /api/bookings/{booking_id}/checkout` — Admin JWT only; only `CheckedIn`.
- Assigned therapists use `/api/therapists/bookings/{booking_id}/checkin` and `/checkout`. Admins can also use `/api/admin/bookings/{booking_id}/cancel`, `/checkin`, and `/checkout`.

---

## Therapist Endpoints

---

### GET /api/therapists/me/schedule

Retrieve the authenticated therapist's schedule for a date range.

**Query Parameters:**
| Name     | Type   | Required | Description    |
| -------- | ------ | -------- | -------------- |
| dateFrom | string | Yes      | YYYY-MM-DD     |
| dateTo   | string | Yes      | YYYY-MM-DD     |

**Response (200):**
```json
{
  "success": true,
  "data": {
    "therapistId": 2,
    "name": "Anna",
    "shopId": 1,
    "schedule": [
      {
        "date": "2026-07-15",
        "dayOfWeek": "Wednesday",
        "shiftStart": "08:00",
        "shiftEnd": "17:00",
        "bookings": [
          { "bookingId": 120, "startTime": "10:00", "endTime": "11:00", "status": "Booked", "numberOfPeople": 1 }
        ]
      }
    ]
  }
}
```

**Errors:**
| HTTP | Code               | Condition            |
| ---- | ------------------ | -------------------- |
| 400  | DATE_REQUIRED      | Missing date range   |
| 401  | UNAUTHORIZED       | Not authenticated    |
| 403  | FORBIDDEN          | Not a therapist role |

---

## Endpoint Summary

### Public
```
GET    /api/shops
GET    /api/shops/{shop_id}
GET    /api/shops/{shop_id}/courses
GET    /api/shops/{shop_id}/available-slots
GET    /api/shops/{shop_id}/available-therapists
POST   /api/booking-eligibility-checks
POST   /api/bookings
POST   /api/booking-access/challenges
POST   /api/booking-access/verifications
```

### Customer phone token or staff JWT
```
GET    /api/bookings
GET    /api/bookings/{booking_id}
PATCH  /api/bookings/{booking_id}
PATCH  /api/bookings/{booking_id}/cancel
PATCH  /api/bookings/{booking_id}/checkin
PATCH  /api/bookings/{booking_id}/checkout
```

### Admin
```
GET    /api/admin/shops
POST   /api/admin/shops
GET    /api/admin/shops/{shop_id}
PATCH  /api/admin/shops/{shop_id}

GET    /api/admin/shops/{shop_id}/courses
POST   /api/admin/shops/{shop_id}/courses
GET    /api/admin/courses/{course_id}
PATCH  /api/admin/courses/{course_id}

GET    /api/admin/shops/{shop_id}/therapists
POST   /api/admin/shops/{shop_id}/therapists
GET    /api/admin/therapists/{therapist_id}
PATCH  /api/admin/therapists/{therapist_id}

GET    /api/admin/shops/{shop_id}/therapist-shifts
POST   /api/admin/therapist-shifts
GET    /api/admin/therapist-shifts/{shift_id}
PATCH  /api/admin/therapist-shifts/{shift_id}
DELETE /api/admin/therapist-shifts/{shift_id}

GET    /api/admin/customer-restrictions
POST   /api/admin/customer-restrictions
GET    /api/admin/customer-restrictions/{restriction_id}
PATCH  /api/admin/customer-restrictions/{restriction_id}
DELETE /api/admin/customer-restrictions/{restriction_id}

GET    /api/admin/bookings
GET    /api/admin/bookings/{booking_id}
GET    /api/admin/shops/{shop_id}/available-slots
```

### Therapist
```
GET    /api/therapists/me/schedule
GET    /api/therapists/bookings
PATCH  /api/therapists/bookings/{booking_id}/checkin
PATCH  /api/therapists/bookings/{booking_id}/checkout
```
