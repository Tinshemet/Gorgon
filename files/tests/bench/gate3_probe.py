"""gate3_probe.py — the two measurements to take BEFORE gate 3 is written.

    PYTHONPATH=. python3 tests/bench/gate3_probe.py

## WHY THIS RUNS FIRST

**1 · WHAT IS GATE 3'S CEILING?** Every check it could make — vacuity, inertness,
contradiction — is a statement about what a reading WOULD DO, which means the writer has to
plan it first. Gates 1 and 2 are pure functions of (request, goals, world); gate 3 is not.

And a reading the writer REFUSES never reaches a gate at all: `cover` raises `Unsolvable` and
the engine promotes to tree. So gate 3 only ever sees readings that PLAN. If most failing
readings die at the writer, gate 3's territory is small and that is worth knowing before it is
built rather than after.

**2 · HOW OFTEN WOULD EACH CANDIDATE FIRE ON A READING THAT PASSED?** That is the false-alarm
rate, and it is the number that decides whether a check refuses, reports, or is dropped.

## AND THE REASON THIS FILE EXISTS AT ALL

Earlier today the arity rule was validated against the 14 hand-written correct readings — 0
occurrences, so a shape no correct reading uses could be refused. Against 83 REAL readings it
appeared on ones that PASS, and it had to be demoted. **Fourteen hand-written readings are ONE
IDIOM.** No gate-3 rule gets written until it has been counted against the corpus.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from engines import extract
from planner import ghost_writer as _gw
from planner.gates import claims as _claims
from planner.ir import config as _config
from planner.ir import consent as _consent
from planner.ir import intent as _intent
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "corpus", "extract_raw.jsonl")


def _single_valued(kind: str, attr: str) -> bool:
    """Can a member hold ONE value of this attribute, or several?

    ASKED OF THE EXISTING AUTHORITY rather than re-derived. `model_world._single` reads it off
    `attr_values`: an attribute with an enumeration takes one of them, one without is a
    collection. A second hand-rolled answer beside it is a second thing to drift.
    """
    from planner.model_world import _single
    spec = (_config.KINDS or {}).get(kind) or {}
    for setter in (spec.get("setters") or {}).values():
        if isinstance(setter, dict) and setter.get("attr") == attr:
            return _single(spec, setter)
    return True


def contradictions(goals) -> list:
    """Two goals forcing the SAME single-valued attribute to DIFFERENT values on a member
    they SHARE. Sound ONLY where the attribute holds one value at a time — `network` and
    `label` are SETS, so "every vm on core" and "db on dmz" do not conflict."""
    forced = {}
    out = []
    for claim in _claims.over(goals):
        if claim.stance != _claims.ASSERTS or claim.identity is None:
            continue
        if not _single_valued(claim.kind, claim.attr):
            continue
        key = (claim.kind, claim.identity, claim.attr)
        if key in forced and forced[key] != claim.value:
            out.append(f"{claim.identity} must have {claim.attr}="
                       f"{forced[key]!r} and {claim.value!r}")
        forced[key] = claim.value
    return out


def unrelated(goals) -> list:
    """Two members created whose kinds the manifest says CAN be related, and no goal relates
    them. Rung 3's shape — and the one with a known false-alarm risk, because "create a
    network called lab" alone is a legal request this would accuse."""
    made = _claims.minted(goals)
    if len(made) < 2:
        return []
    related = set()
    for claim in _claims.over(goals):
        if claim.stance == _claims.ASSERTS and claim.attr:
            ref = _claims.refers_to(claim.attr)
            if ref:
                related.add(ref)
    out = []
    for kind in made:
        for other in made:
            if kind == other:
                continue
            spec = (_config.KINDS or {}).get(kind) or {}
            for setter in (spec.get("setters") or {}).values():
                if isinstance(setter, dict) and setter.get("refs") == other \
                        and other not in related:
                    out.append(f"{kind} and {other} are both made and never related")
                    break
    return sorted(set(out))


def main(argv=None) -> int:
    rows = [json.loads(l) for l in open(CORPUS) if l.strip()]
    by = {r.n: r for r in RUNGS}
    reach = Counter()
    fires = Counter()
    plans = Counter()

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
        if not goals:
            reach[(outcome, "no goals")] += 1
            continue
        # ── 1 · DOES IT EVEN REACH A PLAN? ───────────────────────────────────────────────
        try:
            plan = _gw.cover(goals, world)
        except _gw.Unsolvable:
            reach[(outcome, "UNSOLVABLE — never reaches gate 3")] += 1
            continue
        except Exception as exc:
            reach[(outcome, f"cover raised {type(exc).__name__}")] += 1
            continue
        reach[(outcome, "plans")] += 1
        calls = plan if isinstance(plan, list) else (plan or {}).get("plan") or []
        plans[outcome] += len(calls)

        # ── 2 · WOULD EACH CANDIDATE FIRE? ───────────────────────────────────────────────
        try:
            program = _gw.as_program(plan, goals, world)
        except Exception:
            program = None
        if not calls:
            fires[(outcome, "inert (plans nothing)")] += 1
        if program is not None:
            if _consent.vacuous(program):
                fires[(outcome, "vacuous witness")] += 1
        if _intent.vacuous(goals, "achieve"):
            fires[(outcome, "vacuous reading")] += 1
        if contradictions(goals):
            fires[(outcome, "contradiction (single-valued)")] += 1
        if unrelated(goals):
            fires[(outcome, "made and never related")] += 1

    print(f"\n{'═' * 96}\n  1 · DOES THE READING REACH A PLAN AT ALL?\n")
    print(f"  {'outcome':<16}{'fate':<38}n")
    print("  " + "─" * 92)
    for (outcome, fate), n in sorted(reach.items()):
        print(f"  {outcome:<16}{fate:<38}{n}")
    planned = sum(n for (o, f), n in reach.items() if f == "plans")
    bad_planned = sum(n for (o, f), n in reach.items() if f == "plans" and o != "PASS")
    bad_total = sum(n for (o, _f), n in reach.items() if o != "PASS")
    print(f"\n  ⇒ {planned} of {len(rows)} readings reach a plan.")
    print(f"  ⇒ OF THE FAILING ONES, {bad_planned} of {bad_total} do — that is GATE 3'S CEILING.")

    print(f"\n{'═' * 96}\n  2 · WOULD EACH CANDIDATE FIRE, AND ON WHAT?\n")
    print(f"  {'candidate':<32}{'on PASS (false alarms)':<26}on failing")
    print("  " + "─" * 92)
    names = sorted({f for _o, f in fires})
    for name in names:
        onpass = fires[("PASS", name)]
        onbad = sum(n for (o, f), n in fires.items() if f == name and o != "PASS")
        print(f"  {name:<32}{onpass:<26}{onbad}")
    if not names:
        print("  (nothing fired at all)")
    print(f"\n  A CANDIDATE THAT FIRES ON A PASSING READING IS A REPORT AT BEST. The arity rule")
    print("  looked clean against 14 hand-written readings and had to be demoted against 83.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
