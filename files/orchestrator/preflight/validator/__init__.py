"""
validator — the pre-flight gate: validate a tool call against host reality before it
runs (catch the failure at the door, with a fixable message, instead of a QEMU crash).

Each tool's validation is a PreflightCheck subclass (base.py), auto-registered by the
tool name(s) it handles; ``_preflight_check`` routes a call to its check. Adding a
validation is one file. This facade also re-exports the host_probe symbols validator
has always carried, so callers keep importing from ``orchestrator.preflight.validator``.

  - context.py     shared config + constants + host_probe/sanitizer helpers + _triage
  - stealth.py     the stealth-VM SMBIOS/GPU/firmware/CPU checks
  - create_vm.py   the heavy create_vm pre-flight + CreateVMCheck
  - checks.py      the lighter per-tool checks (profile/launch/delete/resize/…)
  - render.py      the warning panel
"""

import importlib
import pkgutil
from typing import Any, Dict

from .base import ALL_CHECKS
from .context import (
    _PREFLIGHT_TOOLS, _triage, set_custom_mode, _validate_profile_for_host,
    _validate_with_internet, _stealth_infer_from_product, _get_qemu_machine_types,
    _get_qemu_cpu_models, _is_arm_cpu, _is_x86_cpu, _net_get, _net_head,
)
from .stealth import _validate_stealth_args
from .create_vm import _preflight_create_vm
from .render import _show_preflight_warning

# Import every check module so its PreflightCheck subclasses register.
for _mod in pkgutil.iter_modules(__path__):
    if _mod.name not in ("base", "context", "stealth", "render"):
        importlib.import_module(f"{__name__}.{_mod.name}")

# tool name → check instance (a duplicate registration is a loud error).
_REGISTRY: Dict[str, Any] = {}
for _cls in ALL_CHECKS:
    _inst = _cls()
    for _t in _cls.tools:
        if _t in _REGISTRY:
            raise RuntimeError(f"duplicate pre-flight check for tool: {_t!r}")
        _REGISTRY[_t] = _inst


def _preflight_check(tool_name: str, args: Dict[str, Any], manager: object,
                     verbose: bool = False, stateless_only: bool = False) -> Dict[str, Any]:
    """Validate a tool call before execution → {"action": "ok"|"auto_fix"|"ask_user"|
    "abort", …}. ``stateless_only`` (the AI provider in remote mode) skips checks that
    need real filesystem/binary/manager state; the client machine runs the full check."""
    ok = {"action": "ok"}
    if tool_name not in _PREFLIGHT_TOOLS:
        return ok
    check = _REGISTRY.get(tool_name)
    if check is None:
        return ok
    result = check.check(tool_name, args, manager, verbose, stateless_only)
    return result if result is not None else ok
