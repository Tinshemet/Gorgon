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
    grounding  UNGROUNDED

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

from . import env_stamp
from .ladder import BENCH_MODEL
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
    # THE SAME EVENT, TWO OWNERS. A repair lost to trailing prose is a correct answer our
    # reader threw away; a repair lost to malformed JSON is the decoder failing. One is
    # ours to fix in a line, the other is the channel — and under a single code, fixing
    # the first would have taken credit for the second.
    "REPAIR_UNDELIVERED:trailing_prose": "harness",
    "REPAIR_UNDELIVERED:empty": "channel",
    "REPAIR_UNDELIVERED:malformed": "channel",
    "CRASHED": "harness",
    "CHECKER_DISPUTE": "harness",
    # ITS OWN LAYER, because none of the other four owns it. The program is well-formed,
    # the model reasoned to a world the checker accepts, the channel delivered and the
    # harness ran it — and the program still vouches for nothing. Measured 2026-07-31:
    # para:8 and para:11 both passed 3/3 while printing "no ENSURE, operator would be
    # asked here", so a program that acted blind scored exactly as one that verified.
    #
    # THAT CONTRADICTS THE LANGUAGE'S OWN CLAIM ABOUT ITSELF. Decision 6 says observed
    # attributes come out of the findings ledger and are never inferred, and A5 tightened
    # the bench's `reach` on the rule that unverified is not done. The ladder was not
    # holding programs to the property the language is built around, and skipping ENSURE
    # was a free lane: never punished, always cheaper.
    #
    # READ THE COST HONESTLY. The author prompt does NOT currently demand grounding, so
    # cells failing here are being scored against a rule they were never told. That is
    # the [[gorgon-schema-withholding]] trap, and the follow-up is a MEASUREMENT — does
    # one prompt sentence recover them — not an assumption either way.
    "UNGROUNDED": "grounding",
    # THE MODEL'S, NOT THE HARNESS'S. This is the case CHECKER_DISPUTE used to absorb: the
    # program's witness "passed" and the checker failed, but the witness could not have
    # failed, so there were never two verdicts to weigh. rung 11 inverted its own condition
    # and asserted that the member it was iterating existed — a genuine reasoning error
    # that read for a day as a possible bench defect.
    "VACUOUS_WITNESS": "model",
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


def goal_asked(rung, column):
    """The exact sentence a cell was measured on.

    ONE definition, taken the same way `author_probe` takes it (`rung.paraphrase or
    rung.goal` under -p), so the baseline cannot record a question different from the one
    that was asked. The `or` matters: a rung with no paraphrase is measured on its literal
    goal in BOTH columns, and recording the None would make the two columns look like
    different questions when they are the same one.
    """
    return (rung.paraphrase or rung.goal) if column == "para" else rung.goal


def measure(rungs, columns, n, extra=()):
    """Run each cell `n` times. Returns {"lit:4": {"outcomes": {...}, "n": 3, ...}}."""
    from . import author_probe
    by_n = {r.n: r for r in RUNGS}
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
                # THE QUESTION, stored beside the answer. Without it a rewording reads as
                # PASS RATE DOWN forever, and C4, E5 and F1 all imply rewording. The TEXT
                # rather than a hash of it: the file is 26 cells, and a reader diffing a
                # baseline wants to see WHICH words moved, which a digest cannot say.
                "goal": goal_asked(by_n[rung], column),
                "outcomes": dict(outcomes),
                "passes": sum(n for c, n in outcomes.items() if c in SUCCESS),
                "calls_min": min(calls) if calls else None,
                "artifacts": sum(c.get("artifacts") or 0 for c in sink),
                # EVERY DISTINCT DETAIL PER CODE, not the last one. Keeping a single
                # detail made `lit:7` read as a malformed-JSON failure because that was
                # what the third run happened to say, and I classified the cell as a
                # channel problem on it. Re-measured, all three runs were trailing prose —
                # the harness. A summary that keeps one sample of three is how a cell gets
                # attributed to the wrong layer, which is the one thing this file exists
                # to get right.
                "details": {code: sorted({c["detail"] for c in sink
                                          if c["outcome"] == code and c.get("detail")})
                            for code in outcomes},
            }
            print(f"  {key:9} {dict(outcomes)}", flush=True)
    return cells


def flaky(cell):
    """A cell whose own history is not unanimous. Reported, never treated as a move."""
    return 0 < passes_of(cell) < cell["n"]


def diff(base, now, scope=None):
    """Cells that left the band their own history recorded.

    Two kinds of move, and they are different news. A PASS-RATE move is what a scoreboard
    shows. A CLASS move is a cell failing for a different REASON at the same rate — going
    from GOAL_UNMET to BAD_JSON means the model stopped being the problem and the channel
    started, which a pass count cannot say.
    """
    # `scope` is what THIS INVOCATION SET OUT TO MEASURE, derived from the arguments and
    # never from what came back. A partial check reported the other 24 cells as
    # regressions — the same fault as `record` overwriting the file, in the reader instead
    # of the writer. Scoping by INTENT rather than by results keeps the case that matters:
    # a cell that was asked for and produced nothing is still NOT MEASURED, so a silently
    # vanishing cell cannot hide behind a narrow run.
    keys = set(base) | set(now)
    if scope is not None:
        keys = {k for k in keys if k in scope}
    moves = []
    for key in sorted(keys):
        b, a = base.get(key), now.get(key)
        if b is None:
            moves.append((key, "NEW CELL", "", dict(a["outcomes"])))
            continue
        if a is None:
            moves.append((key, "NOT MEASURED", dict(b["outcomes"]), ""))
            continue
        # A DIFFERENT QUESTION IS NOT A REGRESSION. Reword a rung and its pass rate moves
        # for a reason the rate cannot express, so the cell is reported as VOID and its
        # numbers are not compared at all — reporting a move here would be a false
        # accusation with a number attached, which is worse than silence. A baseline
        # predating this field says so explicitly rather than passing for a match.
        if "goal" not in b:
            moves.append((key, "GOAL UNRECORDED", "baseline predates the goal field",
                          "not compared"))
            continue
        if b["goal"] != a.get("goal"):
            moves.append((key, "GOAL CHANGED — baseline void",
                          b["goal"][:60], (a.get("goal") or "")[:60]))
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
    # D1'S LAST UNTESTED CANDIDATE, exposed so it can be run against the recorded baseline.
    # The eight few-shot examples are 32% of the author's prompt (2308 of 7113 chars), and
    # 2026-07-30 established that this prompt is at its limit — ONE added sentence moved
    # five cells from 3/3 to 0/3. Ruled out already: reply size, the eleven-branch oneOf,
    # num_ctx, objection length, and the quantifier router (measured: every FAILING cell
    # routes not/any/all, which license all seven ops, so it narrows nothing that matters).
    p.add_argument("--no-shots", action="store_true",
                   help="ablate the few-shot examples — isolates what they contribute")
    # THE MODEL, AND IT WAS MISSING. `record` and `check` both stamp the conditions with
    # `env_stamp.stamp(a.model)` — an attribute this parser never declared, so BOTH
    # subcommands raised AttributeError. `record` raised AFTER measuring all 26 cells, which
    # is the worst possible place: the run cost its full 13 minutes, printed a complete
    # table, and wrote nothing. The env feature had never once executed on this path.
    p.add_argument("-m", "--model", default=BENCH_MODEL,
                   help="the model to measure AND to stamp — one flag, so a baseline cannot "
                        "name conditions the run did not use")
    p.add_argument("--replace", action="store_true",
                   help="rewrite the whole baseline instead of merging into it. Only for "
                        "a deliberate reset — a partial record normally MERGES, so "
                        "re-measuring one cell cannot drop the others.")
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
    # FORWARDED, not merely stamped. `measure` passes `extra` through to the probe, which
    # otherwise falls back to its own default — so `-m other-model` would have measured
    # BENCH_MODEL while recording `other-model` as the conditions. A baseline that names a
    # model it did not run is worse than one that names none.
    extra = (["--mutate", a.mutate] if a.mutate else []) + ["-m", a.model]
    if a.no_shots:
        extra.append("--no-shots")
    if a.runs < 2:
        print("!! n=1 — this measures a sample, NOT a regression. Cells flip on their own.")
    print(f"measuring {len(rungs)} rung(s) × {len(columns)} column(s) × n={a.runs}\n")
    cells = measure(rungs, columns, a.runs, extra)
    print()
    print(table(cells, f"THIS RUN (n={a.runs} per cell)"))

    if a.action == "record":
        # MERGE, NEVER REPLACE. `record -r 7 -c lit` re-measures one cell; overwriting the
        # file would silently drop the other 25, and the next `check` would report them all
        # as NEW CELL — a baseline destroyed by the command meant to maintain it. Losing
        # measurements is exactly what a regression gate cannot do, so replacing the whole
        # file has to be asked for out loud.
        kept = {}
        if os.path.exists(BASELINE) and not a.replace:
            kept = json.load(open(BASELINE)).get("cells", {})
        merged = {**kept, **cells}
        json.dump({"recorded": "manual", "runs_per_cell": a.runs,
                   # THE CONDITIONS, beside the numbers they produced. A baseline stores a
                   # premise, not only a verdict — same argument as the goal-hash.
                   "env": env_stamp.stamp(a.model), "cells": merged},
                  open(BASELINE, "w"), indent=1)
        updated, carried = len(cells), len(merged) - len(cells)
        print(f"\n   baseline written: {BASELINE}")
        print(f"   {updated} cell(s) re-measured, {carried} carried forward unchanged"
              if carried else f"   {updated} cell(s) recorded")
        return 0

    if not os.path.exists(BASELINE):
        print("\n   NO BASELINE to check against — run `record` first")
        return 1
    saved = json.load(open(BASELINE))
    base = saved["cells"]
    # CONDITIONS FIRST, because a cell that moved under different conditions has not been
    # shown to have regressed. Reported, never fatal: the gate still runs and still prints
    # its moves, but a reader now knows whether the two columns are comparable at all.
    # Found the hard way on 2026-07-30 — a rung went 0/3 to 3/3 on byte-identical code and
    # nothing in either log said what the runs had in common.
    changed = env_stamp.differs(saved.get("env"), env_stamp.stamp(a.model))
    if changed:
        print("\n── CONDITIONS CHANGED SINCE THE BASELINE — moves below may not be regressions")
        for line in changed:
            print(f"   {line}")
    scope = {f"{col}:{r}" for col in columns for r in rungs}
    moves = diff(base, cells, scope)
    skipped = len(set(base) - scope)
    if skipped:
        print(f"\n   ({skipped} baseline cell(s) outside this run's scope — not compared)")
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
