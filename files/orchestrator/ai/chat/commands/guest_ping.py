"""guest-ping — check whether a VM's guest agent is responding."""

from typing import List

from .base import Command
from . import context as ctx


class GuestPingCommand(Command):
    names = ("guest-ping",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.guest_ping(rest[0])
        if not r.get("success"):
            ctx.console.print(f"[error]{r.get('error', 'unknown error')}[/error]")
        else:
            style = "success" if r.get("alive") else "warn"
            state = "alive" if r.get("alive") else "not responding"
            ctx.console.print(f"[{style}]{rest[0]}: guest agent {state}[/{style}]")
