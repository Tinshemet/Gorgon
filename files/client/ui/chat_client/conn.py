"""
chat_client/conn.py — connection constants + auth handles for the chat TUI.

Connection settings come from the shared loader (client/config, env overrides
applied). The chat client prefers this box's logged-in operator session over the
static API_TOKEN (see _EFFECTIVE_TOKEN) — /chat requires a session once an
operator account exists, so the static token alone would get every message
rejected even for a legitimately logged-in operator.
"""

from client import config as _cfg

try:
    from orchestrator.auth import store as _auth_store, sessions as _auth_sessions
except ImportError:
    _auth_store    = None
    _auth_sessions = None

SERVER_URL = _cfg.SERVER
_TOKEN     = _cfg.TOKEN
_TIMEOUT   = _cfg.TIMEOUT
_CA_CERT   = _cfg.CA_CERT
_VERIFY    = _cfg.VERIFY

_SESSION_TOKEN   = _auth_sessions.read_current_session() if _auth_sessions else None
_EFFECTIVE_TOKEN = _SESSION_TOKEN or _TOKEN
_HEADERS         = {"Authorization": f"Bearer {_EFFECTIVE_TOKEN}"} if _EFFECTIVE_TOKEN else {}
