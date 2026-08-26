
# `spa-booking-api/app/services/booking_service.py`

## 1. Purpose

This file contains the `BookingService` class, which encapsulates all the core business logic related to bookings. It acts as the "service layer" that sits between the web controllers (routes) and the database models. Its responsibilities include validating booking data, checking business rules (like customer eligibility), handling the complex logic of therapist assignment, creating and updating database records within a transaction, and querying for booking information.

## 2. Where it fits

This service is called by the booking-related API route handlers. It is the brain of the booking operations.

```text
`bookings/routes.py` (Controller)
    ↓
Receives HTTP request, calls `BookingService.create(data)`
    ↓
This file (`BookingService`)
    ↓
1. Validates data
2. Calls `CustomerService`
3. Queries `Therapist`, `Booking`, `TherapistShift` models
4. Performs complex assignment logic
5. Creates new `Booking` model instances
6. Commits changes to the database via the `db` extension
    ↓
Returns result to the Controller
```

## 3. Inputs

*   **`data` dictionary**: The `create` and `update` methods receive a dictionary of data that originates from the JSON body of an API request. This contains all the user-provided information for the booking.
*   **`filters` dictionary**: The `get_bookings` method receives a dictionary of filter criteria from the controller.
*   **`booking_id`**: Most methods (`get_booking`, `update`, `cancel`) take a `booking_id` to identify the specific booking to operate on.

## 4. Outputs

*   **SQLAlchemy Model Instances**: The methods often return instances of the `Booking` model (or lists of them) to the controller layer.
*   **Dictionaries**: The `get_bookings` method returns a dictionary containing the list of results and pagination metadata.
*   **Exceptions**: A very important output is the raising of custom exceptions (`ValidationError`, `BusinessRuleViolation`, `ResourceNotFound`) when an operation cannot be completed. These exceptions are caught by the global error handlers to produce a clean API error response.

## 5. Important functions/classes

```text
class BookingService
    ↓
Purpose: A static class that groups all booking-related business logic methods together. Using a class with only static methods is a way to namespace these functions without needing to manage an instance of the class.
```

```text
create(data)
    ↓
Purpose: To handle the entire complex process of creating a new booking. This is the most critical method in the service.
    ↓
Input: A dictionary `data` with all booking information.
    ↓
What it does:
    1.  **Validation**: Checks for the presence of required fields like `phoneNumber`, `shopId`, etc.
    2.  **Eligibility Check**: Calls `CustomerService.check_eligibility()` to ensure the customer is not on a blocklist.
    3.  **Therapist Assignment**: This is the most complex part. It contains different logic paths based on `numberOfPeople` and `therapistPreferenceType`:
        *   **Specific Therapist**: Tries to lock the requested therapist's database row (`WITH FOR UPDATE`) and verifies their availability.
        *   **Gender Preference**: Finds and locks the least busy available therapist of the specified gender.
        *   **No Preference**: Finds and locks the overall least loaded therapist (`_lock_least_loaded_therapist`).
        *   **Group Booking**: Randomly selects the required number of available therapists.
    4.  **Customer Handling**: Finds the customer by phone number or creates a new one via `CustomerService`.
    5.  **Database Transaction**: It wraps the database operations. It creates the `Booking`, `BookingTherapist`, `BookingService`, and `BookingAddon` records and adds them to the session.
    6.  **POS Integration**: Makes a (currently mocked) call to an external Point-of-Sale API.
    7.  **Commit/Rollback**: If all steps are successful, it calls `db.session.commit()`. If any exception occurs (including a database deadlock or a business rule violation), it calls `db.session.rollback()` to undo all changes and re-raises the exception.
    ↓
Output: The newly created `Booking` SQLAlchemy model instance.
```

```text
_lock_least_loaded_therapist(shop_id, date, start_time, end_time)
    ↓
Purpose: A helper method to find the therapist with the minimum total booked duration for the day, and then attempt to acquire a database lock on them to prevent race conditions.
    ↓
Input: Shop, date, and time slot information.
    ↓
What it does:
    1.  Builds a complex SQL subquery to calculate the total workload (in seconds) for each active therapist at the shop on the given day.
    2.  Joins this back to the `Therapist` table and orders by workload to find the least busy therapist.
    3.  Within a nested transaction (`begin_nested`), it attempts to re-query for that specific therapist using `with_for_update(skip_locked=True)`. This is a crucial step for handling concurrency: if another request has already locked that therapist, this query will not wait and will immediately return `None`.
    4.  Finally, it double-checks if the (now locked) therapist is actually free for the specific time slot.
    ↓
Output: A locked `Therapist` model instance, or `None` if no suitable therapist could be found or locked.
```

## 6. Execution flow

The execution flow of the `create` method is the most representative:

1.  Input data is validated. An exception is thrown if data is missing.
2.  Customer eligibility is checked. A `BusinessRuleViolation` is thrown if the customer is blocked.
3.  The therapist assignment logic block is entered.
4.  Based on preferences, a helper like `_lock_least_loaded_therapist` is called.
5.  This helper executes a sophisticated SQL query to find and then lock a candidate therapist row in the database.
6.  If a therapist is successfully locked, the `create` method proceeds. If not, it throws a `BusinessRuleViolation('SLOT_UNAVAILABLE')`.
7.  A `Booking` object and its related child objects (`BookingTherapist`, etc.) are created in memory.
8.  The objects are added to the SQLAlchemy session via `db.session.add()`.
9.  The mocked POS API is called.
10. `db.session.commit()` is called. This flushes all the changes to the database and releases the row-level lock acquired earlier.
11. The final `Booking` object is returned.
12. If any step above fails, the `except` block catches the error, calls `db.session.rollback()` to discard all changes, and re-throws the exception.

## 7. Dependencies

```text
db (from `app.extensions`)
    ↓
    The SQLAlchemy instance. It is used extensively for all database operations: querying (`db.session.query`), creating records (`db.session.add`), committing transactions (`db.session.commit`), and rolling back (`db.session.rollback`).

Models (from `app.models.*`)
    ↓
    The SQLAlchemy model classes (`Booking`, `Therapist`, etc.) are used to query the database and instantiate new records.

CustomerService (from `app.services.customer_service`)
    ↓
    Another service layer class, used to handle customer-specific logic like checking eligibility and finding/creating customer records.

Custom Errors (from `app.utils.errors`)
    ↓
    `ValidationError`, `BusinessRuleViolation`, `ResourceNotFound` are custom exception classes used to signal specific types of failures to the controller and global error handlers.
```

## 8. Relationship with other files

```text
This file (app/services/booking_service.py)
 ├── is called by → app/blueprints/bookings/routes.py
 ├── uses → app/services/customer_service.py
 ├── manipulates models from → app/models/*
 └── uses the database session from → app.extensions
```

## 9. Important state/data

This service is stateless itself, but it is deeply involved with the state of the database.

*   **Database Transaction**: The most important state it manages is the database transaction. The `try...except...finally` block in the `create` method carefully controls the lifecycle of the transaction to ensure data integrity (either all changes are saved, or none are).
*   **Row-Level Locks**: The use of `with_for_update(skip_locked=True)` is a critical data-related concept for handling concurrent requests trying to book the same therapist at the same time.

## 10. What I should understand

1.  **This is the "Fat Service" Layer:** This file is where the vast majority of the application's business logic resides. The controllers are thin, and the models are just data structures; the service layer is where the thinking happens.
2.  **Concurrency Handling is Critical:** The logic for therapist assignment is not just about finding a free therapist; it's about finding and *locking* them to prevent race conditions where two customers book the same slot simultaneously. The use of `with_for_update` is the key mechanism for this.
3.  **Transactional Integrity is Enforced:** The `create` method is wrapped in a `try/except/raise` block that ensures the database is never left in a partially complete state. This is fundamental to a reliable booking system.
4.  **Separation of Concerns:** The service uses another service (`CustomerService`). This shows a good separation of concerns, where booking-related logic and customer-related logic are kept in their respective modules.
5.  **Logic is Centralized:** All ways of creating, updating, or changing the state of a booking (create, cancel, check-in, check-out) are centralized in this one class, making the business rules consistent and easy to find.

## 11. Potential confusing parts

*   **`_lock_least_loaded_therapist`**: This method is complex. It combines a workload calculation query with a row-locking query. Understanding that this is designed to solve a concurrency problem (preventing double bookings) and also a business goal (distributing work evenly among therapists) is key.
*   **Mocked POS API:** The `_call_pos_api` method is currently a mock that always returns success. In a real-world scenario, this would contain a network request to an external system and would need much more robust error handling.
*   **Static Class**: The class contains only `@staticmethod`s. This is a design choice to group related functions. It could also have been implemented as a simple file with top-level functions instead of a class. The primary benefit of the class is namespacing (i.e., you call `BookingService.create()`).

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the meticulous and strict manager of the booking process.** It takes a booking request, rigorously checks it against all business rules, performs a complex and concurrency-safe matchmaking process to assign a therapist, and then carefully updates the database within a secure transaction. It is the single source of truth for all business logic related to creating and changing the state of a booking, ensuring the system's data remains consistent and reliable.
