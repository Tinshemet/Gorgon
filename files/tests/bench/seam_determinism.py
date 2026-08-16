"""seam_determinism.py — THE CONTROL THAT CAN ACTUALLY SAY "NOTHING CHANGED".

    PYTHONPATH=. python3 -m tests.bench.seam_determinism            # the fingerprint
    PYTHONPATH=. python3 -m tests.bench.seam_determinism --check    # is it even stable?

# ⇒⇒ WHY THIS FILE EXISTS, AND IT IS AN EMBARRASSING REASON

On 2026-08-16 seven commits landed on the seam, and after every one of them the claim *"all 14
rungs read identically"* was made from a diff of `pass1.run_scanned`.

**`run_scanned` CALLS THE MODEL.** Its own docstring says so — the model supplies the ANCHOR
and the EXISTENCE intent. So every one of those diffs was a MODEL-SAMPLED MEASUREMENT AT n=1
wearing the clothes of a deterministic control. It matched most times because the model is
fairly stable. That is luck, and it was reported as proof.

Measured the moment it was doubted: running the fourteen rungs through `run_scanned` in one
process, **2 runs in 6 give rung 10 a different `references` list**. Disable the model and it
is 6/6 identical. The variance was never code — it is temp-0 sampling, which
[[ladder-is-not-a-feedback-loop]] has said is not deterministic since the day it was written.

⇒ **SO THE FINGERPRINT COVERS ONLY FUNCTIONS WITH ZERO MODEL CALLS.** Everything here is a
  manifest lookup or a scan of the request. If a name is added to this probe, check first that
  nothing behind it can reach `engines.channel`.

⇒ **AND `--check` RUNS IT FIVE TIMES BEFORE ANYONE TRUSTS IT.** A control nobody has proved
  stable is the exact mistake this file exists to stop making twice; the probe must be shown to
  repeat before its output means anything. Model-stability first, always.

# ⇒ HOW TO USE IT ACROSS A CHANGE

    git stash                                                   # or a worktree at the base
    PYTHONPATH=. python3 -m tests.bench.seam_determinism > /tmp/before.txt
    git stash pop
    PYTHONPATH=. python3 -m tests.bench.seam_determinism > /tmp/after.txt
    diff /tmp/before.txt /tmp/after.txt

An empty diff means THE DETERMINISTIC SEAM IS UNCHANGED. It does NOT mean the ladder is
unchanged — the ladder runs the model twice over, and only a recorded n=3 baseline can speak to
that. Do not let this file be quoted for a claim it cannot support. That is how today went.
"""
from typing import List, Optional


def fingerprint(goals: Optional[List[str]] = None) -> List[str]:
    """Every model-free reading of every rung, as lines. Stable, or the probe is broken."""
    from planner.formula.legal import Board
    from orchestrator.seam.scan import (anchors_in, conditions_from, existence_from_determiner,
                                        kinds_named, magnitudes_in, quoted_clauses, scan_all,
                                        uncovered, clause_around)

    if goals is None:
        from tests.bench import rungs as R
        goals = [rung.goal for rung in R.RUNGS]

    board = Board()
    out: List[str] = []
    for n, goal in enumerate(goals, start=1):
        out.append(f"=== {n}  {goal!r}")
        anchors = anchors_in(goal, board)
        out.append(f"  anchors   {anchors}")
        out.append(f"  kinds     {sorted(kinds_named(goal, board))}")
        out.append(f"  quoted    {quoted_clauses(goal)}")
        out.append(f"  magnitude {magnitudes_in(goal, board)}")
        claimed = []
        for anchor in anchors:
            for got in scan_all(anchor, goal, board):
                claimed.append((got.start, got.end))
                out.append(f"  scan {anchor!r:14} span={got.span!r} n={got.count} "
                           f"cmp={got.comparator} kind={got.kind} id={got.identity!r}")
                out.append(f"       mods={got.modifiers!r}")
                out.append(f"       where={conditions_from(got.modifiers, got.kind, board, span=got.span)}")
                out.append(f"       clause={clause_around(goal, got.span)!r}")
                out.append(f"       exist={existence_from_determiner(got.span)}")
        out.append(f"  uncovered {uncovered(goal, claimed, board)}")
    return out


def main(argv=None) -> int:                                       # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--check" in argv:
        runs = [tuple(fingerprint()) for _ in range(5)]
        stable = len(set(runs)) == 1
        print(f"  5 runs, {len(set(runs))} distinct result(s) — "
              f"{'STABLE, the probe may be trusted' if stable else 'FLAKY, DO NOT DIFF WITH IT'}")
        return 0 if stable else 1
    print("\n".join(fingerprint()))
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
