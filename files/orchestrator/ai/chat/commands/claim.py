"""claim — review the per-agent CLAIM store (list / confirm / reject)."""

from typing import List

from rich import box
from rich.table import Table

from .base import Command
from . import context as ctx


class ClaimCommand(Command):
    names = ("claim",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # gorgon claim [list] | confirm <fact> | reject <fact> — review the per-agent
        # CLAIM store: unverifiable facts a run parked as `pending` for a human to judge.
        # confirm → the fact becomes USABLE (loaded into the next run); reject → dropped.
        from orchestrator.ai.planner import findings_store as _store
        from orchestrator.ai.agent import contract as _contract
        agent = _contract.active_agent_key()
        sub   = rest[0] if rest else "list"
        if sub == "confirm" and len(rest) >= 2:
            ok = _store.confirm(agent, rest[1])
            ctx.console.print(f"[success]Confirmed '{rest[1]}' → verified.[/success]" if ok
                              else f"[error]'{rest[1]}' is not a pending claim.[/error]")
        elif sub == "reject" and len(rest) >= 2:
            ok = _store.reject(agent, rest[1])
            ctx.console.print(f"[success]Rejected '{rest[1]}' — dropped.[/success]" if ok
                              else f"[error]'{rest[1]}' not found in the store.[/error]")
        elif sub == "list":
            lst = _store.listing(agent)
            if not (lst["pending"] or lst["verified"]):
                ctx.console.print(f"[dim]No claims for agent '{agent}'.[/dim]")
            else:
                t = Table(box=box.ROUNDED, border_style="cyan", title=f"claims — agent '{agent}'")
                t.add_column("status"); t.add_column("fact", style="bold")
                t.add_column("value"); t.add_column("evidence", style="dim")
                for e in lst["pending"]:
                    t.add_row("[yellow]pending[/yellow]", e["fact"], str(e.get("value") or ""), str(e.get("evidence") or ""))
                for e in lst["verified"]:
                    t.add_row("[green]verified[/green]", e["fact"], str(e.get("value") or ""), str(e.get("evidence") or ""))
                ctx.console.print(t)
                ctx.console.print("[dim]gorgon claim confirm <fact> | reject <fact>[/dim]")
        else:
            ctx.console.print("[yellow]Usage: gorgon claim \\[list] | confirm <fact> | reject <fact>[/yellow]")
