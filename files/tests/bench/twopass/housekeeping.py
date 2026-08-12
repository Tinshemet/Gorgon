"""THE SEALED HOUSEKEEPING TEST, and the model comparison beside it.

    PYTHONPATH=. python3 -m tests.bench.twopass.housekeeping          # the sealed test
    PYTHONPATH=. python3 -m tests.bench.twopass.housekeeping --model qwen2.5:14b --compare

⇒ THE TIERS AND THE SORTING MOVED TO `orchestrator/seam/housekeeping.py` on 2026-08-13 — the pipeline
  calls `sort_out` on every run, so it is production. What stayed here is what GRADES it: a
  sealed table of steps the model really proposed, and the comparison that asks the operator's
  question — *does a better model propose better housekeeping?*

⚠ MODEL-SPECIFIC TUNING LIVES UPSTREAM OF THIS FILE — see two-pass-rules.md §4b.
  Everything measured here was measured on llama3.1:8b.
"""
import argparse
from typing import Dict, List, Tuple

from planner.formula.legal import Board
from orchestrator.seam.effects import Operation
from orchestrator.seam.housekeeping import (BENIGN, CANCEROUS, GOOD, RISKY, Verdict,  # noqa: F401
                                       classify, sort_out)

# ── THE SEALED TEST · every step below was really produced, on the rung named ──────────
CASES: List[Tuple[str, int, Operation, List[Operation], str]] = [
    ("verifies the very attribute the program sets", 5,
     Operation("probe_alive", "stopped_vms", None),
     [Operation("launch_vm", "stopped_vms", None)], GOOD),
    ("a restore point before the program mutates it", 13,
     Operation("create_snapshot", "vms", None),
     [Operation("add_label", "vms", "fleet")], GOOD),
    ("a meaningless label value", 10,
     Operation("add_label", "vms", "label"),
     [Operation("create_vm", "vms", None)], CANCEROUS),
    ("launching machines nobody asked to launch", 4,
     Operation("launch_vm", "vms", None),
     [Operation("create_vm", "vms", None), Operation("add_label", "vms", "fleet")], RISKY),
    ("deleting to satisfy a label count", 7,
     Operation("delete_vm", "prod_vms", None),
     [Operation("add_label", "prod_vms", "prod")], CANCEROUS),
    ("undoing the program's own step", 5,
     Operation("stop_vm", "stopped_vms", None),
     [Operation("launch_vm", "stopped_vms", None)], CANCEROUS),
    ("a probe of something untouched", 4,
     Operation("probe_exists", "network", None),
     [Operation("create_vm", "vms", None)], BENIGN),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="run the SAME rungs on a second model and compare what each proposes")
    ap.add_argument("--model", default=None, help="the second model, for --compare")
    args = ap.parse_args()

    from orchestrator.seam import pass1, pass2
    board = Board()

    if not args.compare:
        print("=" * 96)
        print("HOUSEKEEPING, SORTED — every step below was really produced by the model")
        print("=" * 96)
        ok = 0
        for note, rung, op, program, want in CASES:
            rows = [S for S in ()]
            table = pass2.symbol_table(
                pass1.run_scanned(pass1.EXPECTED[rung].request, board=board), board)
            got = classify(op, program, table, board)
            hit = got.tier == want
            ok += hit
            print(f"  {'ok  ' if hit else 'FAIL'} rung {rung:<3} {note}")
            print(f"       want {want:<10} got {got.tier:<10} {got.why[:64]}")
        print(f"\n  {ok}/{len(CASES)} sorted as sealed")
        return

    # ⇒ THE OPERATOR'S THEORY: a better model proposes MORE and BETTER housekeeping.
    from tests.bench.twopass.metrics import Lab
    from orchestrator.seam import pipeline
    world = Lab()
    print("=" * 96)
    print(f"DOES A BETTER MODEL PROPOSE BETTER HOUSEKEEPING?   second model: {args.model}")
    print("=" * 96)
    for n in (2, 4, 5, 11, 13):
        request = pass1.EXPECTED[n].request
        print(f"\nrung {n} · {request[:70]}")
        for label, model in (("baseline", None), (args.model or "second", args.model)):
            got = pipeline.run(request, board=board, world=world, model=model, retries=0)
            tiers = sort_out(list(got.suggested), list(got.operations), got.table, board)
            counts = " ".join(f"{k}={len(v)}" for k, v in tiers.items() if v) or "none"
            print(f"    {label:<12} program {len(got.operations)}  proposed "
                  f"{len(got.suggested)}   {counts}")
            for tier in (GOOD, RISKY, CANCEROUS):
                for v in tiers[tier]:
                    print(f"                 {v!r}"[:100])


if __name__ == "__main__":
    main()
