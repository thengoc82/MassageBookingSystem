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

Retrieve courses for a shop. Optionally filter by type.

**Query Parameters:**
| Name  | Type    | Required | Description                |
| ----- | ------- | -------- | -------------------------- |
| type  | string  | No       | Filter: `main` or `addon`  |

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "courseId": 1, "courseName": "Thai Massage", "duration": 60, "price": 500000, "courseType": "main" },
    { "courseId": 2, "courseName": "Hot Stone", "duration": 30, "price": 200000, "courseType": "addon" }
  ]
}
```

**Errors:** 404 SHOP_NOT_FOUND

---

### GET /api/shops/{shop_id}/available-slots

Find available time slots for a booking. Capacity is computed per 15-minute step as
(active therapists on shift) − (overlapping bookings).

**Query Parameters:**
| Name           | Type   | Required | Description                                           |
| -------------- | ------ | -------- | ----------------------------------------------------- |
| date           | string | Yes      | YYYY-MM-DD, not in the past                           |
| startTime      | string | No       | HH:MM, filter from specific time                      |
| duration       | int    | Yes      | Total minutes (main course + add-ons)                 |
| numberOfPeople | int    | Yes      | Number of guests                                      |
| courseIds      | string | No       | Comma-separated course IDs (currently unused for skill match) |
| gender         | string | No       | Preferred therapist gender: `Male` or `Female`        |
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
When `show_therapists=true`, **all** shop slots are returned (not just those meeting capacity) so a
client grid stays stable after a booking — a booked slot simply drops the therapist id from the list.

**Errors:**
| HTTP | Code                 | Condition          |
| ---- | -------------------- | ------------------ |
| 400  | DATE_REQUIRED        | Missing date       |
| 400  | DURATION_REQUIRED    | Missing duration   |
| 400  | NUMBER_OF_PEOPLE_REQUIRED | Missing numberOfPeople |
| 422  | INVALID_BOOKING_DATE | Date in the past   |
| 404  | SHOP_NOT_FOUND       | Shop not found     |

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

**Response (200):**
```json
{
  "success": true,
  "data": {
    "customerId": 5,
    "isEligible": true,
    "memberRank": "Silver",
    "visitCount": 3,
    "isBlocked": false
  }
}
```

If blocked:
```json
{
  "success": true,
  "data": {
    "customerId": 5,
    "isEligible": false,
    "memberRank": "Silver",
    "visitCount": 3,
    "isBlocked": true,
    "blockReason": "Customer on NG List"
  }
}
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
| customerId                 | No       | Admin use, skips phone lookup                                |
| shopId                     | Yes      |                                                              |
| bookingDate                | Yes      | YYYY-MM-DD                                                   |
| startTime                  | Yes      | HH:MM                                                        |
| duration                   | Yes      | Total minutes (main course + add-ons)                        |
| numberOfPeople             | Yes      | Must be > 0                                                  |
| services                   | Yes      | Array `{personIndex, courseId}`, main courses only           |
| addOns                     | No       | Array `{personIndex, courseId}`, addon courses only          |
| therapistPreferenceType    | No       | `no_preference` \| `specific` \| `gender`                    |
| therapistPreferenceValue   | No       | `specific` → therapist id (int); `gender` → `Male`/`Female`  |

> Therapist preference is sent as `therapistPreferenceType` / `therapistPreferenceValue` (not the
> legacy `therapistId` / `therapistGender` fields). For `specific`, `therapistPreferenceValue` is the
> therapist id; the system locks that exact therapist at confirm time.

**Business Rules:**
- If `phoneNumber` is new, auto-create customer
- Booking rejected if customer is on NG List
- Group (≥2) cannot assign a specific therapist (`specific` is ignored / must use `no_preference`)
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
| 400  | SERVICES_REQUIRED           | No services provided          |
| 400  | INVALID_COURSE_TYPE         | Course type mismatch          |
| 403  | CUSTOMER_BLOCKED            | Customer on NG List           |
| 404  | CUSTOMER_NOT_FOUND          | customerId not found          |
| 404  | SHOP_NOT_FOUND              | Shop not found                |
| 409  | TIME_SLOT_UNAVAILABLE       | Slot already taken            |
| 409  | THERAPIST_UNAVAILABLE       | Therapist not available       |
| 422  | SHOP_CLOSED                 | Shop closed at selected time  |
| 422  | THERAPIST_NOT_ALLOWED_GROUP | Therapist assigned to group   |

---

### GET /api/bookings

Retrieve bookings list with filters.

**Query Parameters:**
| Name       | Type   | Required | Description                              |
| ---------- | ------ | -------- | ---------------------------------------- |
| shopId     | int    | No       | Filter by shop                           |
| phone      | string | No       | Search by phone number                   |
| status     | string | No       | `Booked`, `CheckedIn`, `CheckedOut`, `Cancelled` |
| dateFrom   | string | No       | YYYY-MM-DD                               |
| dateTo     | string | No       | YYYY-MM-DD                               |
| page       | int    | No       | Default 1                                |
| size       | int    | No       | Default 20, max 100                      |

**Response (200):**
```json
{
  "success": true,
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
      "services": [{ "personIndex": 1, "courseId": 1, "courseName": "Thai Massage" }],
      "therapistId": 2,
      "therapistName": "Anna"
    }
  ],
  "pagination": { "page": 1, "size": 20, "total": 30, "totalPages": 2 }
}
```

---

### GET /api/bookings/{booking_id}

Retrieve full booking detail.

**Response (200):** Same as list item + `addOns` array + `customerId` + `memberRank`.

**Errors:** 404 BOOKING_NOT_FOUND

---

### PATCH /api/bookings/{booking_id}

Update booking. Accepts partial update for changeable fields.

**Request:**
```json
{
  "startTime": "11:00",
  "services": [{ "personIndex": 1, "courseId": 2 }],
  "therapistId": 3
}
```

**Business Rules:**
- Only `Booked` status can be modified
- Time/service changes trigger slot re-validation
- Phone number cannot be changed

**Response (200):**
```json
{ "success": true, "data": { "bookingId": 120, "status": "Booked" }, "message": "Booking updated." }
```

**Errors:**
| HTTP | Code                    | Condition                     |
| ---- | ----------------------- | ----------------------------- |
| 404  | BOOKING_NOT_FOUND       | Not found                     |
| 422  | INVALID_MODIFY_STATUS   | Only Booked can be modified   |
| 409  | TIME_SLOT_UNAVAILABLE   | New time conflicts            |

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

### GET /api/admin/shops/{shop_id}/therapist-shifts

Retrieve all shifts for a shop.

**Query Parameters:** `?therapistId=5&dayOfWeek=Monday`

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

**Validation:** therapistId required, dayOfWeek required (Monday-Sunday), startTime < endTime.

**Response (201):**
```json
{ "success": true, "data": { "shiftId": 20 }, "message": "Shift created." }
```

**Errors:** 404 THERAPIST_NOT_FOUND, 409 SHIFT_OVERLAP

---

### GET /api/admin/therapist-shifts/{shift_id}

Retrieve shift detail.

---

### PATCH /api/admin/therapist-shifts/{shift_id}

Update shift.

**Request:**
```json
{ "startTime": "09:00", "endTime": "18:00" }
```

**Errors:** 404 SHIFT_NOT_FOUND, 409 SHIFT_OVERLAP

---

### Customer Restrictions (NG List)

---

### GET /api/admin/customer-restrictions

Retrieve list of blocked customers.

**Query Parameters:** `?phone=01234&page=1&size=20`

**Response (200):**
```json
{
  "success": true,
  "data": [
    { "restrictionId": 1, "customerId": 10, "phoneNumber": "0111222333", "reason": "No-show 3 times", "blockedAt": "2026-06-01T10:00:00", "blockedBy": "admin" }
  ],
  "pagination": { "page": 1, "size": 20, "total": 5, "totalPages": 1 }
}
```

---

### POST /api/admin/customer-restrictions

Block a customer.

**Request:**
```json
{ "phoneNumber": "0111222333", "reason": "No-show 3 times" }
```

**Response (201):**
```json
{ "success": true, "data": { "restrictionId": 1 }, "message": "Customer blocked." }
```

**Errors:** 404 CUSTOMER_NOT_FOUND, 409 CUSTOMER_ALREADY_BLOCKED

---

### GET /api/admin/customer-restrictions/{restriction_id}

Retrieve restriction detail.

---

### PATCH /api/admin/customer-restrictions/{restriction_id}

Update restriction reason or unblock.

**Request:**
```json
{ "reason": "Resolved after payment", "isActive": false }
```

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
- `PATCH /api/bookings/{booking_id}/cancel` — Cancel (only Booked)
- `PATCH /api/bookings/{booking_id}/checkin` — Check-in (only Booked)
- `PATCH /api/bookings/{booking_id}/checkout` — Check-out (only CheckedIn)

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

GET    /api/admin/customer-restrictions
POST   /api/admin/customer-restrictions
GET    /api/admin/customer-restrictions/{restriction_id}
PATCH  /api/admin/customer-restrictions/{restriction_id}

GET    /api/admin/bookings
GET    /api/admin/bookings/{booking_id}
```

### Therapist
```
GET    /api/therapists/me/schedule
```
