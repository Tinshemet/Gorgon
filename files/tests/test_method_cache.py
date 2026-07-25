#!/usr/bin/env python3
"""
test_method_cache.py — the parameterized decomposition cache.

Proves: seed methods instantiate; parameterization generalizes across names; a miss
is None; and a learned decomposition generalizes to a new goal ("un-reasons over time").

Run:  PYTHONPATH=files python3 files/tests/test_method_cache.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.method_cache import MethodCache, seeded

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
    print("seed methods instantiate (deterministic, no model)")
    c = seeded()
    check("create-and-launch",
          c.lookup("create a linux vm named web and launch it")
          == ["create a linux vm named web", "launch the vm named web"])
    check("create-two",
          c.lookup("create two linux vms named alpha and beta")
          == ["create a linux vm named alpha", "create a linux vm named beta"])
    check("create-two-and-launch (4 steps)",
          c.lookup("create two linux vms named alpha and beta, then launch both")
          == ["create a linux vm named alpha", "create a linux vm named beta",
              "launch the vm named alpha", "launch the vm named beta"])

    print("\nparameterization: different names hit the SAME method")
    check("names swapped still match",
          c.lookup("create two ubuntu vms named db and cache")
          == ["create a ubuntu vm named db", "create a ubuntu vm named cache"])
    check("miss returns None", c.lookup("what time is it") is None)
    check("hit counter advanced", c.hits >= 4)

    print("\nlearning: a model decomposition generalizes to a new goal")
    lc = MethodCache()                       # empty — no seeds
    check("novel goal is a miss", lc.lookup("wipe the alpha vm and the beta vm") is None)
    name = lc.remember("wipe the alpha vm and the beta vm",
                       ["delete the alpha vm", "delete the beta vm"])
    check("a method was learned", name is not None and lc.learned == 1)
    # the SAME shape with different names now decomposes deterministically:
    got = lc.lookup("wipe the web vm and the db vm")
    check("learned method generalizes to new names",
          got == ["delete the web vm", "delete the db vm"])
    check("re-remembering a covered goal is a no-op",
          lc.remember("wipe the x vm and the y vm", ["delete the x vm", "delete the y vm"]) is None)

    print("\nproven-only durability: a method earns persistence by WORKING")
    check("a freshly learned method is NOT yet proven", lc.proven() == [])
    check("confirm marks the method learned from that goal",
          lc.confirm("wipe the alpha vm and the beta vm") is True)
    check("confirming twice is a no-op", lc.confirm("wipe the alpha vm and the beta vm") is False)
    check("confirming an unknown goal marks nothing", lc.confirm("something else entirely") is False)
    rec = lc.proven()
    check("now it is durable, as a plain JSON record",
          len(rec) == 1 and rec[0]["source"] == "wipe the alpha vm and the beta vm"
          and isinstance(rec[0]["pattern"], str) and len(rec[0]["steps"]) == 2)
    check("SEEDS are never persisted (code is their SSOT)", seeded().proven() == [])

    print("\na re-plan SUPERSEDES the unproven method it replaces")
    # The regression this guards: the first plan is learned at PLAN time, before anything
    # runs. If it fails and a revision produces a better plan, `lookup` would match the
    # discarded method and refuse to learn the good one — and `confirm` would then mark the
    # FAILED plan proven, durably teaching every future run a plan known not to work.
    sc = MethodCache()
    sc.remember("set up dev", ["create dev", "fiddle dev"])           # the plan that fails
    sc.remember("set up dev", ["create dev", "launch dev"])           # the corrective re-plan
    check("only one method is held for the goal (superseded, not duplicated)",
          len([m for m in sc._methods if m.get("learned")]) == 1)
    check("it is the RE-PLAN, not the discarded first attempt",
          sc.lookup("set up dev") == ["create dev", "launch dev"])
    sc.confirm("set up dev")
    check("so confirming the close persists the plan that WORKED",
          [m["steps"] for m in sc.proven()] == [["create {s0}", "launch {s0}"]])
    pc = MethodCache()
    pc.remember("set up dev", ["create dev", "launch dev"])
    pc.confirm("set up dev")
    pc.remember("set up dev", ["create dev", "fiddle dev"])           # a later guess
    check("a PROVEN method is never overwritten by a fresh guess",
          pc.lookup("set up dev") == ["create dev", "launch dev"])

    print("\nrehydration: a stored method decomposes without the model")
    rc = MethodCache.from_records(rec)
    check("the learned shape survives a round trip",
          rc.lookup("wipe the web vm and the db vm") == ["delete the web vm", "delete the db vm"])
    check("seeds are layered underneath",
          rc.lookup("create two ubuntu vms named a and b") is not None)
    check("a rehydrated method stays proven (re-saving is idempotent)", len(rc.proven()) == 1)
    check("a CORRUPT record is dropped, not raised on",
          MethodCache.from_records([{"name": "bad", "pattern": "([unclosed", "steps": ["x", "y"]}]
                                   ).lookup("anything") is None)

    print("\nthe durable store (per-agent, on disk)")
    import shared.bundle as _bundle
    _bundle.AGENTS_ROOT = tempfile.mkdtemp()      # isolate bundle storage from ~/.gorgon
    from orchestrator.ai.planner import method_store as mstore
    check("no store yet → empty, never raises", mstore.load("doorman") == [])
    check("merge reports what is genuinely new", mstore.merge_into("doorman", rec) == 1)
    check("it round-trips through disk",
          MethodCache.from_records(mstore.load("doorman")).lookup("wipe the x vm and the y vm")
          == ["delete the x vm", "delete the y vm"])
    check("re-merging the same shape adds no twin", mstore.merge_into("doorman", rec) == 0
          and len(mstore.load("doorman")) == 1)
    check("stores are per-agent isolated", mstore.load("barenboim") == [])
    check("a path-traversal agent name is sanitized (stays under the bundle root)",
          os.path.normpath(mstore.store_path("../../etc/passwd"))
          .startswith(os.path.normpath(_bundle.AGENTS_ROOT)))
    check("newest learning is listed FIRST (outranks older on lookup)",
          mstore.merge_into("doorman", [{"name": "n", "pattern": "^brand new$",
                                         "steps": ["a", "b"], "source": "brand new"}]) == 1
          and mstore.load("doorman")[0]["source"] == "brand new")
    mstore.save("capped", [{"name": f"m{i}", "pattern": f"^g{i}$", "steps": ["a", "b"],
                            "source": f"g{i}"} for i in range(mstore.MAX_METHODS + 50)])
    check("the store is capped (unbounded growth would slow every lookup)",
          len(mstore.load("capped")) == mstore.MAX_METHODS)
    check("forget clears it", mstore.clear("doorman") is True and mstore.load("doorman") == [])
    check("forgetting nothing is False, not an error", mstore.clear("never-existed") is False)

    print("\nthe NEGATIVE twin: plans that did not work are remembered too")
    fail = {"pattern": r"wire\ up\ (?P<s0>[\w-]+)", "source": "wire up q",
            "steps": ["create a vm named {s0}", "attach {s0} to netX"],
            "why": "plan [✓ create; ✗ attach (no such network)] → partial"}
    check("no failures yet → empty, never raises", mstore.load_failures("doorman") == [])
    check("recording reports what is new", mstore.record_failures("doorman", [fail]) == 1)
    check("a REPEAT bumps the count instead of adding a twin",
          mstore.record_failures("doorman", [fail]) == 0
          and [r["n"] for r in mstore.load_failures("doorman")] == [2])
    check("it warns about a NEW goal of the same shape",
          [r["source"] for r in mstore.warnings_for(mstore.load_failures("doorman"), "wire up zeta")]
          == ["wire up q"])
    check("and stays quiet about an unrelated goal",
          mstore.warnings_for(mstore.load_failures("doorman"), "delete the web vm") == [])
    check("a corrupt pattern is skipped, not raised on",
          mstore.warnings_for([{"pattern": "([unclosed", "why": "x"}], "anything") == [])
    check("failures are per-agent isolated", mstore.load_failures("barenboim") == [])
    check("the failure store is capped",
          (mstore.save_failures("cf", [{"pattern": f"^g{i}$", "why": "w"} for i in range(mstore.MAX_FAILURES + 25)])
           or len(mstore.load_failures("cf"))) == mstore.MAX_FAILURES)
    check("forgetting failures works", mstore.clear_failures("doorman") is True
          and mstore.load_failures("doorman") == [])

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
