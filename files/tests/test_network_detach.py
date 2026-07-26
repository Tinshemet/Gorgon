"""test_network_detach.py — the granular remove_vm_from_network inverse.

Until now `add_vm_to_network` had no per-network inverse: only
`remove_vm_from_all_networks` existed, executor-side, callable by nothing but VM
deletion. So an attach could not be undone by the agent at all, and a contract
calling the attach `reversible` was taking that on faith.

The risk lives in two places, and both are covered here:
  * a NIC is TWO list entries (-netdev <val> -device <val>), so a detach must drop
    flag+value PAIRS — dropping single entries leaves an orphaned value that
    silently corrupts the launch line;
  * the netdev id is matched on an EXACT parsed field, never a substring, or
    detaching 'lab' would tear the NIC out of 'lab2'.
"""
import os
import shutil
import tempfile

import pytest

from executor.api import qemu_config
from executor.api.network_manager import IsolatedNetManager
from executor.api.qemu_config import MachineConfig


@pytest.fixture()
def env(monkeypatch):
    """An isolated VM_BASE_DIR + networks.json, so nothing touches ~/.gorgon."""
    tmp = tempfile.mkdtemp(prefix="gorgon_detach_test_")
    monkeypatch.setattr(qemu_config, "VM_BASE_DIR", tmp)
    monkeypatch.setattr(IsolatedNetManager, "NET_FILE", os.path.join(tmp, "networks.json"))
    mgr = IsolatedNetManager()
    try:
        yield mgr, tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _vm(name, tmp):
    os.makedirs(os.path.join(tmp, name), exist_ok=True)
    cfg = MachineConfig(name=name)
    cfg.save()
    return cfg


def test_detach_removes_nic_and_membership(env):
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    assert mgr.add_vm_to_network("lab", "web")["success"]
    assert "web" in mgr._load()["lab"]["members"]

    r = mgr.remove_vm_from_network("lab", "web")
    assert r["success"], r
    assert "web" not in mgr._load()["lab"]["members"]
    assert not [a for a in MachineConfig.load("web").extra_args if "iso_lab" in a]


def test_detach_is_an_exact_round_trip(env):
    """attach → detach leaves extra_args byte-identical to where it started."""
    mgr, tmp = env
    cfg = _vm("web", tmp)
    before = list(cfg.extra_args)
    mgr.create_network("lab")
    mgr.add_vm_to_network("lab", "web")
    assert MachineConfig.load("web").extra_args != before   # the attach really did something
    mgr.remove_vm_from_network("lab", "web")
    assert MachineConfig.load("web").extra_args == before


def test_detach_leaves_other_networks_alone(env):
    """The whole point of granular detach: one network off, the rest untouched."""
    mgr, tmp = env
    _vm("web", tmp)
    for n in ("lab", "prod"):
        mgr.create_network(n)
        mgr.add_vm_to_network(n, "web")

    mgr.remove_vm_from_network("lab", "web")
    args = MachineConfig.load("web").extra_args
    assert not [a for a in args if "iso_lab," in a or a.endswith("iso_lab")]
    assert [a for a in args if "iso_prod" in a], "the prod NIC must survive"
    nets = mgr._load()
    assert "web" not in nets["lab"]["members"]
    assert "web" in nets["prod"]["members"]


def test_prefix_collision_does_not_tear_out_the_wrong_nic(env):
    """'lab' must not match 'lab2' — the substring bug this was written against."""
    mgr, tmp = env
    _vm("web", tmp)
    for n in ("lab", "lab2"):
        mgr.create_network(n)
        mgr.add_vm_to_network(n, "web")

    mgr.remove_vm_from_network("lab", "web")
    args = MachineConfig.load("web").extra_args
    assert [a for a in args if "iso_lab2" in a], "iso_lab2's NIC must survive"
    assert not [a for a in args if "id=iso_lab," in a or a.endswith("id=iso_lab")]
    assert "web" in mgr._load()["lab2"]["members"]


def test_pairs_are_dropped_never_orphaned(env):
    """A NIC is flag+value; dropping one side would leave a dangling value."""
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    mgr.add_vm_to_network("lab", "web")
    mgr.remove_vm_from_network("lab", "web")
    args = MachineConfig.load("web").extra_args
    # every flag still owns its value: no bare value left where a flag should be
    assert len(args) % 2 == 0
    assert all(a.startswith("-") for a in args[::2]), args


def test_attach_prefix_collision_really_attaches(env):
    """The attach side of the same substring bug: a VM on 'lab2' must still be
    attachable to 'lab'. The idempotency check used `netid in arg`, so 'iso_lab'
    matched 'id=iso_lab2' — the attach claimed the VM was already there, wrote the
    membership row, and never wired the NIC."""
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab2")
    mgr.create_network("lab")
    mgr.add_vm_to_network("lab2", "web")
    r = mgr.add_vm_to_network("lab", "web")
    assert r["success"], r
    assert "already" not in r["message"], "falsely reported already-attached"
    args = MachineConfig.load("web").extra_args
    assert [a for a in args if "id=iso_lab," in a or a.endswith("id=iso_lab")], \
        "the lab NIC was never actually wired"
    assert [a for a in args if "iso_lab2" in a], "the lab2 NIC must survive"
    assert "web" in mgr._load()["lab"]["members"]


def test_attach_is_still_idempotent(env):
    """The exact matcher must not break the real idempotency case."""
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    mgr.add_vm_to_network("lab", "web")
    n = len(MachineConfig.load("web").extra_args)
    r = mgr.add_vm_to_network("lab", "web")
    assert r["success"] and "already" in r["message"]
    assert len(MachineConfig.load("web").extra_args) == n, "a second NIC was appended"


def test_detach_when_not_attached_is_a_successful_noop(env):
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    r = mgr.remove_vm_from_network("lab", "web")
    assert r["success"] and "not on" in r["message"]


def test_unknown_network_and_unknown_vm_are_errors(env):
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    assert not mgr.remove_vm_from_network("nope", "web")["success"]
    assert not mgr.remove_vm_from_network("lab", "ghost")["success"]


def test_membership_without_a_nic_is_still_repaired(env):
    """The two halves are fixed on their own evidence — a phantom member is dropped
    even though there is no NIC to remove."""
    mgr, tmp = env
    _vm("web", tmp)
    mgr.create_network("lab")
    nets = mgr._load()
    nets["lab"]["members"].append("web")      # listed, but never attached
    mgr._nets = nets
    mgr._save()

    r = mgr.remove_vm_from_network("lab", "web")
    assert r["success"]
    assert "web" not in mgr._load()["lab"]["members"]


def test_tool_dispatches(env):
    """The handler is auto-discovered and routes to the manager."""
    from executor.tool_dispatch.tools import _REGISTRY
    assert "remove_vm_from_network" in _REGISTRY


def test_registry_declares_the_tool():
    from executor.command_catalog import TOOL_SPECS, VM_SCOPED_TOOLS, TOOL_EFFECTS
    spec = TOOL_SPECS["remove_vm_from_network"]
    assert spec["req"] == ["net_name", "vm_name"]
    assert "remove_vm_from_network" in VM_SCOPED_TOOLS
    assert TOOL_EFFECTS["remove_vm_from_network"] == ("networks",)


def test_contract_prices_it():
    """A mutating tool with no risk facts prices at zero — this one must not."""
    from orchestrator.ai.agent.contract import tool_risk, resolve_tier
    assert tool_risk("remove_vm_from_network") is not None
    assert resolve_tier("remove_vm_from_network") == "none"   # symmetric with the attach
