import threading
from collections import defaultdict
from time import perf_counter
from typing import Any

from fastapi import Request

from chatbot.observability.tracing import generate_trace_id, get_trace_id, set_trace_id


class MetricsCollector:
    """In-memory metrics collector that mirrors a Prometheus style exposition.

    All counters are monotonically increasing. Latency observations are kept as
    running sums and counts so a downstream exporter can compute averages.
    Swap-out friendly: tests only depend on the public API surface.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._latency_sums: dict[str, float] = defaultdict(float)
        self._latency_counts: dict[str, int] = defaultdict(int)
        self._latencies: dict[str, list[float]] = defaultdict(list)

    def incr(
        self,
        metric: str,
        amount: float = 1.0,
        labels: dict[str, str] | None = None,
        **label_kwargs: str,
    ) -> None:
        merged = dict(labels or {})
        merged.update(label_kwargs)
        with self._lock:
            key = self._key(metric, merged)
            self._counters[key] += amount

    def observe(
        self,
        metric: str,
        value: float,
        labels: dict[str, str] | None = None,
        **label_kwargs: str,
    ) -> None:
        merged = dict(labels or {})
        merged.update(label_kwargs)
        with self._lock:
            key = self._key(metric, merged)
            self._latency_sums[key] += value
            self._latency_counts[key] += 1
            self._latencies[key].append(value)

    def render(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "latency_sums": dict(self._latency_sums),
                "latency_counts": dict(self._latency_counts),
                "latencies": {k: list(v) for k, v in self._latencies.items()},
            }

    @staticmethod
    def _key(metric: str, labels: dict[str, str]) -> str:
        if not labels:
            return metric
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{metric}{{{label_str}}}"


_default = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _default


async def tracing_middleware(request: Request, call_next: Any) -> Any:
    incoming = request.headers.get("X-Request-ID")
    trace_id = incoming or generate_trace_id()
    set_trace_id(trace_id)
    start = perf_counter()
    try:
        response = await call_next(request)
    finally:
        duration = perf_counter() - start
        get_metrics().incr("http_requests_total", labels={"path": request.url.path})
        get_metrics().observe(
            "http_request_duration_seconds", duration, labels={"path": request.url.path}
        )
        # contextvar reset is handled by context propagation; explicit clear
        # to avoid leaking between requests when running in the same task
        set_trace_id("")
    response.headers["X-Request-ID"] = trace_id
    return response


def current_trace_id() -> str:
    return get_trace_id()
