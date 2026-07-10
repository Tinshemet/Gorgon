"""
profiles.py — Hardware profile management.

Built-in + custom hardware profiles: load/save/delete on disk, merge, apply a
profile's fields onto a MachineConfig, list them, and check a profile against
the host. Split out of qemu_config.py, which re-exports these names so its many
importers are unchanged. Imports qemu_config only lazily (inside
check_profile_compatibility), so the edge is one-directional (qemu_config ->
profiles) with no import cycle at load time.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_CFG  = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))
_MC   = _CFG["machine_config_defaults"]
_DIRS = _CFG["dirs"]
PROFILES_DIR = os.path.expanduser(_DIRS["profiles"])

# ─────────────────────────────────────────────
#  BUILT-IN HARDWARE PROFILES
# ─────────────────────────────────────────────

HARDWARE_PROFILES: Dict[str, Dict[str, Any]] = _CFG["hardware_profiles"]


# Reads all .json files from ~/.qemu_vms/_profiles/ into a dict.
# In: nothing → Out: dict
def _load_custom_profiles() -> Dict[str, Dict[str, Any]]:
    """Load all user-saved hardware profiles from disk."""
    profiles = {}
    if not os.path.isdir(PROFILES_DIR):
        return profiles
    for fname in os.listdir(PROFILES_DIR):
        if fname.endswith(".json"):
            key = fname[:-5]
            try:
                with open(os.path.join(PROFILES_DIR, fname)) as f:
                    profiles[key] = json.load(f)
            except Exception:
                pass  # one malformed profile file shouldn't block loading the rest — skip it
    return profiles


# Sanitizes the name and writes a custom profile JSON to _profiles/.
# In: str name, dict profile_data → Out: dict with success and path
def save_custom_profile(name: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save a custom hardware profile to disk."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    # Sanitise name
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    profile_data["_custom"] = True
    profile_data["_name"]   = safe_name
    with open(path, "w") as f:
        json.dump(profile_data, f, indent=2)
    return {"success": True, "profile_name": safe_name, "path": path}


# Deletes a custom profile JSON file by name.
# In: str name → Out: dict with success
def delete_custom_profile(name: str) -> Dict[str, Any]:
    """Delete a user-saved profile by name; return a result dict."""
    safe_name = name.lower().replace(" ", "_").replace("-", "_")
    path = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    if not os.path.exists(path):
        return {"success": False, "error": f"Profile '{safe_name}' not found."}
    os.remove(path)
    return {"success": True, "message": f"Profile '{safe_name}' deleted."}


# Merges built-in HARDWARE_PROFILES with any saved custom profiles.
# In: nothing → Out: dict
def get_all_profiles() -> Dict[str, Dict[str, Any]]:
    """Return built-in + custom profiles merged into a single dict.

    Returns:
        Mapping of profile name → profile data dict. Custom profiles from
        disk override built-in profiles with the same name.

    Example::

        profiles = get_all_profiles()
        profiles.keys()
        # → dict_keys(["dell_g15_5520", "lenovo_thinkpad_x1", ..., "my_custom"])
    """
    all_profiles = dict(HARDWARE_PROFILES)
    all_profiles.update(_load_custom_profiles())
    return all_profiles


# Copies all matching profile fields onto a MachineConfig.
# In: MachineConfig, str profile_name → Out: MachineConfig
def apply_profile(config: MachineConfig, profile_name: str) -> MachineConfig:
    """Apply a named hardware profile's fields onto ``config``."""
    all_profiles = get_all_profiles()
    profile = all_profiles.get(profile_name)
    if not profile:
        raise ValueError(
            f"Unknown profile '{profile_name}'. "
            f"Available: {list(all_profiles.keys())}"
        )
    skip_keys = {"_custom", "_name", "_requires", "_notes"}
    for key, value in profile.items():
        if key in skip_keys:
            continue
        if hasattr(config, key):
            setattr(config, key, value)
    return config


# Returns a flat list of all profiles with name, description, arch, and custom flag.
# In: nothing → Out: List[dict]
def list_profiles() -> List[Dict[str, str]]:
    """Return the available hardware profiles as summary dicts."""
    all_profiles = get_all_profiles()
    result = []
    for k, v in all_profiles.items():
        entry = {
            "name":        k,
            "description": v.get("description", ""),
            "arch":        v.get("machine_arch", "x86_64"),
            "custom":      str(v.get("_custom", False)),
        }
        if "_notes" in v:
            entry["notes"] = v["_notes"]
        result.append(entry)
    return result


# Compares a profile's requirements against the host (KVM, RAM, cores, OVMF, arch).
# In: str profile_name → Out: dict with compatible, issues, warnings
def check_profile_compatibility(profile_name: str) -> Dict[str, Any]:
    """
    Check whether a given profile can run on this host system.
    Returns compatibility status, issues found, and alternatives.
    """
    from .qemu_config import check_system_capabilities, OVMF  # lazy: avoid load-time cycle
    _THRESHOLDS = _CFG["compatibility_thresholds"]

    all_profiles = get_all_profiles()
    profile      = all_profiles.get(profile_name)
    caps         = check_system_capabilities()

    if not profile:
        return {"compatible": False, "error": f"Profile '{profile_name}' not found."}

    issues       = []
    warnings     = []
    alternatives = []

    # KVM check
    if profile.get("kvm", True) and not caps["kvm_available"]:
        issues.append("KVM not available — VM will be very slow (software emulation only). Enable VT-x/AMD-V in BIOS.")

    # Architecture check
    arch = profile.get("machine_arch", "x86_64")
    if arch == "aarch64" and not caps["qemu_arm_installed"]:
        issues.append("qemu-system-aarch64 not installed. Run: sudo apt install qemu-system-arm")
        alternatives.append(
            "raspberry_pi_4 requires qemu-system-aarch64."
            " Install it or use a minimal x86 Linux VM instead."
        )

    if arch == "aarch64" and caps["host_arch"] == "x86_64":
        warnings.append(
            "ARM emulation on x86 host — no KVM acceleration possible. "
            "Expect 10-50x slower than native Pi hardware."
        )

    # OVMF check
    if profile.get("uefi") and not OVMF["available"]:
        if profile.get("bios") != "seabios":
            issues.append(
                f"UEFI requested but OVMF not found. "
                f"Run: sudo apt install ovmf — or the system will fall back to SeaBIOS automatically."
            )

    # Memory check
    requested_mb = int(profile.get("memory_mb", 2048))
    host_mb      = caps.get("host_memory_mb", 0)
    if host_mb > 0 and requested_mb > host_mb * _THRESHOLDS["memory_ratio"]:
        warnings.append(
            f"Profile requests {requested_mb}MB RAM but host only has {host_mb}MB. "
            f"Consider reducing memory_mb to {host_mb // 2}MB."
        )

    # CPU core check
    requested_cores = int(profile.get("cpu_cores", 2))
    host_cores      = caps.get("host_cpu_cores", 1)
    if requested_cores > host_cores:
        warnings.append(
            f"Profile requests {requested_cores} cores but host only has {host_cores}. "
            f"QEMU will over-commit — may cause slowdowns."
        )

    # Disk space check
    free_gb = caps.get("home_free_gb", 0)
    if free_gb < _THRESHOLDS["min_disk_free_gb"]:
        warnings.append(f"Low disk space: only {free_gb}GB free in home directory.")

    compatible = len(issues) == 0
    return {
        "profile":    profile_name,
        "compatible": compatible,
        "issues":     issues,
        "warnings":   warnings,
        "alternatives": alternatives,
        "host_summary": {
            "cpu":       caps.get("host_cpu", "unknown"),
            "cores":     caps.get("host_cpu_cores"),
            "memory_mb": caps.get("host_memory_mb"),
            "kvm":       caps.get("kvm_available"),
            "ovmf":      OVMF["available"],
            "qemu_arm":  caps.get("qemu_arm_installed"),
            "arch":      caps.get("host_arch"),
        },
        "notes": profile.get("_notes", ""),
    }


# Injects OS-specific CPU features: Hyper-V flags for Windows, KVM PV for Linux, vendor tweak for macOS.
# In: MachineConfig → Out: MachineConfig
def apply_os_hints(config: MachineConfig) -> MachineConfig:
    """Adjust config defaults based on the guest OS type."""
    os_type = config.os_type.lower()
    _os_cpu = _CFG.get("os_cpu_features", {})
    if "windows" in os_type or os_type == "windows":
        config.cpu_features += _os_cpu.get("windows", [])
        config.hpet = False
        if config.rtc_clock == _MC["rtc_clock"]:
            config.rtc_clock = "localtime"
        config.tsc_deadline = True
    elif "linux" in os_type:
        config.kvm_pv_features = True
    elif "macos" in os_type:
        config.cpu_features += _os_cpu.get("macos", [])
        config.machine_type = "q35"
    return config

