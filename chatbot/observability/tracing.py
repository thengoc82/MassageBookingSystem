from contextvars import ContextVar
from uuid import uuid4

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """Return the current trace_id."""
    return trace_id_var.get()


def set_trace_id(value: str) -> None:
    """Set the current trace_id."""
    trace_id_var.set(value)


def generate_trace_id() -> str:
    """Generate a new trace_id."""
    return str(uuid4())
