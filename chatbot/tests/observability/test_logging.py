import io
import json
import logging

from chatbot.observability.logging import configure_logging, log_structured
from chatbot.observability.tracing import set_trace_id


def test_configure_logging_emits_json() -> None:
    # Use a real logger configured by the function
    configure_logging("DEBUG")
    logger = logging.getLogger("chatbot.test_json")

    # Capture output
    buf = io.StringIO()
    # Find the handler and redirect its stream
    for handler in logging.getLogger("chatbot").handlers:
        if isinstance(handler, logging.StreamHandler):
            original_stream = handler.stream
            handler.stream = buf
            break
    else:
        raise RuntimeError("Could not find StreamHandler to patch")

    set_trace_id("trace-xyz")
    log_structured(logger, logging.INFO, "hello world", foo="bar")

    # Restore stream
    handler.stream = original_stream

    # Assert on captured output
    record = json.loads(buf.getvalue().strip())
    assert record["message"] == "hello world"
    assert record["foo"] == "bar"
    assert record["trace_id"] == "trace-xyz"


def test_configure_logging_runs_without_error() -> None:
    configure_logging("DEBUG")
