import asyncio

import pytest
from chatbot.observability.tracing import (
    generate_trace_id,
    get_trace_id,
    set_trace_id,
)


def test_get_and_set_trace_id() -> None:
    set_trace_id("")  # Reset before test
    assert get_trace_id() == ""
    tid = generate_trace_id()
    set_trace_id(tid)
    assert get_trace_id() == tid
    set_trace_id("")  # Clean up after test


@pytest.mark.asyncio
async def test_trace_id_is_task_local() -> None:
    set_trace_id("main")  # Reset before test

    async def task_a() -> None:
        set_trace_id("a")
        await asyncio.sleep(0.01)
        assert get_trace_id() == "a"

    async def task_b() -> None:
        set_trace_id("b")
        await asyncio.sleep(0.01)
        assert get_trace_id() == "b"

    await asyncio.gather(task_a(), task_b())
    assert get_trace_id() == "main"
    set_trace_id("")  # Clean up after test
