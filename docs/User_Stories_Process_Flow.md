# Booking System — Use Cases, User Stories, Process Flows

---

## UC-01: Create Booking

**Goal:** Customer successfully books a massage and receives a booking code.

### User Stories

#### US-01: Browse Shops

**As a** Customer  
**I want** to view all active shops  
**So that** I can choose which branch to book at.

---

#### US-02: Select Date

**As a** Customer  
**I want** to pick a service date  
**So that** the system can find available slots for that day.

---

#### US-03: Select Number of Guests

**As a** Customer  
**I want** to enter how many people will receive massage  
**So that** the system knows if this is an individual or group booking.

---

#### US-04: Select Duration

**As a** Customer  
**I want** to choose the total duration  
**So that** the system can calculate which time slots fit.

---

#### US-05: Select Services

**As a** Customer  
**I want** to pick a main course and optional add-ons for each guest  
**So that** the system knows exactly which services I want.

---

#### US-06: View Available Slots

**As a** Customer  
**I want** to see available time slots  
**So that** I can pick a time that works for me.

---

#### US-07: Select Start Time

**As a** Customer  
**I want** to pick a start time from available slots  
**So that** my booking is scheduled correctly.

---

#### US-08: Select Therapist (Optional)

**As a** Customer  
**I want** to request a specific therapist or gender preference  
**So that** I can be served by my preferred staff (only for 1-person bookings).

---

#### US-09: Enter Phone Number

**As a** Customer  
**I want** to enter my phone number  
**So that** the system can look up my profile, check my membership tier, and verify I am not on the NG List.

---

#### US-10: Check Eligibility

**As a** Customer  
**I want** the system to check my eligibility before proceeding  
**So that** I know immediately if I can book.

---

#### US-11: Review & Confirm

**As a** Customer  
**I want** to review all booking details before confirming  
**So that** I can ensure everything is correct.

---

#### US-12: Receive Booking Code

**As a** Customer  
**I want** to receive a booking code after successful creation  
**So that** I can use it when I arrive at the shop.

---

### Process Flow

| Step | Customer | System |
|------|----------|--------|
| 1 | Select shop | |
| 2 | Select date | |
| 3 | Select number of guests | |
| 4 | Select duration | |
| 5 | Select main courses per person | |
| 6 | Select add-ons (optional) | |
| 7 | | Calculate and return available slots (optimistic) |
| 8 | Select start time | |
| 9 | Select therapist or gender (optional) | |
| 10 | Enter phone number | Look up or auto-create customer |
| 11 | | Check membership tier |
| 12 | | Check NG List → reject if blocked |
| 13 | Review full booking summary | |
| 14 | Confirm booking | |
| 15 | | Re-validate slot availability (atomic, row lock) |
| 16 | | Re-validate therapist availability |
| 17 | | Check shop is open |
| 18 | | Create booking |
| 19 | | System generates booking code |
| 20 | Receive booking code | |

> Availability is **optimistic** — shown at query time, validated atomically at confirm. There is no
> reservation hold (see `docs/adr/0002-optimistic-availability.md`).

---

## UC-02: Modify Booking

**Goal:** Customer changes the time, services, or therapist of an existing booking.

### User Stories

#### US-13: Modify Booking Details

**As a** Customer  
**I want** to change the time, services, or therapist of my booking  
**So that** I can adjust my plan without cancelling.

---

#### US-14: Re-validate on Change

**As a** Customer  
**I want** the system to check availability again when I change time or services  
**So that** I know the new arrangement is valid.

---

### Process Flow

| Step | Customer | System |
|------|----------|--------|
| 1 | Open existing booking | |
| 2 | Change fields (time, services, therapist) | |
| 3 | | Re-validate slot availability |
| 4 | | Re-validate therapist availability |
| 5 | | Check shop hours |
| 6 | Confirm changes | |
| 7 | | Update booking (status stays Booked) |
| 8 | Receive confirmation | |

---

## UC-03: Cancel Booking

**Goal:** Customer cancels a booking before the service starts.

### User Stories

#### US-15: Cancel Booking

**As a** Customer  
**I want** to cancel my booking  
**So that** I free up the slot and am not charged.

---

### Process Flow

| Step | Customer | System |
|------|----------|--------|
| 1 | Request cancellation | |
| 2 | | Validate status is Booked |
| 3 | | Release slot + therapist |
| 4 | | Mark booking as Cancelled |
| 5 | Receive cancellation confirmation | |

---

## UC-04: Check-in / Check-out

**Goal:** Admin manages booking status when customer arrives and when service ends.

### User Stories

#### US-16: Check-in Customer

**As an** Admin  
**I want** to mark a booking as checked in when the customer arrives  
**So that** the system tracks attendance.

---

#### US-17: Check-out Customer

**As an** Admin  
**I want** to mark a booking as checked out when the service is complete  
**So that** the system records completed services for reporting.

---

### Process Flow

| Step | Admin | System |
|------|-------|--------|
| 1 | Find booking by code or phone | |
| 2 | Mark as Checked In | Validate status is Booked → update to CheckedIn |
| 3 | After service ends | |
| 4 | Mark as Checked Out | Validate status is CheckedIn → update to CheckedOut |

---

## UC-05: Customer Blocking (NG List)

**Goal:** Admin blocks problematic customers from booking.

### User Stories

#### US-18: Block Customer

**As an** Admin  
**I want** to add a customer to the NG List with a reason  
**So that** they cannot create new bookings.

---

#### US-19: Unblock Customer

**As an** Admin  
**I want** to remove a customer from the NG List  
**So that** they can book again.

---

### Process Flow

| Step | Admin | System |
|------|-------|--------|
| 1 | Search customer by phone | |
| 2 | Add restriction with reason | Save to Customer Restriction |
| 3 | | Customer is blocked from future bookings |
| 4 | Optionally unblock later | Deactivate restriction |

---

## UC-06: View Therapist Schedule

**Goal:** Therapist views their upcoming bookings.

### User Stories

#### US-20: View My Schedule

**As a** Therapist  
**I want** to see my shift schedule and assigned bookings for a date range  
**So that** I know when and where I am working.

---

## Endpoint Mapping

### UC-01 Create Booking

| Step | Endpoint |
|------|----------|
| 1-2 | `GET /api/shops` |
| 3-6 | `GET /api/shops/{id}/courses?type=main\|addon` |
| 7 | `GET /api/shops/{id}/available-slots?date=&duration=&numberOfPeople=&courseIds=&gender=` |
| 8-9 | `GET /api/shops/{id}/available-therapists?date=&startTime=&gender=` |
| 10-12 | `POST /api/booking-eligibility-checks` |
| 13-20 | `POST /api/bookings` |

### UC-02 Modify Booking

| Step | Endpoint |
|------|----------|
| 1-8 | `PATCH /api/bookings/{booking_id}` |

### UC-03 Cancel Booking

| Step | Endpoint |
|------|----------|
| 1-5 | `PATCH /api/bookings/{booking_id}/cancel` |

### UC-04 Check-in / Check-out

| Step | Endpoint |
|------|----------|
| 1-2 | `PATCH /api/bookings/{booking_id}/checkin` |
| 3-4 | `PATCH /api/bookings/{booking_id}/checkout` |

### UC-05 Customer Blocking

| Step | Endpoint |
|------|----------|
| 1-3 | `POST /api/admin/customer-restrictions` |
| 4 | `PATCH /api/admin/customer-restrictions/{id}` |

### UC-06 View Schedule

| Step | Endpoint |
|------|----------|
| 1 | `GET /api/therapists/me/schedule?dateFrom=&dateTo=` |

