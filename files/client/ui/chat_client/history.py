"""chat_client/history.py — the scrollback buffer (thread-safe append)."""

import textwrap

from client.ui.chat_client import state
from client.ui.chat_client.colors import cp as _cp, C_DIM


def add(text: str, attr: int = 0, wrap: int = 0) -> None:
    """Append a line to the scrollback buffer (thread-safe), optionally wrapping."""
    with state.lock:
        if wrap:
            for line in textwrap.wrap(text, wrap) or [""]:
                state.history.append((attr, line))
        else:
            state.history.append((attr, text))


def add_sep() -> None:
    """Append a dim horizontal separator to the scrollback."""
    add("  " + "─" * 62, _cp(C_DIM))
