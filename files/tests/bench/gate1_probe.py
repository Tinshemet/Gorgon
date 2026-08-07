"""gate1_probe.py — GATE 1 against the readings, right ones and real ones.

    PYTHONPATH=. python3 tests/bench/gate1_probe.py

## THE TWO COLUMNS, AND ONLY ONE OF THEM IS THE INTERESTING ONE

    KNOWN-GOOD   the hand-written correct reading of each rung (tests/test_ghost_writer.GOALS).
                 **EVERY FLAG HERE IS A FALSE ALARM.** These are the answers we want.
    RECORDED     78 real model readings on disk (tests/bench/corpus/extract_raw.jsonl), each
                 already labelled with the outcome it produced. No model call is made.

A gate is only worth its false-alarm rate. A rule that catches every bad reading and also
accuses the good ones has told the operator nothing and taught them to ignore it — which is
exactly why `clause-untouched` and `inert` were demoted to reports on 2026-08-06.

## AND THE RUNGS ARE SAMPLES, NEVER THE RULE

The operator, 2026-08-07: *"we don't flag the rung for what they are, we use them as EXAMPLES
FOR USER PATTERNS IN NATURE."* So nothing in `planner/gates/completeness.py` names a rung, a
request or a domain word. If a column here only looks good because a rule was fitted to it,
the paraphrase arm will say so.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

from planner.gates import completeness as g1
from tests.bench.rungs import RUNGS
from tests.test_ghost_writer import GOALS

CORPUS = "tests/bench/corpus/extract_raw.jsonl"


def _kinds():
    from planner.ir import config as _config
    return _config.KINDS or {}


def known_good() -> int:
    """COLUMN 1 — every flag is a false alarm, on BOTH arms.

    ⇒ THE PARAPHRASE ARM IS THE ONE THAT DECIDES WHETHER THIS IS A GATE.

    The goals are IDENTICAL for both arms — they are the one correct reading of that rung. Only
    the SENTENCE changes. So a flag that appears on the paraphrase and not on the literal is
    not a finding about the reading at all; it is the rule keying on particular words, which is
    the failure the operator named: *"we don't flag the rung for what they are, we use them as
    examples for user patterns in nature."*

    **A RULE THAT STOPS WORKING WHEN THE WORDING CHANGES WAS NEVER A GATE.**
    """
    print(f"\n{'═' * 100}\n  KNOWN-GOOD READINGS — every flag below is a FALSE ALARM")
    print("  SAME GOALS BOTH ARMS. Only the sentence changes.\n")
    print(f"  {'rung':<6}{'literal':<12}{'paraphrase':<14}what gate 1 said")
    print("  " + "─" * 96)
    false_alarms = 0
    vocabulary_bound = 0
    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if not goals:
            continue
        lit = g1.inspect(rung.goal, goals, _kinds())
        par = g1.inspect(rung.paraphrase, goals, _kinds()) if rung.paraphrase else lit
        false_alarms += (not lit.legal) + (not par.legal)
        if lit.legal != par.legal:
            vocabulary_bound += 1
        mark = "" if lit.legal and par.legal else "  <- FALSE ALARM"
        if lit.legal != par.legal:
            mark = "  <- DISAGREES WITH ITSELF ON WORDING"
        print(f"  {rung.n:<6}{('legal' if lit.legal else 'FLAGGED'):<12}"
              f"{('legal' if par.legal else 'FLAGGED'):<14}{mark}")
        for arm, rep in (("lit", lit), ("par", par)):
            if not rep.legal:
                for line in rep.findings():
                    print(f"  {'':<8}{arm}: {line[:80]}")
    total = len([r for r in RUNGS if GOALS.get(r.n)]) * 2
    print(f"\n  ⇒ FALSE ALARMS: {false_alarms} of {total} readings "
          f"({len([r for r in RUNGS if GOALS.get(r.n)])} rungs x 2 arms)")
    print(f"  ⇒ VOCABULARY-BOUND: {vocabulary_bound} rung(s) where the two arms DISAGREE "
          f"— each one is the rule reading words, not patterns")
    return false_alarms


def recorded() -> None:
    """COLUMN 2 — real model readings, already labelled with what they produced."""
    if not os.path.exists(CORPUS):
        print(f"\n  (no corpus at {CORPUS})")
        return
    from engines import extract
    from tests.bench.sim_world import SimWorld
    by = {r.n: r for r in RUNGS}
    rows = [json.loads(l) for l in open(CORPUS) if l.strip()]
    print(f"\n{'═' * 100}\n  {len(rows)} RECORDED MODEL READINGS — no model call\n")
    seen = Counter()
    cross = Counter()
    examples = {}
    for row in rows:
        rung = by.get(row["rung"])
        if not rung:
            continue
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        lost = []
        try:
            raw = row["raw"] if isinstance(row["raw"], dict) else json.loads(row["raw"])
            goals = extract.to_goals(raw, row["request"], dropped=lost, world=world) or []
        except Exception:
            continue
        rep = g1.inspect(row["request"], goals, _kinds())
        outcome = str(row.get("outcome") or "?")
        for bucket in ("holes", "dropped", "mutated", "invented"):
            hits = getattr(rep, bucket)
            if hits:
                seen[bucket] += 1
                examples.setdefault(bucket, (row["rung"], row["column"], outcome,
                                             rep.findings()[0]))
        cross[(outcome, "FLAGGED" if not rep.legal else "legal")] += 1
    print(f"  {'what it caught':<14}{'readings':<11}first example")
    print("  " + "─" * 96)
    for bucket in ("holes", "dropped", "mutated", "invented"):
        ex = examples.get(bucket)
        tail = f"rung {ex[0]} {ex[1]} [{ex[2]}] {ex[3][:52]}" if ex else "—"
        print(f"  {bucket:<14}{seen[bucket]:<11}{tail}")
    print(f"\n  {'outcome':<20}{'gate 1':<12}readings")
    print("  " + "─" * 96)
    for (outcome, verdict), n in sorted(cross.items()):
        print(f"  {outcome:<20}{verdict:<12}{n}")
    good = sum(n for (o, v), n in cross.items() if o == "PASS" and v == "FLAGGED")
    bad_caught = sum(n for (o, v), n in cross.items() if o != "PASS" and v == "FLAGGED")
    bad_missed = sum(n for (o, v), n in cross.items() if o != "PASS" and v == "legal")
    print(f"\n  ⇒ of the readings that PASSED, {good} were flagged  (false alarms)")
    print(f"  ⇒ of the readings that did NOT pass, {bad_caught} flagged, {bad_missed} missed")


def main(argv=None) -> int:
    known_good()
    recorded()
    print(f"\n{'═' * 100}")
    print("  A GATE IS WORTH ITS FALSE-ALARM RATE. Read column 1 first — if the correct")
    print("  readings are accused, nothing in column 2 matters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
