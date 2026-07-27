import pytest
from chatbot.observability.metrics import MetricsCollector


def test_incr_counter() -> None:
    m = MetricsCollector()
    m.incr("foo")
    m.incr("foo", amount=2)
    assert m._counters["foo"] == 3


def test_observe_latency() -> None:
    m = MetricsCollector()
    m.observe("lat", 0.1)
    m.observe("lat", 0.2)
    assert m._latency_sums["lat"] == pytest.approx(0.3)
    assert m._latency_counts["lat"] == 2


def test_render_snapshot() -> None:
    m = MetricsCollector()
    m.incr("a", k="v")
    snap = m.render()
    assert "a{k=v}" in snap["counters"]


def test_labels_are_sorted_in_key() -> None:
    m = MetricsCollector()
    m.incr("m", b="2", a="1")
    snap = m.render()
    assert "m{a=1,b=2}" in snap["counters"]
