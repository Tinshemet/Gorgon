"""chat_client/render.py — the TUI frame (draw) + per-tool result rendering."""

import time

import curses

from client import config as _cfg
from client.ui.chat_client import state
from client.ui.chat_client.colors import (
    cp as _cp, C_HEADER, C_CYAN, C_GREEN, C_RED, C_DIM, C_YELLOW,
)
from client.ui.chat_client.conn import SERVER_URL
from client.ui.chat_client.history import add as _add
from client.ui.chat_client.vnc import vnc_host as _vnc_host, try_open_vnc as _try_open_vnc


def draw(stdscr: "curses.window", input_buf: str) -> None:
    """Redraw the full TUI — scrollback, separators, and the input/status line."""
    h, w = stdscr.getmaxyx()
    stdscr.erase()

    # Header
    spin_chars = _cfg.SPINNER_FRAMES
    spin  = f" {spin_chars[int(time.time() * 5) % len(spin_chars)]}" if state.waiting else "  "
    with state.lock:
        vm_parts = [
            (_cfg.GLYPH_RUNNING if v.get("status") == "running" else _cfg.GLYPH_STOPPED) + v.get("name", "")
            for v in state.remote_vms[:6]
        ]
    vm_str = "   ".join(vm_parts)
    hdr    = f" gorgon{spin} {SERVER_URL}   {vm_str}"
    try:
        stdscr.addstr(0, 0, hdr[:w - 1].ljust(w - 1), _cp(C_HEADER) | curses.A_BOLD)
    except curses.error:
        pass  # addstr fails past the screen edge — skip drawing the header

    # Separator
    try:
        stdscr.addstr(1, 0, "─" * (w - 1), _cp(C_DIM))
    except curses.error:
        pass  # addstr fails past the screen edge — skip the separator

    # Chat history (rows 2 .. h-5)
    chat_rows = max(1, h - 6)
    with state.lock:
        visible = list(state.history[-chat_rows:])
    for i, (attr, text) in enumerate(visible):
        row = 2 + i
        if row >= h - 4:
            break
        try:
            stdscr.addstr(row, 0, text[:w - 1], attr)
        except curses.error:
            pass  # addstr fails past the screen edge — skip this message row

    # Input separator
    try:
        stdscr.addstr(h - 4, 0, "─" * (w - 1), _cp(C_DIM))
    except curses.error:
        pass  # addstr fails past the screen edge — skip the input separator

    # Input / waiting line
    if state.waiting:
        try:
            stdscr.addstr(h - 3, 0, f" ⟳ waiting for response...", _cp(C_DIM))
        except curses.error:
            pass  # addstr fails past the screen edge — skip the waiting line
    else:
        _shown = ("•" * len(input_buf)) if state.is_password else input_buf
        prompt = f" > {_shown}"
        try:
            stdscr.addstr(h - 3, 0, prompt[:w - 1], _cp(C_CYAN) | curses.A_BOLD)
        except curses.error:
            pass  # addstr fails past the screen edge — skip the prompt

    # Hint line
    try:
        stdscr.addstr(h - 2, 0, _cfg.HINT_LINE[:w - 1], _cp(C_DIM))
    except curses.error:
        pass  # addstr fails past the screen edge — skip the hint line

    stdscr.refresh()


def render_tool_result(tool: str, result: dict) -> None:
    """Render a tool result into the scrollback, formatted per tool type."""
    if tool == "list_vms":
        vms = result if isinstance(result, list) else result.get("vms", [])
        if not vms:
            _add("  (no VMs)", _cp(C_DIM))
            return
        for v in vms:
            status = v.get("status", "?")
            dot    = _cfg.GLYPH_RUNNING if status == "running" else _cfg.GLYPH_STOPPED
            color  = _cp(C_GREEN) if status == "running" else _cp(C_DIM)
            ram    = f"{v.get('memory_mb', 0) // 1024}GB"
            cpu    = v.get("cpu_cores", "")
            os_s   = v.get("os", "")[:18]
            name   = v.get("name", "")[:22]
            flags  = v.get("flags") or []
            labels = v.get("labels") or []
            tags   = f"  [{' '.join(flags)}]" if flags else ""
            if labels:
                tags += "  " + " ".join(f"#{l}" for l in labels)
            _add(f"  {dot}{name:<22} {status:<12} {cpu}cpu  {ram:<6} {os_s:<18}{tags}", color)

    elif tool == "launch_vm":
        if result.get("success") or result.get("already_running"):
            port   = result.get("vnc_port", 5900)
            host   = _vnc_host()
            viewer = _try_open_vnc(port)
            msg    = f"  ✓ VNC: {host}:{port}"
            if viewer:
                msg += f"  (opened {viewer})"
            else:
                msg += f"  —  run: vncviewer {host}:{port}"
            _add(msg, _cp(C_GREEN) | curses.A_BOLD)
        else:
            _add(f"  ✖ {result.get('error', 'launch failed')}", _cp(C_RED))

    elif tool == "check_system":
        caps = result
        kvm  = caps.get("kvm_available") and caps.get("kvm_readable")
        virt = caps.get("vmx") or caps.get("svm")
        ovmf = caps.get("ovmf") or {}
        rows = [
            ("CPU",        f"{caps.get('host_cpu_cores', '?')} cores  ({caps.get('host_cpu', '?')})"),
            ("RAM",        f"{caps.get('host_memory_mb', 0) // 1024} GB"),
            ("Disk free",  f"{caps.get('home_free_gb', '?')} GB"),
            ("Arch",       caps.get("host_arch", "?")),
            ("KVM",        "✓" if kvm  else "✗"),
            ("VT-x/AMD-V", "✓" if virt else "✗"),
        ]
        qemu = caps.get("qemu_version", "")
        if qemu:
            rows.append(("QEMU", qemu[:70]))
        if caps.get("qemu_arm_installed"):
            rows.append(("qemu-arm", "✓"))
        if ovmf.get("code"):
            rows.append(("OVMF", ovmf["code"]))
        for label, value in rows:
            if value in ("✓", "✗"):
                attr = _cp(C_GREEN) if value == "✓" else _cp(C_RED)
            else:
                attr = _cp(C_DIM)
            _add(f"    {label:<16} {value}", attr)

    elif tool == "create_vm":
        if result.get("success"):
            _vm_msg = result.get("message") or f"VM '{result.get('name', '')}' created."
            _add(f"  ✓ {_vm_msg}", _cp(C_GREEN))
            # The ISO-vs-declared-OS mismatch check is done server-side (the
            # executor owns the ISO/OS keyword data — the single source of truth);
            # the client just renders the advisory when present.
            _iso_warn = result.get("iso_os_warning")
            if _iso_warn:
                _add(f"  ⚠ {_iso_warn}", _cp(C_YELLOW) | curses.A_BOLD)
        else:
            _add(f"  ✖ {result.get('error', 'create_vm failed')}", _cp(C_RED))

    elif tool in ("list_profiles",):
        profiles = result if isinstance(result, list) else result.get("profiles", [])
        for p in profiles:
            name = (p.get("name", "") if isinstance(p, dict) else str(p))
            desc = (p.get("description", "") if isinstance(p, dict) else "")
            _add(f"  {name:<28} {desc}", _cp(C_DIM))
        if not profiles:
            _add("  (no profiles)", _cp(C_DIM))

    elif tool == "list_templates":
        templates = result if isinstance(result, list) else result.get("templates", [])
        for t in templates:
            name    = t.get("name", "") if isinstance(t, dict) else str(t)
            os_type = t.get("os_type", "") if isinstance(t, dict) else ""
            disks   = t.get("disks", "") if isinstance(t, dict) else ""
            _add(f"  {name:<28} {os_type:<10} {disks} disk(s)", _cp(C_DIM))
        if not templates:
            _add("  (no templates)", _cp(C_DIM))
        # mark_as_template / remove_template need no dedicated branch — both return a
        # plain {"success", "message"/"error"} dict already handled by the generic
        # fallback further down.

    elif tool in ("vm_status", "monitor_vm"):
        status = result.get("status", "?")
        color  = _cp(C_GREEN) if status == "running" else _cp(C_DIM)
        _add(f"  {result.get('name', '')}  status={status}  "
             f"cpu={result.get('cpu', '?')}%  mem={result.get('memory', '?')}", color)

    elif tool == "list_snapshots":
        snaps = result if isinstance(result, list) else result.get("snapshots", [])
        for s in snaps:
            _add(f"  {s.get('name', ''):<24} {s.get('date', '')}", _cp(C_DIM))
        if not snaps:
            _add("  (no snapshots)", _cp(C_DIM))

    elif result.get("setup_cmd"):
        setup_cmd = result["setup_cmd"]
        vm_name   = result.get("name", "")
        is_win    = setup_cmd.startswith("irm ")
        dest      = "PowerShell inside the VM" if is_win else "a terminal inside the VM (then reboot)"
        _add(f"  ▶ Stealth setup required. Open {dest} and run:", _cp(C_YELLOW) | curses.A_BOLD)
        _add(f"      {setup_cmd}", _cp(C_CYAN))
        _add(f"  When done:  setup-done {vm_name}", _cp(C_DIM))

    elif result.get("vnc_connect_cmd"):
        _add(f"  VNC: {result['vnc_connect_cmd']}", _cp(C_CYAN))

    elif not result.get("success") and result.get("error"):
        _add(f"  ✖ {result['error']}", _cp(C_RED))

    elif result.get("success") and result.get("message"):
        _add(f"  ✓ {result['message']}", _cp(C_GREEN))
