"""
tool_executor.py — Executor-side tool dispatch (facade).

The tool handlers now live one-per-file under tool_dispatch/tools/ (auto-registered;
the dispatcher is tools/__init__.py's run()). The QemuManager singleton, the
parsed config, and the revert-tracking state live in context.py. The complex
create_vm build is in create_vm.py.

This module re-exports the stable public surface external callers import
(manager, _VM_DEFS, _run, dispatch_tool, _set_revert / _clear_revert,
_last_revert_action) so orchestrator.pipeline, executor.server, and the tests
are unaffected by the split. There are no orchestrator imports here.
"""

from executor.tool_dispatch.context import (
    manager,
    _VM_DEFS, _TOOL_DEFS, _REVERT_AWARE_TOOLS,
    _last_revert_action, _set_revert, _clear_revert,
)
from executor.tool_dispatch.tools import run as _run, dispatch_tool
