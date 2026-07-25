"""
_qemu_args_devices.py — QemuArgBuilder display/audio/usb/battery (peripheral) args.
"""
import glob as _glob
import json
import os
import subprocess
import sys
import tempfile

from .qemu_config import AUDIO_PRESETS, GPU_PRESETS, OVMF
from .qemu_host_utils import VNC_PORT_START, SPICE_PORT_START

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)
_TIMEOUTS = _CFG["timeouts"]


class _ArgsDevicesMixin:
    """_qemu_args_devices.py — QemuArgBuilder display/audio/usb/battery (peripheral) args."""

    def _gl_available(self) -> bool:
        """Check if virgl/OpenGL is actually usable before passing gl=on."""
        try:
            r = subprocess.run(
                [self.cfg.qemu_binary, "-display", "sdl,gl=on",
                 "-machine", "none", "-no-user-config"],
                capture_output=True, text=True, timeout=_TIMEOUTS["gl_check"],
            )
            err = (r.stderr or "").lower()
            return "gl" not in err and "opengl" not in err
        except Exception:
            return False

    def _display(self) -> None:
        """Append display args (SDL/GTK/SPICE/VNC/-nographic); downgrade GPU if GL is unavailable."""
        if self.is_raspi:
            self.args += ["-nographic"]  # raspi3b has NO video output in QEMU
            return
        # GPU passthrough: hand the guest a REAL GPU via vfio-pci so its /sys PCI
        # vendor/device IDs are genuine hardware — the one way to defeat the
        # "display adapter = VMware 15ad" tell that no emulated GPU can hide.
        # Requires host prep: IOMMU on, the GPU bound to vfio-pci and isolated.
        # The passed GPU drives the guest's own output, so QEMU runs headless.
        if self.cfg.gpu_passthrough_pci:
            # Comma-separated host PCI addresses (BDF). The first is the primary GPU
            # function and gets x-vga=on; the rest (e.g. the .1 HDMI-audio function,
            # or other devices in the IOMMU group) are passed as plain vfio-pci.
            addrs = [a.strip() for a in self.cfg.gpu_passthrough_pci.split(",") if a.strip()]
            for i, addr in enumerate(addrs):
                dev = f"vfio-pci,host={addr}" + (",x-vga=on" if i == 0 else "")
                self.args += ["-device", dev]
            self.args += ["-display", "none"]
            return
        gpu_device = GPU_PRESETS.get(self.cfg.gpu)
        if self.cfg.display == "none":
            self.args += ["-nographic"]
            return
        if self.cfg.gpu == "none":
            # Linux stealth: vmware-svga loads vmwgfx (no "qemu" in module name).
            # Windows stealth: std VGA — no VMware driver needed, avoids "VMware SVGA"
            #   showing up in Device Manager before any driver install.
            # Non-stealth: cirrus-vga (loads cirrus_qemu, reveals hypervisor via lsmod).
            # Bochs VGA (QEMU default) uses PCI ID 1234:1111 which inxi flags as QEMU.
            if self.cfg.stealth:
                device = "VGA" if self.cfg.os_type == "windows" else "vmware-svga"
            else:
                device = "cirrus-vga"
            self.args += ["-device", device]

        gl_wanted = self.cfg.opengl and not self.is_arm
        gl_ok     = gl_wanted and self._gl_available()
        gl_flag   = "gl=on" if gl_ok else "gl=off"

        # virtio-vga-gl requires GL; downgrade to virtio-vga when GL is off or unavailable
        if self.cfg.gpu == "virtio" and not gl_ok:
            gpu_device = "virtio-vga"

        if self.cfg.display == "sdl":
            self.args += ["-display", f"sdl,{gl_flag}"]
        elif self.cfg.display == "gtk":
            self.args += ["-display", f"gtk,{gl_flag}"]
        elif self.cfg.display == "spice":
            port = self.cfg.spice_port or SPICE_PORT_START
            self.args += [
                "-spice",   f"port={port},disable-ticketing=on",
                "-device",  "virtio-serial",
                "-chardev", "spicevmc,id=vdagent,debug=0,name=vdagent",
                "-device",  "virtserialport,chardev=vdagent,name=com.redhat.spice.0",
                "-display", "spice-app",
            ]
        elif self.cfg.display == "vnc":
            port        = self.cfg.vnc_port or VNC_PORT_START
            display_num = port - 5900
            if self.cfg.vnc_bind_local:
                # Remote mode: bind to localhost only + require password (set via QMP after boot).
                self.args += ["-vnc", f"127.0.0.1:{display_num},password=on"]
            else:
                self.args += ["-vnc", f":{display_num}"]

        if gpu_device and not self.is_raspi:
            if gpu_device == "virtio-vga-gl":
                self.args += ["-device", "virtio-vga-gl,xres=1920,yres=1080"]
            elif gpu_device == "vfio-pci":
                pci = getattr(self.cfg, "_vfio_pci", "0000:01:00.0")
                self.args += ["-device", f"vfio-pci,host={pci}"]
            else:
                # vgamem_mb removed in QEMU 7+ — don't pass it
                self.args += ["-device", gpu_device]

    def _audio(self) -> None:
        """Detect the platform audio server and append the matching -audiodev + -device."""
        if self.is_raspi:
            return
        audio_dev = AUDIO_PRESETS.get(self.cfg.audio)
        if not audio_dev:
            return

        if sys.platform == "linux":
            _tmp = tempfile.gettempdir()
            _ag = _CFG.get("audio_socket_globs", {})
            pa_running = bool(
                _glob.glob(_ag.get("pulse_unix", "/run/user/*/pulse/native")) or
                _glob.glob(os.path.join(_tmp, "pulse-*", "native"))
            )
            pw_running = bool(_glob.glob(_ag.get("pipewire", "/run/user/*/pipewire-0")))
            if pa_running:
                audiodev = "pa,id=audio0"
            elif pw_running:
                audiodev = "pipewire,id=audio0"
            else:
                return  # no audio server — skip to avoid crash
        elif sys.platform == "darwin":
            audiodev = "coreaudio,id=audio0"
        elif sys.platform == "win32":
            audiodev = "dsound,id=audio0"
        else:
            return

        self.args += ["-audiodev", audiodev, "-device", audio_dev]
        if self.cfg.audio in ("hda", "ich9"):
            self.args += ["-device", "hda-duplex,audiodev=audio0"]

    def _usb(self) -> None:
        """Append the NEC xHCI controller, USB keyboard, and pointing device.

        Stealth forces a relative ``usb-mouse`` instead of ``usb-tablet``: the
        absolute-positioning tablet is a hypervisor-console convention (bare-metal
        machines don't have one) that virt-detection reads as a VM tell. The
        tradeoff is relative pointer motion over VNC/SDL for stealth VMs.
        """
        # nec-usb-xhci: NEC uPD720200 USB 3.0 (PCI 1033:0194) — real chip PCI IDs.
        # qemu-xhci uses 1b36 (Red Hat/QEMU) which inxi detects as virtual.
        self.args += ["-device", "nec-usb-xhci,id=usb", "-device", "usb-kbd"]
        use_tablet = self.cfg.tablet and not self.cfg.stealth
        self.args += ["-device", "usb-tablet" if use_tablet else "usb-mouse"]

        # Unattended Windows: attach the FAT answer medium as a removable USB stick.
        # OVMF mounts FAT (unlike the plain answer ISO), so the UEFI shell auto-runs
        # its startup.nsh to launch the installer — the install boots hands-off.
        # Windows Setup also reads autounattend.xml off it. Attached here (after the
        # xHCI controller) so bus=usb.0 resolves. Inert if the image isn't present.
        if self.cfg.unattended:
            unattend_img = os.path.join(self.vm_dir, "autounattend.img")
            if os.path.exists(unattend_img):
                self.args += [
                    "-drive",  f"file={unattend_img},if=none,id=ua_fat,format=raw",
                    "-device", "usb-storage,drive=ua_fat,removable=on,bus=usb.0",
                ]

    def _battery(self) -> None:
        """Inject a synthetic ACPI battery + AC adapter for laptop personas.

        QEMU has no battery device, so a laptop persona otherwise exposes no
        /sys/class/power_supply/BAT0 — a clean "laptop with no battery"
        inconsistency (upower/acpi/GNOME reveal it). When cfg.battery is set
        (laptop machine_class) and the SSDT has been compiled, add it via
        -acpitable. Inert until acpi/battery.aml exists, so a missing/uncompiled
        table never risks the guest's ACPI boot.
        """
        if self.is_arm or not self.cfg.battery:
            return
        aml = os.path.join(os.path.dirname(__file__), "acpi", "battery.aml")
        if os.path.exists(aml):
            self.args += ["-acpitable", f"file={aml}"]
