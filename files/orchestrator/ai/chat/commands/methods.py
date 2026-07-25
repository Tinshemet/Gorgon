"""methods — inspect / forget the decompositions the agent has LEARNED."""

from typing import List

from rich import box
from rich.table import Table

from .base import Command
from . import context as ctx


class MethodsCommand(Command):
    names = ("methods",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # gorgon methods [agent] — the durable method cache: goal shapes this agent can
        # now decompose WITHOUT asking the model, learned from decompositions that
        # actually closed. Read-only; defaults to the active agent.
        from orchestrator.ai.planner import method_store as _store
        from orchestrator.ai.agent import contract as _contract
        if rest and rest[0] == "forget":               # gorgon methods forget [agent]
            agent = rest[1] if len(rest) >= 2 else _contract.active_agent_key()
            ok = _store.clear(agent)
            ctx.console.print(f"[success]Forgot the learned decompositions for '{agent}'.[/success]" if ok
                              else f"[dim]No learned decompositions to forget for '{agent}'.[/dim]")
            return
        agent   = rest[0] if rest else _contract.active_agent_key()
        records = _store.load(agent)
        if not records:
            ctx.console.print(
                f"[yellow]Agent '{agent}' has not learned any decompositions yet.[/yellow]\n"
                f"[dim]A method is learned when the model decomposes a novel goal AND that "
                f"plan closes done; it is then reused deterministically, with no model call.[/dim]")
        else:
            t = Table(box=box.ROUNDED, border_style="cyan",
                      title=f"learned decompositions — agent '{agent}'")
            t.add_column("learned from", style="bold", overflow="fold")
            t.add_column("steps", justify="right")
            t.add_column("decomposes into", style="dim", overflow="fold")
            for r in records:
                steps = r.get("steps") or []
                t.add_row(r.get("source") or r.get("name", "?"), str(len(steps)), " → ".join(steps))
            ctx.console.print(t)
            ctx.console.print(
                f"[dim]{len(records)} method(s), most recent first — a match decomposes "
                f"deterministically (no model call, no variance). "
                f"`gorgon methods forget {agent}` clears them.[/dim]")
        ctx.pp({"agent": agent, "methods": records}, verbose)
