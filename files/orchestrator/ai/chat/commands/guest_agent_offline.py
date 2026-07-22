"""guest-agent-offline — provision the stealth serial agent without networking."""

from typing import List

from .base import Command
from . import context as ctx


class GuestAgentOfflineCommand(Command):
    names = ("guest-agent-offline",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.provision_guest_agent_offline(rest[0])
        if not r.get("success"):
            ctx.console.print(f"[error]{r.get('error', 'unknown error')}[/error]")
        else:
            ctx.console.print(f"[success]Stealth serial-agent provisioned offline on '{rest[0]}'.[/success]")
