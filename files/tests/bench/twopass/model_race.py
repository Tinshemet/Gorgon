"""THREE MODELS, THE SAME FOUR QUESTIONS — fastest, cheapest, most correct, best housekeeping.

    PYTHONPATH=. python3 -m tests.bench.twopass.model_race

⇒ **ONE MODEL AT A TIME, ON PURPOSE.** The GPU holds 6 GB and qwen2.5:14b needs 9, so two
  resident at once thrashes. Each model answers all four rungs before the next is touched.

⇒ **AND THE REQUIRED STEPS ARE WRITTEN DOWN HERE, NOT JUDGED AFTERWARDS** (rule V5). What is
  left over is HOUSEKEEPING and goes through `housekeeping.classify` — so "best housekeeping"
  is a tier count, not an opinion.
"""
import argparse
import json
from typing import Dict, List, Tuple

from planner.formula.legal import Board
from orchestrator.languages.english.seam.effects import Operation
from orchestrator.languages.english.seam.housekeeping import BENIGN, CANCEROUS, GOOD, RISKY, classify
from tests.bench.twopass.token_probe import call, payload_for

# the steps the request actually asks for, as (operator, target)
REQUIRED: Dict[int, List[Tuple[str, str]]] = {
    4: [("create_vm", "vms"), ("create_network", "network"),
        ("add_vm_to_network", "vms"), ("add_label", "vms")],
    13: [("add_vm_to_network", "vms"), ("add_label", "vms")],
    11: [("probe_alive", "vms"), ("stop_vm", "not_alive_vms")],
    5: [("launch_vm", "stopped_vms")],
}

# rung 4 and 13 both end in "make sure they all ping each other", which NO offered operation
# can express — so it is excluded from the key rather than counted against every model.
NOTE = "the clique in rungs 4 and 13 is unexpressible and is not required of anyone"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="llama3.1:8b,mistral-nemo:12b,qwen2.5:14b")
    ap.add_argument("--order", default="pinned", choices=("pinned", "alpha"),
                    help="`alpha` removes the llama-fitted enum pin — the bias control")
    ap.add_argument("--filtered", action="store_true",
                    help="offer only the operators the request warrants")
    args = ap.parse_args()
    board = Board()
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    from orchestrator.languages.english.seam import pass1, pass2
    import engines.channel as channel

    scores: Dict[str, Dict] = {}
    for model in models:
        scores[model] = {"ms": 0, "tokens": 0, "hit": 0, "want": 0, "extra": 0,
                         BENIGN: 0, GOOD: 0, RISKY: 0, CANCEROUS: 0}
        print(f"\n{'=' * 100}\n{model}   (enum order: {args.order})\n{'=' * 100}")
        for rung, required in sorted(REQUIRED.items()):
            prompt, payload, schema = payload_for(rung, board, args.order, args.filtered)
            try:
                got = call(model, prompt, payload, schema)
                steps = json.loads(got["answer"]).get("operations", [])
            except Exception as exc:
                print(f"  rung {rung}: <failed {type(exc).__name__}>")
                continue
            ops = [Operation(s.get("operator"), s.get("on"), s.get("value")) for s in steps
                   if s.get("operator") and s.get("on")]
            pairs = [(o.operator, str(o.on)) for o in ops]
            hit = [r for r in required if r in pairs]
            program = [o for o in ops if (o.operator, str(o.on)) in required]
            extra = [o for o in ops if (o.operator, str(o.on)) not in required]

            was, channel.constrained = channel.constrained, lambda *a, **k: {}
            try:
                table = pass2.symbol_table(
                    pass1.run_scanned(pass1.EXPECTED[rung].request, board=board), board)
            finally:
                channel.constrained = was

            tiers = [classify(o, program, table, board) for o in extra]
            scores[model]["ms"] += got["ms"]
            scores[model]["tokens"] += (got["answer_tokens"] or 0)
            scores[model]["hit"] += len(hit)
            scores[model]["want"] += len(required)
            scores[model]["extra"] += len(extra)
            for v in tiers:
                scores[model][v.tier] += 1
            print(f"  rung {rung:<3} {len(hit)}/{len(required)} required   "
                  f"{len(extra)} extra   {got['answer_tokens']:>4} tok  {got['ms']:>6} ms")
            for v in tiers:
                print(f"          [{v.tier}] {v.op.operator}({v.op.on}"
                      f"{', ' + repr(v.op.value) if v.op.value else ''})")

    print(f"\n{'=' * 100}\nRANKING   ({NOTE})\n{'=' * 100}")
    rows = [(m, s) for m, s in scores.items()]
    print(f"  {'model':<18} {'correct':>9} {'extra':>6} {'good':>5} {'risky':>6} "
          f"{'cancer':>7} {'tokens':>7} {'seconds':>8}")
    for m, s in rows:
        print(f"  {m:<18} {s['hit']}/{s['want']:<7} {s['extra']:>6} {s[GOOD]:>5} "
              f"{s[RISKY]:>6} {s[CANCEROUS]:>7} {s['tokens']:>7} {s['ms'] / 1000:>8.1f}")
    print()
    if rows:
        print(f"  FASTEST          {min(rows, key=lambda r: r[1]['ms'])[0]}")
        print(f"  FEWEST TOKENS    {min(rows, key=lambda r: r[1]['tokens'])[0]}")
        print(f"  MOST CORRECT     {max(rows, key=lambda r: r[1]['hit'])[0]}")
        best = max(rows, key=lambda r: (r[1][GOOD], -r[1][CANCEROUS], -r[1][RISKY]))
        print(f"  BEST HOUSEKEEPING {best[0]}   "
              f"(good {best[1][GOOD]}, risky {best[1][RISKY]}, cancerous {best[1][CANCEROUS]})")


if __name__ == "__main__":
    main()
