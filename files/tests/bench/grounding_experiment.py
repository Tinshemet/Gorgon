"""Does a GOAL make the correction loop converge?

Rung 8 is one of the eight ladder programs that assert nothing, and it is the one whose
revision loop stalled — repeating a call that had already failed, twice, instead of
noticing the missing network. The claim to test: that is not bad luck, it is the absence
of a target. A loop with nothing to aim at can only react to the last error.

Both arms run the SAME first program (the one the model actually wrote, verbatim from
the ladder), the same world, the same revise() and the same loop. The only difference is
whether the program ends in an ACHIEVE.

The goal clause is SUPPLIED BY HAND here, deliberately. The question is whether the loop
uses a target when it has one — not whether the model can write it. That second question
is separate, harder, and left open on purpose.
"""
import sys

sys.path.insert(0, "/home/tinshemet/Desktop/gorgon/files")

from planner.ir import derive, evaluate, render, run
from tests.bench.author_probe import _seams, revise
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

RUNG = next(r for r in RUNGS if r.n == 8)
MODEL, TEMP, REVISIONS = "llama3.1:8b", 0.0, 3

# Exactly what the model wrote on the last full ladder run.
PROGRAM = {"body": [
    {"op": "foreach", "select": {"kind": "vm", "not": {"name": "db"}},
     "call": {"tool": "add_vm_to_network",
              "args": {"net_name": "core", "vm_name": "$item"}}},
    {"op": "call", "tool": "add_vm_to_network",
     "args": {"net_name": "dmz", "vm_name": "db"}}]}

# The rung's own checker, said in Medusa: everything but db on core, db on dmz and NOT on
# core. Three clauses, because the carve-out is the whole point of the rung.
GOAL = {"shape": "all", "of": [
    {"shape": "count", "select": {"kind": "vm", "network": "core", "not": {"name": "db"}},
     "gte": 3},
    {"shape": "count", "select": {"kind": "vm", "network": "dmz", "name": "db"}, "eq": 1},
    {"shape": "count", "select": {"kind": "vm", "network": "core", "name": "db"}, "eq": 0},
]}


def arm(label, program, goal_pred):
    print("=" * 72)
    print(label)
    print("=" * 72)
    print(render(program))
    world = SimWorld()
    RUNG.setup(world)
    world.calls.clear()
    sel, holds = _seams(world)

    res = run(program, world.execute, select=sel, holds=holds,
              known_names=world.names(), consent=True)
    print(f"\n  first run: ok={res['ok']} failed={res.get('failed')}")

    def goal_holds():
        return evaluate(goal_pred, {}, holds) if goal_pred else (True, "")

    if res["ok"] and goal_pred:
        good, why = goal_holds()
        if not good:
            res = {**res, "ok": False, "failed": "unachieved", "why": why}

    rounds = 0
    while (not res["ok"]
           and res.get("failed") in ("unsatisfied", "unachieved", "calls_failed")
           and rounds < REVISIONS):
        rounds += 1
        derived = (derive(goal_pred, sel, res.get("scope"))
                   if goal_pred and res.get("failed") == "unachieved" else None)
        if derived:
            fix, problems = {"body": derived}, []
            print(f"  round {rounds}: DERIVED by the harness")
        else:
            fix, problems = revise(RUNG.goal, program, world, res.get("why", ""),
                                   MODEL, TEMP, True,
                                   reason=("its own check REJECTED the result"
                                           if res.get("failed") != "calls_failed"
                                           else "the world REJECTED its calls, so it did nothing"),
                                   failures=res.get("failures"))
            print(f"  round {rounds}: model revision")
        if fix is None or problems:
            print(f"    -> unusable: {(problems or ['error'])[0]}")
            break
        for line in render(fix).splitlines():
            print(f"    | {line}")
        res = run(fix, world.execute, select=sel, holds=holds,
                  known_names=world.names(), consent=True)
        if goal_pred:
            good, why = goal_holds()
            res = ({**res, "ok": True} if good
                   else {**res, "ok": False, "failed": "unachieved", "why": why})
        print(f"    -> {'GOAL HOLDS' if res['ok'] else 'still short: ' + str(res.get('why') or res.get('failed'))}")

    passed = RUNG.check(world)
    print(f"\n  RUNG CHECKER: {'PASS' if passed else 'FAIL'}")
    print(f"  world: {world.summary()}")
    print(f"  rounds used: {rounds}\n")
    return passed, len(world.calls), rounds


a = arm("ARM A — no goal. The program as the model wrote it.", PROGRAM, None)
b = arm("ARM B — same program, ACHIEVE appended. Objection = goal + rejected calls.",
        {"body": PROGRAM["body"] + [{"op": "achieve", "predicate": GOAL}]}, GOAL)

print("=" * 72)
print(f"  no goal : {'PASS' if a[0] else 'FAIL'}  ({a[1]} calls, {a[2]} rounds)")
print(f"  goal    : {'PASS' if b[0] else 'FAIL'}  ({b[1]} calls, {b[2]} rounds)")
