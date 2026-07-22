"""monitor — live resource view for one VM or all."""

from typing import List

from .base import Command
from . import context as ctx


class MonitorCommand(Command):
    names = ("monitor",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        name = rest[0] if rest else "all"
        r    = ctx.manager.monitor_all() if name == "all" else ctx.manager.monitor_vm(name)
        if isinstance(r, dict) and "state" in r:
            ctx.render_monitor(r)
        else:
            for v in r.values():
                ctx.render_monitor(v)
        if verbose:
            ctx.pp(r, verbose)
