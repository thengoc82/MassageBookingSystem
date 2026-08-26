
# `spa-booking-frontend/app/reservation/page.tsx`

## 1. Purpose

This file is responsible for the final step of the booking process. It takes the initial slot information (shop, date, time, duration) selected on the dashboard and presents the user with a detailed form to select specific massage courses, add-ons, and personal preferences. Once the form is complete, it submits the final booking request to the backend API.

## 2. Where it fits

This page is the second major step in the user's booking journey, following the dashboard.

```text
`app/dashboard/page.tsx`
    ↓
User selects an available time slot
    ↓
Navigates to this file (`app/reservation/page.tsx`) with URL parameters
    ↓
User fills out the detailed reservation form
    ↓
User clicks "Register Reservation"
    ↓
`handleSubmit` function calls the `api.bookings.create` endpoint
    ↓
On success, displays a confirmation screen with the booking code
```

## 3. Inputs

This component's primary inputs come from the URL query parameters passed from the dashboard page.

*   **`shopId`**: The ID of the selected shop.
*   **`date`**: The selected date for the booking (e.g., "2026-08-11").
*   **`time`**: The start time of the selected slot (e.g., "14:00").
*   **`duration`**: The total duration of the selected time slot in minutes (e.g., "60").
*   **`people`**: The number of guests for the booking.
*   **`therapistId`**: (Optional) The ID of the specific therapist, if one was selected on the dashboard.

It also receives input from user interactions with the form elements on the page (e.g., phone number, course selections, preferences).

## 4. Outputs

*   **API Call**: The primary output is a `POST` request to the `/api/bookings` endpoint. This request contains a detailed payload with all the selected courses, preferences, and customer information required to create a booking.
*   **UI State Change**: The component has two main UI states:
    1.  The form itself.
    2.  A success/confirmation screen, which is shown after the API call succeeds. This screen displays the `bookingCode`.
*   **`localStorage` Update**: On a successful booking, it saves a summary of the booking to `localStorage` under the key `recentBookings`.

## 5. Important functions/classes

```text
ReservationForm()
    ↓
Purpose
    ↓
    The main component that contains all the logic for the reservation form, including state management, data fetching, and submission handling.
    ↓
Input
    ↓
    None (it reads its initial state from URL search parameters using `useSearchParams`).
    ↓
What it does
    ↓
    1.  **Initializes State**: Reads `shopId`, `date`, `time`, etc., from the URL to set up the initial state.
    2.  **Fetches Courses**: In a `useEffect` hook, it calls `api.shops.getCourses(shopId)` to get the list of available main courses and add-ons for the selected shop.
    3.  **Manages Form State**: Uses numerous `useState` hooks to manage every piece of the form, from the customer's phone number to their massage strength preference.
    4.  **Calculates Remaining Time**: A `useMemo` hook calculates `remaining`, which is the total slot duration minus the duration of all selected courses. This is a critical piece of validation.
    5.  **Renders the Form**: Renders a multi-section form for customer info, course selection, and various preferences.
    6.  **Handles Submission**: The `handleSubmit` function is called on form submission.
    ↓
Output
    ↓
    A detailed reservation form UI, which transitions to a success screen upon successful booking.
```

```text
handleSubmit()
    ↓
Purpose
    ↓
    To validate the form, construct the API payload, and create the booking via an API call.
    ↓
Input
    ↓
    None (it reads all necessary data from the component's state).
    ↓
What it does
    ↓
    1.  **Validation**: Checks if required fields like `phoneNo` are filled and if the `remaining` time is exactly zero.
    2.  **Payload Construction**: Builds a large `payload` object containing all the booking details in the format expected by the backend API. This includes `shopId`, `bookingDate`, `services`, `addOns`, and all the preferences.
    3.  **API Call**: Calls `api.bookings.create(payload)`.
    4.  **State Update**: On success, it updates the `result` state with the `bookingCode` from the API response, which triggers the UI to switch to the confirmation screen. On failure, it sets an error message in the `error` state.
    ↓
Output
    ↓
    An API request to the backend.
```

## 6. Execution flow

1.  User is redirected from the dashboard to `/reservation?shopId=1&date=...`.
2.  The `ReservationForm` component mounts.
3.  The `useSearchParams` hook reads the initial booking parameters from the URL. State variables like `shopId`, `initDate`, etc., are initialized.
4.  The `useEffect` for fetching courses fires, calling `api.shops.getCourses()` for the given `shopId`. The `courses` state is populated.
5.  The component renders the detailed form, pre-filled with the date and time from the URL.
6.  The user fills in their phone number, selects a main course duration, and adds optional add-on courses until the "Remaining" time is 0.
7.  The user also selects their preferences (e.g., tired parts, massage strength).
8.  The user clicks the "Register Reservation" button.
9.  The `handleSubmit` function is triggered.
10. The function validates the form. If valid, it builds the booking payload and sends it to the `POST /api/bookings` endpoint.
11. If the API call is successful, the `result` state is updated with the booking code.
12. The component re-renders to show the confirmation screen.
13. If the API call fails, the `error` state is updated, and an error message is displayed to the user.

## 7. Dependencies

```text
useSearchParams (from "next/navigation")
    ↓
    The hook used to read the query parameters from the URL. This is the primary way this page gets its initial context from the dashboard.

api (from "@/lib/api")
    ↓
    The API helper. This page heavily uses `api.shops.getCourses` to fetch course data and `api.bookings.create` to finalize the reservation.

Suspense (from "react")
    ↓
    The `ReservationForm` is wrapped in `<Suspense>`. This is a React feature for handling async operations, ensuring that if any data fetching suspends rendering, a fallback UI ("Loading...") is shown.
```

## 8. Relationship with other files

```text
This file (app/reservation/page.tsx)
 ├── receives data from → app/dashboard/page.tsx (via URL parameters)
 ├── uses → lib/api.ts (to get courses and create booking)
 ├── uses → types/index.ts (for course and booking data structures)
 └── on success, links back to → app/dashboard/page.tsx
```

## 9. Important state/data

*   **Initial Parameters from URL**: `initShopId`, `initDate`, `initTime`, `slotDuration` are the foundational data for this page.
*   **`courses`**: An array of `ApiCourse` objects, representing the menu of services the user can choose from.
*   **`fbmDuration` and `selectedAddons`**: These two state variables track the user's course selections. They are used to calculate the `remaining` time.
*   **`remaining`**: A derived state variable that is critical for form validation. The booking cannot proceed unless `remaining === 0`.
*   **`payload` (in `handleSubmit`)**: The large object built just before the API call. It represents the complete, structured data for the new booking.
*   **`result`**: State that holds the final booking confirmation details (`bookingCode`), used to switch the UI to the success screen.

## 10. What I should understand

1.  **This Page is a "Data Aggregator":** Its main purpose is to collect a lot of detailed information from the user to build a complex API request.
2.  **URL Parameters are the Entry Point:** The page is useless without the context provided by the query parameters from the dashboard.
3.  **The "Remaining Time" Logic is Central:** The core interactive loop for the user is selecting courses to make the `remaining` time equal to zero. This is the main validation gate.
4.  **It Handles Two Major UI States:** The form view and the success view. The `result` state variable is the switch that toggles between them.
5.  **Payload Construction is Key:** The `handleSubmit` function's main job is to transform the many `useState` variables into a single, structured `payload` object that the backend can understand.

## 11. Potential confusing parts

*   **`Suspense` Wrapper**: The `<Suspense>` component is used here. While simple in this case, it hints that this page is designed to work well with React's concurrent features, potentially allowing parts of the UI to render while data is still being fetched.
*   **Hardcoded Course Logic**: The code assumes a "Full Body Massage" (`fbmCourse`) is the "main" course and everything else is an add-on. This logic (`c.courseName.toLowerCase().includes('full body')`) could be brittle if the course names change.
*   **State Slicing**: The page uses many individual `useState` hooks for each piece of form data. In a more complex application, this might be managed by a `useReducer` hook or a form library for better organization.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the final checkout counter for a booking.** It takes the basic time slot from the dashboard, presents the user with a detailed menu of services and preferences, and guides them to fill their selected time slot completely. Once all details are gathered and validated, it bundles everything up and sends the final order to the kitchen (the backend API).
