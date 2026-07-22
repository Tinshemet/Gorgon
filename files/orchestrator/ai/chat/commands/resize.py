"""resize — grow a VM's disk."""

from typing import List

from .base import Command
from . import context as ctx


class ResizeCommand(Command):
    names = ("resize",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r     = ctx.manager.resize_disk(rest[0], 0, int(rest[1]))
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
