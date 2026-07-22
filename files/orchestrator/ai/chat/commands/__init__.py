"""
commands — the direct ``gorgon <cmd>`` sub-command package.

Every module here (except ``base``/``context``) defines one ``Command`` subclass;
importing them fires ``__init_subclass__``, which fills ``ALL_COMMANDS``, folded
below into a verb → instance registry. ``cli_direct`` is the dispatcher: it holds
every command to the operator gate, enforces per-command ``min_args``, and renders
the help panel for anything unrecognised. Adding a command is one new file.

Mirrors client/cli/commands/__init__.py.
"""

import importlib
import pkgutil
from typing import List

from rich.panel import Panel

from .base import ALL_COMMANDS
from . import context as ctx

# Import every command module so its Command subclass registers itself.
for _mod in pkgutil.iter_modules(__path__):
    if _mod.name not in ("base", "context"):
        importlib.import_module(f"{__name__}.{_mod.name}")

# Fold registered commands into a verb → instance registry (duplicate = loud error).
_REGISTRY: dict = {}
for _cls in ALL_COMMANDS:
    _instance = _cls()
    for _name in _cls.names:
        if _name in _REGISTRY:
            raise RuntimeError(f"duplicate direct-CLI command verb: {_name!r}")
        _REGISTRY[_name] = _instance


def _render_help() -> None:
    """Render the ``gorgon help`` panel (executor catalog + direct-CLI extras)."""
    from shared.command_help import load_local_catalog, render_terminal_panel
    try:
        from orchestrator.executor_client import _ALLOWED_TOOLS
        allowed = set(_ALLOWED_TOOLS) or None
    except Exception:
        allowed = None
    catalog, order = load_local_catalog()
    body = (render_terminal_panel(catalog, allowed, order) if catalog
            else "[dim]Command list unavailable.[/dim]")
    body += (
        "\n\n[bold cyan]Direct-CLI extras[/bold cyan]\n"
        "  limit <vm> <cpu%> \\[mem_mb]     Set CPU/memory resource limits\n"
        "  cmd <vm> \"<monitor cmd>\"        Send a raw QEMU monitor command\n"
        "  reliability \\[agent]|reset       Show / reset learned per-tool p_world\n"
        "  claim \\[list]|confirm|reject     Review / confirm parked claim findings\n"
        "  (in chat) verbose on|off        Toggle the debug view: risk weights, tier, reward-cost knobs\n"
        "  serve \\[host] \\[port]           Run this node as the executor API\n"
        "  clear-session                  Wipe the saved AI session\n"
        "  -tf <vm>                       Show a fingerprint report for a VM\n"
        "  login \\[username]               Log in (creates the first operator if none exist)\n"
        "  logout                         End this box's login session\n"
        "  operator add|list|remove       Manage operator accounts (requires login)\n\n"
        "[bold cyan]Flags[/bold cyan]\n"
        "  -v   verbose / raw output      -cu  custom mode      -cs  clear session first"
    )
    ctx.console.print(Panel(body, border_style="cyan", title="gorgon help"))


# Dispatches direct sub-commands (list, launch, stop, snapshot, network, etc.) to
# the registered Command and renders output.
# In: List[str] args, bool verbose → Out: nothing
def cli_direct(args: List[str], verbose: bool = False) -> None:
    """Dispatch a direct ``gorgon <cmd>`` sub-command and render its output."""
    if ctx.manager is None:
        ctx.console.print("[bold yellow]Direct CLI requires the client package. In server-only mode use the AI chat — commands execute remotely via API_URL.[/bold yellow]")
        return

    if not args:
        _render_help()
        return

    cmd  = args[0]
    rest = args[1:]

    if not ctx._operator_gate_ok(cmd):
        ctx.console.print("[bold red]Login required.[/bold red] Run [cyan]gorgon login[/cyan] first.")
        return

    command = _REGISTRY.get(cmd)
    if command is None or len(rest) < command.min_args:
        _render_help()
        return

    command.run(cmd, rest, verbose)
