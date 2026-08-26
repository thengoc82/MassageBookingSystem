# Data Flow

This document describes the primary data flows within the AI Massage Booking system.

## Main Request/Response Flow (Booking a Massage)

This flow describes a typical conversation where a user books a massage.

1.  **User Sends Message**: The user sends a message to the `POST /chat` endpoint in `[[chatbot/app/chat_endpoint.py]]`.
2.  **State Retrieval**: The system retrieves the current `ConversationState` for the user's `session_id` from the `[[RedisSessionStore]]`.
3.  **NLU Processing**: The `[[chatbot/nlu/nlu.py]]` module processes the message to extract an `Intent` and any `Entities` (like a shop name, date, or time).
4.  **Dialogue Policy Decision**: The `[[chatbot/conversation/policy.py]]` receives the `ConversationState` and the `NLUResult`. It decides on the next `Action` to take (e.g., `ASK_SLOT`, `RUN_TOOL`).
5.  **Slot Filling**: If the policy decides to gather more information, the `[[chatbot/conversation/slot_filling.py]]` manager identifies the next required piece of information (slot) and prompts the user for it.
6.  **Tool Execution**:
    *   If enough information is gathered to search for something (e.g., shops, courses, time slots), the policy decides to `RUN_TOOL`.
    *   The corresponding tool from `[[chatbot/tools/search_tools.py]]` is executed.
    *   The tool makes an HTTP request via the `[[chatbot/gateway/client.py]]` to the external booking API.
    *   The results are stored in the `ConversationState`.
7.  **Confirmation & Write Action**:
    *   Once all booking details are collected, the policy moves to `CONFIRM_ACTION`. The user is asked to confirm the booking.
    *   Upon user confirmation, the policy decides `EXECUTE_WRITE_ACTION`.
    *   The `CreateBookingTool` from `[[chatbot/tools/write_tools.py]]` is executed, sending a request to the external API to create the booking.
8.  **State Update**: The final `ConversationState` is saved back to the `[[RedisSessionStore]]`.
9.  **Response to User**: A `ChatResponse` is sent back to the user with the chatbot's message, the current conversation phase, and any relevant data (like a list of shops or available times).

## Data and State Management

- **`[[chatbot/conversation/state.py]]`**: Defines the core data structures that hold the state of the conversation. This includes:
    - `ConversationState`: The main container for all session data.
    - `BookingContext`: A Pydantic model that stores the details of the booking being constructed (e.g., `shop_id`, `course_id`, `date`).
    - `RecentToolResults`: Caches the results of recent tool calls (e.g., the last list of shops fetched).
- **`[[RedisSessionStore]]` (`chatbot/session/store.py`)**: Serializes the `ConversationState` and stores it in Redis with a key based on the user's `session_id`. This makes the chat endpoint stateless.

## FAQ / RAG Flow

1.  **User Asks a Question**: The user asks a general question (e.g., "What are your opening hours?").
2.  **NLU and Policy**: The NLU identifies this as an `Intent.FAQ` or similar, and the policy decides to `ANSWER_FAQ`.
3.  **Knowledge Service Query**: The `_faq_search` method in `[[chatbot/app/chat_endpoint.py]]` is called.
4.  **Embedding**: The `[[chatbot/knowledge/embedding_service.py]]` converts the user's question into a vector embedding.
5.  **Vector Search**: The `[[chatbot/knowledge/pgvector_store.py]]` searches the PostgreSQL database for the most similar document chunks based on the query vector.
6.  **Response Generation**: The content of the top-matching document chunk is returned to the user as the answer.
