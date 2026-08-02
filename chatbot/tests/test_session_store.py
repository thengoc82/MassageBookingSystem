"""Tests for session — Redis session storage"""
from unittest.mock import AsyncMock, patch

import pytest
from chatbot.app.config import Settings
from chatbot.session.store import RedisSessionStore, SessionData
from chatbot.conversation.state import ConversationState
from pydantic import ValidationError


@pytest.fixture
def store() -> RedisSessionStore:
    settings = Settings(redis_url="redis://localhost:6379/0", session_expiration_seconds=60)
    return RedisSessionStore(settings)


def test_session_data_defaults() -> None:
    session = SessionData(session_id="test-1")
    assert session.session_id == "test-1"
    assert session.user_id is None
    assert session.conversation_state == ConversationState()
    assert session.created_at > 0


def test_session_data_validation() -> None:
    with pytest.raises(ValidationError):
        SessionData()  # missing session_id


@pytest.mark.asyncio
async def test_create_session(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    with patch.object(store, "_get_redis", return_value=mock_redis):
        session = await store.create_session("test-1", "user-1")
        assert session.session_id == "test-1"
        assert session.user_id == "user-1"
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_exists(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    session_data = SessionData(session_id="test-1")
    mock_redis.get = AsyncMock(return_value=session_data.model_dump_json())
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.get_session("test-1")
        assert result is not None
        assert result.session_id == "test-1"


@pytest.mark.asyncio
async def test_get_session_not_exists(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.get_session("nonexistent")
        assert result is None


@pytest.mark.asyncio
async def test_save_session(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    with patch.object(store, "_get_redis", return_value=mock_redis):
        session = SessionData(session_id="test-1")
        await store.save_session(session)
        mock_redis.setex.assert_called_once()
        # Check TTL is set
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 60  # TTL


@pytest.mark.asyncio
async def test_delete_session(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=1)
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.delete_session("test-1")
        assert result is True
        mock_redis.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_session_not_exists(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock(return_value=0)
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.delete_session("nonexistent")
        assert result is False


@pytest.mark.asyncio
async def test_update_context(store: RedisSessionStore) -> None:
    session_data = SessionData(session_id="test-1")
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=session_data.model_dump_json())
    mock_redis.setex = AsyncMock()
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.update_context("test-1", {"shop_id": "123"})
        assert result is not None
        assert result.conversation_state.booking_context.shop_id == "123"


@pytest.mark.asyncio
async def test_update_context_session_not_exists(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.update_context("nonexistent", {"key": "value"})
        assert result is None


@pytest.mark.asyncio
async def test_update_conversation_state(store: RedisSessionStore) -> None:
    session_data = SessionData(session_id="test-1")
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=session_data.model_dump_json())
    mock_redis.setex = AsyncMock()
    with patch.object(store, "_get_redis", return_value=mock_redis):
        result = await store.update_conversation_state("test-1", {"phase": "greeting"})
        assert result is not None
        assert result.conversation_state.phase == "greeting"


@pytest.mark.asyncio
async def test_close(store: RedisSessionStore) -> None:
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    store._redis = mock_redis
    await store.close()
    assert store._redis is None
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_close_when_none(store: RedisSessionStore) -> None:
    store._redis = None
    await store.close()
    assert store._redis is None


def test_session_key_format(store: RedisSessionStore) -> None:
    key = store._session_key("abc-123")
    assert key == "chatbot:session:abc-123"


@pytest.mark.asyncio
async def test_async_context_manager() -> None:
    settings = Settings(redis_url="redis://test:6379/0")
    async with RedisSessionStore(settings) as store:
        assert store is not None
    assert store._redis is None
