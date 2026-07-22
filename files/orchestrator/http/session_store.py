"""
orchestrator/http/session_store.py — the in-memory chat session store.

Session state is kept here as the single source of truth so both the /chat route
(api_server) and the chat turn handler (chat_endpoint) mutate the same dict without
importing each other (which would be circular). Each session:
    {"messages": [...], "pending_tool": {"tool_name": str, "args": dict} | None,
     "critical_step2": bool, "last_active": float}
"""
import time
from typing import Any, Dict

from .context import MAX_SESSIONS, SESSION_TTL_SECONDS

SESSIONS: Dict[str, Dict[str, Any]] = {}


def evict_expired() -> None:
    """Remove sessions that have been inactive longer than SESSION_TTL_SECONDS."""
    cutoff = time.time() - SESSION_TTL_SECONDS
    # Sessions without last_active are treated as live (float('inf') > cutoff always).
    expired = [sid for sid, s in list(SESSIONS.items())
               if s.get("last_active", float("inf")) < cutoff]
    for sid in expired:
        SESSIONS.pop(sid, None)


def get_session(sid: str) -> Dict[str, Any]:
    """Return (and touch) the session for *sid*, creating it with eviction if missing."""
    if sid not in SESSIONS:
        evict_expired()
        if len(SESSIONS) >= MAX_SESSIONS:
            # Drop the oldest session to stay under the cap.
            oldest = min(SESSIONS, key=lambda k: SESSIONS[k].get("last_active", 0))
            SESSIONS.pop(oldest, None)
        SESSIONS[sid] = {"messages": [], "pending_tool": None,
                         "critical_step2": False, "last_active": time.time()}
    SESSIONS[sid]["last_active"] = time.time()
    return SESSIONS[sid]
