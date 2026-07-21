"""
chat_client — the curses AI-chat TUI (client-side).

Bare `gorgon` (no args) routes here via client_wrapper.py. Split into focused
modules; this package exposes the single public entry point, chat_loop:
    state      — shared mutable UI state
    conn       — connection constants + auth handles
    colors     — curses palette (config-driven)
    session    — chat session-id persistence
    history    — the scrollback buffer
    render     — the TUI frame + per-tool result rendering
    vnc        — VNC viewer launch
    net        — HTTP calls, /sync, the chat worker
    autostart  — local orchestrator autostart
    response   — apply a /chat reply
    help       — the in-TUI command help
    operator   — mission + claim chat verbs
    dispatch   — built-in shortcuts
    app        — the curses main loop + chat_loop
"""

from client.ui.chat_client.app import chat_loop

__all__ = ["chat_loop"]
