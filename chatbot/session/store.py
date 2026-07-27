import logging
import time

import redis.asyncio as redis
from pydantic import BaseModel, Field

from chatbot.app.config import Settings

logger = logging.getLogger(__name__)


class SessionData(BaseModel):
    """Session data model."""
    session_id: str
    user_id: str | None = None
    conversation_state: dict = Field(default_factory=dict)
    conversation_history: list[list[str]] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class RedisSessionStore:
    """Redis-backed session storage."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def __aenter__(self) -> "RedisSessionStore":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _session_key(self, session_id: str) -> str:
        return f"chatbot:session:{session_id}"

    async def create_session(self, session_id: str, user_id: str | None = None) -> SessionData:
        """Create a new session."""
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=time.time(),
            updated_at=time.time(),
        )
        await self.save_session(session)
        return session

    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session by ID."""
        redis_client = await self._get_redis()
        key = self._session_key(session_id)
        data = await redis_client.get(key)
        if data is None:
            return None
        return SessionData.model_validate_json(data)

    async def save_session(self, session: SessionData) -> None:
        """Save session to Redis."""
        session.updated_at = time.time()
        redis_client = await self._get_redis()
        key = self._session_key(session.session_id)
        ttl = self._settings.session_expiration_seconds
        await redis_client.setex(key, ttl, session.model_dump_json())

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        redis_client = await self._get_redis()
        key = self._session_key(session_id)
        result = await redis_client.delete(key)
        return result > 0

    async def update_context(self, session_id: str, context: dict) -> SessionData | None:
        """Update session context."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        session.context.update(context)
        await self.save_session(session)
        return session

    async def update_conversation_state(
        self, session_id: str, state: dict
    ) -> SessionData | None:
        """Update conversation state."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        session.conversation_state.update(state)
        await self.save_session(session)
        return session
