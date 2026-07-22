"""delete — remove a VM (interactive confirm)."""

from typing import List

from .base import Command
from . import context as ctx


class DeleteCommand(Command):
    names = ("delete",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        if ctx.console.input(f"[warn]Delete '{rest[0]}'? [y/N]:[/warn] ").lower() == "y":
            r = ctx.manager.delete_vm(rest[0])
            ctx.console.print(f"[success]{r.get('message', r.get('error'))}[/success]")
