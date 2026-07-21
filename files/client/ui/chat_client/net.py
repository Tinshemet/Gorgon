"""chat_client/net.py — HTTP calls to the server, the /sync refresh, and the chat worker."""

import requests

from client import config as _cfg
from client.ui.chat_client import state
from client.ui.chat_client.conn import SERVER_URL, _HEADERS, _TIMEOUT, _VERIFY


def post_chat(message: str, session_id: str,
              auto_confirm: bool = False, verbose: bool = False) -> dict:
    """POST a message to the server's /chat endpoint; return the parsed response."""
    payload = {
        "message":      message,
        "session_id":   session_id,
        "auto_confirm": auto_confirm,
        "verbose":      verbose,
    }
    try:
        resp = requests.post(
            f"{SERVER_URL}/chat",
            json=payload, headers=_HEADERS,
            timeout=_TIMEOUT, verify=_VERIFY,
        )
    except requests.ConnectionError:
        return {"error": f"Cannot connect to {SERVER_URL}"}
    except Exception as e:
        return {"error": str(e)}

    if resp.status_code == 401:
        return {"error": "Server rejected token (401) — check API_TOKEN"}
    if not resp.ok:
        return {"error": f"Server error {resp.status_code}"}

    try:
        return resp.json()
    except Exception as e:
        return {"error": f"Invalid JSON from server: {e}"}


def execute(tool_name: str, args: dict | None = None) -> dict:
    """POST a direct tool call to the server's /execute endpoint; return the result."""
    if args is None:
        args = {}
    try:
        resp = requests.post(
            f"{SERVER_URL}/execute",
            json={"tool_name": tool_name, "args": args, "verbose": False},
            headers=_HEADERS, timeout=_TIMEOUT, verify=_VERIFY,
        )
        if not resp.ok:
            try:
                body = resp.json()
                msg = body.get("result", {}).get("error") or body.get("detail") or f"Server error {resp.status_code}"
            except Exception:
                msg = f"Server error {resp.status_code}"
            return {"success": False, "error": msg}
        return resp.json().get("result", {})
    except requests.ConnectionError:
        return {"success": False, "error": f"Cannot connect to {SERVER_URL}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def is_localhost() -> bool:
    """Return True when the configured server URL points at the local machine."""
    from urllib.parse import urlparse
    host = urlparse(SERVER_URL).hostname or "localhost"
    return host in ("localhost", "127.0.0.1", "::1")


def server_reachable() -> bool:
    """Return True if the server's /health endpoint answers."""
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=_cfg.HEALTH_TIMEOUT_S, verify=_VERIFY)
        return r.ok
    except Exception:
        return False


def sync_from_server() -> bool:
    """Refresh the cached remote VM/profile lists from the server; return success."""
    try:
        resp = requests.get(f"{SERVER_URL}/sync",
                            headers=_HEADERS, timeout=_cfg.REQUEST_TIMEOUT_S, verify=_VERIFY)
        if not resp.ok:
            return False
        data = resp.json()
    except Exception:
        return False

    sc = data.get("shortcut_commands", {})
    if sc.get("list"):          state.sc_list      = set(sc["list"])
    if sc.get("system"):        state.sc_system    = set(sc["system"])
    if sc.get("profiles"):      state.sc_profiles  = set(sc["profiles"])
    if sc.get("templates"):     state.sc_templates = set(sc["templates"])
    if sc.get("drift"):         state.sc_drift     = set(sc["drift"])
    if sc.get("clear_session"): state.sc_clear     = set(sc["clear_session"]) | {"/clear"}

    state.remote_vms      = data.get("vms", [])
    state.remote_profiles = data.get("profiles", [])
    state.commands        = data.get("commands", []) or state.commands
    state.allowed_tools   = set(data.get("allowed_remote_tools", []))
    return True


def http_worker(message: str, auto_confirm: bool, verbose: bool) -> None:
    """Background thread body — send one message and queue the response."""
    result = post_chat(message, state.session_id, auto_confirm, verbose)
    state.resp_q.put(result)
