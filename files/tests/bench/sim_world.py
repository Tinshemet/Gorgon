"""SimWorld — a faithful in-memory stand-in for the executor, for benchmarking the planner.

The ladder measures the REASONING harness, not qemu: a run must be repeatable, free, and
fast, and must never touch the operator's real ~/.gorgon. So the bench swaps the executor
for this world, which speaks the SAME tool names and argument names as `tools.json` and
returns the SAME result shapes the findings layer reads (`all_reachable` off a fleet ping,
`success` off guest_ping). Everything else about the run is the real thing — the real
model, the real tool schemas, the real Engine.

The world is also the SSOT for the ladder's own pass/fail: `reach()` is called both by the
`fleet ping` tool AND by the rung-4 checker, so the benchmark can't grade a goal by a
weaker rule than the one the system was graded by at runtime (the bug that let 5-on-netA +
5-on-netB score as a mesh).

SIMPLIFICATION, on the record: reachability ignores run status — VMs sharing a network are
reachable whether or not they're launched. The ladder's goals never ask for a launch, and
requiring one would measure a different thing than the set-tracking this ladder targets.
"""
from typing import Any, Dict, List, Optional, Set


class SimWorld:
    """The lab: VMs (status/labels/networks) and isolated networks, driven by tool calls."""

    def __init__(self) -> None:
        self.vms: Dict[str, Dict[str, Any]] = {}
        self.nets: Set[str] = set()
        self.snapshots: Dict[str, Dict[str, Any]] = {}   # a THIRD resource kind (rung 12)
        # VMs that do not answer a ping. Knowable only by asking — see _t_guest_ping.
        self.unreachable: Set[str] = set()
        self.calls: List[Dict[str, Any]] = []       # every tool call, in order (the run's cost)

    def names(self) -> Set[str]:
        """Every resource that exists, for grounding a program's `FROM` before it runs."""
        return set(self.vms) | set(self.nets) | set(self.snapshots)

    # ── the reach predicate (SSOT: the fleet tool AND the rung checker both use it) ──
    def members(self, label: str) -> List[str]:
        return sorted(n for n, v in self.vms.items() if label in v["labels"])

    def common_networks(self, names: List[str]) -> Set[str]:
        """The networks EVERY named VM is on — non-empty ⇔ they can reach each other."""
        if not names:
            return set()
        common = set(self.vms[names[0]]["nets"])
        for n in names[1:]:
            common &= self.vms[n]["nets"]
        return common

    def reach(self, label: str, minimum: int = 2) -> bool:
        """True ⇔ at least `minimum` VMs carry `label` and ALL of them share one network.
        Counting netted VMs and labelled VMs independently is NOT this: that passes a split
        fleet with zero reachable pairs."""
        m = self.members(label)
        return len(m) >= minimum and bool(self.common_networks(m))

    # ── the executor surface ──
    @classmethod
    def tools(cls) -> tuple:
        """Every tool this world actually simulates, read off its own handlers.

        Derived, never listed: `execute` dispatches to `_t_<tool>`, so the handlers ARE
        the set. A hand-written copy elsewhere drifts the moment a handler is added or
        renamed, and a probe offering a tool the world cannot run would be testing the
        wrong thing — it would look like a model failure.
        """
        return tuple(sorted(n[3:] for n in dir(cls) if n.startswith("_t_")))

    def execute(self, tool: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        self.calls.append({"tool": tool, "args": args})
        fn = getattr(self, f"_t_{tool}", None)
        if fn is None:
            # Unknown/unsimulated tool: fail LOUDLY rather than returning a bogus success —
            # a silent True would let a run "pass" a rung on a tool the world never modelled.
            return {"success": False, "error": f"{tool} is not simulated by the bench world"}
        return fn(args)

    def _vm(self, args: Dict[str, Any]) -> Optional[str]:
        return args.get("name") or args.get("vm_name")

    def _t_create_vm(self, a):
        n = self._vm(a)
        if not n:
            return {"success": False, "error": "name is required"}
        if n in self.vms:
            # The REAL create_vm refuses: executor/api/_vm_lifecycle.py returns
            # {"success": False, "error": "VM 'x' already exists — delete it first."}
            # This used to answer success with a note, under a comment claiming that was
            # what the real one did. It is not, and the lie mattered: it made re-running a
            # program look free and idempotent when in production every creation fails.
            # A sim that is kinder than the world it stands in measures nothing.
            return {"success": False, "error": f"VM '{n}' already exists — delete it first."}
        self.vms[n] = {"status": "stopped", "labels": set(), "nets": set()}
        return {"success": True, "name": n}

    def _t_clone_vm(self, a):
        # `source_name` is what the REAL clone_vm takes; the others are spellings the
        # model has reached for. Accepting the real one matters most — the sim silently
        # refusing a correctly-formed call would look like a language bug.
        src = a.get("source_name") or a.get("name") or a.get("source")
        dst = a.get("new_name") or a.get("clone_name") or a.get("target")
        if src not in self.vms:
            return {"success": False, "error": f"no VM named {src}"}
        if not dst:
            return {"success": False, "error": "new_name is required"}
        rec = self.vms[src]
        self.vms[dst] = {"status": "stopped", "labels": set(rec["labels"]), "nets": set(rec["nets"])}
        return {"success": True, "name": dst}

    def _t_delete_vm(self, a):
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        del self.vms[n]
        return {"success": True}

    def _t_launch_vm(self, a):
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        self.vms[n]["status"] = "running"
        return {"success": True, "status": "running"}

    def _t_stop_vm(self, a):
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        self.vms[n]["status"] = "stopped"
        return {"success": True, "status": "stopped"}

    def _t_create_network(self, a):
        net = a.get("net_name") or a.get("network")
        if not net:
            return {"success": False, "error": "net_name is required"}
        if net in self.nets:                       # network_manager.py:62 says the same
            return {"success": False, "error": f"Network '{net}' already exists."}
        self.nets.add(net)
        return {"success": True, "net_name": net}

    def _t_add_vm_to_network(self, a):
        net = a.get("net_name") or a.get("network")
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        if net not in self.nets:
            return {"success": False, "error": f"no network named {net}"}
        self.vms[n]["nets"].add(net)
        return {"success": True}

    def _t_remove_vm_from_network(self, a):
        """The granular inverse of the attach — one VM off one network, the rest kept.
        Mirrors the real tool's shape: an unknown VM or network is an error, and a VM
        that simply is not on that network is a successful no-op, not a failure."""
        net = a.get("net_name") or a.get("network")
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        if net not in self.nets:
            return {"success": False, "error": f"no network named {net}"}
        self.vms[n]["nets"].discard(net)
        return {"success": True}

    def _t_add_label(self, a):
        n, label = self._vm(a), a.get("label")
        if n not in self.vms:
            return {"success": False, "error": f"no VM named {n}"}
        if not label:
            return {"success": False, "error": "label is required"}
        self.vms[n]["labels"].add(label)
        return {"success": True}

    def _t_remove_label(self, a):
        n, label = self._vm(a), a.get("label")
        if n in self.vms:
            self.vms[n]["labels"].discard(label)
        return {"success": True}

    def _t_list_vms(self, a):
        label = a.get("label")
        names = self.members(label) if label else sorted(self.vms)
        return {"success": True, "vms": [{"name": n, "status": self.vms[n]["status"],
                                          "labels": sorted(self.vms[n]["labels"]),
                                          "networks": sorted(self.vms[n]["nets"])} for n in names]}

    def _t_list_networks(self, a):
        # Row shape matches the real executor's (name + members) — the Active Library and
        # the planner's state check both read membership off these rows.
        return {"success": True, "networks": [
            {"name": n, "members": sorted(v for v, r in self.vms.items() if n in r["nets"])}
            for n in sorted(self.nets)]}

    def _t_guest_ping(self, a):
        """Reachability, which a program can only learn by ASKING.

        A VM in `unreachable` answers False. That set is deliberately not exposed as a
        queryable attribute: rung 11 exists to test acting on a CALL RESULT, and if the
        answer could be reached with a SELECT the rung would silently become another
        filtered collective. The world knows; the registry does not.
        """
        n = self._vm(a)
        if n not in self.vms:
            return {"success": False, "error": f"no vm {n}"}
        # A ping that reports "not reachable" has SUCCEEDED — it ran and produced an
        # answer. Returning success:False for a negative answer conflates "the call
        # failed" with "the answer is no", which is the same conflation the codebase
        # already refuses elsewhere: success means the command RAN, not that the goal is
        # met. It also makes a program that correctly branches on the answer look like a
        # program whose calls failed.
        # `alive` is the key the REAL guest_ping returns. The sim said `reachable`, so a
        # program written and verified here would have read a field that does not exist in
        # production and branched wrong — silently, since a missing key is just falsy.
        # A bench that speaks a different vocabulary than the tool it stands in for is
        # worse than no bench: it certifies programs that cannot work.
        alive = n not in self.unreachable
        return {"success": True, "name": n, "alive": alive, "reachable": alive}

    def _t_snapshot_create(self, a):
        """A third resource kind. The whole point of rung 12: the design claims a new kind
        is one manifest row and zero language code, and until something other than vm and
        network exists that claim is untested."""
        vm, snap = self._vm(a), a.get("snap_name")
        if vm not in self.vms:
            return {"success": False, "error": f"no vm {vm}"}
        if not snap:
            return {"success": False, "error": "snap_name is required"}
        self.snapshots[snap] = {"vm": vm}
        return {"success": True, "snap_name": snap, "vm": vm}

    def _t_snapshot_list(self, a):
        return {"success": True, "snapshots": [{"snap_name": k, **v}
                                               for k, v in sorted(self.snapshots.items())]}

    def _t_fleet(self, a):
        """The real fleet tool's shape: per-member results plus the `all_reachable` value
        the findings schema turns into the fact mesh(<label>)."""
        label, action = a.get("label"), a.get("action")
        m = self.members(label)
        if not m:
            return {"success": False, "error": f"no VMs carry the label {label}"}
        if action == "ping":
            ok = self.reach(label)
            return {"success": True, "label": label, "action": "ping", "all_reachable": ok,
                    "results": [{"name": n, "reachable": ok} for n in m]}
        if action == "status":
            return {"success": True, "results": [{"name": n, "status": self.vms[n]["status"]} for n in m]}
        if action in ("launch", "stop"):
            for n in m:
                self.vms[n]["status"] = "running" if action == "launch" else "stopped"
            return {"success": True, "results": [{"name": n, "ok": True} for n in m]}
        return {"success": False, "error": f"action {action} is not simulated"}

    # ── grounding for the planner ──
    def vms_getter(self) -> Dict[str, Dict[str, Any]]:
        """The Active-Library shape run_autonomous grounds planning in. Deliberately does
        NOT expose network membership: the real LIBRARY.vms record doesn't either (nets
        live in its own compartment, reached via list_networks), and a bench that hands the
        planner a field production lacks would test a system that doesn't exist."""
        return {n: {"status": v["status"], "labels": sorted(v["labels"]), "flags": []}
                for n, v in self.vms.items()}

    def summary(self) -> str:
        return (f"{len(self.vms)} vms {sorted(self.vms)} | nets {sorted(self.nets)} | "
                f"{len(self.calls)} calls")
