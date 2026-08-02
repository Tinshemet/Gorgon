"""commands/help_cmd.py — gorgon help / --help / -h."""

from client.cli.commands.base import Command
from client.cli.commands.context import _allowed_tools, console, Panel


class HelpCommand(Command):
    names = ("help", "--help", "-h")

    def run(self, cmd, rest, verbose):
        from shared.command_help import load_local_catalog, render_terminal_panel
        catalog, order = load_local_catalog()
        if catalog is None:
            console.print("[dim]Command list unavailable — the executor package "
                          "could not be loaded.[/dim]")
        else:
            body = render_terminal_panel(catalog, _allowed_tools(), order)
            # THE CATALOG IS THE EXECUTOR'S TOOL LIST, so it cannot name these: they reach
            # the ENGINE ARCHITECTURE rather than a tool, and there is no registry row to
            # read them off. Written here, and the only place in this file that is — if a
            # third one appears, that is the argument for the catalog growing a
            # client-side section rather than for a third list.
            body += (
                "\n\n[bold cyan]The engine path[/bold cyan]\n"
                "  plan <request>                 Plan it and run it, stage by stage\n"
                "  plan --dry <request>           Plan it and show it, WITHOUT acting\n"
                "  procedures                     The Medusa programs Gorgon has written\n"
                "  procedures show|verify <name>  Read one, or check it still loads\n"
                "  procedures run|delete <name>   Run one, or forget it\n"
                "  procedures syntax              Write the language reference\n"
                "  routines [run]                 What runs without being asked\n"
                "  books                          The creation ledger"
            )
            body += (
                "\n\n[bold cyan]Flags[/bold cyan]\n"
                "  -v                             Verbose / raw JSON output\n"
                "  -cu                            Custom mode: skip product verification\n"
                "  -cs                            Clear the saved session first"
            )
            console.print(Panel(body, title="gorgon help", border_style="cyan"))
