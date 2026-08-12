"""PASS TWO OVER THE RUNG CORPUS — what has to be done, graded per rung.

    PYTHONPATH=. python3 -m tests.bench.twopass.run_pass2 --runs 3

⇒ EXTRACTED FROM `pass2.py` ON 2026-08-13, with `run_pass1`/`run_chain`. The lab it needs is
  the BENCH's, so a runner that lives in the bench needs no upward import at all — which is
  the argument for moving it rather than declaring the edge it used to create.
"""
import argparse
from collections import Counter

from planner.formula.legal import Board
from orchestrator.seam import pass1
from orchestrator.seam.pass2 import WANT, grade, operations_for, symbol_table
from tests.bench.twopass.metrics import Lab


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3, help="rule V3 — never diagnose from n=1")
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--handles", default="derived", choices=("derived", "span"),
                    help="`span` offers pass 1's raw span as the enum member — the thing the "
                         "original probe never tested")
    args = ap.parse_args()

    board = Board()
    tally: Counter = Counter()
    print("=" * 100)
    print(f"PASS 2 · WHAT HAS TO BE DONE — handles={args.handles}, n={args.runs}")
    print("=" * 100)

    for n, want in sorted(pass1.EXPECTED.items()):
        if args.only and n != args.only:
            continue
        rows = pass1.settle_with_world(
            pass1.run_scanned(want.request, board=board, model=args.model), Lab(), board)
        table = symbol_table(rows, board, args.handles)
        print(f"\n{'─' * 100}\nrung {n} · “{want.request[:78]}”")
        for sym in table:
            print(f"    {sym.handle:<18} {sym.row.object_type:<10} {sym.definition:<40} "
                  f"{sym.settled}")
        expected = WANT.get(n)
        print(f"    WANT  {expected if expected else '— not keyed, reported only'}")
        for i in range(args.runs):
            got = operations_for(want.request, rows, board, model=args.model,
                                 handles=args.handles)
            steps = [(o.operator, o.on, o.value) for o in got]
            if expected is None:
                print(f"    run {i + 1}  {steps}")
                continue
            verdict = grade(got, expected)
            tally[verdict.split("/")[0] if "/" in verdict else verdict] += 1
            tally["cells"] += 1
            print(f"    run {i + 1}  {verdict:<12} {steps}")

    print(f"\n{'=' * 100}")
    for verdict, count in sorted(tally.items()):
        if verdict != "cells":
            print(f"    {verdict:<12} {count}/{tally['cells']}")


if __name__ == "__main__":
    main()
