"""surplus_probe.py — does a request whose only verb is CREATE delete a machine?

    PYTHONPATH=. python3 tests/bench/surplus_probe.py

## THE CLAIM UNDER TEST

A pipeline scan on 2026-08-07 reported that *"create 10 vms"* against a lab that already holds
twelve plans `stop_vm` + `delete_vm` on the surplus two and, with the shipped grant, RUNS them.
**A request whose only verb is "create" would delete the operator's machine.** That is the kind
of claim to verify rather than repeat, so this probe reproduces it with NO MODEL CALL — the
goal is handed to the writer directly, so nothing here depends on how a request was read.

## WHY THE GOAL IS NOT ITSELF THE BUG

`count(vm) = 10` is a TOTAL ([[gorgon-count-is-a-total]]). Against twelve machines the writer
is CORRECT to remove two: that is what the claim says. So this probe deliberately separates
two questions that look like one —

    1. does the WRITER plan the deletions?      it should, given that goal
    2. does anything ASK before they run?       and this is the whole finding

— because the fix belongs at 2 (and at the reading), never at 1. `Step.destroys` exists for
exactly this; the question is whether anything on the ENGINE path reads it, as the chat path
does at `orchestrator/ai/chat/shortcuts/plan.py:275`.
"""
from __future__ import annotations

import sys

from planner import ghost_writer
from tests.bench.sim_world import SimWorld

LAB = ["web", "work-laptop", "db", "a", "b", "c", "d", "e", "f", "g", "h", "i"]


def _lab() -> SimWorld:
    world = SimWorld()
    for name in LAB:
        world.vms[name] = world.blank_vm()
    return world


def main(argv=None) -> int:
    world = _lab()
    goal = {"shape": "count", "select": {"kind": "vm"}, "eq": 10}
    print(f"\n  world before : {sorted(world.vms)}  ({len(world.vms)} machines)")
    print(f"  the goal     : count(vm) = 10   <- a TOTAL, not 'ten more'")

    # 1 · WHAT DOES THE WRITER PLAN? Against a scratch, so nothing moves yet.
    planned = ghost_writer.cover([goal], world)
    if isinstance(planned, dict):
        calls = planned.get("calls") or planned.get("program") or []
    else:
        calls = planned
    print(f"\n  1 · THE PLAN")
    deleters, stoppers = [], []
    rows = list(calls) if isinstance(calls, (list, tuple)) else []
    rows = [r if isinstance(r, dict) else {"tool": r[0], "args": r[1]}
            for r in rows if isinstance(r, dict) or (isinstance(r, (list, tuple)) and len(r) == 2)]
    for row in rows:
        tool = row.get("tool") if isinstance(row, dict) else None
        args = row.get("args") if isinstance(row, dict) else {}
        if tool:
            print(f"      {tool}({', '.join(f'{k}={v}' for k, v in (args or {}).items())})")
        if tool and "delete" in str(tool):
            deleters.append(args)
        if tool and "stop" in str(tool):
            stoppers.append(args)
    if not rows:
        print(f"      (could not read calls off the plan; keys = {sorted(planned)})")
    print(f"      => {len(deleters)} deletion(s), {len(stoppers)} stop(s)")

    # 2 · DOES ANYTHING ASK? The finding, and the only part that is a defect.
    print(f"\n  2 · DOES ANYTHING ASK BEFORE THEY RUN?")
    from engines import insession as _insession
    from engines.orchestrator import Orchestrator
    step = _insession.Step("run", "the plan", destroys=[("delete_vm", a) for a in deleters])

    class _Absent:                    # NOBODY IS THERE — the shipped default
        consent = None

    class _Present:                   # an operator who is asked, and says no
        asked: list = []

        def consent(self, question):
            _Present.asked.append(question)
            return False

    print(f"      Step.destroys declared : {len(step.destroys)}")
    for who, session in (("no operator present", _Absent()), ("operator says no", _Present())):
        verdict = Orchestrator._grant(step, session)
        stopped = verdict.action == _insession.STOP
        print(f"      {who:<22} : {verdict.action.upper():<5} "
              f"{'— ' + verdict.why if stopped else '(the machines go)'}")
    print(f"      operator was ASKED     : {_Present.asked or 'never'}")

    # AND THE ONE THAT MUST STILL WORK. A real deletion request has to survive this.
    granted = Orchestrator._grant(step, type("S", (), {"consent": True})())
    print(f"      consent granted        : {granted.action.upper()}  <- must be RUN")

    print(f"\n{'─' * 88}")
    absent = Orchestrator._grant(step, _Absent())
    if deleters and absent.action == _insession.STOP and granted.action == "run":
        print("  FIXED: the surplus is still PLANNED — correctly, since count is a total —")
        print("  but nothing destroys it without an operator. Unauthorised deletion STOPS")
        print("  with the machines named; an authorised one still runs.")
    elif not deleters:
        print("  NOT REPRODUCED: the writer planned no deletion for this goal.")
    elif absent.action != _insession.STOP:
        print("  STILL BROKEN: an unauthorised deletion was granted.")
    else:
        print("  OVER-CORRECTED: an AUTHORISED deletion was refused. That breaks 'delete web'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
