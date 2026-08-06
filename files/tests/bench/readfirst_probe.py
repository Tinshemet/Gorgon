"""readfirst_probe.py — MOCK-UP. Does saying it in words first change what gets translated?

THE LEVER, and it is the best-evidenced one nobody here has tested:

    Format Tax (2604.03616)          two-turn (freeform, then reformat)   +6.8pp
                                     thinking before the formatted answer +9.2pp
    Capacity, Not Format (2606.09410) delayed structure recovers 79.5% of the loss
    Disambiguate First (2502.18448)   interpretations before parsing, 12.3% -> 53.2%
                                     — and on UNAMBIGUOUS questions 35.9% -> 77.9%

AND GORGON IS IN THE WORST REGIME FOR IT. `Capacity, Not Format` shows the format tax is
CAPACITY-DEPENDENT: frontier models lose ~0 and capacity-limited ones up to 36 points. This
runs an 8b, straight into a constrained JSON schema, with no step in between.

IT WAS STARTED ONCE AND NEVER FINISHED. A `reading` field was added to the schema on
2026-07-31 and never appeared in the output — which is how the grammar bug was found. The
experiment was abandoned there. **There is no result, only an abort.**

## WHY TWO CALLS RATHER THAN A FIELD

A `reading` field is a REQUIRED slot the model cannot always fill, and this codebase has
measured twice what that does: the `except` field invented exclusions "to have something to
say", and the `state` slot cost six ladder cells by answering when nothing was asked.
`PhantomFill` (2607.20492) is the same finding at scale — a required field with no honest
answer gets fabricated ~100% of the time.

A SECOND CALL ADDS NO SLOT AND NO PROMPT TEXT. The main prompt stays byte-identical, which
is the constraint this file's own history keeps proving matters: four prompt levers measured
on 2026-08-05, all negative.

## WHAT IT ASKS FOR, AND WHAT IT DELIBERATELY DOES NOT

The restatement asks for END STATES in plain English — "what must be true when this is
done". It does NOT name a shape, a kind, an attribute or an op, because the moment it does
it is teaching the schema in prose, which is the lever already measured dead.

    PYTHONPATH=. python3 tests/bench/readfirst_probe.py [-n 3] [-r 11]

Reported per rung and arm: the goals the ordinary path produces, and the goals produced when
the restatement rides along with the request. A goal the ordinary path never produces is the
result; anything else is noise.
"""
from __future__ import annotations

import argparse
import json
import sys

from engines import extract
from engines.channel import constrained
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

DEFAULT = (2, 3, 10, 11)

# ONE FIELD, ONE BRANCH. `constrained` is the only door to the model and it requires a
# schema — deliberately, because a caller that could skip it would be free generation
# wearing a schema's name (2026-07-31). A single string property is the weakest possible
# grammar, so this is freeform in everything but the wrapper, and single-branch schemas are
# the regime where enforcement was observed to hold.
# ITERATION 2. A single string field measured DEGENERATE: the model answered "beta", "lab",
# and once literally "true" — one token where several facts were wanted, because one string
# gives a two-clause request nowhere to put its second clause. That is the sink defect
# reappearing in the mock-up itself, which is a fair warning about the shape and not about
# the idea.
#
# AN ARRAY GIVES EACH FACT ITS OWN CELL. No `minItems`: a minimum-count array is the one
# shape `PhantomFill` (2607.20492) singles out as unable to carry a hedge — "fabrication
# concentrates in fields where no hedge fits" — and demanding two entries from a one-clause
# request is exactly how the `except` field learned to invent exclusions.
_SCHEMA = {"type": "object",
           "properties": {"true_when_done": {"type": "array", "items": {"type": "string"}}},
           "required": ["true_when_done"],
           "additionalProperties": False}

# NO SHAPE WORDS. Not "count", not "every", not "select", not a kind — naming any of them
# turns this into the schema taught in prose, which is the lever measured dead four times on
# 2026-08-05. It asks for END STATES because that is what a goal IS, in the operator's
# language rather than the writer's.
_ASK = ("What must be TRUE about the lab when this request has been fully carried out?\n"
        "Give ONE plain-English statement per thing that must be true.\n"
        "Include anything the request says to do AFTERWARDS, and anything it says to do TO "
        "SOMETHING IT JUST MADE.\n"
        "Do not write code. Do not explain. Do not leave anything out.\n\nREQUEST: ")


def reading_of(request: str, model=None, temp: float = 0.0, timeout: int = 300):
    """The request in the model's own words. None if the call fails — never fatal."""
    try:
        got = constrained(_ASK + request, request, _SCHEMA,
                          model=model, temp=temp, timeout=timeout)
    except Exception:
        return None
    lines = (got or {}).get("true_when_done") or []
    kept = [str(x).strip() for x in lines if str(x).strip()]
    return "\n".join(f"- {line}" for line in kept) if kept else None


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-r", "--rung", type=int, action="append")
    args = ap.parse_args(argv)

    wanted = set(args.rung or DEFAULT)
    gained = 0

    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm, request in (("literal", rung.goal), ("paraphrase", rung.paraphrase)):
            if not request:
                continue
            world = _world(rung)
            print(f"\n── rung {rung.n} · {arm} · n={args.repeats}")
            print(f"   {request!r}")

            plain, withread, readings = [], [], []
            for _ in range(args.repeats):
                try:
                    plain = extract.merge(plain, extract.to_goals(
                        extract.extract(request), request, world=world) or [])
                except Exception as exc:
                    print(f"      ordinary call failed: {type(exc).__name__}: {exc}")
                said = reading_of(request)
                if not said:
                    print("      restatement call failed")
                    continue
                readings.append(said)
                # THE RESTATEMENT RIDES WITH THE REQUEST, never replaces it. The operator's
                # own words are the thing being translated; this is context beside them, and
                # a paraphrase standing IN for the request would be translating the model's
                # reading of the lab rather than the lab's operator.
                framed = f"{request}\n\nWHAT THAT MEANS:\n{said}"
                try:
                    withread = extract.merge(withread, extract.to_goals(
                        extract.extract(framed), request, world=world) or [])
                except Exception as exc:
                    print(f"      second call failed: {type(exc).__name__}: {exc}")

            if readings:
                print("   the model's own reading (first draw):")
                for line in readings[0].splitlines()[:8]:
                    if line.strip():
                        print(f"      | {line.strip()}")
            seen = {json.dumps(g, sort_keys=True, default=str) for g in plain}
            added = [g for g in withread
                     if json.dumps(g, sort_keys=True, default=str) not in seen]
            print(f"   ordinary path ({len(plain)}):")
            for g in plain:
                print(f"      {_shape(g)}")
            print(f"   reading-first ADDS ({len(added)}):")
            for g in added:
                print(f"      + {_shape(g)}")
            if not added:
                print("      (nothing — a negative result for this row)")
            gained += len(added)

    print(f"\n── {gained} goal(s) the ordinary path never produced")
    print("   A GOAL ADDED IS NOT A RUNG CLOSED. It has to be the RIGHT goal and the run has"
          "\n   to reach DONE with the checker agreeing — which only the ladder can say.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
