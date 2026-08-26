# API Key Files

This document ranks the 15 most important files in the `spa-booking-api` for a developer to read to understand the system. They are ordered to provide a logical learning path from the highest level down to the implementation details.

1.  **[[spa-booking-api/run.py]]**
    -   **Why**: The application's main entry point. It shows how the app server is started and that it uses the `create_app` factory.

2.  **[[spa-booking-api/app/__init__.py]]**
    -   **Why**: The application factory. This is the single most important file for understanding the overall structure. It shows which extensions (DB, JWT), blueprints (URL routes), and error handlers are registered.

3.  **[[spa-booking-api/app/services/booking_service.py]]**
    -   **Why**: Contains the **primary business logic** for the entire application: creating, updating, and managing bookings. The `create` method with its database transaction and therapist locking is the most critical piece of logic in the repo.

4.  **[[spa-booking-api/app/services/therapist_service.py]]**
    -   **Why**: Contains the second most important piece of business logic: calculating therapist availability. The `is_available` method is the source of truth for whether a therapist can be booked.

5.  **[[spa-booking-api/app/services/slot_service.py]]**
    -   **Why**: Orchestrates the availability search. It shows how the low-level logic from `TherapistService` is used to generate a user-facing list of available time slots.

6.  **[[spa-booking-api/app/models/booking.py]]**
    -   **Why**: Defines the `Booking` model and its crucial satellite tables (`BookingTherapist`, `BookingService`, `BookingAddon`). Understanding these relationships is key to understanding how a booking is stored.

7.  **[[spa-booking-api/app/models/therapist.py]]**
    -   **Why**: Defines the `Therapist` model, which is central to all availability and booking logic.

8.  **[[spa-booking-api/app/models/therapist_shift.py]]**
    -   **Why**: Defines the `TherapistShift` model. No availability logic can be understood without knowing how therapist work schedules are defined.

9.  **[[spa-booking-api/app/blueprints/bookings/routes.py]]**
    -   **Why**: The main API endpoint for creating and managing bookings. It's a clear example of the blueprint/service pattern, showing how HTTP requests are mapped to business logic.

10. **[[spa-booking-api/app/blueprints/public/slots.py]]**
    -   **Why**: The endpoint for the critical "search available slots" feature. Shows how complex queries with multiple parameters are handled and passed to the service layer.

11. **[[spa-booking-api/app/blueprints/auth/__init__.py]]**
    -   **Why**: Contains all login logic. Shows how different user roles are authenticated and how JWTs are created.

12. **[[spa-booking-api/app/utils/decorators.py]]**
    -   **Why**: The `@role_required` decorator is the key to the system's authorization. This file explains how admin-only endpoints are protected.

13. **[[spa-booking-api/app/models/shop.py]]**
    -   **Why**: Defines the `Shop` model, a high-level entity that groups most other data (therapists, courses, bookings).

14. **[[spa-booking-api/app/models/customer.py]]**
    -   **Why**: Defines the `Customer` model and its link to `CustomerRestriction`, showing how the blocklist (NG List) is implemented.

15. **[[spa-booking-api/app/extensions.py]]**
    -   **Why**: A simple file, but it declares all the global Flask extension objects (db, jwt, etc.) that are initialized and used throughout the application.
