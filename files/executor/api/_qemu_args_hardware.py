"""
_qemu_args_hardware.py — QemuArgBuilder machine/cpu/memory/firmware/disks/network args.
"""
import json
import os
import socket

from .qemu_config import BIOS_OPTIONS, CPU_PRESETS, NetworkConfig, OVMF

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)


class _ArgsHardwareMixin:
    """_qemu_args_hardware.py — QemuArgBuilder machine/cpu/memory/firmware/disks/network args."""

    def _machine(self) -> None:
        """Append -machine (with KVM/IOMMU/OEM overrides) and -rtc."""
        machine_str = self.cfg.machine_type
        extras = []
        if self.cfg.kvm and not self.is_arm:
            extras.append("accel=kvm")
        if self.cfg.iommu and not self.is_arm:
            extras.append("kernel_irqchip=on")
        # Override ACPI OEM ID (defaults to "BOCHS  ") to match the declared
        # manufacturer — inxi and systemd-detect-virt can read ACPI table headers.
        if self.cfg.manufacturer and not self.is_arm:
            # Commas in -machine option values inject extra directives.
            oem_id = self.cfg.manufacturer.replace(",", "")[:6].ljust(6)
            extras.append(f"x-oem-id={oem_id}")
            if self.cfg.product_name:
                oem_table = (self.cfg.product_name.replace(",", "").replace(" ", ""))[:8]
                extras.append(f"x-oem-table-id={oem_table}")
        if extras:
            machine_str += "," + ",".join(extras)
        self.args += ["-machine", machine_str]
        if self.cfg.hpet and not self.is_arm:
            self.args += ["-device", "hpet"]
        if not self.is_raspi:
            # 'host' is NOT a valid -rtc base value — use 'utc' instead
            rtc_base = self.cfg.rtc_clock
            if rtc_base not in ("utc", "localtime") and not rtc_base[0].isdigit():
                rtc_base = _CFG["machine_config_defaults"]["rtc_base_fallback"]
            self.args += ["-rtc", f"base={rtc_base},driftfix=slew"]

    def _cpu(self) -> None:
        """Append -cpu (with feature flags) and -smp topology."""
        cpu_str  = CPU_PRESETS.get(self.cfg.cpu_model, self.cfg.cpu_model)
        cpu_name = cpu_str.replace("-cpu ", "").split(",")[0]
        features = list(self.cfg.cpu_features)
        if self.cfg.kvm_pv_features and not self.is_arm and "kvm=off" not in features:
            features.append("+kvm_pv_unhalt")
        feature_str = "".join(f",{f}" for f in features)
        self.args += ["-cpu", f"{cpu_name}{feature_str}"]
        self.args += [
            "-smp",
            f"cores={self.cfg.cpu_cores},"
            f"threads={self.cfg.cpu_threads},"
            f"sockets={self.cfg.cpu_sockets},"
            f"maxcpus={self.cfg.cpu_cores * self.cfg.cpu_threads * self.cfg.cpu_sockets}",
        ]

    def _memory(self) -> None:
        """Append -m, optional hugepages path, and the virtio balloon device."""
        self.args += ["-m", str(self.cfg.memory_mb)]
        if self.cfg.hugepages and not self.is_arm:
            self.args += ["-mem-path", self.cfg.hugepages_path, "-mem-prealloc"]
        if self.cfg.balloon and not self.is_raspi:
            self.args += ["-device", "virtio-balloon-pci"]

    def _firmware(self) -> None:
        """Append OVMF code + vars pflash drives (x86 only; no-op on ARM)."""
        if self.is_arm:
            return
        bios_path = BIOS_OPTIONS.get(self.cfg.bios) or OVMF.get("code")
        if bios_path and os.path.exists(bios_path):
            self.args += ["-drive", f"if=pflash,format=raw,readonly=on,file={bios_path}"]
            vars_path = self.cfg.uefi_vars
            if not vars_path or not os.path.exists(vars_path):
                for candidate in [
                    os.path.join(self.vm_dir, "OVMF_VARS.fd"),
                    os.path.join(self.vm_dir, "OVMF_VARS_4M.fd"),
                ]:
                    if os.path.exists(candidate):
                        vars_path = candidate
                        break
            if vars_path and os.path.exists(vars_path):
                self.args += ["-drive", f"if=pflash,format=raw,file={vars_path}"]


    def _disks(self) -> None:
        """Append disk drives (SD for raspi; virtio/NVMe/SCSI/IDE for x86) and the ISO cdrom."""
        if self.is_raspi:
            # raspi3b ONLY accepts SD card interface
            for disk in self.cfg.disks:
                disk_path = os.path.expanduser(disk.path)
                self.args += ["-drive", f"file={disk_path},format={disk.format},if=sd,index=0"]
            return

        has_scsi = any(d.bus == "scsi" for d in self.cfg.disks)
        has_sata = any(d.bus == "sata" for d in self.cfg.disks)
        if has_scsi:
            self.args += ["-device", "virtio-scsi-pci,id=scsi0"]
        if has_sata:
            self.args += ["-device", "ich9-ahci,id=ahci"]
        for i, disk in enumerate(self.cfg.disks):
            self.args += disk.to_qemu_args(i)
        if self.cfg.iso_path:
            self.args += [
                "-drive",  f"file={self.cfg.iso_path},if=none,id=cdrom0,readonly=on,media=cdrom",
                "-device", f"ide-cd,drive=cdrom0,bootindex=1,model={_CFG['cdrom_model']}",
            ]
            if not self.cfg.uefi:
                # Legacy BIOS only — UEFI uses bootindex and ignores -boot order
                self.args += ["-boot", f"order={self.cfg.boot_order},menu=on"]
        else:
            if not self.cfg.uefi:
                self.args += ["-boot", "order=c,menu=on"]
        # Unattended Windows install: attach the generated answer-file CD so
        # Windows Setup runs fully hands-off. Opt-in; the ISO is built at
        # create_vm time into the VM dir. Inert if the ISO isn't present.
        if self.cfg.unattended:
            unattend_iso = os.path.join(self.vm_dir, "autounattend.iso")
            if os.path.exists(unattend_iso):
                # The install ISO already holds the single default-IDE unit, so put
                # the answer CD on the AHCI controller (present for Windows' SATA
                # disk) at the port after the disks. Falls back to plain ide-cd only
                # if there's no AHCI controller (non-Windows edge case).
                n_sata = sum(1 for d in self.cfg.disks if d.bus == "sata")
                dev = f"ide-cd,drive=cdrom_ua,bus=ahci.{n_sata}" if has_sata else "ide-cd,drive=cdrom_ua"
                self.args += [
                    "-drive",  f"file={unattend_iso},if=none,id=cdrom_ua,readonly=on,media=cdrom",
                    "-device", dev,
                ]
        # Unattended Linux (casper family — Ubuntu/Mint) install: attach the
        # generated cidata volume so cloud-init's autoinstall runs hands-off up
        # to account creation. Opt-in; built at create_vm time into the VM dir.
        # Inert if absent — debian-installer family (Kali) injects its preseed
        # into the initrd instead and never creates this file.
        if self.cfg.unattended:
            cidata_iso = os.path.join(self.vm_dir, "cidata.iso")
            if os.path.exists(cidata_iso):
                # q35's default ide.0 (where cdrom0 lands) is a single-unit bus —
                # a second bare ide-cd collides on it ("bus supports only 1
                # units"). ide.1 is q35's other independent single-unit legacy
                # IDE channel, confirmed free.
                self.args += [
                    "-drive",  f"file={cidata_iso},if=none,id=cdrom_cidata,readonly=on,media=cdrom",
                    "-device", "ide-cd,drive=cdrom_cidata,bus=ide.1",
                ]

    def _network(self) -> None:
        """Append network args from each NetworkConfig, falling back to default user-NAT."""
        if not self.cfg.networks:
            net = NetworkConfig(manufacturer_hint=self.cfg.manufacturer)
            self.args += net.to_qemu_args()
            return
        for net in self.cfg.networks:
            self.args += net.to_qemu_args()
