# 6. Debugging Map

This document provides a quick reference for locating the source of common problems in the application.

---

## Frontend Issues

Problems related to what the user sees and interacts with.

#### **Problem: UI is not displaying correctly or is missing data.**
-   **Where to Look**: The React component responsible for that part of the UI.
-   **Files**:
    -   Check the relevant page file in [[spa-booking-frontend/app]].
    -   Check the specific component file in [[spa-booking-frontend/components]].
    -   For booking state, inspect [[spa-booking-frontend/lib/hooks/useChat.ts]] to see if the `bookingState` object is being updated correctly from the chatbot's response.

#### **Problem: Login fails or user data is not loading after login.**
-   **Where to Look**: The authentication context and local storage.
-   **Files**:
    -   [[spa-booking-frontend/contexts/AuthContext.tsx]]: Check the `login` function and how it handles the API response.
    -   [[spa-booking-frontend/lib/api.ts]]: Verify the `authFetch` function is correctly reading the token from `localStorage`.
    -   Use browser developer tools to inspect `localStorage` for the `token` and `user` items.

#### **Problem: Chat messages are not being sent or received.**
-   **Where to Look**: The chat hook and its API call.
-   **Files**:
    -   [[spa-booking-frontend/lib/hooks/useChat.ts]]: This is the central file for all chat functionality. Check the `sendMessage` function and inspect the `body` being sent to the backend.
    -   [[spa-booking-frontend/lib/api.ts]]: Check the `api.chat.sendMessage` function and the `CHATBOT_API_URL`.
    -   Use browser developer tools to check the network request to `/chat` and its response.

---

## Chatbot Issues

Problems related to conversation flow and understanding.

#### **Problem: Chatbot misunderstands the user's message (wrong intent or entities).**
-   **Where to Look**: The Natural Language Understanding (NLU) pipeline.
-   **Files**:
    -   [[chatbot/nlu/nlu_pipeline.py]]: The entry point for NLU. Check how the text is processed.
    -   [[chatbot/nlu/intent_classifier.py]]: Check the logic for determining user intent (`book_massage`, `faq`, etc.).
    -   [[chatbot/nlu/entity_extractor.py]]: Check the rules or models used to extract information like dates, numbers, and names.

#### **Problem: Chatbot has correct info but gets stuck or asks the wrong question.**
-   **Where to Look**: The dialogue state and policy management.
-   **Files**:
    -   [[chatbot/conversation/slot_filling.py]]: Check how the `BookingContext` is being updated. The chatbot might not be storing the extracted entities correctly.
    -   [[chatbot/conversation/policy.py]]: The logic for choosing the next action is here. Check the conditions for the different policies (`SlotFillingPolicy`, `FaqPolicy`, etc.).
    -   [[chatbot/app/chat_endpoint.py]]: Inspect the `ConversationState` object at the beginning and end of a request to see how it changes.

#### **Problem: Chatbot gives an error when trying to find shops or availability.**
-   **Where to Look**: The "tool" that calls the Booking API.
-   **Files**:
    -   [[chatbot/tools/search_tools.py]]: Check the relevant tool (e.g., `SearchAvailableSlotsTool`). Verify that it's receiving the correct data from the `BookingContext` to build its API request.
    -   [[chatbot/gateway/client.py]]: Check how the `HTTPClient` makes requests and handles errors from the Booking API.

#### **Problem: FAQ answer is wrong or enters the booking flow.**
-   **Where to Look**: The intent classification and FAQ policy.
-   **Files**:
    -   [[chatbot/nlu/intent_classifier.py]]: The intent might be wrongly classified as `book_massage` instead of `faq`.
    -   [[chatbot/conversation/policy.py]]: The `FaqPolicy` might not be triggering correctly, or the `SlotFillingPolicy` might be incorrectly taking precedence.
    -   [[chatbot/tools/search_tools.py]]: The `FAQSearchTool` might be failing to find relevant results in the `KnowledgeService`.

---

## Booking API / Backend Issues

Problems related to business logic, data, and external systems.

#### **Problem: A booking was not saved to the database.**
-   **Where to Look**: The booking service and database model.
-   **Files**:
    -   [[spa-booking-api/app/services/booking_service.py]]: The `create_booking` function contains the core logic. Check for errors, validation failures, or rollbacks.
    -   [[spa-booking-api/app/models/booking.py]]: Ensure the `Booking` model and its relationships are correctly defined.
    -   [[spa-booking-api/app/blueprints/bookings.py]]: Check the `create_booking` route for how it handles the request and calls the service.

#### **Problem: Availability is wrong (slots are shown when they shouldn't be, or vice-versa).**
-   **Where to Look**: The slot calculation service.
-   **Files**:
    -   [[spa-booking-api/app/services/slot_service.py]]: This file contains the entire logic for calculating availability. This is almost certainly the source of the issue.
    -   [[spa-booking-api/app/models/therapist_shift.py]]: Check that therapist shifts are correctly defined.
    -   [[spa-booking-api/app/models/booking.py]]: Check how existing bookings are queried.

#### **Problem: User gets a "Permission Denied" or 403 error.**
-   **Where to Look**: Authentication and endpoint protection.
-   **Files**:
    -   [[spa-booking-api/app/blueprints]]: Check the route in question for `@jwt_required()` and any role-checking decorators.
    -   [[spa-booking-frontend/lib/api.ts]]: Ensure `authFetch` is being used for the request and that the token is being attached.
    -   Decode the JWT being sent to the API to verify its contents (especially the `role`).

#### **Problem: Data is incorrect (e.g., wrong price, wrong duration).**
-   **Where to Look**: The service layer and the database models.
-   **Files**:
    -   The relevant service file in [[spa-booking-api/app/services]], which may be applying incorrect logic.
    -   The relevant model file in [[spa-booking-api/app/models]], which might have an incorrect default, relationship, or column type.
