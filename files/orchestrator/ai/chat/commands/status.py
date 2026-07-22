"""status — show one VM's status."""

from typing import List

from .base import Command
from . import context as ctx


class StatusCommand(Command):
    names = ("status",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.vm_status(rest[0])
        ctx.render_status(r)
        if verbose:
            ctx.pp(r, verbose)
