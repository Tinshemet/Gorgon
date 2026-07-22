"""
chat_turn.py — facade for the interactive gates and per-tool-call dispatch.

The five interactive gates (safety, pre-flight, context-assistant, manual-config,
clarify) and the dispatch hub _process_tool_call() now live in the chat/gates/
subpackage (one module per gate); the gate-independent base (TurnState,
GateOutcome, the pure arg transforms) lives in chat_types.py. This module stays
as the stable import surface for cli.py / http_chat / the tests / the
chat_harness module-reload — nothing else imports the gate modules directly.
"""

from .gates.dispatch import _process_tool_call
from .gates.config import _FLEET_CONFIRM_ACTIONS
from .chat_types import (  # re-exported base types + pure transforms
    TurnState, GateOutcome, _is_critical, _build_vm_spec_rows,
    _maybe_enable_custom_mode, _resolve_os_type, _build_pre_gate_result,
)

__all__ = [
    "_process_tool_call", "_FLEET_CONFIRM_ACTIONS",
    "TurnState", "GateOutcome", "_is_critical", "_build_vm_spec_rows",
    "_maybe_enable_custom_mode", "_resolve_os_type", "_build_pre_gate_result",
]
