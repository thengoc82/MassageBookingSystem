
# `spa-booking-frontend/app/layout.tsx`

## 1. Purpose

This file is the root layout for the entire Next.js application. It defines the main HTML shell, including the `<html>` and `<body>` tags, that wraps every page. Its primary responsibilities are to set up global providers (like authentication), include consistent UI elements like the navigation bar and footer, and load global styles and fonts.

## 2. Where it fits

This is the top-most component in the front-end application's rendering tree.

```text
Next.js Server
    ↓
Renders this RootLayout
    ↓
Renders the current page (as `children`) inside the layout
    ↓
Page is sent to the browser
```

## 3. Inputs

This component receives one primary input from Next.js:

*   **`children`**: This is a React Node that represents the current page being rendered. Next.js automatically passes the specific page component (e.g., `app/dashboard/page.tsx` or `app/login/page.tsx`) as the `children` prop. This allows the layout to wrap the page content with a consistent structure.

## 4. Outputs

This file produces the main HTML document structure for every page in the application. Its output includes:

*   A standard HTML5 document structure.
*   The `NavBar` component at the top of the page.
*   The `ChatWidget` component, which is fixed to the bottom-right of the screen.
*   A consistent `footer` at the bottom of the page.
*   The actual page content, rendered inside the `<body>` tag where `{children}` is placed.

This entire structure is then sent to the client's browser.

## 5. Important functions/classes

```text
RootLayout()
    ↓
Purpose
    ↓
    To provide a consistent structure and global context for all pages in the application.
    ↓
Input
    ↓
    - `children`: The active page component provided by the Next.js router.
    ↓
What it does
    ↓
    1.  Wraps the entire application in an `<html>` and `<body>` tag.
    2.  Applies the "Inter" font to the body.
    3.  Wraps the page content (`children`) and the `NavBar` with the `AuthProvider`. This makes authentication state (like the current user) available to all components.
    4.  Renders the `NavBar` component.
    5.  Renders the page content (`children`).
    6.  Renders the `ChatWidget` component.
    7.  Renders a static footer.
    ↓
Output
    ↓
    A complete HTML page structure with the application's global components and the specific page content.
```

## 6. Execution flow

When a user navigates to any page in the application:

1.  Next.js identifies the page component to be rendered (e.g., `app/dashboard/page.tsx`).
2.  It then renders the `RootLayout` component from `app/layout.tsx`.
3.  The `AuthProvider` is mounted, which attempts to load user and token information from `localStorage`.
4.  The `NavBar` is rendered. Inside the `NavBar`, the `useAuth` hook retrieves the user's data from `AuthProvider` to determine which dashboard link to show.
5.  The page component itself (passed as `children`) is rendered.
6.  The `ChatWidget` is rendered, which manages its own state for being open or closed.
7.  A static footer is rendered.
8.  The complete HTML is delivered to the browser.

## 7. Dependencies

```text
AuthProvider (from "@/contexts/AuthContext")
    ↓
    This is a React Context Provider that manages the application's authentication state. It wraps the entire application so that any component can access the current user, the auth token, and login/logout functions.

ChatWidget (from "@/components/chatbot/ChatWidget")
    ↓
    A floating UI component that allows the user to open a chat window. It is included in the root layout to be present on all pages.

NavBar (from "@/components/NavBar")
    ↓
    The main navigation bar for the application. It is included in the root layout to appear on every page and displays navigation links based on the user's authentication status.

Inter (from "next/font/google")
    ↓
    A font loader from Next.js to optimize and load the Inter web font.

globals.css
    ↓
    The global stylesheet for the application, providing base styles.
```

## 8. Relationship with other files

```text
This file (app/layout.tsx)
 ├── wraps → every page in the `app/` directory (e.g., `app/dashboard/page.tsx`)
 ├── uses → contexts/AuthContext.tsx (to provide auth state)
 ├── displays → components/NavBar.tsx (at the top of every page)
 └── displays → components/chatbot/ChatWidget.tsx (on every page)
```

## 9. Important state/data

*   **`metadata`**: An object exported from this file that Next.js uses to set the page's default `<title>` and `<meta name="description">` tags. This is important for SEO and browser tab information.
*   **`children`**: The dynamic page content passed in by Next.js. This is the most critical piece of data as it represents the unique content of each URL.

The state itself is not managed in this file but in its dependencies:
*   **Authentication State (`user`, `token`)**: Managed within `AuthProvider`, which this file uses to wrap the application. This state determines what the user sees and can do.

## 10. What I should understand

1.  **This is the single entry point for all pages.** Every page transition will re-render the `children` prop, but the `RootLayout` itself (and its state, like `AuthProvider`) persists.
2.  **Global context is established here.** The placement of `AuthProvider` is critical. It means authentication state is available everywhere.
3.  **It defines the "frame" of the application.** The `NavBar`, `ChatWidget`, and `footer` are part of this frame and will not be re-rendered on page navigation, which is efficient.
4.  **It is a server-side component by default in Next.js App Router.** Although it uses client-side components like `AuthProvider`, the layout itself is first rendered on the server.
5.  **Styling and fonts are loaded globally here.** The `globals.css` and the `Inter` font are applied to the `<body>` tag, ensuring a consistent look and feel.

## 11. Potential confusing parts

*   **Server vs. Client components**: `RootLayout` is a Server Component, but it directly renders Client Components like `AuthProvider` and `NavBar` (indicated by `"use client"` in their respective files). This is a key concept in the Next.js App Router. The layout itself renders on the server, but the interactive, stateful components it uses are hydrated and run on the client.
*   **The `{children}` prop**: It might not be immediately obvious that `{children}` is not a regular prop but a special one provided by Next.js to render the matched page. You won't see it passed manually.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the master template for the entire application**. It sets up the permanent furniture of the UI—the navigation bar, the footer, and the chat button—and wraps everything in the global authentication provider, ensuring every page has a consistent structure and access to user login state.
