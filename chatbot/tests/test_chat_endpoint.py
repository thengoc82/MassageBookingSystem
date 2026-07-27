"""Tests for chat endpoint — web chat with deterministic flow"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from chatbot.app.chat_endpoint import ChatEndpoint, ChatRequest, create_app
from chatbot.conversation.state import ConversationPhase
from chatbot.models import SearchShopsResponse
from chatbot.session.store import RedisSessionStore, SessionData
from chatbot.tools.registry import ToolRegistry


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


def make_endpoint() -> ChatEndpoint:
    endpoint = ChatEndpoint()
    endpoint._session_store = make_session_store_mock()
    endpoint._tool_registry = make_tool_registry_mock()
    endpoint._http_client = MagicMock()
    endpoint._initialized = True
    return endpoint


# --- Basic process_message flow ---


@pytest.mark.asyncio
async def test_process_message_creates_new_session() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="Hello", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.session_id == "test-1"
    assert response.phase == ConversationPhase.GREETING
    assert "welcome" in response.message.lower()


@pytest.mark.asyncio
async def test_process_message_search_shops() -> None:
    endpoint = make_endpoint()
    mock_tool = AsyncMock()
    mock_tool.name = "searchShops"
    mock_tool.execute = AsyncMock(
        return_value=SearchShopsResponse(success=True, data=[], message="Success")
    )
    with patch.object(endpoint._tool_registry, "get", return_value=mock_tool):
        request = ChatRequest(message="show me shops", session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        assert "couldn't find any shops" in response.message.lower()


# --- Reset / start over / go back ---


@pytest.mark.asyncio
async def test_reset_intent() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="reset", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "start over" in response.message.lower()


# --- Intent classifier tests ---


@pytest.mark.asyncio
async def test_parse_intent_reset() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._is_start_over("reset")
    assert endpoint._is_start_over("start over")


@pytest.mark.asyncio
async def test_parse_intent_unknown() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._classify_intent("xyz random text").intent.value == "unknown"


@pytest.mark.asyncio
async def test_parse_intent_search_shops_in_greeting() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._classify_intent("show me shops").intent.value == "search_shops"
    assert endpoint._classify_intent("branch locations").intent.value == "search_shops"


@pytest.mark.asyncio
async def test_parse_intent_search_courses() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._classify_intent("what courses do you have").intent.value == "search_courses"
    assert endpoint._classify_intent("show me massage services").intent.value == "search_courses"


@pytest.mark.asyncio
async def test_parse_intent_faq_search() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._classify_intent("I have a question").intent.value == "faq"
    assert endpoint._classify_intent("faq").intent.value == "faq"


@pytest.mark.asyncio
async def test_parse_intent_lookup_booking() -> None:
    endpoint = ChatEndpoint()
    assert endpoint._classify_intent("I want to check my booking").intent.value == "lookup_booking"
    assert endpoint._classify_intent("lookup my booking").intent.value == "lookup_booking"


# --- FastAPI app & health ---


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


# --- Conversational intents (greeting, goodbye, help) ---


@pytest.mark.asyncio
async def test_greeting_intent() -> None:
    endpoint = make_endpoint()
    for msg in ["hello", "hi", "good morning"]:
        request = ChatRequest(message=msg, session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        assert "welcome" in response.message.lower()


@pytest.mark.asyncio
async def test_goodbye_intent() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="goodbye", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "goodbye" in response.message.lower()


@pytest.mark.asyncio
async def test_help_intent() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="help", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "what i can do" in response.message.lower()


# --- Unknown intent with helpful suggestions ---


@pytest.mark.asyncio
async def test_unknown_intent_returns_help() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="asdf qwerty gibberish", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "i'm not sure i understand" in response.message.lower()


@pytest.mark.asyncio
async def test_unknown_intent_provides_helpful_suggestions() -> None:
    endpoint = make_endpoint()
    request = ChatRequest(message="gibberish xyz", session_id="test-1")
    response = await endpoint.process_message(request)
    assert response.success is True
    assert "book a massage" in response.message.lower()


# --- Slot-filling booking flow ---


@pytest.mark.asyncio
async def test_book_massage_with_slot_filling() -> None:
    endpoint = make_endpoint()
    mock_tool = AsyncMock()
    mock_tool.name = "searchShops"
    mock_tool.execute = AsyncMock(
        return_value=SearchShopsResponse(success=True, data=[], message="Success")
    )
    with patch.object(endpoint._tool_registry, "get", return_value=mock_tool):
        request = ChatRequest(message="I want a massage tomorrow", session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        assert "shops" in response.message.lower()
        assert response.phase == ConversationPhase.SEARCHING_SHOPS


@pytest.mark.asyncio
async def test_book_me_a_massage_slot_filling() -> None:
    endpoint = make_endpoint()
    mock_tool = AsyncMock()
    mock_tool.name = "searchShops"
    mock_tool.execute = AsyncMock(
        return_value=SearchShopsResponse(success=True, data=[], message="Success")
    )
    with patch.object(endpoint._tool_registry, "get", return_value=mock_tool):
        request = ChatRequest(message="Book me a massage", session_id="test-1")
        response = await endpoint.process_message(request)
        assert response.success is True
        assert response.phase == ConversationPhase.SEARCHING_SHOPS


# --- Initialize / close / idempotent ---


@pytest.mark.asyncio
async def test_initialize_and_close() -> None:
    with patch("chatbot.app.chat_endpoint.create_client", new_callable=AsyncMock), \
         patch("chatbot.app.chat_endpoint.RedisSessionStore"), \
         patch("chatbot.app.chat_endpoint.OpenAILLMService") as mock_llm, \
         patch("chatbot.app.chat_endpoint.PgVectorStore"):
        mock_llm_instance = MagicMock()
        mock_llm.return_value = mock_llm_instance
        endpoint = ChatEndpoint(llm_service=mock_llm_instance)
        await endpoint.initialize()
        assert endpoint._initialized
        await endpoint.close()
        assert not endpoint._initialized


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
