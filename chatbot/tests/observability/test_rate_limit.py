import time

import pytest
from chatbot.observability.rate_limit import (
    RateLimitConfig,
    RateLimitExceeded,
    TokenBucketRateLimiter,
)


def test_check_passes_within_capacity() -> None:
    limiter = TokenBucketRateLimiter(RateLimitConfig(capacity=3, refill_rate=1.0))
    for _ in range(3):
        limiter.check("s1")


def test_check_raises_when_exhausted() -> None:
    limiter = TokenBucketRateLimiter(RateLimitConfig(capacity=2, refill_rate=0.0001))
    limiter.check("s1")
    limiter.check("s1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("s1")


def test_refill_over_time() -> None:
    limiter = TokenBucketRateLimiter(RateLimitConfig(capacity=1, refill_rate=10.0))
    limiter.check("s1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("s1")
    time.sleep(0.2)
    limiter.check("s1")  # should pass after refill


def test_separate_keys_have_separate_buckets() -> None:
    limiter = TokenBucketRateLimiter(RateLimitConfig(capacity=1, refill_rate=0.0001))
    limiter.check("s1")
    limiter.check("s2")  # different key, fresh bucket


def test_user_id_overrides_session() -> None:
    limiter = TokenBucketRateLimiter(RateLimitConfig(capacity=1, refill_rate=0.0001))
    limiter.check("s1", user_id="u1")
    with pytest.raises(RateLimitExceeded):
        limiter.check("s2", user_id="u1")  # same user, different session
