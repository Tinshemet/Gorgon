"""qemu.py — QEMU capability introspection (machine types, CPU models) + cpu classify."""
import subprocess
from typing import Optional

from .config import _ARM_CPU_PREFIXES, _X86_CPU_NAMES

_QEMU_MACHINES_CACHE: Optional[set] = None
_QEMU_CPUS_CACHE:     Optional[set] = None


def _get_qemu_machine_types(binary: str = "qemu-system-x86_64") -> set:
    """Ask the local QEMU binary what machine types it supports."""
    global _QEMU_MACHINES_CACHE
    if _QEMU_MACHINES_CACHE is not None:
        return _QEMU_MACHINES_CACHE
    try:
        result = subprocess.run([binary, "-machine", "help"], capture_output=True, text=True, timeout=_CFG["qemu_timeout"])
        machines = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts:
                machines.add(parts[0].lower().rstrip(","))
        _QEMU_MACHINES_CACHE = machines
        return machines
    except Exception:
        return set()


# Queries the local QEMU binary for all supported CPU models (result is cached).
# In: str binary → Out: set
def _get_qemu_cpu_models(binary: str = "qemu-system-x86_64") -> set:
    """Ask the local QEMU binary what CPU models it supports."""
    global _QEMU_CPUS_CACHE
    if _QEMU_CPUS_CACHE is not None:
        return _QEMU_CPUS_CACHE
    try:
        result = subprocess.run([binary, "-cpu", "help"], capture_output=True, text=True, timeout=_CFG["qemu_timeout"])
        cpus = set()
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if parts and not parts[0].startswith("-"):
                cpus.add(parts[0].lower())
        _QEMU_CPUS_CACHE = cpus
        return cpus
    except Exception:
        return set()


# Returns True if the CPU name matches known ARM prefixes.
# In: str cpu_model → Out: bool
def _is_arm_cpu(cpu_model: str) -> bool:
    """Return True if the CPU model name matches a known ARM prefix."""
    lower = cpu_model.lower()
    return any(lower.startswith(p) for p in _ARM_CPU_PREFIXES)


# Returns True if the CPU name matches known x86 names.
# In: str cpu_model → Out: bool
def _is_x86_cpu(cpu_model: str) -> bool:
    """Return True if the CPU model name matches a known x86 name."""
    lower = cpu_model.lower().replace("-", "").replace("_", "")
    return any(x86 in lower for x86 in _X86_CPU_NAMES)


# Queries DuckDuckGo to verify a hardware product is real; returns found flag and summary snippet.
# In: str manufacturer, str product → Out: dict
