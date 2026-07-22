"""
preflight.py — the pre-flight validation gate.

Runs pre-flight validation and acts on the result before execution: abort →
re-plan, auto_fix → patch args, ask_user → prompt, plus the create_profile
force-flag handling.
"""

import json
from typing import List, Tuple

from shared.display import console
from orchestrator.executor_client import API_URL
from orchestrator.preflight.validator import _preflight_check, _show_preflight_warning

from ..chat_types import TurnState, GateOutcome
from ...agent.contract import confirms_by_name

try:
    from executor.tool_dispatch.tool_executor import manager
except ImportError:
    manager = None                                                            # type: ignore[assignment]


def _preflight_gate(tool_name: str, raw_args: dict, state: "TurnState",
                    messages: List[dict], verbose: bool) -> Tuple[dict, "GateOutcome"]:
    """Run pre-flight validation and act on the result before execution.

    Returns (raw_args, outcome): EXIT (Ctrl-C), REPLAN (abort — the AI is nudged
    to re-plan), CANCELLED (ask_user declined), or PROCEED (ok / auto_fix /
    ask_user-approved). Mutates raw_args for auto_fix, an ask_user fix_field, and
    the create_profile force flag.

    Example::

        raw_args, out = _preflight_gate("create_vm", {"name": "v"}, st, msgs, False)
        # out is GateOutcome.PROCEED when preflight returns action == "ok"
    """
    pf = _preflight_check(
        tool_name, raw_args,
        manager if API_URL == "local" else None,
        verbose,
        stateless_only=(API_URL != "local"),
    )
    action = pf.get("action", "ok")

    if action == "abort":
        messages.append({
            "role":    "tool",
            "content": json.dumps({"success": False, "error": pf["reason"]}, default=str),
        })
        messages.append({
            "role":    "user",
            "content": (
                f"_INTERNAL_ {pf['reason']}. "
                f"{pf.get('correction', '')} Do not retry this operation."
            ),
        })
        return raw_args, GateOutcome.REPLAN

    if action == "auto_fix":
        raw_args = pf["fixed_args"]
        if not verbose:
            console.print(f"  [yellow]⚙  Pre-flight auto-fixed: {pf['correction']}[/yellow]")

    elif action == "ask_user" and not confirms_by_name(tool_name, raw_args):
        _show_preflight_warning(pf, console)
        fix_field = pf.get("fix_field")
        opts      = pf.get("options", [])
        try:
            pf_answer = console.input("[bold cyan]Your choice:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            return raw_args, GateOutcome.EXIT
        cancelled = (
            not pf_answer
            or (opts and pf_answer.lower() == opts[-1].lower())
            or pf_answer.lower() in ("no", "cancel", "n")
        )
        if cancelled:
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
            return raw_args, GateOutcome.CANCELLED
        if fix_field:
            raw_args = dict(raw_args)
            raw_args[fix_field] = pf_answer
            state.clarified_fields.add(fix_field)
        elif tool_name == "create_profile":
            # User approved "Save anyway" — bypass the executor's duplicate preflight.
            raw_args = dict(raw_args)
            raw_args["force"] = True

    # After the CLI handled preflight for create_profile (ok / auto_fix /
    # ask_user-approved), mark force=True so the executor skips its own preflight.
    if tool_name == "create_profile" and action in ("ok", "auto_fix"):
        raw_args = dict(raw_args)
        raw_args["force"] = True
    return raw_args, GateOutcome.PROCEED
