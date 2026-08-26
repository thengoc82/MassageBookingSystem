# Step 2: Reading Roadmap (Corrected)

This document provides a recommended reading order for understanding the AI Massage Booking project, based on the corrected architecture. We will start with the most fundamental component—the data—and work our way up to the AI.

## 1. `spa-booking-api/app/models/` (Directory)

*   **Why read now?**: This is the single source of truth for the data that runs the entire business. Every other piece of code exists to manipulate or display the data defined here. Understanding the `User`, `Booking`, and `Therapist` models is non-negotiable.
*   **Prerequisites**: Basic understanding of SQL databases and ORMs (like SQLAlchemy).
*   **Concepts you will learn**:
    *   The core data structures of the application.
    *   The relationships and constraints between different data entities.
    *   This is the "domain model" of the spa business.

## 2. `spa-booking-api/app/blueprints/` (Directory): The API Contract

*   **Why read now?**: This directory defines the complete set of actions the system can perform. It's the "contract" that the AI and frontend will use. We now know the key endpoints are split by resource, for example:
    *   `public/slots.py`: Exposes `GET /shops/<id>/available-slots` which is crucial for the booking process.
    *   `bookings/routes.py`: Handles creating and managing bookings via `POST /bookings` and other endpoints.
*   **Prerequisites**: Understanding of the models. Basic knowledge of REST APIs.
*   **Concepts you will learn**:
    *   The complete set of capabilities of the booking system.
    *   The specific inputs and outputs for each API endpoint.
    *   How the system is organized by resources (`shops`, `bookings`, `therapists`, etc.).

## 3. `spa-booking-api/app/services/` (Directory)

*   **Why read now?**: This is the implementation of the business logic. If a blueprint defines *that* you can create a booking, the service file defines *how*—checking for conflicts, validating data, etc.
*   **Prerequisites**: Understanding of models and blueprints.
*   **Concepts you will learn**:
    *   The core algorithms of the booking system (e.g., how availability is calculated).
    *   The detailed, step-by-step logic for all business operations.

## 4. `chatbot/tools/` (Directory)

*   **Why read now?**: This is the crucial bridge between the AI and the booking API. Each file in here is likely a Python function that calls one of the API endpoints you learned about in the `spa-booking-api/app/blueprints/` step.
*   **Prerequisites**: Understanding of the `spa-booking-api`'s blueprints.
*   **Concepts you will learn**:
    *   How the abstract idea of "booking a massage" is translated into a concrete API call.
    *   The exact functions the chatbot has at its disposal to interact with the real world.

## 5. `chatbot/prompts/` (Directory)

*   **Why read now?**: This is the "brain" of the AI. These are not simple files; they are carefully crafted instruction sets that tell the AI how to behave, what its personality is, and most importantly, how and when to use the `tools`.
*   **Prerequisites**: Understanding of the `tools` available to the chatbot.
*   **Concepts you will learn**:
    *   The core reasoning process of the AI agent.
    *   How the AI makes decisions about which tool to use based on the conversation.
    *   The "guardrails" and instructions that define the AI's behavior.

## 6. `chatbot/session/store.py`

*   **Why read now?**: This component gives the chatbot its "memory." It's responsible for loading and saving the history of a conversation so the AI has context.
*   **Prerequisites**: General understanding of the chatbot's role.
*   **Concepts you will learn**:
    *   How conversational state is persisted and retrieved.
    *   The mechanism for how the chatbot maintains context across multiple user messages.

## 7. `spa-booking-frontend/` (Directory)

*   **Why read now?**: With a full understanding of the backend and AI, you can now see how it's all presented to the user. The frontend is the final layer that consumes the services you've learned about.
*   **Prerequisites**: Understanding of the `chatbot` service API.
*   **Concepts you will learn**:
    *   How the conversational interface is built.
    *   How the frontend communicates with the chatbot service.
    *   How application state is managed on the client side.
