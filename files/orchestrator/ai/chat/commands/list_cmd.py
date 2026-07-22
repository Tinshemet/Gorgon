"""list — list all VMs."""

from typing import List

from .base import Command
from . import context as ctx


class ListCommand(Command):
    names = ("list",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        vms = ctx.manager.list_vms()
        ctx.render_vm_list(vms)
        if verbose:
            ctx.pp(vms, verbose)
