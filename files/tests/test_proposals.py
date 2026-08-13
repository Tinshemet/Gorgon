#!/usr/bin/env python3
"""
test_proposals.py — the referendum/amendment proposal lifecycle.

Proves: a typed proposal is validated on file (a malformed referendum can't even be
reviewed), pending/get/reject work, and to_rule turns a proposal into the rule inserted
into the law at the OPERATOR-assigned weight (the AI proposes a weight; the human decides).

Run:  PYTHONPATH=files python3 files/tests/test_proposals.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.agent import proposals as P

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def main():
    import shared.bundle as _bundle
    _bundle.AGENTS_ROOT = tempfile.mkdtemp()      # isolate proposal storage from ~/.gorgon

    print("validate — a typed proposal must be coherent before it's even reviewable")
    check("unknown kind rejected", P.validate("nonsense", {"x": 1}) is not None)
    check("delegation with no effect rejected", P.validate("delegation", {}) is not None)
    check("access with forbid is valid", P.validate("access", {"forbid": ["delete_vm"]}) is None)
    check("documentary 'rule' needs no effect", P.validate("rule", None) is None)
    check("access with a SCOPE is valid (K5 — a grant bounded by a context)",
          P.validate("access", {"scope": {"tools": ["scan_network"],
                                          "args": {"net_name": "lab"}}}) is None)
    check("a scope bound to an OBJECT is valid too",
          P.validate("access", {"scope": {"tools": ["delete_vm"],
                                          "object": {"kind": "vm", "label": "scratch"}}}) is None)
    check("a MALFORMED scope is refused before the operator ever sees it",
          P.validate("access", {"scope": {"tools": ["scan_network"]}}) is not None)

    print("\npropose — a referendum lands as pending; malformed is refused")
    try:
        P.propose("barenboim", kind="delegation", text="bad", effect={})
        refused = False
    except ValueError:
        refused = True
    check("malformed proposal is refused at file time", refused)

    r = P.propose("barenboim", kind="delegation", text="deleting decoys is routine → y/n",
                  effect={"tier": "normal", "tools": ["delete_vm"]}, proposed_weight=2,
                  origin="ai", prompted_by="hit the delete gate 3×", id="r-test1")
    check("proposal stored pending with its metadata",
          r["status"] == "pending" and r["origin"] == "ai" and r["proposed_weight"] == 2
          and r["prompted_by"] == "hit the delete gate 3×")

    print("\npending / get")
    check("shows in pending", [p["id"] for p in P.pending("barenboim")] == ["r-test1"])
    check("get returns it", P.get("barenboim", "r-test1")["kind"] == "delegation")
    check("per-agent isolation (another agent has none)", P.pending("doorman") == [])

    print("\nto_rule — the AI proposed 2, the OPERATOR sets the final weight")
    rule = P.to_rule(r, weight=1)
    check("becomes a {w,kind,text,effect} rule at the operator's weight",
          rule == {"w": 1, "kind": "delegation", "text": "deleting decoys is routine → y/n",
                   "effect": {"tier": "normal", "tools": ["delete_vm"]}})

    print("\nenact / reject bookkeeping")
    check("mark_enacted records the final weight", P.mark_enacted("barenboim", "r-test1", 1) is True
          and P.get("barenboim", "r-test1")["status"] == "enacted")
    check("an enacted proposal is no longer pending", P.pending("barenboim") == [])
    r2 = P.propose("barenboim", kind="access", text="allow recon", effect={"allow": ["scan_network"]}, id="r-test2")
    check("reject marks it rejected", P.reject("barenboim", "r-test2") is True
          and P.get("barenboim", "r-test2")["status"] == "rejected")
    check("reject a non-pending proposal is False", P.reject("barenboim", "r-test2") is False)

    print("\nEND-TO-END: propose → operator enacts → the LAW governs (via a versioned amend)")
    import json
    from orchestrator.ai.agent import forge as F
    from orchestrator.ai.agent.contract.core import Contract
    _files = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    g = json.load(open(os.path.join(_files, "orchestrator/ai/agent/doorman.grgn")))
    F.sign(g, "banana")
    check("before enact, create_vm is 'normal'", Contract(g, "lab", "signed").resolve_tier("create_vm") == "normal")
    prop = P.propose("lab", kind="delegation", text="create is routine here",
                     effect={"tier": "none", "tools": ["create_vm"]}, proposed_weight=2, id="r-e2e")
    rule = P.to_rule(prop, 1)                          # operator sets weight 1 (AI proposed 2)
    F.amend(g, {"rules": list(g["contract"].get("rules") or []) + [rule]}, "banana", prior_safeword="banana")
    P.mark_enacted("lab", "r-e2e", 1)
    check("after enact, the delegation rule governs → create_vm is 'none'",
          Contract(g, "lab", "signed").resolve_tier("create_vm") == "none")
    check("the enactment is a versioned, logged amendment",
          g["contract"]["version"] == 2 and len(g["contract"]["amendments"]) == 1
          and P.get("lab", "r-e2e")["status"] == "enacted")

    print("\nGRANT handler (the engine's per-leaf hook): grant proceeds; deny/unattended auto-drafts")
    from orchestrator.ai.autonomous import make_grant_handler
    granted = make_grant_handler(agent="g1", prompt=lambda t, a, c: True)
    check("a GRANT proceeds (True) and drafts nothing",
          granted("delete_vm", {"name": "x"}, "delete") is True and P.pending("g1") == [])
    denied = make_grant_handler(agent="g2", prompt=lambda t, a, c: False)
    r1 = denied("delete_vm", {"name": "x"}, "delete")
    r2 = denied("delete_vm", {"name": "y"}, "delete")     # same tool again
    check("a DENY blocks (False) and auto-drafts ONE referendum for the tool",
          r1 is False and r2 is False and len(P.pending("g2")) == 1)
    draft = P.pending("g2")[0]
    check("the draft is a delegation referendum lifting that gate, origin=ai",
          draft["kind"] == "delegation" and draft["effect"] == {"tier": "normal", "tools": ["delete_vm"]}
          and draft["origin"] == "ai")
    unattended = make_grant_handler(agent="g3")            # no prompt → unattended
    check("UNATTENDED (no prompt) blocks and drafts for review",
          unattended("snapshot_restore", {"name": "z"}, "restore") is False and len(P.pending("g3")) == 1)

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
