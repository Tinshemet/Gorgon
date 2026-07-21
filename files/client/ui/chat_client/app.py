"""chat_client/app.py — the curses main loop + the public chat_loop entry point."""

import queue
import sys
import threading
import time
import uuid

import curses

from client import config as _cfg
from client.ui.chat_client import state
from client.ui.chat_client.autostart import autostart_server as _autostart_server
from client.ui.chat_client.colors import (
    init_colours as _init_colours, cp as _cp, C_BOLD, C_DIM, C_GREEN, C_RED, C_YELLOW,
)
from client.ui.chat_client.conn import SERVER_URL, _auth_store, _auth_sessions
from client.ui.chat_client.dispatch import dispatch as _dispatch
from client.ui.chat_client.history import add as _add
from client.ui.chat_client.net import (
    execute as _execute, http_worker as _http_worker, is_localhost as _is_localhost,
    server_reachable as _server_reachable, sync_from_server as _sync_from_server,
)
from client.ui.chat_client.operator import apply_claim as _apply_claim, render_mission_result as _render_mission_result
from client.ui.chat_client.render import draw as _draw
from client.ui.chat_client.response import process_response as _process_response
from client.ui.chat_client.session import load_session_id as _load_session_id, save_session_id as _save_session_id


def _run(stdscr: "curses.window", verbose: bool = False, color_hex: str = None, font_size: int = None) -> None:
    """curses main loop — draw, read keys, and dispatch commands until quit."""
    if font_size is None:
        font_size = _cfg.FONT_SIZE

    curses.curs_set(0)
    stdscr.timeout(100)
    _init_colours(color_hex)

    # Resize terminal and set font size (best-effort; xterm-compatible terminals).
    # Geometry comes from config (terminal_rows/cols).
    sys.stdout.write(f"\033]50;xft:{_cfg.FONT_FAMILY}:size={font_size}\007")
    sys.stdout.write(f"\033[8;{_cfg.TERM_ROWS};{_cfg.TERM_COLS}t")
    sys.stdout.flush()
    time.sleep(_cfg.STARTUP_DELAY_S)

    state.session_id = _load_session_id() or str(uuid.uuid4())
    _save_session_id(state.session_id)

    _add(f"  Connecting to {SERVER_URL}...", _cp(C_DIM))
    _draw(stdscr, "")

    if _is_localhost() and not _server_reachable():
        _add("  Server not running — starting it...", _cp(C_YELLOW))
        _draw(stdscr, "")
        started = _autostart_server(stdscr)
        if started:
            _add("  Server ready.", _cp(C_GREEN))
        else:
            _add(f"  Could not start server. Check {_cfg.LOG_PATH}", _cp(C_RED))
        _draw(stdscr, "")

    ok = _sync_from_server()

    with state.lock:
        state.history.clear()

    _add(f"  gorgon  →  {SERVER_URL}", _cp(C_GREEN) | curses.A_BOLD)
    if not ok:
        _add(f"  ⚠ Could not reach server. Check connection.", _cp(C_YELLOW))
    elif state.remote_vms:
        vm_summary = "  ".join(
            (_cfg.GLYPH_RUNNING if v.get("status") == "running" else _cfg.GLYPH_STOPPED) + v.get("name", "")
            for v in state.remote_vms
        )
        _add(f"  VMs:  {vm_summary}", _cp(C_DIM))
    if state.remote_profiles:
        _pnames = ',  '.join(
            str(p) if not isinstance(p, dict) else p.get('name', '')
            for p in state.remote_profiles[:8]
        )
        _add(f"  Profiles:  {_pnames}", _cp(C_DIM))
    _add("", 0)
    _add('  Type a message or ask the AI anything. Type "help" for shortcuts.', _cp(C_DIM))
    _add("", 0)

    input_buf = ""

    while not state.quit_event.is_set():
        # Drain HTTP response queue
        try:
            result = state.resp_q.get_nowait()
            state.waiting = False
            if isinstance(result, dict) and "_mission" in result:
                _render_mission_result(result["_mission"])   # locally-run mission, not a /chat reply
            else:
                _process_response(result, verbose)
        except queue.Empty:
            pass  # no response queued this tick — nothing to drain

        _draw(stdscr, input_buf if not state.waiting else "")

        if state.waiting:
            time.sleep(0.05)
            continue

        try:
            ch = stdscr.get_wch()
        except curses.error:
            continue

        if ch in (3, "\x03"):          # Ctrl-C
            state.quit_event.set()
            break

        if ch in ("\n", "\r", curses.KEY_ENTER):
            cmd = input_buf.strip()
            input_buf = ""
            if not cmd and not state.allow_empty:      # empty Enter is a real answer when a wizard field allows blank
                continue

            # Pending claim confirm/reject — the next line is the operator password.
            if state.pending_claim:
                action, fact = state.pending_claim
                state.pending_claim = None
                state.is_password = False
                _add("  You: " + "•" * len(cmd), _cp(C_BOLD) | curses.A_BOLD)
                user = _auth_sessions.current_username() if _auth_sessions else None
                if user and _auth_store is not None and _auth_store.verify_password(user, cmd):
                    _apply_claim(action, fact)
                else:
                    _add("  Password incorrect — aborted.", _cp(C_RED))
                continue

            # Pending kill confirmation
            if state.pending_kill:
                vm = state.pending_kill
                state.pending_kill = ""
                _add(f"  You: {cmd}", _cp(C_BOLD) | curses.A_BOLD)
                if cmd.lower() in ("y", "yes"):
                    result = _execute("stop_vm", {"name": vm, "force": True})
                    if result.get("success"):
                        _add(f"  ✓ {vm} force-stopped.", _cp(C_GREEN))
                    else:
                        _add(f"  ✖ {result.get('error', 'failed')}", _cp(C_RED))
                else:
                    _add("  Cancelled.", _cp(C_DIM))
                continue

            _disp = ("•" * len(cmd)) if state.is_password else cmd
            _add(f"  You: {_disp}", _cp(C_BOLD) | curses.A_BOLD)

            # Built-in shortcuts
            if not state.needs_confirm and _dispatch(cmd, verbose):
                continue

            # Send to AI via HTTP worker thread
            auto_confirm = state.is_confirm if state.needs_confirm else False
            state.needs_confirm = False
            state.is_confirm    = False
            state.is_password   = False
            state.allow_empty   = False
            state.waiting = True
            threading.Thread(
                target=_http_worker,
                args=(cmd, auto_confirm, verbose),
                daemon=True,
            ).start()

        elif ch in (curses.KEY_BACKSPACE, "\x7f", 8):
            input_buf = input_buf[:-1]

        elif isinstance(ch, str) and ch.isprintable():
            input_buf += ch


def chat_loop(verbose: bool = False, color_hex: str = None, font_size: int = None) -> None:
    """Entry point — run the curses chat client until the user exits.

    Same gate as client/cli/commands' operator gate and orchestrator/ai/cli.py's
    chat_loop — bare `gorgon` (no args) routes here via client_wrapper.py, a THIRD
    entry point that needed this independently (see the dual-CLI-dispatch note).
    """
    if (_auth_store is not None and _auth_store.operators_exist()
            and _auth_sessions.current_username() is None):
        print("Login required. Run `gorgon login` first.")
        return
    try:
        curses.wrapper(lambda s: _run(s, verbose, color_hex, font_size))
    except KeyboardInterrupt:
        pass  # Ctrl-C — exit the TUI cleanly
