
# `spa-booking-frontend/components/chatbot/ChatWindow.tsx`

## 1. Purpose

This file is the main user interface for the chatbot. It is responsible for rendering the entire chat conversation, including user messages, bot responses, and custom interactive components for things like selecting a time, choosing a package, or confirming a booking. It orchestrates the entire visual and interactive experience of the chatbot, powered by the logic from the `useChat` hook.

## 2. Where it fits

This component is rendered by `ChatWidget` when the user decides to open the chat.

```text
`ChatWidget`
    ↓
`isOpen` state becomes true
    ↓
Renders this file (`ChatWindow`)
    ↓
`useChat` hook is initialized, starting or continuing the conversation
    ↓
The conversation history (`messages`) is rendered
    ↓
User interacts with the chat input or custom components
    ↓
Interaction handlers (e.g., `handleSubmit`, `handleShopSelect`) call functions from `useChat` (e.g., `sendMessage`)
    ↓
`useChat` hook updates its state, causing `ChatWindow` to re-render with new messages/UI
```

## 3. Inputs

*   **Props**:
    *   `onClose: () => void`: A callback function passed from `ChatWidget`. It's called when the user clicks the "X" button to close the chat window.
*   **Context**:
    *   `useAuth()`: It consumes the `user` object from the authentication context to pass the `userId` to the `useChat` hook.
*   **Hook State (`useChat`)**: This is the primary input. The component de-structures dozens of state variables and functions from the `useChat` hook, including:
    *   `messages`: An array of message objects to be rendered.
    *   `input`, `setInput`: The current value of the text input and the function to change it.
    *   `sendMessage`: The function to send a new message to the backend.
    *   `isLoading`: A boolean to show a loading indicator.
    *   `bookingState`: An object representing the current state of the booking being built by the conversation.
    *   `currentPhase`: A string indicating the current stage of the conversation (e.g., `SELECTING_DATE`, `BOOKING_COMPLETE`).

## 4. Outputs

*   **A complete chat UI**: Renders the chat header, the scrollable message area, and the text input form.
*   **Calls to `onClose`**: Invokes the `onClose` prop when the close button is clicked.
*   **Calls to `useChat` functions**: It calls `sendMessage`, `confirm`, `cancel`, `updateMessage`, and other functions from the `useChat` hook in response to user actions. These calls are the primary way the UI communicates user intent back to the core chat logic.

## 5. Important functions/classes

```text
ChatWindow({ onClose })
    ↓
Purpose
    ↓
    To orchestrate the entire chatbot UI, manage local UI state (like which section is being edited), and connect user interactions to the chat logic hook.
    ↓
Input
    ↓
    - `onClose`: Function to close the window.
    ↓
What it does
    ↓
    1.  **Initializes Hooks**: Calls `useAuth()` to get the user and `useChat()` to get all chat-related state and functions.
    2.  **Manages UI State**: Uses `useState` for `editingSection`, which tracks which part of the `CurrentBooking` summary the user wants to change.
    3.  **Handles Scrolling**: Uses `useEffect` and `useRef` to automatically scroll the message list to the bottom when new messages arrive.
    4.  **Defines Interaction Handlers**: Contains numerous handler functions (`handleSubmit`, `handlePackageSelect`, `handleTimeConfirm`, etc.) that are passed as props to child components. These handlers translate UI events into calls to the `useChat` hook.
    5.  **Renders Dynamically**: Implements the `renderMessageContent` function, which contains complex logic to loop through messages and render special interactive components (`PackageOptions`, `TimePicker`, etc.) when the message `phase` requires them.
    6.  **Renders Layout**: Renders a two-column layout. The left column is the conversation, and the right column (`CurrentBooking`) appears when a booking is in progress to show a summary.
    ↓
Output
    ↓
    The fully interactive chat window interface.
```

```text
renderMessageContent()
    ↓
Purpose
    ↓
    To render the list of chat messages and conditionally inject interactive UI components based on the conversation's phase.
    ↓
Input
    ↓
    None (reads `messages` from the component's scope).
    ↓
What it does
    ↓
    1.  Maps over the `messages` array.
    2.  For each message, it renders the basic `ChatMessage`.
    3.  It then checks the `phase` of the message. If the phase matches a specific interactive stage (e.g., `SELECTING_PACKAGE`, `SEARCHING_SLOTS`), it renders the corresponding interactive component (`PackageOptions`, `TimePicker`, etc.) right below that message.
    ↓
Output
    ↓
    A list of React elements representing the full conversation history with interactive widgets included.
```

## 6. Execution flow

1.  `ChatWidget` renders `ChatWindow`.
2.  `ChatWindow` mounts. The `useChat` hook is called, which may trigger an initial `startConversation` API call.
3.  The initial messages (e.g., a greeting from the bot) are received and set in the `messages` state.
4.  The component renders the initial state: the header, an empty input box, and the greeting message from the bot. The `BookingProgress` sidebar is likely hidden at this stage.
5.  The user types a message and hits send, or clicks a button in an interactive component.
6.  The appropriate handler fires (e.g., `handleSubmit` or `handleShopSelect`).
7.  The handler calls `sendMessage()` from the `useChat` hook, passing the user's intent as a string.
8.  `useChat` adds the user's message to the `messages` list and sends the data to the backend API. `isLoading` becomes `true`.
9.  `ChatWindow` re-renders to show the user's message and a "typing..." indicator.
10. The backend responds. `useChat` processes the response, adding the bot's new message to the `messages` list and updating the `bookingState` and `currentPhase`. `isLoading` becomes `false`.
11. `ChatWindow` re-renders again. The `renderMessageContent` function now sees the new message and potentially a new `phase`, causing it to render a new interactive component (e.g., `DateOptions`). The `CurrentBooking` sidebar updates based on the new `bookingState`.
12. This cycle repeats, building the `bookingState` step-by-step until the conversation is complete.

## 7. Dependencies

```text
useChat (from "@/lib/hooks/useChat")
    ↓
    This is the most critical dependency. It's a custom hook that encapsulates ALL of the chatbot's business logic: managing the conversation state, communicating with the backend API, and handling the booking state machine. `ChatWindow` is a "view" that is almost entirely driven by this hook.

ChatMessage, ConfirmationButtons, PackageOptions, etc.
    ↓
    A suite of smaller, specialized components used to render different parts of the conversation. `ChatWindow` acts as an orchestrator, deciding which of these to render and when, based on the conversation phase.

CurrentBooking (from "./CurrentBooking")
    ↓
    A component displayed in the right-hand sidebar that shows a summary of the booking as it's being built.
```

## 8. Relationship with other files

```text
This file (components/chatbot/ChatWindow.tsx)
 ├── is rendered by → components/chatbot/ChatWidget.tsx
 ├── is powered by → lib/hooks/useChat.ts
 ├── renders many sub-components → ./ChatMessage.tsx, ./TimePicker.tsx, etc.
 └── renders → ./CurrentBooking.tsx (to show booking summary)
```

## 9. Important state/data

*   **All state from `useChat`**: The `messages` array, `bookingState` object, and `currentPhase` string are the most important pieces of data, as they dictate almost everything that is displayed.
*   **`editingSection: string | null`**: A piece of local UI state that controls which part of the `CurrentBooking` sidebar is currently being edited by the user. This allows a user to jump back to a previous step in the conversation.

## 10. What I should understand

1.  **It's an "Orchestrator" View:** This component's main job is not to *manage* state, but to *render* state provided by the `useChat` hook. It's a complex view that translates the `currentPhase` and `bookingState` into a rich, interactive UI.
2.  **Interactive Components are Phase-Driven:** The chatbot isn't just text. The rendering of complex UI widgets like `PackageOptions` or `TimePicker` is tied directly to the `phase` of a specific bot message. This is the core mechanism for making the bot interactive.
3.  **The Two-Column Layout is Conditional:** The appearance of the right-hand sidebar with the `CurrentBooking` summary is controlled by the `showBookingUI` variable, which is derived from the `currentPhase`. The chat window physically expands when it needs to show this summary.
4.  **Handlers are Glue Code:** The many `handle...` functions serve as "glue." They connect a specific UI event (e.g., "user clicked a time") to the more generic `sendMessage` function from the `useChat` hook, translating the specific action into a text-based message the backend can understand.

## 11. Potential confusing parts

*   **`renderMessageContent` function**: This function contains a lot of conditional logic and is the most complex part of the file. Understanding that it's a "dispatcher" that decides which interactive component to render for a given message is key to understanding the file.
*   **`editingSection` vs. `currentPhase`**: These are two different state-tracking mechanisms. `currentPhase` is the state of the *conversation* as dictated by the backend. `editingSection` is a purely *UI state* that lets the user signal their intent to change a past decision, which then gets fed back into the conversation.
*   **`updateMessage`**: The `useChat` hook provides an `updateMessage` function. This is used to attach data to an *existing* message in the chat history. For example, when a user selects a time in the `TimePicker`, that selection is attached to the bot message that *asked* for the time, before a new confirmation message is sent.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the master puppeteer for the chat UI, but the `useChat` hook is pulling the strings.** It takes the raw conversation state—messages, booking details, and the current phase—from the hook and translates it into a dynamic, two-column interface. It renders not just text, but a series of interactive mini-apps for date picking, package selection, and more, directly within the conversation flow, and funnels all user interactions back to the `useChat` hook to continue the conversation.
