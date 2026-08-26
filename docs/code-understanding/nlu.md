
# `chatbot/nlu/nlu.py`

## 1. Purpose

This file defines the `NLU` class, which serves as the main entry point and facade for the entire Natural Language Understanding pipeline. Its primary purpose is to take a raw user message and the current conversation state, and process it through a series of steps to determine the user's **intent** (what they want to do) and extract structured **entities** (the specific pieces of information in their message). It coordinates the `IntentClassifier` and the `EntityExtractor` to produce a single, structured `NLUResult` object.

## 2. Where it fits

The NLU module is the very first stage in the chatbot's message processing pipeline, as orchestrated by the `ChatEndpoint`.

```text
`ChatEndpoint` receives a message
    ↓
Calls `nlu.understand(message, state)` from this file
    ↓
This file's `understand` method orchestrates:
    1. `classify_intent` (from `intent_classifier.py`)
    2. `detect_correction` (from `entity_extractor.py`)
    3. `self._extractor.extract` (from `entity_extractor.py`)
    4. `break_tie` (from `intent_classifier.py`)
    ↓
Returns a structured `NLUResult` object back to the `ChatEndpoint`
```

## 3. Inputs

*   **`message: str`**: The raw text message from the user.
*   **`state: ConversationState`**: (Optional) The current state of the conversation. This is used by some sub-modules to resolve ambiguities (though this is being phased out) and understand context.
*   **`focused_slot: str`**: (Optional) A hint indicating which specific piece of information (slot) the chatbot is currently asking for. This helps the `EntityExtractor` prioritize its search.
*   **Knowledge Items**: The `NLU` instance is initialized with and can be updated with `known_shops`, `known_courses`, and `known_therapists`. This "knowledge" is passed to the `EntityExtractor` to allow it to recognize specific names and map them to IDs.

## 4. Outputs

*   **`NLUResult`**: A data class object containing:
    *   `intent`: The classified `Intent` enum (e.g., `CREATE_BOOKING`, `FAQ`).
    *   `intent_confidence`: A float score indicating the classifier's confidence.
    *   `entities`: A list of `Entity` objects that were extracted (e.g., `EntityType.DATE` with value `2026-08-12`).
    *   `ambiguities`: A list of potential ambiguities (currently unused).
    *   `raw_message`: The original user message.

## 5. Important functions/classes

```text
class NLU
    ↓
Purpose: To act as a stateful container for the NLU pipeline, primarily holding the `EntityExtractor` instance which contains the "known items" knowledge base.
    ↓
Input: (on initialization) Optional lists of known shops, courses, and therapists.
    ↓
What it does:
    - `__init__()`: Initializes an instance of the `EntityExtractor`, passing the known items to it.
    - `set_known_items()`: A crucial method that allows the `ChatEndpoint` to dynamically update the NLU's knowledge. For example, after fetching the courses for a specific shop, this method is called to make the NLU aware of them for subsequent processing.
    - `understand()`: The main method that executes the entire NLU pipeline.
```

```text
understand(message, state, focused_slot)
    ↓
Purpose: To orchestrate the step-by-step process of turning raw text into structured understanding.
    ↓
Input: The user's message, conversation state, and an optional focused slot.
    ↓
What it does:
    1.  **Intent Classification**: It first calls `classify_intent` from the `intent_classifier` module, which uses regex patterns and keywords to get an initial guess at the user's intent.
    2.  **Question Heuristic**: It applies a simple but effective rule: if the message looks like a question (ends with '?' or starts with a question word), it overrides the intent to `Intent.FAQ` to prevent misclassification.
    3.  **Correction Detection**: It calls `detect_correction` to see if the user is trying to change a previous piece of information.
    4.  **Entity Extraction**: It calls `self._extractor.extract()`, which runs a battery of regexes and other parsers to find all possible entities (dates, times, durations, shop names, etc.) in the text.
    5.  **Tie-Breaking**: If the initial intent confidence is low, it calls `break_tie`, which uses the presence of extracted entities to make a more informed guess about the intent. For example, if entities were found but the intent was `UNKNOWN`, it's upgraded to `PROVIDE_INFORMATION`.
    6.  **Result Assembly**: It constructs the final `NLUResult` object, packaging the intent, confidence, and entities together.
    7.  **Final Confidence Adjustment**: It calls `overall_confidence` to apply penalties based on ambiguities, slightly adjusting the final score.
    ↓
Output: A final, structured `NLUResult` object.
```

## 6. Execution flow

1.  `ChatEndpoint` calls `nlu.understand("book a massage for 2 people tomorrow at Shinjuku")`.
2.  `classify_intent` is called. It finds keywords like "book" and "massage" and returns `(Intent.CREATE_BOOKING, 0.9)`.
3.  The question heuristic does not match.
4.  `detect_correction` returns `False`.
5.  `self._extractor.extract` is called.
    *   It finds "2 people" and creates a `NUMBER_OF_PEOPLE` entity with value `2`.
    *   It finds "tomorrow" and creates a `DATE` entity with the corresponding date string.
    *   It searches for "Shinjuku" in its list of `_known_shops` and, upon finding a match, creates a `SHOP_ID` entity with the corresponding shop's ID.
    *   It returns a list of these three `Entity` objects.
6.  The `break_tie` logic is skipped because the initial confidence (0.9) is high.
7.  The final `NLUResult` is created containing the `CREATE_BOOKING` intent and the three extracted entities.
8.  This result is returned to the `ChatEndpoint`.

## 7. Dependencies

```text
intent_classifier.py
    ↓
    This module is responsible for the first and last steps of intent recognition. It provides `classify_intent` for the initial regex-based classification and `break_tie` to refine the classification using entity information.

entity_extractor.py
    ↓
    This module provides the `EntityExtractor` class, which does the heavy lifting of finding and parsing specific pieces of data from the user's message. It is the most complex dependency.

models.py
    ↓
    Provides the data structures (`NLUResult`, `Intent`, `Entity`, etc.) that are used as the inputs and outputs of this pipeline.
```

## 8. Relationship with other files

```text
This file (nlu/nlu.py)
 ├── is called by → app/chat_endpoint.py
 ├── uses → nlu/intent_classifier.py (to determine intent)
 ├── uses → nlu/entity_extractor.py (to extract data)
 └── uses models from → nlu/models.py
```

## 9. Important state/data

*   **`self._extractor: EntityExtractor`**: The only significant state held by the `NLU` class is its instance of the `EntityExtractor`.
*   **`self._extractor._known_shops` / `_known_courses`**: The state *within* the extractor is crucial. This "knowledge base" of known items is what allows the NLU to recognize named entities like "Shinjuku" and convert them into structured data (an ID). This knowledge is dynamic and can be updated mid-conversation.

## 10. What I should understand

1.  **It's a Pipeline:** The `understand` method is a clear, sequential pipeline of steps. It's not a single monolithic model but a series of transformations.
2.  **Rule-Based, Not ML-Based:** This NLU system is entirely rule-based. It relies on regular expressions, keyword lists, and heuristics. There are no machine learning models involved, which makes it fast, predictable, and easy to debug, but less flexible than a statistical model.
3.  **Dynamic Knowledge is Key:** The ability to call `set_known_items()` mid-conversation is a powerful feature. It allows the `ChatEndpoint` to perform a "multi-pass" NLU, where it can fetch data (like a list of courses for a shop) and then re-run the NLU with this new knowledge to better understand the user's original message.
4.  **Separation of Intent and Entities:** The system correctly separates the task of figuring out *what the user wants to do* (intent) from *what specific information they provided* (entities). These two streams of information are later combined by the `DialoguePolicyManager` to make a decision.
5.  **Confidence is Heuristic:** The confidence scores are not statistical probabilities. They are hand-tuned weights associated with the regex patterns. They are used as a guide for the system to know when it should be "sure" vs. when it should be cautious.

## 11. Potential confusing parts

*   **Stateful but Mostly Not:** The `NLU` class itself appears stateful because it's a class, but its primary `understand` method is stateless. The only state it holds is the `EntityExtractor`, which in turn holds the dynamic knowledge base. This is a clean way to manage the knowledge while keeping the processing logic itself pure.
*   **Commented-Out/Obsolete Code:** The code contains comments and empty method stubs (`_resolve_entities_against_state`) that refer to older ways of doing things. This indicates the design has evolved, with more logic being pushed into the `EntityExtractor` itself.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it acts as the chatbot's "ears and brainstem," performing the initial, reflexive processing of a user's message.** It runs a fast, rule-based assembly line: one worker identifies the user's general intent (like "wants to book"), while another worker simultaneously pulls out all the concrete details (like dates, times, and names). It then packages this structured understanding into a neat report (`NLUResult`) and hands it off to the higher-level parts of the brain (`DialoguePolicyManager`) for conscious decision-making.
