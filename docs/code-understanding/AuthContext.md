
# `spa-booking-frontend/contexts/AuthContext.tsx`

## 1. Purpose

This file implements a React Context for managing global authentication state throughout the application. It is responsible for handling the login and logout processes, storing the user's information and authentication token, and making this data available to any component that needs it. It also persists the user's session by storing and retrieving auth data from the browser's `localStorage`.

## 2. Where it fits

This context provider is wrapped around the entire application in the root layout, making it a foundational piece of the app's architecture.

```text
RootLayout (`app/layout.tsx`)
    ↓
Renders `AuthProvider`
    ↓
Any child component (e.g., `NavBar`, `LoginPage`, `RequireAuth`)
    ↓
Calls `useAuth()` hook to access context
    ↓
Context provides `user`, `token`, `login()`, `logout()`
    ↓
`login()` function calls the backend API
```

## 3. Inputs

The `AuthProvider` component itself receives one input:

*   **`children`**: The React nodes to be rendered within the provider. In this app, this is the entire application content.

The functions within the context receive inputs:
*   **`login(username, password)`**: Receives the user's credentials from the component that calls it (e.g., `LoginPage`).

## 4. Outputs

*   **Context Value**: The `AuthProvider` provides a context object with the following properties to all its children:
    *   `user`: A `User` object (or `null` if not logged in).
    *   `token`: The JWT authentication token string (or `null`).
    *   `isLoading`: A boolean that is `true` while the login process is active or during the initial check of `localStorage`.
    *   `login`: The function to initiate authentication.
    *   `logout`: The function to clear the session.
*   **API Calls**: The `login` function makes a `POST` request to the `http://localhost:5000/api/auth/login` endpoint.
*   **`localStorage` Manipulation**:
    *   `login()`: On success, it writes the `token` and `user` object to `localStorage`.
    *   `logout()`: It removes the `token` and `user` from `localStorage`.
    *   `useEffect`: On initial mount, it reads the `token` and `user` from `localStorage` to re-establish the session.

## 5. Important functions/classes

```text
AuthProvider({ children })
    ↓
Purpose
    ↓
    To create the authentication context and provide its state and functions to the rest of the application.
    ↓
Input
    ↓
    - `children`: The rest of the React application.
    ↓
What it does
    ↓
    1.  **Initializes State**: Manages `user`, `token`, and `isLoading` state using `useState`.
    2.  **Session Restoration**: On its initial render, a `useEffect` hook runs to check `localStorage` for a stored `token` and `user`. If found, it restores them to the component's state, effectively logging the user back in.
    3.  **Defines `login` and `logout`**: Contains the implementation for the `login` and `logout` functions.
    4.  **Provides Context**: It uses `AuthContext.Provider` to pass down the state variables (`user`, `token`, `isLoading`) and the `login`/`logout` methods to all descendant components.
    ↓
Output
    ↓
    A context provider that makes authentication data and functions available to its children.
```

```text
useAuth()
    ↓
Purpose
    ↓
    A custom hook that simplifies the process of accessing the authentication context.
    ↓
Input
    ↓
    None.
    ↓
What it does
    ↓
    1.  Calls the `useContext(AuthContext)` hook.
    2.  Performs a check to ensure the hook is being used within an `AuthProvider`. If not, it throws an error. This prevents runtime errors from using the hook in the wrong place.
    ↓
Output
    ↓
    The authentication context value (`{ user, token, isLoading, login, logout }`).
```

## 6. Execution flow

**Login Flow:**
1.  A component (e.g., `LoginPage`) calls the `login(username, password)` function from the `useAuth` hook.
2.  The `isLoading` state is set to `true`.
3.  An `axios.post` request is made to the backend login endpoint.
4.  **On Success**:
    *   The `access_token` and `user` object are extracted from the API response.
    *   The `token` and `user` state variables are updated using `setToken` and `setUser`.
    *   The token and user data are written to `localStorage`.
    *   `isLoading` is set to `false`.
    *   The `user` object is returned to the calling component.
5.  **On Failure**:
    *   The `catch` block executes.
    *   `isLoading` is set to `false`.
    *   The error is re-thrown to be handled by the calling component.

**Initial Load / Page Refresh Flow:**
1.  The `AuthProvider` component mounts for the first time.
2.  The `useEffect` hook runs.
3.  It attempts to get the `token` and `user` items from `localStorage`.
4.  If both exist, it calls `setToken` and `setUser` to restore the authentication state.
5.  `isLoading` is set to `false`.

## 7. Dependencies

```text
axios
    ↓
    A third-party library used to make the HTTP `POST` request for logging in.

React (createContext, useContext, useState, useEffect)
    ↓
    Core React hooks used to create the context, manage state, and handle side effects (like reading from `localStorage`).
```

## 8. Relationship with other files

```text
This file (contexts/AuthContext.tsx)
 ├── is used by → app/layout.tsx (to wrap the whole app)
 ├── is consumed by → app/login/page.tsx (to perform login)
 ├── is consumed by → components/NavBar.tsx (to display user info and conditional links)
 └── is consumed by → components/RequireAuth.tsx (to check authorization)
```

## 9. Important state/data

*   **`user: User | null`**: The central piece of state. It holds the logged-in user's `id`, `name`, and `role`. Its presence or absence determines if a user is authenticated.
*   **`token: string | null`**: The JWT token received from the backend. While stored in state, its primary purpose is to be retrieved from `localStorage` and sent in the `Authorization` header of subsequent API requests (as seen in `lib/api.ts`).
*   **`isLoading: boolean`**: A flag to indicate that an asynchronous authentication operation is in progress.

**Data Persistence:** The most important data handling concept here is the synchronization between the component's state (`user`, `token`) and the browser's `localStorage`. This is what allows a user's session to persist across page reloads.

## 10. What I should understand

1.  **This is the Single Source of Truth for Authentication:** All authentication state and logic are centralized here. No other part of the app needs to know how logins, logouts, or session persistence works.
2.  **It Bridges State and `localStorage`:** It perfectly demonstrates the pattern of using `useEffect` to load initial state from `localStorage` and updating `localStorage` whenever the state changes as a result of an action (like login or logout).
3.  **The `useAuth` Hook is the Public API:** Components don't interact with `AuthContext` directly. They use the `useAuth` custom hook, which is a clean abstraction that also provides a helpful error message if used incorrectly.
4.  **Abstraction is Key:** The `login` function hides the `axios` call, the API URL, and the handling of `localStorage`. Components just call `login()` with credentials and `await` the result.

## 11. Potential confusing parts

*   **`isLoading` State:** The `isLoading` state is set to `true` at the start of a login attempt, but it's set to `false` in both the success path and the `catch` block. This is correct, but it means the caller of `login` can't solely rely on `isLoading` to know if the login was successful; they must also check the return value or handle the thrown error.
*   **Token vs. User in `localStorage`**: Both the token and the user object are stored in `localStorage`. The token is used for authenticating API requests, while the user object is used for immediate access to user details like `role` and `name` without needing an extra API call on every page load. This is a common and efficient pattern.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the application's dedicated security guard and session manager.** It holds the keys (the auth token) and the user's ID card, handles the process of verifying credentials with the backend, and remembers who the user is between visits by checking `localStorage`. Any component in the app that needs to know who is logged in, or needs to perform a login/logout, talks to this context.
