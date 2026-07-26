"""
orchestrator/config — Configuration for the orchestrator role (loader + data).

These are the settings the orchestrator needs to reach the EXECUTOR and to run its
own client-facing HTTP surface: the executor URL and token, TLS verification, request
timeouts, the remote-mode allowlists, and the operator/chat session limits.

  connection_config.defaults.json  — the single manifest of every setting + default
  connection_config.json           — this deployment's overrides (win on merge)

Like the admin/client/shared loaders, this file holds no literal setting values of its
own: it merges the two JSON files and exposes each as a named constant, so code says
`config.SYNC_TIMEOUT_S` instead of repeating `_CFG.get("sync_timeout_s", 10)` at each
call site — which is what it used to do, in two modules, with the fallback literal
written out twice.

WHY THE SPLIT MATTERS HERE. The overrides file carries the executor token, so it is
gitignored — and it used to be the ONLY copy. A clean checkout therefore had no
connection_config.json at all and `import orchestrator.executor_client` raised
FileNotFoundError before it could do anything. The committed defaults manifest fixes
that: a fresh clone imports and runs against local mode, and the gitignored overrides
supply the secret when a deployment has one.

The long-standing environment overrides (`API_URL`, `EXECUTOR_TOKEN`, `API_TIMEOUT`)
still win over both files, so existing deployments do not change behaviour.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))            # …/files/orchestrator/config


def load_json(path: str) -> dict:
    """Load a JSON file, returning an empty dict on any error."""
    try:
        return json.load(open(path))
    except Exception:
        return {}


_DEFAULTS  = load_json(os.path.join(_HERE, "connection_config.defaults.json"))
_OVERRIDES = load_json(os.path.join(_HERE, "connection_config.json"))
_CFG       = {**_DEFAULTS, **_OVERRIDES}   # deployment overrides win


def _c(key: str):
    """Fetch a merged setting; KeyError if the defaults manifest is missing it."""
    return _CFG[key]


# ── reaching the executor ───────────────────────────────────────────────────────
API_URL          = _c("url")
TOKEN            = _c("token")
TIMEOUT          = _c("timeout")
SYNC_TIMEOUT_S   = _c("sync_timeout_s")     # shorter, for the startup /profiles+/capabilities probe
VERIFY_SSL       = _c("verify_ssl")
CA_CERT          = _c("ca_cert")
MIN_TOKEN_LENGTH = _c("min_token_length")

# ── remote-mode restriction (blacklist > whitelist naming: these are ALLOW lists
#    only because they gate a remote client, not the operator) ────────────────────
CLIENT_ALLOWED_VMS      = _c("client_allowed_vms")
CLIENT_ALLOWED_PROFILES = _c("client_allowed_profiles")
ALLOWED_REMOTE_TOOLS    = _c("allowed_remote_tools")
LOCAL_ONLY_DISPLAYS     = _c("local_only_displays")

# ── sessions + payload limits ───────────────────────────────────────────────────
SESSION_TTL_SECONDS        = _c("session_ttl_seconds")
MAX_SESSIONS               = _c("max_sessions")
MAX_MESSAGE_LENGTH         = _c("max_message_length")
OPERATOR_SESSION_TTL_HOURS = _c("operator_session_ttl_hours")

# ── streaming / proxy chunking ──────────────────────────────────────────────────
IO_CHUNK_BYTES        = _c("io_chunk_bytes")
BUNDLE_CHUNK_BYTES    = _c("bundle_chunk_bytes")
PROXY_SHA256_TIMEOUT_S = _c("proxy_sha256_timeout_s")
PROXY_STREAM_TIMEOUT_S = _c("proxy_stream_timeout_s")


# The raw merged mapping, for the few callers that legitimately want the whole dict
# (the /info surface reports the effective config).
def as_dict() -> dict:
    """The merged config, defaults ∪ overrides."""
    return dict(_CFG)
