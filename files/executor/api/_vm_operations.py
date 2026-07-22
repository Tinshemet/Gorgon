"""
_vm_operations.py — VM Operations Mixin (disk, resources, config, labels, monitor).

Provides _VmOperationsMixin which is composed into QemuManager. Snapshots were
carved out into _vm_snapshots.py (_VmSnapshotsMixin) to keep this focused.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from ._vm_constants import (
    _BUFFERS, _LOG_DEFAULT_LINES, _LOG_ERROR_PATTERNS,
    _MONITOR_ALLOWED_CMDS, _TIMEOUTS, _UPDATE_ALLOWED_FIELDS,
    _VALID_MACHINE_TYPES, VM_BASE_DIR, TEMPLATE_LABEL,
)
from .qemu_config import MachineConfig
from .qemu_arg_builder import QemuArgBuilder
from .qmp_client import QMPClient
from .label_registry import register_label, list_registered_labels


class _VmOperationsMixin:
    """Mixin providing disk ops, resource limits, config, labels, and monitor commands."""

    # ------------------------------------------------------------------
    # Disk
    # ------------------------------------------------------------------

    def resize_disk(self, name: str, disk_index: int, new_size_gb: int) -> Dict[str, Any]:
        """Grow a stopped VM's disk image and update its config.

        Args:
            name:        VM name (must be stopped).
            disk_index:  Zero-based index into ``config.disks``.
            new_size_gb: New disk size in GiB (must be larger than current).

        Returns:
            ``{"success": True, "message": str}`` or error dict.

        Example::
            >>> mgr.resize_disk("my-linux", 0, 60)
            {"success": True, "message": "Disk 0 resized to 60GB. Remember to expand..."}
        """
        if self._is_running(name):
            return {"success": False, "error": "Stop the VM before resizing."}
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        if disk_index < 0 or disk_index >= len(cfg.disks):
            return {"success": False, "error": f"Disk index {disk_index} out of range."}

        disk_path = os.path.expanduser(cfg.disks[disk_index].path)
        result    = subprocess.run(
            ["qemu-img", "resize", disk_path, f"{new_size_gb}G"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        cfg.disks[disk_index].size_gb = new_size_gb
        cfg.save()
        return {
            "success": True,
            "message": (
                f"Disk {disk_index} resized to {new_size_gb}GB. "
                "Remember to expand the partition inside the guest."
            ),
        }


    # ------------------------------------------------------------------
    # Resource limits
    # ------------------------------------------------------------------

    def set_resource_limits(
        self,
        name: str,
        cpu_percent: Optional[int] = None,
        memory_mb:   Optional[int] = None,
    ) -> Dict[str, Any]:
        """Cap CPU via cpulimit/cgroups and adjust balloon memory via QMP.

        Args:
            name:        VM name (must be running).
            cpu_percent: CPU cap as a percentage of one core (e.g. ``50``).
                         Linux only; no-op on other platforms.
            memory_mb:   Target balloon size in MiB.

        Returns:
            ``{"success": True, "name": str, "results": dict}`` where ``results``
            holds per-resource outcome or error keys.

        Example::
            >>> mgr.set_resource_limits("my-linux", cpu_percent=50, memory_mb=2048)
            {"success": True, "name": "my-linux", "results": {"cpu_limit": "...", ...}}
        """
        if not self._is_running(name):
            return {"success": False, "error": f"VM '{name}' is not running."}

        results: Dict[str, Any] = {}
        pid = self._state.get_pid(name)

        if cpu_percent is not None:
            if sys.platform != "linux":
                results["cpu_limit_error"] = (
                    f"CPU limiting via cpulimit/cgroups is Linux-only "
                    f"(current platform: {sys.platform})."
                )
            elif shutil.which("cpulimit"):
                subprocess.Popen(
                    ["cpulimit", "-p", str(pid), "-l", str(cpu_percent), "-b"],
                    start_new_session=True,
                )
                results["cpu_limit"] = f"cpulimit set to {cpu_percent}% (PID {pid})"
            else:
                cgroup_path = f"/sys/fs/cgroup/gorgon-{name}"
                try:
                    os.makedirs(cgroup_path, exist_ok=True)
                    quota  = int(cpu_percent * 1000)
                    period = 100_000
                    with open(f"{cgroup_path}/cpu.max", "w") as f:
                        f.write(f"{quota} {period}\n")
                    with open(f"{cgroup_path}/cgroup.procs", "w") as f:
                        f.write(str(pid))
                    results["cpu_limit"] = f"cgroup cpu.max set to {cpu_percent}%"
                except PermissionError:
                    results["cpu_limit_error"] = (
                        "Need sudo for cgroups. "
                        "Install cpulimit instead: sudo apt install cpulimit"
                    )

        if memory_mb is not None:
            try:
                cfg = MachineConfig.load(name)
                with QMPClient(cfg.get_qmp_socket()) as qmp:
                    qmp.connect()
                    qmp.execute("balloon", {"value": memory_mb * 1024 * 1024})
                results["memory_balloon"] = f"Ballooned to {memory_mb}MB"
            except Exception as e:
                results["memory_balloon_error"] = str(e)

        return {"success": True, "name": name, "results": results}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def show_config(self, name: str) -> Dict[str, Any]:
        """Return the VM's full config as a dict.

        Args:
            name: VM name.

        Returns:
            ``{"success": True, "config": dict}`` or error dict.

        Example::
            >>> mgr.show_config("my-linux")
            {"success": True, "config": {"name": "my-linux", "memory_mb": 4096, ...}}
        """
        try:
            cfg = MachineConfig.load(name)
            return {"success": True, "config": cfg.to_dict()}
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

    def update_config(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a dict of field updates to a stopped VM's config and persist it.

        Only fields present in ``_UPDATE_ALLOWED_FIELDS`` may be changed.

        Args:
            name:    VM name (must be stopped).
            updates: Mapping of field name → new value.

        Returns:
            ``{"success": True, "message": str}`` or error dict.

        Example::
            >>> mgr.update_config("my-linux", {"memory_mb": 8192})
            {"success": True, "message": "Updated ['memory_mb'] for 'my-linux'."}
        """
        if self._is_running(name):
            return {"success": False, "error": "Stop the VM before updating config."}
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

        changed = []
        for key, value in updates.items():
            if key not in _UPDATE_ALLOWED_FIELDS:
                return {"success": False,
                        "error": f"Field '{key}' cannot be updated via API."}
            if not hasattr(cfg, key):
                return {"success": False, "error": f"Unknown config field: '{key}'"}
            setattr(cfg, key, value)
            changed.append(key)
        cfg.save()
        return {"success": True, "message": f"Updated {changed} for '{name}'."}

    # ------------------------------------------------------------------
    # Labels (user-defined tags)
    # ------------------------------------------------------------------

    def add_label(self, name: str, label: str) -> Dict[str, Any]:
        """Assign a user label to a VM, registering it machine-wide if new.

        Labels are metadata, so this works whether the VM is running or stopped.

        Args:
            name:  VM name.
            label: Free-form tag (e.g. "work_vm"). Added to the universal registry.

        Returns:
            ``{"success": True, "labels": [...]}`` or error dict.

        Example::
            >>> mgr.add_label("tomer", "work_vm")
            {"success": True, "message": "Labeled 'tomer' with 'work_vm'.", "labels": ["work_vm"]}
        """
        label = (label or "").strip()
        if not label:
            return {"success": False, "error": "A label name is required."}
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        if label not in cfg.labels:
            cfg.labels.append(label)
            cfg.save()
        register_label(label)
        return {"success": True,
                "message": f"Labeled '{name}' with '{label}'.",
                "labels": cfg.labels}

    def remove_label(self, name: str, label: str) -> Dict[str, Any]:
        """Remove a user label from a VM (it stays in the universal registry).

        Args:
            name:  VM name.
            label: Label to remove from this VM.

        Returns:
            ``{"success": True, "labels": [...]}`` or error dict.

        Example::
            >>> mgr.remove_label("tomer", "work_vm")
            {"success": True, "message": "Removed label 'work_vm' from 'tomer'.", "labels": []}
        """
        if label == TEMPLATE_LABEL:
            return {"success": False,
                    "error": f"The '{TEMPLATE_LABEL}' label can't be removed directly — use "
                             f"remove_template('{name}') instead, which also cleans up the golden copy."}
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}
        if label not in cfg.labels:
            return {"success": False, "error": f"VM '{name}' has no label '{label}'."}
        cfg.labels = [l for l in cfg.labels if l != label]
        cfg.save()
        return {"success": True,
                "message": f"Removed label '{label}' from '{name}'.",
                "labels": cfg.labels}

    def list_labels(self) -> Dict[str, Any]:
        """List every registered label and which VMs carry each.

        Returns:
            ``{"success": True, "labels": [...], "usage": {label: [vm, ...]}}``.

        Example::
            >>> mgr.list_labels()
            {"success": True, "labels": ["work_vm"], "usage": {"work_vm": ["tomer"]}}
        """
        usage: Dict[str, List[str]] = {lbl: [] for lbl in list_registered_labels()}
        for vm in self.list_vms():
            for lbl in vm.get("labels", []):
                usage.setdefault(lbl, []).append(vm["name"])
        return {"success": True, "labels": sorted(usage), "usage": usage}

    # ------------------------------------------------------------------
    # Command
    # ------------------------------------------------------------------

    def print_command(self, name: str) -> Dict[str, Any]:
        """Build and return the full QEMU CLI string without executing it.

        Args:
            name: VM name.

        Returns:
            ``{"success": True, "command": str}`` or error dict.

        Example::
            >>> mgr.print_command("my-linux")
            {"success": True, "command": "qemu-system-x86_64 -name my-linux ..."}
        """
        try:
            cfg = MachineConfig.load(name)
            cmd = QemuArgBuilder(cfg).build()
            return {"success": True, "command": " ".join(cmd)}
        except FileNotFoundError as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Monitor
    # ------------------------------------------------------------------

    def send_monitor_cmd(self, name: str, cmd: str) -> Dict[str, Any]:
        """Send a command to the QEMU human monitor socket.

        Only commands matching a prefix in ``_MONITOR_ALLOWED_CMDS`` are permitted.

        Args:
            name: VM name.
            cmd:  HMP command string (e.g. ``"info status"``).

        Returns:
            ``{"success": True, "output": str}`` or error dict.

        Example::
            >>> mgr.send_monitor_cmd("my-linux", "info status")
            {"success": True, "output": "VM status: running\\r\\n(qemu) "}
        """
        cmd_stripped = cmd.strip()
        if not any(
            cmd_stripped == allowed.rstrip() or cmd_stripped.startswith(allowed)
            for allowed in _MONITOR_ALLOWED_CMDS
        ):
            return {"success": False, "error": f"Command not permitted: '{cmd_stripped}'"}
        try:
            cfg       = MachineConfig.load(name)
            sock_path = cfg.get_monitor_socket()
            if sock_path.startswith("tcp:"):
                host, port = sock_path[4:].rsplit(":", 1)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(_TIMEOUTS["qmp_connect"])
                s.connect((host, int(port)))
            else:
                if not os.path.exists(sock_path):
                    return {"success": False, "error": "Monitor socket not found."}
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(_TIMEOUTS["qmp_connect"])
                s.connect(sock_path)
            time.sleep(_TIMEOUTS["monitor_recv_sleep"])
            s.recv(_BUFFERS["monitor_send"])
            s.sendall((cmd + "\n").encode())
            time.sleep(_TIMEOUTS["monitor_recv_sleep"])
            response = s.recv(_BUFFERS["monitor_recv"]).decode()
            s.close()
            return {"success": True, "output": response}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Disk check
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

