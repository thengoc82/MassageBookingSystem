
# PART 1: WHAT IS THIS SYSTEM?

This project is an **AI-powered booking platform for a chain of massage parlors**.

It solves the problem of inefficient and manual appointment scheduling. Instead of calling the shop or using a simple web form, customers can book, modify, or ask questions about their appointments through a sophisticated, conversational AI chatbot, or through a more traditional graphical user interface.

The users of this system are:

*   **Customers**: They want to book massages, check their existing bookings, or ask questions about services. They can be new guests or returning members.
*   **Shop Administrators**: They manage the day-to-day operations, including viewing all bookings, managing shop details, courses, and therapist schedules.
*   **Therapists**: They can view their own schedules and manage their assigned bookings (e.g., check-in/check-out customers).

The major features are:

*   **Conversational Booking**: A customer can have a natural language conversation with a chatbot to find available slots and make a booking.
*   **GUI Booking**: A customer can use a traditional Gantt-chart-like interface to see availability and book a slot.
*   **FAQ Answering (RAG)**: The chatbot can answer questions about the business (e.g., "What are your opening hours?") by searching a knowledge base.
*   **Multi-Role Dashboards**: Separate, secure dashboards for Admins and Therapists to manage their specific tasks.
*   **Comprehensive Admin Panel**: Admins can manage shops, courses, therapists, schedules, customers, and all bookings.

The three applications are responsible for:

1.  **`spa-booking-frontend` (The Face)**: This is the web application that users interact with. It's a Next.js single-page application (SPA) that provides both the traditional booking UI and the chatbot interface. It's responsible for all visual presentation.
2.  **`spa-booking-api` (The Business Brain)**: This is the authoritative backend service. It's a Flask API that contains all the core business logic: what constitutes a valid booking, how to calculate availability, how to manage users, etc. It is the single source of truth for all business data.
3.  **`chatbot` (The Conversational Brain)**: This is a separate FastAPI service that understands human language. It does **not** contain any core booking logic itself. Its job is to have a conversation, understand the user's goal, and when it's time to act, **it calls the `spa-booking-api`** just like the frontend would.

---

# PART 2: THE BIG ARCHITECTURE

Here is the high-level architecture diagram based on the code:

```text
                     End User
                        │
                        ▼ (HTTPS via Browser)
   ┌──────────────────────────────────────────────┐
   │         Next.js Frontend Application         │
   │        (spa-booking-frontend @ :3000)        │
   └────────────────────┬─────────────────────────┘
                        │
    ┌───────────────────┴──────────────────┐
    │ REST API Calls     │ WebSocket/REST  │
    ▼                    ▼                 │
┌──────────────────┐ ┌───────────────────┐ │
│  Booking API     │ │   Chatbot API     │ │
│ (Flask @ :5000)  │ │ (FastAPI @ :8000) │ │
└────────┬─────────┘ └────────┬──────────┘ │
         │                    │            │
  ┌──────┴──────┐      ┌──────┴──────┐     │
  │ SQL Queries │      │ HTTP Client │     │
  ▼             ▼      ▼             ▼     │
┌──────────┐ ┌────────┐ ┌───────────┐ ┌───┴───┐
│ PostgreSQL │ │ Redis  │ │ Booking API │ │ pgvector│
│  (Data)    │ │(Cache/ │ │  (:5000)   │ │ (RAG) │
└────────────┘ │Session)│ └───────────┘ └───────┘
               └────────┘
```

### Connection Explanations:

**Frontend → Booking API**
*   **WHO**: The frontend `AuthProvider` and `api.ts` client.
*   **CALLS**: The backend `spa-booking-api`.
*   **FOR WHAT**:
    *   Authenticating users (`/api/auth/login`).
    *   Fetching data for the GUI booking dashboard (shops, courses, availability).
    *   Creating the final booking from the GUI (`/api/bookings`).

**Frontend → Chatbot API**
*   **WHO**: The `useChat` hook in the frontend.
*   **CALLS**: The `chatbot` FastAPI service.
*   **FOR WHAT**: To send the user's message and session ID for processing, and to receive the bot's response and updated state. This is the main conversational loop.

**Chatbot API → Booking API**
*   **WHO**: The "Tools" within the chatbot (e.g., `SearchShopsTool`, `CreateBookingTool`).
*   **CALLS**: The `spa-booking-api`.
*   **FOR WHAT**: To execute actions on behalf of the user. The chatbot **delegates** all business logic. When it needs to find shops, it calls the Booking API's `/shops` endpoint. When it needs to create a booking, it calls the `/bookings` endpoint. **The chatbot acts like another client to the Booking API.**

**Booking API → PostgreSQL**
*   **WHO**: The `BookingService` and other services, via SQLAlchemy models.
*   **CALLS**: The PostgreSQL database.
*   **FOR WHAT**: To create, read, update, and delete all persistent business data (bookings, users, shops, etc.). This is the primary data store.

**Booking API → Redis**
*   **WHO**: Not explicitly shown in the currently inspected code, but Redis is initialized.
*   **CALLS**: The Redis server.
*   **FOR WHAT**: Typically used for caching expensive queries or managing temporary state. Its exact usage is not clear from the inspected files but it is part of the architecture.

**Chatbot API → Redis**
*   **WHO**: The `RedisSessionStore`.
*   **CALLS**: The Redis server.
*   **FOR WHAT**: To store the `ConversationState` for each active chat session. This is how the bot remembers the context of a conversation from one turn to the next.

**Chatbot API → pgvector**
*   **WHO**: The `FAQSearchTool` via the `KnowledgeService`.
*   **CALLS**: The PostgreSQL database with the `pgvector` extension enabled.
*   **FOR WHAT**: To perform semantic similarity searches for the RAG (Retrieval-Augmented Generation) feature. It searches for user questions in a vectorized knowledge base to find the most relevant answer.

---

# PART 3: FOLLOW ONE USER THROUGH THE SYSTEM

**Scenario**: A customer wants to book a 60-minute massage at Shinjuku tomorrow for 2 people.

1.  **User Input**
    *   **What happens?** The user types "a 60 min massage tomorrow at Shinjuku for 2 people" into the chat window.
    *   **Application**: `spa-booking-frontend`
    *   **Component**: The `<textarea>` in `ChatWindow.tsx`.
    *   **Data In**: Keystrokes.
    *   **Data Out**: A call to the `sendMessage` function from the `useChat` hook.

2.  **Frontend to Chatbot Communication**
    *   **What happens?** The `useChat` hook sends an HTTP POST request to the chatbot backend.
    *   **Application**: `spa-booking-frontend`
    *   **Component**: `lib/hooks/useChat.ts`'s `sendMessage` function.
    *   **Data In**: The user's message string.
    *   **Data Out**: A `ChatRequest` JSON object: `{ "message": "...", "session_id": "...", "user_id": "..." }` sent to `POST /chat`.

3.  **Natural Language Understanding (NLU)**
    *   **What happens?** The chatbot's `ChatEndpoint` receives the request and immediately passes the message to the NLU pipeline. The NLU processes the text and extracts structured information.
    *   **Application**: `chatbot`
    *   **Component**: `chatbot/nlu/nlu.py`'s `understand()` method.
    *   **Data In**: The raw message string.
    *   **Data Out**: An `NLUResult` object.
        *   `intent`: `CREATE_BOOKING`
        *   `entities`: `[DATE: "2026-08-12", DURATION: 60, NUMBER_OF_PEOPLE: 2, SHOP_ID: "shinjuku_id"]` (assuming "Shinjuku" is a known shop).

4.  **Dialogue Policy Decision**
    *   **What happens?** The `ChatEndpoint` takes the `NLUResult` and the current `ConversationState` and asks the policy manager what to do next. The policy sees the goal is to book an appointment but the `course_id` is missing. It decides it needs to run a tool to find available courses.
    *   **Application**: `chatbot`
    *   **Component**: `chatbot/conversation/policy.py`'s `_next_booking_step()` method.
    *   **Data In**: The current `ConversationState` and the `CREATE_BOOKING` intent.
    *   **Data Out**: A `PolicyDecision` object: `{ action: RUN_TOOL, tool: 'search_courses' }`.

5.  **Tool Execution**
    *   **What happens?** The `ChatEndpoint` executes the decision. It looks up the `search_courses` tool and calls it. The tool makes an HTTP GET request to the **Booking API**.
    *   **Application**: `chatbot`
    *   **Component**: `chatbot/tools/search_tools.py`'s `SearchCoursesTool.execute()`.
    *   **Data In**: A `SearchCoursesRequest` with `shopId='shinjuku_id'`.
    *   **Data Out**: An HTTP `GET` request to `spa-booking-api/api/shops/shinjuku_id/courses`.

6.  **Booking API Logic**
    *   **What happens?** The Booking API receives the request. The appropriate service method queries the database for all courses available at the Shinjuku shop.
    *   **Application**: `spa-booking-api`
    *   **Component**: A route in the `public` blueprint, which calls a service method that queries the `Course` model.
    *   **Data In**: HTTP Request.
    *   **Data Out**: A JSON response containing a list of course objects.

7.  **Response Generation**
    *   **What happens?** The `SearchCoursesTool` in the chatbot receives the list of courses. The `ChatEndpoint` takes this result, generates user-friendly "packages" from them, and formulates a response asking the user which course they'd like.
    *   **Application**: `chatbot`
    *   **Component**: `chatbot/app/chat_endpoint.py`'s `_search_courses()` helper.
    *   **Data In**: The list of courses from the Booking API.
    *   **Data Out**: A `ChatResponse` object:
        *   `message`: "Here are the available courses... Which would you like?"
        *   `phase`: `SELECTING_PACKAGE`
        *   `data`: `{ "packages": [...] }` for the frontend to render as interactive options.

8.  **Frontend Renders Response**
    *   **What happens?** The `useChat` hook receives the `ChatResponse`. It updates its `messages` and `bookingState`. The `ChatWindow` component re-renders, displaying the bot's question and a list of interactive `PackageOptions` components.
    *   **Application**: `spa-booking-frontend`
    *   **Component**: `components/chatbot/ChatWindow.tsx`'s `renderMessageContent()` function.
    *   **Data In**: The `ChatResponse` object.
    *   **Data Out**: Rendered HTML for the user to see.

This cycle continues, with the chatbot asking for the `start_time` and then finally the `phone_number`, before presenting a final confirmation.

---

# PART 4: UNDERSTAND THE THREE APPLICATIONS

## A. Frontend (`spa-booking-frontend`)

```text
User
 ↓
Next.js Page (e.g., `/dashboard`)
 ↓
React Component (e.g., `DashboardPage.tsx`)
 ↓
React Hook (e.g., `useAuth` or `useChat`)
 ↓
HTTP Request (via `api.ts` or `axios`)
 ↓
Backend Service (Booking API or Chatbot)
```

*   **Pages**: The app directory structure defines the pages: `/` (redirects), `/dashboard`, `/login`, `/reservation`, and the admin/therapist sections (`/admin`, `/admin/bookings`, etc.).
*   **Important Components**: `NavBar.tsx` (site navigation), `TherapistGantt.tsx` (the GUI booking view), `ChatWidget.tsx` (launches chat), `ChatWindow.tsx` (the main chat UI).
*   **Authentication**: Handled by `contexts/AuthContext.tsx`. It provides the `useAuth` hook, stores the token in `localStorage`, and makes login/logout functions available globally.
*   **Booking State (GUI)**: Stored locally as component state within `app/dashboard/page.tsx` and `app/reservation/page.tsx`.
*   **Chatbot State**: Managed by the `lib/hooks/useChat.ts` hook. It holds the message history and a copy of the `bookingState` received from the chatbot backend.
*   **Communication with Booking API**: Done via a typed wrapper in `lib/api.ts`, which makes authenticated `fetch` calls.
*   **Communication with Chatbot**: Handled exclusively by `lib/hooks/useChat.ts`, which calls the chatbot's `/chat` endpoint.
*   **Booking UI**: Comes from components like `TherapistGantt.tsx` and the form in `app/reservation/page.tsx`.
*   **Chat UI**: Comes from `ChatWidget.tsx`, `ChatWindow.tsx`, and its many sub-components (`PackageOptions.tsx`, `TimePicker.tsx`, etc.).

## B. Booking API (`spa-booking-api`)

```text
HTTP Request
 ↓
Blueprint (e.g., `bookings_bp` in `bookings/routes.py`)
 ↓
Service (e.g., `BookingService` in `services/booking_service.py`)
 ↓
Model (e.g., `Booking` in `models/booking.py`)
 ↓
PostgreSQL (via SQLAlchemy)
 ↓
HTTP Response
```

*   **Blueprint**: A collection of related routes (API endpoints) for a specific business domain. It's Flask's way of organizing a large application.
*   **Service**: A class containing the core business logic. It orchestrates database operations, validation, and calls to other services.
*   **Model**: A Python class that maps to a database table, defining its schema. It's used by SQLAlchemy to query and manipulate data.
*   **Why are they separated?**: This is the classic **three-tier architecture**.
    *   **Controllers (Blueprints)** handle HTTP and are kept thin.
    *   **Services** handle business logic, making it reusable and testable.
    *   **Models** handle data representation and persistence.
    This separation makes the application maintainable and scalable.
*   **Blueprint Domains**:
    *   `auth_bp`: Handles login.
    *   `public_bp`: Handles public data (shops, courses).
    *   `bookings_bp`: Handles customer-facing booking operations.
    *   `admin_bp`: Handles all admin-only operations.
    *   `therapist_bp`: Handles therapist-specific operations.
*   **Where Logic Lives**:
    *   **Booking Logic**: `app/services/booking_service.py`.
    *   **Availability Logic**: Primarily in `app/services/availability_service.py`.
    *   **Therapist Logic**: Both in `booking_service.py` (for assignment) and `therapist_service.py`.
    *   **Authentication**: Handled by the `auth` blueprint and the `flask-jwt-extended` extension.

### Customer Booking Flow (Component Mapping)

*   **Shop**: `public_bp` -> `ShopService`
*   **Date, Guests, Duration, Course**: These are inputs to the availability search.
*   **Availability**: `public_bp` -> `AvailabilityService`
*   **Time**: User selects from the availability results.
*   **Therapist**: `booking_bp` -> `BookingService._lock_least_loaded_therapist`
*   **Reservation**: `booking_bp` -> `BookingService.create`
*   **Confirmation**: `BookingService` returns the created booking details.

## C. Chatbot (`chatbot`)

The chatbot is a pipeline that processes a message in sequential stages.

```text
User Message
     ↓
`ChatEndpoint.process_message()`
(The Orchestrator)
     ↓
`NLU.understand()`
(Extracts Intent & Entities: "What does the user mean?")
     ↓
`ConversationState` loaded from Redis
(Tracks Memory: "What do we already know?")
     ↓
`DialoguePolicyManager.decide()`
(The Brain: "Based on what they want and what we know, what's the next strategic move?")
     ↓
`SlotFillingManager.continue_filling()`
(The Task Manager: "The brain wants to run a tool, do I have all the required info? If not, ask for it.")
     ↓
`ToolRegistry` & a specific `*Tool.execute()`
(The Hands: "Execute the decided action, like calling the Booking API or searching the knowledge base.")
     ↓
The Tool returns a result
     ↓
`ChatEndpoint` formats the result into a `ChatResponse`
(The Mouth: "Formulate a user-friendly response.")
     ↓
`ConversationState` saved back to Redis
(Update Memory)
     ↓
`ChatResponse` sent to Frontend
```

*   **Chat Endpoint**: The web server layer (`chat_endpoint.py`) that receives HTTP requests and orchestrates the entire pipeline.
*   **NLU**: Understands the user's raw text.
*   **Dialogue State**: The memory of the conversation, stored in Redis. `ConversationState` in `conversation/state.py` is the main data model.
*   **Dialogue Policy**: The strategic brain (`conversation/policy.py`) that decides the high-level next action.
*   **Planner / Tool Orchestrator**: This role is shared. The **Policy** plans the high-level action (`RUN_TOOL`). The **Slot Filler** micro-manages the prerequisites. The **Chat Endpoint** is the final orchestrator that executes the tool.
*   **Tools**: The "hands" of the chatbot. They are wrappers (`tools/search_tools.py`, `tools/write_tools.py`) around external calls, primarily to the Booking API.
*   **Session**: The concept of an ongoing conversation, identified by a `session_id` and persisted in Redis.
*   **RAG / Knowledge**: Handled by the `FAQSearchTool`, which uses the `KnowledgeService` to query a `pgvector` database.

---

# PART 5: TWO COMPLETELY DIFFERENT FLOWS

### Booking Conversation vs. FAQ Conversation

The divergence happens right after the NLU stage, in the **Dialogue Policy Manager**.

| **Booking Flow ("I want a 60 min massage")** | **FAQ Flow ("What are your opening hours?")** |
| :--- | :--- |
| **1. NLU** `nlu.py` | **1. NLU** `nlu.py` |
| `intent`: `CREATE_BOOKING` | `intent`: `FAQ` |
| `entities`: `[DURATION: 60]` | `entities`: `[]` |
| **2. Policy** `policy.py` | **2. Policy** `policy.py` |
| `decide()` sees `CREATE_BOOKING` intent and calls `_decide_booking()`. | `decide()` sees `FAQ` intent and calls `_decide_faq()`. |
| **3. Action** | **3. Action** |
| The policy sees that `shop_id` is missing. It returns a decision: `{ action: RUN_TOOL, tool: 'search_shops' }`. | The policy returns a decision: `{ action: ANSWER_FAQ }`. |
| **4. Execution** `chat_endpoint.py` | **4. Execution** `chat_endpoint.py` |
| The `ChatEndpoint` runs the `SearchShopsTool`. | The `ChatEndpoint` runs the `_faq_search` handler. |
| **5. Data Source** | **5. Data Source** |
| The tool calls the **Booking API** (`GET /shops`). | The handler calls the `FAQSearchTool`, which queries the **pgvector Knowledge Base**. |
| **6. Result** | **6. Result** |
| Returns a list of shops and asks the user to choose one. **The conversation continues.** | Returns the retrieved answer. **The conversation goal is complete**, and it may ask "Is there anything else?" |

The chatbot knows the difference because of the **`intent`** classified by the NLU. The `DialoguePolicyManager` has a main `if/elif/else` block that routes the flow based on this intent.

---

# PART 6: DATA

### Data Map

```text
              ┌───────────────────┐
              │   Browser State   │
              │ (localStorage)    │
              └─────────┬─────────┘
                        │ (User Token, UI state)
                        ▼
          ┌──────────────────────────┐
          │ `spa-booking-frontend`   │
          └──────────┬───────────────┘
                     │
          ┌──────────┴───────────┐
          ▼                      ▼
  `spa-booking-api`         `chatbot`
          │                      │
          │                      ▼
  ┌───────┴──────┐      ┌────────┴────────┐
  │  PostgreSQL  │      │      Redis      │
  └───────┬──────┘      └─────────────────┘
          │ (Business Data)
  ┌───────┴──────┐
  │   pgvector   │
  │  (KB Embeds) │
  └──────────────┘
```

*   **PostgreSQL**: Stores all **persistent, authoritative business data**. This includes `Bookings`, `Users`, `Customers`, `Shops`, `Courses`, `Therapists`, and their schedules.
*   **Redis**: Stores **temporary session data**. Specifically, it stores the `ConversationState` object for each active chatbot session, keyed by `session_id`.
*   **pgvector**: Stores the **vector embeddings of the knowledge base documents**. It's a specialized part of the main PostgreSQL database used for fast similarity searches.
*   **Frontend State (`localStorage`)**: Stores the **user's authentication token** (`token`) and a copy of the `user` object to persist the login session across page reloads.
*   **Chatbot Session**: The full `ConversationState` for a chat is stored in **Redis**.
*   **Data Ownership**:
    *   `spa-booking-api` **owns** all data in PostgreSQL.
    *   `chatbot` **owns** the conversation session data in Redis.
    *   `spa-booking-frontend` **owns** the local browser state (auth token).

### Data Flow Answers:

*   **When a customer books something, where is the data saved?**
    It is saved in the **PostgreSQL** database by the **`spa-booking-api`**.
*   **When the chatbot remembers the conversation, where is it saved?**
    The current state of the conversation is saved in **Redis** by the **`chatbot`** service.
*   **When RAG searches knowledge, where does the knowledge come from?**
    The knowledge comes from text documents that have been pre-processed, converted into vector embeddings, and stored in the **`pgvector`** table within the **PostgreSQL** database.

---

# PART 7: ONE COMPLETE END-TO-END EXAMPLE

**User Input**: `"Book a 60-minute Full Body Massage tomorrow at Shinjuku for 2 people."`

1.  **NLU (`nlu.py`)**
    *   **Input**: The string above.
    *   **Output**: `NLUResult`
        *   `intent`: `CREATE_BOOKING`
        *   `entities`:
            *   `DURATION`: 60
            *   `COURSE_ID`: `{"courseId": fbm_id, "name": "Full Body Massage"}` (assuming it's a known course)
            *   `DATE`: `"2026-08-12"`
            *   `SHOP_ID`: `{"shopId": shinjuku_id, "shopName": "Shinjuku"}`
            *   `NUMBER_OF_PEOPLE`: 2

2.  **State Update (`chat_endpoint.py`)**
    *   The `ChatEndpoint` applies these entities to the `booking_context`.
    *   **Data**: `ConversationState.booking_context` now contains all the extracted values.

3.  **Policy Decision (`policy.py`)**
    *   `_next_booking_step` is called. It checks the sequence of required slots.
    *   It finds that `start_time` is the next missing slot.
    *   It checks the prerequisite for finding `start_time`: `searchAvailableSlots` tool must be run.
    *   **Output**: `PolicyDecision(action=RUN_TOOL, tool='search_available_slots')`.

4.  **Tool Execution (`search_tools.py`)**
    *   `ChatEndpoint` executes the `SearchAvailableSlotsTool`.
    *   **Input**: `SearchAvailableSlotsRequest` built from the `booking_context`.
    *   The tool makes an HTTP call.
    *   **Data Out**: `GET /api/shops/{shinjuku_id}/available-slots?date=2026-08-12&duration=60&numberOfPeople=2`

5.  **Booking API (`availability_service.py`)**
    *   The API receives the request. The `AvailabilityService` queries **PostgreSQL**, checking `TherapistShift` and existing `Booking` tables to find free slots.
    *   **Output**: A JSON list of available time strings: `["10:00", "11:30", "14:00", ...]`.

6.  **Chatbot Response (`chat_endpoint.py`)**
    *   The tool receives the list of times.
    *   The `ChatEndpoint` formats this into a `ChatResponse`.
    *   **Data Out**:
        *   `message`: "Here are the available times: 10:00, 11:30, 14:00. Please choose a start time."
        *   `phase`: `SEARCHING_SLOTS`
        *   `data`: `{ "available_times": ["10:00", "11:30", "14:00"] }`

7.  **Frontend Rendering (`ChatWindow.tsx`)**
    *   The frontend receives the `ChatResponse`.
    *   It renders the bot's message.
    *   Because the `phase` is `SEARCHING_SLOTS`, it also renders the `TimePicker.tsx` component, displaying the available times as clickable buttons.

---

# PART 8: WHAT CHANGES WHEN I MODIFY SOMETHING?

### Dependency Map

```text
┌────────────────┐   ┌───────────┐   ┌───────────┐
│   Frontend     │ → │  Chatbot  │ → │ Booking API│
│ (React/Next.js)│   │ (FastAPI) │   │  (Flask)   │
└────────────────┘   └───────────┘   └─────┬─────┘
                                           │
                                     ┌─────▼─────┐
                                     │ Databases │
                                     │(PG/Redis) │
                                     └───────────┘
```

*   **If I modify `chatbot/nlu/...`**:
    *   **Impact**: High impact on chatbot accuracy, low risk to system stability.
    *   **What changes?**: How the chatbot understands user messages will change. It could lead to incorrect intent classification or entity extraction. This would cause the **Dialogue Policy** to make the wrong decisions, but it won't crash the server. The **Frontend** and **Booking API** are completely unaffected.

*   **If I modify `chatbot/app/chat_endpoint.py`**:
    *   **Impact**: Very high risk. This is the central orchestrator.
    *   **What changes?**: The entire pipeline of how a message is processed could change. A bug here could break the entire chatbot service. It could affect how state is loaded/saved, how tools are called, or how the final response is formatted. **Frontend** would receive malformed responses. **Booking API** is unaffected.

*   **If I modify `spa-booking-api/app/services/...`**:
    *   **Impact**: Very high risk. This is the core business logic.
    *   **What changes?**: The fundamental rules of the business will change. A bug in `BookingService` could lead to double bookings, incorrect pricing, or data corruption in the **PostgreSQL Database**. Both the **Frontend** (using the GUI) and the **Chatbot** (via its tools) would be affected because both are clients to this API.

*   **If I modify `spa-booking-frontend/components/chatbot/ChatWindow.tsx`**:
    *   **Impact**: Purely visual. Low risk to backend systems.
    *   **What changes?**: How the chat conversation is displayed to the user will change. It could be a UI bug or an improvement. It has zero effect on the **Chatbot** or **Booking API** backends, as long as it still correctly calls the `useChat` hook's functions.

---

# PART 9: STARTUP

Based on the code and standard practices:

**1. Start Databases (Docker)**
*   **Command**: `docker-compose up -d` (or similar)
*   **What it does**: Starts the PostgreSQL and Redis containers.

**2. Start Booking API (Terminal 1)**
*   **Command**: `cd spa-booking-api && python run.py`
*   **What it does**: Starts the Flask development server.
*   **Listens on**: `http://localhost:5000`

**3. Start Chatbot (Terminal 2)**
*   **Command**: `cd chatbot && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (or similar, based on `app.main`)
*   **What it does**: Starts the FastAPI development server.
*   **Listens on**: `http://localhost:8000`

**4. Start Frontend (Terminal 3)**
*   **Command**: `cd spa-booking-frontend && npm run dev`
*   **What it does**: Starts the Next.js development server.
*   **Listens on**: `http://localhost:3000`

### Service Dependencies:

*   **Normal website browsing (no booking)**: Frontend only.
*   **GUI booking**: Frontend, Booking API, PostgreSQL.
*   **Chatbot (basic conversation)**: Frontend, Chatbot, Redis.
*   **Chatbot (that can actually book)**: Frontend, Chatbot, Redis, Booking API, PostgreSQL.
*   **Chatbot (with RAG/FAQ)**: All of the above, plus `pgvector` must be enabled and populated in PostgreSQL.
*   **Background Tasks**: Celery is not present in the inspected code. If it were, it would be another service to start.

---

# PART 10: THE 10 THINGS I MUST UNDERSTAND

1.  **Three Separate Applications**: The system is not a monolith. The Frontend, Booking API, and Chatbot are distinct applications that communicate over HTTP.
2.  **Booking API is the Source of Truth**: The Flask `spa-booking-api` owns all business logic and persistent data. Everything else is a client to it.
3.  **Chatbot is a Smart Translator, Not a Business Engine**: The `chatbot`'s job is to translate human language into structured API calls to the Booking API. It doesn't know *how* to check availability; it only knows *how to ask* the Booking API to do it.
4.  **State is Segregated**: Persistent business state is in **PostgreSQL**. Temporary conversation state is in **Redis**. Ephemeral UI state is in the **Frontend**.
5.  **The Chatbot is a Pipeline**: A user message goes through a strict sequence: NLU → Policy → Slot Filling → Tool Execution → Response.
6.  **The Dialogue Policy is Rule-Based**: The chatbot's conversational flow is determined by a hardcoded decision tree in `policy.py`, not by a large language model.
7.  **Tools are API Wrappers**: The "tools" the chatbot uses are just typed Python classes that make HTTP calls to the Booking API.
8.  **The Frontend has Two Ways to Book**: A user can use the **GUI** (`TherapistGantt`) or the **Chatbot**. Both paths ultimately hit the same Booking API endpoints.
9.  **NLU Knowledge is Dynamic**: The chatbot can update its understanding of the world (e.g., the courses available at a specific shop) in the middle of a conversation by calling a tool and feeding the results back into its NLU module.
10. **Services and Blueprints Organize the Booking API**: The Booking API is not a single file of routes. It's cleanly organized by domain into Blueprints (controllers) and Services (business logic).

---

# PART 11: WHAT TO READ NEXT

This provides a structured path to learning the codebase, moving from the highest level to the most specific.

**STEP 1: Understand the API Contracts**
*   **What**: Before anything else, understand the "language" the services speak.
*   **Files**:
    *   `spa-booking-api/app/blueprints/` (browse the `routes.py` files to see the endpoints).
    *   `chatbot/models.py` and `chatbot/tools/search_tools.py`/`write_tools.py` (look at the `*Request` and `*Response` Pydantic models).
*   **Why**: This shows you what each application expects as input and provides as output. It's the most stable, high-level view of the system's interactions.

**STEP 2: Understand the End-to-End GUI Booking Flow**
*   **What**: Trace a simple booking made without the chatbot. This is simpler and reveals the core business logic first.
*   **Files**:
    1.  `spa-booking-frontend/app/dashboard/page.tsx` (the start)
    2.  `spa-booking-frontend/lib/api.ts` (how the frontend calls the backend)
    3.  `spa-booking-api/app/blueprints/public/routes.py` (receiving the request)
    4.  `spa-booking-api/app/services/availability_service.py` (the core logic)
    5.  `spa-booking-api/app/models/Booking.py` & `Therapist.py` (the data schema)
*   **Why**: This path isolates the core business logic in the `spa-booking-api` without the added complexity of the chatbot.

**STEP 3: Understand the Chatbot Pipeline**
*   **What**: Now, trace how the chatbot achieves the same goal by following its internal pipeline.
*   **Files**:
    1.  `chatbot/app/chat_endpoint.py` (focus on the `process_message` method)
    2.  `chatbot/nlu/nlu.py` (the first step)
    3.  `chatbot/conversation/policy.py` (the second step)
    4.  `chatbot/conversation/slot_filling.py` (the third step)
    5.  `chatbot/tools/search_tools.py` (the final action step)
*   **Why**: This shows you how the conversational layer is built on top of the core API. You will see how it translates language into the same API calls the GUI makes.

**STEP 4: Understand State Management**
*   **What**: See how state is persisted in different parts of the system.
*   **Files**:
    1.  `spa-booking-frontend/contexts/AuthContext.tsx` (frontend login state in `localStorage`).
    2.  `chatbot/session/store.py` (chatbot conversation state in Redis).
    3.  `spa-booking-api/app/extensions.py` (how the `db` object is created and used to persist to PostgreSQL).
*   **Why**: Understanding where data lives and for how long is crucial to understanding the system's reliability and behavior.

**STEP 5: Then read individual files**
After completing these steps, you will have a strong mental model. You can then pick any individual file, and you will understand how it fits into the larger picture.
