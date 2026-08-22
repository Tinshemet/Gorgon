"""THE WHOLE CHAIN OVER THE RUNG CORPUS — request in, verdict out, one line per rung.

    PYTHONPATH=. python3 -m tests.bench.twopass.run_chain
    PYTHONPATH=. python3 -m tests.bench.twopass.run_chain --no-lab

⇒ EXTRACTED FROM `pipeline.py` ON 2026-08-13. This is the run that produces the SERVE/BOUNCE/
  ASK tally quoted in every handover, so it is a measuring instrument and belongs with the
  other instruments.
"""
import argparse
from typing import Dict

from planner.formula.legal import Board
from orchestrator.languages.english.seam import pass1
from orchestrator.languages.english.seam.pipeline import ASK, BOUNCE, REFUSE, SERVE, run
from tests.bench.twopass.metrics import Lab


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--retries", type=int, default=1,
                    help="how many times a BOUNCE is handed back to the model")
    ap.add_argument("--no-lab", action="store_true",
                    help="run with no world at all — every bare name stays kindless")
    args = ap.parse_args()

    board = Board()
    world = None if args.no_lab else Lab()
    tally: Dict[str, int] = {}

    print("=" * 100)
    print(f"THE WHOLE CHAIN{'  ·  NO LAB' if args.no_lab else '  ·  with a lab'}")
    print("=" * 100)

    for n, want in sorted(pass1.EXPECTED.items()):
        if args.only and n != args.only:
            continue
        got = run(want.request, board=board, world=world, model=args.model,
                  retries=args.retries)
        tally[got.outcome] = tally.get(got.outcome, 0) + 1
        print(f"\n{'─' * 100}\nrung {n} · “{want.request[:74]}”")
        print(f"    declared   {', '.join(got.handles) or '—'}")
        print(f"    operations {[(o.operator, o.on, o.value) for o in got.operations] or '—'}")
        for r in got.repairs:
            print(f"      REPAIRED {r}")
        for n in got.notices:
            print(f"      NOTICE   {n}")
        if got.suggested:
            print(f"    SUGGESTED  {[(o.operator, o.on, o.value) for o in got.suggested]}")
        print(f"    conditions {got.conditions or '—'}")
        for a in got.asks:
            print(f"      ASK     {a[:92]}")
        for b in got.bounces:
            print(f"      BOUNCE  {b[:92]}")
        print(f"    ⇒ {got.outcome}")

    print(f"\n{'=' * 100}")
    for outcome in (SERVE, BOUNCE, ASK, REFUSE):
        if tally.get(outcome):
            print(f"    {outcome:<8} {tally[outcome]}")


if __name__ == "__main__":
    main()
