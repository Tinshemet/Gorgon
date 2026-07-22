"""cmd — send a raw QEMU monitor command to a VM."""

from typing import List

from .base import Command
from . import context as ctx


class MonitorCmdCommand(Command):
    names = ("cmd",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.send_monitor_cmd(rest[0], rest[1])
        if r.get("success"):
            ctx.console.print(r["output"])
