"""network — list/create/delete networks, attach a VM to one."""

import json
from typing import List

from .base import Command
from . import context as ctx


class NetworkCommand(Command):
    names = ("network",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        sub = rest[0]
        if sub == "list":
            ctx.console.print_json(json.dumps(ctx.manager.list_networks(), default=str))
        elif sub == "create" and len(rest) >= 2:
            ctx.console.print_json(json.dumps(ctx.manager.create_network(rest[1]), default=str))
        elif sub == "delete" and len(rest) >= 2:
            ctx.console.print_json(json.dumps(ctx.manager.delete_network(rest[1]), default=str))
        elif sub == "add" and len(rest) >= 3:
            ctx.console.print_json(json.dumps(ctx.manager.add_vm_to_network(rest[1], rest[2]), default=str))
