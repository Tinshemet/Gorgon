"""
debug.py — the verbose per-call debug panel.

Renders, for ONE tool call, the weighted risk-score breakdown and the active
reward-cost knobs — surfacing WHY a call is gated the way it is. Verbose-only.
"""

from shared.display import console


def _render_debug_panel(tool_name: str, raw_args: dict) -> None:
    """Verbose/debug view for ONE tool call: the weighted risk-score breakdown (which
    factors × contract weights produced the scrutiny tier + gate action) and the active
    reward-cost knobs (α, λ, θ, …). Surfaces WHY a call is gated the way it is. Best-
    effort — a contract without an assessment for this tool just shows 'not assessed'."""
    from rich.table import Table
    from rich import box as _box
    try:
        from ...agent import contract as _contract
        bd = _contract.risk_breakdown(tool_name, raw_args)
        rc = {**_reward_cost_defaults(), **_contract.reward_cost_cfg()}
    except Exception as e:
        console.print(f"  [dim]debug: unavailable ({e})[/dim]")
        return

    t = Table(box=_box.SIMPLE, show_header=True, header_style="dim", pad_edge=False)
    t.add_column("risk factor"); t.add_column("value", justify="right")
    t.add_column("× weight", justify="right"); t.add_column("= contrib", justify="right")
    for f in bd["factors"]:
        lbl = f["name"] + (f"  ({bd['blast_label']})" if f["name"] == "blast" else "")
        t.add_row(lbl, f"{f['value']:.2f}", f"{f['weight']:.2f}", f"{f['contribution']:.3f}")
    console.print(t)
    if not bd["assessed"]:
        console.print(f"  [dim](contract did not assess {tool_name} → tier none)[/dim]")
    console.print(
        f"  [bold]score[/bold] {bd['score']:.3f}  →  formula tier [bold]{bd['formula_tier']}[/bold]"
        f"  |  resolved [bold]{bd['resolved_tier']}[/bold]  |  gate action [bold cyan]{bd['action']}[/bold cyan]")
    console.print(
        "  [dim]reward-cost:[/dim] "
        f"α={rc.get('alpha', 0):.2f}  λ={rc.get('lambda', 0):.2f}  θ={rc.get('theta', 0):.2f}  "
        f"H={rc.get('H', 0):.2f}  p_world={rc.get('p_world', 0):.2f}  k={rc.get('p_world_k', 0):.0f}")


def _reward_cost_defaults() -> dict:
    """The reward-cost DEFAULTS, so the debug panel shows a full knob set even when the
    contract only overrides a few."""
    from ...planner.reward_cost import DEFAULTS
    return dict(DEFAULTS)
