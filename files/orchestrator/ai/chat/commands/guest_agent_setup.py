"""guest-agent-setup — serve the stealth serial-agent setup script over HTTP."""

import os
from typing import List

from rich.panel import Panel

from .base import Command
from . import context as ctx


class GuestAgentSetupCommand(Command):
    names = ("guest-agent-setup",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        vm_name = rest[0]
        r = ctx.manager.generate_guest_agent_setup(vm_name)
        if not r.get("success"):
            ctx.console.print(f"[error]{r['error']}[/error]")
            return

        script_path = r["path"]
        srv, port   = ctx.serve_dir_once(os.path.dirname(script_path))
        url         = r["cmd_template"].format(port=port)

        ctx.console.print(Panel(
            f"[bold]Script:[/bold] {script_path}\n\n"
            f"[bold]Inside the VM, run:[/bold]\n"
            f"[cyan]{url}[/cyan]\n\n"
            f"[dim]Server will exit when you press Ctrl+C.[/dim]",
            title=f"Guest Agent Setup — {vm_name}",
            border_style="green",
        ))
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            srv.shutdown()
            ctx.console.print("[dim]Server stopped.[/dim]")
