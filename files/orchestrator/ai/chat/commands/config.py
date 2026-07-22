"""config — show a VM's stored configuration."""

import json
from typing import List

from .base import Command
from . import context as ctx


class ConfigCommand(Command):
    names = ("config",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.show_config(rest[0])
        if r.get("success"):
            ctx.console.print_json(json.dumps(r["config"], default=str))
        else:
            ctx.console.print(f"[error]{r['error']}[/error]")
