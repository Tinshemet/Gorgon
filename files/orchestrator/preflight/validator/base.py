"""
base.py — the PreflightCheck base class + auto-registration.

One PreflightCheck subclass per tool (or tool-group): set ``tools`` (the tool names
it validates) and implement ``check(tool_name, args, manager, verbose,
stateless_only)`` → an action dict ({"action": "ok"|"auto_fix"|"ask_user"|"abort", …})
or None (= ok). Declaring a subclass with a non-empty ``tools`` registers it; the
dispatcher (__init__) routes a tool call to its check. Adding a validation is a file.
"""

from typing import Any, Dict, List, Optional

# Every concrete PreflightCheck subclass appends itself here at class-definition time.
ALL_CHECKS: list = []


class PreflightCheck:
    """A pre-flight validator for one or more tools."""

    tools: tuple = ()      # the tool name(s) this check handles ("" = abstract)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.tools:
            ALL_CHECKS.append(cls)

    def check(self, tool_name: str, args: Dict[str, Any], manager: object,
              verbose: bool, stateless_only: bool) -> Optional[Dict[str, Any]]:
        """Validate the call. Return an action dict, or None when there's nothing to
        flag (the dispatcher treats None as {"action": "ok"})."""
        raise NotImplementedError
