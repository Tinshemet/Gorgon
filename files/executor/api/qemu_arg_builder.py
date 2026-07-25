"""
qemu_arg_builder.py — QEMU Argument Building Layer

Translates a MachineConfig into the full QEMU command-line argument
list. Also owns: QEMU version detection, port pool helpers, and the
ISO search-directory scanner.
"""

import glob as _glob
import json
import os
import re
import socket
import struct
import subprocess
import sys
import tempfile
from typing import List, Tuple

from .qemu_config import (
    AUDIO_PRESETS, BIOS_OPTIONS, CPU_PRESETS, GPU_PRESETS, MachineConfig, NetworkConfig, OVMF,
)
from ._qemu_smbios import _QemuSmbiosMixin
from ._qemu_args_hardware import _ArgsHardwareMixin
from ._qemu_args_devices  import _ArgsDevicesMixin
from ._qemu_args_comms    import _ArgsCommsMixin
from .qemu_host_utils import (  # host/qemu utils (extracted from this file)
    _parse_qemu_version, qemu_version_warn, _port_free,
    next_free_port, build_iso_search_dirs,
    # port-pool bases moved here (SSOT); re-exported below for existing importers
    VNC_PORT_START, SPICE_PORT_START, PORT_RANGE,
)

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)
_PORTS    = _CFG["ports"]
_TIMEOUTS = _CFG["timeouts"]

# ── QEMU Version Detection ─────────────────────────────────────────────────────


QEMU_VERSION: Tuple[int, int, int] = _parse_qemu_version()


# ── Port Pool ─────────────────────────────────────────────────────────────────
# VNC_PORT_START / SPICE_PORT_START / PORT_RANGE now live in qemu_host_utils (imported
# above) so the arg-builder mixins can use them without a cycle; re-exported here for
# _vm_lifecycle / _vm_runtime, which import them from this module.


# ── ISO Search Directory Scanner ───────────────────────────────────────────────

# Builds a list of directories to search for ISO files based on common home subdirectories.
# In: nothing → Out: List[str]
_ISO_DESKTOP_SUBDIRS = set(_CFG["iso_desktop_subdirs"])
_ISO_HOME_SUBDIRS    = _CFG["iso_home_subdirs"]


# ── QEMU Argument Builder ──────────────────────────────────────────────────────

class QemuArgBuilder(_QemuSmbiosMixin, _ArgsHardwareMixin, _ArgsDevicesMixin, _ArgsCommsMixin):
    def __init__(self, config: MachineConfig) -> None:
        """Store the config and precompute ARM/raspi detection flags."""
        self.cfg      = config
        self.vm_dir   = config.get_vm_dir()
        self.args:    List[str] = []
        self.qemu_ver = QEMU_VERSION
        self.is_arm   = config.machine_arch in ("aarch64", "arm", "armhf")
        self.is_raspi = "raspi" in config.machine_type.lower()

    def build(self) -> List[str]:
        """Build and return the full QEMU command list for this config.

        Calls every ``_*`` sub-method in order, applies hardening and extra-arg
        filtering, and returns a clean list with empty strings stripped.

        Returns:
            The complete QEMU argv starting with the binary name.

        Example::
            >>> QemuArgBuilder(cfg).build()[0]
            'qemu-system-x86_64'
        """
        self.args = [self.cfg.qemu_binary]
        self._base()
        if self.cfg.hardened and not self.is_arm:
            self._harden()
        self._machine()
        self._cpu()
        self._memory()
        if not self.is_raspi:
            self._firmware()   # raspi has its own ROM, no pflash
        self._smbios()
        self._disks()
        self._network()
        self._display()
        self._audio()
        if not self.is_raspi:
            self._usb()        # raspi machine handles USB itself
        self._battery()
        self._kernel_direct()
        self._qmp()
        self._monitor()
        self._serial()
        self._qga()
        self._serial_agent()
        if not self.is_arm:
            self._misc()       # virtio-rng not needed on ARM
        if self.cfg.tpm and not self.is_arm:
            self._tpm()
        # Drop any extra_arg that disables the seccomp sandbox when hardened.
        # The sanitizer filters AI-supplied args, but the arg_builder is the
        # last line of defense before the QEMU command is assembled.
        extra = self.cfg.extra_args
        if self.cfg.hardened and not self.is_arm:
            extra = [a for a in extra if "-sandbox" not in a and "obsolete=allow" not in a]
        self.args += extra
        return [a for a in self.args if a]

    def _base(self) -> None:
        """Append -name and (when enabled) -enable-kvm; force kvm=False for ARM."""
        self.args += ["-name", f"{self.cfg.name},process={self.cfg.name}"]
        # -enable-kvm enables KVM; accel=kvm is set in _machine() — do NOT add -accel kvm here
        if self.cfg.kvm and not self.is_arm:
            self.args += ["-enable-kvm"]
        if self.is_arm:
            self.cfg.kvm = False  # KVM never works for ARM guests on x86 host

    def _harden(self) -> None:
        """Apply CPU masking, sandbox, and network hardening; mutates self.cfg in place."""
        # Hide hypervisor CPUID bit and KVM paravirt leaves — keeps KVM perf,
        # removes the flag that tells the guest it's inside a hypervisor.
        # -vmx: remove VMX flag so kvm_intel.ko cannot load inside the guest
        # (if the guest sees vmx, it loads kvm_intel, which lsmod exposes to inxi).
        # +invtsc: advertise an invariant TSC (CPUID 80000007H:EDX[8]) like real
        # silicon. KVM masks it by default (it blocks live migration, which we
        # don't do), and its ABSENCE is a common timing-based VM tell. This does
        # NOT defeat VMEXIT-latency red-pills — that overhead is inherent to
        # hardware virtualisation — but it closes the naive "no invariant TSC" check.
        for flag in ("-hypervisor", "kvm=off", "-vmx", "+invtsc"):
            if flag not in self.cfg.cpu_features:
                self.cfg.cpu_features.append(flag)
        # cpu=host already inherits all host mitigations (ssbd, ibrs, md-clear,
        # etc.) so don't force-add them — KVM rejects flags the host doesn't
        # actually expose (e.g. spec-ctrl on Enhanced IBRS CPUs).
        # Disable memory balloon — it can leak timing information between tenants.
        self.cfg.balloon = False
        # Disable hugepages in hardened mode — cross-tenant side-channel risk.
        self.cfg.hugepages = False
        # Force NAT for hardened VMs — prevents guest from seeing or attacking
        # the LAN. Exception: stealth VMs use bridge intentionally so they get
        # a real LAN IP and don't expose the 10.0.2.x QEMU NAT subnet.
        if not self.cfg.stealth:
            for net in self.cfg.networks:
                if net.mode == "bridge":
                    net.mode = "nat"
        # QEMU seccomp sandbox — prevents the QEMU process itself from making
        # dangerous syscalls even if the guest achieves code execution in QEMU.
        self.args += [
            "-sandbox",
            "on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny",
        ]

    def _kernel_direct(self) -> None:
        """Append -kernel/-initrd/-append when direct kernel boot paths are configured."""
        if self.cfg.kernel_path:    self.args += ["-kernel", self.cfg.kernel_path]
        if self.cfg.initrd_path:    self.args += ["-initrd", self.cfg.initrd_path]
        if self.cfg.kernel_cmdline: self.args += ["-append", self.cfg.kernel_cmdline]

    def _tpm(self) -> None:
        """Append TPM chardev, tpmdev emulator, and tpm-tis device."""
        tpm_sock = os.path.join(self.cfg.get_vm_dir(), "tpm.sock")
        self.args += [
            "-chardev", f"socket,id=chrtpm,path={tpm_sock}",
            "-tpmdev",  "emulator,id=tpm0,chardev=chrtpm",
            "-device",  "tpm-tis,tpmdev=tpm0",
        ]

    def _misc(self) -> None:
        """Append virtio-rng (non-hardened), -no-reboot (ISO boot), and -no-user-config."""
        if not self.cfg.hardened:
            self.args += ["-device", "virtio-rng-pci"]
        if self.cfg.iso_path:
            self.args += ["-no-reboot"]
        self.args += ["-no-user-config"]
