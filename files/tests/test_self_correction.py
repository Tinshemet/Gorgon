#!/usr/bin/env python3
"""
test_self_correction.py — plan-level revision (self-correction).

Proves the corrigibility-spine addition: an AND plan left `partial` (a REQUIRED step
failed for good) is not a dead branch — the tree RE-PLANS the goal, feeding the model a
post-mortem of which steps failed so it produces the CORRECTIVE remainder, not the same
decomposition. Distinct from leaf backtrack (same sub-goal, new approach). Bounded by
max_revisions; re-attempts skip the method cache (the root-replan landmine); off unless
max_revisions > 0.

Run:  PYTHONPATH=files python3 files/tests/test_self_correction.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.engine import Engine
from orchestrator.ai.planner.score import run_score
from orchestrator.ai.planner.method_cache import MethodCache

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


_TOOLS = [{"type": "function", "function": {"name": n, "parameters": {}}}
          for n in ("create_vm", "configure_vm", "configure_fallback")]
_NO_LEGAL = lambda *a: False


class World:
    """create_vm is idempotent (re-running a done step is harmless); configure_vm always
    fails (a broken approach); configure_fallback is the corrective step that works."""
    def __init__(self):
        self.vms = {}
        self.configured = set()

    def execute(self, tool, args):
        n = args.get("name")
        if tool == "create_vm":
            self.vms[n] = {"status": "stopped"}
            return {"success": True}
        if tool == "configure_vm":
            return {"success": False, "error": "driver missing"}
        if tool == "configure_fallback":
            self.configured.add(n)
            return {"success": True}
        return {"success": True}


def _dec(steps):
    return {"message": {"tool_calls": [{"function": {"name": "decompose", "arguments": {"steps": steps}}}]}}


def _tc(name, args):
    return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}


def _goal(m):
    return next((x["content"][6:] for x in m if x["role"] == "user" and x["content"].startswith("Goal: ")), "")


def _sys(m):
    return next((x["content"] for x in m if x["role"] == "system"), "")


def _leaf_model(m, tools):
    """Shared leaf routing for the sub-goals (the whole test uses these primitives)."""
    g = _goal(m)
    if g == "create web":                 return _tc("create_vm", {"name": "web"})
    if g == "configure web":              return _tc("configure_vm", {"name": "web"})
    if g == "configure web via fallback": return _tc("configure_fallback", {"name": "web"})
    return {"message": {"tool_calls": []}}


def main():
    print("AND partial → RE-PLAN the corrective remainder → done (revised)")
    w = World()
    def model(m, tools):
        g = _goal(m)
        if g == "set up web":
            # On revision the post-mortem ("→ partial") is in the prompt → switch to the
            # working plan; the first, naive plan uses the broken configure_vm.
            if "→ partial" in _sys(m):
                return _dec(["create web", "configure web via fallback"])
            return _dec(["create web", "configure web"])
        return _leaf_model(m, tools)
    r = run_score("set up web", call_model=model, execute=w.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, max_revisions=1), max_retries=0)
    check("root recovered to done via revision", r["root"]["status"] == "done" and r["ok"] is True)
    check("root flagged revised (1 revision)", r["root"].get("revised") is True and r["root"].get("revisions") == 1)
    check("the corrective step actually ran (world changed)", "web" in w.configured)

    print("\nrevision is BOUNDED — a persistently-broken plan stays partial after the budget")
    w = World()
    def stuck(m, tools):
        g = _goal(m)
        if g == "set up web":
            return _dec(["create web", "configure web"])   # never switches — always the broken plan
        return _leaf_model(m, tools)
    r = run_score("set up web", call_model=stuck, execute=w.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, max_revisions=2), max_retries=0)
    check("still partial after exhausting revisions", r["root"]["status"] == "partial")
    check("used the full revision budget", r["root"].get("revisions") == 2)
    check("not falsely marked revised", "revised" not in r["root"])

    print("\noff by default — max_revisions=0 leaves a partial partial (backward compatible)")
    w = World()
    r = run_score("set up web", call_model=stuck, execute=w.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL), max_retries=0)
    check("partial, and no revision attempted", r["root"]["status"] == "partial" and "revisions" not in r["root"])

    print("\nlandmine fixed: a re-plan SKIPS the cached (failing) decomposition")
    w = World()
    mc = MethodCache()
    mc.remember("set up web", ["create web", "configure web"])   # a cached plan that fails
    def cache_model(m, tools):
        g = _goal(m)
        if g == "set up web":
            # If the cache were re-used on revision this never runs; reaching the model
            # with the post-mortem is how the corrective plan gets chosen.
            if "→ partial" in _sys(m):
                return _dec(["create web", "configure web via fallback"])
            return _dec(["create web", "configure web"])
        return _leaf_model(m, tools)
    r = run_score("set up web", call_model=cache_model, execute=w.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, method_cache=mc, decompose_first=True,
                                max_revisions=1), max_retries=0)
    check("first plan came from the cache (deterministic)", any(
        c.get("goal") == "create web" for c in r["root"].get("children", [])))
    check("revision reached the model despite the cache → recovered", r["root"]["status"] == "done"
          and r["root"].get("revised") is True and "web" in w.configured)

    print("\nTARGETED revision — a completed NON-IDEMPOTENT step is NOT re-run")
    # The 5-vm regression in miniature: plan = [create (non-idempotent), configure].
    # configure fails the first time (prerequisite not yet satisfied) and succeeds the
    # second. The OLD wholesale re-plan re-ran BOTH steps → create fired twice (the
    # duplication cascade). Targeted revision re-resolves ONLY the not-done `configure`,
    # so `create` runs exactly ONCE.
    class CountWorld:
        def __init__(self):
            self.creates = 0
            self.configure_calls = 0
        def execute(self, tool, args):
            if tool == "create_vm":
                self.creates += 1                       # non-idempotent: each call is a NEW resource
                return {"success": True}
            if tool == "configure_vm":
                self.configure_calls += 1
                return {"success": self.configure_calls >= 2}   # transient: fails once, then works
            return {"success": True}
    w = CountWorld()
    def cmodel(m, tools):
        g = _goal(m)
        if g == "provision X":
            return _dec(["create X", "configure X"])    # SAME plan every time — no fallback
        if g == "create X":    return _tc("create_vm", {"name": "X"})
        if g == "configure X": return _tc("configure_vm", {"name": "X"})
        return {"message": {"tool_calls": []}}
    r = run_score("provision X", call_model=cmodel, execute=w.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, max_revisions=1), max_retries=0)
    check("plan recovered to done", r["root"]["status"] == "done")
    check("the non-idempotent create ran EXACTLY once (not re-run on revision)", w.creates == 1)
    check("configure was retried (ran twice: fail then succeed)", w.configure_calls == 2)

    print("\nalready-satisfied leaves: 'no tool call' is correct when the effect is in place")
    # The defect: on a re-entry the model rightly declines to redo a done step, the engine
    # scores that no_action, and the composite is stuck `partial` forever — it can never
    # close, so revision re-runs it, and it declines again.
    sat_world = {"seen": 0}
    def _mute_on_second(m, tools):
        g = _goal(m)
        if g == "set up X":
            return _dec(["create a vm named x", "configure X"])
        if g == "create a vm named x":
            sat_world["seen"] += 1
            if sat_world["seen"] == 1:
                return _tc("create_vm", {"name": "x"})
            return {"message": {"tool_calls": []}}      # already there → no call (correct!)
        if g == "configure X":
            return _tc("configure_vm", {"name": "X"}) if sat_world["seen"] < 2 else _tc("configure_fallback", {"name": "X"})
        return {"message": {"tool_calls": []}}
    w2 = World()
    r = run_score("set up X", call_model=_mute_on_second, execute=w2.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, max_revisions=1,
                                already_satisfied=lambda g: "named x" in g and "x" in w2.vms),
                  max_retries=0)
    creates = [n for n in r["root"]["children"] if "named x" in n["goal"]]
    check("the re-entered create closed DONE, not no_action", creates and creates[0]["status"] == "done")
    check("it is marked as satisfied-by-state, not by a tool call",
          creates and creates[0].get("satisfied") == "already" and creates[0].get("tool") is None)
    check("so the composite could close (no permanent partial)", r["root"]["status"] == "done")

    # The guard: satisfaction is read off STATE, so a goal whose effect is NOT in place
    # still fails on a mute model — the check can never launder a real no_action into done.
    w3 = World()
    sat_world["seen"] = 1                                # so the create step mutes immediately
    r = run_score("set up X", call_model=_mute_on_second, execute=w3.execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, already_satisfied=lambda g: False),
                  max_retries=0)
    creates = [n for n in r["root"]["children"] if "named x" in n["goal"]]
    check("state says NOT satisfied → the same mute model is still no_action",
          creates and creates[0]["status"] == "no_action" and "x" not in w3.vms)
    r = run_score("make Y", call_model=lambda m, t: {"message": {"tool_calls": []}},
                  execute=World().execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL, already_satisfied=lambda g: False),
                  max_retries=0)
    check("a mute model with nothing satisfied stays no_action", r["root"]["status"] == "no_action")
    r = run_score("make Y", call_model=lambda m, t: {"message": {"tool_calls": []}},
                  execute=World().execute, tools=_TOOLS,
                  engine=Engine(legal_filter=_NO_LEGAL), max_retries=0)
    check("no check wired → unchanged behavior (no_action)", r["root"]["status"] == "no_action")

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
