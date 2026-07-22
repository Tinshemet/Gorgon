"""test_active_library_remote.py — the split-mode Active Library fix.

Regression guard for the "AI list_vms returns empty after a mid-session server restart on the
split rig" bug: in split mode the orchestrator's in-process manager scans its own empty
~/.gorgon, so the library must pull the registry from the executor over the wire instead.
"""
import orchestrator.executor_client as ec
from orchestrator.ai.active_library import ActiveLibrary, _remote_mode


_FAKE_VMS = [
    {"name": "box",   "os": "linux",   "status": "running", "cpu_cores": 2,
     "memory_mb": 4096, "disks": 1, "flags": ["stealth"], "labels": []},
    {"name": "win11", "os": "windows", "status": "stopped", "memory_mb": 8192, "disks": 1},
]


def test_remote_snapshot_pulls_from_executor(monkeypatch):
    monkeypatch.setattr(ec, "API_URL", "http://executor:8001")
    monkeypatch.setattr(ec, "execute_tool",
                        lambda tool, args, **kw: (_FAKE_VMS if tool == "list_vms" else []))
    assert _remote_mode() is True

    lib = ActiveLibrary().snapshot()
    assert lib.built is True
    assert set(lib._vms) == {"box", "win11"}
    assert lib._vms["box"]["status"] == "running"
    assert lib._vms["box"]["os_type"] == "linux"

    digest = lib.ai_digest()          # the AI grounds on this — must show the VMs
    assert "box" in digest and "win11" in digest


def test_remote_snapshot_tolerates_executor_failure(monkeypatch):
    """A failed executor call leaves the registry empty, not raising (built stays True)."""
    monkeypatch.setattr(ec, "API_URL", "http://executor:8001")
    def _boom(tool, args, **kw):
        raise RuntimeError("executor unreachable")
    monkeypatch.setattr(ec, "execute_tool", _boom)

    lib = ActiveLibrary().snapshot()
    assert lib.built is True and lib._vms == {}


def test_local_mode_unaffected(monkeypatch):
    monkeypatch.setattr(ec, "API_URL", "local")
    assert _remote_mode() is False
    lib = ActiveLibrary().snapshot()   # uses the in-process manager
    assert isinstance(lib._vms, dict)  # no crash; local path intact
