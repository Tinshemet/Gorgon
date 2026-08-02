"""Do the two routers contradict each other, and how often?

E8's precondition, and it answered NO. The atomicity router names a leaf's OPERATOR and
scores 4/10 at it; the quantifier router answers all/any/single/not and scores 15/16. If
the better one denied what the worse one chose, that disagreement would be the whole case
for narrowing per leaf.

MEASURED 2026-07-30, 13 rungs, routing only:

    35 leaves · DISAGREEMENTS 2 · quantifier: single 20 · all 8 · any 5 · not 2

    rung 4  atomicity `foreach` vs quantifier `single`  "connect each node to every other
            node"   — and here the QUANTIFIER is wrong: that is plainly a set operation.

They agree on 33 of 35, and the two exceptions are the good router's own errors. So
wiring "quantifier wins" would deny `foreach` to a leaf that needs it, on a rung that
already never builds. I predicted the opposite before running it — that disagreements
would be common and concentrated on `single` — and the corpus says otherwise.

WHY IT COMES OUT THIS WAY, and it is structural rather than luck: after decomposition most
leaves ARE single clauses about one object (20 of 35 route `single`), and for those the
atomicity router already picks an op that `single` licenses. The only op-level edge the
quantifier has is `single` denying `foreach`, so agreement is the default outcome.

Routing only: no emission, no execution. One decomposition per rung plus one quantifier
call per leaf.

Run:  PYTHONPATH=. python3 -m tests.bench.router_agreement_probe
"""
import sys
from collections import Counter

from planner.ir import lower, master          # noqa: E402
from tests.bench import tree_probe as tp                      # noqa: E402
from tests.bench.author_probe import _route_quantifier        # noqa: E402
from tests.bench.ladder import BENCH_MODEL                    # noqa: E402
from tests.bench.rungs import RUNGS                           # noqa: E402
from tests.bench.sim_world import SimWorld                    # noqa: E402


def leaves(node, out):
    if node.get("children"):
        for kid in node["children"]:
            leaves(kid, out)
    else:
        out.append(node)
    return out


def main():
    rows, tally = [], Counter()
    for rung in RUNGS:
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        stats = {"route_calls": 0, "emit_calls": 0, "leaf_bad_json": 0, "route_channel": 0}
        try:
            root = lower.decompose(rung.goal, tp.make_route(BENCH_MODEL, world, stats))
        except Exception as exc:
            print(f"rung {rung.n}: decompose failed — {type(exc).__name__}: {exc}", flush=True)
            continue
        for leaf in leaves(root, []):
            op, goal = leaf["op"], leaf["goal"]
            q = _route_quantifier(goal, BENCH_MODEL)
            allowed = master.ops("achieve", q) if q else master.ops("achieve")
            clash = op not in allowed
            tally["leaves"] += 1
            tally["clash"] += clash
            tally[f"q:{q}"] += 1
            if clash:
                rows.append((rung.n, op, q, goal))
            print(f"  rung {rung.n:>2}  op={op:8} q={str(q):7} "
                  f"{'CLASH' if clash else '     '}  {goal[:52]}", flush=True)

    print(f"\n── leaves {tally['leaves']} · DISAGREEMENTS {tally['clash']}")
    print("   quantifier distribution:",
          {k[2:]: v for k, v in tally.items() if k.startswith("q:")})
    for n, op, q, goal in rows:
        print(f"   rung {n}: atomicity says `{op}`, quantifier says `{q}` -> {goal[:60]}")


if __name__ == "__main__":
    main()
