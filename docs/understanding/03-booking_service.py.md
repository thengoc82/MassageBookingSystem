# Step 3: Explain `spa-booking-api/app/services/booking_service.py`

This document details the purpose, design, and implementation of `BookingService`, which is the logical core of the entire booking system.

## Purpose of the File

This file acts as the **Service Layer** for all booking-related operations. It encapsulates the complex business logic required to create, manage, and query bookings. Its primary reason for existence is to separate the business rules from the web layer (the blueprints). When a request comes in to create a booking, the blueprint's only job is to pass the data to `BookingService.create()`. All the hard work happens here.

## Important Classes and Functions

The file consists of a single class, `BookingService`, which contains only static methods.

### `create(data)`

This is the most critical and complex method in the entire service. It orchestrates the entire booking creation process.

*   **Why it exists**: To provide a single, transactional entry point for creating a new booking.
*   **Who calls it**: `spa-booking-api/app/blueprints/bookings/routes.py` in the `create_booking()` endpoint.
*   **What it returns**: A `Booking` model object on success.
*   **How it fits into the architecture**: This is the engine of the booking system. It's where the AI's request to "book a massage" becomes a reality in the database.

**Execution Flow of `create()`:**

1.  **Validation**: Checks for required data like `phoneNumber`, `shopId`, `bookingDate`, etc.
2.  **Customer Eligibility**: Calls `CustomerService.check_eligibility()` to ensure the customer is not on the "NG List" (blocked).
3.  **Therapist Assignment Logic**: This is the heart of the method. It's a complex conditional block to find and lock a therapist.
    *   **If single person, specific therapist requested**: It tries to find the therapist by ID and lock that database row using `with_for_update(skip_locked=True)`. If the row is already locked by another transaction, it fails immediately (`SLOT_UNAVAILABLE`), preventing waits and deadlocks. It then double-checks if the locked therapist is actually free for the requested timeslot using `_is_therapist_free()`.
    *   **If single person, gender preference**: It uses `_lock_available_therapist_by_gender()` to find the least-busy therapist of that gender and locks them.
    *   **If single person, no preference**: It uses `_lock_least_loaded_therapist()` to find and lock the therapist with the minimum total booked time for that day.
    *   **If multi-person booking**: It gets a list of all available therapists and uses `random.sample()` to pick the required number. This is a key detail: it's **random**, not least-loaded, for groups.
4.  **Data Creation**:
    *   Finds or creates a `Customer` record.
    *   Generates a unique `booking_code`.
    *   Creates the primary `Booking` object.
    *   Creates `BookingTherapist` records to link each person in the booking to their assigned therapist.
    *   Creates `BookingService` and `BookingAddon` records for the selected courses.
5.  **POS Integration**: Makes a (currently mocked) call to `_call_pos_api()`.
6.  **Transaction Commit**: If everything succeeds, it commits the transaction to the database. If any step fails (e.g., `BusinessRuleViolation`), it rolls the entire transaction back, ensuring data integrity.

### `_lock_least_loaded_therapist()` & `_lock_available_therapist_by_gender()`

*   **Why they exist**: To implement the core concurrency-safe therapist selection logic.
*   **How they work**: They execute a complex SQL query that joins `Therapist` and `Booking` tables, calculates the total `workload` for each therapist on a given day, and orders them by least workload.
*   **Design Decision**: The use of `with_for_update(skip_locked=True)` is a critical design decision. This is an **optimistic locking** strategy. It assumes the therapist is available and tries to lock them. If another booking request is currently holding the lock, this query doesn't wait; it immediately skips the locked row and moves on. This makes the API responsive and avoids deadlocks, at the cost of potentially telling a user a slot is unavailable if it's merely being booked by someone else at that exact moment.

### `_is_therapist_free(therapist_id, date, start_time, end_time)`

*   **Why it exists**: To provide the final, definitive check for a therapist's availability, preventing double bookings.
*   **How it works**: It runs a query to count any `Booking` or `BookingTherapist` records that overlap with the requested time slot for that specific therapist. An overlap is defined as `(Booking.start_time < requested_end_time AND Booking.end_time > requested_start_time)`.
*   **Common Pitfall**: A maintainer might forget that this function needs to check both the `therapist_id` on the main `Booking` table (for single-person bookings) and the `BookingTherapist` table (for multi-person bookings). The current implementation correctly checks both.

### State Change Methods (`cancel`, `checkin`, `checkout`)

*   **Why they exist**: To manage the lifecycle of a booking.
*   **How they work**: They are simple methods that load a booking, check if it's in the correct state for the requested action (e.g., you can only cancel a `Booked` booking), and then update its `status`.

## Common Bugs & Surprises

*   **Concurrency is Hard**: The biggest source of bugs in a system like this is always concurrency. A developer unfamiliar with `with_for_update` or transactional logic could easily introduce a race condition that leads to double-bookings.
*   **Random Assignment for Groups**: The fact that multi-person bookings use random therapist assignment, while single-person bookings use a "least-loaded" strategy, is a surprising inconsistency. This might be a deliberate business decision or an oversight.
*   **Mocked POS API**: The `_call_pos_api` function currently does nothing but return success. In a real-world scenario, this would be a major point of failure. If the POS system is down, the booking might be created in this system but not in the POS, leading to data inconsistency. The error handling for this is critical.
*   **Timezone Ambiguity**: The code uses a mix of `date`, `time`, and `datetime` objects. While the booking code generation uses UTC, other parts like `datetime.strptime` do not specify a timezone. This could lead to subtle off-by-one errors if different components of the system run in different timezones.

---

This service is the most important file for understanding the core business logic of the application. Any changes here have significant consequences for the entire system.
