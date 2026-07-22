"""fleet — preview or broadcast an action across a labelled fleet of VMs."""

from typing import List

from .base import Command
from . import context as ctx


class FleetCommand(Command):
    names = ("fleet",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # fleet                       → list current fleets (labels → member VMs)
        # fleet <label>               → preview members of one fleet
        # fleet <label> exec <cmd...> → run a command on every member
        # fleet <label> stop|launch|ping|status → broadcast that action
        if not rest:
            ctx.render_fleets(ctx.manager.list_labels().get("usage", {}))
            return
        label  = rest[0]
        action = rest[1] if len(rest) > 1 else None
        if action is None:
            # Preview: show the members of this fleet (status action, read-only)
            r = ctx.manager.fleet(label, "status")
            ctx.render_fleet(r) if r.get("results") else ctx.console.print(
                f"[warn]{r.get('error', 'No members.')}[/warn]")
            return
        if action == "exec":
            if len(rest) < 3:
                ctx.console.print("[error]Usage: gorgon fleet <label> exec <command>[/error]")
                return
            r = ctx.manager.fleet(label, "exec", command=" ".join(rest[2:]))
        elif action in ("ping", "status", "stop", "launch"):
            r = ctx.manager.fleet(label, action)
        else:
            ctx.console.print(f"[error]Unknown fleet action '{action}'. "
                              f"Use: exec, ping, status, stop, launch.[/error]")
            return
        ctx.render_fleet(r)
