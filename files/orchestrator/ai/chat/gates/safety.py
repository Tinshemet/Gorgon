"""
safety.py — the interactive safety confirmation gate (+ fleet y/n).

Human confirmation before a mutating tool runs: delete_vm double-confirms,
reversible tools confirm once (batched per turn), name-confirm tools require an
exact match. Fleet exec/stop get their own action-conditional y/n.
"""

import json
from typing import List

from shared.display import console, render_vm_specs

from ..chat_types import TurnState, GateOutcome, _build_vm_spec_rows
from ...agent.contract import gate_action, confirm_meta
from .config import _FLEET_CONFIRM_ACTIONS


def _fleet_confirm(raw_args: dict, state: "TurnState", cancel) -> GateOutcome:
    """y/n confirm for the high-stakes fleet actions (exec + stop).

    ``exec`` runs a command on every member and ``stop`` halts the whole group,
    so both warrant an explicit confirm; ``ping``/``status``/``launch`` pass
    straight through. Confirmed once per (action, label, command) within a turn,
    matching the batch-skip behavior of the y/n gate.

    Returns EXIT (Ctrl-C/EOF), CANCELLED (declined), or PROCEED.
    """
    action = (raw_args.get("action") or "").strip().lower()
    if action not in _FLEET_CONFIRM_ACTIONS:
        return GateOutcome.PROCEED
    label   = raw_args.get("label", "")
    command = raw_args.get("command", "")
    key = ("fleet", action, label, command)
    if key in state.confirmed_values:
        return GateOutcome.PROCEED

    if action == "exec":
        what = f"run [bold]{command or '(no command)'}[/bold] on every VM labeled [bold]{label}[/bold]"
    else:
        what = f"stop every VM labeled [bold]{label}[/bold]"
    console.print(f"\n[yellow]⚠  fleet {action}: {what}[/yellow]")
    try:
        answer = console.input("[bold cyan]Proceed? (y/n):[/bold cyan] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Cancelled.[/dim]")
        return GateOutcome.EXIT
    if answer not in ("y", "yes", "1"):
        cancel()
        return GateOutcome.CANCELLED
    state.confirmed_values.add(key)
    return GateOutcome.PROCEED


def _safety_gate(tool_name: str, raw_args: dict, state: "TurnState",
                 messages: List[dict]) -> GateOutcome:
    """Interactive safety confirmation before a mutating tool runs.

    delete_vm double-confirms (YES then the exact name); the reversible y/n tools
    confirm once (and batch within a turn); the name-confirm tools require an
    exact name match. Skipped when the value was already clarified/confirmed this
    turn.

    Returns EXIT (Ctrl-C/EOF), CANCELLED (declined — cancel messages appended and
    state.op_cancelled set), or PROCEED (confirmed or not required).

    Example::

        _safety_gate("delete_vm", {"name": "box"}, state, messages)
        # prompts YES + name; → GateOutcome.PROCEED once both match
    """
    def cancel() -> None:
        """Append the cancellation messages and mark the operation cancelled."""
        messages.append({
            "role":    "tool",
            "content": json.dumps(
                {"success": False, "error": "Operation cancelled by user."}, default=str),
        })
        messages.append({
            "role":    "user",
            "content": "_INTERNAL_ The user cancelled this operation. Ask what they would like to do instead.",
        })
        state.op_cancelled = True

    # fleet is action-conditional (exec/stop confirm; ping/status pass through);
    # its confirm UX builds the prompt from args, so it keeps its own helper.
    if tool_name == "fleet":
        return _fleet_confirm(raw_args, state, cancel)

    # The active agent's contract decides how to HANDLE this call: the risk tier
    # mapped through the agent's disposition. For the Doorman (human-confirm) the
    # actions are the human prompts below; a Conductor (autonomous) resolves tiers
    # without a human (log/checkpoint/halt) in its own harness, not here.
    action = gate_action(tool_name, raw_args)
    if action == "proceed":
        return GateOutcome.PROCEED

    meta = confirm_meta(tool_name)
    field, verb = meta if meta else ("name", tool_name)
    proposed = raw_args.get(field, "")
    if (field, proposed) in state.clarified_values or (field, proposed) in state.confirmed_values:
        return GateOutcome.PROCEED

    if action == "halt":
        # Autonomous red line reaching a human harness → block + surface it.
        console.print(f"\n[bold red]■ HALT: {verb}: {proposed} — blocked (autonomous red line).[/bold red]")
        cancel()
        return GateOutcome.CANCELLED

    if action in ("log", "checkpoint"):
        # Autonomous low/mid-risk handling has no human ceremony; the Conductor
        # harness does the logging/checkpointing. In a human harness, just proceed.
        console.print(f"  [dim]↪ {action}: {verb}: {proposed}[/dim]")
        return GateOutcome.PROCEED

    if action == "ask_double":
        # YES → then the exact name (irreversible + destructive).
        console.print(f"\n[bold red]⚠  {verb}: [bold]{proposed}[/bold] — this will also delete its disk(s)[/bold red]")
        console.print("[dim]Type YES to proceed, or press Enter to cancel.[/dim]")
        try:
            step1 = console.input("[bold red]Confirm (YES):[/bold red] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return GateOutcome.EXIT
        if step1.upper() != "YES":
            cancel()
            return GateOutcome.CANCELLED
        console.print(f"[dim]Type the name [bold]{proposed}[/bold] to confirm.[/dim]")
        try:
            step2 = console.input("[bold red]Confirm name:[/bold red] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return GateOutcome.EXIT
        if step2 != proposed:
            console.print("[dim]Name did not match. Cancelled.[/dim]")
            cancel()
            return GateOutcome.CANCELLED

    elif action == "notify":
        # Run it, but surface a catchable heads-up — non-blocking by design.
        hint = f"[bold]{proposed}[/bold]" if proposed else ""
        console.print(f"  [dim]↪ {verb}: {hint}[/dim]")

    elif action == "ask_yn":
        # y/n confirm for reversible modify and launch/stop. Batch-skip if this
        # tool type was already confirmed earlier in the same turn.
        if tool_name in state.confirmed_tool_types:
            console.print(f"  [dim]auto-confirmed: {verb}: {proposed}[/dim]")
        else:
            if tool_name == "create_vm":
                render_vm_specs(_build_vm_spec_rows(raw_args))
            hint = f"[bold]{proposed}[/bold]" if proposed else "[dim]unknown[/dim]"
            console.print(f"\n[yellow]⚠  {verb}: {hint}[/yellow]")
            try:
                answer = console.input("[bold cyan]Proceed? (y/n):[/bold cyan] ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Cancelled.[/dim]")
                return GateOutcome.EXIT
            if answer not in ("y", "yes", "1"):
                cancel()
                return GateOutcome.CANCELLED
            state.confirmed_tool_types.add(tool_name)

    else:  # action == "ask_name"
        # Type the exact name to confirm — proof of intent for a destructive op.
        hint = f"[bold]{proposed}[/bold]" if proposed else "[dim]unknown[/dim]"
        console.print(f"\n[yellow]⚠  {verb}: {hint}[/yellow]")
        console.print(f"[dim]Type the name to confirm, or press Enter to cancel.[/dim]")
        try:
            confirmed = console.input("[bold cyan]Confirm:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return GateOutcome.EXIT
        if confirmed != proposed:
            if confirmed:
                console.print("[dim]Name did not match. Cancelled.[/dim]")
            cancel()
            return GateOutcome.CANCELLED

    state.confirmed_values.add((field, proposed))   # this exact value confirmed
    return GateOutcome.PROCEED
