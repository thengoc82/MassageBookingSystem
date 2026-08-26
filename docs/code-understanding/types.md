
# `spa-booking-frontend/lib/types.ts`

## 1. Purpose

This file defines the core TypeScript types and interfaces that govern the data structures used within the chatbot conversation. It acts as a centralized "dictionary" or "schema" for the data exchanged between the frontend UI (`ChatWindow`), the frontend logic (`useChat` hook), and the backend chatbot API. Its primary purpose is to ensure type safety and a consistent data contract across different parts of the chatbot system.

## 2. Where it fits

This file doesn't execute any code. It is a collection of type definitions that are imported and used by other files at development/compile time.

```text
Backend Chatbot API
    ↓ (sends a `ChatResponse`)
`useChat` hook
    ↓ (uses `ChatResponse` and `BookingState` types)
`ChatWindow` component
    ↓ (receives `BookingState` and `ConversationPhase` as props/state)
Renders UI
```

## 3. Inputs

This file has no inputs. It is a static file containing only type definitions.

## 4. Outputs

This file's outputs are TypeScript types that are used by other files to type-check their variables, function parameters, and return values. The most important types it exports are:

*   `BookingState`: The structure of the booking object as it's being built by the chatbot.
*   `ConversationPhase`: A string literal type that defines all possible stages of the conversation.
*   `ChatRequest`: The shape of the object sent *to* the backend API.
*   `ChatResponse`: The shape of the object received *from* the backend API.

## 5. Important functions/classes

This file does not contain functions or classes, only type and interface definitions.

```text
interface BookingState
    ↓
Purpose
    ↓
    To define the structure of the front-end's knowledge about the booking in progress. This object is synchronized with the backend on every turn of the conversation. It drives the "Current Booking" summary UI.
    ↓
Structure
    ↓
    - `shopId?`, `shopName?`: Details of the selected shop.
    - `courseId?`, `courseName?`: Details of the selected main course.
    - `date?`, `time?`, `duration?`, `guests?`: Core booking parameters.
    - `therapistId?`, `therapistName?`: Details of the selected therapist.
    - `phone?`, `bookingCode?`, `status?`: Customer and finalization details.
    - `review?`, `confirm?`: Boolean flags to indicate the conversation is in a final review or confirmation step.
```

```text
const ConversationPhase
    ↓
Purpose
    ↓
    To define a fixed set of all possible states (or "phases") that the conversation can be in. This acts as a state machine definition, ensuring that the `currentPhase` variable can only be one of these known strings.
    ↓
Structure
    ↓
    - An object where keys and values are the same string literals (e.g., `GREETING: "greeting"`). This is a common TypeScript pattern for creating an enum-like object.
    - Example phases include `GREETING`, `COLLECTING_DURATION`, `SELECTING_DATE`, `SEARCHING_SLOTS`, `REQUESTING_REVIEW`, `BOOKING_COMPLETE`.
```

```text
interface ChatRequest / ChatResponse
    ↓
Purpose
    ↓
    To define the strict data contract for communication with the backend chatbot API.
    ↓
Structure
    ↓
    - `ChatRequest`: Defines what the frontend must send, including `message`, `session_id`, and optional `user_id` and `packageSelection` data.
    - `ChatResponse`: Defines what the frontend can expect to receive, including `success`, `message`, `session_id`, the current `phase`, the synchronized `booking_state`, and optional `data` or `error` payloads.
```

## 6. Execution flow

This file is not executed at runtime. It is used by the TypeScript compiler to enforce type checking on other files that import its types.

For example, in `useChat.ts`:
1.  The `bookingState` is declared as `useState<BookingState | null>(null)`. TypeScript ensures that only data matching the `BookingState` interface (or `null`) can be assigned to it.
2.  The `handleBackendResponse` function takes a parameter `data: ChatResponse`. TypeScript ensures the code inside this function can safely access properties like `data.phase` and `data.booking_state` because it knows they will exist on the `ChatResponse` object.
3.  The `currentPhase` is typed as `ConversationPhase`, preventing it from being set to an arbitrary, unknown string.

## 7. Dependencies

This file has no dependencies. It is a foundational file.

## 8. Relationship with other files

```text
This file (lib/types.ts)
 └── is imported by → lib/hooks/useChat.ts (to type its state and API calls)
 └── is imported by → components/chatbot/ChatWindow.tsx (to understand the `currentPhase` and `bookingState`)
```
Other component files, such as those for interactive options, may also import these types to define their props.

## 9. Important state/data

This file *defines the shape* of important state, but does not hold any state itself. The most important data structures it defines are:

*   **`BookingState`**: This is the blueprint for the primary data object that tracks the user's progress through the booking flow.
*   **`ConversationPhase`**: This defines the vocabulary for the conversational state machine.
*   **`ChatRequest` / `ChatResponse`**: These interfaces are the formal contract for the API, which is the most critical boundary in the system.

## 10. What I should understand

1.  **This is the "Data Dictionary":** This file is the single source of truth for the *shape* of the data flowing through the chatbot system.
2.  **It Enforces the API Contract:** The `ChatRequest` and `ChatResponse` interfaces are the most important part of this file. They ensure that the frontend and backend are speaking the same language. Any breaking change in the API response should be reflected here first.
3.  **It Defines the State Machine:** The `ConversationPhase` object explicitly lists every possible step in the conversation. This makes the code in `ChatWindow` (which checks the phase) and `useChat` (which sets the phase) much more robust and predictable.
4.  **It's a Development Tool:** The value of this file is primarily for the developer at compile time. It prevents bugs by catching type mismatches early and provides autocompletion and clarity when working with the data structures.

## 11. Potential confusing parts

*   **`ConversationPhase` Object vs. Type:** The file exports both a `const ConversationPhase` object and a `type ConversationPhase`.
    *   The `const` is a runtime object that holds the string values (e.g., `ConversationPhase.GREETING` evaluates to `"greeting"`).
    *   The `type` is a TypeScript "union type" derived from the object's values (`"greeting" | "collecting_people" | ...`). This is a common and powerful TypeScript pattern for creating string-based enums that are easy to work with.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the blueprint for the chatbot's language and memory.** It doesn't do anything on its own, but it provides the strict grammatical rules (`ChatRequest`, `ChatResponse`) and vocabulary (`ConversationPhase`, `BookingState`) that allow the different parts of the system—the UI, the frontend logic, and the backend API—to communicate with each other clearly and without misunderstanding.
