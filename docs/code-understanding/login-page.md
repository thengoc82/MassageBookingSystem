
# `spa-booking-frontend/app/login/page.tsx`

## 1. Purpose

This file provides the user interface and logic for user authentication. It renders a simple form with username and password fields. Upon submission, it uses the global `AuthContext` to perform the login operation and then redirects the user to the appropriate dashboard based on their role (admin, therapist, or customer).

## 2. Where it fits

The login page is a crucial entry point for authenticated users. It sits apart from the main booking flow but is essential for accessing role-specific parts of the application.

```text
User navigates to "/login" (typically by clicking a "Login" button in the NavBar)
    ↓
This file (`app/login/page.tsx`) is rendered
    ↓
User enters credentials and clicks "Login"
    ↓
`handleSubmit` calls the `login` function from `AuthContext`
    ↓
`AuthContext` sends a POST request to the backend API (`/api/auth/login`)
    ↓
On success, the user is redirected to their specific dashboard (`/admin`, `/therapist`, or `/dashboard`)
```

## 3. Inputs

This component's inputs are derived from:

*   **User Input**: The `username` and `password` that the user types into the form fields.
*   **`AuthContext`**: It consumes the `login` function from the `useAuth` hook. This function is responsible for making the actual API call to the backend.

## 4. Outputs

*   **API Call**: Indirectly, through the `login` function, it triggers a `POST` request to the backend's login endpoint.
*   **Navigation**: Upon successful login, it triggers a client-side navigation to a different page using `router.push()`. The destination depends on the user's role.
*   **UI State Changes**:
    *   It displays an error message if the login fails.
    *   It renders a standard login form.

## 5. Important functions/classes

```text
LoginPage()
    ↓
Purpose
    ↓
    To manage the state and rendering of the login form.
    ↓
Input
    ↓
    None.
    ↓
What it does
    ↓
    1.  Initializes state for `username`, `password`, and `error`.
    2.  Gets the `login` function from the `useAuth` context and the `router` object from `next/navigation`.
    3.  Renders a form with input fields bound to the `username` and `password` state.
    4.  Attaches the `handleSubmit` function to the form's `onSubmit` event.
    ↓
Output
    ↓
    A complete login page UI.
```

```text
handleSubmit(e)
    ↓
Purpose
    ↓
    To handle the form submission, call the login function, and manage the outcome (redirection or error).
    ↓
Input
    ↓
    - `e`: The React form event, which is used to prevent the default browser form submission.
    ↓
What it does
    ↓
    1.  Prevents the default form submission behavior.
    2.  Resets any previous error messages.
    3.  Calls the `login(username, password)` function obtained from `AuthContext`.
    4.  **On Success**: It receives the `user` object. A `switch` statement checks `user.role` and uses `router.push()` to redirect to the appropriate dashboard (`/admin`, `/therapist`, or `/dashboard`).
    5.  **On Failure**: The `login` function throws an error, which is caught. The `error` state is updated with a generic "Invalid username or password" message, which is then displayed in the UI.
    ↓
Output
    ↓
    Either a navigation action or an error message displayed to the user.
```

## 6. Execution flow

1.  The user navigates to the `/login` page.
2.  The `LoginPage` component mounts and renders the login form.
3.  The user types their username and password into the input fields. The `onChange` handlers update the `username` and `password` state variables on every keystroke.
4.  The user clicks the "Login" button.
5.  The `handleSubmit` function is called.
6.  It calls `await login(username, password)`.
7.  The `login` function within `AuthContext` makes a `POST` request to the backend with the credentials.
8.  **If the credentials are valid**: The backend returns a token and user object. `AuthContext` saves these to its state and `localStorage`. `handleSubmit` receives the `user` object. The `switch` statement runs, and `router.push()` redirects the user.
9.  **If the credentials are invalid**: The backend returns an error. `AuthContext` throws an error. The `catch` block in `handleSubmit` executes, setting the `error` state. The component re-renders to display the error message.

## 7. Dependencies

```text
useAuth (from "@/contexts/AuthContext")
    ↓
    This is the most critical dependency. The component is a "consumer" of the `AuthContext`. It uses this hook to get access to the `login` function, abstracting away the details of API calls, token handling, and state updates.

useRouter (from "next/navigation")
    ↓
    This Next.js hook provides the `router` object, which is used to programmatically change pages after a successful login.
```

## 8. Relationship with other files

```text
This file (app/login/page.tsx)
 ├── heavily relies on → contexts/AuthContext.tsx (for the login logic)
 ├── on success, redirects to → app/admin/page.tsx
 ├── on success, redirects to → app/therapist/page.tsx
 └── on success, redirects to → app/dashboard/page.tsx
```

## 9. Important state/data

*   **`username`, `password`**: State variables that hold the user's input from the form fields.
*   **`error`**: A string that holds the error message to be displayed if authentication fails.
*   **`user` object (from `login` call)**: A temporary but crucial piece of data returned from the `login` function. Its `role` property dictates where the user will be redirected.

## 10. What I should understand

1.  **It's a "dumb" component for login.** The page itself doesn't contain any complex logic. Its main job is to collect credentials and delegate the actual authentication process to the `AuthContext`.
2.  **Decoupling via Context:** Using `AuthContext` is a good design choice. It means if the login API endpoint or the method of storing tokens changes, only `AuthContext.tsx` needs to be updated, not this login page.
3.  **Role-Based Redirection is Key:** The `switch` statement in `handleSubmit` is the central piece of logic that routes different types of users to their correct starting pages after logging in.
4.  **Error Handling is Simple:** It doesn't give specific feedback (e.g., "user not found" vs. "wrong password") for security reasons. It just shows a generic "Invalid username or password" message.

## 11. Potential confusing parts

*   **Where is the API call?** Someone reading this file might wonder where the `fetch` or `axios` call is. It's abstracted away into the `login` function provided by `AuthContext`. To understand the network request, one must look at `contexts/AuthContext.tsx`.
*   **No Loading State:** The form doesn't show a loading spinner or disable the button while the `login` function is in progress (though a real user might not notice the delay). The `handleSubmit` is `async`, but there's no `isLoading` state managed within this component itself.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is a simple, clean entry gate for users.** It does nothing more than collect a username and password, hand them off to the global `AuthContext` to handle the complex work of authentication, and then act as a traffic director, pointing users to the correct part of the app based on the role they are assigned upon a successful login.
