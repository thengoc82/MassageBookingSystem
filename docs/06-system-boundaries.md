# 6. System Boundaries and Responsibilities

This document defines the clear responsibilities for each of the three main systems. These boundaries are verified against the source code to ensure this reflects the actual implementation.

---

## 1. `spa-booking-frontend` (Next.js)

The frontend is responsible for everything the user sees and directly interacts with. It is a presentation and user input layer.

### Should Do:

-   **Render UI**: Display all pages, components, forms, and data.
    -   *Evidence*: [[spa-booking-frontend/app]] directory structure defines all user-facing pages.
-   **Manage UI State**: Handle local UI state, such as form inputs, toggles, and pop-ups.
    -   *Evidence*: Components use `useState` and other React hooks extensively.
-   **Manage Authentication State**: Store the auth token and user information, making it available to the application.
    -   *Evidence*: [[spa-booking-frontend/contexts/AuthContext.tsx]] manages user state and token persistence in `localStorage`.
-   **Client-Side Routing**: Handle navigation between pages.
    -   *Evidence*: Next.js App Router is used for navigation.
-   **Make API Calls**: Act as a client for the Chatbot and Booking APIs. It formats requests and handles responses.
    -   *Evidence*: [[spa-booking-frontend/lib/api.ts]] and [[spa-booking-frontend/lib/hooks/useChat.ts]] define all outgoing communication.
-   **Maintain Chat Session**: Generate and persist the `session_id` for the duration of a user's interaction with the chatbot.
    -   *Evidence*: The `useChat` hook manages the `sessionId` in a `useRef`.

### Should NOT Do:

-   **Contain Business Logic**: It should not know *how* to calculate availability, validate a booking's business rules, or decide if a user is eligible to book.
    -   *Evidence*: The frontend calls `/api/shops/{id}/available-slots` and `/api/booking-eligibility-checks`; it doesn't perform these checks itself.
-   **Directly Access the Database**: The frontend must never have any database credentials or make direct connections.
    -   *Evidence*: No database-related libraries or code are present in the frontend project.
-   **Understand Conversation Logic**: It should not know what the "next step" in a chatbot conversation is. It just displays the messages and options provided by the chatbot.
    -   *Evidence*: The `useChat` hook receives a `phase` from the chatbot and uses it to conditionally render UI, but it does not determine the phase itself.

---

## 2. `chatbot` (Python/FastAPI)

The chatbot is the conversational brain. It is responsible for understanding natural language and managing the dialogue flow to achieve a user's goal.

### Should Do:

-   **Process Natural Language (NLU)**: Understand the user's intent and extract key information (entities) from their messages.
    -   *Evidence*: [[chatbot/nlu/nlu_pipeline.py]] is dedicated to intent classification and entity extraction.
-   **Manage Dialogue State**: Maintain the state of the conversation, including what information has been collected and what is still needed.
    -   *Evidence*: [[chatbot/conversation/slot_filling.py]] manages the `BookingContext`, and [[chatbot/session/manager.py]] persists this state.
-   **Control Conversation Flow (Policy)**: Decide the chatbot's next action based on the current state (e.g., ask a question, call a tool, end the conversation).
    -   *Evidence*: [[chatbot/conversation/policy.py]] contains different policies (`SlotFillingPolicy`, `FaqPolicy`) that determine the next action.
-   **Execute Tools**: Call external APIs or internal services to get information or perform actions.
    -   *Evidence*: The `Planner` selects tools from [[chatbot/tools/search_tools.py]] and [[chatbot/tools/write_tools.py]].
-   **Handle FAQs**: Answer general questions by searching an internal knowledge base, separate from the booking flow.
    -   *Evidence*: The `FAQSearchTool` uses a `KnowledgeService`, not the Booking API.

### Should NOT Do:

-   **Implement Core Business Logic**: It should not contain the rules for booking eligibility or slot availability. It is a *client* of the Booking API for this information.
    -   *Evidence*: It calls the Booking API to check eligibility and search for slots; it does not calculate them.
-   **Directly Access the Main Database**: It must not connect to the PostgreSQL database. All data access must go through the Booking API.
    -   *Evidence*: The chatbot's `HTTPClient` in [[chatbot/gateway/client.py]] only communicates with the Booking API's HTTP interface. It has no `psycopg2` or `sqlalchemy` dependencies for the main DB.
-   **Render UI**: It should not generate HTML or any other UI components. Its output is a structured JSON `ChatResponse`.
    -   *Evidence*: The chat endpoint in [[chatbot/app/main.py]] returns a Pydantic model, not a rendered template.

---

## 3. `spa-booking-api` (Python/Flask)

The Booking API is the single source of truth for all business data and rules. It is the gatekeeper to the database.

### Should Do:

-   **Define the Data Model**: Own the canonical definition of all data entities.
    -   *Evidence*: [[spa-booking-api/app/models]] contains all SQLAlchemy models that map directly to database tables.
-   **Enforce Business Rules**: Implement all business logic, such as validating a booking, checking for conflicts, and calculating availability.
    -   *Evidence*: [[spa-booking-api/app/services/booking_service.py]] contains complex logic for therapist assignment, conflict checking, and booking creation. [[spa-booking-api/app/services/slot_service.py]] calculates availability.
-   **Expose a Secure REST API**: Provide HTTP endpoints for the frontend and chatbot to interact with the data.
    -   *Evidence*: [[spa-booking-api/app/blueprints]] define all the API routes.
-   **Handle Authentication and Authorization**: Verify user credentials and check roles/permissions for API access.
    -   *Evidence*: [[spa-booking-api/app/blueprints/auth.py]] handles login. `flask_jwt_extended` decorators protect endpoints throughout the blueprints.
-   **Directly Access the Database**: Be the only system that performs read and write operations on the PostgreSQL database.
    -   *Evidence*: The services and blueprints extensively use the `db.session` object from `SQLAlchemy`.

### Should NOT Do:

-   **Render UI**: It should never return HTML. All responses should be JSON.
    -   *Evidence*: All blueprint routes return `jsonify` or a serialized response, not `render_template`.
-   **Manage Conversational State**: It should not know anything about chatbot sessions or dialogue history. Every API request is treated as an independent, stateless transaction.
    -   *Evidence*: There is no concept of a `session_id` or conversation history in the Booking API's codebase.
-   **Contain Presentation Logic**: It should not format data for display (e.g., formatting dates or currency). That is the frontend's responsibility.
    -   *Evidence*: The API returns raw data structures and ISO-formatted dates/times.
