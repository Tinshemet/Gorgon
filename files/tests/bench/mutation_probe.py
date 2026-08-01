"""mutation_probe.py — HOW MUCH DOES WORDING MATTER, measured where the sensitivity now is.

#19 asked for a phrasing-sensitivity arm. It was written when a MODEL AUTHORED PROGRAMS, so
the question was "does rewording change the program". It does not author any more: the
writer is deterministic and gives one program per goal set, four runs running. So rewording
can only change one thing — WHAT THE EXTRACTOR HEARS — and that is where this measures.

THE MUTATIONS ARE MECHANICAL AND MEANING-PRESERVING, which is the whole reason to prefer
them to hand-written paraphrases. `test_medusa` already holds that line: every identity name
survives, quoted values survive verbatim, one concept keeps one word. An author cannot audit
their own paraphrases for leakage because the leak is the part they thought was clarity —
rung 9's paraphrase says "sort out whatever is stopping that", which TELLS the model
something is broken on the rung whose whole point is diagnosis.

WHAT IS READ OUT. Per mutation kind: how often the goals still plan and still pass. A kind
that costs more than the others is a kind the extractor is brittle to, and the brittleness is
NAMED — `typo`, `reorder`, `verbose` — rather than averaged into one "robustness" number
that says nothing about what to fix.

    PYTHONPATH=. python3 -m tests.bench.mutation_probe [-n 1] [-k typo,terse]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict

from tests.bench import extract as _extract
from tests.bench import mutate
from tests.bench.repair_ab import grade
from tests.bench.rungs import RUNGS


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=1)
    ap.add_argument("-k", "--kinds", default="",
                    help="comma-separated mutation names (default: all)")
    ap.add_argument("-r", "--rung", type=int, action="append")
    a = ap.parse_args(argv)

    wanted = [k for k in (a.kinds.split(",") if a.kinds else mutate.MUTATIONS) if k]
    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    # THE UNMUTATED WORDING IS THE CONTROL, and it is measured in the same run rather than
    # taken from an earlier one — the model is not deterministic at temperature 0, so a
    # baseline from yesterday would put the model's drift into the mutation's column.
    columns = ["literal"] + wanted

    tally = defaultdict(Counter)
    for rung in rungs:
        for column in columns:
            text = rung.goal if column == "literal" else mutate.apply(rung.goal, column)
            for i in range(a.repeats):
                try:
                    raw = _extract.extract(text)
                except Exception as exc:
                    tally[column][f"ERROR:{type(exc).__name__}"] += 1
                    continue
                outcome = grade(_extract.to_goals(raw, text), rung)
                tally[column][outcome] += 1
                print(f"  {column:<9} rung {rung.n:>2} [{i + 1}/{a.repeats}] {outcome}",
                      flush=True)

    total = len(rungs) * a.repeats
    print(f"\n── phrasing sensitivity · {len(rungs)} rung(s) × n={a.repeats}")
    control = tally["literal"]["PASS"]
    print(f"{'wording':<10} {'pass':>5}  {'vs literal':>10}   failures")
    for column in columns:
        passed = tally[column]["PASS"]
        delta = "" if column == "literal" else f"{passed - control:+d}"
        fails = ", ".join(f"{k}×{v}" for k, v in sorted(tally[column].items())
                          if k != "PASS")
        print(f"{column:<10} {passed:>3}/{total:<3} {delta:>10}   {fails or '—'}")
    # NO SINGLE ROBUSTNESS NUMBER. A kind that costs more than the others is the thing to
    # fix, and an average hides exactly that.
    return 0


if __name__ == "__main__":
    sys.exit(main())
