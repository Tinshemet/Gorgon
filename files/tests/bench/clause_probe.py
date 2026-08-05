"""clause_probe.py — does asking one clause at a time PRODUCE the clause nobody translates?

THE HYPOTHESIS THIS EXISTS TO TEST, and it is the only one left standing. Every mechanism
built against the missing-clause defect — the clause ledger, `intent.vacuous`,
`extract.invented`, the reconcilers, both provenance schemes — DETECTS it. Detectors took
literal false successes to zero, which is worth having, and not one of them can close a rung:
the clause still does not exist. `extract.by_clause` asks for it.

WHY THIS IS NOT THE LADDER. The ladder measures a whole run and answers "did rung 11 pass",
which folds the front seam, the writer, the executor and the checker into one bit. The
question here is narrower and comes first: GIVEN a request whose second clause has never been
translated at any model size, does asking for that clause ALONE produce a goal for it? If the
answer is no, nothing downstream matters and the ladder run is 40 minutes spent confirming it.

    PYTHONPATH=. python3 tests/bench/clause_probe.py [-n 3] [-r 11] [-r 3]

WHAT IT PRINTS. Per rung and arm: the clauses the splitter found, the goals the ordinary
whole-request reading produced, and the goals the per-clause reading ADDS. The last column is
the finding — a clause split that adds nothing is a negative result and should be reported as
one rather than tuned until it is not.

TEMPERATURE 0 IS NOT DETERMINISTIC, so `-n` repeats and a goal is reported as FOUND if any
repeat produced it. That is the generous reading ON PURPOSE: this asks whether the model CAN
produce the clause, and a mechanism that cannot manage it at its most generous is dead
without a second measurement. A mechanism that can is then owed a worst-of-N ladder run,
which is the honest one.
"""
from __future__ import annotations

import argparse
import json
import sys

from engines import extract
from planner import clause_ledger as ledger
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

# THE RUNGS WHOSE FAILURE IS THIS DEFECT, from the blocker table. Others may be passed with
# -r; these are the default because a mechanism aimed at them should be judged on them.
DEFAULT = (3, 8, 10, 11)


def _world(rung) -> SimWorld:
    """The lab as the rung starts it — the same state the ladder gives the front seam."""
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    return world


def _shape(goal: dict) -> str:
    """A goal in one line, so two readings can be compared by eye."""
    if "every" in goal:
        return f"every {json.dumps(goal['every'])} must {json.dumps(goal.get('must'))}"
    if "per" in goal:
        return f"per {json.dumps(goal['per'])} make {json.dumps(goal.get('make'))}"
    if "observe" in goal:
        return f"observe {json.dumps(goal['observe'])} {goal.get('fact')}"
    return (f"{goal.get('shape')} {json.dumps(goal.get('select'))} "
            f"{ {k: v for k, v in goal.items() if k in ('eq', 'gte', 'lte')} }")


def _gather(request: str, world, repeats: int):
    """`(whole, added)` — goals the ordinary reading found, and what the split ADDS."""
    whole, split = [], []
    for _ in range(repeats):
        try:
            raw = extract.extract(request)
            whole = extract.merge(whole, extract.to_goals(raw, request, world=world) or [])
        except Exception as exc:                                  # a decode failure is data
            print(f"      whole-request call failed: {type(exc).__name__}: {exc}")
        try:
            split = extract.merge(split, extract.by_clause(request, world=world))
        except Exception as exc:
            print(f"      clause call failed: {type(exc).__name__}: {exc}")
    seen = {json.dumps(g, sort_keys=True, default=str) for g in whole}
    added = [g for g in split
             if json.dumps(g, sort_keys=True, default=str) not in seen]
    return whole, added


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-r", "--rung", type=int, action="append")
    ap.add_argument("-p", "--paraphrase", action="store_true",
                    help="the paraphrase arm only (default runs both)")
    args = ap.parse_args(argv)

    wanted = set(args.rung or DEFAULT)
    arms = ("paraphrase",) if args.paraphrase else ("literal", "paraphrase")
    gained = 0

    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm in arms:
            request = rung.goal if arm == "literal" else rung.paraphrase
            if not request:
                continue
            clauses = ledger.enumerate_clauses(request)
            print(f"\n── rung {rung.n} · {arm} · n={args.repeats}")
            print(f"   {request!r}")
            print(f"   split into {len(clauses)}: "
                  + "  ||  ".join(c["text"] for c in clauses))
            if len(clauses) < 2:
                print("   ONE CLAUSE — the split does not apply, and asking again would buy "
                      "a second identical draw")
                continue
            whole, added = _gather(request, _world(rung), args.repeats)
            print(f"   whole-request reading ({len(whole)}):")
            for goal in whole:
                print(f"      {_shape(goal)}")
            print(f"   the split ADDS ({len(added)}):")
            for goal in added:
                print(f"      + {_shape(goal)}")
            if not added:
                print("      (nothing — a negative result for this row)")
            gained += len(added)

    print(f"\n── {gained} goal(s) the whole-request reading never produced")
    print("   A GOAL ADDED IS NOT A RUNG CLOSED. It has to be the RIGHT goal, and the run has"
          "\n   to reach DONE with the checker agreeing — which only the ladder can say.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
