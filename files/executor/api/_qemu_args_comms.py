"""
_qemu_args_comms.py — QemuArgBuilder QMP/QGA/serial-agent/monitor/serial channel args.
"""
import json
import os
import socket
import struct
import sys

from .qemu_host_utils import next_free_port

with open(os.path.join(os.path.dirname(__file__), "config.json")) as _f:
    _CFG = json.load(_f)


class _ArgsCommsMixin:
    """_qemu_args_comms.py — QemuArgBuilder QMP/QGA/serial-agent/monitor/serial channel args."""

    def _qmp(self) -> None:
        """Append QMP chardev/mon args; Unix socket on Linux/macOS, TCP on Windows."""
        if sys.platform == "win32":
            port = self.cfg.qmp_tcp_port or next_free_port(
                _CFG["ports"].get("qmp_port_start", 9000), []
            )
            self.cfg.qmp_tcp_port = port
            self.cfg.qmp_socket   = f"tcp:127.0.0.1:{port}"
            self.args += [
                "-chardev", f"socket,id=qmp,host=127.0.0.1,port={port},server=on,wait=off",
                "-mon",     "chardev=qmp,mode=control,pretty=off",
            ]
        else:
            sock = os.path.join(self.vm_dir, "qmp.sock")
            self.cfg.qmp_socket = sock
            self.args += [
                "-chardev", f"socket,id=qmp,path={sock},server=on,wait=off",
                "-mon",     "chardev=qmp,mode=control,pretty=off",
            ]

    def _qga(self) -> None:
        """Append the qemu-guest-agent virtio-serial channel — non-stealth VMs only.

        Opt-in (``cfg.guest_agent``) and OFF for stealth VMs (the virtio-serial
        device is a hypervisor tell; stealth VMs get a serial-console channel via
        ``_serial_agent()`` instead). Gives the agent its OWN virtio-serial
        controller (not shared with the SPICE vdagent bus) exposing a port named
        ``org.qemu.guest_agent.0`` — the fixed name the ``qemu-ga`` daemon expects.
        Mirrors ``_qmp()``'s Unix-socket / Windows-TCP split.
        """
        if not self.cfg.guest_agent or self.cfg.stealth or self.is_arm:
            return
        if sys.platform == "win32":
            port = self.cfg.qga_tcp_port or next_free_port(
                _CFG["ports"].get("qga_port_start", 9300), []
            )
            self.cfg.qga_tcp_port = port
            self.cfg.qga_socket   = f"tcp:127.0.0.1:{port}"
            chardev = f"socket,id=qga0,host=127.0.0.1,port={port},server=on,wait=off"
        else:
            sock = os.path.join(self.vm_dir, "qga.sock")
            self.cfg.qga_socket = sock
            chardev = f"socket,id=qga0,path={sock},server=on,wait=off"
        self.args += [
            "-device",  "virtio-serial-pci,id=qga",
            "-chardev", chardev,
            "-device",  "virtserialport,bus=qga.0,chardev=qga0,name=org.qemu.guest_agent.0",
        ]

    def _serial_agent(self) -> None:
        """Append a second plain UART (COM2) as the stealth guest-agent channel.

        Mutually exclusive with ``_qga()`` by construction — stealth VMs skip
        virtio-serial entirely (a hypervisor tell) and instead get a second
        ``-serial`` flag, the exact same device class as ``_serial()``'s COM1
        console, so nothing about this port's hardware signature differs from
        a real second UART. The wire protocol spoken over it (PSK-authenticated
        JSON lines) lives in ``serial_agent_client.py`` / the guest-side daemon
        from ``_vm_guest.py``, not here — this method only wires the transport.
        """
        if not self.cfg.guest_agent or not self.cfg.stealth or self.is_arm:
            return
        if sys.platform == "win32":
            port = self.cfg.serial_agent_tcp_port or next_free_port(
                _CFG["ports"].get("serial_agent_port_start", 9400), []
            )
            self.cfg.serial_agent_tcp_port = port
            self.cfg.serial_agent_socket   = f"tcp:127.0.0.1:{port}"
            self.args += ["-serial", f"telnet:127.0.0.1:{port},server,nowait"]
        else:
            sock = self.cfg.get_serial_agent_socket()
            self.cfg.serial_agent_socket = sock
            self.args += ["-serial", f"unix:{sock},server,nowait"]

    def _monitor(self) -> None:
        """Append human-monitor chardev/mon args; Unix socket on Linux/macOS, TCP on Windows."""
        if sys.platform == "win32":
            port = self.cfg.monitor_tcp_port or next_free_port(
                _CFG["ports"].get("monitor_port_start", 9100), []
            )
            self.cfg.monitor_tcp_port = port
            self.cfg.monitor_socket   = f"tcp:127.0.0.1:{port}"
            self.args += [
                "-chardev", f"socket,id=mon,host=127.0.0.1,port={port},server=on,wait=off",
                "-mon",     "chardev=mon,mode=readline",
            ]
        else:
            sock = os.path.join(self.vm_dir, "monitor.sock")
            self.cfg.monitor_socket = sock
            self.args += [
                "-chardev", f"socket,id=mon,path={sock},server=on,wait=off",
                "-mon",     "chardev=mon,mode=readline",
            ]

    def _serial(self) -> None:
        """Append a serial console (Unix socket on Linux/macOS, TCP telnet on Windows)."""
        if sys.platform == "win32":
            port = self.cfg.serial_tcp_port or next_free_port(
                _CFG["ports"].get("serial_port_start", 9200), []
            )
            self.cfg.serial_tcp_port = port
            self.args += ["-serial", f"telnet:127.0.0.1:{port},server,nowait"]
        else:
            sock = os.path.join(self.vm_dir, "serial.sock")
            self.args += ["-serial", f"unix:{sock},server,nowait"]
