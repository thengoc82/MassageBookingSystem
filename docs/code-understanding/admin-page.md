
# `spa-booking-frontend/app/admin/page.tsx`

## 1. Purpose

This file serves as the main dashboard for the admin panel. Its primary purpose is to provide administrators with a high-level overview of the day's operations. It displays a Gantt chart of all therapist activities for a selected shop and date, as well as a list of all bookings for that day. This page acts as the central hub from which an admin can monitor activity and navigate to other management sections.

## 2. Where it fits

This is the landing page for any user with the 'admin' role after they log in.

```text
User with 'admin' role logs in
    ↓
Redirected to `/admin`
    ↓
`AdminPage` component renders
    ↓
`RequireAuth` component validates the user's role
    ↓
`AdminDashboard` is rendered
    ↓
Fetches shops and bookings from the admin API endpoints
    ↓
Displays `AdminSidebar`, `TherapistGantt`, and a list of bookings
```

## 3. Inputs

*   **User Role**: The component is wrapped in `RequireAuth`, which implicitly takes the user's role from `localStorage` as input to determine if the user is allowed to see the page.
*   **User Selections**:
    *   The selected `shopId` from the shops dropdown.
    *   The selected `date` from the date input.
*   **API Responses**:
    *   `api.admin.getShops()`: Fetches the list of shops to populate the dropdown.
    *   `api.admin.getBookings()`: Fetches the list of bookings for the selected shop and date.

## 4. Outputs

*   **A comprehensive UI**: Renders a full-page dashboard layout including a sidebar for navigation, a Gantt chart for visual scheduling, and a list of daily bookings.
*   **API Calls**: Makes calls to the backend to fetch necessary data based on user selections.
*   **Navigation**: The list of bookings is interactive; clicking on a booking navigates the admin to a detailed view for that specific booking (`/bookings/[bookingId]`).

## 5. Important functions/classes

```text
AdminPage()
    ↓
Purpose
    ↓
    To act as a security gateway for the admin dashboard.
    ↓
Input
    ↓
    - `children`: The `AdminDashboard` component.
    ↓
What it does
    ↓
    1.  Wraps the entire `AdminDashboard` content within the `RequireAuth` component.
    2.  Passes an `allowedRoles` array containing only `'admin'` to `RequireAuth`. This ensures that only users with the admin role can view the page.
    ↓
Output
    ↓
    Either the `AdminDashboard` component (if authorized) or a "Forbidden" / loading screen from `RequireAuth`.
```

```text
AdminDashboard()
    ↓
Purpose
    ↓
    To fetch and display all the data for the admin's daily overview.
    ↓
Input
    ↓
    None.
    ↓
What it does
    ↓
    1.  **Initializes State**: Sets up state for `shops`, `shopId`, `date`, and `bookings`.
    2.  **Fetches Data**:
        *   A `useEffect` hook fetches the list of all shops via `api.admin.getShops()` on component mount.
        *   Another `useEffect` hook re-fetches the list of bookings via `api.admin.getBookings()` whenever the selected `shopId` or `date` changes.
    3.  **Renders Layout**: Renders the `AdminSidebar` and the main content area.
    4.  **Renders Controls**: Displays a dropdown to select a shop and a date input.
    5.  **Renders Gantt Chart**: Renders the `TherapistGantt` component, passing it the selected `shopId` and `date`. It sets `showDetails={true}` to display a more information-rich version of the chart.
    6.  **Renders Booking List**: Maps over the `bookings` state to display a list of all bookings for the selected day, each with a status indicator and a link to its details page.
    ↓
Output
    ↓
    The complete, data-driven UI for the admin dashboard.
```

## 6. Execution flow

1.  An admin user navigates to `/admin`.
2.  The `AdminPage` component renders. `RequireAuth` checks `localStorage` for a user and token. It verifies the user's role is 'admin'.
3.  Assuming authorization succeeds, `RequireAuth` renders its children, the `AdminDashboard` component.
4.  `AdminDashboard` mounts. Its first `useEffect` hook fires, calling `api.admin.getShops()`.
5.  The `shops` state is updated. The first shop in the list is selected by default, updating the `shopId` state.
6.  The update to `shopId` triggers the second `useEffect` hook, which calls `api.admin.getBookings()` for the current shop and date.
7.  The `bookings` state is updated.
8.  The component re-renders with all the fetched data, displaying the shop selector, date picker, the populated `TherapistGantt` chart, and the list of bookings.
9.  If the admin changes the shop or date, the relevant `useEffect` hook is re-triggered, fetching new data and updating the UI.

## 7. Dependencies

```text
RequireAuth (from "@/components/RequireAuth")
    ↓
    A higher-order component that acts as a client-side authentication and authorization guard. It checks if a user is logged in and if their role is in the `allowedRoles` list. If not, it redirects to login or shows a "Forbidden" page.

AdminSidebar (from "@/components/AdminSidebar")
    ↓
    The navigation component for the admin section. It displays links to all the different admin pages (Manage Bookings, Shops, Therapists, etc.).

TherapistGantt (from "@/components/TherapistGantt")
    ↓
    The same Gantt chart component used on the public dashboard, but configured with `showDetails={true}` to display existing bookings rather than just availability. This provides a visual overview of the day's schedule.

api (from "@/lib/api")
    ↓
    The API client. This page specifically uses the `api.admin` section to fetch data from admin-only endpoints (`/admin/shops`, `/admin/bookings`).
```

## 8. Relationship with other files

```text
This file (app/admin/page.tsx)
 ├── is protected by → components/RequireAuth.tsx
 ├── displays → components/AdminSidebar.tsx
 ├── displays → components/TherapistGantt.tsx
 ├── fetches data using → lib/api.ts
 └── links to → app/bookings/[bookingId]/page.tsx (and other admin pages via the sidebar)
```

## 9. Important state/data

*   **`shopId`**: The ID of the currently selected shop. This is the primary filter for all data displayed on the dashboard.
*   **`date`**: The currently selected date.
*   **`shops`**: An array of shop objects fetched from the API, used to populate the dropdown.
*   **`bookings`**: An array of booking objects for the selected shop and date. This is used to render the list at the bottom of the page.

## 10. What I should understand

1.  **This is a protected route.** The `RequireAuth` wrapper is the first line of defense, ensuring only admins can access this component.
2.  **It's a data-driven dashboard.** The entire UI is driven by the data fetched from the API based on the admin's selection of a shop and a date.
3.  **Component Re-use is happening.** The `TherapistGantt` component is re-used from the public-facing dashboard, but in a different mode (`showDetails={true}`) to serve a different purpose (showing what's booked vs. what's available).
4.  **It's the Admin "Home Base".** This page serves as the entry point and overview for all administrative tasks, with the `AdminSidebar` providing clear navigation to more specific management pages.
5.  **The API calls are to admin-specific endpoints.** It uses `api.admin.*` functions, which likely hit a separate set of secured routes on the backend.

## 11. Potential confusing parts

*   **`shopId || s.id`**: The code contains `s.shopId || s.id`. This suggests some inconsistency in the data structure returned by the API, where the shop identifier might be named either `shopId` or `id`. This is a defensive coding practice to handle both possibilities.
*   **Client-Side Authorization**: The authorization check in `RequireAuth` happens on the client side by reading `localStorage`. While effective for UI purposes, a robust application would also have server-side protection on the API endpoints themselves to prevent unauthorized data access. This file only shows the client-side part of that protection.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the administrator's mission control center.** After passing a security check, it provides a dynamic, at-a-glance view of a selected shop's daily schedule through a visual Gantt chart and a clear list of bookings. It's a read-only dashboard designed for monitoring, with the sidebar serving as the door to all other sections where an admin can take action.
