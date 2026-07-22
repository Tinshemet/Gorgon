"""launch — start a VM (and surface stealth guest-setup instructions)."""

from typing import List

from rich.panel import Panel

from .base import Command
from . import context as ctx


class LaunchCommand(Command):
    names = ("launch",)
    min_args = 1

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        r     = ctx.manager.launch_vm(rest[0], display=rest[1] if len(rest) > 1 else None)
        style = "success" if r.get("success") else "error"
        ctx.console.print(f"[{style}]{r.get('message', r.get('error', ''))}[/{style}]")
        if r.get("setup_cmd"):
            setup_cmd  = r["setup_cmd"]
            is_windows = setup_cmd.startswith("irm ")
            how_line   = (
                "Open [bold]PowerShell[/bold] inside the VM and run:"
                if is_windows else
                "Open a terminal inside the VM and run (then reboot):"
            )
            ctx.console.print(Panel(
                f"[bold]Stealth guest setup required.[/bold] {how_line}\n\n"
                f"[cyan]{setup_cmd}[/cyan]\n\n"
                f"[dim]When done, run:[/dim] [bold]gorgon setup-done {rest[0]}[/bold]",
                title="Stealth Setup", border_style="yellow",
            ))
            ctx._show_stealth_popup(rest[0], setup_cmd)
