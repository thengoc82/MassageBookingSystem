"""Tests for chat endpoint — web chat with deterministic flow"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest, create_app
from chatbot.conversation.state import ConversationPhase, ConversationState
from chatbot.models import SearchShopsResponse
from chatbot.session.store import RedisSessionStore, SessionData
from chatbot.tools.registry import ToolRegistry
from fastapi.testclient import TestClient


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


@pytest.mark.asyncio
async def test_process_message_creates_new_session() -> None:
    endpoint = ChatEndpoint()
    endpoint._session_store = make_session_store_mock()
    endpoint._tool_registry = make_tool_registry_mock()
    endpoint._http_client = MagicMock()
    endpoint._initialized = True

    request = ChatRequest(message="Hello", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.session_id == "test-1"
    assert response.phase == ConversationPhase.GREETING


@pytest.mark.asyncio
async def test_process_message_search_shops() -> None:
    endpoint = ChatEndpoint()
    endpoint._session_store = make_session_store_mock()
    endpoint._tool_registry = make_tool_registry_mock()
    endpoint._http_client = MagicMock()
    endpoint._initialized = True

    # Mock the searchShops tool
    mock_tool = AsyncMock()
    mock_tool.name = "searchShops"
    mock_tool.execute = AsyncMock(return_value=SearchShopsResponse(
        success=True,
        data=[],
        message="Success",
    ))
    with patch.object(endpoint._tool_registry, "get", return_value=mock_tool):
        request = ChatRequest(message="I want to find a shop", session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        assert (
            "shops" in response.message.lower()
            or "found" in response.message.lower()
            or "search" in response.message.lower()
        )




@pytest.mark.asyncio
async def test_parse_intent_reset() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("reset", state) == "reset"
    assert endpoint._parse_intent("start over", state) == "reset"


@pytest.mark.asyncio
async def test_parse_intent_unknown() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("xyz random text", state) == "unknown"


@pytest.mark.asyncio
async def test_parse_intent_search_shops_in_greeting() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("show me shops", state) == "search_shops"
    assert endpoint._parse_intent("branch locations", state) == "search_shops"


@pytest.mark.asyncio
async def test_parse_intent_search_courses() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("what courses do you have", state) == "search_courses"
    assert endpoint._parse_intent("show me massage services", state) == "search_courses"


@pytest.mark.asyncio
async def test_parse_intent_faq_search() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("help me", state) == "faq_search"
    assert endpoint._parse_intent("I have a question", state) == "faq_search"
    assert endpoint._parse_intent("faq", state) == "faq_search"


@pytest.mark.asyncio
async def test_parse_intent_lookup_booking() -> None:
    endpoint = ChatEndpoint()
    state = ConversationState()
    assert endpoint._parse_intent("I want to check my booking", state) == "lookup_booking"
    assert endpoint._parse_intent("lookup my booking", state) == "lookup_booking"


def test_create_app() -> None:
    app = create_app()
    assert app.title == "Chatbot Service"
    assert app.version == "1.0.0"


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_reset_intent() -> None:
    endpoint = ChatEndpoint()
    endpoint._session_store = make_session_store_mock()
    endpoint._tool_registry = make_tool_registry_mock()
    endpoint._http_client = MagicMock()
    endpoint._initialized = True

    request = ChatRequest(message="reset", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "reset" in response.message.lower()


@pytest.mark.asyncio
async def test_unknown_intent_returns_help() -> None:
    endpoint = ChatEndpoint()
    endpoint._session_store = make_session_store_mock()
    endpoint._tool_registry = make_tool_registry_mock()
    endpoint._http_client = MagicMock()
    endpoint._initialized = True

    request = ChatRequest(message="asdf qwerty gibberish", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is False
    assert "search" in response.message.lower()


@pytest.mark.asyncio
async def test_initialize_and_close() -> None:
    endpoint = ChatEndpoint()
    # Patch the gateway components
    with patch("chatbot.app.chat_endpoint.create_client") as mock_create:
        with patch("chatbot.app.chat_endpoint.RedisSessionStore") as mock_store_class:
            with patch("chatbot.app.chat_endpoint.PgVectorStore") as mock_pg_store:
                mock_client = AsyncMock()
                mock_client.close = AsyncMock()
                mock_create.return_value = mock_client

                mock_store_instance = MagicMock()
                mock_store_instance.close = AsyncMock()
                mock_store_class.return_value = mock_store_instance

                mock_pg_store.return_value = MagicMock()

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
