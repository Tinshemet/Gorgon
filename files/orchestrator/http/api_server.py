"""
api_server.py — gorgon Server HTTP Service

Runs on the server machine alongside Ollama and the QEMU engine.
Exposes /chat (AI loop), /execute (direct tool call), /health, /images,
and /rotate-token. Every request except /health requires a Bearer token.

Start with:
    uvicorn orchestrator.http.api_server:app --host 0.0.0.0 --port 8080

Environment variables:
    API_TOKEN   shared secret — server refuses to start if not set
                alternatively write the token to ~/.gorgon.token

This module is the routing + auth surface. The heavier per-route logic lives in
sibling modules so this one stays readable:
    context.py         connection_config.json load + allowlists/limits (shared)
    session_store.py   the in-memory chat session store (shared with chat_endpoint)
    chat_endpoint.py   the /chat turn handler (AI loop, forge wizard, fast path)
    execute_endpoint.py the /execute tool dispatch + preflight + manager proxy
    image_delivery.py  /images + /vms/{vm}/bundle streaming
"""

import json
import os
import pathlib
import secrets

from fastapi import FastAPI, HTTPException, Depends, Body, Request, Response, Cookie
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from . import chat_endpoint, execute_endpoint, image_delivery, session_store
from .context import (
    ALLOWED_TOOLS      as _ALLOWED_TOOLS,
    ALLOWED_VMS        as _ALLOWED_VMS,
    ALLOWED_PROFILES   as _ALLOWED_PROFILES,
    MAX_MESSAGE_LEN    as _MAX_MESSAGE_LEN,
    MIN_TOKEN_LEN      as _MIN_TOKEN_LEN,
    LOCALHOST          as _LOCALHOST,
    SESSION_COOKIE_NAME as _SESSION_COOKIE_NAME,
    filter_allowed     as _filter_allowed,
)

# ── Token bootstrap ───────────────────────────────────────────────────────────
# Precedence: env var → ~/.gorgon.token file → refuse to start.
_TOKEN_FILE = pathlib.Path.home() / ".gorgon.token"

def _load_token() -> str:
    """Load the API token from the environment variable or the token file."""
    t = os.environ.get("API_TOKEN", "").strip()
    if t:
        return t
    if _TOKEN_FILE.exists():
        t = _TOKEN_FILE.read_text().strip()
        if t:
            return t
    return ""

_TOKEN = _load_token()
if not _TOKEN:
    print(
        "[gorgon] WARNING: No API token configured — remote connections will be refused.\n"
        "  Localhost connections are always allowed without a token.\n"
        "  To enable remote access set API_TOKEN or write to ~/.gorgon.token"
    )

app   = FastAPI(title="gorgon executor", version="1.0")
_auth = HTTPBearer(auto_error=False)


def _active_agent_warnings() -> List[str]:
    """Warnings about the active .grgn: integrity status (tampered/unsigned) plus
    tool-reference drift vs. the executor. Never raises."""
    warnings: List[str] = []
    try:
        from orchestrator.ai.agent import contract as _contract
        status = _contract.agent_signature_status()
        if status == "tampered":
            warnings.append("SECURITY: active agent file failed its integrity check "
                            "(tampered) — running doorman.grgn instead")
        elif status == "expired":
            warnings.append("active agent contract has EXPIRED — running doorman.grgn instead")
        elif status == "voided":
            warnings.append("active agent was VOIDED (its contract is revoked) — running "
                            "doorman.grgn instead; its missions are disabled. Restore with "
                            "`gorgon contract restore <agent>`")
        elif status == "unsigned":
            warnings.append("active agent file was unsigned — signed on this boot "
                            "(trust-on-first-use)")
        warnings += _contract.agent_tool_issues(_ALLOWED_TOOLS)
    except Exception:
        pass
    return warnings


@app.on_event("startup")
async def _startup() -> None:
    """Sync from the executor, TOFU-sign the active agent (so later tampering is
    detectable), then log any integrity/drift warnings — surfaced after a
    `gorgon agent load` restart."""
    from orchestrator.executor_client import sync as _sync
    _sync()
    try:
        import shared.bundle as _bundle
        from orchestrator.ai.agent import AGENT_DIR
        _bundle.migrate(AGENT_DIR)   # legacy → bundles
    except Exception:
        pass
    try:
        from orchestrator.ai.agent import contract as _contract
        from shared.grgn_sign import ensure_integrity
        ensure_integrity(_contract._AGENT_PATH)       # sign plaintext templates (TOFU)
    except Exception:
        pass
    for _msg in _active_agent_warnings():
        print(f"  ⚠ agent: {_msg}")


def _require_auth(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_auth),
    session_cookie: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE_NAME),
) -> None:
    """FastAPI dependency: require a valid API_TOKEN bearer OR a valid operator
    session (bearer token or cookie — one /login response serves both the CLI
    and a future browser client from the same session store).

    Localhost is trusted freely ONLY while no operator account exists yet —
    identical to the old behavior, so nothing breaks until an operator opts
    into the login system via `gorgon login`. The moment one exists, localhost
    is held to the same bar as anyone else — this is what actually closes the
    gap for the CLI's normal (localhost) traffic.
    """
    from orchestrator.auth import sessions as _op_sessions
    from orchestrator.auth import store as _op_store

    bootstrap_open = not _op_store.operators_exist()
    is_localhost   = bool(request.client and request.client.host in _LOCALHOST)
    if bootstrap_open and is_localhost:
        return

    # Operator session — Bearer token or cookie, either way.
    session_token = (creds.credentials if creds else None) or session_cookie
    if session_token and _op_sessions.validate_session(session_token):
        return

    # API_TOKEN bearer — unchanged machine-to-machine / AI-provider path.
    # Re-read fresh so env-var changes (token rotation, test setup) take
    # effect without a server restart.
    token = _load_token() or _TOKEN
    if token and creds is not None and secrets.compare_digest(creds.credentials, token):
        return

    if bootstrap_open and not is_localhost and not token:
        raise HTTPException(status_code=401, detail="No API token configured on server.")
    raise HTTPException(status_code=401, detail="Login required (run `gorgon login`) or provide a valid API token.")


def _require_operator_auth(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_auth),
    session_cookie: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE_NAME),
) -> None:
    """Stricter than _require_auth — applied to /chat and /execute (the primary
    human-interactive surfaces) plus operator/token management (/operators
    create+delete, /rotate-token): high-impact endpoints where the shared token
    must not suffice once an operator exists. In particular, operator deletion
    is gated here because emptying the store would disable auth entirely.

    The plain API_TOKEN is shipped as the same default value
    (connection_config.json's "token") in both the server's and the client's
    config, so any interactive client (e.g. client/ui/chat_client.py) carries
    working "credentials" out of the box regardless of whether anyone has
    ever logged in — making operator login optional in practice, not
    mandatory, for exactly the surfaces this feature was built to gate.

    Once an operator account exists, ONLY a valid operator session (bearer or
    cookie) is accepted here — the shared token no longer suffices. The
    remaining _require_auth-gated endpoints (sync, events, ...) keep accepting
    the plain token unchanged. Pre-bootstrap (no operators yet) behaves
    identically to _require_auth, including the plain-token fallback for
    non-localhost callers — so first-operator creation from localhost still
    works with no credentials.
    """
    from orchestrator.auth import sessions as _op_sessions
    from orchestrator.auth import store as _op_store

    bootstrap_open = not _op_store.operators_exist()
    is_localhost   = bool(request.client and request.client.host in _LOCALHOST)
    if bootstrap_open:
        if is_localhost:
            return
        token = _load_token() or _TOKEN
        if token and creds is not None and secrets.compare_digest(creds.credentials, token):
            return
        raise HTTPException(
            status_code=401,
            detail="No API token configured on server." if not token else "Invalid API token.",
        )

    session_token = (creds.credentials if creds else None) or session_cookie
    if session_token and _op_sessions.validate_session(session_token):
        return
    raise HTTPException(
        status_code=401,
        detail="Login required (run `gorgon login`) — the shared API token alone no "
               "longer authorizes this endpoint once an operator account exists.",
    )


def _current_operator(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_auth),
    session_cookie: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE_NAME),
) -> Optional[str]:
    """The authenticated operator's username, or None (pre-bootstrap, or a
    shared-token/localhost caller with no operator session). Resolved the same
    way _require_operator_auth validates — used by /chat so the forge wizard can
    re-verify the operator's password before forging."""
    from orchestrator.auth import sessions as _op_sessions, store as _op_store
    if not _op_store.operators_exist():
        return None
    token = (creds.credentials if creds else None) or session_cookie
    return _op_sessions.validate_session(token) if token else None


class ExecuteRequest(BaseModel):
    tool_name: str
    args:      Dict[str, Any] = {}
    verbose:   bool           = False
    log:       bool           = True


class ChatRequest(BaseModel):
    message:      str           = Field(..., max_length=_MAX_MESSAGE_LEN)
    session_id:   Optional[str] = None
    auto_confirm: bool          = False
    verbose:      bool          = False


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateOperatorRequest(BaseModel):
    username: str
    password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> Dict[str, Any]:
    """Liveness endpoint — return a simple ok status."""
    return {"status": "ok"}


@app.get("/info", dependencies=[Depends(_require_auth)])
def info() -> Dict[str, Any]:
    """Return server-side runtime info for the client banner."""
    from orchestrator.ai.chat.ollama_client import OLLAMA_URL, OLLAMA_MODEL
    try:
        import executor.api.qemu_config as _qc
        ovmf = _qc.OVMF
    except ImportError:
        ovmf = {"available": False, "code": ""}
    return {
        "ollama_model":   OLLAMA_MODEL,
        "ollama_url":     OLLAMA_URL,
        "ovmf_available": ovmf.get("available", False),
        "ovmf_code":      ovmf.get("code") or "",
        "agent_warnings": _active_agent_warnings(),
    }


@app.get("/events", dependencies=[Depends(_require_auth)])
def get_events(limit: int = 100, since: str = "") -> Dict[str, Any]:
    """Return recent server events (tool calls, outcomes, durations)."""
    from orchestrator.event_log import read_events
    return {"events": read_events(limit=limit, since=since)}


@app.get("/sync", dependencies=[Depends(_require_auth)])
def sync() -> Dict[str, Any]:
    """Return server-authoritative config the client should apply at startup."""
    ai_cfg_path = pathlib.Path(__file__).parent.parent / "ai" / "config.json"
    try:
        ai_cfg = json.loads(ai_cfg_path.read_text())
    except Exception:
        ai_cfg = {}

    try:
        from orchestrator.executor_client import execute_tool as _exec
        raw = _exec("list_vms", {})
        vms = raw if isinstance(raw, list) else raw.get("vms", [])
    except Exception:
        vms = []

    try:
        from orchestrator.executor_client import execute_tool as _exec
        profiles = _exec("list_profiles", {})
        if not isinstance(profiles, list):
            profiles = []
    except Exception:
        profiles = []

    vm_names      = [v.get("name") for v in vms]
    profile_names = [p.get("name") if isinstance(p, dict) else p for p in profiles]

    try:
        from executor.command_catalog import COMMAND_CATALOG
        commands = COMMAND_CATALOG
    except Exception:
        commands = []

    return {
        "shortcut_commands":    ai_cfg.get("shortcut_commands", {}),
        "allowed_remote_tools": list(_ALLOWED_TOOLS),
        "commands":             commands,
        "vms":      [{"name": n, "status": next((v.get("status") for v in vms if v.get("name") == n), None)}
                     for n in _filter_allowed(vm_names, _ALLOWED_VMS)],
        "profiles": _filter_allowed(profile_names, _ALLOWED_PROFILES),
    }


@app.post("/chat", dependencies=[Depends(_require_operator_auth)])
def chat(req: ChatRequest, operator: Optional[str] = Depends(_current_operator)) -> Dict[str, Any]:
    """Process one AI chat turn server-side (see chat_endpoint.handle_chat)."""
    return chat_endpoint.handle_chat(req, operator)


@app.get("/sessions", dependencies=[Depends(_require_auth)])
def list_sessions() -> Dict[str, Any]:
    """List active session IDs (debug/admin)."""
    return {"sessions": list(session_store.SESSIONS.keys())}


@app.delete("/sessions/{session_id}", dependencies=[Depends(_require_auth)])
def clear_session(session_id: str) -> Dict[str, Any]:
    """Delete a session's conversation history."""
    session_store.SESSIONS.pop(session_id, None)
    return {"ok": True, "session_id": session_id}


@app.post("/rotate-token", dependencies=[Depends(_require_operator_auth)])
def rotate_token(new_token: str = Body(..., embed=True)) -> Dict[str, Any]:
    """Replace the in-memory token and persist it to ~/.gorgon.token."""
    global _TOKEN
    if len(new_token) < _MIN_TOKEN_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"New token must be at least {_MIN_TOKEN_LEN} characters.",
        )
    _TOKEN = new_token
    os.environ["API_TOKEN"] = new_token
    # Create the file 0600 from the start — write_text()+chmod leaves a brief
    # world-readable window. chmod still covers a pre-existing looser file.
    _fd = os.open(str(_TOKEN_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(_fd, new_token.encode())
    finally:
        os.close(_fd)
    _TOKEN_FILE.chmod(0o600)
    return {"ok": True, "message": "Token rotated. Update API_TOKEN on the AI provider too."}


@app.post("/login")
def login(body: LoginRequest, response: Response) -> Dict[str, Any]:
    """Authenticate an operator; return a session token and set it as a cookie.

    No auth dependency — this IS the entry point auth hangs off of. Rate
    limiting/lockout is out of scope for 1.1 (single-operator, localhost-first
    threat model); revisit alongside the 1.2 multi-tenant work.
    """
    from orchestrator.auth import sessions as _op_sessions
    from orchestrator.auth import store as _op_store

    if not _op_store.verify_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = _op_sessions.create_session(body.username)
    response.set_cookie(key=_SESSION_COOKIE_NAME, value=token, httponly=True, samesite="lax")
    return {"success": True, "session_token": token, "username": body.username}


@app.post("/logout", dependencies=[Depends(_require_auth)])
def logout(
    response: Response,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_auth),
    session_cookie: Optional[str] = Cookie(default=None, alias=_SESSION_COOKIE_NAME),
) -> Dict[str, Any]:
    """Invalidate the caller's operator session (bearer token or cookie)."""
    from orchestrator.auth import sessions as _op_sessions
    token = (creds.credentials if creds else None) or session_cookie
    _op_sessions.invalidate_session(token)
    response.delete_cookie(_SESSION_COOKIE_NAME)
    return {"success": True}


@app.post("/operators", dependencies=[Depends(_require_operator_auth)])
def create_operator_endpoint(body: CreateOperatorRequest) -> Dict[str, Any]:
    """Create a new operator account.

    Reachable pre-bootstrap from localhost with no credentials at all — the
    same "localhost trusted until an operator exists" rule _require_auth
    applies everywhere else covers creating that first account too.
    """
    from orchestrator.auth import store as _op_store
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
    result = _op_store.create_operator(body.username, body.password)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.get("/operators", dependencies=[Depends(_require_auth)])
def list_operators_endpoint() -> Dict[str, Any]:
    """List all operator usernames."""
    from orchestrator.auth import store as _op_store
    return {"operators": _op_store.list_operators()}


@app.delete("/operators/{username}", dependencies=[Depends(_require_operator_auth)])
def delete_operator_endpoint(username: str) -> Dict[str, Any]:
    """Delete an operator account by username."""
    from orchestrator.auth import store as _op_store
    result = _op_store.delete_operator(username)
    if not result.get("success"):
        status = 409 if result.get("reason") == "last_operator" else 404
        raise HTTPException(status_code=status, detail=result.get("error"))
    return result


@app.post("/custom-mode", dependencies=[Depends(_require_auth)])
def custom_mode(enabled: bool = Body(..., embed=True)) -> Dict[str, Any]:
    """Toggle custom-machine mode (skip product verification) for -cu.

    Note: this is a process-global toggle (matches orchestrator/ai/cli.py's own
    -cu handling in local mode) — it affects every client talking to this
    orchestrator, not just the caller.
    """
    from orchestrator.preflight.validator import set_custom_mode
    set_custom_mode(enabled)
    return {"ok": True, "custom_mode": enabled}


@app.post("/execute", dependencies=[Depends(_require_operator_auth)])
def execute(req: ExecuteRequest) -> Any:
    """Dispatch a tool call (see execute_endpoint.handle_execute)."""
    return execute_endpoint.handle_execute(req)


# ── Ship-image delivery ───────────────────────────────────────────────────────

@app.get("/images/{vm_name}/sha256", dependencies=[Depends(_require_auth)])
def image_sha256(vm_name: str) -> Dict[str, Any]:
    """Return the SHA-256 checksum of the VM's primary disk."""
    return image_delivery.image_sha256(vm_name)


@app.get("/images/{vm_name}", dependencies=[Depends(_require_auth)])
def image_download(vm_name: str, request: Request) -> StreamingResponse:
    """Stream the VM's primary qcow2 disk — proxied from executor in remote mode."""
    return image_delivery.image_download(vm_name, request)


@app.get("/vms/{vm_name}/bundle", dependencies=[Depends(_require_auth)])
def vm_bundle(vm_name: str) -> StreamingResponse:
    """Stream the entire VM folder as a tar.gz — proxied from executor in remote mode."""
    return image_delivery.vm_bundle(vm_name)
