"""
_qemu_smbios.py — SMBIOS / chassis identity arg building.

_QemuSmbiosMixin builds the QEMU SMBIOS override args (type-1 system info,
type-3 chassis byte, escaping, and the raw chassis binary) used for stealth
fingerprinting. Composed into QemuArgBuilder; split out to keep the builder
focused. Operates purely on builder state (self.cfg / self.args / self.vm_dir).
"""
import json
import os
import struct

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)


class _QemuSmbiosMixin:
    """Mixin: SMBIOS type-1/type-3 override args + chassis binary for stealth VMs."""

    # Adds -smbios type=0 (BIOS), type=1 (system), type=3 (chassis); skipped on ARM.
    # In: nothing → Out: appends to self.args
    def _chassis_type_byte(self) -> int:
        """Return the SMBIOS chassis-type byte for the config's smbios_type/machine_class."""
        mapping = _CFG["smbios_chassis_type_map"]
        guess = mapping.get((self.cfg.smbios_type or "").lower(), 0)
        if not guess:
            guess = mapping.get((self.cfg.machine_class or "").lower(), 3)
        return guess

    def _write_smbios_chassis_bin(self, chassis_type: int) -> str:
        """Write a raw SMBIOS type=3 structure with the given chassis_type byte.

        QEMU appends -smbios file= entries after its built-in structures.
        Linux dmi_scan overwrites dmi_chassis_type for every type=3 hit, so
        our appended entry overrides QEMU's default chassis_type=1 (Other).
        Returns the file path, or '' on failure.
        """
        if self.is_arm or not chassis_type:
            return ''
        mfr = self.cfg.manufacturer or ''
        mfr_idx = 1 if mfr else 0
        # SMBIOS type=3 header: type, length, handle, then 9 field bytes
        header = struct.pack('<BBHBBBBBBBBB',
            3, 0x0D, 0x0301,          # type, length=13, handle (unique from built-in)
            mfr_idx, chassis_type,    # manufacturer string-index, chassis_type byte
            0, 0, 0,                  # version, serial, asset (no strings)
            3, 3, 3, 3,               # boot-up, psu, thermal, security states = Safe
        )
        strings = (mfr.encode('ascii', errors='replace') + b'\x00') if mfr else b''
        strings += b'\x00'  # end-of-strings marker
        blob = header + strings

        try:
            os.makedirs(self.vm_dir, exist_ok=True)
            path = os.path.join(self.vm_dir, 'smbios_chassis.bin')
            with open(path, 'wb') as f:
                f.write(blob)
            return path
        except OSError:
            return ''

    @staticmethod
    def _smbios_escape(value: str) -> str:
        """Remove commas from a string value used in a -smbios option.

        In: "Dell, Inc." → Out: "Dell Inc."
        A comma in a -smbios value terminates the current field and starts a
        new key=value pair, allowing injection of arbitrary QEMU SMBIOS directives.
        """
        return value.replace(",", "")

    def _smbios(self) -> None:
        """Emit SMBIOS type-1 override args (manufacturer/product/serial/family)."""
        if self.is_arm:
            return
        if self.cfg.manufacturer or self.cfg.product_name:
            parts = ["type=1"]
            if self.cfg.manufacturer:  parts.append(f"manufacturer={self._smbios_escape(self.cfg.manufacturer)}")
            if self.cfg.product_name:  parts.append(f"product={self._smbios_escape(self.cfg.product_name)}")
            if self.cfg.serial_number: parts.append(f"serial={self._smbios_escape(self.cfg.serial_number)}")
            # DMI "family" is the product line (e.g. "Latitude"), NOT the hostname —
            # using the hostname here leaks "localhost" into dmidecode/inxi. Derive
            # it from the product name's leading token; omit rather than emit a tell.
            family = self.cfg.product_name.split()[0] if self.cfg.product_name else ""
            if family:                 parts.append(f"family={self._smbios_escape(family)}")
            self.args += ["-smbios", ",".join(parts)]
        if self.cfg.bios_vendor or self.cfg.bios_version:
            parts = ["type=0"]
            if self.cfg.bios_vendor:  parts.append(f"vendor={self._smbios_escape(self.cfg.bios_vendor)}")
            if self.cfg.bios_version: parts.append(f"version={self._smbios_escape(self.cfg.bios_version)}")
            self.args += ["-smbios", ",".join(parts)]
        # type=2 (baseboard): override board_vendor/board_name which default to
        # "QEMU" and "Standard PC (Q35+ICH9)" — inxi reads these via DMI and
        # uses them to identify KVM even when CPUID is hidden.
        board_vendor  = self.cfg.manufacturer
        board_product = self.cfg.board_product or self.cfg.product_name
        if board_vendor or board_product:
            parts = ["type=2"]
            if board_vendor:  parts.append(f"manufacturer={self._smbios_escape(board_vendor)}")
            if board_product: parts.append(f"product={self._smbios_escape(board_product)}")
            self.args += ["-smbios", ",".join(parts)]
        # type=3 (chassis): override chassis_vendor which defaults to "QEMU".
        # chassis_type byte is NOT settable via -smbios CLI in QEMU 8.x, so we
        # inject a raw SMBIOS type=3 binary. QEMU appends -smbios file= entries
        # AFTER its built-in structures; the Linux DMI scanner overwrites
        # dmi_chassis_type on each type=3 hit, so the last entry (ours) wins.
        chassis_type = self._chassis_type_byte()
        chassis_bin  = self._write_smbios_chassis_bin(chassis_type)
        if chassis_bin:
            # Binary already includes manufacturer; QEMU rejects both file= and
            # type=3 CLI for the same structure type simultaneously.
            self.args += ["-smbios", f"file={chassis_bin}"]
        elif self.cfg.manufacturer:
            self.args += ["-smbios", f"type=3,manufacturer={self.cfg.manufacturer}"]

