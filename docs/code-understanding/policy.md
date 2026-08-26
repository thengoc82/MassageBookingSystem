
# `chatbot/conversation/policy.py`

## 1. Purpose

This file defines the `DialoguePolicyManager`, which is the core **decision-making engine** or "brain" of the chatbot. Its sole purpose is to look at the current state of the conversation, the user's intent (from the NLU), and a set of predefined rules, and decide on the single next `Action` the bot should take. It determines the conversational flow, deciding whether to ask for more information, run a tool to fetch data, confirm an action with the user, or end the conversation.

## 2. Where it fits

The policy manager is a central component in the `ChatEndpoint`'s processing pipeline. It is called after the NLU has processed the user's message.

```text
`ChatEndpoint`'s `process_message` method
    ↓
`NLU.understand()` produces an `NLUResult` (intent + entities)
    ↓
`DialoguePolicyManager.decide(state, intent)` is called from this file
    ↓
The policy evaluates the state and intent against its internal rules
    ↓
It returns a `PolicyDecision` object (e.g., `action=RUN_TOOL`, `tool='search_shops'`)
    ↓
`ChatEndpoint` executes the action described in the decision
```

## 3. Inputs

The main `decide` method takes:

*   **`state: ConversationState`**: The complete state of the current conversation, including the `booking_context` (what's been filled so far), any pending actions, and recent tool results.
*   **`intent: str`**: The user's intent as determined by the NLU module (e.g., `CREATE_BOOKING`, `FAQ`).
*   **`message: str`**: The raw user message, used for some specific checks (like "yes" or "no").
*   **`nlu_result: NLUResult`**: (Optional) The full NLU result, although the policy primarily operates on the high-level `intent`.

## 4. Outputs

*   **`PolicyDecision`**: A structured data object that represents a command for the `ChatEndpoint`. It contains:
    *   `action: Action`: The single most important field, an enum value like `ASK_SLOT`, `RUN_TOOL`, or `CONFIRM_ACTION`.
    *   `tool: str | None`: The name of the tool to run if the action is `RUN_TOOL`.
    *   `slot: str | None`: The name of the slot to ask for if the action is `ASK_SLOT`.
    *   `goal: Goal | None`: The overall user goal this decision is working towards (e.g., `BOOK_APPOINTMENT`).
    *   `message: str | None`: A pre-formatted message to be sent to the user, if applicable.

## 5. Important functions/classes

```text
class DialoguePolicyManager
    ↓
Purpose: A stateless class (it has no `self` state) that contains the logic for making conversational decisions.
```

```text
decide(state, intent, message, nlu_result)
    ↓
Purpose: The main entry point to the policy. It acts as a master dispatcher, routing the decision-making process to more specific sub-handlers based on the current context.
    ↓
Input: The conversation state, user intent, and message.
    ↓
What it does (The Decision Tree):
    1.  **Recovery**: Checks if a tool has failed too many times and decides to end the conversation.
    2.  **Confirmation Gate**: If the bot is waiting for a "yes/no" confirmation (`state.pending_confirm`), it immediately calls `_decide_confirmation` and stops.
    3.  **Explicit Commands**: Handles high-priority intents like `RESET` or `CANCEL_ACTION`.
    4.  **Goal Routing**: Based on the `intent`, it dispatches to a more specific decision method: `_decide_write_intent`, `_decide_lookup`, `_decide_faq`, or the default, `_decide_booking`.
    ↓
Output: A `PolicyDecision` object.
```

```text
_decide_booking(state, intent, message) -> PolicyDecision
    ↓
Purpose: To manage the step-by-step logic of the main booking flow. This is the core sequential logic of the chatbot.
    ↓
Input: The conversation state.
    ↓
What it does:
    1.  Calls `_next_booking_step` to determine the next action.
```

```text
_next_booking_step(state) -> PolicyDecision
    ↓
Purpose: To figure out the very next step required to complete a booking.
    ↓
Input: The conversation state.
    ↓
What it does:
    1.  **Checks Prerequisites**: It iterates through a defined sequence of required slots (`shop_id`, `date`, `course_id`, `start_time`, etc.).
    2.  **Runs Tools if Needed**: For a given step, it checks if a tool needs to be run to gather information. For example, if `course_id` is the next missing slot, it first checks if the `searchCourses` tool has already been run. If not, it returns a decision to `RUN_TOOL` for `search_courses`.
    3.  **Asks for Missing Slot**: If no tool needs to be run, and a slot is missing, it returns a decision to `ASK_SLOT` for that specific slot.
    4.  **Moves to Confirmation**: If all slots in the sequence are filled, it returns a decision to `CONFIRM_ACTION`, packaging up all the booking data for a final review by the user.
    ↓
Output: A `PolicyDecision` object commanding the next step in the booking flow.
```

## 6. Execution flow

1.  The `ChatEndpoint` calls `policy.decide(state, intent='CREATE_BOOKING')`.
2.  The `decide` method sees the intent is for booking and calls `_decide_booking`.
3.  `_decide_booking` calls `_next_booking_step`.
4.  `_next_booking_step` checks the `state.booking_context`. It sees `shop_id` is the first missing slot.
5.  It then checks if the `searchShops` tool has already been run by looking at `state.recent_tool_results`. It has not.
6.  It returns a `PolicyDecision(action=Action.RUN_TOOL, tool='search_shops')`.
7.  The `ChatEndpoint` receives this decision and executes the `searchShops` tool. The tool's results are saved to the state.
8.  **On the next turn**, the user picks a shop. The NLU extracts the `shop_id`.
9.  The `ChatEndpoint` calls `policy.decide()` again.
10. `_next_booking_step` runs again. It sees `shop_id` is now filled. The next missing slot is `date`.
11. It sees that no tool is required to get the date.
12. It returns a `PolicyDecision(action=Action.ASK_SLOT, slot='date')`.
13. The `ChatEndpoint` receives this decision and asks the user for the date.
14. This cycle continues until all slots are filled and the policy returns a `CONFIRM_ACTION` decision.

## 7. Dependencies

*   **`ConversationState`**: The policy is completely dependent on the structure and content of the state object to make its decisions.
*   **`Intent` enum**: It uses the intent provided by the NLU as its primary input signal.
*   **`Action` enum**: It uses this enum to define its possible output commands.

## 8. Relationship with other files

```text
This file (conversation/policy.py)
 ├── is called by → app/chat_endpoint.py
 ├── uses models from → conversation/state.py
 └── uses enums from → nlu/models.py (specifically `Intent`)
```

## 9. Important state/data

This policy manager is **stateless**. It does not have any `self` attributes that change between calls. It is a pure function that takes `state` as input and returns a `decision`. The important data it *operates on* is:

*   **`state.booking_context`**: It constantly checks which fields in the booking context are filled.
*   **`state.pending_confirm`**: The presence of this dictionary is a critical flag that puts the policy into a confirmation mode.
*   **`_BOOKING_TOOL_CHAIN` / sequence**: This hardcoded list defines the required order of operations for the booking flow. It is the "script" that the policy follows.

## 10. What I should understand

1.  **It is a Hardcoded Rule-Based System:** The policy's logic is a large, explicit decision tree implemented with `if/elif/else` statements. It is not a machine learning model. This makes it deterministic and debuggable.
2.  **It Separates "What" from "How":** The policy's job is to decide *what* to do (e.g., "run the search shops tool"), not *how* to do it. The "how" is handled by the `ChatEndpoint` and the tools themselves.
3.  **It Manages the Conversational Flow:** This is the component that prevents the bot from asking for the time before it knows the date, or asking for a therapist before a time slot is chosen. It enforces the logical sequence of the conversation.
4.  **It Has a "Memory" via the State Object:** Although the policy itself is stateless, it has access to the full conversation state, including `recent_tool_results`. This allows it to make decisions like "don't run `searchShops` again if we just ran it."
5.  **Confirmation is a Gated Step:** The policy explicitly handles a confirmation "gate". When it needs to confirm a destructive action (like creating a booking), it sets `state.pending_confirm` and returns a `CONFIRM_ACTION`. On the next turn, it enters a special `_decide_confirmation` block to handle the user's "yes" or "no" response.

## 11. Potential confusing parts

*   **The Many `_decide_*` methods:** The main `decide` method is a dispatcher. To understand a specific flow (like booking vs. lookup), you need to trace the logic to the correct sub-handler (e.g., `_decide_booking`).
*   **Implicit State Changes:** Many of the policy methods modify the `state` object directly (e.g., `state.current_goal = Goal.BOOK_APPOINTMENT`). This is a key part of how it works, but it's a side effect. The function's primary return is the `PolicyDecision`, but it also updates the state object that will be saved back to Redis.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the chatbot's "cerebellum," responsible for coordinating the sequence of actions needed to achieve a goal.** It's a stateless, rule-based referee that looks at the current game state (the `ConversationState`) and the last play (the user's `Intent`) and blows the whistle to signal the next required action—whether that's asking a player for the ball (`ASK_SLOT`), sending a scout to gather information (`RUN_TOOL`), or asking the team captain for final confirmation (`CONFIRM_ACTION`). It doesn't play the game itself, but it dictates the flow of the game turn by turn.
