"""stealth.py — the stealth-VM SMBIOS/GPU/firmware/CPU checks (used by the create_vm
pre-flight). Returns a list of issue dicts (severity error/warning/auto_fix)."""

from typing import Any, Dict, List

from .context import _QEMU_CPU_MODELS, _LAPTOP_TYPE_KEYWORDS, _stealth_infer_from_product


def _validate_stealth_args(args: Dict[str, Any]) -> List[Dict]:
    """
    Return a list of issue dicts for a stealth VM config.
    Severity "error"   = directly exposes the VM (inxi / lspci / dmidecode will detect it).
    Severity "warning" = weakens stealth but doesn't break core detection bypass.
    """
    issues = []

    product_name = str(args.get("product_name", "")).strip()
    inferred     = _stealth_infer_from_product(product_name) if product_name else {}

    # ── SMBIOS identity fields ────────────────────────────────────────────────

    # manufacturer + product_name drive the inxi "System:" line.
    # Blank fields are themselves a detection signal.
    # If product_name was given and we can infer manufacturer, auto-fix rather than block.
    if not str(args.get("manufacturer", "")).strip():
        if inferred.get("manufacturer"):
            issues.append({
                "severity":  "auto_fix",
                "message":   f"stealth VM missing 'manufacturer' — inferred '{inferred['manufacturer']}' from product_name",
                "fix":       f"manufacturer set to '{inferred['manufacturer']}'",
                "fix_field": "manufacturer",
                "fix_value": inferred["manufacturer"],
                "auto_fix":  True,
            })
        else:
            issues.append({
                "severity":  "error",
                "message":   "stealth VM missing 'manufacturer' — inxi System line will be blank, a VM signal",
                "fix":       "Set manufacturer to match the spoofed hardware (e.g. 'Dell Inc.')",
                "fix_field": "manufacturer",
            })

    if not product_name:
        issues.append({
            "severity":  "error",
            "message":   "stealth VM missing 'product_name' — inxi product field will be blank, a VM signal",
            "fix":       "Set product_name to match the spoofed hardware (e.g. 'Latitude 5530')",
            "fix_field": "product_name",
        })

    # smbios_type drives chassis_type byte injection.
    # No smbios_type + no machine_class → chassis defaults to Desktop (type=3).
    # That is fine for a desktop profile, but a laptop fingerprint requires type=9 (Notebook).
    smbios_type   = str(args.get("smbios_type", "")).lower()
    machine_class = str(args.get("machine_class", "desktop")).lower()
    if not smbios_type:
        if inferred.get("smbios_type"):
            issues.append({
                "severity":  "auto_fix",
                "message":   f"stealth VM missing 'smbios_type' — inferred '{inferred['smbios_type']}' from product_name",
                "fix":       f"smbios_type set to '{inferred['smbios_type']}'",
                "fix_field": "smbios_type",
                "fix_value": inferred["smbios_type"],
                "auto_fix":  True,
            })
        elif any(k in machine_class for k in _LAPTOP_TYPE_KEYWORDS):
            issues.append({
                "severity":  "warning",
                "message":   "stealth VM has laptop machine_class but no smbios_type — chassis defaults to Desktop (type=3) not Laptop (type=9); inxi may call check_vm()",
                "fix":       "Set smbios_type='Notebook' to inject chassis_type=9",
                "fix_field": "smbios_type",
            })

    # bios_vendor spoofs SMBIOS type=0 (BIOS info).
    # Without it QEMU's "EFI Development Kit II" or "SeaBIOS" leaks through.
    if not str(args.get("bios_vendor", "")).strip():
        if inferred.get("bios_vendor"):
            issues.append({
                "severity":  "auto_fix",
                "message":   f"stealth VM missing 'bios_vendor' — inferred '{inferred['bios_vendor']}' from product_name",
                "fix":       f"bios_vendor set to '{inferred['bios_vendor']}'",
                "fix_field": "bios_vendor",
                "fix_value": inferred["bios_vendor"],
                "auto_fix":  True,
            })
        else:
            issues.append({
                "severity":  "warning",
                "message":   "stealth VM missing 'bios_vendor' — BIOS vendor will show QEMU/EFI defaults in dmidecode",
                "fix":       "Set bios_vendor matching the spoofed hardware (e.g. 'Dell Inc.')",
                "fix_field": "bios_vendor",
            })

    # bios_version appears in SMBIOS type=0 and is visible in dmidecode + WMI.
    # OVMF default is something like "0.0.0" or an edk2 build string.
    if not str(args.get("bios_version", "")).strip():
        issues.append({
            "severity":  "warning",
            "message":   "stealth VM missing 'bios_version' — OVMF default version string leaks in SMBIOS type=0",
            "fix":       "Set bios_version matching the spoofed hardware (e.g. '1.15.0' for a Dell)",
            "fix_field": "bios_version",
        })

    # serial_number is in SMBIOS type=1 — not checked by inxi but visible to
    # browser fingerprinting tools that read WMI (Windows) or dmidecode (Linux).
    if not str(args.get("serial_number", "")).strip():
        issues.append({
            "severity":  "warning",
            "message":   "stealth VM missing 'serial_number' — SMBIOS chassis/system serial will be empty (visible via dmidecode/WMI)",
            "fix":       "Set serial_number matching the spoofed hardware",
            "fix_field": "serial_number",
        })

    # ── GPU / display ─────────────────────────────────────────────────────────

    # virtio-vga / virtio-vga-gl carries PCI vendor 0x1af4 (Red Hat/QEMU).
    # lspci inside the guest shows this; it is one of the most common VM detection
    # vectors. create_vm auto-sets gpu="none" for stealth VMs that don't request a
    # specific GPU (qemu_arg_builder then picks vmware-svga on Linux / VGA on
    # Windows) — so this is informational only, not a blocking ask_user prompt.
    gpu = str(args.get("gpu", "virtio")).lower()
    if gpu == "virtio" and "gpu" in args:
        stealth_gpu_device = "VGA" if str(args.get("os_type", "")).lower() == "windows" else "vmware-svga"
        issues.append({
            "severity":  "warning",
            "message":   (
                "stealth VM GPU is 'virtio' (virtio-vga) — PCI vendor 0x1af4 (Red Hat/QEMU) "
                "is trivially detectable via lspci"
            ),
            "fix":       f"Remove the explicit gpu='virtio' to get the stealth default ({stealth_gpu_device}), or set gpu='qxl'",
            "fix_field": "gpu",
        })

    # SPICE display requires the SPICE guest agent and virtio-serial inside the VM.
    # The SPICE agent package name and the virtio-serial PCI device both reveal the VM.
    if str(args.get("display", "")).lower() == "spice":
        issues.append({
            "severity":  "error",
            "message":   "stealth VM using SPICE display — SPICE requires virtio-serial (PCI 0x1af4) and guest agent, both are VM signals",
            "fix":       "Use display='sdl' or display='gtk' instead",
            "fix_field": "display",
        })

    # ── Firmware ──────────────────────────────────────────────────────────────

    # UEFI=False means SeaBIOS. SeaBIOS sets BIOS vendor to "SeaBIOS" and
    # version to a build string — both are unambiguous VM signals in dmidecode.
    if args.get("uefi") is False:
        issues.append({
            "severity":  "error",
            "message":   "stealth VM has uefi=False — SeaBIOS sets BIOS vendor 'SeaBIOS', a clear VM signal in SMBIOS type=0",
            "fix":       "Use uefi=True (OVMF) so BIOS vendor/version can be spoofed via smbios args",
            "fix_field": "uefi",
        })

    # ── CPU model ─────────────────────────────────────────────────────────────

    # QEMU-named CPU models (qemu64, kvm64, etc.) expose a CPU model string that
    # doesn't match any real hardware — detectable via /proc/cpuinfo and CPUID tools.
    cpu_model = str(args.get("cpu_model", "host")).lower()
    if cpu_model in _QEMU_CPU_MODELS:
        issues.append({
            "severity":  "error",
            "message":   f"stealth VM cpu_model='{cpu_model}' is a QEMU synthetic model — /proc/cpuinfo will show a non-existent CPU, detectable by any fingerprinting tool",
            "fix":       "Use cpu_model='host' to pass through the real host CPU identity",
            "fix_field": "cpu_model",
        })

    return issues
