# API Dependency Map

This document illustrates the dependencies between the main components of the API: Blueprints, Services, and Models.

```mermaid
graph TD
    subgraph Blueprints
        A1["/api (public_bp)"]
        A2["/api/bookings (bookings_bp)"]
        A3["/api/auth (auth_bp)"]
        A4["/api/admin (admin_bp)"]
    end

    subgraph Services
        B1["slot_service.py"]
        B2["therapist_service.py"]
        B3["booking_service.py"]
        B4["customer_service.py"]
    end

    subgraph Models
        C1["Shop"]
        C2["Therapist"]
        C3["TherapistShift"]
        C4["Booking"]
        C5["BookingTherapist"]
        C6["Customer"]
        C7["CustomerRestriction"]
        C8["Course"]
        C9["User"]
    end
    
    subgraph Database Tables
        D1["shops"]
        D2["therapists"]
        D3["therapist_shifts"]
        D4["bookings"]
        D5["booking_therapists"]
        D6["customers"]
        D7["customer_restrictions"]
        D8["courses"]
        D9["users"]
    end

    %% Blueprint to Service
    A1 --> B1
    A2 --> B3
    A4 --> B3
    A4 --> B4
    
    %% Service to Service
    B1 --> B2
    
    %% Service to Model
    A1 -.-> C1
    B1 --> C1
    B1 --> C4
    B1 --> C5
    B2 --> C2
    B2 --> C3
    B2 --> C4
    B2 --> C5
    B3 --> C4
    B3 --> C5
    B3 --> C2
    B3 --> C6
    B3 --> C8
    B4 --> C6
    B4 --> C7
    A3 --> C9
    A3 --> C2
    A3 --> C6

    %% Model to Table
    C1 --> D1
    C2 --> D2
    C3 --> D3
    C4 --> D4
    C5 --> D5
    C6 --> D6
    C7 --> D7
    C8 --> D8
    C9 --> D9

    linkStyle 7 stroke-width:2px,fill:none,stroke:red,stroke-dasharray: 3 3;
```

## Dependency Paths

### Blueprint → Service

-   `public_bp` (`/api`)
    -   `slots.py` → `SlotService`
    -   `shops.py` → No service, direct model access.
-   `bookings_bp` (`/api/bookings`)
    -   `routes.py` → `BookingService`
-   `auth_bp` (`/api/auth`)
    -   `__init__.py` → No service, direct model access for authentication.
-   `admin_bp` (`/api/admin`)
    -   Most routes use direct model access for simple CRUD, but more complex operations like creating a booking would likely call `BookingService`. `customers.py` calls `CustomerService`.

### Service → Service

-   `SlotService` → `TherapistService`: `SlotService` delegates the core availability check for each therapist to `TherapistService`.

### Service → Model

-   `SlotService`: Uses `Shop` (to get hours), `Therapist` (to list them), `Booking` and `BookingTherapist` (to show existing bookings).
-   `TherapistService`: Uses `Therapist`, `TherapistShift` (to check schedules), and `Booking`/`BookingTherapist` (to check for conflicts). **This is the core of availability logic.**
-   `BookingService`: The most complex service. It uses `Customer` (eligibility), `Therapist` (locking/assignment), `Booking`, `BookingTherapist`, `BookingService` model, `BookingAddon` (to create the records).
-   `CustomerService`: Uses `Customer` and `CustomerRestriction` to manage the NG List.

### Model → Table

Each model class maps directly to a database table via the `__tablename__` attribute. For example, the `Booking` class in `booking.py` maps to the `bookings` table.
