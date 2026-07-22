"""login — log in (bootstraps the first operator if none exist)."""

import getpass
from typing import List

from .base import Command
from . import context as ctx


class LoginCommand(Command):
    names = ("login",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        username = rest[0] if rest else None
        if not ctx._auth_store.operators_exist():
            ctx.console.print("[bold cyan]No operator account exists yet — creating the first one.[/bold cyan]")
            username = username or ctx.console.input("Username: ").strip()
            while True:
                pw1 = getpass.getpass("Password: ")
                pw2 = getpass.getpass("Confirm password: ")
                if pw1 != pw2:
                    ctx.console.print("[red]Passwords didn't match — try again.[/red]")
                    continue
                if len(pw1) < 8:
                    ctx.console.print("[red]Password must be at least 8 characters.[/red]")
                    continue
                break
            r = ctx._auth_store.create_operator(username, pw1)
            if not r.get("success"):
                ctx.console.print(f"[bold red]{r.get('error')}[/bold red]")
                return
            password = pw1
        else:
            username = username or ctx.console.input("Username: ").strip()
            password = getpass.getpass("Password: ")
        if not ctx._auth_store.verify_password(username, password):
            ctx.console.print("[bold red]Invalid username or password.[/bold red]")
            return
        token = ctx._auth_sessions.create_session(username)
        ctx._auth_sessions.write_current_session(token)
        ctx.console.print(f"[bold green]Logged in as '{username}'.[/bold green]")
