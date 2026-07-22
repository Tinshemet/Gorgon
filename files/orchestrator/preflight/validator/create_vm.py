"""create_vm.py — the create_vm pre-flight check (the heaviest: hardware/host
validation, stealth args, internet product lookup, ISO resolution)."""

import os
import re
from typing import Any, Dict, List

from .base import PreflightCheck
from .context import (
    _THRESHOLDS, VALID_MACHINE_TYPES, PLACEHOLDER_VM_NAMES, REAL_HOME, _resolve_iso,
    _validate_with_internet, _validate_profile_for_host, get_all_profiles, _triage,
)
from .stealth import _validate_stealth_args


def _preflight_create_vm(args: Dict[str, Any], manager: object, verbose: bool,
                         stateless_only: bool) -> Dict[str, Any]:
    """Pre-flight validation for create_vm (name/ISO/arch/memory/profile checks
    and the destructive-unattended confirmation gate). Extracted from
    _preflight_check() to keep the per-tool dispatch readable.

    Returns an action dict — {"action": "ok"} when nothing needs attention,
    else "auto_fix" / "ask_user" / "abort" with the relevant fields.

    Example::
        _preflight_create_vm({"name": "dev", "os_type": "linux"}, mgr, False, False)
        # -> {"action": "ok"}
    """
    name     = str(args.get("name", "")).strip()
    iso_path = str(args.get("iso_path", "")).strip()
    os_type  = str(args.get("os_type", "")).lower()
    mt       = str(args.get("machine_type", "")).lower()

    if not name or name.lower() in PLACEHOLDER_VM_NAMES:
        return {"action":"ask_user","reason":f"VM name is missing or looks invented (got: '{name}')","question":"What would you like to name this VM?","fix_field":"name","options":["my-windows-vm","dev-box","test-ubuntu"]}

    if not stateless_only:
        try:
            _known = {v.get("name") for v in (manager.list_vms() if manager else [])}
        except Exception:
            _known = set()
        if name in _known:
            return {"action":"ask_user","reason":f"A VM named '{name}' already exists","question":f"A VM called '{name}' already exists. Overwrite it, or use a different name?","fix_field":"name","original_name":name,"options":[f"{name}-2",f"{name}-new","overwrite"],"correction":"Use a different name or delete the existing VM first."}

    # Destructive opt-in: unattended install WIPES the target disk — confirm first
    # (bypassed by force=true, like delete_vm). Windows normally also auto-creates
    # a local admin account unless unattended_skip_user leaves that step manual;
    # Linux's autoinstall/preseed always leaves account creation for a human.
    _is_win = "windows" in os_type or "windows" in str(args.get("os_name", "")).lower()
    if args.get("unattended") and not args.get("force"):
        if _is_win and not args.get("unattended_skip_user"):
            _acct = args.get("unattended_username") or "user"
            return {"action":"ask_user","reason":"Unattended install wipes the target disk and auto-creates a local admin account","question":f"Unattended Windows install will WIPE this VM's disk and auto-create local admin '{_acct}'. Proceed?","fix_field":None,"options":["Yes, wipe and install","No, cancel"],"correction":"On 'Yes' the client re-runs with force=true; the disk is erased/repartitioned and a known-password admin account is created."}
        else:
            _os_label = "Windows" if _is_win else "Linux"
            return {"action":"ask_user","reason":"Unattended install wipes the target disk, stopping at account creation for you to set up manually","question":f"Unattended {_os_label} install will WIPE this VM's disk and auto-partition it, stopping at the account-creation screen. Proceed?","fix_field":None,"options":["Yes, wipe and install","No, cancel"],"correction":"On 'Yes' the client re-runs with force=true; the disk is erased/repartitioned."}

    if mt and mt not in VALID_MACHINE_TYPES and not mt.startswith("pc-"):
        fixed = dict(args)
        if mt in get_all_profiles():
            fixed["profile"] = mt
        fixed.pop("machine_type", None)
        return {"action":"auto_fix","reason":f"machine_type='{mt}' is a profile name, not a machine type","correction":f"Set profile='{mt}' and removed invalid machine_type","fixed_args":fixed}

    if iso_path and not stateless_only:
        bad_path = any([
            any(p in iso_path for p in _BAD_ISO_PATH_PATTERNS),
            not os.path.exists(os.path.expanduser(re.sub(r"^/home/[^/]+/", REAL_HOME+"/", iso_path))),
        ])
        if bad_path:
            resolved = _resolve_iso(iso_path)
            if resolved and os.path.exists(resolved):
                fixed = dict(args); fixed["iso_path"] = resolved
                return {"action":"auto_fix","reason":f"ISO path '{iso_path}' doesn't exist — auto-resolved to '{resolved}'","correction":f"iso_path corrected to: {resolved}","fixed_args":fixed}
            else:
                isos = manager.scan_isos()
                if isos:
                    return {"action":"ask_user","reason":f"ISO '{iso_path}' not found on disk","question":"Can't find that ISO. Which file did you mean?","fix_field":"iso_path","options":[iso["name"] for iso in isos[:4]]+["skip ISO"],"iso_list":isos}
                else:
                    fixed = dict(args); fixed.pop("iso_path", None)
                    return {"action":"auto_fix","reason":f"ISO '{iso_path}' not found — no ISOs found anywhere","correction":"Removed iso_path. VM will be created without an install ISO.","fixed_args":fixed}

    if iso_path and not stateless_only and os.path.exists(iso_path):
        iso_lower = os.path.basename(iso_path).lower()
        if any(k in iso_lower for k in ("arm64","aarch64")) and str(args.get("machine_arch","x86_64")).lower() == "x86_64":
            return {"action":"ask_user","reason":f"ARM64 ISO '{os.path.basename(iso_path)}' with x86_64 VM — incompatible","question":"This is an ARM64 ISO. Do you want an ARM64 VM, or an x86_64 ISO instead?","fix_field":None,"options":["Use ARM64 VM","Get x86_64 ISO instead"],"correction":f"For x86_64: download Windows 11 x64 from microsoft.com"}

    is_win = "windows" in os_type or "win" in os_type
    if is_win and args.get("uefi") is False:
        fixed = dict(args); fixed["uefi"] = True; fixed["bios"] = "ovmf"
        return {"action":"auto_fix","reason":"Windows 11 requires UEFI but uefi=False was set","correction":"Forced uefi=True and bios=ovmf","fixed_args":fixed}

    disk_gb = int(args.get("disk_size_gb", _THRESHOLDS["min_windows_disk_gb"]))
    if is_win and disk_gb < _THRESHOLDS["min_windows_disk_gb"]:
        _win_disk = _THRESHOLDS["auto_windows_disk_gb"]
        fixed = dict(args); fixed["disk_size_gb"] = _win_disk
        return {"action":"auto_fix","reason":f"Windows 11 needs at least {_win_disk}GB disk, got {disk_gb}GB","correction":f"Increased disk_size_gb from {disk_gb} to {_win_disk}","fixed_args":fixed}

    if is_win and args.get("tpm") is not False and not stateless_only:
        import shutil
        if not shutil.which("swtpm"):
            return {
                "action":     "ask_user",
                "reason":     "Windows 11 requires TPM 2.0 but swtpm is not installed",
                "question":   "Install swtpm for TPM 2.0 support, or proceed without it (Windows 11 setup will block)?",
                "fix_field":  None,
                "options":    ["Install swtpm first (sudo apt install swtpm)", "Proceed without TPM (bypass during install)"],
                "correction": "sudo apt install swtpm",
            }

    if args.get("stealth"):
        stealth_issues            = _validate_stealth_args(args)
        blockers, auto_fixes, warnings = _triage(stealth_issues)

        # Apply auto-fixes first (inferred from product_name)
        if auto_fixes:
            fixed = dict(args)
            for issue in auto_fixes:
                if issue.get("fix_field") and issue.get("fix_value") is not None:
                    fixed.setdefault(issue["fix_field"], issue["fix_value"])
            fix_notes = [f"{i['fix_field']}={i['fix_value']!r}" for i in auto_fixes]
            return {
                "action":     "auto_fix",
                "reason":     "Stealth preflight inferred missing SMBIOS fields from product_name: " + ", ".join(fix_notes),
                "correction": " | ".join(i["fix"] for i in auto_fixes),
                "fixed_args": fixed,
                "warnings":   [w["message"] for w in warnings],
            }

        if blockers:
            return {
                "action":     "ask_user",
                "reason":     " | ".join(i["message"] for i in blockers),
                "question":   "Stealth mode requires hardware identity fields to spoof SMBIOS. Provide them or proceed with partial masking?",
                "fix_field":  blockers[0].get("fix_field"),
                "options":    ["Provide the missing fields", "Proceed anyway (partial masking)"],
                "correction": " | ".join(i["fix"] for i in blockers if i.get("fix")),
                "issues":     stealth_issues,
            }
        if warnings:
            # Non-blocking — surface as warnings in the result but continue
            args = dict(args)
            args.setdefault("_stealth_warnings", [w["message"] for w in warnings])

    if not stateless_only:
        internet_issues = _validate_with_internet(args, verbose=verbose)
        if internet_issues:
            blockers, auto_fixes, warnings = _triage(internet_issues)
            if blockers:
                return {"action":"ask_user","reason":" | ".join(i["message"] for i in blockers),"question":"Pre-flight found issues with this VM config. Proceed anyway or fix first?","fix_field":None,"options":["Proceed anyway","Cancel and fix"],"correction":" | ".join(i["fix"] for i in blockers if i.get("fix")),"issues":internet_issues}
            if auto_fixes:
                fixed = dict(args); fix_notes = []
                for issue in auto_fixes:
                    if issue.get("fix_field") and issue.get("fix_value") is not None:
                        fixed[issue["fix_field"]] = issue["fix_value"]
                        fix_notes.append(f"{issue['fix_field']}={issue['fix_value']!r}")
                return {"action":"auto_fix","reason":"Internet/QEMU validation auto-fixed: "+", ".join(fix_notes),"correction":" | ".join(i["message"] for i in auto_fixes),"fixed_args":fixed,"warnings":[i["message"] for i in warnings]}

        profile_name = args.get("profile") or mt
        if profile_name:
            profile_issues = _validate_profile_for_host(profile_name)
            if profile_issues:
                blockers, auto_fixes, warnings = _triage(profile_issues)
                if blockers:
                    return {"action":"ask_user","reason":f"Profile '{profile_name}' has compatibility issues: {' | '.join(i['message'] for i in blockers)}","question":f"Profile '{profile_name}' may not work on this system. Proceed anyway or cancel?","fix_field":None,"options":["Proceed anyway","Cancel","Use minimal profile instead"],"correction":" | ".join(i["fix"] for i in blockers if i.get("fix")),"issues":profile_issues}
                if auto_fixes:
                    fixed = dict(args); fix_notes = []
                    for issue in auto_fixes:
                        if issue.get("fix_field") and issue.get("fix_value") is not None:
                            fixed[issue["fix_field"]] = issue["fix_value"]
                            fix_notes.append(f"{issue['fix_field']}={issue['fix_value']}")
                    return {"action":"auto_fix","reason":f"Profile '{profile_name}': auto-fixed "+", ".join(fix_notes),"correction":" | ".join(i["message"] for i in auto_fixes),"fixed_args":fixed,"warnings":[i["message"] for i in warnings]}

    return {"action": "ok"}




class CreateVMCheck(PreflightCheck):
    tools = ("create_vm",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        return _preflight_create_vm(args, manager, verbose, stateless_only)
