"""
run_program.py — run an IR program against the simulated world, end to end.

The point is that this is the SAME visitor the orchestrator would use. Only the three
injected seams differ: `execute` is the sim's instead of the gated execute_tool,
`select` reads the sim's registry instead of the Active Library, and `holds` reads the
sim's reach() instead of the findings ledger. Nothing about the language changes.

Run:  PYTHONPATH=. python3 -m tests.bench.run_program            # X=5
      PYTHONPATH=. python3 -m tests.bench.run_program -x 3
"""
import argparse
import json
import sys

from orchestrator.ai.planner.ir import render, run, validate

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
        {"op": "new", "var": "vms", "kind": "vm", "count": "$X"},
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


def seams(world: SimWorld):
    """The three injected seams, backed by the sim.

    `holds` is where finding #2 shows: `count` is answered from the registry, but `reach`
    is answered by the world's reach() — a probe result, not state. In the orchestrator
    those are the Active Library and the findings ledger respectively. An ENSURE that
    could only read the registry could not express this program's last line.
    """
    def select(sel):
        # Canonicalise aliases first — a program may say `tag` or `label` and mean the
        # same attribute; the manifest owns which spellings are equivalent.
        from orchestrator.ai.planner.ir import config as _ic
        kind = sel.get("kind")
        alias = (_ic.KINDS.get(kind) or {}).get("aliases") or {}
        sel = {alias.get(k, k): v for k, v in sel.items()}
        if kind == "network":
            return sorted(world.nets)
        out = []
        for name, vm in sorted(world.vms.items()):
            if "label" in sel and sel["label"] not in (vm["labels"] | vm.get("flags", set())):
                continue
            if "status" in sel and vm["status"] != sel["status"]:
                continue
            if "name" in sel and name != sel["name"]:
                continue
            out.append(name)
        return out

    def holds(pred, scope):
        shape = pred.get("shape")
        if shape == "count":
            n = len(select(pred["select"]))
            for cmp_, want in (("eq", "=="), ("gte", ">="), ("lte", "<=")):
                if cmp_ in pred:
                    good = eval(f"{n} {want} {int(pred[cmp_])}")   # bench only
                    return good, f"count is {n}, wanted {want} {pred[cmp_]}"
            return False, "no comparator"
        if shape == "reach":
            want = int(pred.get("min", 2))
            _s = pred.get("select") or {}
            tag = _s.get("label", _s.get("tag"))
            good = world.reach(tag, minimum=want)
            return good, f"reach({tag}, min={want}) is {good}"
        if shape == "disjoint":
            return False, "disjoint not evaluated in the bench"
        return False, f"unknown shape {shape}"

    return select, holds


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
