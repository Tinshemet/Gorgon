"""
context.py — the context-assistant gate.

Fires the context assistant once per turn and acts on its hint: a hallucinated
required field is asked of the user and patched in (PROCEED); a tool mismatch
pops the bad message and nudges the AI to re-plan (REPLAN).
"""

from typing import List, Tuple

from shared.display import console
from orchestrator.executor_client import live_vm_names, _VM_TOOLS

from ...active_library import LIBRARY
from ..context_assistant import check_context
from ..chat_types import TurnState, GateOutcome


def _context_assistant_gate(tool_name: str, raw_args: dict, user_input: str,
                            recent_context: str, state: "TurnState",
                            messages: List[dict]) -> Tuple[dict, "GateOutcome"]:
    """Fire the context assistant (once per turn) and act on its hint.

    A hallucinated required field ("never mentioned it") is asked of the user
    directly and patched into raw_args (PROCEED); a tool mismatch / high-stakes
    hint pops the bad assistant message and nudges the AI to re-plan (REPLAN).

    Returns (raw_args, outcome): EXIT (Ctrl-C), REPLAN (mismatch), or PROCEED
    (patched / no hint / already fired this turn).

    Example::

        _context_assistant_gate("delete_vm", {"name": "x"}, "show x", "", st, msgs)
        # mismatch hint → (raw_args, GateOutcome.REPLAN)
    """
    if state.context_assistant_fired:
        return raw_args, GateOutcome.PROCEED
    known_names = None
    if tool_name in _VM_TOOLS:
        # Ground truth from the Active Library (no live list_vms round-trip);
        # fall back to a live query only if the Library hasn't been built.
        known_names = LIBRARY.known_names() if LIBRARY.built else live_vm_names()
    hint = check_context(user_input, tool_name, raw_args, recent_context=recent_context,
                          known_names=known_names)
    if not hint:
        return raw_args, GateOutcome.PROCEED
    state.context_assistant_fired = True
    if "never mentioned it" in hint:
        # Hallucinated required field — ask the user directly (the model ignores
        # the hint if we just re-prompt it).
        import re as _re
        fields = _re.findall(r"You set (\w+)=", hint)
        filled = {}
        for f in fields:
            console.print(f"[yellow]?[/yellow] What {f} would you like to use?")
            try:
                ans = console.input("[bold cyan]You:[/bold cyan] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]Cancelled.[/dim]")
                return raw_args, GateOutcome.EXIT
            if ans:
                filled[f] = ans
        if filled:
            raw_args = dict(raw_args)
            raw_args.update(filled)
            messages.append({"role": "user", "content": str(filled)})
            state.clarified_fields.update(filled.keys())
            state.clarified_values.update(filled.items())
        return raw_args, GateOutcome.PROCEED   # continue with the corrected args
    # Mismatch or high-stakes — let the AI re-evaluate.
    messages.pop()
    messages.append({
        "role":    "user",
        "content": f"_INTERNAL_ {hint} Re-evaluate and call the correct tool.",
    })
    return raw_args, GateOutcome.REPLAN
