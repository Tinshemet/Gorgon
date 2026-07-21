"""chat_client/session.py — persist the chat session id across runs."""

import os

_SESSION_FILE = os.path.expanduser("~/.qemu_vms/.chat_session_id")


def load_session_id() -> str:
    """Return the persisted chat session id, or "" if none is saved."""
    try:
        return open(_SESSION_FILE).read().strip()
    except FileNotFoundError:
        return ""


def save_session_id(sid: str) -> None:
    """Persist the chat session id to the local session file."""
    os.makedirs(os.path.dirname(_SESSION_FILE), exist_ok=True)
    with open(_SESSION_FILE, "w") as f:
        f.write(sid)
