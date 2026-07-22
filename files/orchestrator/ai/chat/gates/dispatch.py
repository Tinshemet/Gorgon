"""
dispatch.py — _process_tool_call: drive one model tool call through every gate.

The hub of the interactive turn: runs a single tool_call dict through custom-mode
detection, the context assistant, os_type resolution, pre-flight, the safety
confirmation, the manual-config prompt, execution, output rendering, and clarify
draining — appending the tool-result message along the way.
"""

import json
from typing import List

from shared.display import console
from orchestrator.executor_client import execute_tool

from ...active_library import LIBRARY
from ..chat_types import (
    TurnState, GateOutcome, _maybe_enable_custom_mode, _resolve_os_type,
    _build_pre_gate_result,
)
from .config import _RECENT_CONTEXT_WINDOW, _RENDERS_OUTPUT
from .debug import _render_debug_panel
from .context import _context_assistant_gate
from .preflight import _preflight_gate
from .safety import _safety_gate
from .manual_config import _manual_config_gate, _clarify_drain


def _process_tool_call(tc: dict, user_input: str, ui: str, state: "TurnState",
                       messages: List[dict], verbose: bool) -> "GateOutcome":
    """Run one model tool call through every gate, then execute it.

    Drives a single tool_call dict through custom-mode detection, the context
    assistant, os_type resolution, pre-flight, the safety confirmation, the
    manual-config prompt, execution, output rendering, and clarify draining —
    appending the tool-result message to ``messages`` along the way.

    Returns a GateOutcome the caller acts on:
        PROCEED            → move to the next tool call in this round
        EXIT               → user asked to quit; caller returns from chat_loop
        REPLAN / CANCELLED → stop this round; caller breaks the tool loop and
                             lets the post-round logic (op_cancelled / clarify /
                             context-assistant) run

    Example::

        out = _process_tool_call(tc, "make a vm", "make a vm", state, msgs, False)
        if out is GateOutcome.EXIT:   return
        if out is not GateOutcome.PROCEED:  break
    """
    fn        = tc.get("function", {})
    tool_name = fn.get("name", "")
    raw_args  = fn.get("arguments", {})
    if isinstance(raw_args, str):
        try:
            raw_args = json.loads(raw_args)
        except Exception:
            raw_args = {}

    if verbose:
        console.print(
            f"  [tool]→ {tool_name}[/tool]  [dim]{json.dumps(raw_args)}[/dim]"
        )
        _render_debug_panel(tool_name, raw_args)

    # ── Custom mode: "custom" in prompt disables HTTP check for profiles ──
    _maybe_enable_custom_mode(tool_name, ui, messages)

    # ── Context assistant ──────────────────────────────────────
    # Only runs once per user turn — if it already fired and the
    # AI still chose a bad tool, let the downstream layers handle it.
    #
    # _recent_context: last 6 real user messages joined into one
    # string. Used by the context assistant and the pre-gate so
    # multi-turn flows ("delete test1" → "yes") don't lose the
    # entity name when only the confirmation arrives as user_input.
    _recent_user_msgs = [
        m.get("content", "").lower() for m in messages
        if m.get("role") == "user"
        and not str(m.get("content", "")).startswith("_INTERNAL_")
    ]
    _recent_context = " ".join(_recent_user_msgs[-_RECENT_CONTEXT_WINDOW:])
    raw_args, _ca_out = _context_assistant_gate(
        tool_name, raw_args, user_input, _recent_context, state, messages)
    if _ca_out is GateOutcome.EXIT:
        return GateOutcome.EXIT
    if _ca_out is GateOutcome.REPLAN:
        return GateOutcome.REPLAN

    # ── os_type guard ──────────────────────────────────────────
    raw_args = _resolve_os_type(tool_name, raw_args, ui, state)

    # ── Pre-flight check ───────────────────────────────────────
    raw_args, _pf_out = _preflight_gate(tool_name, raw_args, state, messages, verbose)
    if _pf_out is GateOutcome.EXIT:
        return GateOutcome.EXIT
    if _pf_out is not GateOutcome.PROCEED:   # REPLAN (abort) or CANCELLED
        return _pf_out

    # ── Safety confirmation gate ───────────────────────────────
    safety_out = _safety_gate(tool_name, raw_args, state, messages)
    if safety_out is GateOutcome.EXIT:
        return GateOutcome.EXIT
    if safety_out is GateOutcome.CANCELLED:
        return GateOutcome.CANCELLED

    # ── Pre-execution gate ─────────────────────────────────────────
    _pre_gate_result = _build_pre_gate_result(
        tool_name, raw_args, user_input, _recent_context, state
    )

    # ── Manual per-VM config prompt ────────────────────────────────
    raw_args, _pre_gate_result, _mc_out = _manual_config_gate(
        tool_name, raw_args, _pre_gate_result, state)
    if _mc_out is GateOutcome.EXIT:
        return GateOutcome.EXIT

    if _pre_gate_result:
        result = _pre_gate_result
    else:
        result = execute_tool(tool_name, raw_args, verbose)
        state.tool_executed = True
        # Keep the Active Library current: log the transaction + targeted update
        # of just the entity this tool touched (no-op for read-only tools).
        LIBRARY.apply(tool_name, raw_args, result=result)

    # Remote VNC launch — render connection panel and strip from tool result.
    if (
        not verbose
        and isinstance(result, dict)
        and result.get("success")
        and result.get("vnc_connect_cmd")
    ):
        from shared.display import render_vnc_connect
        render_vnc_connect(console, result)
        result = {
            "success": True, "name": result.get("name"), "display": "vnc",
            "rendered": True,
            "note": "VM launched via VNC. Connection panel shown to user. Do not repeat the commands.",
        }
        tool_content = json.dumps(result, default=str)

    # Tools that self-render formatted output: strip data so the AI
    # doesn't repeat the table/panel in its text response.
    elif tool_name in _RENDERS_OUTPUT and not verbose and not _pre_gate_result:
        tool_content = json.dumps(
            {"success": True, "rendered": True,
             "note": "Output already displayed to user. Do not repeat it."},
            default=str,
        )
    else:
        tool_content = json.dumps(result, default=str)

    messages.append({
        "role":    "tool",
        "content": tool_content,
    })

    if isinstance(result, dict) and result.get("clarify"):
        if _clarify_drain(result, tool_name, state, messages) is GateOutcome.EXIT:
            return GateOutcome.EXIT
        return GateOutcome.REPLAN

    return GateOutcome.PROCEED
