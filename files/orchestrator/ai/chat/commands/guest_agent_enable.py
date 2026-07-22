"""guest-agent-enable — turn the guest agent on in a VM's config."""

from typing import List

from .base import Command
from . import context as ctx


class GuestAgentEnableCommand(Command):
    names = ("guest-agent-enable",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r = ctx.manager.update_config(rest[0], {"guest_agent": True})
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
