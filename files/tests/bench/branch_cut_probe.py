"""C1: cutting the statement `oneOf` from ELEVEN branches to SEVEN — MEASURED, NO EFFECT.

D1's chain said branch count was the mechanism: every constraint shape held 5/5 in
isolation at one or two branches, the real eleven-branch `oneOf` produced an op no branch
permits, and at ONE branch per leaf 345 calls produced zero malformed output. The implied
fix was to cut branches and let the validator catch what the grammar no longer can.

MEASURED 2026-07-30, rungs 8/11/13, both columns, n=3, 18 cells per arm:

    A:eleven   pass 3/18 · CHANNEL 12/18
    B:seven    pass 3/18 · CHANNEL 12/18     identical in every outcome code

AND THE CUT DEMONSTRABLY TOOK EFFECT — the schema is enforced, so this is a real null and
not a wiring failure. Same goal, same prompt, the two schemas produce different programs:

    eleven -> {"op": "foreach", "select": {...}, "do": [{"op": "call", ...}]}
    seven  -> {"op": "foreach", "select": {...}, "call": {"tool": ...}}

The model switched from `do` to `call` exactly where the grammar removed `do`. It adapted,
and failed at the same rate in the same ways.

SO D1'S EVIDENCE WAS CONFOUNDED. The one-branch result came from the TREE path, where the
prompt is also far shorter, the task is one statement and the output a fraction as long.
Branch count was never isolated from TASK SIZE. This holds prompt and task fixed and varies
only branches: nothing moves. The remaining explanation is task size, which no amount of
schema trimming addresses — a whole program needs several ops by definition.

Kept because "just cut the branches" will look obviously right again in a month.

Run:  PYTHONPATH=. python3 -m tests.bench.branch_cut_probe
"""
import sys
from collections import Counter

from tests.bench import author_probe as ap  # noqa: E402

RUNGS, N = [8, 11, 13], 3
_real_program_schema = ap.program_schema


def one_branch_per_op(want=None, known=None, quantifier=None):
    """The same schema with the sugar branches removed — first combination per op."""
    schema = _real_program_schema(want, known, quantifier)
    seen, kept = set(), []
    for branch in schema["$defs"]["stmt"]["oneOf"]:
        op = branch["properties"]["op"]["const"]
        if op in seen:
            continue
        seen.add(op)
        kept.append(branch)
    schema["$defs"]["stmt"]["oneOf"] = kept
    return schema


def run(arm_name, builder):
    ap.program_schema = builder
    outcomes = Counter()
    for rung in RUNGS:
        for column in ("lit", "para"):
            for _ in range(N):
                sink = []
                argv = ["-r", str(rung), "--execute"] + (["-p"] if column == "para" else [])
                ap._SANITISED.clear()
                try:
                    ap.main(argv, sink=sink)
                except Exception as exc:
                    sink.append({"outcome": f"CRASHED:{type(exc).__name__}"})
                for cell in sink:
                    outcomes[cell["outcome"]] += 1
            print(f"  {arm_name} rung {rung} {column} done", flush=True)
    return outcomes


def main():
    print(f"branches: full={len(_real_program_schema('achieve')['$defs']['stmt']['oneOf'])} "
          f"cut={len(one_branch_per_op('achieve')['$defs']['stmt']['oneOf'])}\n", flush=True)

    results = {}
    for name, builder in (("A:eleven", _real_program_schema), ("B:seven", one_branch_per_op)):
        print(f"── arm {name}", flush=True)
        results[name] = run(name, builder)
        print(f"   {dict(results[name])}\n", flush=True)

    CHANNEL = ("BAD_JSON", "NO_EMISSION", "REPAIR_UNDELIVERED")
    print("── C1 A/B · rungs 8, 11, 13 · both columns · n=3 · 18 cells per arm")
    for name, out in results.items():
        total = sum(out.values())
        channel = sum(v for k, v in out.items() if k.split(":")[0] in CHANNEL)
        passed = sum(v for k, v in out.items() if k in ("PASS", "OVER_BUDGET"))
        print(f"   {name:10} pass {passed}/{total} · CHANNEL {channel}/{total} · {dict(out)}")


if __name__ == "__main__":
    main()
