"""reliability — inspect / reset the learned per-tool p_world."""

from typing import List

from rich import box
from rich.table import Table

from .base import Command
from . import context as ctx


class ReliabilityCommand(Command):
    names = ("reliability",)

    def run(self, cmd: str, rest: List[str], verbose: bool) -> None:
        # gorgon reliability [agent] — inspect the LEARNED per-tool p_world (how often
        # each primitive actually succeeds), accumulated in the durable tool-stats store.
        # Read-only; defaults to the active agent, or pass an agent key to inspect another.
        from orchestrator.ai.planner import findings_store as _store
        from orchestrator.ai.agent import contract as _contract
        from orchestrator.ai.planner.reward_cost import p_world_estimate as _pwe, cfg_with as _cfgw
        if rest and rest[0] == "reset":                # gorgon reliability reset [agent]
            agent = rest[1] if len(rest) >= 2 else _contract.active_agent_key()
            ok = _store.clear_tool_counts(agent)
            ctx.console.print(f"[success]Cleared learned tool reliability for '{agent}'.[/success]" if ok
                              else f"[dim]No reliability data to clear for '{agent}'.[/dim]")
            return
        agent  = rest[0] if rest else _contract.active_agent_key()
        cfg    = _cfgw(_contract.reward_cost_cfg())
        counts = _store.load_tool_counts(agent)
        pw     = _pwe(counts, cfg)
        if not counts:
            ctx.console.print(
                f"[yellow]No reliability data yet for agent '{agent}'.[/yellow]\n"
                f"[dim]Every tool starts at the contract default p_world = {cfg['p_world']:.2f}; "
                f"per-tool stats accumulate as autonomous missions run.[/dim]")
        else:
            t = Table(box=box.ROUNDED, border_style="cyan",
                      title=f"learned p_world — agent '{agent}'")
            t.add_column("tool", style="bold")
            t.add_column("ok",   justify="right")
            t.add_column("runs", justify="right")
            t.add_column("raw rate",        justify="right", style="dim")
            t.add_column("learned p_world", justify="right", style="bold")
            for tool in sorted(counts, key=lambda x: (-counts[x]["n"], x)):
                a   = counts[tool]
                raw = a["ok"] / a["n"] if a["n"] else 0.0
                p   = pw.get(tool, cfg["p_world"])
                col = "green" if p >= 0.75 else ("yellow" if p >= 0.5 else "red")
                t.add_row(tool, str(a["ok"]), str(a["n"]), f"{raw:.2f}", f"[{col}]{p:.3f}[/{col}]")
            ctx.console.print(t)
            ctx.console.print(
                f"[dim]Beta-smoothed toward the contract default p_world={cfg['p_world']:.2f} "
                f"(prior strength k={cfg['p_world_k']:.0f}); tools never run yet use that default.[/dim]")
        ctx.pp({"agent": agent, "counts": counts, "p_world": pw}, verbose)
