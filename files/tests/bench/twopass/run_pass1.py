"""PASS ONE OVER THE RUNG CORPUS — the scoreboard, not the machinery.

    PYTHONPATH=. python3 -m tests.bench.twopass.run_pass1 --scanned --runs 3

⇒ IT LIVED AT THE BOTTOM OF `pass1.py` UNTIL 2026-08-13, when that package moved out of the
  test tree. A production module that ships its own argparse scoreboard is how a bench gets
  installed on a customer's machine; the grader belongs beside the corpus it grades.
"""
import argparse
from collections import Counter
from typing import List

from planner.formula.legal import Board
from orchestrator.seam.pass1 import EXPECTED, grade, run_pass1, run_scanned


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--paired", action="store_true",
                    help="ask NAME and TYPE together — the cascade fix (REJECTED, kept for A/B)")
    ap.add_argument("--scanned", action="store_true",
                    help="ANCHOR-AND-SCAN: the model points, the code reads, the world decides")
    ap.add_argument("--forced-conditions", action="store_true",
                    help="ask ALL-or-SOME first — MEASURED WORSE (32 invented against 16) "
                         "because committing to SOME leaves no way to decline afterwards")
    ap.add_argument("--no-expand", action="store_true",
                    help="do NOT repair chunked names from the request")
    ap.add_argument("--no-fold", action="store_true",
                    help="do NOT fold repeated mentions — the pre-fold baseline")
    args = ap.parse_args()

    board = Board()
    tally: Counter = Counter()
    print("=" * 104)
    print(f"ITEM 3 · PASS ONE AGAINST THE MODEL — "
          f"{'ANCHOR-AND-SCAN' if args.scanned else ('PAIRED name+type' if args.paired else 'separate questions')}"
          f"{'' if args.no_expand else ' + EXPAND'}"
          f"{'' if args.no_fold else ' + FOLD'}, "
          f"graded on structure, never on names")
    print("=" * 104)

    for n, want in sorted(EXPECTED.items()):
        if args.only and n != args.only:
            continue
        print(f"\n{'─' * 104}\nrung {n} · “{want.request[:88]}”")
        print(f"    want   names {want.identities}   conditions {want.conditions}   "
              f"sets>={want.sets}   residual={want.residual}   rows {want.rows}")
        for i in range(args.runs):
            trace: List = []
            rows = (run_scanned(want.request, board=board, model=args.model, trace=trace)
                    if args.scanned else
                    run_pass1(want.request, board=board, model=args.model, trace=trace,
                              paired=args.paired, fold=not args.no_fold,
                              expand_names=not args.no_expand,
                              forced=args.forced_conditions))
            g = grade(rows, want)
            for row in rows:
                mark = "  ⇐ RESIDUAL" if row.residual else ""
                where = ", ".join(f"{k}={v}" for k, v in row.where.items()) or "—"
                print(f"      {row.name[:28]:<30} {row.object_type:<14} {where:<26} "
                      f"{row.existence}{mark}")
            print(f"    run {i + 1}  names {g['identities']}  conditions {g['conditions']}  "
                  f"invented {g['invented']}  sets {g['sets']}  residual {g['residual']}  "
                  f"rows {g['rows']} (want {want.rows})  folded {g['folded']}")
            tally["identities_ok"] += g["identities_ok"]
            tally["folded"] += g["folded"]
            tally["extra_rows"] += max(0, g["extra_rows"])
            tally["conditions_ok"] += g["conditions_ok"]
            tally["sets_ok"] += g["sets_ok"]
            tally["residual_ok"] += g["residual_ok"]
            tally["invented"] += g["invented"]
            tally["new"] += g["new"]
            tally["cells"] += 1

    c = max(tally["cells"], 1)
    print(f"\n{'=' * 104}")
    print(f"  cells                    {tally['cells']}")
    print(f"  named things found       {tally['identities_ok']}/{c}")
    print(f"  SURPLUS rows declared    {tally['extra_rows']}    (over-declaration)")
    print(f"  mentions FOLDED as refs  {tally['folded']}    (repeat mentions recognised)")
    print(f"  every condition found    {tally['conditions_ok']}/{c}")
    print(f"  groups declared as sets  {tally['sets_ok']}/{c}")
    print(f"  residual correct         {tally['residual_ok']}/{c}   "
          f"⇐ rung 11 is the only one that can score TRUE here")
    print(f"  conditions invented      {tally['invented']}    (P4 said under- beats over-fill)")
    print(f"  rows called NEW          {tally['new']}    (P5: near-zero means MY enum "
          f"ordering backfired)")


if __name__ == "__main__":
    main()
