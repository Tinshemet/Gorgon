"""select_probe.py — MOCK-UP. Does spending the referee beat drawing once?

THE OPERATOR, 2026-08-06: *"we were pretty good at catching mistakes not correcting them...
we havent used the ability we honed at catching to actual progress."*

Three readings of the same request, side by side:

    SINGLE      one draw, judged — today's behaviour exactly
    BEST-OF-N   N draws, keep the one with nothing dropped and no clause proven unaddressed
    +REPAIR     when none is clean, tell the model WHY in the seam's own words and re-ask

WHAT IT IS LOOKING FOR, in order of what would settle the question:

  * IS THERE ANYTHING TO SELECT FROM? If every draw of a request is identical, selection is
    a no-op and the idea dies here for nothing. Reported as `spread`.
  * DOES SELECTION RECOVER A REQUEST THAT A SINGLE DRAW REFUSES? That is the gain.
  * DOES REPAIR RECOVER ONE THAT SELECTION CANNOT? That is the correction half.
  * AND WHAT DOES IT COST — every draw is a model call.

THE RISK THIS MUST ALSO SHOW, because it is the honest direction of the danger: selection
turns refusals into RUNS. A clean-but-wrong reading would now execute where a dirty one was
safely refused. So the probe prints the goals it chose, not only that it chose one — a
recovered request whose goals are wrong is worse than the refusal it replaced, and no
summary line can tell you which happened.

    PYTHONPATH=. python3 tests/bench/select_probe.py [-n 3] [-d 3] [-r 11]
"""
from __future__ import annotations

import argparse
import json
import sys

from engines import extract
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

DEFAULT = (2, 3, 8, 10, 11)


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


def _key(goals) -> str:
    return json.dumps(sorted(json.dumps(g, sort_keys=True, default=str) for g in goals))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3,
                    help="how many times to run the whole comparison")
    ap.add_argument("-d", "--draws", type=int, default=3,
                    help="draws per selection")
    ap.add_argument("-r", "--rung", type=int, action="append")
    args = ap.parse_args(argv)

    wanted = set(args.rung or DEFAULT)
    tally = {"single": 0, "best": 0, "repair": 0, "cells": 0}

    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm, request in (("literal", rung.goal), ("paraphrase", rung.paraphrase)):
            if not request:
                continue
            print(f"\n── rung {rung.n} · {arm} · {args.repeats}x, {args.draws} draws each")
            print(f"   {request!r}")
            tally["cells"] += 1

            for run in range(args.repeats):
                world = _world(rung)
                # SINGLE — today's path, and the control.
                lost1: list = []
                try:
                    one = extract.to_goals(extract.extract(request), request,
                                           dropped=lost1, world=world) or []
                except Exception as exc:
                    one, lost1 = [], [f"{type(exc).__name__}: {exc}"]

                world = _world(rung)
                many, lost2, why2 = extract.best_of(request, world=world, draws=args.draws)

                world = _world(rung)
                fixed, lost3, why3 = extract.with_repair(request, world=world,
                                                         draws=args.draws, rounds=1)

                ok1, ok2, ok3 = (bool(one) and not lost1,
                                 bool(many) and not lost2,
                                 bool(fixed) and not lost3)
                tally["single"] += ok1
                tally["best"] += ok2
                tally["repair"] += ok3
                mark = lambda ok: "clean " if ok else "REFUSED"
                print(f"   [{run + 1}] single={mark(ok1)}  best-of={mark(ok2)}  "
                      f"+repair={mark(ok3)}"
                      f"{'   spread: readings differ' if _key(one) != _key(many) else ''}")
                if why2:
                    print(f"        {why2}")
                if why3 and why3 != why2:
                    print(f"        {why3}")
                # THE GOALS, ALWAYS. A recovered request with the wrong goals is worse than
                # the refusal it replaced, and only the reader can tell which this is.
                if ok3 and not ok1:
                    for g in fixed:
                        print(f"        + {_shape(g)}")
                elif not ok3 and lost3:
                    print(f"        why refused: {'; '.join(str(x) for x in lost3)[:150]}")

    total = tally["cells"] * args.repeats
    print(f"\n── clean readings, out of {total}")
    print(f"   single draw   {tally['single']}")
    print(f"   best-of-{args.draws}     {tally['best']}")
    print(f"   + repair      {tally['repair']}")
    print("\n   A CLEAN READING IS NOT A CORRECT ONE. This counts what the referee accepts;"
          "\n   only the ladder can say whether the world agreed afterwards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
