"""
context.py — Shared machinery for the direct-CLI command package.

Commands reference these as module attributes (``ctx.manager``, ``ctx.console``,
…) rather than binding them at import, so a test patches them in one place.
Mirrors client/cli/commands/context.py.
"""

import getpass
import json
import os
import threading
from typing import List

from orchestrator.executor_client import (
    execute_tool, API_URL, _VERIFY, _TOKEN, _TIMEOUT,
    get_ovmf as _get_ovmf, get_profiles as list_profiles,
    get_capabilities as check_system_capabilities, check_profile_compatibility,
)
from orchestrator.auth import store as _auth_store, sessions as _auth_sessions
from ..session import clear_session
from shared.display import (
    console, render_compat, render_fleet, render_fleets, render_monitor,
    render_profiles, render_templates, render_snapshots, render_status,
    render_system, render_vm_list,
)
try:
    from executor.tool_dispatch.tool_executor import manager
except ImportError:
    manager = None                                                            # type: ignore[assignment]


# executor/api/config.json is absent on an orchestrator-only checkout
# (files/executor/ isn't part of that sparse checkout) — fall back to defaults.
_SHARED_API_CFG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "executor", "api", "config.json",
)
try:
    _SHARED_API_CFG = json.load(open(_SHARED_API_CFG_PATH))
except (FileNotFoundError, json.JSONDecodeError):
    _SHARED_API_CFG = {}
_QEMU_HOST_IP = _SHARED_API_CFG.get("qemu_user_net_gateway", "10.0.2.2")
_IO_CHUNK     = _SHARED_API_CFG.get("io_chunk_bytes", 4 * 1024 * 1024)


def pp(data: object, verbose: bool) -> None:
    """Pretty-print a JSON result when running in verbose mode."""
    if verbose:
        console.print_json(json.dumps(data, default=str))


def tf_report(vm_name: str) -> None:
    """Print an inxi-style fingerprint report for a VM."""
    result = execute_tool("fingerprint_vm", {"name": vm_name})
    console.print(result.get("report") or result.get("error") or result)


def serve_dir_once(script_dir: str):
    """Bind a fresh HTTP server serving ``script_dir`` on a free port; return
    ``(server, port)``.

    Don't expose the script directory on every interface. In user-mode
    networking the guest reaches the host's loopback via the SLIRP gateway
    (10.0.2.2 → 127.0.0.1), so binding loopback is both reachable AND unexposed
    to the LAN; in bridged mode bind the gateway IP the host owns. A single
    foreground accept loop — the caller runs ``serve_forever`` itself.
    """
    import http.server
    import socket
    with socket.socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=script_dir, **kw)

        def log_message(self, *_) -> None:
            """Silence the default HTTP request logging."""
            pass  # silence access log

    _bind_host = "127.0.0.1" if _QEMU_HOST_IP == "10.0.2.2" else _QEMU_HOST_IP
    return http.server.HTTPServer((_bind_host, port), _Handler), port


def _show_stealth_popup(vm_name: str, setup_cmd: str) -> None:
    """Show the one-time stealth guest-setup instructions via a GUI popup."""
    import platform
    import subprocess
    is_win_guest = setup_cmd.startswith("irm ")
    if is_win_guest:
        how    = "Open PowerShell inside the VM and run:"
        reboot = "No reboot required."
    else:
        how    = "Open a terminal inside the VM and run:"
        reboot = "Then reboot the VM."
    text = (
        f"Stealth VM \"{vm_name}\" needs one-time guest setup.\n\n"
        f"{how}\n\n"
        f"  {setup_cmd}\n\n"
        f"{reboot}\n\n"
        f"When done, run on the host:\n"
        f"  gorgon setup-done {vm_name}"
    )
    title = f"Stealth Setup: {vm_name}"

    # ── Windows host ──────────────────────────────────────────────────────────
    if platform.system() == "Windows":
        try:
            import ctypes
            # Run in a daemon thread so the CLI doesn't block on the dialog
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(0, text, title, 0x40),
                daemon=True,
            ).start()
            return
        except Exception:
            pass  # ctypes/user32 unavailable — fall through to the next GUI method

    # ── Linux/macOS host: zenity first (GNOME/Cinnamon) ──────────────────────
    try:
        subprocess.Popen([
            "zenity", "--info",
            f"--title={title}",
            f"--text={text}",
            "--width=520",
            "--no-wrap",
        ])
        return
    except FileNotFoundError:
        pass  # zenity not installed — fall through to notify-send
    # notify-send (desktop notification, non-blocking)
    try:
        subprocess.Popen([
            "notify-send", title, setup_cmd,
            "--urgency=critical", "--expire-time=0",
        ])
        return
    except FileNotFoundError:
        pass  # notify-send not installed — fall through to tkinter
    # tkinter (universal fallback)
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(title, text)
        root.destroy()
    except Exception:
        pass  # no GUI toolkit available — the popup is optional, so give up silently


# login/logout bypass the gate itself (nothing to check a session against
# yet); everything else — including "operator" management — is held to it.
# Mirror of client/cli/commands/context.py's _operator_gate_ok: that module is
# the OTHER in-process path to `manager` (client_wrapper.py routes `gorgon <cmd>`
# there, not here), so any change to this gate must be made in both files.
_AUTH_EXEMPT_COMMANDS = {"login", "logout"}


def _operator_gate_ok(cmd: str) -> bool:
    """True if cmd may dispatch: no operator accounts exist yet (pre-bootstrap,
    identical to legacy behavior — nothing breaks until someone opts in via
    `gorgon login`), or this box holds a valid, unexpired login."""
    if cmd in _AUTH_EXEMPT_COMMANDS:
        return True
    if not _auth_store.operators_exist():
        return True
    return _auth_sessions.current_username() is not None
