import logging
import sys
from typing import Any

import pythonjsonlogger.jsonlogger

from chatbot.observability.tracing import get_trace_id


class TraceFilter(logging.Filter):
    """Injects the current trace_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure JSON structured logging for the chatbot service."""
    root_logger = logging.getLogger("chatbot")
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    formatter = pythonjsonlogger.jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s"
    )
    handler.setFormatter(formatter)

    handler.addFilter(TraceFilter())
    root_logger.addHandler(handler)

    root_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a structured logger bound to the chatbot namespace."""
    return logging.getLogger(f"chatbot.{name}")


def log_structured(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Emit a structured log record with arbitrary fields."""
    logger.log(level, event, extra=fields)
