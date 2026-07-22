"""
checks.py — the per-tool pre-flight checks (one PreflightCheck class each).

The lighter checks (the create_vm one is heavy enough to live in create_vm.py):
create_profile hardware/compat validation, and the destructive/existence guards for
launch/delete/remove_template/resize/monitor-cmd/snapshot. Each returns an action
dict or None (= ok).
"""

import os
from typing import Any, Dict, Optional

from executor.api._vm_constants import VM_BASE_DIR
from .base import PreflightCheck
from .context import (
    _PREFLIGHT_HW_FIELDS, _DESTRUCTIVE_MON_CMDS, _triage,
    _validate_profile_for_host, _validate_with_internet,
)


class CreateProfileCheck(PreflightCheck):
    tools = ("create_profile",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        profile_name = str(args.get("profile_name", "")).strip()
        profile_data = {k: v for k, v in args.items() if k not in ("profile_name", "force")}

        if not any(f in profile_data for f in _PREFLIGHT_HW_FIELDS):
            return {
                "action":     "abort",
                "reason":     f"Profile '{profile_name}' has no hardware configuration — only a description was provided.",
                "correction": "Provide at least cpu_model, machine_type, and memory_mb when creating a profile.",
            }

        profile_issues = [] if stateless_only else (
            _validate_profile_for_host(profile_name, profile_data=profile_data)
            + _validate_with_internet(profile_data, verbose=verbose)
        )
        if profile_issues:
            blockers, auto_fixes, warnings = _triage(profile_issues)
            if blockers:
                return {
                    "action":      "ask_user",
                    "reason":      " | ".join(i["message"] for i in blockers),
                    "question":    f"Profile '{profile_name}' has compatibility issues. Save anyway or cancel?",
                    "fix_field":   None,
                    "options":     ["Save anyway", "Cancel"],
                    "correction":  " | ".join(i["fix"] for i in blockers if i.get("fix")),
                    "issues":      profile_issues,
                }
            if auto_fixes:
                fixed      = dict(args)
                fix_notes  = []
                for issue in auto_fixes:
                    if issue.get("fix_field") and issue.get("fix_value") is not None:
                        fixed[issue["fix_field"]] = issue["fix_value"]
                        fix_notes.append(f"{issue['fix_field']}={issue['fix_value']!r}")
                return {
                    "action":      "auto_fix",
                    "reason":      "Pre-flight auto-fixed: " + ", ".join(fix_notes),
                    "correction":  " | ".join(i["message"] for i in auto_fixes),
                    "fixed_args":  fixed,
                    "warnings":    [i["message"] for i in warnings],
                }
        return None


class LaunchVMCheck(PreflightCheck):
    tools = ("launch_vm",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        if stateless_only:
            return None
        name = str(args.get("name", "")).strip()
        if name:
            # Check VM existence via manager (works in both local and split/remote mode)
            vm_exists = False
            candidates = []
            try:
                all_vms = manager.list_vms() if hasattr(manager, "list_vms") else []
                vm_names = [v["name"] for v in all_vms if isinstance(v, dict) and "name" in v]
                vm_exists = name in vm_names
                if not vm_exists:
                    candidates = [n for n in vm_names if name.lower() in n.lower()]
            except Exception:
                vm_dir = os.path.join(VM_BASE_DIR, name)
                vm_exists = os.path.exists(vm_dir)
            if not vm_exists:
                if candidates:
                    return {"action":"abort","reason":f"VM '{name}' not found. Did you mean: {candidates}?","correction":f"Use one of these names: {candidates}"}
                return {"action":"abort","reason":f"VM '{name}' doesn't exist. Create it first.","correction":"Call create_vm before launch_vm."}
        try:
            from executor.api.qemu_config import MachineConfig
            cfg = MachineConfig.load(name)
            if cfg.iso_path and not os.path.exists(cfg.iso_path):
                return {"action":"ask_user","reason":f"ISO file missing: {cfg.iso_path}","question":f"The ISO '{os.path.basename(cfg.iso_path)}' is missing. Launch without ISO, or fix the path?","fix_field":None,"options":["Launch anyway (no ISO)","Cancel"]}
        except Exception:
            pass  # preflight is advisory — unreadable config skips the ISO check rather than blocking launch
        return None


class DeleteVMCheck(PreflightCheck):
    tools = ("delete_vm",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        name = str(args.get("name", "")).strip()
        if name and not args.get("force"):
            return {"action":"ask_user","reason":f"Destructive operation: delete VM '{name}'","question":f"Are you sure you want to delete '{name}'?","fix_field":None,"options":["Yes, delete it","No, keep it"],"correction":"Deletion cannot be undone without recreating the VM."}
        return None


class RemoveTemplateCheck(PreflightCheck):
    tools = ("remove_template",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        name = str(args.get("name", "")).strip()
        if name and not args.get("force"):
            return {"action":"ask_user","reason":f"Remove template '{name}'","question":f"Delete the template copy for '{name}'? This permanently removes the golden disk copy.","fix_field":None,"options":["Yes, remove it","No, cancel"],"correction":"The golden disk copy cannot be recovered without re-marking the source VM (if it still exists)."}
        return None


class ResizeDiskCheck(PreflightCheck):
    tools = ("resize_disk",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        if stateless_only:
            return None
        name     = str(args.get("name", "")).strip()
        new_size = int(args.get("new_size_gb", 0))
        if name and new_size:
            try:
                known_vms = {v.get("name") for v in (manager.list_vms() if manager else [])}
                if name not in known_vms:
                    return {"action":"abort","reason":f"VM '{name}' does not exist — cannot resize disk","correction":"Create the VM first with create_vm, then resize."}
            except Exception:
                pass  # advisory check — if listing VMs fails, skip existence check rather than block resize
            try:
                from executor.api.qemu_config import MachineConfig
                cfg = MachineConfig.load(name)
                if cfg.disks:
                    current = cfg.disks[0].size_gb
                    if new_size < current:
                        return {"action":"abort","reason":f"Cannot shrink disk from {current}GB to {new_size}GB — QEMU doesn't support shrinking","correction":f"new_size_gb must be >= current size ({current}GB)"}
            except Exception:
                pass  # advisory check — unreadable config skips the shrink check rather than blocking resize
        return None


class MonitorCmdCheck(PreflightCheck):
    tools = ("send_monitor_cmd",)

    def check(self, tool_name, args, manager, verbose, stateless_only):
        cmd = str(args.get("cmd", "")).strip().lower()
        if any(d in cmd for d in _DESTRUCTIVE_MON_CMDS):
            return {"action":"ask_user","reason":f"Potentially destructive monitor command: '{cmd}'","question":f"Run QEMU monitor command '{cmd}'? This may affect the running VM.","fix_field":None,"options":["Yes, run it","No, cancel"]}
        return None


class SnapshotCheck(PreflightCheck):
    tools = ("snapshot_restore", "snapshot_delete")

    def check(self, tool_name, args, manager, verbose, stateless_only):
        name      = str(args.get("name", "")).strip()
        snap_name = str(args.get("snap_name", "")).strip()
        if not args.get("force"):
            verb = "restore" if tool_name == "snapshot_restore" else "delete"
            return {"action":"ask_user","reason":f"Snapshot {verb}: '{snap_name}' on VM '{name}'","question":f"Confirm {verb} snapshot '{snap_name}' on '{name}'?","fix_field":None,"options":[f"Yes, {verb} it","No, cancel"],"correction":"Snapshot restore replaces current VM state. Snapshot delete is permanent."}
        return None
