"""gate4_probe.py — count gate 4's candidates BEFORE writing it.

    PYTHONPATH=. python3 tests/bench/gate4_probe.py

Third time this order has paid. The arity rule looked clean against 14 hand-written readings
and had to be demoted against 83; gate 3's four rules were counted first and every one held.
Nothing here gets written until it has been counted.

## THE TWO CANDIDATES, AND WHY THEY ARE GATE 4'S RATHER THAN ANYBODY ELSE'S

**1 · THE ARTIFACT DESTROYS WHAT NO CLAIM ASKED TO REMOVE.** The measured case, and the one
that started all of this: `count(vm) = 10` against a lab holding twelve is covered by DELETING
TWO, and gates 1, 2 and 3 all pass it CORRECTLY — nothing is missing, `web` and `work-laptop`
genuinely exist, and removing two is a logical and possible way to reach ten. The defect lives
nowhere in the parts, only in the relation between the finished artifact and the request.

⇒ AND IT IS ASKED STRUCTURALLY, NOT LEXICALLY. The tempting version is *"the request contains
no destructive verb"*, which is a vocabulary test and inherits every weakness of one. The
structural version needs no words: **does any CLAIM in the reading take the REMOVES stance,
and does the PLAN contain a deleter anyway?**

**2 · THE READING DISAGREES WITH ITSELF.** The corpus holds THREE draws per cell, so
disagreement between them is measurable with no oracle at all — this is ambiguity-by-
disagreement, and it is the one gate-4 signal that needs neither the world nor a checker. The
question is whether a cell whose draws disagree is likelier to fail.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

from engines import extract
from planner import ghost_writer as _gw
from planner.gates import claims as _claims
from planner.ir import config as _config
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "corpus", "extract_raw.jsonl")


def destroys_unasked(goals, plan) -> list:
    """Deleters in the plan when no claim in the reading asked to remove anything."""
    deleters = set()
    for kind, spec in (_config.KINDS or {}).items():
        if isinstance(spec, dict) and spec.get("delete"):
            deleters.add(spec["delete"])
    calls = plan if isinstance(plan, list) else (plan or {}).get("plan") or []
    removing = [c for c in calls if (c[0] if isinstance(c, (list, tuple)) else None) in deleters]
    if not removing:
        return []
    asked = any(c.stance == _claims.REMOVES for c in _claims.over(goals))
    if asked:
        return []
    return [f"{t}({list(a.values())[0] if a else '?'})" for t, a in removing]


def main(argv=None) -> int:
    rows = [json.loads(l) for l in open(CORPUS) if l.strip()]
    by = {r.n: r for r in RUNGS}
    fires = Counter()
    draws = defaultdict(list)

    for row in rows:
        rung = by.get(row["rung"])
        world = SimWorld()
        if rung and rung.setup:
            rung.setup(world)
        outcome = str(row.get("outcome") or "?")
        raw = row["raw"] if isinstance(row["raw"], dict) else json.loads(row["raw"])
        try:
            goals = extract.to_goals(raw, row["request"], world=world) or []
        except Exception:
            goals = []
        # READING STABILITY — the shape of the reading, for comparing draws of one cell.
        draws[(row["rung"], row["column"])].append(
            (json.dumps(goals, sort_keys=True), outcome))
        if not goals:
            continue
        try:
            plan = _gw.cover(goals, world)
        except Exception:
            continue
        if destroys_unasked(goals, plan):
            fires[(outcome, "destroys what nothing asked to remove")] += 1

    print(f"\n{'═' * 92}\n  1 · THE ARTIFACT DESTROYS WHAT NO CLAIM ASKED TO REMOVE\n")
    if fires:
        for (outcome, name), n in sorted(fires.items()):
            print(f"  {outcome:<16}{name:<44}{n}")
    else:
        print("  never fires on this corpus — no reading plans an unasked deletion")

    print(f"\n{'═' * 92}\n  2 · DOES A CELL WHOSE DRAWS DISAGREE FAIL MORE OFTEN?\n")
    print(f"  {'cell':<14}{'distinct readings':<20}{'outcomes'}")
    print("  " + "─" * 88)
    agree_pass = agree_fail = differ_pass = differ_fail = 0
    for (rung, col), got in sorted(draws.items()):
        shapes = {g for g, _o in got}
        outcomes = [o for _g, o in got]
        distinct = len(shapes)
        passed = sum(1 for o in outcomes if o == "PASS")
        if distinct == 1:
            agree_pass += passed
            agree_fail += len(outcomes) - passed
        else:
            differ_pass += passed
            differ_fail += len(outcomes) - passed
        flag = "  <- disagrees" if distinct > 1 else ""
        print(f"  rung {rung:<3}{col:<6}{distinct:<20}{Counter(outcomes).most_common()}{flag}")
    tot_a, tot_d = agree_pass + agree_fail, differ_pass + differ_fail
    print(f"\n  cells whose draws AGREE   : {agree_pass}/{tot_a} pass "
          f"({100 * agree_pass // max(tot_a, 1)}%)")
    print(f"  cells whose draws DIFFER  : {differ_pass}/{tot_d} pass "
          f"({100 * differ_pass // max(tot_d, 1)}%)")
    print("\n  IF THOSE TWO RATES ARE THE SAME, DISAGREEMENT PREDICTS NOTHING and a gate built")
    print("  on it would spend a model call per request to learn nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
