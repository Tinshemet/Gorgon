"""setup-done — mark a stealth VM's one-time guest setup complete."""

from typing import List

from .base import Command
from . import context as ctx


class SetupDoneCommand(Command):
    names = ("setup-done",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.mark_stealth_done(rest[0])
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
