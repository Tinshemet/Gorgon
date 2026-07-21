"""
tool_dispatch/tools — the executor's tool handlers, one class per file.

The dispatcher run() routes a pre-validated tool call to its Tool handler. It is
called two ways (unchanged from before the split):
  * dispatch_tool()             — the executor server path (stub callables)
  * orchestrator.pipeline       — the local-mode path (real callables)

Adding a tool: drop a module here with a Tool subclass (set `names`, implement
run(args, ctx)). It's auto-discovered — no edit to this file.
"""

import importlib
import pkgutil
from typing import Any, Dict

from executor.tool_dispatch.context import _REVERT_AWARE_TOOLS, _clear_revert
from executor.tool_dispatch.tools.base import ALL_TOOLS, ToolCtx

# Import every tool module so each Tool subclass registers itself.
for _mod in pkgutil.iter_modules(__path__):
    if _mod.name != "base":
        importlib.import_module(f"{__name__}.{_mod.name}")

# tool name -> handler instance. Duplicate names are a programming error.
_REGISTRY = {}
for _cls in ALL_TOOLS:
    _instance = _cls()
    for _name in _cls.names:
        if _name in _REGISTRY:
            raise RuntimeError(f"duplicate executor tool name: {_name!r}")
        _REGISTRY[_name] = _instance


# Stubs for the executor-only path (no orchestrator pipeline).
_STUB_PLACEHOLDER_VM_NAMES = frozenset()


def _resolve_iso_stub(p: str) -> str:
    """Identity ISO resolver used in executor-only mode (no orchestrator)."""
    return p


def _preflight_check_stub(*a, **k) -> dict:
    """No-op preflight stub — the orchestrator already validated the args."""
    return {"action": "ok"}


def _show_preflight_warning_stub(*a, **k) -> None:
    """No-op preflight-warning stub for executor-only dispatch."""
    pass


def run(
    tool_name: str,
    args: Dict[str, Any],
    verbose: bool,
    *,
    raw_os_type: str = "",
    placeholder_vm_names=None,
    resolve_iso=None,
    preflight_check=None,
    show_preflight_warning=None,
) -> Any:
    """Dispatch a pre-pipeline tool call to its Tool handler.

    Called by dispatch_tool (executor path, with stubs) and by
    orchestrator.pipeline.execute_tool (local-mode path, with real implementations).
    All orchestrator-side concerns (sanitize, gate, name resolution) must be
    completed before calling this function.
    """
    if placeholder_vm_names is None:
        placeholder_vm_names = _STUB_PLACEHOLDER_VM_NAMES
    if resolve_iso is None:
        resolve_iso = _resolve_iso_stub
    if preflight_check is None:
        preflight_check = _preflight_check_stub
    if show_preflight_warning is None:
        show_preflight_warning = _show_preflight_warning_stub

    # A revert action is only meaningful immediately after the call that set it —
    # any unrelated tool call in between means "undo my last action" would target
    # something the caller probably isn't thinking about anymore, so drop it.
    # Tools that manage the state themselves are exempted.
    if tool_name not in _REVERT_AWARE_TOOLS:
        _clear_revert()

    def _redispatch(t, a):
        return run(
            t, a, verbose,
            raw_os_type=a.get("os_type", ""),
            placeholder_vm_names=placeholder_vm_names,
            resolve_iso=resolve_iso,
            preflight_check=preflight_check,
            show_preflight_warning=show_preflight_warning,
        )

    ctx = ToolCtx(
        verbose=verbose, raw_os_type=raw_os_type,
        placeholder_vm_names=placeholder_vm_names, resolve_iso=resolve_iso,
        preflight_check=preflight_check, show_preflight_warning=show_preflight_warning,
        redispatch=_redispatch,
    )

    tool = _REGISTRY.get(tool_name)
    if tool is None:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    return tool.run(args, ctx)


def dispatch_tool(tool_name: str, args: Dict[str, Any], verbose: bool = False) -> Any:
    """Execute a pre-validated tool call — no orchestrator pipeline.

    Entry point for the remote executor server. The orchestrator has already run
    sanitizer, context gate, and preflight; args are clean and VM names resolved.

    Example::
        >>> dispatch_tool("list_vms", {})
        [{"name": "my-linux", "status": "stopped", ...}]
    """
    return run(
        tool_name, args, verbose,
        raw_os_type=args.get("os_type", ""),
        placeholder_vm_names=_STUB_PLACEHOLDER_VM_NAMES,
        resolve_iso=_resolve_iso_stub,
        preflight_check=_preflight_check_stub,
        show_preflight_warning=_show_preflight_warning_stub,
    )
