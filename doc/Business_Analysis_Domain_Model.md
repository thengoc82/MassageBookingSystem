# Booking Management System

## 1. Business Entities

### Customer

Person who books massage services.

### Therapist

Staff who performs massage services for customers.

### Admin

System operator who manages shops, staff, services, and bookings.

### Booking

A service reservation made by a customer.

### Shop

A branch location that provides massage services.

### Course (Service)

A specific massage service offered at a shop. Can be a main course or an add-on.

### Time Slot

An available time window for a service at a shop, optionally linked to a therapist.

### Therapist Shift

A recurring weekly shift assigned to a therapist (e.g. Monday 08:00-17:00).

### Customer Restriction (NG List)

A block placed on a customer preventing them from making bookings.

### Reservation

A time-limited hold on a booking slot while the customer is in the booking flow.

---

## 2. Entity Attributes

### Customer

| Attribute     | Description              |
|---------------|--------------------------|
| customerId    | Unique ID                |
| phoneNumber   | Phone number (unique)    |
| memberRank    | Silver / Gold / Platinum |
| visitCount    | Number of visits         |
| isBlocked     | NG List flag             |
| createdAt     | Account creation date    |

### Therapist

| Attribute     | Description                  |
|---------------|------------------------------|
| therapistId   | Unique ID                    |
| shopId        | Assigned shop                |
| name          | Full name                    |
| gender        | Male / Female                |
| phoneNumber   | Contact number               |
| status        | Active / Inactive            |

### Therapist Shift

| Attribute     | Description                         |
|---------------|-------------------------------------|
| shiftId       | Unique ID                           |
| therapistId   | Linked therapist                    |
| dayOfWeek     | Monday - Sunday                     |
| startTime     | Shift start (HH:MM)                 |
| endTime       | Shift end (HH:MM)                   |
| effectiveFrom | Date from which shift is active     |

### Shop

| Attribute     | Description                  |
|---------------|------------------------------|
| shopId        | Unique ID                    |
| shopName      | Branch name                  |
| address       | Physical address             |
| phoneNumber   | Contact number               |
| status        | Open / Closed                |
| openTime      | Daily opening time (HH:MM)   |
| closeTime     | Daily closing time (HH:MM)   |

### Course

| Attribute     | Description                  |
|---------------|------------------------------|
| courseId      | Unique ID                    |
| shopId        | Owning shop                  |
| courseName    | Service name                 |
| duration      | Minutes                      |
| price         | Cost (VND)                   |
| courseType    | `main` or `addon`            |
| status        | Active / Inactive            |

### Booking

| Attribute         | Description                                   |
|-------------------|-----------------------------------------------|
| bookingId         | Unique ID                                     |
| bookingCode       | POS-generated unique code                     |
| shopId            | Branch                                        |
| phoneNumber       | Customer phone                                |
| customerId        | Linked customer                               |
| bookingDate       | YYYY-MM-DD                                    |
| startTime         | HH:MM                                         |
| numberOfPeople    | Guest count                                   |
| services          | Array `{personIndex, courseId}` (main courses)|
| addOns            | Array `{personIndex, courseId}` (add-ons)     |
| therapistId       | Assigned therapist (optional, 1-person only)  |
| therapistGender   | Preferred gender (optional, 1-person only)    |
| status            | Booked / CheckedIn / CheckedOut / Cancelled   |
| internalNotes     | Admin notes                                   |

### Time Slot

| Attribute     | Description                       |
|---------------|-----------------------------------|
| slotId        | Unique ID                         |
| shopId        | Branch                            |
| date          | YYYY-MM-DD                        |
| startTime     | HH:MM                             |
| endTime       | HH:MM                             |
| therapistId   | Assigned therapist (nullable)     |
| isAvailable   | Whether the slot can be booked    |

### Customer Restriction

| Attribute     | Description                       |
|---------------|-----------------------------------|
| restrictionId | Unique ID                         |
| customerId    | Blocked customer                  |
| phoneNumber   | Customer phone                    |
| reason        | Block reason                      |
| blockedAt     | Timestamp                         |
| blockedBy     | Admin who blocked                 |
| isActive      | Whether restriction is active     |

### Reservation

| Attribute        | Description                              |
|------------------|------------------------------------------|
| bookingId        | Linked booking                           |
| isReserved       | Whether slot is on hold                  |
| reservedUntil    | Timestamp when hold expires              |
| remainingSeconds | Seconds left before hold releases        |

---

## 3. Business Rules

### Customer

- Customer is identified by phone number. If new, auto-create on booking.
- Blocked customers (NG List) cannot create bookings.
- Phone number cannot be changed after booking is created.

### Therapist Assignment

- **1-person booking:** Can specify `therapistId` or `therapistGender`.
- **Group (2+):** Cannot assign a therapist. System auto-assigns.
- Therapist must belong to the same shop as the booking.
- Therapist must be within their active shift at the booking time.
- Therapist must be available (no overlapping booking).

### Booking Modification

- Only `Booked` status bookings can be modified.
- Changing time or services triggers slot re-validation.
- Changing therapist triggers therapist availability re-check.

### Booking Status Transitions

```
Booked ──► CheckedIn ──► CheckedOut
  │
  └──► Cancelled
```

- `Booked` → `Cancelled`: Customer cancels. Only for Booked status.
- `Booked` → `CheckedIn`: Customer arrives. Only from Booked.
- `CheckedIn` → `CheckedOut`: Service complete. Only from CheckedIn.
- `Cancelled` and `CheckedOut` are terminal states.

### Shifts

- A therapist can have multiple shifts across the week.
- Shifts cannot overlap for the same therapist.
- Shift changes require re-validation of future bookings.

### Reservation Hold

- When a customer starts the booking flow, a time-limited hold is placed on the slot.
- Hold expires after a configurable period (default 5 minutes).
- Other customers cannot book a held slot.

### General Constraints

- Each person in a booking gets exactly 1 main course + 0..N add-ons.
- Booking code is unique system-wide, generated by POS.
- Slot must be available before booking is confirmed.
- Course type must match: `main` for services, `addon` for add-ons.
- Shop must be open at the selected time.

---

## 4. Relationships

| Entity A            | Entity B             | Cardinality |
|---------------------|----------------------|-------------|
| Customer            | Booking              | 1 : N       |
| Shop                | Booking              | 1 : N       |
| Shop                | Therapist            | 1 : N       |
| Shop                | Course               | 1 : N       |
| Shop                | Time Slot            | 1 : N       |
| Therapist           | Booking              | 1 : N       |
| Therapist           | Therapist Shift      | 1 : N       |
| Therapist           | Time Slot            | 1 : N       |
| Course              | Time Slot            | 1 : N       |
| Customer            | Customer Restriction | 1 : N       |

### ER Summary

```
Customer (1) -------- (N) Booking
Customer (1) -------- (N) Customer Restriction
Shop     (1) -------- (N) Booking
Shop     (1) -------- (N) Therapist
Shop     (1) -------- (N) Course
Shop     (1) -------- (N) Time Slot

Therapist(1) -------- (N) Booking
Therapist(1) -------- (N) Therapist Shift
Therapist(1) -------- (N) Time Slot

Course   (1) -------- (N) Time Slot
```

---

## 5. Booking Lifecycle

### Full Booking Flow

1. Customer browses shops
2. Customer selects date
3. Customer selects number of guests
4. Customer selects duration
5. Customer selects course + add-ons
6. System returns available slots
7. Customer selects start time
8. Customer optionally selects therapist or gender
9. Customer enters phone number
10. System checks eligibility (not on NG List)
11. System places reservation hold on slot
12. Customer confirms booking
13. System re-validates slot + therapist availability
14. POS generates booking code
15. Customer receives booking code

### Post-Booking Flow

- Customer arrives → Admin checks in (Booked → CheckedIn)
- Service complete → Admin checks out (CheckedIn → CheckedOut)
- Customer cancels → Booking cancelled (Booked → Cancelled)
- Customer modifies → Booking re-validated (stays Booked)

---

## 6. Permissions

### Customer (Public)

| Permission                        | Endpoint                                            |
|-----------------------------------|-----------------------------------------------------|
| List shops                        | `GET /api/shops`                                    |
| View shop detail                  | `GET /api/shops/{shop_id}`                          |
| List courses                      | `GET /api/shops/{shop_id}/courses`                  |
| View available slots              | `GET /api/shops/{shop_id}/available-slots`          |
| View available therapists         | `GET /api/shops/{shop_id}/available-therapists`     |
| Check booking eligibility         | `POST /api/booking-eligibility-checks`              |
| Create booking                    | `POST /api/bookings`                                |
| List own bookings                 | `GET /api/bookings`                                 |
| View booking detail               | `GET /api/bookings/{booking_id}`                    |
| Modify booking                    | `PATCH /api/bookings/{booking_id}`                  |
| View reservation hold             | `GET /api/bookings/{booking_id}/reservations`       |

### Admin

| Permission                        | Endpoint                                            |
|-----------------------------------|-----------------------------------------------------|
| Full CRUD shops                   | `GET/POST /api/admin/shops`, `GET/PATCH /{id}`     |
| Full CRUD courses                 | `GET/POST /api/admin/shops/{id}/courses`, `GET/PATCH /api/admin/courses/{id}` |
| Full CRUD therapists              | `GET/POST /api/admin/shops/{id}/therapists`, `GET/PATCH /api/admin/therapists/{id}` |
| Full CRUD therapist shifts        | `GET /api/admin/shops/{id}/therapist-shifts`, `POST/GET/PATCH /api/admin/therapist-shifts/{id}` |
| Full CRUD customer restrictions   | `GET/POST /api/admin/customer-restrictions`, `GET/PATCH /{id}` |
| View all bookings                 | `GET /api/admin/bookings`                           |
| View any booking detail           | `GET /api/admin/bookings/{booking_id}`              |

### Therapist

| Permission                        | Endpoint                                            |
|-----------------------------------|-----------------------------------------------------|
| View own schedule                 | `GET /api/therapists/me/schedule`                   |

---

## 7. Key Constraints

1. A booking can have multiple guests.
2. Each guest gets 1 main course + 0..N add-ons.
3. Only 1-person bookings can specify therapist or gender.
4. Therapist must belong to the same shop as the booking.
5. Therapist must be on shift at the booking time.
6. Slot must be available and not held by another reservation.
7. Booking code is unique system-wide.
8. Course type (`main` / `addon`) must match the context.
9. Shop must be open during the booking time window.
10. Bookings can only be modified in `Booked` status.
11. Cancelled or Completed bookings cannot be modified.
12. Reservation holds expire after a configurable timeout.