"""translation_table.py — what does the AI actually READ each rung as? No writer, no run.

    PYTHONPATH=. python3 tests/bench/translation_table.py [-n 3] [-r 8]

## THE READING, THE ASSISTANT AND THE GATE — AND NOTHING RUNS

Extraction, `to_goals`, the context assistant and the reading gate. A plan IS made, because
the assistant reads a program's CALLS and the gate asks what the reading WOULD do — and
`cover` plans against a scratch copy, so nothing real is touched and no rung checker is
consulted. **Nothing is executed.**

## IT DOUBLES AS THE NOISE MEASUREMENT

Each request is read `n` times and the DISTINCT readings are counted. That single column
answers the first of the four candidates in [[gorgon-why-the-noise]]: if a request yields one
reading every time, the model is stable on it and any run-to-run movement is downstream —
the gate, the loop, or the hint. If it yields three, this is the floor and everything above
it is amplification.

**READ THE `n=` COLUMN FIRST.** A rung that translates DIFFERENTLY on every draw cannot be
diagnosed from any single run of anything, and several arguments made on 2026-08-05 and 08-06
were about cells in exactly that state.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from engines import extract
from planner import reading_gate as gate
from engines.rig import translator as _make_translator
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

try:                                    # the only ground truth for a READING here
    from tests.test_ghost_writer import GOALS as KNOWN
except Exception:                       # pragma: no cover
    KNOWN = {}


def _world(rung) -> SimWorld:
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    return world


def _short(goal: dict) -> str:
    """One goal, compact enough for a table cell."""
    def sel(s):
        if not isinstance(s, dict):
            return str(s)
        bits = [f"{k}={v}" for k, v in s.items() if k != "kind"]
        return f"{s.get('kind')}" + (f"[{','.join(bits)}]" if bits else "")
    if "every" in goal:
        must = ",".join(f"{k}={v}" for k, v in (goal.get("must") or {}).items())
        return f"every {sel(goal['every'])} must {must}"
    if "per" in goal:
        return f"per {sel(goal['per'])} make {goal.get('make')}"
    if "observe" in goal:
        return f"observe {sel(goal['observe'])} {goal.get('fact')}"
    cmp_ = next((f"{k} {goal[k]}" for k in ("eq", "gte", "lte") if k in goal), "?")
    return f"count {sel(goal.get('select'))} {cmp_}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-r", "--rung", type=int, action="append")
    args = ap.parse_args(argv)
    wanted = set(args.rung or [r.n for r in RUNGS])

    _translate = _make_translator()
    print(f"\n{'rung':<5}{'arm':<4}{'n=':<4}{'match':<10}{'gate':<8}{'gates hit':<12}reading "
          f"(most common of {args.repeats} draws)")
    print("─" * 126)
    unstable = 0
    scores = Counter()
    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm, request in (("lit", rung.goal), ("par", rung.paraphrase)):
            if not request:
                continue
            readings, store = Counter(), {}
            # ⇒ EVERY DRAW, KEPT, BECAUSE GATE 4 JUDGES THE SET AND NOT A MEMBER OF IT.
            #   The first port of this harness called gate 4 once per draw with a single
            #   reading — and one reading cannot disagree with itself, so it fired 0 times
            #   while the `n=` column beside it reported 5 rows that DID disagree. The same
            #   `built-and-never-called` shape fixed in `engines/rig.py` the same hour,
            #   reproduced here while copying it across. The draws were always in this loop.
            for _ in range(args.repeats):
                world = _world(rung)
                # ⇒ THE REAL FRONT SEAM, NOT A REIMPLEMENTATION OF IT.
                #
                #   This harness used to call `extract`, `to_goals` and each gate by hand —
                #   which measured a COPY of production's wiring and would drift from it
                #   silently. `rig.translator()` is what the orchestrator actually mounts, so
                #   everything wired into it is exercised here: gate 1's repairs applied, gate
                #   2's supplied probe, gate 4's second draw, and the verdicts on
                #   `Answer.gates`.
                #
                #   WHAT IT STILL DOES NOT REACH: `_restandardise` lives in the ORCHESTRATOR,
                #   one layer up, so the re-ask is NOT measured here. This table is the
                #   reading and the gates; it is not the whole front door.
                answer = _translate(request, world)
                goals = list(answer.components or [])
                lost = list(answer.dropped or [])
                flags = {g: (ok is False)
                         for g, ok in (answer.gates or {}).items() if g != "reask"}
                warn = list(answer.asks or []) + list(answer.fetch or [])
                verdict = gate.Verdict(
                    gate.PROCEED if not any(flags.values()) else gate.ASK,
                    "+".join(sorted(k for k, v in flags.items() if v)) or "",
                    detail="; ".join(answer.illegal or []))
                vetoed = (answer.gates or {}).get("reask") is False
                if vetoed:
                    warn = ["gate 4: reads more than one way — not re-asking"] + warn
                key = json.dumps([_short(g) for g in goals], sort_keys=True)
                readings[key] += 1
                store[key] = (goals, lost, verdict, warn)
            distinct = len(readings)
            unstable += distinct > 1
            top, _n = readings.most_common(1)[0]
            goals, lost, verdict, warn = store[top]
            flag = "  " if distinct == 1 else "!!"
            mark = {gate.PROCEED: "ok", gate.ASK: "ASK", gate.REFUSE: "REFUSE"}[verdict.outcome]
            # AGAINST THE KNOWN-GOOD READING, which is the only ground truth for a
            # TRANSLATION anywhere here — the hand-written goals the writer serves 13/13.
            truth = {_short(g) for g in (KNOWN.get(rung.n) or [])}
            mine = {_short(g) for g in goals}
            if not truth:
                match, bucket = "?", "?"
            elif truth == mine:
                match, bucket = "same", "same"
            elif truth & mine:
                match, bucket = f"partial {len(truth & mine)}/{len(truth)}", "partial"
            else:
                match, bucket = "DIFF", "DIFF"
            scores[bucket] += 1
            head = (f"{rung.n:<5}{arm:<4}{str(distinct) + flag:<4}{match:<10}{mark:<8}"
                    f"{verdict.caught or '-':<12}")
            if not goals:
                print(head + f"— nothing kept: {'; '.join(lost)[:52] or 'no reading'}")
            else:
                for i, g in enumerate(goals):
                    print((head if i == 0 else " " * 51) + _short(g)[:72])
                for m in sorted(truth - mine):
                    print(" " * 51 + f"MISSING: {m[:63]}")
            if warn:
                print(" " * 51 + f"assistant: {warn[0][:63]}")
    print("─" * 100)
    print("   vs the known-good reading: "
          + " · ".join(f"{k} {v}" for k, v in scores.most_common()))
    print(f"   `n=` is DISTINCT readings from {args.repeats} identical calls. "
          f"{unstable} row(s) marked !! disagree with themselves.")
    print("   A ROW THAT DISAGREES WITH ITSELF CANNOT BE DIAGNOSED FROM ONE RUN OF ANYTHING.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
