"""commands/operator.py — gorgon operator add|list|remove <username>."""

import getpass

from client.cli.commands.base import Command
from client.cli.commands.context import _auth_store, console


class OperatorCommand(Command):
    names = ("operator",)
    min_args = 1

    def run(self, cmd, rest, verbose):
        if _auth_store is None:
            console.print("[bold red]Auth package unavailable on this checkout.[/bold red]")
            return
        sub = rest[0]
        if sub == "add" and len(rest) >= 2:
            pw = getpass.getpass("Password: ")
            r  = _auth_store.create_operator(rest[1], pw)
            console.print(f"[green]Operator '{rest[1]}' created.[/green]" if r.get("success")
                          else f"[bold red]{r.get('error')}[/bold red]")
        elif sub == "list":
            for u in _auth_store.list_operators():
                console.print(f"  {u}")
        elif sub == "remove" and len(rest) >= 2:
            r = _auth_store.delete_operator(rest[1])
            console.print(f"[green]Operator '{rest[1]}' removed.[/green]" if r.get("success")
                          else f"[bold red]{r.get('error')}[/bold red]")
        elif sub == "passwd" and len(rest) >= 2:
            # Recovery for a forgotten password — deliberately does NOT ask for the
            # old one (see reset_password's docstring). Prompted via getpass so the
            # secret never lands in argv, shell history, or the terminal.
            while True:
                pw1 = getpass.getpass("New password: ")
                pw2 = getpass.getpass("Confirm new password: ")
                if pw1 != pw2:
                    console.print("[red]Passwords didn't match — try again.[/red]")
                    continue
                if len(pw1) < 8:
                    console.print("[red]Password must be at least 8 characters.[/red]")
                    continue
                break
            r = _auth_store.reset_password(rest[1], pw1)
            console.print(f"[green]Password reset for '{rest[1]}'.[/green]" if r.get("success")
                          else f"[bold red]{r.get('error')}[/bold red]")
        else:
            console.print("[yellow]Usage: gorgon operator add|list|remove|passwd <username>[/yellow]")
