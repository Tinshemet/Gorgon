"""validate.py — host/internet validation of VM + profile args (the checks the
create_vm/create_profile pre-flight calls)."""
from typing import Any, Dict, List, Optional

from orchestrator.executor_client import (
    get_ovmf as _get_ovmf, get_capabilities as check_system_capabilities, get_all_profiles,
)
from .net import custom_mode, net_enabled, _net_get, _net_head
from .qemu import _get_qemu_machine_types, _get_qemu_cpu_models, _is_arm_cpu, _is_x86_cpu
from .product import _lookup_product
from .config import _THRESHOLDS, _MS_WINDOWS_ISO_PAGE, _ARM_CPU_PREFIXES


def _validate_with_internet(args: Dict[str, Any], verbose: bool = False) -> List[Dict]:
    """
    Cross-check AI-provided hardware assumptions against real-world data.
    Non-blocking — all failures are warnings, not hard errors.
    Returns list of issue dicts with severity / auto_fix / fix_field / fix_value.
    """
    issues      = []
    qemu_binary = args.get("qemu_binary", "qemu-system-x86_64")

    # 1. Machine type
    machine_type = str(args.get("machine_type", "q35")).lower().split(",")[0].strip()
    if machine_type and machine_type not in ("", "none"):
        supported = _get_qemu_machine_types(qemu_binary)
        if supported and machine_type not in supported:
            close = [m for m in supported if machine_type[:3] in m][:3]
            issues.append({
                "severity": "error",
                "message":  f"Machine type '{machine_type}' is not supported by your installed QEMU",
                "fix":      f"Supported types include: {close or list(supported)[:5]}",
                "auto_fix": False, "source": "local_qemu",
            })

    # 2. CPU model
    cpu_model = str(args.get("cpu_model", "host")).strip()
    if cpu_model and cpu_model not in ("host", "kvm64", "qemu64", "max"):
        supported_cpus = _get_qemu_cpu_models(qemu_binary)
        if supported_cpus:
            cpu_lower = cpu_model.lower()
            if cpu_lower not in supported_cpus and not _is_arm_cpu(cpu_model):
                close = [c for c in supported_cpus if cpu_lower[:4] in c][:3]
                if not close:
                    issues.append({
                        "severity":  "warning",
                        "message":   f"CPU model '{cpu_model}' not found in QEMU's cpu list",
                        "fix":       "Try: host, kvm64, or a named model. Run: qemu-system-x86_64 -cpu help",
                        "auto_fix":  True, "fix_field": "cpu_model", "fix_value": "host",
                        "source":    "local_qemu",
                    })

    # 3. CPU / arch consistency
    machine_arch = str(args.get("machine_arch", "x86_64")).lower()
    if _is_arm_cpu(cpu_model) and machine_arch == "x86_64":
        issues.append({
            "severity":  "error",
            "message":   f"CPU '{cpu_model}' is an ARM processor but VM arch is x86_64",
            "fix":       "Either use an x86 CPU model or set machine_arch=aarch64",
            "auto_fix":  True, "fix_field": "cpu_model", "fix_value": "host",
            "source":    "local_knowledge",
        })
    elif _is_x86_cpu(cpu_model) and machine_arch in ("aarch64", "arm"):
        issues.append({
            "severity":  "error",
            "message":   f"CPU '{cpu_model}' is an x86 processor but VM arch is {machine_arch}",
            "fix":       "Either use an ARM CPU model (cortex-a72) or set machine_arch=x86_64",
            "auto_fix":  True, "fix_field": "cpu_model", "fix_value": "cortex-a72",
            "source":    "local_knowledge",
        })

    # 4. Product verification via DuckDuckGo
    manufacturer = str(args.get("manufacturer", "")).strip()
    product_name = str(args.get("product_name", "")).strip()
    if manufacturer and product_name and net_enabled() and not custom_mode():
        result = _lookup_product(manufacturer, product_name)
        if result and not result.get("found"):
            issues.append({
                "severity": "warning",
                "message":  f"Could not verify '{manufacturer} {product_name}' as a real product online",
                "fix":      "Check manufacturer and product_name — SMBIOS spoofing works best with real product names",
                "auto_fix": False, "source": "duckduckgo",
            })

    # 5. Memory sanity vs known product specs
    memory_mb = int(args.get("memory_mb", 0))
    if memory_mb and product_name and not custom_mode():
        prod_lower = product_name.lower()
        if any(k in prod_lower for k in _CFG["laptop_product_keywords"]) and memory_mb > _THRESHOLDS["max_laptop_memory_mb"]:
            issues.append({
                "severity": "warning",
                "message":  f"'{product_name}' typically supports max 32-64GB RAM, got {memory_mb//1024}GB",
                "fix":      "Reduce memory_mb to match the actual product's maximum",
                "auto_fix": False, "source": "local_knowledge",
            })

    # 6. Windows ISO architecture hint
    os_type  = str(args.get("os_type", "")).lower()
    iso_path = str(args.get("iso_path", ""))
    if ("windows" in os_type or "win" in os_type) and iso_path:
        iso_lower = os.path.basename(iso_path).lower()
        if any(k in iso_lower for k in _CFG["arm_iso_keywords"]) and machine_arch == "x86_64":
            issues.append({
                "severity": "error",
                "message":  "ARM64 Windows ISO with x86_64 VM — will not boot",
                "fix":      f"Get x86_64 ISO from: {_MS_WINDOWS_ISO_PAGE}",
                "auto_fix": False, "source": "iso_filename",
            })

    return issues


# Checks a profile against the host for ARM binary, KVM/OVMF/hugepages/RAM/core constraints, and raspi binary mismatch.
# In: str profile_name, dict? profile_data → Out: List[dict] issues

def _validate_profile_for_host(profile_name: str, profile_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Validate any profile (built-in or custom) against the current host.
    Returns a list of issue dicts.
    """
    import shutil as _shutil

    issues       = []
    all_profiles = get_all_profiles()
    profile      = profile_data or all_profiles.get(profile_name)
    if not profile:
        return []

    caps   = check_system_capabilities()
    arch   = profile.get("machine_arch", "x86_64")
    binary = profile.get("qemu_binary", "qemu-system-x86_64")

    if arch in ("aarch64", "arm") and not caps.get("qemu_arm_installed"):
        issues.append({"severity":"error","message":f"Profile '{profile_name}' needs qemu-system-aarch64 which is not installed","fix":"sudo apt install qemu-system-arm","auto_fix":False})
    if binary and not _shutil.which(binary):
        issues.append({"severity":"error","message":f"Required QEMU binary '{binary}' not found","fix":f"sudo apt install {'qemu-system-arm' if 'aarch64' in binary else 'qemu-system-x86'}","auto_fix":False})

    if profile.get("kvm", True) and arch in ("aarch64","arm") and caps.get("host_arch","x86_64") == "x86_64":
        issues.append({"severity":"warning","message":f"Profile '{profile_name}' has kvm=True but ARM guests can't use KVM on x86","fix":"kvm will be forced to False automatically","auto_fix":True,"fix_field":"kvm","fix_value":False})

    if profile.get("uefi") and not _get_ovmf().get("available") and profile.get("bios","ovmf") in ("ovmf","ovmf_ms"):
        issues.append({"severity":"warning","message":f"Profile '{profile_name}' requires UEFI but OVMF not found","fix":"sudo apt install ovmf","auto_fix":True,"fix_field":"bios","fix_value":"seabios"})

    if profile.get("hugepages"):
        try:
            with open("/proc/sys/vm/nr_hugepages") as f:
                if int(f.read().strip()) == 0:
                    issues.append({"severity":"error","message":f"Profile '{profile_name}' uses hugepages but none are allocated","fix":"sudo sysctl vm.nr_hugepages=2048","auto_fix":True,"fix_field":"hugepages","fix_value":False})
        except Exception:
            pass  # hugepages probe is advisory — skip the warning if /proc can't be read

    profile_mem = int(profile.get("memory_mb", 2048))
    host_mem    = caps.get("host_memory_mb", 0)
    if host_mem > 0 and profile_mem > host_mem:
        issues.append({"severity":"warning","message":f"Profile requests {profile_mem}MB RAM but host only has {host_mem}MB","fix":f"Reduce memory_mb to {host_mem//2} or less","auto_fix":True,"fix_field":"memory_mb","fix_value":min(profile_mem, int(host_mem*_THRESHOLDS["profile_memory_ratio"]))})

    profile_cores = int(profile.get("cpu_cores", 2))
    host_cores    = caps.get("host_cpu_cores", 1)
    if profile_cores > host_cores * _THRESHOLDS["profile_cores_overcommit"]:
        issues.append({"severity":"warning","message":f"Profile requests {profile_cores} cores but host only has {host_cores} — heavy over-commit","fix":f"Reduce cpu_cores to {host_cores} or less","auto_fix":True,"fix_field":"cpu_cores","fix_value":host_cores})

    free_gb = caps.get("home_free_gb", 999)
    if free_gb < _THRESHOLDS["min_disk_free_gb_error"]:
        issues.append({"severity":"error","message":f"Only {free_gb}GB free in home directory","fix":"Free up disk space before creating the VM","auto_fix":False})
    elif free_gb < _THRESHOLDS["min_disk_free_gb_warn"]:
        issues.append({"severity":"warning","message":f"Only {free_gb}GB free — VM disk image may exceed available space","fix":"Use a smaller disk_size_gb or free up space","auto_fix":False})

    mt = profile.get("machine_type", "q35")
    if "raspi" in mt and "aarch64" not in binary:
        issues.append({"severity":"error","message":f"Profile '{profile_name}' uses raspi machine type but qemu_binary is not aarch64","fix":"Set qemu_binary=qemu-system-aarch64 in the profile","auto_fix":True,"fix_field":"qemu_binary","fix_value":"qemu-system-aarch64"})

    notes = profile.get("_notes", "")
    if notes and "slow" in notes.lower():
        issues.append({"severity":"warning","message":f"Profile note: {notes}","fix":"","auto_fix":False})

    if profile.get("_custom"):
        cpu_model = profile.get("cpu_model", "host")
        if any(cpu_model.lower().startswith(p) for p in _ARM_CPU_PREFIXES) and arch == "x86_64":
            issues.append({"severity":"error","message":f"Custom profile '{profile_name}' has ARM cpu_model='{cpu_model}' but machine_arch=x86_64","fix":"Change cpu_model to 'host' or set machine_arch=aarch64","auto_fix":True,"fix_field":"cpu_model","fix_value":"host"})
        missing = [f for f in ("manufacturer","product_name") if not profile.get(f)]
        if missing:
            issues.append({"severity":"warning","message":f"Custom profile '{profile_name}' is missing SMBIOS fields: {missing}","fix":"Add manufacturer and product_name for better hardware spoofing","auto_fix":False})

    return issues


