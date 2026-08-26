# 6. System Data Flow

This document traces key data objects as they move through the `Frontend`, `Chatbot`, and `Booking API` systems.

---

## `User`

Represents an authenticated staff member (Admin or Therapist).

1.  **Origination**: A user enters their username and password into the [[spa-booking-frontend/app/login/page.tsx|Frontend Login Page]].
2.  **Transformation**:
    -   The [[spa-booking-api/app/blueprints/auth.py|Booking API Auth Blueprint]] receives the credentials.
    -   It queries the `users` table in **PostgreSQL** via the [[spa-booking-api/app/models/user.py|User model]].
    -   It verifies the password hash.
    -   It generates a `JWT` containing the `user.id` and `user.role`.
3.  **Storage**:
    -   The `users` table in **PostgreSQL** is the source of truth.
    -   The `JWT` is stored in the user's browser `localStorage`.
    -   The user object from the API response is stored in React state via [[spa-booking-frontend/contexts/AuthContext.tsx|AuthContext]].
4.  **Consumption**:
    -   The **Frontend** uses the user's role to show/hide UI elements (e.g., Admin dashboard links).
    -   The **Booking API** uses the `@jwt_required()` decorator to protect endpoints, checking the user's role to authorize access to specific resources (e.g., `/api/admin/*`).

---

## `Shop`, `Course`, `Therapist`

These are core business entities, mostly read-only for non-admin flows.

1.  **Origination**: Created and managed by Admins through the Admin dashboard.
2.  **Storage**: Stored in their respective tables (`shops`, `courses`, `therapists`) in **PostgreSQL**.
3.  **Consumption**:
    -   **Chatbot**: The chatbot's `search` tools ([[chatbot/tools/search_tools.py]]) query API endpoints like `/api/shops` and `/api/shops/{id}/courses`.
        -   The API response is parsed into Pydantic models like `ShopInfo` and `CourseInfo` ([[chatbot/models/__init__.py]]).
        -   This information is used to answer user questions and fill slots in the `BookingContext`.
    -   **Frontend**: The frontend booking page fetches and displays this data directly from the API to populate selection menus.

---

## `Slot`

Represents an available time for a booking. It is a **dynamic, calculated object**, not a stored entity.

1.  **Origination**: A `Slot` is calculated on-the-fly by the **Booking API**.
    -   A request is made by the **Frontend** or **Chatbot** to `GET /api/shops/{id}/available-slots` with parameters like `date`, `duration`, and `numberOfPeople`.
    -   The request is handled by [[spa-booking-api/app/blueprints/shops.py]].
2.  **Transformation**:
    -   The [[spa-booking-api/app/services/slot_service.py|Slot Service]] calculates availability. It fetches:
        -   Therapists on shift for that day.
        -   Existing bookings for that day.
    -   It iterates through time blocks, checks for overlapping bookings, and calculates the available capacity for each block.
3.  **Storage**: Slots are not stored in the database. They exist only in the API response.
4.  **Consumption**:
    -   The **Chatbot** receives a `SearchAvailableSlotsResponse` containing a list of `SlotInfo` objects ([[chatbot/models/__init__.py]]) and presents them to the user.
    -   The **Frontend** receives the same data and renders it as a list of available times for the user to click.

---

## `Chat Message` & `Session State`

Represents the user's conversation with the chatbot.

1.  **Origination**: The user types a message into the [[spa-booking-frontend/components/chatbot/ChatWindow.tsx|ChatWindow]] component.
2.  **Transformation**:
    -   The [[spa-booking-frontend/lib/hooks/useChat.ts|useChat hook]] wraps the message text in a `ChatRequest` object, including the `session_id`.
    -   It sends a `POST` request to the `/chat` endpoint on the **Chatbot** server.
3.  **Storage**:
    -   The **Frontend** stores the `session_id` in a React `useRef` to maintain the session across messages. The history of messages is stored in React state.
    -   The **Chatbot** backend uses a [[chatbot/session/manager.py|SessionManager]] to persist the `ConversationState` (which includes the `BookingContext` and message history) between requests, typically using a Redis cache keyed by `session_id`.
4.  **Consumption**:
    -   The **Chatbot**'s [[chatbot/app/chat_endpoint.py|chat endpoint]] uses the `session_id` to retrieve the user's current `ConversationState`.
    -   The NLU, Policy, and Planner components use this state to understand the context and decide on the next action.
    -   The final `ChatResponse` sent back to the frontend includes the updated state.

---

## `BookingContext` & `NLUResult`

These objects represent the chatbot's understanding of the user's booking request.

1.  **Origination**: `NLUResult` is created by the [[chatbot/nlu/nlu_pipeline.py|NLU Pipeline]] after processing a user's `Chat Message`. It contains the extracted `intent` and `entities` (e.g., `duration: 60`, `shop_name: "Shinjuku"`).
2.  **Transformation**:
    -   The `NLUResult` is passed to the [[chatbot/conversation/slot_filling.py|Slot Filling]] manager.
    -   This manager uses the entities from the `NLUResult` to update the `BookingContext` object, which holds the structured booking data.
3.  **Storage**: `BookingContext` is the central data store for a single booking conversation. It is part of the `ConversationState` and is persisted in the session store (Redis) between user messages.
4.  **Consumption**:
    -   The [[chatbot/conversation/policy.py|Dialogue Policy]] inspects the `BookingContext` to see which "slots" (pieces of information) are filled and which are still missing. This determines its next action (e.g., ask for the date, ask for the time).
    -   When all required slots are filled, the `BookingContext` is used by the `createBooking` tool to construct the `CreateBookingRequest` sent to the **Booking API**.

---

## `Booking`

The final, confirmed booking record.

1.  **Origination**: A `Booking` is created when the **Frontend** or **Chatbot** sends a `POST` request to `/api/bookings`.
    -   The chatbot uses the `createBooking` tool, which takes the filled `BookingContext` and creates a `CreateBookingRequest` Pydantic model.
    -   The frontend's booking page constructs a similar object from its form state.
2.  **Transformation**:
    -   The **Booking API** receives the request at [[spa-booking-api/app/blueprints/bookings.py]].
    -   It calls the [[spa-booking-api/app/services/booking_service.py|Booking Service]].
3.  **Storage**:
    -   The booking service maps the request data to SQLAlchemy models: `Booking`, `BookingService`, `BookingAddon`, `BookingTherapist`.
    -   It inserts these records into their corresponding tables in **PostgreSQL** within a single transaction. This is the canonical storage location.
4.  **Consumption**:
    -   The API returns the newly created booking object (including the `booking_code`).
    -   The **Frontend** or **Chatbot** displays the confirmation to the user.
    -   **Admins** and **Therapists** can later view the booking data through their respective dashboards, which query the Booking API.
