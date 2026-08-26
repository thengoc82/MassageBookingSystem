# Frontend Key Files

To understand the frontend architecture and flows, read these files in the following order.

1.  **`[[contexts/AuthContext.tsx]]`**
    - **Why**: This is the foundation of user session management. It shows how login, logout, and user state persistence are handled for the entire application. Understanding this is crucial as nearly every other component depends on it.

2.  **`[[lib/hooks/useChat.ts]]`**
    - **Why**: This is the "brain" of the entire chatbot booking flow. It manages the conversation state machine, communication with the backend AI, and the assembly of the `bookingState` object.

3.  **`[[components/chatbot/ChatWindow.tsx]]`**
    - **Why**: This is the "body" of the chatbot. It's the master component that consumes the `useChat` hook and decides which interactive sub-components to render based on the conversation's phase.

4.  **`[[app/dashboard/page.tsx]]`**
    - **Why**: This is the entry point for the traditional Gantt chart booking flow. It shows how users select initial booking parameters and how the application visualizes therapist availability.

5.  **`[[app/reservation/page.tsx]]`**
    - **Why**: This is the second half of the Gantt chart booking flow. It's a large, complex form that shows how a booking is finalized with courses, add-ons, and customer details before being sent directly to the bookings API.

6.  **`[[lib/api.ts]]`**
    - **Why**: This file centralizes all communication with the backend. It shows how `axios` is configured and provides a clean interface (`api.shops.getAll`, `api.bookings.create`, etc.) used by the rest of the application.

7.  **`[[lib/types.ts]]`**
    - **Why**: This file contains the TypeScript definitions for all the major data structures, like `BookingState` and `ConversationPhase`. It's a map to the data that flows through the system.

8.  **`[[app/layout.tsx]]`**
    - **Why**: The root layout of the entire application. It shows how the `AuthProvider` is applied to wrap all pages, making authentication state globally available.

9.  **`[[components/NavBar.tsx]]`**
    - **Why**: A clear and simple example of how authentication state from `useAuth` is used to conditionally render UI elements and control navigation.

10. **`[[app/booking/page.tsx]]`**
    - **Why**: While its entry point is unclear, this file is a good example of a multi-step confirmation UI. It shows how to handle complex forms, state updates, and error conditions like slot unavailability.
