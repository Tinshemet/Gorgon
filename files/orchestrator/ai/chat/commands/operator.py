"""operator — manage operator accounts (add/list/remove)."""

import getpass
from typing import List

from .base import Command
from . import context as ctx


class OperatorCommand(Command):
    names = ("operator",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        sub = rest[0]
        if sub == "add" and len(rest) >= 2:
            pw = getpass.getpass("Password: ")
            r  = ctx._auth_store.create_operator(rest[1], pw)
            ctx.console.print(f"[green]Operator '{rest[1]}' created.[/green]" if r.get("success")
                              else f"[bold red]{r.get('error')}[/bold red]")
        elif sub == "list":
            for u in ctx._auth_store.list_operators():
                ctx.console.print(f"  {u}")
        elif sub == "remove" and len(rest) >= 2:
            r = ctx._auth_store.delete_operator(rest[1])
            ctx.console.print(f"[green]Operator '{rest[1]}' removed.[/green]" if r.get("success")
                              else f"[bold red]{r.get('error')}[/bold red]")
        else:
            ctx.console.print("[yellow]Usage: gorgon operator add|list|remove <username>[/yellow]")
