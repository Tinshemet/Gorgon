"""stop — stop a running VM."""

from typing import List

from .base import Command
from . import context as ctx


class StopCommand(Command):
    names = ("stop",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r     = ctx.manager.stop_vm(rest[0])
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
