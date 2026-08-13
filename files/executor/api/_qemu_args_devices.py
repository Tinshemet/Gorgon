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


def effective_gpu_device(cfg) -> str:
    """Return the display device the guest will ACTUALLY see, or "" for none.

    The SSOT for the emulated-GPU choice: ``_display()`` emits it and
    ``executor/fingerprint.py`` scores it. Reading ``cfg.gpu`` alone is wrong and
    was a real audit bug — the default ``"none"`` does not mean "no GPU", it means
    "let the builder pick", and the builder always emits a device.

    Example::
        effective_gpu_device(cfg)   # cfg.gpu="none", cfg.stealth=True  -> "VGA"
    """
    # getattr throughout: fingerprint.py scores configs loaded straight off disk,
    # which may predate any of these fields.
    if getattr(cfg, "gpu_passthrough_pci", ""):
        return "vfio-pci"                       # a REAL GPU; not emulated
    if getattr(cfg, "display", "") == "none":
        return ""                               # -nographic: no display device
    if getattr(cfg, "gpu", "none") == "none":
        # Stealth (both OSes): std VGA. Its PCI ID 1234:1111 is readable as QEMU,
        #   which is the price; every alternative is worse.
        #   NOT vmware-svga: vmwgfx binds the device, deactivates the VGA console,
        #   THEN rejects it ("running on an unsupported hypervisor") and unbinds.
        #   No DRM node is ever created, so systemd-logind reports CanGraphical=no
        #   and no display manager will ever start X — the guest boots headless with
        #   a black screen. Measured on Kali 6.18: /sys/class/drm holds only
        #   `version`, vmwgfx sits at 0 users, lightdm waits forever. Guests do not
        #   ship xserver-xorg-video-vmware either, so X had no driver regardless.
        #   std VGA binds bochs-drm, which yields a real DRM node.
        # Windows stealth additionally avoids "VMware SVGA" in Device Manager.
        # Non-stealth: cirrus-vga (loads cirrus_qemu, reveals hypervisor via lsmod).
        return "VGA" if getattr(cfg, "stealth", False) else "cirrus-vga"
    _g = getattr(cfg, "gpu", "none")
    return GPU_PRESETS.get(_g) or str(_g)


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
            # Choice + rationale live in effective_gpu_device() so the fingerprint
            # audit scores the same device this emits.
            self.args += ["-device", effective_gpu_device(self.cfg)]

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
        """Append the NEC xHCI controller and, on non-stealth VMs, USB HID input.

        STEALTH EMITS NO USB HID AT ALL, and that is the whole point. QEMU writes
        its own name into the HID USB descriptors — "QEMU USB Keyboard" and
        "QEMU USB Mouse" under vendor 0627 — and no argument renames them, so on
        a machine whose SMBIOS, ACPI, MAC, disk and CPUID are all spoofed the
        input devices still announce the hypervisor: seven lines of it in guest
        dmesg, measured on kali-testbox 2026-08-13, plus lsusb and
        /proc/bus/input/devices. Nothing can be substituted, so the fix is
        SUBTRACTIVE — drop the devices and let the machine's own i8042 carry
        input. The guest then reports "AT Translated Set 2 keyboard" and
        "ImExPS/2 Generic Explorer Mouse", which is exactly what a real laptop's
        internal keyboard and touchpad report. Both were verified present on the
        live VM (serio0/serio1, i8042 PNP0303/PNP0f13) BEFORE the USB devices
        were removed, so this trades a tell for hardware that is already there.

        NOT on ARM: the virt machine has no i8042, so removing HID there would
        leave the guest with no input at all.

        The xHCI controller stays either way — its PCI IDs are a real NEC part, a
        machine with no USB controller is odd in itself, and the unattended
        installer medium hangs off bus=usb.0.

        Non-stealth is unchanged: usb-kbd plus usb-tablet for absolute pointer
        positioning over VNC/SDL, or usb-mouse when cfg.tablet is off.
        """
        # nec-usb-xhci: NEC uPD720200 USB 3.0 (PCI 1033:0194) — real chip PCI IDs.
        # qemu-xhci uses 1b36 (Red Hat/QEMU) which inxi detects as virtual.
        self.args += ["-device", "nec-usb-xhci,id=usb"]
        if not (self.cfg.stealth and not self.is_arm):
            self.args += ["-device", "usb-kbd"]
            # ARM stealth still lands here (no i8042 to fall back to), and the
            # absolute-positioning tablet is itself a hypervisor-console
            # convention — so stealth keeps taking the relative mouse.
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
