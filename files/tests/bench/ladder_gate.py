"""
ladder_gate.py — the ladder as a REGRESSION GATE, with failures attributed to a layer.

`run_all.py` exists so no unit suite can rot. There was no equivalent for the ladder: it
was run ad hoc, on whichever rungs the author had in mind, usually once. Two consequences,
both of which cost a full day:

  * a change to text that ships on EVERY authoring call was measured on 6 of 13 rungs and
    reported as "the scoreboard did not move";
  * three separate cells were diagnosed as regressions caused by that change, and all
    three dissolved at n=3. Rung 4 fails roughly one run in three ON AN UNCHANGED BUILD.
    Read at n=1, that is indistinguishable from "my change broke rung 4" — so the fix
    perturbs the prompt, the next single run shows a different cell flipped, and the
    whack-a-mole is manufactured by the measurement rather than by the system.

So this stores a RATE, never a verdict, and reports a cell as moved only when it leaves
the band its own history recorded.

WHY THE REASON CODES. PASS/FAIL/INVALID collapses four independent failure points into
one word — the LANGUAGE, the MODEL, the HARNESS, and the person reading the output. Every
outcome here names which one owns it:

    layer      codes
    ─────────  ────────────────────────────────────────────────────────────────
    model      GOAL_UNMET · UNRECOVERED · OVER_BUDGET
    channel    NO_EMISSION · BAD_JSON:trailing_prose · BAD_JSON:malformed
    language   GATE_REFUSED · (UNRECOVERED's detail carries the rule that refused)
    harness    REPAIR_UNDELIVERED · CRASHED · CHECKER_DISPUTE

Two of those exist because a real failure was invisible without them.
REPAIR_UNDELIVERED: rung 11's repair produced the correct program and explained itself in
prose, json.loads threw on the trailing sentence, and the fix was discarded — which read
for a day as a model that could not act on an objection. CHECKER_DISPUTE: the program's
own ENSURE/ACHIEVE vouches for the end state and the rung's checker disagrees; one of them
is wrong and a run reporting only the checker cannot say it might be the checker.

THE FOURTH FAILURE POINT IS THE REPORT ITSELF, so the table is GENERATED here and every
number is printed with the n it came from. Anyone can re-run this and get the same table
without taking a summary on trust.

Run:
    PYTHONPATH=. python3 -m tests.bench.ladder_gate record -n 3     # write the baseline
    PYTHONPATH=. python3 -m tests.bench.ladder_gate check  -n 3     # diff against it
    PYTHONPATH=. python3 -m tests.bench.ladder_gate show            # print the baseline
"""
import argparse
import json
import os
import sys
from collections import Counter

from .rungs import RUNGS

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ladder_baseline.json")

# Which layer owns each outcome. A code absent here is UNATTRIBUTED and says so rather
# than being quietly filed under the model — the same unknown-is-not-false rule the
# observed attributes are built on.
LAYER = {
    "PASS": "-",
    "OVER_BUDGET": "model",
    "GOAL_UNMET": "model",
    "UNRECOVERED": "model",
    "NO_EMISSION": "channel",
    "BAD_JSON:trailing_prose": "channel",
    "BAD_JSON:malformed": "channel",
    "GATE_REFUSED": "language",
    "REPAIR_UNDELIVERED": "harness",
    "CRASHED": "harness",
    "CHECKER_DISPUTE": "harness",
}


# WHAT COUNTS AS ACHIEVING THE GOAL. OVER_BUDGET means the rung's own checker PASSED and
# the program simply cost more than its recorded best — scoring it as a miss reports a
# solved rung as a failure, which is the over-reporting this whole file exists to stop.
# Cost is a separate axis and gets its own line; it is not a pass/fail. It is also not yet
# trustworthy: `rung.best` is stale in the loose direction and absent on 8 of 13 rungs, so
# treating it as a failure would fail cells against a number nobody has re-earned.
SUCCESS = {"PASS", "OVER_BUDGET"}


def layer_of(code):
    return LAYER.get(code, "UNATTRIBUTED")


def passes_of(cell):
    """Runs that achieved the goal. ONE definition, so the table, the diff and the flaky
    rule cannot disagree about what a pass is — which is exactly how a stored `passes`
    field went stale the moment the definition changed."""
    return sum(n for code, n in cell["outcomes"].items() if code in SUCCESS)


def over_budget_of(cell):
    return cell["outcomes"].get("OVER_BUDGET", 0)


def measure(rungs, columns, n, extra=()):
    """Run each cell `n` times. Returns {"lit:4": {"outcomes": {...}, "n": 3, ...}}."""
    from . import author_probe
    cells = {}
    for column in columns:
        for rung in rungs:
            key = f"{column}:{rung}"
            sink = []
            for _ in range(n):
                argv = ["-r", str(rung), "--execute"] + list(extra)
                if column == "para":
                    argv.append("-p")
                author_probe._SANITISED.clear()
                author_probe.main(argv, sink=sink)
            outcomes = Counter(c["outcome"] for c in sink)
            calls = [c["calls"] for c in sink if c.get("calls") is not None]
            cells[key] = {
                "n": len(sink),
                "outcomes": dict(outcomes),
                "passes": sum(n for c, n in outcomes.items() if c in SUCCESS),
                "calls_min": min(calls) if calls else None,
                "artifacts": sum(c.get("artifacts") or 0 for c in sink),
                # A DETAIL PER CODE, kept so a moved cell can be read without re-running.
                "details": {c["outcome"]: c["detail"] for c in sink if c.get("detail")},
            }
            print(f"  {key:9} {dict(outcomes)}", flush=True)
    return cells


def flaky(cell):
    """A cell whose own history is not unanimous. Reported, never treated as a move."""
    return 0 < passes_of(cell) < cell["n"]


def diff(base, now):
    """Cells that left the band their own history recorded.

    Two kinds of move, and they are different news. A PASS-RATE move is what a scoreboard
    shows. A CLASS move is a cell failing for a different REASON at the same rate — going
    from GOAL_UNMET to BAD_JSON means the model stopped being the problem and the channel
    started, which a pass count cannot say.
    """
    moves = []
    for key in sorted(set(base) | set(now)):
        b, a = base.get(key), now.get(key)
        if b is None:
            moves.append((key, "NEW CELL", "", dict(a["outcomes"])))
            continue
        if a is None:
            moves.append((key, "NOT MEASURED", dict(b["outcomes"]), ""))
            continue
        # A CELL THAT RECORDED NOTHING IS A HARNESS FAULT, never a clean cell. The
        # probe used to `continue` past its own sink on a non-result, so a cell whose every
        # reply was malformed JSON came back as {} — three channel failures reported as an
        # empty line, and then a ZeroDivisionError here. Both directions are named rather
        # than averaged: n=0 is an absence of evidence and cannot be divided into a rate.
        if not a["n"] or not b["n"]:
            moves.append((key, "NO RECORD (harness)",
                          f"{passes_of(b)}/{b['n']}", f"{passes_of(a)}/{a['n']}"))
            continue
        bp, ap = passes_of(b) / b["n"], passes_of(a) / a["n"]
        # A flaky cell has to move by more than one run to count, or its own noise
        # reports itself as a regression every time.
        room = (1.0 / a["n"]) if flaky(b) else 0.0
        if ap < bp - room:
            moves.append((key, "PASS RATE DOWN",
                          f"{passes_of(b)}/{b['n']}", f"{passes_of(a)}/{a['n']}"))
        elif ap > bp + room:
            moves.append((key, "pass rate up",
                          f"{passes_of(b)}/{b['n']}", f"{passes_of(a)}/{a['n']}"))
        else:
            fresh = set(a["outcomes"]) - set(b["outcomes"]) - SUCCESS
            if fresh:
                moves.append((key, "NEW FAILURE REASON",
                              ",".join(sorted(set(b["outcomes"]) - SUCCESS)) or "none",
                              ",".join(sorted(fresh))))
    return moves


def table(cells, title):
    """The report, GENERATED — every number carries the n it came from."""
    out = [f"── {title}", ""]
    out.append(f"   {'cell':9} {'n':>2}  {'passes':>7}  outcomes")
    for key in sorted(cells, key=lambda k: (k.split(':')[0], int(k.split(':')[1]))):
        c = cells[key]
        marks = " ".join(f"{k}×{v}" for k, v in sorted(c["outcomes"].items()))
        flag = ("  !! NO RECORD — harness lost this cell" if not c["n"]
                else "  ~flaky" if flaky(c) else "")
        out.append(f"   {key:9} {c['n']:>2}  {passes_of(c):>3}/{c['n']:<3}  {marks}{flag}")
    by_layer = Counter()
    for c in cells.values():
        for code, k in c["outcomes"].items():
            if code not in SUCCESS:
                by_layer[layer_of(code)] += k
    total_runs = sum(c["n"] for c in cells.values())
    total_pass = sum(passes_of(c) for c in cells.values())
    over = sum(over_budget_of(c) for c in cells.values())
    out += ["", f"   RUNS {total_runs} · GOAL ACHIEVED {total_pass}/{total_runs}",
            "   failures by layer: "
            + (", ".join(f"{l}={n}" for l, n in by_layer.most_common()) or "none")]
    # COST IS A SEPARATE AXIS, and it is REPORTED rather than counted, because rung.best is
    # stale in the loose direction and absent on 8 of 13 rungs. A baseline learned from
    # observed passing runs would certify whatever the model already does.
    out.append(f"   over budget (goal met, cost above `best`): {over}"
               + ("  — `best` is stale/absent on most rungs; reported, not counted"
                  if over else ""))
    out.append("   (every figure above is from this run; n is stated per cell)")
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="ladder regression gate")
    p.add_argument("action", choices=["record", "check", "show"])
    p.add_argument("-n", "--runs", type=int, default=3,
                   help="runs per cell — 1 is NOT a regression check and is labelled so")
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-c", "--column", action="append", choices=["lit", "para"])
    p.add_argument("--mutate")
    a = p.parse_args(argv)

    if a.action == "show":
        if not os.path.exists(BASELINE):
            print("no baseline recorded")
            return 1
        saved = json.load(open(BASELINE))
        print(table(saved["cells"], f"BASELINE recorded {saved.get('recorded', '?')}"))
        return 0

    rungs = a.rung or [r.n for r in RUNGS]
    columns = a.column or ["lit", "para"]
    extra = ["--mutate", a.mutate] if a.mutate else []
    if a.runs < 2:
        print("!! n=1 — this measures a sample, NOT a regression. Cells flip on their own.")
    print(f"measuring {len(rungs)} rung(s) × {len(columns)} column(s) × n={a.runs}\n")
    cells = measure(rungs, columns, a.runs, extra)
    print()
    print(table(cells, f"THIS RUN (n={a.runs} per cell)"))

    if a.action == "record":
        json.dump({"recorded": "manual", "runs_per_cell": a.runs, "cells": cells},
                  open(BASELINE, "w"), indent=1)
        print(f"\n   baseline written: {BASELINE}")
        return 0

    if not os.path.exists(BASELINE):
        print("\n   NO BASELINE to check against — run `record` first")
        return 1
    base = json.load(open(BASELINE))["cells"]
    moves = diff(base, cells)
    print()
    print("── REGRESSION CHECK")
    if not moves:
        print("   no cell left the band its own history recorded")
        return 0
    for key, what, was, now in moves:
        print(f"   {key:9} {what:20} was {was!s:22} now {now!s}")
    bad = [m for m in moves if m[1] in ("PASS RATE DOWN", "NEW FAILURE REASON",
                                        "NOT MEASURED", "NO RECORD (harness)")]
    print(f"\n   {len(bad)} regression(s), {len(moves) - len(bad)} improvement(s)")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
