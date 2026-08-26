# Step 1: Architecture Overview (Corrected)

This document provides a high-level, and now corrected, overview of the AI Massage Booking project's architecture.

## Overall Architecture

The system is a sophisticated, multi-service application, not a simple three-tier monolith. It consists of three primary, independent services:

1.  **Frontend (`spa-booking-frontend`)**: A web-based user interface.
2.  **Booking API (`spa-booking-api`)**: A backend service dedicated to managing spa-related business logic (bookings, users, etc.).
3.  **Chatbot Service (`chatbot`)**: An advanced, standalone AI service that manages conversational state, natural language understanding (NLU), and tool orchestration. This is the "brain" of the operation.

These services communicate with each other over HTTP, making it a distributed system.

## Major Components and Folder Responsibilities

*   ### `spa-booking-frontend/`
    *   **Responsibility**: Provides the user-facing chat and booking management interface. It is a "dumb" client that primarily renders state provided by the backend services.
    *   **Technologies**: A modern JavaScript framework (e.g., React).

*   ### `spa-booking-api/`
    *   **Responsibility**: Acts as the authoritative source for all business data. It handles creating, reading, updating, and deleting all data related to the spa business itself. It does **not** handle chat logic.
    *   **Key Sub-directories**:
        *   `app/models/`: Database schema (SQLAlchemy).
        *   `app/blueprints/`: API endpoint definitions (Flask Blueprints).
        *   `app/services/`: Core business logic (e.g., booking creation, availability calculation).
        *   `app/tasks.py`: Asynchronous background jobs (Celery).

*   ### `chatbot/`
    *   **Responsibility**: This is a complete, stateful AI agent service. It is responsible for the entire lifecycle of a user conversation.
    *   **Key Sub-directories**:
        *   `nlu/`: Natural Language Understanding components.
        *   `tools/`: A set of "tools" the chatbot can use. These are functions that often wrap API calls to the `spa-booking-api`. For example, a `check_availability` tool would call the booking API's availability endpoint.
        *   `session/`: Manages the conversational session, keeping track of the user's state over time.
        *   `gateway/`: The entry point for incoming messages.
        *   `prompts/`: Contains the sophisticated prompts that define the AI's behavior and personality. This is a critical component.

## Data Flow (Corrected)

The interaction is orchestrated by the Chatbot service, which acts as a central controller.

1.  User sends a message from the **Frontend** to an endpoint on the **Chatbot Service**.
2.  The **Chatbot Service's Gateway** receives the message.
3.  The **Session Manager** retrieves the user's conversation history.
4.  The **NLU** component processes the new message to extract intent and entities.
5.  The core agent logic, guided by **Prompts**, decides what to do next. It might be to respond with text or to use a **Tool**.
6.  If a tool is chosen (e.g., `book_appointment`), the chatbot executes the tool's function.
7.  The tool function makes a specific, non-conversational API call to the **Booking API** (e.g., `POST /api/bookings`).
8.  The **Booking API** performs the requested action (e.g., creates a booking in the database) and returns a result to the **Chatbot Service**.
9.  The chatbot receives the tool's result, formulates a natural language response for the user, and sends it back to the **Frontend**.
10. The **Frontend** displays the chatbot's response.

## Top 10 Most Important Files (Corrected)

1.  **`chatbot/main.py`**: The main entry point for the entire Chatbot service.
2.  **`chatbot/prompts/` (Directory)**: This directory is critical. The files within define the AI's core logic, personality, and how it uses tools.
3.  **`chatbot/tools/` (Directory)**: The functions in this directory are the bridge between the AI and the `spa-booking-api`.
4.  **`chatbot/session/manager.py`**: Manages the state of each user's conversation.
5.  **`chatbot/nlu/` (Directory)**: Responsible for interpreting user messages.
6.  **`spa-booking-api/app/blueprints/` (Directory)**: Defines all the concrete actions the `spa-booking-api` can perform.
7.  **`spa-booking-api/app/services/` (Directory)**: The implementation of the business logic for the booking system.
8.  **`spa-booking-api/app/models/` (Directory)**: The database schema, the single source of truth for data.
9.  **`spa-booking-frontend/src/App.js`**: The main entry point for the user-facing application.
10. **`docker-compose.yml`** (if present, otherwise `manage.py`/`run.py` scripts): Defines how the different services are run and connected.

## ASCII Architecture Diagram (Corrected)

```
+------------------------+
|   User (Web Browser)   |
+------------------------+
           |
           v
+------------------------+      +---------------------+
| spa-booking-frontend   |----->|   Chatbot Service   |
| (UI)                   |      |    (Orchestrator)   |
+------------------------+      +----------+----------+
                                           | (Tools via HTTP)
                                           v
                                +---------------------+
                                |   spa-booking-api   |
                                | (Business Logic/DB) |
                                +----------+----------+
                                           |
                                           v
                                +---------------------+
                                |      Database       |
                                +---------------------+
```
