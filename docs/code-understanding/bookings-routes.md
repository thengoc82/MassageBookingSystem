
# `spa-booking-api/app/blueprints/bookings/routes.py`

## 1. Purpose

This file defines the public-facing API endpoints for managing bookings. It acts as the **thin controller layer** for all booking-related operations. Its primary responsibility is to receive incoming HTTP requests, parse any necessary data from the request body or URL, delegate the actual business logic to the `BookingService`, and then format the service's response into a proper JSON success response.

## 2. Where it fits

This file is a "blueprint" that gets registered by the main application factory. It handles the routing for all URLs under the `/api/bookings` prefix.

```text
HTTP Request (e.g., POST /api/bookings)
    ↓
Flask routes the request to this file
    ↓
The corresponding route function (`create_booking()`) is executed
    ↓
Function calls the appropriate method on `BookingService` (e.g., `BookingService.create(data)`)
    ↓
`BookingService` performs business logic (validation, database operations, therapist assignment)
    ↓
`BookingService` returns a result (e.g., a Booking object)
    ↓
Route function formats the result into a JSON response using `success_response()`
    ↓
HTTP Response is sent back to the client
```

## 3. Inputs

The functions in this file receive inputs from the incoming HTTP request:

*   **Request Body**: `POST` and `PATCH` requests use `request.get_json()` to get the JSON payload sent by the client. This is the primary input for creating or updating a booking.
*   **URL Parameters**: `GET /api/bookings/<booking_id>` uses the `booking_id` captured from the URL path.
*   **Query String Parameters**: `GET /api/bookings` uses `request.args.get()` to read optional filtering criteria from the URL's query string (e.g., `?shopId=1&status=Booked`).

## 4. Outputs

*   **JSON Responses**: Every endpoint returns a standardized JSON response. This is handled by the `success_response` utility, which wraps the data in a consistent structure (e.g., `{"success": true, "data": {...}}`) and sets the correct HTTP status code.
*   **HTTP Status Codes**:
    *   `201 Created` for a successful `POST` request.
    *   `200 OK` for all other successful requests.
*   **Error Responses**: If `BookingService` raises an exception (e.g., `ValidationError`, `ResourceNotFound`), a centralized error handler (registered in `app/__init__.py`) catches it and transforms it into a standardized JSON error response with an appropriate HTTP status code (e.g., 400, 404). This file does not handle errors directly.

## 5. Important functions/classes

This file contains one function for each API endpoint.

```text
create_booking()
@bookings_bp.route('', methods=['POST'])
    ↓
Purpose: To handle the creation of a new booking. This is the most critical endpoint in the file.
    ↓
Input: A JSON object from the request body containing all details for the new booking (`shopId`, `date`, `time`, `courses`, preferences, etc.).
    ↓
What it does:
    1. Gets the JSON data from the request.
    2. Calls `BookingService.create(data)`, delegating all validation, therapist assignment, and database logic.
    3. Receives the created `booking` object back from the service.
    4. Formats a custom response payload containing the `bookingId`, `bookingCode`, and therapist assignment details.
    5. Wraps this payload in a `success_response` and returns it with a 201 status code.
```

```text
get_bookings()
@bookings_bp.route('', methods=['GET'])
    ↓
Purpose: To retrieve a paginated and filtered list of bookings.
    ↓
Input: Optional query string parameters for filtering (`shopId`, `phone`, `status`, etc.) and pagination (`page`, `size`).
    ↓
What it does:
    1. Collects all filter parameters from `request.args` into a dictionary.
    2. Calls `BookingService.get_bookings(filters)`.
    3. Returns the result (which includes the data and pagination info) directly in a `success_response`.
```

## 6. Execution flow

**Example Flow for Creating a Booking:**

1.  A client sends a `POST` request to `/api/bookings` with a JSON payload.
2.  Flask matches the URL and method to the `create_booking` function.
3.  `request.get_json()` parses the request body into a Python dictionary.
4.  This `data` dictionary is passed to `BookingService.create(data)`.
5.  `BookingService` performs a series of complex operations:
    *   Validates required fields.
    *   Checks customer eligibility.
    *   Finds and locks an available therapist based on preferences and workload, which involves database queries with row-level locking (`WITH FOR UPDATE`).
    *   Creates a `Booking` record and associated `BookingTherapist`, `BookingService`, and `BookingAddon` records in the database session.
    *   Generates a unique `booking_code`.
    *   Makes a (mock) call to a POS API.
    *   If all steps succeed, it commits the database transaction. If any step fails, it rolls back the transaction and raises an exception.
6.  If `BookingService.create` is successful, it returns the newly created `Booking` SQLAlchemy object.
7.  The `create_booking` function builds a dictionary from this object, including therapist assignment details.
8.  This dictionary is passed to `success_response`, which creates a `Flask.Response` object with a JSON body and a `201 Created` status.
9.  This response is sent back to the client.

## 7. Dependencies

```text
bookings_bp (from `app.blueprints.bookings`)
    ↓
    The Blueprint object itself. The `@bookings_bp.route()` decorator is used to attach these functions as routes to this specific blueprint.

BookingService (from `app.services.booking_service`)
    ↓
    This is the most important dependency. This file is a "controller" that delegates almost all of its business logic to this "service" layer.

success_response, ResourceNotFound (from `app.utils.*`)
    ↓
    Utility functions and custom exceptions. `success_response` standardizes the format of all successful API responses. `ResourceNotFound` is a custom exception that can be raised if a booking ID doesn't exist.
```

## 8. Relationship with other files

```text
This file (app/blueprints/bookings/routes.py)
 ├── is part of the blueprint defined in → app/blueprints/bookings/__init__.py
 ├── delegates all logic to → app/services/booking_service.py
 └── uses utilities from → app/utils/
```

## 9. Important state/data

This file is **stateless**. It does not maintain any state between requests. Each request is handled independently. The important data it handles is transient:

*   **`data` from `request.get_json()`**: The incoming booking data, which is immediately passed to the service layer.
*   **`booking` object**: The SQLAlchemy model instance returned by the service layer, which is immediately transformed into a dictionary for the JSON response.

## 10. What I should understand

1.  **It's a Thin Controller:** This file is a perfect example of the "thin controller, fat model/service" design pattern. The route handlers are very short and declarative. Their only job is to manage the HTTP interface, not to implement business rules.
2.  **Logic is Delegated to the Service Layer:** All the complex work—database interaction, validation, therapist assignment—is handled by `BookingService`. This makes the code organized and easy to test.
3.  **Standardized Responses:** The use of `success_response` and centralized error handling means the API will be consistent and predictable for frontend developers.
4.  **The Endpoints Match CRUD Operations:** The routes generally correspond to Create, Read, Update, Delete (CRUD) operations on the `Booking` resource:
    *   `POST /`: Create
    *   `GET /`: Read (List)
    *   `GET /<id>`: Read (Single)
    *   `PATCH /<id>`: Update
    *   `PATCH /<id>/cancel`: Update (a specific state change).

## 11. Potential confusing parts

*   **Where is the Logic?**: Someone reading this file alone would have no idea how a booking is actually created. The comment "delegates all the actual work to a `BookingService`" is key. To understand the business logic, you *must* look at `app/services/booking_service.py`.
*   **Implicit Error Handling:** There are no `try...except` blocks in most functions. This is because errors are handled globally by a decorator or a handler registered on the Flask `app` object in `app/__init__.py`, which catches exceptions raised from the service layer.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the polite receptionist for the bookings API.** It greets incoming HTTP requests, takes down their details (`request.get_json()`), and passes the request to the back office (`BookingService`) to do the actual work. It doesn't make any decisions itself; it just ensures the paperwork is handed off correctly and then presents the final result back to the client in a clean, standardized format.
