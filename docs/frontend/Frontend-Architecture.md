# Frontend Architecture

This document outlines the architecture of the `spa-booking-frontend`.

## Main Pages and Routes

The frontend uses Next.js with the App Router. The main pages are:

- **`/` (`[[app/page.tsx]]`):** The main landing page.
- **`/login` (`[[app/login/page.tsx]]`):** User login page.
- **`/dashboard` (`[[app/dashboard/page.tsx]]`):** User dashboard.
- **`/my-bookings` (`[[app/my-bookings/page.tsx]]`):** List of bookings for the current user.
- **`/booking` (`[[app/booking/page.tsx]]`):** The main booking creation page.
- **`/bookings/[id]` (`[[app/bookings/[id]/page.tsx]]`):** Details of a specific booking.
- **`/reservation` (`[[app/reservation/page.tsx]]`):** A page related to reservations.
- **`/shops` (`[[app/shops/page.tsx]]`):** A page to display shops.
- **`/therapist`:** Pages for therapist users.
    - `/therapist/profile`
    - `/therapist/schedule`
    - `/therapist/bookings`
- **`/admin`:** Pages for admin users.
    - `/admin/shops`
    - `/admin/courses`
    - `/admin/therapists`
    - `/admin/customers`
    - `/admin/schedules`
    - `/admin/bookings`

## Main UI Components

- **`[[app/layout.tsx]]`**: The root layout for the entire application. It likely includes the `NavBar` and wraps content in the `AuthProvider`.
- **`[[components/NavBar.tsx]]`**: The main navigation bar. It displays links based on the user's authentication status and role.
- **`[[components/AuthNav.tsx]]`**: Part of the `NavBar`, this component shows "Login" or "Logout" buttons and user-specific navigation.
- **`[[components/RequireAuth.tsx]]`**: A higher-order component that protects routes by checking for a user and token in `localStorage`.
- **Chatbot Components (`[[components/chatbot]]`)**: A collection of components for the chatbot interface, including `ChatWidget.tsx`, `ChatWindow.tsx`, and various option selectors.

## Authentication

Authentication is handled via a context and `localStorage`.

- **`[[contexts/AuthContext.tsx]]`**:
    - **Role**: Provides authentication state and functions to the entire app.
    - **Input**: `children` (React components).
    - **Output**: A context with `user`, `token`, `isLoading`, `login`, and `logout`.
    - **Dependencies**: `axios` for making API calls.
    - **Who uses it**: Wrapped around the application in `[[app/layout.tsx]]`. The `useAuth` hook is used by many components to access auth state.
- **Flow**:
    1. User logs in via the `[[app/login/page.tsx]]`.
    2. The `login` page calls the `login` function from `AuthContext`.
    3. The `login` function sends credentials to the API.
    4. On success, the received `access_token` and `user` object are stored in `localStorage` and React state.
    5. On subsequent visits, `AuthProvider` reads the user and token from `localStorage` to maintain the session.
    6. The `RequireAuth` component checks `localStorage` to protect routes.

## User State

User state, including the user object and authentication token, is stored in two places:
- **React state**: Managed by the `[[contexts/AuthContext.tsx]]` for real-time UI updates.
- **`localStorage`**: For persistence between page reloads and across browser tabs.
