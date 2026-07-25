"""
qemu_host_utils.py — Host/QEMU probing utilities.

Standalone helpers used around QEMU arg building but not tied to a builder
instance: parse the qemu binary version, warn on old versions, find a free TCP
port, and discover ISO search directories. Split out of qemu_arg_builder.py,
which re-exports them so its importers are unchanged.
"""
import json
import os
import re
import socket
import subprocess
import tempfile
from typing import List, Tuple

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)
_PORTS               = _CFG["ports"]
_TIMEOUTS            = _CFG["timeouts"]

# Port-pool bases live here (next to next_free_port / _port_free) so the qemu_arg_builder
# mixins can import them without a cycle back to qemu_arg_builder. qemu_arg_builder re-exports
# them for its long-standing importers (_vm_lifecycle, _vm_runtime).
VNC_PORT_START       = _PORTS["vnc_start"]
SPICE_PORT_START     = _PORTS["spice_start"]
PORT_RANGE           = _PORTS["port_range"]
PORT_RANGE           = _PORTS["port_range"]
_ISO_DESKTOP_SUBDIRS = set(_CFG["iso_desktop_subdirs"])
_ISO_HOME_SUBDIRS    = _CFG["iso_home_subdirs"]


def _parse_qemu_version(binary: str = "qemu-system-x86_64") -> Tuple[int, int, int]:
    """Return the QEMU version as ``(major, minor, patch)``.

    Args:
        binary: QEMU binary to query (default ``qemu-system-x86_64``).

    Returns:
        Version tuple, or ``(0, 0, 0)`` if detection fails.

    Example::

        _parse_qemu_version()         # → (8, 2, 1)  on a typical Ubuntu 24.04
        _parse_qemu_version("qemu-system-aarch64")  # → (8, 2, 1)
        _parse_qemu_version("missing-binary")       # → (0, 0, 0)
    """
    try:
        r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=_TIMEOUTS["qemu_version"])
        m = re.search(r"version (\d+)[.](\d+)[.](\d+)", r.stdout)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
    except Exception:
        pass  # qemu --version unparseable/absent — caller falls back to a default below
    return (0, 0, 0)


QEMU_VERSION: Tuple[int, int, int] = _parse_qemu_version()


def qemu_version_warn() -> None:
    """Print a Rich warning panel for known version-specific issues."""
    major, minor, patch = QEMU_VERSION
    ver_str = f"{major}.{minor}.{patch}" if QEMU_VERSION != (0, 0, 0) else "unknown"
    warnings = []

    if QEMU_VERSION == (0, 0, 0):
        warnings.append("QEMU version could not be detected — some features may not work")
    if major >= 7:
        warnings.append(
            f"QEMU {ver_str}: 'vgamem_mb' property removed — "
            "virtio-vga 'vgamem_mb' property removed — resolution set via xres/yres (handled automatically)"
        )
    if major >= 6:
        warnings.append(
            f"QEMU {ver_str}: '-accel kvm' conflicts with '-machine accel=kvm' "
            "— using -enable-kvm only (handled automatically)"
        )
    if major >= 7:
        warnings.append(
            f"QEMU {ver_str}: PulseAudio backend may need pipewire-pulse — "
            "falling back to 'none' if pa fails"
        )

    if warnings:
        from rich.console import Console as _Con
        from rich.panel   import Panel   as _Pan
        _c = _Con()
        body = "\n".join(f"  [yellow]warn[/yellow] {w}" for w in warnings)
        _c.print(_Pan(
            body,
            title=f"[bold yellow]QEMU {ver_str} Compatibility Notes[/bold yellow]",
            border_style="yellow",
        ))


def _port_free(port: int) -> bool:
    """Check whether a localhost TCP port is available.

    Args:
        port: Port number to probe.

    Returns:
        ``True`` if nothing is listening on 127.0.0.1:port; ``False`` if
        the port is bound.

    Example::

        _port_free(5900)  # → True if no VNC server is running
        _port_free(22)    # → False on a typical Linux machine (sshd)
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) != 0


def next_free_port(start: int, used: List[int]) -> int:
    """Return the first port ≥ start that is not in *used* and is not actively bound.

    Args:
        start: Lowest port number to try.
        used:  Ports already assigned to existing VMs.

    Returns:
        A free port number.

    Raises:
        RuntimeError: If no free port is found in the search range.

    Example::
        >>> next_free_port(5900, [5900, 5901])
        5902
    """
    for p in range(start, start + PORT_RANGE):
        if p not in used and _port_free(p):
            return p
    raise RuntimeError(f"No free port found starting from {start}")


def build_iso_search_dirs() -> List[str]:
    """Build ISO search dirs dynamically — handles capital/lowercase variants."""
    home = os.path.expanduser("~")
    dirs: List[str] = []

    # Home subdirectories and one level deep inside them for named ISO folders
    for sub in _ISO_HOME_SUBDIRS:
        p = os.path.join(home, sub)
        if not os.path.isdir(p):
            continue
        if p not in dirs:
            dirs.append(p)
        try:
            for entry in os.listdir(p):
                full = os.path.join(p, entry)
                if os.path.isdir(full) and entry.lower() in _ISO_DESKTOP_SUBDIRS and full not in dirs:
                    dirs.append(full)
        except PermissionError:
            pass  # ISO search dir not readable — skip it

    # System-wide mount points: /media/<user>/<device>, /mnt/<device>, /run/media/<user>/<device>
    for mount_root in _CFG.get("iso_mount_roots", []):
        if not os.path.isdir(mount_root):
            continue
        try:
            for top in sorted(os.listdir(mount_root)):
                top_path = os.path.join(mount_root, top)
                if not os.path.isdir(top_path):
                    continue
                # /media/<user>/<device> layout — descend one more level
                try:
                    children = [os.path.join(top_path, c) for c in os.listdir(top_path)
                                if os.path.isdir(os.path.join(top_path, c))]
                except PermissionError:
                    children = []
                targets = children if children else [top_path]
                for t in targets:
                    if t not in dirs:
                        dirs.append(t)
        except PermissionError:
            pass  # ISO search dir not readable — skip it

    dirs.append(tempfile.gettempdir())
    return dirs

