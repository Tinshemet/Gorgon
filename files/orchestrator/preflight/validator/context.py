"""
context.py — shared config, constants, and helpers for the pre-flight checks.

The per-tool PreflightCheck subclasses reference these as module attributes (config
thresholds, the tool/field sets, the host_probe + sanitizer helpers, _triage), so a
check file stays small. Config comes from preflight/config.json (one dir up).
"""

import json
import os
from typing import Any, Dict, List

from orchestrator.executor_client import (
    get_ovmf as _get_ovmf, get_capabilities as check_system_capabilities, get_all_profiles,
)
from orchestrator.sanitizer.sanitizer import PLACEHOLDER_VM_NAMES, REAL_HOME, VALID_MACHINE_TYPES, _resolve_iso
from ..host_probe import (  # host/internet probing
    set_custom_mode, _validate_profile_for_host, _validate_with_internet,
    _stealth_infer_from_product, _get_qemu_machine_types, _get_qemu_cpu_models,
    _is_arm_cpu, _is_x86_cpu, _net_get, _net_head,
)

_CFG = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")))
_THRESHOLDS = _CFG["thresholds"]

# ── Pre-flight constants ───────────────────────────────────────────────────────
_QEMU_CPU_MODELS        = set(_CFG["qemu_cpu_models"])
_LAPTOP_TYPE_KEYWORDS   = tuple(_CFG["laptop_type_keywords"])
_PREFLIGHT_TOOLS        = set(_CFG["preflight_tools"])
_PREFLIGHT_HW_FIELDS    = set(_CFG["preflight_hw_fields"])
_DESTRUCTIVE_MON_CMDS   = _CFG["destructive_monitor_cmds"]
_BAD_ISO_PATH_PATTERNS  = _CFG["bad_iso_path_patterns"]


def _triage(issues: List[Dict]) -> tuple:
    """Split an issue list into (blockers, auto_fixes, warnings).

    Args:
        issues: List of issue dicts, each with ``"severity"`` and optionally
                ``"auto_fix"`` keys.

    Returns:
        ``(blockers, auto_fixes, warnings)`` — three lists partitioned by
        severity and whether the issue can be fixed automatically.

    Example::

        blockers, fixes, warns = _triage([
            {"severity": "error",   "message": "no KVM"},
            {"severity": "warning", "auto_fix": True, "message": "low RAM"},
            {"severity": "warning", "message": "no OVMF"},
        ])
        # blockers → [{"severity": "error", ...}]
        # fixes    → [{"severity": "warning", "auto_fix": True, ...}]
        # warns    → [{"severity": "warning", "message": "no OVMF"}]
    """
    return (
        [i for i in issues if i["severity"] == "error"],
        [i for i in issues if i.get("auto_fix") and i["severity"] != "error"],
        [i for i in issues if i["severity"] == "warning" and not i.get("auto_fix")],
    )
