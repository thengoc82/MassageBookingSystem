
# `spa-booking-frontend/components/chatbot/ChatWidget.tsx`

## 1. Purpose

This file is the user-facing entry point for the AI chatbot. Its sole responsibility is to render a floating action button at the bottom-right of the screen. When this button is clicked, it reveals the main `ChatWindow` component, and when the chat window is closed, it reverts to showing the button. It acts as a simple toggle for the chatbot's visibility.

## 2. Where it fits

This component is rendered once in the root layout (`app/layout.tsx`), ensuring it is present and maintains its state across all pages of the application.

```text
`app/layout.tsx`
    ↓
Renders `ChatWidget`
    ↓
User clicks the floating chat button
    ↓
`ChatWidget`'s internal state `isOpen` becomes true
    ↓
`ChatWindow` component is rendered
    ↓
User closes the chat window
    ↓
`onClose` callback is triggered, setting `isOpen` to false
    ↓
`ChatWindow` is unmounted, and the button is shown again
```

## 3. Inputs

This component does not receive any props from its parent. It is entirely self-contained.

## 4. Outputs

*   **UI State Change**: The component's output is purely visual. It conditionally renders one of two things based on its internal `isOpen` state:
    1.  A floating button with a message icon.
    2.  The `ChatWindow` component.

## 5. Important functions/classes

```text
ChatWidget()
    ↓
Purpose
    ↓
    To manage the visibility of the chatbot and act as the user's entry point to start a conversation.
    ↓
Input
    ↓
    None.
    ↓
What it does
    ↓
    1.  **Manages State**: It uses a single `useState` hook to manage the `isOpen` boolean state, which defaults to `false`.
    2.  **Conditional Rendering**:
        *   If `isOpen` is `true`, it renders the `<ChatWindow />` component and passes it an `onClose` callback function. This function simply sets `isOpen` back to `false`.
        *   If `isOpen` is `false`, it renders a `<button>`. The button's `onClick` handler sets `isOpen` to `true`.
    ↓
Output
    ↓
    A toggleable UI element that shows either a button or the main chat window.
```

## 6. Execution flow

1.  The `ChatWidget` component is mounted as part of the root layout.
2.  The `isOpen` state is initialized to `false`.
3.  The component renders the floating `<button>`.
4.  The user clicks the button.
5.  The button's `onClick` handler fires, calling `setIsOpen(true)`.
6.  The component re-renders. Now, because `isOpen` is `true`, the `<ChatWindow />` component is rendered instead of the button.
7.  The user interacts with the `ChatWindow`.
8.  When the user clicks the "close" button inside `ChatWindow`, the `onClose` prop (which is `() => setIsOpen(false)`) is called.
9.  The `isOpen` state in `ChatWidget` is set back to `false`.
10. The component re-renders, unmounting `ChatWindow` and showing the floating `<button>` again.

## 7. Dependencies

```text
ChatWindow (from "./ChatWindow")
    ↓
    This is the most important dependency. It is the actual, complex component containing the entire chat interface (messages, input box, etc.). `ChatWidget` is merely a launcher for `ChatWindow`.

MessageCircle (from "lucide-react")
    ↓
    An icon library used to get the chat bubble icon for the floating button.
```

## 8. Relationship with other files

```text
This file (components/chatbot/ChatWidget.tsx)
 ├── is rendered by → app/layout.tsx
 └── conditionally renders → components/chatbot/ChatWindow.tsx
```

## 9. Important state/data

*   **`isOpen: boolean`**: This is the only piece of state in this file. It is a simple boolean flag that determines whether to show the chat button or the full chat window. This state is ephemeral and resets if the user refreshes the entire page.

## 10. What I should understand

1.  **It's a "Launcher," not the Chatbot:** This file does not contain any chat logic. It is purely a UI component for toggling the visibility of the actual chat window.
2.  **State is Simple and Local:** The `isOpen` state is managed entirely within this component and is not shared. This is a good example of keeping state as local as possible.
3.  **It controls the mounting/unmounting of `ChatWindow`:** The entire lifecycle of the main `ChatWindow` is controlled by the `isOpen` state in this file. When `isOpen` becomes false, the `ChatWindow` and all of its internal state (including the conversation) are unmounted. *Correction*: Based on the `useChat` hook's logic, the conversation state is managed in the hook and may persist via `useRef` even if the component unmounts, but the UI state is indeed destroyed.

## 11. Potential confusing parts

*   **State Persistence**: It might be assumed that closing the chat window (and unmounting `ChatWindow`) would destroy the conversation. However, the `useChat` hook, used by `ChatWindow`, is designed to handle this. The conversation state (e.g., `sessionId`) is stored in a `useRef`, which can persist across re-renders. The conversation is only truly reset when the hook is re-initialized or explicitly told to restart.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is simply the light switch for the chatbot.** It doesn't generate any light itself; it just holds the button. Clicking it turns on the `ChatWindow` (the light bulb), and closing the window is like flipping the switch off. Its sole job is to manage the `on` and `off` state for the chat interface's visibility.
