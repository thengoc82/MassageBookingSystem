# Chatbot Architecture: Key Files

This document outlines the most important files in the chatbot's architecture, ranked in the order a developer should read them to build a mental model of the system.

## 1. Entrypoint and Configuration

These files are the starting point of the application and define its configuration.

### `chatbot/main.py`

-   **Role**: The main entry point for the chatbot application.
-   **Function**: Initializes and runs the FastAPI application using `uvicorn`. It creates the app by calling `create_app` from `chatbot/app/chat_endpoint.py`.
-   **Inputs**: None.
-   **Outputs**: A running `uvicorn` server.
-   **Dependencies**: `chatbot/app/chat_endpoint.py`.
-   **Called by**: The application server process.

### `chatbot/app/config.py`

-   **Role**: Application configuration management.
-   **Function**: Defines the `Settings` model using `pydantic-settings` to load configuration from environment variables (prefixed with `CHATBOT_`). This includes Redis URL, session settings, NLU thresholds, and knowledge base settings.
-   **Inputs**: Environment variables.
-   **Outputs**: A `Settings` object with application configuration.
-   **Dependencies**: `pydantic`.
-   **Called by**: `chatbot/app/chat_endpoint.py`.

## 2. Request Handling and Orchestration

This is the core of the request lifecycle, where incoming messages are processed and responses are generated.

### `chatbot/app/chat_endpoint.py`

-   **Role**: The main orchestrator of the chatbot's logic.
-   **Function**: Defines the FastAPI application, including the `/chat` endpoint. The `ChatEndpoint` class initializes all major components (NLU, policy manager, tool registry, session store) and its `process_message` method executes the full request-response cycle:
    1.  Loads the session state.
    2.  Runs the NLU pipeline.
    3.  Consults the `DialoguePolicyManager` for a decision.
    4.  Executes the decision (e.g., asking for a slot, running a tool).
    5.  Saves the updated state.
    6.  Returns a response to the user.
-   **Inputs**: `ChatRequest` model containing the user's message and session ID.
-   **Outputs**: `ChatResponse` model with the bot's reply and current state.
-   **Dependencies**: Almost all other key components (`nlu`, `policy`, `state`, `tools`, `session`, etc.).
-   **Called by**: The FastAPI router when a request hits the `/chat` endpoint.

## 3. State and Session Management

These files are responsible for maintaining the state of the conversation across multiple turns.

### `chatbot/session/store.py`

-   **Role**: Session data persistence.
-   **Function**: Implements the `RedisSessionStore`, which is responsible for creating, retrieving, saving, and deleting user session data in a Redis database.
-   **Inputs**: Session ID, `SessionData` model.
-   **Outputs**: `SessionData` model.
-   **Dependencies**: `redis`, `pydantic`, `chatbot/conversation/state.py`.
-   **Called by**: `chatbot/app/chat_endpoint.py`.

### `chatbot/conversation/state.py`

-   **Role**: Defines the structure of the conversation's state.
-   **Function**: Contains the Pydantic models that define the entire state of a conversation:
    -   `ConversationState`: The main container, holding the current phase, booking context, tool results, etc.
    -   `BookingContext`: Holds all the information related to a booking (e.g., `shop_id`, `date`, `course_id`).
    -   `RecentToolResults`: Caches the output of recent tool calls.
    -   `ConversationPhase`: An enum defining the different stages of the conversation.
-   **Inputs**: None.
-   **Outputs**: Data models for conversation state.
-   **Dependencies**: `pydantic`, `chatbot/nlu/models.py`.
-   **Called by**: Virtually every part of the system that needs to read or write conversation state.

### `chatbot/conversation/dialogue_state_tracker.py`

-   **Role**: A high-level wrapper for managing conversation state.
-   **Function**: Provides a more abstract interface for loading, saving, and updating the `ConversationState` for a given session. It acts as a convenience layer on top of the `RedisSessionStore`.
-   **Inputs**: Session ID.
-   **Outputs**: `ConversationState`.
-   **Dependencies**: `chatbot/conversation/state.py`, `chatbot/session/store.py`.
-   **Called by**: Potentially higher-level orchestration logic (though `chat_endpoint.py` handles much of this directly).

## 4. Natural Language Understanding (NLU)

The NLU pipeline is responsible for understanding the user's raw text message.

### `chatbot/nlu/nlu.py`

-   **Role**: The main facade for the NLU pipeline.
-   **Function**: The `NLU` class's `understand` method takes a raw text message and the current conversation state, and returns a structured `NLUResult`. It coordinates the different parts of the NLU process.
-   **Inputs**: Raw user message string, `ConversationState`.
-   **Outputs**: `NLUResult` object containing the classified intent and extracted entities.
-   **Dependencies**: `chatbot/nlu/intent_classifier.py`, `chatbot/nlu/entity_extractor.py`.
-   **Called by**: `chatbot/app/chat_endpoint.py`.

### `chatbot/nlu/intent_classifier.py`

-   **Role**: Determines the user's intent.
-   **Function**: Uses a combination of regex patterns and keyword matching to classify the user's intent (e.g., `CREATE_BOOKING`, `LOOKUP_BOOKING`, `FAQ`). It also includes logic to break ties between potential intents.
-   **Inputs**: Raw user message string.
-   **Outputs**: An `Intent` enum and a confidence score.
-   **Dependencies**: `chatbot/nlu/models.py`.
-   **Called by**: `chatbot/nlu/nlu.py`.

### `chatbot/nlu/entity_extractor.py`

-   **Role**: Extracts structured information (entities) from the user's message.
-   **Function**: Uses a series of specialized parsers to find and extract entities like dates (`date_parser.py`), times (`time_parser.py`), duration, number of people, and named entities (shops, courses, therapists) from the text.
-   **Inputs**: Raw user message string.
-   **Outputs**: A list of `Entity` objects.
-   **Dependencies**: `chatbot/nlu/date_parser.py`, `chatbot/nlu/time_parser.py`, `word2number`.
-   **Called by**: `chatbot/nlu/nlu.py`.

## 5. Dialogue Management and Logic

This is the "brain" of the chatbot, deciding what to do at each step of the conversation.

### `chatbot/conversation/policy.py`

-   **Role**: The core decision-making engine of the chatbot.
-   **Function**: The `DialoguePolicyManager`'s `decide` method is the central component. It takes the current `ConversationState` and the `NLUResult` and returns a `PolicyDecision` that specifies the next `Action` to take (e.g., `ASK_SLOT`, `RUN_TOOL`, `CONFIRM_ACTION`). It implements the logic for the booking flow, confirmation handling, and error recovery.
-   **Inputs**: `ConversationState`, `Intent`.
-   **Outputs**: `PolicyDecision` object.
-   **Dependencies**: `chatbot/conversation/state.py`, `chatbot/nlu/models.py`.
-   **Called by**: `chatbot/app/chat_endpoint.py`.

### `chatbot/conversation/slot_filling.py`

-   **Role**: Manages the process of collecting required information from the user.
-   **Function**: The `SlotFillingManager` is responsible for identifying which pieces of information (slots) are missing for a given task (like `search_slots`) and generating prompts to ask the user for that information. It continues this process until all required slots for an action are filled.
-   **Inputs**: `ConversationState`, user message.
-   **Outputs**: A tuple indicating if slot filling is complete, the next prompt message, and any associated data.
-   **Dependencies**: `chatbot/conversation/state.py`, `chatbot/nlu/nlu.py`, `chatbot/conversation/slot_parser.py`.
-   **Called by**: `chatbot/app/chat_endpoint.py`.

### `chatbot/conversation/tool_orchestrator.py`

-   **Role**: Executes tools based on the policy's decision.
-   **Function**: This class is responsible for taking a proposed action from the policy, validating it, and executing the corresponding tool from the `ToolRegistry`. It handles the lifecycle of an action, including proposing write actions and executing them after confirmation.
-   **Inputs**: `ConversationState`, `Plan` (from the planner).
-   **Outputs**: The result of the tool execution.
-   **Dependencies**: `chatbot/tools/registry.py`, `chatbot/conversation/state.py`.
-   **Called by**: Higher-level orchestration logic (e.g., `chat_endpoint.py`).

## 6. External System Integrations (Tools & Knowledge)

These files define how the chatbot interacts with the outside world, such as backend APIs and the knowledge base.

### `chatbot/tools/registry.py`

-   **Role**: A central registry for all available tools.
-   **Function**: The `ToolRegistry` class holds a dictionary mapping tool names to their respective `BaseTool` implementations. This allows the orchestrator to dynamically look up and execute tools by name.
-   **Inputs**: Tool name, `BaseTool` instance.
-   **Outputs**: `BaseTool` instance.
-   **Dependencies**: `chatbot/tools/base.py`.
-   **Called by**: `chatbot/app/chat_endpoint.py` (to register tools), `chatbot/conversation/tool_orchestrator.py` (to get tools).

### `chatbot/knowledge/knowledge_service.py`

-   **Role**: High-level interface for the knowledge base (for RAG/FAQ).
-   **Function**: The `KnowledgeService` provides a simple `query` method that takes a user's text query, embeds it using an `EmbeddingService`, and searches a `VectorStore` for the most relevant information.
-   **Inputs**: User query string.
-   **Outputs**: A list of `KnowledgeResult` objects.
-   **Dependencies**: `chatbot/knowledge/embedding_service.py`, `chatbot/knowledge/vector_store.py`.
-   **Called by**: The `FAQSearchTool` (which is in turn called by the `chat_endpoint`).

### `chatbot/conversation/planner.py`

-   **Role**: An LLM-based planner for creating multi-step plans (more advanced, less used currently than `policy.py`).
-   **Function**: The `Planner` uses an LLM to generate a `Plan` object based on the current conversation state and user input. This represents a more dynamic, AI-driven approach to dialogue management, contrasting with the rule-based `DialoguePolicyManager`.
-   **Inputs**: `ConversationState`, user input.
-   **Outputs**: A `Plan` object.
-   **Dependencies**: `chatbot/app/llm.py`, `chatbot/tools/registry.py`, `chatbot/prompts/plan.py`.
-   **Called by**: Potentially by the main orchestrator, as an alternative to the policy manager.
