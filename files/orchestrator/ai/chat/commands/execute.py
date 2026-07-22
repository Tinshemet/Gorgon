"""execute — run a shell command inside a VM via its guest agent."""

from typing import List

from .base import Command
from . import context as ctx


class ExecuteCommand(Command):
    names = ("execute",)
    min_args = 2

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.run_guest_command(rest[0], " ".join(rest[1:]))
        if not r.get("success"):
            ctx.console.print(f"[error]{r.get('error', 'unknown error')}[/error]")
            return
        if r.get("stdout"):
            ctx.console.print(r["stdout"], end="" if r["stdout"].endswith("\n") else "\n")
        if r.get("stderr"):
            ctx.console.print(f"[error]{r['stderr']}[/error]", end="")
        ctx.console.print(f"[dim]exit code: {r.get('exit_code')}[/dim]")
