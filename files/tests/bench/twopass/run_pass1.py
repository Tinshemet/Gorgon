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
from tests.bench import mutate as _mutate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--mutate", default="", metavar="ARM",
                    help="perturb each request before reading it. MUTATIONS preserve the "
                         "goal (filler, synonym, terse, verbose, reorder, casing, typo) — "
                         "the scoreboard reads normally. FRAMINGS do not (asked, framed) "
                         "— see the banner they print")
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

    # ⇒ A REFRAMED ARM INVERTS THE SCOREBOARD, so it is announced before a single number is
    #   printed rather than in a footnote. `vacuum_probe.py` voided a whole run because a
    #   grader marked a correct answer wrong, and this is the same hazard from the other
    #   side: every column below is "how much of the ACTIONABLE reading came back", which is
    #   the goal under a MUTATION and the DEFECT under a FRAMING.
    reframed = args.mutate in _mutate.FRAMINGS
    if args.mutate and args.mutate not in _mutate.MUTATIONS and not reframed:
        ap.error(f"unknown arm {args.mutate!r} — "
                 f"mutations {sorted(_mutate.MUTATIONS)} · framings {sorted(_mutate.FRAMINGS)}")

    board = Board()
    tally: Counter = Counter()
    print("=" * 104)
    print(f"ITEM 3 · PASS ONE AGAINST THE MODEL — "
          f"{'ANCHOR-AND-SCAN' if args.scanned else ('PAIRED name+type' if args.paired else 'separate questions')}"
          f"{'' if args.no_expand else ' + EXPAND'}"
          f"{'' if args.no_fold else ' + FOLD'}, "
          f"graded on structure, never on names")
    if args.mutate:
        print(f"{'FRAMING' if reframed else 'MUTATION'} ARM · {args.mutate}"
              + ("   (the goal is preserved; read the scoreboard normally)"
                 if not reframed else ""))
    if reframed:
        print("⚠ " + "─" * 101)
        print("⚠ THE GOAL IS NOT PRESERVED. THESE REQUESTS ASK ABOUT AN ACT, THEY DO NOT ORDER ONE.")
        print("⚠ The correct reading of a reframed request is NOT the rung's reading, so every")
        print("⚠ column below is INVERTED: a HIGH score is the DEFECT — it means the seam read an")
        print("⚠ information request as an instruction. `rows 0` is the outcome to hope for.")
        print("⚠ " + "─" * 101)
    print("=" * 104)

    for n, want in sorted(EXPECTED.items()):
        if args.only and n != args.only:
            continue
        # THE REQUEST IS PERTURBED; `want` IS NOT. Grading a reframed request against the
        # unchanged expectation is the whole measurement — it asks how much of a reading
        # the request no longer orders still came back.
        request = _mutate.apply(want.request, args.mutate) if args.mutate else want.request
        print(f"\n{'─' * 104}\nrung {n} · “{want.request[:88]}”")
        if request != want.request:
            print(f"    {'ASKED' if reframed else 'SENT '}  “{request}”")
        elif args.mutate:
            print(f"    ⚠ arm {args.mutate} left this rung UNCHANGED — it is a literal, not a cell")
        print(f"    want   names {want.identities}   conditions {want.conditions}   "
              f"sets>={want.sets}   residual={want.residual}   rows {want.rows}")
        for i in range(args.runs):
            trace: List = []
            rows = (run_scanned(request, board=board, model=args.model, trace=trace)
                    if args.scanned else
                    run_pass1(request, board=board, model=args.model, trace=trace,
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
    if reframed:
        # Repeated at the bottom because this is the half a person copies into a note.
        print(f"\n⚠ FRAMING ARM `{args.mutate}` — READ EVERY NUMBER ABOVE UPSIDE DOWN.")
        print("⚠ Nothing was ordered. A found name, a found condition and a declared row are")
        print("⚠ each the seam reading an information request as an instruction.")


if __name__ == "__main__":
    main()
