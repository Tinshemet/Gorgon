"""limit — set CPU/memory resource limits on a VM."""

import json
from typing import List

from .base import Command
from . import context as ctx


class LimitCommand(Command):
    names = ("limit",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        cpu = int(rest[1]) if len(rest) > 1 else None
        mem = int(rest[2]) if len(rest) > 2 else None
        r   = ctx.manager.set_resource_limits(rest[0], cpu_percent=cpu, memory_mb=mem)
        ctx.console.print_json(json.dumps(r, default=str))
