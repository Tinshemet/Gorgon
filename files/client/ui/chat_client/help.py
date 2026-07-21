"""chat_client/help.py — the in-TUI command help, rendered from the command catalog."""

import curses

from client.ui.chat_client import state
from client.ui.chat_client.colors import cp as _cp, C_CYAN, C_DIM
from client.ui.chat_client.history import add as _add, add_sep as _add_sep


def show_help() -> None:
    """Print the in-TUI command help into the scrollback, rendered from the command catalog.

    Shows every command available to the user (filtered to the allowed-tools list) plus
    a short example prompt per command for the AI. Both the catalog and the allow-list
    come from /sync; falls back to the local catalog when the server list is empty.
    """
    from shared.command_help import visible_commands, load_local_catalog
    catalog = state.commands
    if not catalog:
        catalog, _ = load_local_catalog()
    _add_sep()

    if not catalog:
        _add("  Command list unavailable (sync the server to load it).", _cp(C_DIM))
        _add_sep()
        return

    entries = visible_commands(catalog, state.allowed_tools or None)
    _add("  Commands (type the word, or just ask in plain language):",
         _cp(C_CYAN) | curses.A_BOLD)
    for e in entries:
        verb = e["command"] + (" " + e["args"] if e["args"] else "")
        _add(f"    {verb:<28} {e['desc']}", _cp(C_DIM))

    _add("  Example prompts for the AI:", _cp(C_CYAN) | curses.A_BOLD)
    for e in entries:
        ex = e.get("ai_example")
        if ex:
            _add(f"    {ex}", _cp(C_DIM))

    _add("  Built-in: drift · clear/clear session · help/? · q/quit/exit", _cp(C_DIM))
    _add("  Operator: mission [list|run <name>|\"<goal>\"] · claim [list|confirm <fact>|reject <fact>]",
         _cp(C_DIM))
    _add_sep()
