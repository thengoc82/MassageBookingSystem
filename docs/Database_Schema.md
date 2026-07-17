# Database Schema

**Database:** SQLite (default, no setup required)

---

## Table: users

System users (admin, therapist login).

| Column    | Type         | Constraints              |
|-----------|--------------|--------------------------|
| id        | SERIAL       | PK                       |
| username  | VARCHAR(50)  | UNIQUE, NOT NULL         |
| password  | VARCHAR(255) | NOT NULL                 |
| role      | VARCHAR(20)  | NOT NULL (admin / therapist) |
| ref_id    | INTEGER      | FK → therapists.id (nullable) |
| is_active | BOOLEAN      | DEFAULT true             |
| created_at| TIMESTAMP    | DEFAULT NOW()            |

---

## Table: customers

| Column       | Type          | Constraints              |
|--------------|---------------|--------------------------|
| id           | SERIAL        | PK                       |
| phone_number | VARCHAR(20)   | UNIQUE, NOT NULL         |
| member_rank  | VARCHAR(20)   | NOT NULL DEFAULT 'Silver'|
| visit_count  | INTEGER       | NOT NULL DEFAULT 0       |
| is_blocked   | BOOLEAN       | NOT NULL DEFAULT false   |
| created_at   | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_customers_phone` on phone_number.

---

## Table: shops

| Column      | Type          | Constraints              |
|-------------|---------------|--------------------------|
| id          | SERIAL        | PK                       |
| name        | VARCHAR(100)  | NOT NULL                 |
| address     | VARCHAR(255)  | NOT NULL                 |
| phone_number| VARCHAR(20)   | UNIQUE, NOT NULL         |
| status      | VARCHAR(10)   | NOT NULL DEFAULT 'Open'  |
| open_time   | TIME          | NOT NULL                 |
| close_time  | TIME          | NOT NULL                 |
| created_at  | TIMESTAMP     | DEFAULT NOW()            |

---

## Table: courses

| Column      | Type          | Constraints              |
|-------------|---------------|--------------------------|
| id          | SERIAL        | PK                       |
| shop_id     | INTEGER       | FK → shops.id, NOT NULL  |
| name        | VARCHAR(100)  | NOT NULL                 |
| duration    | INTEGER       | NOT NULL (minutes)       |
| price       | INTEGER       | NOT NULL (VND)           |
| course_type | VARCHAR(10)   | NOT NULL CHECK IN ('main','addon') |
| status      | VARCHAR(10)   | NOT NULL DEFAULT 'active'|
| created_at  | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_courses_shop` on shop_id.

---

## Table: therapists

| Column       | Type          | Constraints              |
|--------------|---------------|--------------------------|
| id           | SERIAL        | PK                       |
| shop_id      | INTEGER       | FK → shops.id, NOT NULL  |
| name         | VARCHAR(100)  | NOT NULL                 |
| gender       | VARCHAR(10)   | NOT NULL CHECK IN ('Male','Female') |
| phone_number | VARCHAR(20)   | UNIQUE                   |
| status       | VARCHAR(10)   | NOT NULL DEFAULT 'active'|
| created_at   | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_therapists_shop` on shop_id.

---

## Table: therapist_shifts

| Column        | Type          | Constraints              |
|---------------|---------------|--------------------------|
| id            | SERIAL        | PK                       |
| therapist_id  | INTEGER       | FK → therapists.id, NOT NULL |
| day_of_week   | VARCHAR(10)   | NOT NULL CHECK IN ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday') |
| start_time    | TIME          | NOT NULL                 |
| end_time      | TIME          | NOT NULL, CHECK (end_time > start_time) |
| effective_from| DATE          | NOT NULL                 |
| created_at    | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_shifts_therapist` on therapist_id, `ix_shifts_day` on day_of_week.

**Constraint:** No overlapping shifts for same therapist + day_of_week + effective_from.

---

## Table: time_slots  ⚠️ DEPRECATED — NOT USED

Created in the initial migration but **no active model exists** (`app/models/time_slot.py.deprecated`).
Availability is computed on demand from `therapist_shifts` + `bookings` (see ADR 0002 / `docs/CONTEXT.md`
"Terms NOT in Use"). Do not rely on this table.

| Column      | Type          | Constraints              |
|-------------|---------------|--------------------------|
| id          | SERIAL        | PK                       |
| shop_id     | INTEGER       | FK → shops.id, NOT NULL  |
| date        | DATE          | NOT NULL                 |
| start_time  | TIME          | NOT NULL                 |
| end_time    | TIME          | NOT NULL                 |
| therapist_id| INTEGER       | FK → therapists.id (nullable) |
| is_available| BOOLEAN       | NOT NULL DEFAULT true    |
| created_at  | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_slots_shop_date` on (shop_id, date), `ix_slots_therapist_date` on (therapist_id, date).

---

## Table: bookings

| Column          | Type          | Constraints              |
|-----------------|---------------|--------------------------|
| id              | SERIAL        | PK                       |
| booking_code    | VARCHAR(20)   | UNIQUE, NOT NULL         |
| shop_id         | INTEGER       | FK → shops.id, NOT NULL  |
| customer_id     | INTEGER       | FK → customers.id, NOT NULL |
| phone_number    | VARCHAR(20)   | NOT NULL                 |
| booking_date    | DATE          | NOT NULL                 |
| start_time      | TIME          | NOT NULL                 |
| end_time        | TIME          | NOT NULL                 |
| number_of_people| INTEGER       | NOT NULL, CHECK (> 0)    |
| therapist_id    | INTEGER       | FK → therapists.id (nullable) |
| therapist_gender| VARCHAR(10)   | (nullable)               |
| status          | VARCHAR(20)   | NOT NULL DEFAULT 'Booked' CHECK IN ('Booked','CheckedIn','CheckedOut','Cancelled') |
| internal_notes  | TEXT          | (nullable)               |
| created_by      | VARCHAR(20)   | DEFAULT 'customer'       |
| created_at      | TIMESTAMP     | DEFAULT NOW()            |
| updated_at      | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_bookings_code` on booking_code, `ix_bookings_customer` on customer_id, `ix_bookings_shop_date` on (shop_id, booking_date), `ix_bookings_status` on status, `ix_bookings_phone` on phone_number.

---

## Table: booking_services

Each row = one main course for one person in a booking.

| Column      | Type    | Constraints                       |
|-------------|---------|-----------------------------------|
| id          | SERIAL  | PK                                |
| booking_id  | INTEGER | FK → bookings.id, NOT NULL        |
| person_index| INTEGER | NOT NULL, CHECK (> 0)             |
| course_id   | INTEGER | FK → courses.id, NOT NULL         |

**Indexes:** `ix_booking_services_booking` on booking_id.

**Constraint:** course_id must reference a course with course_type = 'main'.

---

## Table: booking_addons

Each row = one add-on for one person in a booking.

| Column      | Type    | Constraints                       |
|-------------|---------|-----------------------------------|
| id          | SERIAL  | PK                                |
| booking_id  | INTEGER | FK → bookings.id, NOT NULL        |
| person_index| INTEGER | NOT NULL, CHECK (> 0)             |
| course_id   | INTEGER | FK → courses.id, NOT NULL         |

**Indexes:** `ix_booking_addons_booking` on booking_id.

**Constraint:** course_id must reference a course with course_type = 'addon'.

---

## Table: customer_restrictions

| Column        | Type          | Constraints              |
|---------------|---------------|--------------------------|
| id            | SERIAL        | PK                       |
| customer_id   | INTEGER       | FK → customers.id, NOT NULL |
| phone_number  | VARCHAR(20)   | NOT NULL                 |
| reason        | TEXT          | NOT NULL                 |
| is_active     | BOOLEAN       | NOT NULL DEFAULT true    |
| blocked_by    | VARCHAR(100)  | NOT NULL                 |
| blocked_at    | TIMESTAMP     | DEFAULT NOW()            |
| updated_at    | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_restrictions_customer` on customer_id, `ix_restrictions_phone` on phone_number.

---

## Table: reservations  ⚠️ REMOVED — NOT USED

Present in the initial migration for an abandoned two-phase "reserve → confirm" flow, but **removed
by design** (see `docs/adr/0002-optimistic-availability.md`). No model, service, or blueprint
references it. Availability is optimistic — validated atomically at booking creation.

| Column           | Type          | Constraints              |
|------------------|---------------|--------------------------|
| id               | SERIAL        | PK                       |
| booking_id       | INTEGER       | FK → bookings.id, UNIQUE, NOT NULL |
| is_reserved      | BOOLEAN       | NOT NULL DEFAULT true    |
| reserved_until   | TIMESTAMP     | NOT NULL                 |
| created_at       | TIMESTAMP     | DEFAULT NOW()            |

**Indexes:** `ix_reservations_booking` on booking_id, `ix_reservations_expiry` on reserved_until.

---

## Entity Relationship Diagram (Simplified)

```
customers ──< bookings ──< booking_services
  │            │            booking_addons
  │            │
  └── customer_restrictions

shops ──< courses
  │  ──< therapists ──< therapist_shifts
  │  ──< bookings

users (admin/therapist login)
```

> Note: `time_slots` and `reservations` tables exist only in the initial migration and are unused
> (deprecated / removed by ADR 0002). Availability is derived, not stored.

---

## Notes

- All monetary values stored as INTEGER (VND, no decimals).
- Timestamps stored as UTC `DateTime` (SQLite has no native timezone).
- Soft deletes preferred: use `status` or `is_active` flags instead of DELETE.
- Availability is computed from `therapist_shifts` + `bookings`, never read from `time_slots`.
