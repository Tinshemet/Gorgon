"""show-cmd — print the QEMU command line for a VM."""

from typing import List

from rich.panel import Panel

from .base import Command
from . import context as ctx


class ShowCmdCommand(Command):
    names = ("show-cmd",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.print_command(rest[0])
        if r.get("success"):
            ctx.console.print(Panel(r["command"], title="QEMU Command", border_style="cyan"))
