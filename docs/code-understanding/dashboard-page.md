
# `spa-booking-frontend/app/dashboard/page.tsx`

## 1. Purpose

This file is the main user interface for finding and selecting a massage appointment. It allows users to choose a shop, date, duration, and number of people, and then displays available time slots in a Gantt chart-like view showing therapist availability. It serves as the primary interactive component for starting the booking process.

## 2. Where it fits

This is the main application screen that users are redirected to after visiting the root URL.

```text
User visits "/"
    ↓
`app/page.tsx` redirects to "/dashboard"
    ↓
This file (`app/dashboard/page.tsx`) is rendered
    ↓
Fetches data from the API (`/api/shops`, `/api/shops/.../available-slots`)
    ↓
Renders the `TherapistGantt` component with availability data
    ↓
User clicks an available slot
    ↓
Navigates to the `/reservation` page with selected parameters
```

## 3. Inputs

This component does not receive props from a parent but manages its own state based on user interaction and API calls. Its key inputs are derived from:

*   **User Actions**: Clicks on date pickers, dropdowns for shop, duration, and number of people.
*   **API Responses**:
    *   `api.shops.getAll()`: Fetches the list of all available shops to populate the shop selection dropdown.
    *   `api.shops.getAvailableSlots()`: Fetches the available time slots and therapists based on the user's selections (shop, date, duration, etc.). This data is the primary driver for the `TherapistGantt` component.
*   **Browser `localStorage`**: Reads `recentBookings` on initial load, though it does not appear to use this data in the current implementation.

## 4. Outputs

This file's primary output is a rich, interactive user interface. When a user interacts with this interface, it can produce:

*   **UI Updates**: The Gantt chart updates dynamically when the user changes the date, shop, or other parameters.
*   **Navigation**: When a user clicks on an available time slot in the `TherapistGantt` component, the `handleSlotClick` function is triggered. This constructs a URL with query parameters (e.g., `shopId`, `date`, `time`, `duration`) and programmatically navigates the user to the `/reservation` page to continue the booking process.

## 5. Important functions/classes

```text
DashboardPage()
    ↓
Purpose
    ↓
    The main component for this page. It manages all the state for the booking search criteria and orchestrates data fetching and rendering.
    ↓
Input
    ↓
    None (it's a top-level page component).
    ↓
What it does
    ↓
    1.  Initializes state for `date`, `shops`, selected `shopId`, `duration`, and `people`.
    2.  In a `useEffect` hook, it calls `api.shops.getAll()` to fetch the list of shops and populates the dropdown. It defaults to selecting the first shop.
    3.  Renders the top control bar with date navigation, a calendar pop-up, and dropdowns for shop, duration, and party size.
    4.  Conditionally renders the `TherapistGantt` component, passing down the selected `shopId`, `date`, `duration`, and `numberOfPeople` as props.
    5.  Provides the `handleSlotClick` callback function to `TherapistGantt`.
    ↓
Output
    ↓
    A full-page interactive view for searching booking slots.
```

```text
handleSlotClick(time, therapistId)
    ↓
Purpose
    ↓
    To handle the user's selection of an available time slot.
    ↓
Input
    ↓
    - `time`: The start time of the selected slot (e.g., "10:30").
    - `therapistId`: The ID of the selected therapist.
    ↓
What it does
    ↓
    1.  Creates a `URLSearchParams` object.
    2.  Populates it with the current state: `shopId`, `date`, `time`, `duration`, `people`, and `therapistId`.
    3.  Uses the `useRouter` hook's `push` method to navigate to the `/reservation` page with the parameters encoded in the URL.
    ↓
Output
    ↓
    A browser navigation event to the reservation page.
```

## 6. Execution flow

1.  The user lands on the `/dashboard` page.
2.  The `DashboardPage` component mounts.
3.  The `useEffect` hook fires, calling the `api.shops.getAll()` endpoint.
4.  The state is updated with the list of shops, and the first shop is selected by default, triggering a re-render.
5.  With `shopId` now set, the `TherapistGantt` component is rendered for the first time.
6.  Inside `TherapistGantt`, a `useEffect` hook fires, calling `api.shops.getAvailableSlots()` with the current `shopId`, `date`, and other parameters.
7.  The API returns available slots and therapist data. The `TherapistGantt` component state is updated, and it renders the visual grid of availability.
8.  The user can then change the date or other dropdowns. Each change updates the state in `DashboardPage`, which flows down as props to `TherapistGantt`, causing it to re-fetch data and re-render.
9.  When the user clicks a green (available) cell, the `handleSlotClick` callback is invoked.
10. `handleSlotClick` builds the URL for the reservation page and navigates the user there.

## 7. Dependencies

```text
TherapistGantt (from "@/components/TherapistGantt")
    ↓
    This is the most important child component. It is responsible for fetching the detailed availability data and rendering the interactive Gantt chart of therapists and their time slots.

api (from "@/lib/api")
    ↓
    A helper object that centralizes all API calls. This page uses `api.shops.getAll()` to get the list of shops. The actual slot data is fetched within `TherapistGantt`.

useRouter (from "next/navigation")
    ↓
    A Next.js hook used to perform client-side navigation. It's used in `handleSlotClick` to redirect the user to the reservation page after they select a slot.

Shop, TimeSlot, TherapistInfo (from "@/types/index")
    ↓
    TypeScript interfaces that define the shape of the data being fetched from the API and held in the component's state.
```

## 8. Relationship with other files

```text
This file (app/dashboard/page.tsx)
 ├── renders → components/TherapistGantt.tsx
 ├── uses → lib/api.ts (for fetching shop list)
 ├── uses → types/index.ts (for data shapes)
 └── sends user to → app/reservation/page.tsx (on slot selection)
```

## 9. Important state/data

*   **`date`**: A `Date` object representing the currently selected day.
*   **`shops`**: An array of `Shop` objects fetched from the API.
*   **`shopId`**: A number representing the ID of the currently selected shop. This is crucial as it's passed to the `TherapistGantt` component to fetch the correct data.
*   **`duration`**: The length of the desired appointment in minutes.
*   **`people`**: The number of people for the booking.
*   **Data in `TherapistGantt`**: The dashboard delegates the management of `slots` and `therapists` data to the `TherapistGantt` component, which fetches it based on the props it receives from the dashboard.

## 10. What I should understand

1.  **It's a "Container" Component:** `DashboardPage` acts as a container. It manages the high-level search criteria (shop, date, etc.) but delegates the complex rendering and data-fetching of the availability grid to the `TherapistGantt` "presentational" component.
2.  **The Flow of Props is Key:** The state managed by `DashboardPage` (like `shopId` and `date`) is passed down as props to `TherapistGantt`. The Gantt component then uses these props to fetch its own data.
3.  **Client-Side Interactivity:** This is a client component (`'use client'`) because it relies heavily on state, effects, and browser events for its interactive nature.
4.  **The End Goal is Navigation:** The ultimate purpose of this page is to gather enough information from the user to construct a URL that leads them to the `/reservation` page.
5.  **State Management is Simple:** It uses standard React `useState` and `useCallback` hooks for state management. There are no complex state management libraries like Redux or Zustand involved here.

## 11. Potential confusing parts

*   **Who Fetches What?**: It might be slightly confusing that `DashboardPage` fetches the list of *shops*, but the `TherapistGantt` component fetches the *availability slots*. This separation is logical: the dashboard owns the list of shops, while the Gantt chart owns the data it is responsible for displaying.
*   **`readRecent()`**: This function is defined and called to initialize the `recentBookings` state from `localStorage`, but the state variable itself is never used in the component. This could be leftover code from a previous implementation.
*   **The Calendar (`showCal`)**: The calendar is a custom-built component within this file, not a third-party library. Its logic for rendering days and handling month navigation is all self-contained.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the central hub for starting a booking.** It's an interactive form that presents the user with choices (shop, date, duration) and then delegates the heavy lifting of displaying therapist availability to the `TherapistGantt` component. Its primary job is to collect the user's initial preferences and, once they've selected a time, pass that information along to the reservation page.
