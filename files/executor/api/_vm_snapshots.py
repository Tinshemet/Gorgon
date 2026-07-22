"""
_vm_snapshots.py — VM Snapshot Mixin (create / list / restore / delete).

Provides _VmSnapshotsMixin which is composed into QemuManager. Carved out of
_vm_operations.py to keep each mixin focused — these four methods (live via QMP,
offline via qemu-img) were the file's largest cohesive block.
"""
import os
import re
import subprocess
from typing import Any, Dict

from .qemu_config import MachineConfig
from .qmp_client import QMPClient


# Parses one `qemu-img snapshot -l` data row: ID, TAG, VM SIZE ("<num> <unit>"),
# DATE ("<yyyy-mm-dd> <hh:mm:ss>"). Size and date are two whitespace-separated
# tokens each, so a plain split() mis-aligns every later column.
_SNAP_LINE_RE = re.compile(
    r"^\s*(?P<id>\S+)\s+(?P<tag>.+?)\s+"
    r"(?P<size>\d[\d.]*\s*[KMGTP]?i?B)\s+"
    r"(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)


class _VmSnapshotsMixin:
    """Mixin providing qcow2 snapshot create / list / restore / delete."""

    def snapshot_create(self, name: str, snap_name: str) -> Dict[str, Any]:
        """Create an internal qcow2 snapshot — live via QMP or offline via qemu-img.

        Live mode (VM running): uses ``blockdev-snapshot-internal-sync`` on each
        data disk, which works on UEFI/pflash VMs unlike the legacy ``savevm``
        HMP command.  Offline mode (VM stopped): uses ``qemu-img snapshot -c``.

        Args:
            name:      VM name.
            snap_name: Tag for the new snapshot.

        Returns:
            ``{"success": True, "message": str}`` or error dict.

        Example::
            >>> mgr.snapshot_create("my-linux", "pre-update")
            {"success": True, "message": "Snapshot 'pre-update' created on 1 disk(s)."}
        """
        try:
            cfg = MachineConfig.load(name)
        except FileNotFoundError:
            return {"success": False, "error": f"VM '{name}' does not exist."}
        if self._is_running(name):
            try:
                with QMPClient(cfg.get_qmp_socket()) as qmp:
                    qmp.connect()
                    r       = qmp.execute("query-block")
                    created = 0
                    errors  = []
                    for dev in r.get("return", []):
                        dev_name = dev.get("device", "")
                        # Skip pflash (OVMF vars/code), CD-ROMs, and read-only drives
                        if dev_name.startswith("pflash") or dev_name.startswith("cdrom"):
                            continue
                        inserted = dev.get("inserted")
                        if not inserted or inserted.get("ro", True):
                            continue
                        resp = qmp.execute("blockdev-snapshot-internal-sync",
                                           {"device": dev_name, "name": snap_name})
                        if "error" in resp:
                            errors.append(f"{dev_name}: {resp['error'].get('desc','?')}")
                        else:
                            created += 1
                if errors:
                    return {"success": False, "error": "; ".join(errors)}
                if created == 0:
                    return {"success": False, "error": "No writable data disks found to snapshot."}
                return {"success": True,
                        "message": f"Snapshot '{snap_name}' created on {created} disk(s)."}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            errors = []
            created = 0
            for disk in cfg.disks:
                disk_path = os.path.expanduser(disk.path)
                result = subprocess.run(
                    ["qemu-img", "snapshot", "-c", snap_name, disk_path],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    errors.append(result.stderr.strip())
                else:
                    created += 1
            if errors:
                return {"success": False, "error": "; ".join(errors)}
            return {"success": True,
                    "message": f"Snapshot '{snap_name}' created (offline) on {created} disk(s)."}

    def snapshot_list(self, name: str) -> Dict[str, Any]:
        """List all snapshots for a VM — live via QMP or offline via qemu-img.

        Args:
            name: VM name.

        Returns:
            ``{"success": True, "snapshots": list, "raw": str}`` or error dict.
            Each snapshot dict has ``id``, ``tag``, ``date``, ``vm_state_size``.

        Example::
            >>> mgr.snapshot_list("my-linux")
            {"success": True, "snapshots": [{"id": "1", "tag": "pre-update", ...}], ...}
        """
        try:
            cfg = MachineConfig.load(name)
            if not cfg.disks:
                return {"success": False, "error": "No disks."}
            if self._is_running(name):
                with QMPClient(cfg.get_qmp_socket()) as qmp:
                    qmp.connect()
                    r    = qmp.execute("query-block")
                snaps = []
                seen  = set()
                for dev in r.get("return", []):
                    for s in dev.get("inserted", {}).get("image", {}).get("snapshots", []):
                        tag = s.get("name", "")
                        if tag and tag not in seen:
                            seen.add(tag)
                            snaps.append({
                                "id":            s.get("id", ""),
                                "tag":           tag,
                                "date":          str(s.get("date-sec", "")),
                                "vm_state_size": s.get("vm-state-size", 0),
                            })
                return {"success": True, "snapshots": snaps, "raw": ""}
            else:
                disk_path = os.path.expanduser(cfg.disks[0].path)
                result    = subprocess.run(
                    ["qemu-img", "snapshot", "-l", disk_path],
                    capture_output=True, text=True,
                )
                snaps = []
                for line in result.stdout.splitlines()[2:]:
                    # qemu-img prints VM SIZE as "<num> <unit>" (e.g. "349 MiB",
                    # "0 B") and DATE as "<yyyy-mm-dd> <hh:mm:ss>" — two tokens
                    # each. A naive split() read parts[2]/parts[3] as size/date
                    # and mis-parsed both (size="349", date="MiB"). Match the
                    # units-bearing size + full timestamp explicitly instead.
                    m = _SNAP_LINE_RE.match(line)
                    if m:
                        snaps.append({
                            "id":            m.group("id"),
                            "tag":           m.group("tag"),
                            "date":          m.group("date"),
                            "vm_state_size": m.group("size"),
                        })
                return {"success": True, "snapshots": snaps, "raw": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def snapshot_restore(self, name: str, snap_name: str) -> Dict[str, Any]:
        """Restore a snapshot — live via QMP ``loadvm`` or offline via ``qemu-img -a``.

        Args:
            name:      VM name.
            snap_name: Tag of the snapshot to restore.

        Returns:
            ``{"success": True, "message": str}`` or error dict.
            Message indicates whether the restore was live or offline.

        Example::
            >>> mgr.snapshot_restore("my-linux", "pre-update")
            {"success": True, "message": "Snapshot 'pre-update' restored (offline)."}
        """
        if self._is_running(name):
            try:
                cfg  = MachineConfig.load(name)
                with QMPClient(cfg.get_qmp_socket()) as qmp:
                    qmp.connect()
                    resp = qmp.execute("human-monitor-command",
                                       {"command-line": f"loadvm {snap_name}"})
                # HMP loadvm returns empty string on success; any text is an error
                hmp_out = resp.get("return", "").strip()
                if hmp_out:
                    return {"success": False, "error": hmp_out}
                return {"success": True,
                        "message": f"Snapshot '{snap_name}' restored (live)."}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            try:
                cfg = MachineConfig.load(name)
                if not cfg.disks:
                    return {"success": False, "error": "No disks."}
                # Restore EVERY disk (snapshot_create tags them all); a disk0-only
                # rollback leaves other disks in their post-snapshot state → an
                # inconsistent/corrupt guest.
                restored, errors = [], []
                for disk in cfg.disks:
                    disk_path = os.path.expanduser(disk.path)
                    result    = subprocess.run(
                        ["qemu-img", "snapshot", "-a", snap_name, disk_path],
                        capture_output=True, text=True,
                    )
                    if result.returncode != 0:
                        errors.append(f"{disk_path}: {result.stderr.strip()}")
                    else:
                        restored.append(disk_path)
                if errors:
                    # Restore is destructive with no saved pre-state to undo the
                    # disks already reverted — surface the mixed state loudly
                    # rather than silently reporting success.
                    warn = (f" WARNING: {len(restored)} disk(s) already rolled back "
                            f"to '{snap_name}' while others failed — VM may be in "
                            f"an inconsistent state.") if restored else ""
                    return {"success": False, "error": "; ".join(errors) + warn}
                return {"success": True,
                        "message": f"Snapshot '{snap_name}' restored (offline) "
                                   f"on {len(restored)} disk(s)."}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def snapshot_delete(self, name: str, snap_name: str) -> Dict[str, Any]:
        """Delete a snapshot — live via QMP or offline via qemu-img.

        Args:
            name:      VM name.
            snap_name: Tag of the snapshot to delete.

        Returns:
            ``{"success": True, "message": str}`` or error dict.

        Example::
            >>> mgr.snapshot_delete("my-linux", "old-snap")
            {"success": True, "message": "Snapshot 'old-snap' deleted."}
        """
        cfg = MachineConfig.load(name)
        if self._is_running(name):
            try:
                with QMPClient(cfg.get_qmp_socket()) as qmp:
                    qmp.connect()
                    r   = qmp.execute("query-block")
                    deleted = 0
                    errors  = []
                    for dev in r.get("return", []):
                        dev_name = dev.get("device", "")
                        snaps    = dev.get("inserted", {}).get("image", {}).get("snapshots", [])
                        if not any(s.get("name") == snap_name for s in snaps):
                            continue
                        resp = qmp.execute("blockdev-snapshot-delete-internal-sync",
                                           {"device": dev_name, "name": snap_name})
                        if "error" in resp:
                            errors.append(f"{dev_name}: {resp['error'].get('desc','?')}")
                        else:
                            deleted += 1
                if errors:
                    return {"success": False, "error": "; ".join(errors)}
                if deleted == 0:
                    return {"success": False, "error": f"Snapshot '{snap_name}' not found."}
                return {"success": True, "message": f"Snapshot '{snap_name}' deleted."}
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            errors  = []
            deleted = 0
            for disk in cfg.disks:
                disk_path = os.path.expanduser(disk.path)
                result = subprocess.run(
                    ["qemu-img", "snapshot", "-d", snap_name, disk_path],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    errors.append(result.stderr.strip())
                else:
                    deleted += 1
            if deleted == 0:
                return {"success": False, "error": "; ".join(errors) or f"Snapshot '{snap_name}' not found."}
            return {"success": True, "message": f"Snapshot '{snap_name}' deleted."}
