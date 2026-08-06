"""reading_probe.py — the READING layer alone: the AI, the assistant, and the gate.

    PYTHONPATH=. python3 tests/bench/reading_probe.py [-n 3] [-r 8] [-p]

## WHAT THIS DELIBERATELY DOES NOT DO

**NOTHING RUNS.** No program is executed, no world is changed, no rung checker is consulted.
The question is only whether the request was READ, and every other measure in this repository
folds that together with the writer, the executor and an oracle — so a reading failure and an
execution failure arrive as the same cell and the ladder cannot tell them apart.

A PLAN IS STILL MADE, and that is not the same as running one. The gate asks what the reading
WOULD do, which needs `cover` — and `cover` plans against a scratch copy precisely so nothing
real is touched. The plan is evidence about the reading; it is never carried out.

## WHY THIS IS THE MEASURE THE GATE WAS BUILT FOR

The ladder needs a hand-written checker per rung, so it can only ever measure fourteen
requests, and it scores what the WORLD ended up looking like. This needs no oracle at all: the
gate fires or it does not, and what it catches is the number. That is what makes it usable on
real operator requests later, where nobody has written down the right answer in advance.

## HOW TO READ IT

    PROCEED   the reading survived every check — NOT a claim that it is correct
    ASK       something was caught, with the reason, and the operator can settle it
    REFUSE    nothing to ask about — the reading cannot be planned at all

**A HIGH `PROCEED` RATE IS NOT A GOOD SCORE.** It is the absence of a caught fault, and the
whole finding of 2026-08-06 is that the surviving faults are the ones no current rule can see.
Read the CAUSES, not the total.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from engines import extract
from engines.medusa._run import _assistant
from planner import reading_gate as gate
from planner import refine
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld


def _world(rung) -> SimWorld:
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    return world


def _shape(goal: dict) -> str:
    if "every" in goal:
        return f"every {json.dumps(goal['every'])} must {json.dumps(goal.get('must'))}"
    if "per" in goal:
        return f"per {json.dumps(goal['per'])} make {json.dumps(goal.get('make'))}"
    if "observe" in goal:
        return f"observe {json.dumps(goal['observe'])} {goal.get('fact')}"
    return (f"{goal.get('shape')} {json.dumps(goal.get('select'))} "
            f"{ {k: v for k, v in goal.items() if k in ('eq', 'gte', 'lte')} }")


def read_once(request: str, world):
    """One reading, judged. Returns `(verdict, goals, lost, warnings)`. Nothing runs."""
    lost: list = []
    try:
        raw = extract.extract(request)
    except Exception as exc:
        return (gate.Verdict(gate.REFUSE, "channel", detail=f"{type(exc).__name__}"),
                [], [f"{type(exc).__name__}: {exc}"], [])
    try:
        goals = extract.to_goals(raw, request, dropped=lost, world=world) or []
    except Exception as exc:
        return (gate.Verdict(gate.REFUSE, "extractor", detail=str(exc)), [],
                [f"{type(exc).__name__}: {exc}"], [])
    if not goals:
        # NOTHING TO JUDGE. The seam produced no reading at all, which is its own outcome and
        # must not be folded in with a reading that was caught by a rule.
        return (gate.Verdict(gate.REFUSE, "no-reading",
                             detail="; ".join(lost) or "nothing usable"), [], lost, [])
    rehearsal = refine.rehearse(goals, world, request)
    warnings = _assistant(request, rehearsal.plan, world)
    return gate.judge(request, rehearsal, lost, warnings), goals, lost, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-r", "--rung", type=int, action="append")
    ap.add_argument("-p", "--paraphrase", action="store_true",
                    help="the paraphrase arm only (default runs both)")
    ap.add_argument("-v", "--verbose", action="store_true", help="show the goals")
    args = ap.parse_args(argv)

    wanted = set(args.rung or [r.n for r in RUNGS])
    arms = ("par",) if args.paraphrase else ("lit", "par")
    tally, causes = Counter(), Counter()
    verdicts = []

    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm in arms:
            request = rung.goal if arm == "lit" else rung.paraphrase
            if not request:
                continue
            for i in range(args.repeats):
                verdict, goals, lost, warnings = read_once(request, _world(rung))
                verdicts.append(verdict)
                tally[verdict.outcome] += 1
                if verdict.caught:
                    causes[verdict.caught] += 1
                mark = {gate.PROCEED: "ok     ", gate.ASK: "ASK    ",
                        gate.REFUSE: "REFUSE "}[verdict.outcome]
                print(f"  rung {rung.n:>2} {arm} [{i + 1}/{args.repeats}] {mark}"
                      f"{verdict.caught:20} {len(goals)} goal(s)")
                if verdict.outcome != gate.PROCEED:
                    why = (verdict.question or verdict.detail or "").replace("\n", " ")
                    print(f"              {why[:120]}")
                if args.verbose:
                    for g in goals:
                        print(f"              · {_shape(g)}")

    total = sum(tally.values())
    print(f"\n── the reading layer alone · {total} reading(s), nothing executed")
    for outcome in (gate.PROCEED, gate.ASK, gate.REFUSE):
        print(f"   {outcome:9} {tally[outcome]:4}")
    if causes:
        print("\n   what was caught:")
        for cause, n in causes.most_common():
            print(f"      {cause:20} {n}")
    print("\n   A HIGH `proceed` IS NOT A SCORE — it is the absence of a CAUGHT fault, and"
          "\n   the surviving faults are the ones no current rule can see. Read the causes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
