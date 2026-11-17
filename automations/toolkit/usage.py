"""Usage: count the tokens one run uses.

Each run gets its own count. A webhook can handle several requests at once, so
one shared number would mix their counts.
"""
from contextvars import ContextVar

_count: ContextVar[list[int] | None] = ContextVar("tokens", default=None)


def start() -> None:
    """Start a new count for the run in progress."""
    _count.set([0])


def add(tokens: int) -> None:
    count = _count.get()
    if count is None:  # a call outside a run, such as tools/triage.py
        start()
        count = _count.get()
    assert count is not None
    count[0] += tokens


def tokens() -> int:
    """Tokens used so far in this run."""
    count = _count.get()
    return count[0] if count else 0
