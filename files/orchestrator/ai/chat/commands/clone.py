"""clone — copy a VM to a new name."""

from typing import List

from .base import Command
from . import context as ctx


class CloneCommand(Command):
    names = ("clone",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r     = ctx.manager.clone_vm(rest[0], rest[1])
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
