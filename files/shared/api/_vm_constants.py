"""
_vm_constants.py — Shared constants for QemuManager and its mixins.

Loaded once at import time from config.json in the same directory.
All mixin files import their constants from here to avoid re-parsing.
"""
import json
import os

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)

_TIMEOUTS              = _CFG["timeouts"]
_BUFFERS               = _CFG["buffers"]
_MACOS_OVMF            = _CFG["ovmf_macos_vars_paths"]
_WIN_OVMF              = _CFG["ovmf_win_vars_paths"]
_LOG_ERROR_PATTERNS    = [tuple(p) for p in _CFG["log_error_patterns"]]
_VALID_MACHINE_TYPES   = set(_CFG["valid_machine_types"])
_UPDATE_ALLOWED_FIELDS = frozenset(_CFG["update_allowed_fields"])
_MONITOR_ALLOWED_CMDS  = tuple(_CFG["monitor_allowed_cmds"])
_LINUX_DISTROS         = _CFG["linux_distros"]
_LOG_DEFAULT_LINES     = _CFG["log_default_lines"]
VM_BASE_DIR            = os.path.expanduser(_CFG["dirs"]["vm_base"])
