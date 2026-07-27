import time
from dataclasses import dataclass


class RateLimitExceeded(Exception):
    """Raised when a request exceeds the configured rate limit."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"Rate limit exceeded; retry in {retry_after:.2f}s")
        self.retry_after = retry_after


@dataclass
class RateLimitConfig:
    """Configuration for the token bucket rate limiter."""

    capacity: int = 10  # max tokens
    refill_rate: float = 10.0 / 60.0  # tokens per second (10 per minute default)


class TokenBucketRateLimiter:
    """Token bucket rate limiter, session-keyed.

    Lazy import of redis so tests do not need a running Redis. When a redis
    client is supplied, state lives in Redis (using INCR + EXPIRE pattern via a
    Lua script). Without redis, an in-memory dict is used.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        redis_client: object | None = None,
    ) -> None:
        self._config = config or RateLimitConfig()
        self._redis = redis_client
        # In-memory buckets: {key: (tokens, last_refill_ts)}
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = False  # single-process guard; tests run sequentially

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def check(self, session_id: str, user_id: str | None = None) -> None:
        """Check (and consume) a token for the given identity.

        Raises RateLimitExceeded when the bucket is empty.
        """
        key = self._key(session_id, user_id)
        if self._redis is not None:
            self._check_redis(key)
            return
        self._check_memory(key)

    def _key(self, session_id: str, user_id: str | None) -> str:
        if user_id:
            return f"user:{user_id}"
        return f"session:{session_id}"

    def _check_memory(self, key: str) -> None:
        capacity = self._config.capacity
        refill = self._config.refill_rate
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(capacity), now))
        delta = now - last
        tokens = min(float(capacity), tokens + delta * refill)
        if tokens < 1.0:
            retry_after = (1.0 - tokens) / refill if refill > 0 else 60.0
            self._buckets[key] = (tokens, now)
            raise RateLimitExceeded(retry_after)
        tokens -= 1.0
        self._buckets[key] = (tokens, now)

    def _check_redis(self, key: str) -> None:
        assert self._redis is not None
        # Atomic implementation using a Lua script.
        script = """
        local capacity = tonumber(ARGV[1])
        local refill = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local data = redis.call('HMGET', KEYS[1], 'tokens', 'last')
        local tokens = tonumber(data[1])
        local last = tonumber(data[2])
        if tokens == nil then
            tokens = capacity
            last = now
        end
        local delta = now - last
        tokens = math.min(capacity, tokens + delta * refill)
        if tokens < 1 then
            local retry = (1 - tokens) / refill
            redis.call('HMSET', KEYS[1], 'tokens', tokens, 'last', now)
            redis.call('EXPIRE', KEYS[1], 600)
            return {0, retry}
        end
        tokens = tokens - 1
        redis.call('HMSET', KEYS[1], 'tokens', tokens, 'last', now)
        redis.call('EXPIRE', KEYS[1], 600)
        return {1, 0}
        """
        now = time.time()
        result = self._redis.eval(  # type: ignore[attr-defined]
            script,
            1,
            key,
            self._config.capacity,
            self._config.refill_rate,
            now,
        )
        allowed = bool(result[0])
        if not allowed:
            retry_after = float(result[1])
            raise RateLimitExceeded(retry_after)
