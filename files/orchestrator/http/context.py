"""
orchestrator/http/context.py — shared configuration for the HTTP layer.

The allowlists/limits derived from the orchestrator config live here as the single
source of truth, so api_server.py (routing + auth) and the endpoint-body modules
(chat_endpoint, execute_endpoint, image_delivery) all read the same values without
importing each other — which would be circular.

The VALUES come from orchestrator/config (defaults ∪ overrides). This module used to
load the JSON itself and repeat every fallback literal, which made three copies of
each default across executor_client, auth/sessions and here.
"""
from orchestrator import config as _cfg

ALLOWED_TOOLS:       set  = set(_cfg.ALLOWED_REMOTE_TOOLS)
LOCAL_ONLY_DISPLAYS: set  = set(_cfg.LOCAL_ONLY_DISPLAYS)
MIN_TOKEN_LEN:       int  = _cfg.MIN_TOKEN_LENGTH
# Empty list = all allowed; non-empty = allowlist
ALLOWED_VMS:         list = _cfg.CLIENT_ALLOWED_VMS
ALLOWED_PROFILES:    list = _cfg.CLIENT_ALLOWED_PROFILES
MAX_MESSAGE_LEN:     int  = _cfg.MAX_MESSAGE_LENGTH
MAX_SESSIONS:        int  = _cfg.MAX_SESSIONS
SESSION_TTL_SECONDS: int  = _cfg.SESSION_TTL_SECONDS

# ── image/bundle delivery (proxy to the executor) ──────────────────────────────
IO_CHUNK_BYTES:         int = _cfg.IO_CHUNK_BYTES            # disk stream chunk
BUNDLE_CHUNK_BYTES:     int = _cfg.BUNDLE_CHUNK_BYTES        # tar.gz proxy chunk
PROXY_SHA256_TIMEOUT_S: int = _cfg.PROXY_SHA256_TIMEOUT_S    # sha256 proxy request
PROXY_STREAM_TIMEOUT_S: int = _cfg.PROXY_STREAM_TIMEOUT_S    # disk/bundle stream proxy

LOCALHOST           = {"127.0.0.1", "::1", "localhost"}
SESSION_COOKIE_NAME = "gorgon_session"


def filter_allowed(names: list, allowlist: list) -> list:
    """Return names visible to clients. Empty allowlist means all are visible."""
    if not allowlist:
        return names
    return [n for n in names if n in allowlist]
