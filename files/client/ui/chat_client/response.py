"""chat_client/response.py — apply a /chat response (render text/tools, set confirm state)."""

import textwrap

import curses

from client import config as _cfg
from client.ui.chat_client import state
from client.ui.chat_client.colors import cp as _cp, C_CYAN, C_DIM, C_RED, C_YELLOW
from client.ui.chat_client.history import add as _add
from client.ui.chat_client.render import render_tool_result as _render_tool_result
from client.ui.chat_client.session import save_session_id as _save_session_id


def process_response(result: dict, verbose: bool = False) -> None:
    """Apply a /chat response — render text/tools and update confirm state."""
    if result.get("error"):
        _add(f"  ✖ {result['error']}", _cp(C_RED))
        return

    sid = result.get("session_id", state.session_id)
    if sid:
        state.session_id = sid
        _save_session_id(sid)

    for tr in result.get("tool_results", []):
        tool = tr.get("tool", "")
        res  = tr.get("result", {})
        if tool:
            _add(f"  [{tool}]", _cp(C_DIM))
        _render_tool_result(tool, res)

    text = result.get("text", "").strip()
    if text:
        _add(f" AI:", _cp(C_CYAN) | curses.A_BOLD)
        # Preserve the server's line breaks — wrap each line on its own so a
        # multi-line reply (issue lists, the rendered contract box) keeps its
        # structure instead of collapsing into one re-wrapped paragraph.
        for para in text.split("\n"):
            for line in textwrap.wrap(para, _cfg.WRAP_WIDTH) or [""]:
                _add(f"    {line}", _cp(C_CYAN))

    ni = result.get("needs_input")
    if ni:
        state.needs_confirm = True
        ni_type  = ni.get("type", "clarify")
        question = ni.get("question", "Confirm?")
        opts     = ni.get("options", [])
        proposed = ni.get("proposed", "")
        state.is_confirm = ni_type in ("confirm_yn", "confirm_name", "confirm_critical", "preflight")
        state.is_password = ni_type == "password"
        # 'prompt' is a free-text wizard answer — the question is already in the AI
        # text, so don't re-render a ▶ line; allow_empty lets a blank Enter through.
        state.allow_empty = ni_type == "prompt" and bool(ni.get("allow_empty"))
        if ni_type != "prompt":
            color = _cp(C_RED) if ni_type == "confirm_critical" else _cp(C_YELLOW)
            _add(f"  ▶ {question}", color | curses.A_BOLD)
            if proposed:
                _add(f"    Type exactly: {proposed}", _cp(C_RED))
            if opts:
                _add(f"    Options: {' / '.join(opts)}", _cp(C_DIM))
    else:
        state.needs_confirm = False
        state.is_confirm    = False
        state.is_password   = False
        state.allow_empty   = False
