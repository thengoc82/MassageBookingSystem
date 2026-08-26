
# `chatbot/tools/search_tools.py`

## 1. Purpose

This file defines a collection of "search tools" that the chatbot can use to retrieve information. Each tool is a class that encapsulates the logic for making a specific query, either to the main booking API via an HTTP client or to the internal knowledge base. These tools represent the chatbot's ability to "read" or "look up" information from the outside world. They are the actions that are executed when the `DialoguePolicyManager` decides to run a read-only tool.

## 2. Where it fits

These tools are registered in the `ToolRegistry` within the `ChatEndpoint`. When the `ChatEndpoint` needs to execute a tool, it retrieves the appropriate class from the registry and calls its `execute` method.

```text
`ChatEndpoint`
    ↓
Gets a decision from `DialoguePolicyManager` (e.g., `action=RUN_TOOL`, `tool='search_shops'`)
    ↓
Looks up "searchShops" in its `ToolRegistry` to get an instance of `SearchShopsTool`
    ↓
Calls `tool.execute(request)` where `tool` is an instance of a class from this file
    ↓
The `execute` method uses its `_client` to make an HTTP GET request to the booking API
    ↓
The tool wraps the API response in a structured `*Response` Pydantic model
    ↓
The response object is returned to the `ChatEndpoint`
```

## 3. Inputs

*   **`http_client: HTTPClient`**: (For most tools) An instance of the HTTP client, which is dependency-injected during the tool's initialization. This client is used to make the actual API calls.
*   **`knowledge_service: KnowledgeService`**: (For `FAQSearchTool`) An instance of the knowledge base service, used for performing vector similarity searches.
*   **`request` Pydantic Model**: Each tool's `execute` method takes a specific Pydantic model as input (e.g., `SearchShopsRequest`, `SearchAvailableSlotsRequest`). This provides strong typing and validation for the arguments required to run the tool.

## 4. Outputs

*   **`*Response` Pydantic Model**: Each tool's `execute` method returns a `Promise` that resolves to a specific Pydantic response model (e.g., `SearchShopsResponse`, `SearchAvailableSlotsResponse`). These models structure the data received from the API call and include a `success` flag, a `message`, and the `data` payload.
*   **`ChatbotError`**: If a prerequisite is missing (e.g., trying to search for courses without a `shopId`), the tool can raise a `ChatbotError`, which is a custom exception that can be caught upstream.

## 5. Important functions/classes

This file primarily consists of tool classes that inherit from a `BaseTool`.

```text
class SearchShopsTool(BaseTool[SearchShopsRequest, SearchShopsResponse])
    ↓
Purpose: To fetch a list of all available shops.
    ↓
Logic:
    - It is initialized with an `HTTPClient`.
    - The `execute` method makes a simple `GET` request to the `/shops` endpoint of the booking API.
    - It then wraps the JSON response in a `SearchShopsResponse` object and returns it.
```

```text
class SearchAvailableSlotsTool(BaseTool[...])
    ↓
Purpose: To find available time slots based on a set of criteria.
    ↓
Logic:
    - It takes a `SearchAvailableSlotsRequest` which contains `shopId`, `date`, `duration`, etc.
    - The `execute` method constructs a dictionary of query parameters from the request object.
    - It makes a `GET` request to the `/shops/{shopId}/available-slots` endpoint with the constructed parameters.
    - It wraps the JSON response in a `SearchAvailableSlotsResponse` object.
```

```text
class FAQSearchTool(BaseTool[...])
    ↓
Purpose: To find relevant information from the internal knowledge base (vector database) to answer a user's question. This is the basis for the RAG (Retrieval-Augmented Generation) functionality.
    ↓
Logic:
    - It is initialized with a `KnowledgeService` instead of an HTTP client.
    - The `execute` method takes a `FAQSearchRequest` containing the user's `query`.
    - It calls `self._knowledge_service.query()`, which performs a vector similarity search in the database.
    - It formats the search results into a list of `FAQItem` objects and returns them within a `FAQSearchResponse`.
```

## 6. Execution flow

1.  The `ChatEndpoint` determines it needs to run the `searchAvailableSlots` tool.
2.  It retrieves the `SearchAvailableSlotsTool` instance from the `ToolRegistry`.
3.  It constructs a `SearchAvailableSlotsRequest` object using the information stored in the current `booking_context`.
4.  It calls `await tool.execute(request)`.
5.  Inside the tool's `execute` method:
    *   The path `/shops/123/available-slots` is constructed.
    *   The query parameters `{'date': '2026-08-12', 'duration': 60, ...}` are assembled.
    *   The `self._client.get()` method is called, which makes the actual `GET` request to the booking API.
6.  The booking API responds with a JSON payload.
7.  The tool receives the JSON and unpacks it into a `SearchAvailableSlotsResponse` Pydantic model (`SearchAvailableSlotsResponse(**response)`). This validates the structure of the API response.
8.  The `SearchAvailableSlotsResponse` object is returned up the call stack to the `ChatEndpoint`.

## 7. Dependencies

```text
HTTPClient (from `chatbot.gateway.client`)
    ↓
    The client used to make HTTP requests to the main booking API. This is the bridge to the outside world for most tools.

KnowledgeService (from `chatbot.knowledge.knowledge_service`)
    ↓
    The service used to interact with the vector database for RAG. This is a different kind of external dependency, pointing to an internal data source rather than a remote API.

Pydantic Models (from `chatbot.models`)
    ↓
    A large number of Pydantic models are imported to define the typed inputs (`*Request`) and outputs (`*Response`) for each tool. This enforces a strict data contract for each tool's interface.

BaseTool (from `chatbot.tools.base`)
    ↓
    A base class that the tools inherit from, likely providing some common functionality or structure.
```

## 8. Relationship with other files

```text
This file (tools/search_tools.py)
 ├── is registered and used by → app/chat_endpoint.py
 ├── makes API calls using → gateway/client.py
 ├── queries the knowledge base using → knowledge/knowledge_service.py
 └── uses data models from → models.py
```

## 9. Important state/data

The tool classes themselves are stateful only in that they hold a reference to the `_client` or `_knowledge_service`. They do not maintain any state between calls. The important data they handle is:

*   **`request` object**: The structured input for the tool.
*   **`response` object**: The structured output of the tool.

## 10. What I should understand

1.  **Tools are Typed API Wrappers:** Each tool is a clean, strongly-typed wrapper around a single API endpoint or service call. The use of Pydantic `*Request` and `*Response` models makes their inputs and outputs explicit and self-documenting.
2.  **Separation of Concerns is Clear:** This file is only concerned with *how to fetch data*. It contains no dialogue logic, no state management, and no complex business rules. It just executes a query and returns the result.
3.  **Two Kinds of Tools:** There are two distinct types of search tools here:
    *   **API Tools**: Most tools (`SearchShopsTool`, `SearchCoursesTool`, etc.) talk to the external booking API.
    *   **Knowledge Tool**: The `FAQSearchTool` talks to an internal knowledge base, demonstrating that the "tool" concept is abstract and can apply to different data sources.
4.  **The `execute` Method is the Workhorse:** For every tool, the `execute` method is the public entry point where the action happens.
5.  **Dependency Injection:** The tools are not hardcoded to a global client. They receive the `HTTPClient` or `KnowledgeService` in their constructor (`__init__`), which is a good practice that makes them easy to test with mocks.

## 11. Potential confusing parts

*   **`SearchAvailableSlotsResponse(**response)`**: This Python syntax is "dictionary unpacking." It takes a dictionary (the JSON response from the API) and passes its key-value pairs as keyword arguments to the Pydantic model's constructor. This is a concise way to create a Pydantic object from a dictionary, and it simultaneously validates that the dictionary has the expected keys and types.
*   **The `LookupBookingTool`'s Logic:** This tool has slightly more complex logic. It first tries to look up a booking by its code via a direct URL (`/bookings/{code}`). If that fails (raises an error), it falls back to searching by phone number. This is a small piece of business logic embedded within a tool.

## 12. One-paragraph mental model

If I remember only one thing about this file, it should be that **it is the chatbot's library of encyclopedias and phone books.** Each tool class is a specific book (like "The Directory of Shops" or "The Timetable of Available Slots"). When the chatbot's brain needs a piece of information, it picks the correct book off the shelf, turns to the right page by providing a structured `Request` (like looking up an entry), and the book returns a clean, structured `Response`. These tools are the bot's read-only access to the world's information.
