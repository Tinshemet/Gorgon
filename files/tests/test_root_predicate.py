#!/usr/bin/env python3
"""
test_root_predicate.py — the CONTRACT ROOT PREDICATE (gauntlet E, acceptance).

Proves the reward-hacking-by-bad-plan gate: all-children-done is NECESSARY but, at
the ROOT, not SUFFICIENT. A plan whose steps each 'succeed' but do not COMPOSE (a
later step undid an earlier one, or a step was simply omitted) is `unverified`, NOT
done — so it books no reward. The predicate comes from the CONTRACT and is checked
against ground truth, and it's gated to the root (intermediate composites stand).

Run:  PYTHONPATH=files python3 files/tests/test_root_predicate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.engine import Engine
from planner.score import run_score
from orchestrator.ai.autonomous import make_goal_verifier
import orchestrator.ai.agent.contract as C

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


_TOOLS = [{"type": "function", "function": {"name": "create_vm", "parameters": {}}}]


def _dc(steps):
    return {"message": {"tool_calls": [{"function": {"name": "decompose", "arguments": {"steps": steps}}}]}}


def _tc(name, args):
    return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}


def _goal_of(m):
    return next((x["content"][6:] for x in m if x["role"] == "user" and x["content"].startswith("Goal: ")), "")


# A two-level plan: root → [set up web, set up db]; "set up web" → [create web1, create web2].
# Every leaf create_vm 'succeeds', so all-children-done holds at every composite.
def _model(m, t):
    goal = _goal_of(m)
    if goal == "build lab":
        return _dc(["set up web", "set up db"])
    if goal == "set up web":
        return _dc(["create web1", "create web2"])
    return _tc("create_vm", {"name": goal.split()[-1]})


def _run(verify_goal, **engine_kw):
    return run_score("build lab", call_model=_model,
                     execute=lambda t, a: {"success": True}, tools=_TOOLS,
                     engine=Engine(verify_goal=verify_goal, **engine_kw))


def main():
    print("a clean-but-WRONG plan books no reward")
    r = _run(lambda g, kids, led: False)          # every step 'succeeded'; the GOAL does not hold
    check("root is unverified, not done", r["root"]["status"] == "unverified")
    check("reason is goal_predicate_unmet", r["root"].get("reason") == "goal_predicate_unmet")
    check("run is not ok (no reward)", r["ok"] is False)
    # A rejected plan is NOT re-run blind. This used to assert the opposite (retries == 2,
    # 9 ledger entries = 3 leaves × 3 attempts), and 0aba77b deliberately ended that: an
    # AND composite whose every step is `done` cannot be helped by re-running the SAME
    # plan — identical steps yield an identical predicate — and re-running a
    # non-idempotent step ('create 5 vms') duplicates work, the measured 5→10→15 cascade.
    # The correction that REPLACED it is revision (re-plan against the objection), asserted
    # below. This test kept asserting the old semantics and silently failed for a day; it
    # is not in the routinely-run list, which is how that went unnoticed.
    check("the rejected plan is NOT re-run blind", r["root"].get("retries") is None)
    check("no duplicated work — one honest pass", len(r["ledger"]) == 3)

    print("\nthe correction that replaced the retry: revision, when the driver enables it")
    # run_score defaults max_revisions=0; the autonomous driver turns it on. With it on,
    # the unverified root DOES self-correct — and still without duplicating work, because
    # a call this run already made is suppressed off the ledger.
    rv = _run(lambda g, kids, led: False, max_revisions=2)
    check("an unverified root revises when revision is enabled", rv["root"].get("revisions") == 2)
    check("revision still books no reward on a goal that never holds", rv["ok"] is False)
    check("revision does not duplicate the executed work", len(rv["ledger"]) == 3)

    print("\nthe predicate is gated to the ROOT — intermediate composites stand")
    kids = {c["goal"]: c for c in r["root"]["children"]}
    check("the depth-1 composite is done (not gated)", kids["set up web"]["status"] == "done")
    check("its children both done", all(c["status"] == "done" for c in kids["set up web"]["children"]))

    print("\na plan whose goal DOES hold is accepted")
    r = _run(lambda g, kids, led: True)
    check("root is done", r["root"]["status"] == "done" and r["ok"] is True)

    print("\nno predicate (None) → behaviour unchanged")
    r = _run(lambda g, kids, led: None)
    check("root is done when the predicate has no opinion", r["root"]["status"] == "done")
    r = _run(None)
    check("root is done when no verify_goal is wired at all", r["root"]["status"] == "done")

    print("\nthe verifier is the arg to the predicate: goal-string, children, ledger")
    seen = []
    _run(lambda g, kids, led: seen.append((g, len(kids))) or True)
    check("called once, at the root, with the root goal + its children", seen == [("build lab", 2)])

    print("\ncontract.goal_predicate wires the state check (make_goal_verifier)")
    check("Doorman has no structured predicate → None", C.goal_predicate() is None)
    vg = make_goal_verifier(lambda: {})
    check("no predicate → verifier stays silent (None, never blocks)", vg("g", [], []) is None)

    orig = C.goal_predicate
    try:
        C.goal_predicate = lambda: [{"criterion": "present", "target": "honeypot"},
                                    {"criterion": "absent", "target": "web01"}]
        vg = make_goal_verifier(lambda: {"honeypot": {"status": "running"}})
        check("True when every clause holds against live state", vg("g", [], []) is True)
        vg = make_goal_verifier(lambda: {"honeypot": {"status": "running"}, "web01": {"status": "stopped"}})
        check("False when a clause fails (web01 should be absent)", vg("g", [], []) is False)
    finally:
        C.goal_predicate = orig

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
