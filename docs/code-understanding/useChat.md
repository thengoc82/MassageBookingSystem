
# `spa-booking-frontend/lib/hooks/useChat.ts`

## 1. Purpose

This file defines the `useChat` custom hook, which is the core engine of the entire chatbot system. It encapsulates all the logic for managing a conversation: maintaining the message history, handling user input, communicating with the backend chatbot API, and synchronizing the frontend's understanding of the booking state with the backend's state machine. It is a headless component; it has no UI of its own but provides all the necessary state and functions for a UI component like `ChatWindow` to operate.

## 2. Where it fits

This hook is the central controller for the chat functionality. It sits between the UI (`ChatWindow`) and the network (the Chatbot API).

```text
`ChatWindow` component
    ↓
Calls `useChat()` hook
    ↓
Hook provides state (`messages`, `bookingState`) and functions (`sendMessage`)
    ↓
`ChatWindow` renders the state and calls functions on user interaction
    ↓
`sendMessage` function within the hook calls `api.chat.sendMessage()`
    ↓
Backend Chatbot API
```

## 3. Inputs

*   **`userId: string | null`**: The ID of the logged-in user, passed in from the `ChatWindow` component (which gets it from `AuthContext`). This is used to associate the conversation with a user on the backend.

## 4. Outputs

This hook doesn't render anything. It returns an object containing the state and functions that the UI component needs to render the chat and handle interactions.

*   **State**:
    *   `messages`: The array of all messages in the current conversation.
    *   `input`, `setInput`: The controlled input state for the message box.
    *   `isLoading`: A boolean indicating if a backend request is in flight.
    *   `error`: An error message string if an API call fails.
    *   `pendingConfirmation`: A boolean that is true when the bot is waiting for a "yes/no" confirmation from the user.
    *   `bookingState`: The rich object representing the current state of the booking being constructed (e.g., `shopId`, `date`, `time`).
    *   `currentPhase`: The current phase of the conversation, as dictated by the backend (e.g., `SELECTING_DATE`).
    *   `isBookingCompleted`: A flag that becomes true when the booking is finalized.
*   **Functions**:
    *   `sendMessage`: The primary function to send a user's message to the backend.
    *   `confirm`, `cancel`: Helper functions that call `sendMessage` with "yes" or "no".
    *   `updateMessage`: A function to modify an existing message in the `messages` array (e.g., to attach a user's selection to a bot's question).
    *   `restartBooking`: A function to reset the chat state and start a new booking conversation.

## 5. Important functions/classes

```text
useChat(userId)
    ↓
Purpose
    ↓
    To encapsulate all state and logic for a chat conversation.
    ↓
Input
    ↓
    - `userId`: The ID of the currently authenticated user.
    ↓
What it does
    ↓
    1.  **State Management**: Initializes all the core state for the chat (`messages`, `isLoading`, `bookingState`, etc.) using `useState`. It also uses `useRef` for `sessionId` to ensure it persists across re-renders without causing them.
    2.  **Starts Conversation**: A `useEffect` hook calls `startConversation()` on the initial mount to get the first greeting message from the bot.
    3.  **Defines `sendMessage`**: This is the main workhorse function. It adds the user's message to the state, sets loading to true, constructs the request payload, calls the backend API, and processes the response using `handleBackendResponse`.
    4.  **Defines `handleBackendResponse`**: A crucial helper function that takes the raw response from the backend API and updates all the relevant state variables (`messages`, `bookingState`, `currentPhase`, `pendingConfirmation`, etc.).
    5.  **Returns Public Interface**: It returns a large object containing all the state and functions that the UI component (`ChatWindow`) needs to function.
    ↓
Output
    ↓
    An object containing the state of the chat and functions to interact with it.
```

```text
sendMessage(text, payload)
    ↓
Purpose
    ↓
    To send a message to the backend and handle the full request/response cycle.
    ↓
Input
    ↓
    - `text`: The user's text message.
    - `payload`: (Optional) An object with extra data to be sent to the backend, such as `packageSelection`.
    ↓
What it does
    ↓
    1.  Adds the user's message to the `messages` state immediately for a responsive UI.
    2.  Sets `isLoading` to `true`.
    3.  Builds the `ChatRequest` body.
    4.  Calls `api.chat.sendMessage(body)`.
    5.  On success, calls `handleBackendResponse` with the API response data.
    6.  On failure, sets an error message.
    7.  Finally, sets `isLoading` to `false`.
    ↓
Output
    ↓
    None (it updates state via side effects).
```

## 6. Execution flow

1.  The `useChat` hook is called by `ChatWindow`.
2.  The `useEffect` runs, calling `startConversation`. This function sends a "start" message to the backend.
3.  The backend responds with a greeting. `handleBackendResponse` processes this, adding the greeting to `messages`. The UI displays the greeting.
4.  The user types a message and the UI calls `sendMessage(text)`.
5.  `sendMessage` optimistically adds the user's message to the `messages` array and shows a loading state.
6.  `sendMessage` sends the request to the backend API.
7.  The backend's Natural Language Understanding (NLU) processes the text, updates its internal state machine, and formulates a response. This response includes the next message, the new `phase` of the conversation, and the updated `booking_state`.
8.  The frontend receives the response. `handleBackendResponse` is called.
9.  `handleBackendResponse` updates the frontend's state: it adds the bot's new message to `messages`, updates `currentPhase`, and synchronizes `bookingState`.
10. The UI (`ChatWindow`) re-renders based on this new state, showing the new message and potentially new interactive components or an updated booking summary.
11. This cycle continues until the `phase` is `BOOKING_COMPLETE`.

## 7. Dependencies

```text
api.chat.sendMessage (from "@/lib/api")
    ↓
    The specific API client function used to communicate with the backend chatbot service. This is the only network dependency.

BookingState, ChatRequest, ChatResponse, ConversationPhase (from "@/lib/types")
    ↓
    TypeScript types that define the data contract between this hook and the backend API. They ensure that the data being sent and received matches the expected structure.
```

## 8. Relationship with other files

```text
This file (lib/hooks/useChat.ts)
 ├── is consumed by → components/chatbot/ChatWindow.tsx
 ├── calls the API via → lib/api.ts
 └── uses types from → lib/types.ts
```

## 9. Important state/data

*   **`sessionId: useRef<string | null>`**: A critical piece of data. It's generated once per conversation and sent with every API request. The backend uses this ID to maintain the context of the ongoing conversation. Using `useRef` is deliberate; it ensures the ID is stable and doesn't get reset if the component re-renders.
*   **`messages: Message[]`**: The chronological history of the conversation. It's the source of truth for what the user sees in the chat log.
*   **`bookingState: BookingState | null`**: A mirror of the backend's understanding of the booking being built. This object is what powers the "Current Booking" summary in the UI. It gets completely replaced with the backend's version on every response, ensuring frontend and backend are always in sync.
*   **`currentPhase: ConversationPhase`**: A state machine variable. It tells the frontend what stage the conversation is in, which `ChatWindow` uses to decide which interactive components to display.

## 10. What I should understand

1.  **This is the Brain:** All significant logic for the chatbot lives here. The UI components are comparatively "dumb" and simply render the state provided by this hook.
2.  **Backend-Driven State Machine:** The frontend does not decide what the next step in the conversation is. It sends a message, and the backend's response dictates the new `currentPhase` and `bookingState`. This hook's job is to faithfully apply the backend's state to the frontend.
3.  **Optimistic UI Updates:** When a user sends a message, `sendMessage` immediately adds it to the `messages` array before waiting for the API response. This makes the UI feel fast and responsive.
4.  **Synchronization is Key:** The `handleBackendResponse` function is the synchronization point. It ensures that after every turn, the frontend's `bookingState` and `currentPhase` perfectly match what the backend has determined.
5.  **Session Management is Simple but Effective:** A random `sessionId` is generated and stored in a ref. As long as the user doesn't refresh the page (which would re-mount the `ChatWindow` and re-run the hook from scratch), this session ID persists, allowing for a continuous conversation.

## 11. Potential confusing parts

*   **Who owns the state?**: While the frontend holds state like `bookingState`, it's not the owner. It's a temporary copy. The backend is the true owner of the conversation state. The frontend sends user input, and the backend returns the *new* state that the frontend must adopt.
*   **`updateMessage` vs. `sendMessage`**: `sendMessage` is for advancing the conversation with a new turn. `updateMessage` is a clever utility for modifying a *previous* message in the log. This is used when a user makes a selection in an interactive component (like `TimePicker`); the selection is attached to the bot's *question* message before a new confirmation message is sent.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the headless engine of a stateful conversation.** It acts as the central nervous system for the chatbot, maintaining a short-term memory of the conversation (`messages` and `sessionId`) and constantly synchronizing its view of the world (`bookingState` and `currentPhase`) with the backend's authoritative state machine. It takes simple commands from the UI (like "send this text") and translates them into structured API calls, then unpacks the complex responses to provide the UI with exactly the state it needs to render the next step.
