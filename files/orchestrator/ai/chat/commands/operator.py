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
        elif sub == "passwd" and len(rest) >= 2:
            # Recovery for a forgotten password — deliberately does NOT ask for the
            # old one (see reset_password's docstring). Prompted via getpass so the
            # secret never lands in argv, shell history, or the terminal.
            while True:
                pw1 = getpass.getpass("New password: ")
                pw2 = getpass.getpass("Confirm new password: ")
                if pw1 != pw2:
                    ctx.console.print("[red]Passwords didn't match — try again.[/red]")
                    continue
                if len(pw1) < 8:
                    ctx.console.print("[red]Password must be at least 8 characters.[/red]")
                    continue
                break
            r = ctx._auth_store.reset_password(rest[1], pw1)
            ctx.console.print(f"[green]Password reset for '{rest[1]}'.[/green]" if r.get("success")
                              else f"[bold red]{r.get('error')}[/bold red]")
        else:
            ctx.console.print("[yellow]Usage: gorgon operator add|list|remove|passwd <username>[/yellow]")
