
# `chatbot/conversation/slot_filling.py`

## 1. Purpose

This file defines the `SlotFillingManager`, a specialized sub-system responsible for gathering the specific pieces of information (the "slots") required to execute a tool. When the main `DialoguePolicyManager` decides to run a tool like `search_slots`, it doesn't ask all the questions itself. Instead, it delegates the task of collecting the necessary prerequisites (like `shop_id`, `date`, `duration`) to this manager. The `SlotFillingManager` then engages in a sub-dialogue with the user, asking questions one by one until all required slots are filled.

## 2. Where it fits

The Slot-Filling Manager is a stateful loop that runs under the direction of the `ChatEndpoint` when the conversation state indicates a tool is pending execution (`state.pending_read_action`).

```text
`ChatEndpoint`'s `process_message` method
    ↓
Checks `state.pending_read_action`. If it's set (e.g., to "search_slots")...
    ↓
Calls `slot_filling_manager.continue_filling(state, message)` from this file
    ↓
`continue_filling` does the following:
    1.  Parses the user's message for any relevant entities.
    2.  Applies valid entities to the `booking_context`.
    3.  Invalidates any dependent slots (e.g., changing the shop invalidates the selected course).
    4.  Checks the list of required slots for the pending action.
    5.  Finds the next missing slot.
    ↓
**If a slot is still missing:**
    Returns `(False, "Prompt for the missing slot", data)` to the `ChatEndpoint`.
**If all slots are now filled:**
    Returns `(True, "All info collected", None)` to the `ChatEndpoint`.
    ↓
`ChatEndpoint` then proceeds to execute the tool.
```

## 3. Inputs

*   **`state: ConversationState`**: The full, mutable conversation state. The manager reads the `pending_read_action` and `pending_slot_to_fill` from it and writes the extracted entity values directly into `state.booking_context`.
*   **`message: str`**: The user's latest message, which is parsed for information.
*   **`nlu_result: NLUResult`**: (Optional) The pre-computed NLU result for the message, which `parse_message` can use to avoid re-running the NLU.
*   **Dependencies (in `__init__`)**:
    *   `conversation_manager: ConversationManager`: A helper for state manipulation.
    *   `nlu: NLU`: The NLU engine, used to parse the user's message for entities.

## 4. Outputs

The main `continue_filling` method returns a tuple: `(is_complete, message, data)`.

*   **`is_complete: bool`**:
    *   `False`: More information is needed. The loop should continue.
    *   `True`: All required slots for the pending action have been filled. The `ChatEndpoint` can now proceed to execute the tool.
*   **`message: str`**: The prompt to send back to the user (e.g., "What date would you like to book for?").
*   **`data: dict | None`**: Any supplementary data for the frontend, like a list of options to display as buttons.

## 5. Important functions/classes

```text
class SlotFillingManager
    ↓
Purpose: To manage the process of gathering required information for a specific task.
```

```text
continue_filling(state, message, nlu_result)
    ↓
Purpose: To process one turn of a slot-filling sub-dialogue. This is the main entry point for the manager.
    ↓
Input: The conversation state and the user's latest message.
    ↓
What it does:
    1.  **Determines Requirements**: Identifies the list of required slots for the `state.pending_read_action`.
    2.  **Parses Message**: Calls `parse_message` to extract any entities from the user's utterance.
    3.  **Applies Results**: Calls `_apply_parse_result` to validate and save the extracted entities into the `state.booking_context`. This method also handles invalidating dependent slots (e.g., changing `shop_id` clears `course_id`).
    4.  **Handles Invalid Input**: If the user provides an invalid value for a requested slot, it increments a retry counter and, after a few failures, gives up and resets.
    5.  **Finds Next Missing Slot**: It checks the requirements again to find the next piece of information it needs.
    6.  **Decides Outcome**:
        *   If a slot is still missing, it formats a new question using `get_prompt` and returns `False`.
        *   If all slots are filled, it returns `True`, signaling that the loop is complete.
    ↓
Output: A tuple `(is_complete, message, data)` indicating whether the process is finished and what to say next.
```

```text
_apply_parse_result(result, state) -> bool
    ↓
Purpose: To take the parsed entities and safely apply them to the conversation state.
    ↓
Input: A `ParseResult` object and the `ConversationState`.
    ↓
What it does:
    1.  Iterates through the entities found by the parser.
    2.  Validates each entity's value using `_validate_slot`.
    3.  If valid, it updates the corresponding field in `state.booking_context` (e.g., `state.booking_context.date = '2026-08-12'`).
    4.  After updating a slot, it calls `_invalidate_dependencies` to clear any other slots that are no longer valid (e.g., changing the date invalidates the previously selected `start_time`).
    ↓
Output: A boolean indicating if at least one valid slot was successfully applied.
```

## 6. Execution flow

1.  The `DialoguePolicyManager` decides to run the `search_slots` tool, but sees that `date` is missing. It returns a decision: `ASK_SLOT` for `date`, and sets `state.pending_read_action = "search_slots"`.
2.  The `ChatEndpoint` receives this, sets `state.pending_slot_to_fill = "date"`, and asks the user, "What date would you like to book for?".
3.  The user replies, "tomorrow".
4.  On the next turn, the `ChatEndpoint` sees `state.pending_read_action` is set, so it calls `slot_manager.continue_filling(state, "tomorrow")`.
5.  `continue_filling` calls `parse_message("tomorrow")`, which returns a `DATE` entity with tomorrow's date string.
6.  `_apply_parse_result` is called. It validates the date and updates `state.booking_context.date`.
7.  `continue_filling` then re-checks the required slots for "search_slots". It finds that all are now filled.
8.  It returns `(True, "I have all the information...", None)`.
9.  The `ChatEndpoint` sees `True`, knows the slot-filling is done, and proceeds to execute the `search_slots` tool.

## 7. Dependencies

*   **`ConversationManager` & `ConversationState`**: Used to read and write to the conversation's state.
*   **`NLU`**: The NLU engine is used by the `parse_message` utility to extract entities from the user's response.
*   **`slot_parser.py` & `slot_prompts.py`**: Helper modules that contain the logic for parsing a message for a specific slot and for getting the canned text prompt for asking about a slot.

## 8. Relationship with other files

```text
This file (conversation/slot_filling.py)
 ├── is called by → app/chat_endpoint.py
 ├── uses the → nlu/nlu.py module for parsing
 ├── manipulates → conversation/state.py objects
 └── uses helpers from → conversation/slot_parser.py and conversation/slot_prompts.py
```

## 9. Important state/data

This manager is highly state-driven and operates directly on the `ConversationState` object. The key fields it uses are:

*   **`state.pending_read_action: str`**: The name of the tool that is waiting for information. This is the *reason* the slot-filling loop is active.
*   **`state.pending_slot_to_fill: str`**: The specific slot the manager asked for on the *previous* turn. This helps it focus its parsing and validate the user's answer.
*   **`state.booking_context: BookingContext`**: The manager's primary goal is to fill in the fields of this object.
*   **`REQUIRED_SLOTS: dict`**: A static dictionary that acts as a schema, defining which slots are required for each tool/action. This is the rulebook for the manager.
*   **`SLOT_DEPENDENCIES: dict`**: A static dictionary defining the dependency graph between slots, used to ensure data consistency.

## 10. What I should understand

1.  **It's a Sub-Routine of the Main Dialogue:** This manager handles a specific, temporary goal: "collect info for this one tool." It takes control of the conversation for a few turns and then hands control back to the main `ChatEndpoint` and `DialoguePolicyManager`.
2.  **It's Driven by a Schema (`REQUIRED_SLOTS`):** The logic is not arbitrary; it follows a clear set of requirements defined in the `REQUIRED_SLOTS` dictionary. This makes it predictable and easy to configure.
3.  **It Handles User Corrections and Invalid Input:** The manager has built-in logic for retries and for invalidating data. If a user changes their mind about the date, the manager knows to clear the previously selected time slot, because time depends on date.
4.  **It's Both a Parser and a Prompter:** In each turn, it first tries to *parse* the user's message for answers, and then, if more information is needed, it *prompts* for the next missing piece.
5.  **Separation of Concerns:** It cleanly separates the task of information gathering from the main conversational policy, making the `DialoguePolicyManager` simpler and more focused on high-level strategy.

## 11. Potential confusing parts

*   **`start` vs. `continue_filling`**: The `start` method seems to just be a simple wrapper that sets the initial state and then immediately calls `continue_filling`. The main logic is always in `continue_filling`.
*   **Who is in Control?**: It can be tricky to see who is driving. The `DialoguePolicyManager` initiates the process by setting `pending_read_action`. Then, the `SlotFillingManager` takes over for a few turns. Once it's done, the `ChatEndpoint` is responsible for calling the final tool. It's a three-part choreography.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the chatbot's diligent "form filler."** When the main policy brain decides it needs to perform a complex action (like searching for slots), it hands a form (`REQUIRED_SLOTS`) to this manager. The manager then takes over the conversation, methodically asking the user for one piece of information at a time, checking it for errors, and neatly filling in the boxes on the form. Once every required box is filled, it hands the completed form back and says, "Ready to proceed."
