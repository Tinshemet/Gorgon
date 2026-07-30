"""
run_program.py — run an IR program against the simulated world, end to end.

The point is that this is the SAME visitor the orchestrator would use. Only the three
injected seams differ: `execute` is the sim's instead of the gated execute_tool,
`select` reads the sim's registry instead of the Active Library, and `holds` reads the
sim's reach() instead of the findings ledger. Nothing about the language changes.

`select` and `holds` come from `seams.py`, which is their one authority. This module used
to define its own weaker pair — no `not`/`in`/`any`/`all` and no `disjoint` evaluator — so
a carve-out was silently ignored here while the copy in `author_probe` answered it
correctly. Two sim-backed seams is one too many.

Run:  PYTHONPATH=. python3 -m tests.bench.run_program            # X=5
      PYTHONPATH=. python3 -m tests.bench.run_program -x 3
"""
import argparse
import json
import sys

from orchestrator.ai.planner.ir import render, run, validate

from .seams import seams
from .sim_world import SimWorld

# THE PROGRAM. "create X vms, label them 'test', put them on a network, make sure they
# can ping each other" — rung 4 generalised, with the count as a PARAMETER.
#
# Two things here exist because writing this exposed gaps in the four-node set:
#   * `count: "$X"` — the count is a parameter, so one procedure covers any size.
#   * `foreach in "$vms"` — the VMs must be labelled BEFORE anything can select them by
#     tag, so the first loop iterates the set `new` just bound. Until `in` existed there
#     was no way to act on freshly-created resources at all, and this program could not
#     be written.
PROGRAM = {
    "name": "test_fleet",
    "params": {"X": "int"},
    "imports": [{"package": "core"}],
    "body": [
        {"op": "new", "var": "net", "kind": "network"},
        # os_type rides along because create_vm REQUIRES it — the validator now reads
        # that off the live catalog, and this program was refused until it complied.
        # It had been "working" only because the sim world does not enforce required
        # fields; against the real executor it could never have built a VM.
        {"op": "new", "var": "vms", "kind": "vm", "amount": "$X",
         "args": {"os_type": "linux"}},
        {"op": "foreach", "in": "$vms",
         "call": {"tool": "add_label", "args": {"name": "$item", "label": "test"}}},
        {"op": "foreach", "select": {"kind": "vm", "tag": "test"},
         "call": {"tool": "add_vm_to_network",
                  "args": {"net_name": "$net", "vm_name": "$item"}}},
        {"op": "ensure",
         "predicate": {"shape": "reach", "select": {"kind": "vm", "tag": "test"},
                       "min": "$X"}},
    ],
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Run the test_fleet program on the sim world")
    p.add_argument("-x", type=int, default=5, help="how many VMs (the X parameter)")
    p.add_argument("--json", action="store_true", help="print the IR")
    a = p.parse_args(argv)

    ok, problems = validate(PROGRAM)
    print(f"validates: {ok}" + ("" if ok else f" — {problems}"))
    print("\n── the program, as the operator reads it ──")
    print(render(PROGRAM))
    if a.json:
        print("\n── the program, as it is stored ──")
        print(json.dumps(PROGRAM, indent=2))

    world = SimWorld()
    select, holds = seams(world)
    print(f"\n── running with X={a.x} ──")
    result = run(PROGRAM, world.execute, select=select, holds=holds, params={"X": a.x})

    for i, (tool, args) in enumerate(result["calls"], 1):
        print(f"   {i:3} {tool:22} {json.dumps(args)}")
    print(f"\n   ok: {result['ok']}" + ("" if result["ok"]
                                        else f"  ({result.get('failed')}: {result.get('why', '')})"))
    print(f"   world: {world.summary()}")
    print(f"   calls: {len(result['calls'])}  (minimum for X={a.x}: {1 + 3 * a.x})")
    reached = world.reach("test", minimum=a.x)
    print(f"   CHECK reach('test', min={a.x}) = {reached}")
    return 0 if (result["ok"] and reached) else 1


if __name__ == "__main__":
    sys.exit(main())
