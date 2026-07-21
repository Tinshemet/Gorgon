"""chat_client/dispatch.py — built-in chat shortcuts (list/system/drift/kill/mission/claim…)."""

import uuid

import curses
import requests

from client.ui.chat_client import state
from client.ui.chat_client.colors import cp as _cp, C_DIM, C_GREEN, C_YELLOW
from client.ui.chat_client.conn import SERVER_URL, _HEADERS, _VERIFY
from client.ui.chat_client.history import add as _add
from client.ui.chat_client.net import execute as _execute
from client.ui.chat_client.render import render_tool_result as _render_tool_result
from client.ui.chat_client.session import save_session_id as _save_session_id
from client.ui.chat_client.help import show_help as _show_help
from client.ui.chat_client.operator import handle_claim as _handle_claim, handle_mission as _handle_mission


def dispatch(cmd: str, verbose: bool) -> bool:
    """Handle a built-in shortcut. Returns True if handled (no HTTP needed)."""
    low = cmd.lower().strip()

    if low in state.exit_cmds:
        state.quit_event.set()
        return True

    if low in state.sc_clear:
        try:
            requests.delete(f"{SERVER_URL}/sessions/{state.session_id}",
                            headers=_HEADERS, timeout=10, verify=_VERIFY)
        except Exception:
            pass  # best-effort server-side session clear — ignore network errors
        state.session_id = str(uuid.uuid4())
        _save_session_id(state.session_id)
        _add("  Session cleared.", _cp(C_DIM))
        state.needs_confirm = False
        state.is_confirm    = False
        state.is_password   = False
        return True

    if low in state.sc_help:
        _show_help()
        return True

    # Operator verbs, wired into the chat (mirror the terminal `gorgon claim/mission`).
    if low == "claim" or low.startswith("claim "):
        _handle_claim(cmd.strip()[len("claim"):].strip())
        return True
    if low == "mission" or low.startswith("mission "):
        _handle_mission(cmd.strip()[len("mission"):].strip(), verbose)
        return True

    # list / list <label> — an optional trailing flag or user label filters the list
    _list_pfx = next((p for p in ("list ", "vms ", "ls ") if low.startswith(p)), None)
    if low in state.sc_list or _list_pfx:
        label = cmd.strip()[len(_list_pfx):].strip() if (_list_pfx and low not in state.sc_list) else ""
        result = _execute("list_vms", {"label": label} if label else {})
        _render_tool_result("list_vms", result)
        return True

    if low in state.sc_system:
        result = _execute("check_system")
        _render_tool_result("check_system", result)
        return True

    if low in state.sc_profiles:
        result = _execute("list_profiles")
        _render_tool_result("list_profiles", result)
        return True

    if low in state.sc_templates:
        result = _execute("list_templates")
        _render_tool_result("list_templates", result)
        return True

    if low in state.sc_drift:
        result = _execute("check_drift")
        if result.get("drifted"):
            _add("  Drift detected:", _cp(C_YELLOW) | curses.A_BOLD)
            for k, v in result.items():
                if k != "drifted":
                    _add(f"    {k}: {v}", _cp(C_DIM))
        else:
            _add("  ✓ No drift detected.", _cp(C_GREEN))
        return True

    # kill <name> shortcut
    for pfx in ("kill ", "force stop ", "force kill ", "hard stop "):
        if low.startswith(pfx):
            name = cmd[len(pfx):].strip()
            if name:
                state.pending_kill = name
                _add(f"  Force-kill (SIGKILL) VM: {name}?  [yes / cancel]",
                     _cp(C_YELLOW) | curses.A_BOLD)
                return True

    return False
