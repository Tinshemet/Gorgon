"""agent_select.py — the persisted active-agent selection.

A tiny file (``~/.gorgon.agent``) holding the basename (or absolute path) of the
.grgn the runtime should load. ``contract.py`` reads it as a fallback beneath the
GORGON_AGENT env var; the ``gorgon agent`` CLI writes it. Kept as one module so
the client (writer) and orchestrator (reader) agree on path + format.

Resolution order the runtime honors:
    GORGON_AGENT env var  >  ~/.gorgon.agent  >  doorman.grgn
"""
import os
from typing import Optional

from shared.config import AGENT_SELECTION_FILE, DEFAULT_AGENT, AGENT_ENV_VAR

_SELECTION_FILE = AGENT_SELECTION_FILE


def selection_path() -> str:
    """Absolute path of the persisted-selection file."""
    return _SELECTION_FILE


def resolve() -> str:
    """The agent file the runtime should load, honoring the full resolution order:
    ``GORGON_AGENT`` env var  >  the persisted selection  >  the doorman default.
    This is the single authority for that order (contract.py defers to it)."""
    return os.environ.get(AGENT_ENV_VAR) or get_selection() or DEFAULT_AGENT


def get_selection() -> Optional[str]:
    """The persisted agent basename/path, or None if none is set."""
    try:
        with open(_SELECTION_FILE) as f:
            value = f.read().strip()
        return value or None
    except (FileNotFoundError, OSError):
        return None


def set_selection(name: str) -> None:
    """Persist *name* as the active agent for the next runtime boot."""
    with open(_SELECTION_FILE, "w") as f:
        f.write((name or "").strip())


def clear_selection() -> None:
    """Remove the persisted selection (revert to the doorman default)."""
    try:
        os.remove(_SELECTION_FILE)
    except FileNotFoundError:
        pass
