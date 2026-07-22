"""
_vm_templates.py — VM Template Mixin (mark / remove / list golden images).

Provides _VmTemplatesMixin which is composed into QemuManager. Carved out of
_vm_lifecycle.py to keep that focused on create / clone / delete; the shared
_template_dir helper now lives in _vm_constants.
"""
import json
import os
import shutil
import subprocess
from typing import Any, Dict, List

from ._vm_constants import TEMPLATES_DIR, TEMPLATE_LABEL, _template_dir
from .qemu_config import MachineConfig
from .label_registry import register_label


class _VmTemplatesMixin:
    """Mixin providing golden-image template mark / remove / list."""

    def mark_as_template(self, name: str) -> Dict[str, Any]:
        """Snapshot a stopped VM's current disk state into a reusable golden template.

        Flattens each disk (qemu-img convert, not a backing-file link) into
        ``~/.qemu_vms/_templates/<name>/diskN.qcow2`` so the template never depends on the
        source VM's own disk surviving. Tags the source VM with the protected "template"
        label; the template.json copy also records "template" in its own labels.

        Args:
            name: VM to snapshot (must be stopped).

        Returns:
            ``{"success": True, "message": str, "template": str}`` or error dict.

        Example::
            >>> mgr.mark_as_template("vm_perfect_kali")
            {"success": True, "message": "...", "template": "vm_perfect_kali"}
        """
        if self._is_running(name):
            return {"success": False, "error": "Stop the VM before marking it as a template."}
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

        if TEMPLATE_LABEL in cfg.labels:
            return {"success": False, "error": f"'{name}' is already marked as a template."}

        tmpl_dir = _template_dir(name)
        if os.path.exists(tmpl_dir):
            return {"success": False, "error": f"A template named '{name}' already exists."}
        os.makedirs(tmpl_dir, exist_ok=True)

        disks_meta = []
        for i, disk in enumerate(cfg.disks):
            src_path = os.path.expanduser(disk.path)
            dst_path = os.path.join(tmpl_dir, f"disk{i}.qcow2")
            if not os.path.exists(src_path):
                shutil.rmtree(tmpl_dir)
                return {"success": False, "error": f"Disk not found: {src_path}"}
            result = subprocess.run(
                ["qemu-img", "convert", "-O", "qcow2", src_path, dst_path],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                shutil.rmtree(tmpl_dir)
                return {"success": False, "error": f"Template disk conversion failed: {result.stderr}"}
            disks_meta.append({"size_gb": disk.size_gb, "format": "qcow2", "bus": disk.bus})

        with open(os.path.join(tmpl_dir, "template.json"), "w") as f:
            json.dump({
                "name":     name,
                "os_type":  cfg.os_type,
                "disks":    disks_meta,
                "labels":   [TEMPLATE_LABEL],
            }, f, indent=2)

        cfg.labels.append(TEMPLATE_LABEL)
        cfg.save()
        register_label(TEMPLATE_LABEL)

        return {"success": True,
                "message": f"'{name}' marked as a template ({len(disks_meta)} disk(s) saved to {tmpl_dir}).",
                "template": name}

    def remove_template(self, name: str) -> Dict[str, Any]:
        """Delete a golden template's disk copy and un-tag the source VM if it still exists.

        Gated behind a Yes/Cancel confirmation at the preflight layer (see
        _PREFLIGHT_TOOLS/"remove_template" in the preflight validator) — this method itself
        performs the deletion unconditionally once called, same as delete_vm.

        Args:
            name: Template name (matches the VM name it was created from).

        Returns:
            ``{"success": True, "message": str}`` or error dict.

        Example::
            >>> mgr.remove_template("vm_perfect_kali")
            {"success": True, "message": "Template 'vm_perfect_kali' removed."}
        """
        tmpl_dir = _template_dir(name)
        if not os.path.exists(tmpl_dir):
            return {"success": False, "error": f"No template named '{name}'."}
        shutil.rmtree(tmpl_dir)

        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError:
            return {"success": True, "message": f"Template '{name}' removed (source VM no longer exists)."}

        if TEMPLATE_LABEL in cfg.labels:
            cfg.labels = [l for l in cfg.labels if l != TEMPLATE_LABEL]
            cfg.save()
        return {"success": True, "message": f"Template '{name}' removed."}

    def list_templates(self) -> List[Dict[str, Any]]:
        """List every registered golden-image template.

        Returns:
            List of ``{"name": str, "os_type": str, "disks": int}`` dicts.

        Example::
            >>> mgr.list_templates()
            [{"name": "vm_perfect_kali", "os_type": "linux", "disks": 1}]
        """
        if not os.path.isdir(TEMPLATES_DIR):
            return []
        result = []
        for name in sorted(os.listdir(TEMPLATES_DIR)):
            meta_path = os.path.join(TEMPLATES_DIR, name, "template.json")
            if not os.path.isfile(meta_path):
                continue
            with open(meta_path) as f:
                meta = json.load(f)
            result.append({
                "name":    name,
                "os_type": meta.get("os_type", ""),
                "disks":   len(meta.get("disks", [])),
            })
        return result
