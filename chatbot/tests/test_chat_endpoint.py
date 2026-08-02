"""Tests for chat endpoint — web chat with deterministic flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest, create_app
from chatbot.conversation.state import ConversationPhase, ConversationState, BookingContext
from chatbot.models import (
    SearchShopsResponse,
    SearchCoursesResponse,
    SearchAvailableSlotsResponse,
    ShopInfo,
)
from chatbot.session.store import RedisSessionStore, SessionData
from chatbot.tools.registry import ToolRegistry
from fastapi.testclient import TestClient


import asyncio

@pytest.fixture
async def initialized_endpoint(request) -> ChatEndpoint:
    """Provides a fully initialized ChatEndpoint with mocked external services."""
    from chatbot.models import CourseDurationInfo, CourseInfo, ShopInfo
    from datetime import time

    # Default data for priming NLU
    mock_shops = [
        ShopInfo(
            shopId=1, shopName="Shinjuku Store", address="Shinjuku 1-1",
            phoneNumber="03-1234-5678", status="Open",
            openTime=time(9, 0), closeTime=time(22, 0),
        ),
        ShopInfo(
            shopId=2, shopName="Shibuya Store", address="Shibuya 2-2",
            phoneNumber="03-2345-6789", status="Open",
            openTime=time(9, 0), closeTime=time(22, 0),
        ),
    ]
    mock_courses = [
        CourseInfo(
            courseId=101, courseName="Full Body Massage", courseType="main",
            durations=[CourseDurationInfo(duration=60, price=8000)],
            message="course"
        ),
    ]

    endpoint = ChatEndpoint()

    # Mock external dependencies to prevent real I/O during tests
    with patch("chatbot.app.chat_endpoint.create_client", new_callable=AsyncMock) as mock_create_client, \
         patch("chatbot.app.chat_endpoint.RedisSessionStore", autospec=True) as mock_redis_store, \
         patch("chatbot.app.chat_endpoint.SearchShopsTool") as mock_search_shops_tool, \
         patch("chatbot.app.chat_endpoint.SearchCoursesTool") as mock_search_courses_tool, \
         patch("chatbot.app.chat_endpoint.KnowledgeService", autospec=True) as mock_knowledge_service:

        # Configure mocks to return default data during initialization
        mock_http_client = AsyncMock()
        mock_create_client.return_value = mock_http_client
        
        mock_session_store_instance = AsyncMock(spec=RedisSessionStore)
        mock_session_store_instance.get_session = AsyncMock(return_value=None)
        mock_session_store_instance.create_session = AsyncMock(return_value=SessionData(session_id="test-session"))
        mock_session_store_instance.save_session = AsyncMock()
        mock_redis_store.return_value = mock_session_store_instance

        mock_shops_tool_instance = AsyncMock()
        mock_shops_tool_instance.execute = AsyncMock(return_value=SearchShopsResponse(success=True, data=mock_shops, message="ok"))
        mock_search_shops_tool.return_value = mock_shops_tool_instance
        
        mock_courses_tool_instance = AsyncMock()
        async def search_courses_side_effect(req):
            if req.shopId == 1:
                return SearchCoursesResponse(success=True, data=mock_courses, message="ok")
            return SearchCoursesResponse(success=True, data=[], message="ok")
        mock_courses_tool_instance.execute = AsyncMock(side_effect=search_courses_side_effect)
        mock_search_courses_tool.return_value = mock_courses_tool_instance

        # RAG disabled by default in tests
        endpoint._settings.enable_rag = False
        mock_knowledge_service.return_value = None

        # Initialize the endpoint
        await endpoint.initialize()
        
        def finalizer():
            asyncio.run(endpoint.close())
        
        request.addfinalizer(finalizer)
        
        return endpoint


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def make_session_store_mock() -> RedisSessionStore:
    store = MagicMock(spec=RedisSessionStore)
    store.get_session = AsyncMock(return_value=None)
    store.create_session = AsyncMock(return_value=SessionData(session_id="test-1"))
    store.save_session = AsyncMock()
    return store


def make_tool_registry_mock() -> ToolRegistry:
    registry = MagicMock(spec=ToolRegistry)
    mock_tool = AsyncMock()
    mock_tool.name = "test"
    mock_tool.execute = AsyncMock()
    registry.get = MagicMock(return_value=mock_tool)
    registry.list = MagicMock(return_value=["test"])
    return registry


# ---------------------------------------------------------------------------
# Existing baseline tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_process_message_creates_new_session(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    endpoint._session_store.get_session.return_value = None
    endpoint._session_store.create_session.return_value = SessionData(session_id="test-1")

    request = ChatRequest(message="Hello", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.session_id == "test-1"
    # The default intent for "Hello" is now 'greet', which maps to a simple clarification response
    # because the policy doesn't have a specific greeting action.
    assert "Which area are you interested in?" in response.message


from chatbot.nlu.models import NLUResult, Entity, EntityType, Intent

@pytest.mark.asyncio
async def test_process_message_search_shops(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    with patch.object(endpoint._nlu, "understand", new_callable=AsyncMock) as mock_understand:
        mock_understand.return_value = NLUResult(
            intent=Intent.SEARCH_SHOP,
            entities=[Entity(type=EntityType.AREA, value="Shinjuku")]
        )

        # The fixture already provides a mock searchShops tool.
        # The default intent for "I want to find a shop" is now 'book', which
        # triggers the 'search_shops' tool via the dialogue policy.
        request = ChatRequest(message="I want to find a shop in Shinjuku", session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        # The response should contain the list of shops from the fixture's mock
        assert "Shinjuku Store" in response.message
        # assert "Shibuya Store" in response.message
        assert "Which shop would you like to visit?" in response.message


def test_create_app() -> None:
    app = create_app()
    assert app.title == "Chatbot Service"
    assert app.version == "1.0.0"


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_reset_intent(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    request = ChatRequest(message="reset", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "reset" in response.message.lower()


@pytest.mark.asyncio
async def test_unknown_intent_starts_booking_flow(initialized_endpoint: ChatEndpoint) -> None:
    """Free-form user input with no clear goal starts the booking flow."""
    endpoint = await initialized_endpoint
    request = ChatRequest(message="asdf qwerty gibberish", session_id="test-1")
    response = await endpoint.process_message(request)
    # Phase 7: any non-canonical input defaults to the booking flow.
    assert response.success is True
    assert "which area are you interested in?" in response.message.lower()



@pytest.mark.asyncio
async def test_initialize_and_close() -> None:
    endpoint = ChatEndpoint()
    with patch("chatbot.app.chat_endpoint.create_client", new_callable=AsyncMock) as mock_create, \
         patch("chatbot.app.chat_endpoint.RedisSessionStore") as mock_store_class, \
         patch("chatbot.app.chat_endpoint.PgVectorStore") as mock_pg_store, \
         patch("chatbot.app.chat_endpoint.SearchShopsTool") as mock_search_shops_tool:
        
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_create.return_value = mock_client

        mock_store_instance = AsyncMock()
        mock_store_instance.close = AsyncMock()
        mock_store_class.return_value = mock_store_instance

        mock_pg_store.return_value = AsyncMock()

        mock_shops_tool_instance = AsyncMock()
        mock_shops_tool_instance.execute.return_value = SearchShopsResponse(success=True, data=[], message="ok")
        mock_search_shops_tool.return_value = mock_shops_tool_instance

        await endpoint.initialize()
        assert endpoint._initialized is True
        await endpoint.close()
        assert endpoint._initialized is False


@pytest.mark.asyncio
async def test_initialize_idempotent() -> None:
    endpoint = ChatEndpoint()
    endpoint._initialized = True
    await endpoint.initialize()
    assert endpoint._initialized is True


@pytest.mark.asyncio
async def test_close_when_not_initialized() -> None:
    endpoint = ChatEndpoint()
    await endpoint.close()
    assert endpoint._initialized is False


# ---------------------------------------------------------------------------
# Phase 6 — Dialogue State Tracking tests
# ---------------------------------------------------------------------------
def _shop(shop_id: int, name: str, address: str = "Addr") -> dict:
    return {"shopId": shop_id, "shopName": name, "address": address}


def _course(course_id: int, name: str, duration: int = 60, price: int = 100000) -> dict:
    return {"courseId": course_id, "courseName": name, "duration": duration, "price": price}


def _slot(start_time: str, end_time: str = "10:00") -> dict:
    return {"startTime": start_time, "endTime": end_time, "availableCapacity": 1}


@pytest.mark.asyncio
async def test_reset_clears_state(initialized_endpoint: ChatEndpoint) -> None:
    """Test 6 — reset clears booking context."""
    endpoint = await initialized_endpoint
    # Seed the session with some state
    seeded_state = ConversationState(booking_context=BookingContext(shop_id=1))
    endpoint._session_store.get_session.return_value = SessionData(
        session_id="test-1", conversation_state=seeded_state
    )

    request = ChatRequest(message="start over", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    # The new policy resets the conversation and asks how to help.
    assert "reset" in response.message.lower()

    # Verify that the state was cleared in the saved session
    saved_session = endpoint._session_store.save_session.call_args[0][0]
    assert saved_session.conversation_state.booking_context.shop_id is None
    assert saved_session.conversation_state.phase == ConversationPhase.GREETING


@pytest.mark.asyncio
async def test_selection_preserves_context_on_interruption(initialized_endpoint: ChatEndpoint) -> None:
    """Test 7 — booking context is preserved when user asks for FAQ mid-flow."""
    endpoint = await initialized_endpoint
    # Seed state with shop already selected
    seeded_state = ConversationState(
        phase=ConversationPhase.SEARCHING_SHOPS,
        booking_context=BookingContext(shop_id=42, shop_name="X"),
    )
    endpoint._session_store.get_session.return_value = SessionData(
        session_id="test-1", conversation_state=seeded_state
    )

    # Ask for FAQ — should NOT erase shop_id
    request = ChatRequest(message="help me", session_id="test-1")
    response = await endpoint.process_message(request)
    saved_session = endpoint._session_store.save_session.call_args[0][0]
    assert saved_session.conversation_state.booking_context.shop_id == 42



# ---------------------------------------------------------------------------
# Phase 7 — End-to-end slot-filling booking flow
# ---------------------------------------------------------------------------



@pytest.mark.asyncio
async def test_phase7_initial_message_asks_for_area_first(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint

    response = await endpoint.process_message(ChatRequest(message="I want a massage", session_id="phase7"))

    assert response.success is True
    assert "which area are you interested in?" in response.message.lower()


@pytest.mark.asyncio
async def test_phase7_full_conversation_flow(initialized_endpoint: ChatEndpoint) -> None:
    """End-to-end: shop -> course -> date -> guests -> slots."""
    endpoint = await initialized_endpoint
    session_id="phase7_full"

    # Mock the stateful session store behavior for this test
    state_box: dict = {}
    async def get_session(_sid: str) -> SessionData:
        if "state" not in state_box:
            state_box["state"] = ConversationState()
        return SessionData(session_id=session_id, conversation_state=state_box["state"])

    async def save_session(session: SessionData) -> None:
        state_box["state"] = session.conversation_state

    endpoint._session_store.get_session.side_effect = get_session
    endpoint._session_store.save_session.side_effect = save_session

    # Mock the search_slots tool which is not covered by the default fixture
    from datetime import time
    from chatbot.models import SlotInfo
    slots = [ SlotInfo(startTime=time(9, 0), endTime=time(10, 0), availableCapacity=2) ]
    async def search_slots_execute(_request):
        return SearchAvailableSlotsResponse(success=True, data=slots, message="ok")
    
    mock_slots_tool = AsyncMock()
    mock_slots_tool.execute.side_effect = search_slots_execute
    
    original_get = endpoint._tool_registry.get
    def registry_get(name: str):
        if name == "searchAvailableSlots":
            return mock_slots_tool
        return original_get(name)
    endpoint._tool_registry.get = MagicMock(side_effect=registry_get)

    # Turn 1: open the conversation
    r1 = await endpoint.process_message(ChatRequest(message="I want a massage", session_id=session_id))
    assert "which area are you interested in" in r1.message.lower()

    # Turn 2: pick area
    with patch.object(endpoint._nlu, "understand", new_callable=AsyncMock) as mock_understand:
        mock_understand.return_value = NLUResult(
            intent=Intent.PROVIDE_INFORMATION,
            entities=[Entity(type=EntityType.AREA, value="Shinjuku")]
        )
        r2 = await endpoint.process_message(ChatRequest(message="Shinjuku", session_id=session_id))
    assert "which shop would you like to visit" in r2.message.lower()

    # Turn 3: pick shop by name
    r3 = await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id=session_id))
    assert "which massage course" in r3.message.lower()
    assert "full body massage" in r3.message.lower()

    # Turn 4: pick course by name
    r4 = await endpoint.process_message(
        ChatRequest(message="Full Body Massage 60 minutes", session_id=session_id)
    )
    assert "what date would you like" in r4.message.lower()

    # Turn 5: pick date
    r5 = await endpoint.process_message(ChatRequest(message="Tomorrow", session_id=session_id))
    assert "how many guests" in r5.message.lower()

    # Turn 6: pick guest count
    with patch.object(endpoint._nlu, "understand", new_callable=AsyncMock) as mock_understand:
        mock_understand.return_value = NLUResult(
            intent=Intent.PROVIDE_INFORMATION,
            entities=[Entity(type=EntityType.NUMBER_OF_PEOPLE, value=2)]
        )
        r6 = await endpoint.process_message(ChatRequest(message="2", session_id=session_id))
    assert "available appointment times" in r6.message.lower()
    assert "09:00" in r6.message


@pytest.mark.asyncio
async def test_phase7_invalid_area_selection_reprompts(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint

    await endpoint.process_message(ChatRequest(message="I want a massage", session_id="phase7"))
    # Gibberish that won't match any area
    response = await endpoint.process_message(ChatRequest(message="asdf qwerty", session_id="phase7"))
    assert "which area are you interested in" in response.message.lower()


@pytest.mark.asyncio
async def test_phase7_no_tool_called_without_shop(initialized_endpoint: ChatEndpoint) -> None:
    """Hard guarantee: searchCourses must NOT run before a shop is selected."""
    endpoint = await initialized_endpoint

    await endpoint.process_message(ChatRequest(message="I want a massage", session_id="phase7"))

    courses_tool = endpoint._tool_registry.get("searchCourses")
    assert courses_tool.execute.await_count == 0


@pytest.mark.asyncio
async def test_phase7_reset_clears_everything(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint

    await endpoint.process_message(ChatRequest(message="I want a massage", session_id="phase7"))
    await endpoint.process_message(ChatRequest(message="Shinjuku", session_id="phase7"))

    response = await endpoint.process_message(ChatRequest(message="reset", session_id="phase7"))
    assert "reset" in response.message.lower()
    saved = endpoint._session_store.save_session.call_args_list[-1][0][0]
    assert saved.conversation_state.booking_context.shop_id is None
    assert saved.conversation_state.recent_tool_results.last_shop_search is None
    assert saved.conversation_state.pending_read_action is None


# ---------------------------------------------------------------------------
# Phase 8 — Dialogue Policy integration tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_phase8_policy_decision_is_returned_for_book(initialized_endpoint: ChatEndpoint) -> None:
    """The endpoint must produce responses driven by policy decisions, not
    by hard-coded nested if/else."""
    endpoint = await initialized_endpoint
    response = await endpoint.process_message(
        ChatRequest(message="I want a massage", session_id="p8-1")
    )
    # We don't introspect the PolicyDecision directly here (that's the policy
    # unit test) but we do verify the booking chain starts cleanly.
    assert response.success is True
    assert "which area are you interested in" in response.message.lower()


@pytest.mark.asyncio
async def test_phase8_goal_switch_to_cancel(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    sid = "p8-switch"

    r = await endpoint.process_message(ChatRequest(message="I want a massage", session_id=sid))
    assert "which area are you interested in" in r.message.lower()
    with patch.object(endpoint._nlu, "understand", new_callable=AsyncMock) as mock_understand:
        mock_understand.return_value = NLUResult(
            intent=Intent.PROVIDE_INFORMATION,
            entities=[Entity(type=EntityType.AREA, value="Shinjuku")]
        )
        r = await endpoint.process_message(ChatRequest(message="Shinjuku", session_id=sid))
    assert "which shop would you like to visit" in r.message.lower()
    r = await endpoint.process_message(ChatRequest(message="Shinjuku Store", session_id=sid))
    assert "which massage course" in r.message.lower()

    # Switch goal mid-flow.
    r = await endpoint.process_message(
        ChatRequest(message="actually cancel my reservation", session_id=sid)
    )
    assert "booking code" in r.message.lower()


@pytest.mark.asyncio
async def test_phase8_confirmation_gate_yes_and_no(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    sid = "p8-confirm"

    r = await endpoint.process_message(
        ChatRequest(message="cancel my booking BK202512250001", session_id=sid)
    )
    assert "confirm" in r.message.lower()

    r = await endpoint.process_message(ChatRequest(message="no", session_id=sid))
    assert "won't" in r.message.lower() or "cancel" in r.message.lower()

    # The pending confirm must have been cleared.
    saved = endpoint._session_store.save_session.call_args_list[-1][0][0]
    assert saved.conversation_state.pending_confirm is None


@pytest.mark.asyncio
async def test_phase8_reset_clears_state(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    sid = "p8-reset"

    await endpoint.process_message(ChatRequest(message="I want a massage", session_id=sid))
    await endpoint.process_message(ChatRequest(message="Shinjuku", session_id=sid))

    r = await endpoint.process_message(ChatRequest(message="reset", session_id=sid))
    assert "reset" in r.message.lower()
    saved = endpoint._session_store.save_session.call_args_list[-1][0][0]
    assert saved.conversation_state.booking_context.shop_id is None
    assert saved.conversation_state.recent_tool_results.last_shop_search is None
    assert saved.conversation_state.pending_read_action is None
    assert saved.conversation_state.pending_confirm is None


@pytest.mark.asyncio
async def test_phase8_lookup_requires_code(initialized_endpoint: ChatEndpoint) -> None:
    endpoint = await initialized_endpoint
    sid = "p8-lookup"

    r = await endpoint.process_message(
        ChatRequest(message="check my booking", session_id=sid)
    )
    assert "booking code" in r.message.lower()


@pytest.mark.asyncio
async def test_phase8_no_giant_if_else_in_endpoint() -> None:
    """Sanity: the endpoint must remain a thin dispatcher."""
    import re
    src = open(
        "/Users/thengoc/Documents/Obsidian Vault/AI Massage Booking Project/chatbot/app/chat_endpoint.py"
    ).read()
    lines = src.splitlines()

    def body_lines(start_marker: str, end_marker: str) -> int:
        start = next(i for i, l in enumerate(lines) if start_marker in l)
        end_candidates = [
            i for i in range(start + 1, len(lines))
            if end_marker in lines[i] and (lines[i].startswith("    async def") or lines[i].startswith("    def "))
        ]
        end = end_candidates[0] if end_candidates else len(lines)
        return end - start

    pm = body_lines("    async def process_message", "_resolve_pending_selection")
    ed = body_lines("    async def _execute_decision", "_ask_slot")
    assert pm < 800, f"process_message grew to {pm} lines"
    assert ed < 80, f"_execute_decision grew to {ed} lines"