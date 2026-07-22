"""system — show host virtualization capabilities."""

from typing import List

from .base import Command
from . import context as ctx


class SystemCommand(Command):
    names = ("system",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        caps = ctx.check_system_capabilities()
        caps["ovmf_paths"] = ctx._get_ovmf()
        ctx.render_system(caps)
