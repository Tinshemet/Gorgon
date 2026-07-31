#!/usr/bin/env python3
"""
test_tile_solver.py — can code alone write the program? Step 2 of #61.

The rung's OWN checker decides it — the same function that grades the model — so this is not
a private definition of success invented to be passed. Rung 3 is the one that matters:
"create a network called lab and a vm named web, then put web on lab" carries a real
dependency, and ordering is the thing a writer must DERIVE rather than be told.

WHAT IS AND IS NOT BEING CLAIMED. Only the writing half is under test. The goal arrives as
predicates — the components the operator's design has the AI extract — and whether a model
can produce those is a separate measurement. That separation is the point: today a wrong
program could mean the goal was misread OR the writing was fumbled, and nothing tells them
apart.

Run:  PYTHONPATH=. python3 -m tests.test_tile_solver
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir import consent, render, validate
from orchestrator.ai.planner.ir import run as ir_run
from tests.bench.rungs import RUNGS
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld
from tests.bench.tile_solver import Unsolvable, as_program, cover

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


# Rung 3's goal as COMPONENTS — what the AI would extract, nothing more. Deliberately
# written in the order the SENTENCE says it ("a network, and a vm, then put web on lab"),
# so that if the solver emitted goals in the order given it would still be wrong: putting
# web on lab is stated last but its preconditions come first. The order in the output has
# to be earned.
RUNG3_GOALS = [
    {"shape": "count", "select": {"kind": "network", "net_name": "lab"}, "eq": 1},
    {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1},
    {"shape": "count", "select": {"kind": "vm", "name": "web", "network": "lab"}, "eq": 1},
]


def test_the_solver_writes_rung_3_and_the_rungs_own_checker_passes():
    print("[step 2] rung 3, covered by tiles, no model anywhere")
    rung = next(r for r in RUNGS if r.n == 3)
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    sel, holds = seams(world)

    plan = cover(RUNG3_GOALS, holds)
    prog = as_program(plan, RUNG3_GOALS)
    print("      " + "\n      ".join(render(prog).splitlines()))

    # (ok, problems) — unpacked, not truth-tested. `validate` returns a TUPLE, so
    # `not validate(...)` is always False and the check would have passed no matter what
    # the validator said. It failed here only because the tuple's first element is True;
    # had the program been invalid it would have read the same way.
    ok, problems = validate(prog, known_names=world.names())
    check("the program is structurally valid", ok and not problems)
    if problems:
        print(f"      {problems[0]}")

    # ORDERING IS THE REAL ASSERTION. Nothing told the writer that a network must exist
    # before a machine joins it; it placed create_network first because add_vm_to_network's
    # precondition said so. Emitting the goals in the order given would fail here.
    tools = [t for t, _ in plan]
    check("it creates the network before attaching to it",
          tools.index("create_network") < tools.index("add_vm_to_network"))
    check("it creates the vm before attaching it",
          tools.index("create_vm") < tools.index("add_vm_to_network"))

    res = ir_run(prog, world.execute, select=sel, holds=holds,
                 known_names=world.names(), consent=True, intent="achieve")
    check(f"the program runs and its own checks hold ({res.get('failed') or 'ok'})",
          res["ok"])
    check("THE RUNG'S OWN CHECKER PASSES", bool(rung.check(world)))
    check(f"and it costs {len(res['calls'])} calls vs the recorded best {rung.best}",
          len(res["calls"]) <= (rung.best or 99))


def test_the_written_program_is_grounded_without_anyone_asking():
    """The property 60 of 78 model-written programs lacked, for free.

    The goal becomes the program's own closing ENSURE, so grounding is not a request that
    can be ignored — it is a consequence of having a goal at all. 2026-07-31 measured the
    alternative twice: asking produced 60 ungrounded programs, and DEMANDING it made the
    ladder worse while breaking the decoder.
    """
    print("[grounding] the writer cannot produce an ungrounded program")
    world = SimWorld()
    sel, holds = seams(world)
    prog = as_program(cover(RUNG3_GOALS, holds), RUNG3_GOALS)
    s = consent.survey(prog)
    check("it acts", s["acts"] > 0)
    check("it is grounded", s["grounded"] is True)
    check("and no assertion of it is vacuous", s["vacuous"] == 0)
    check("so the operator is never asked", consent.question(prog) is None)


def test_a_goal_that_already_holds_costs_nothing():
    """The empty program is the correct answer, and the writer can say it."""
    print("[idempotence] re-running against a finished world writes nothing")
    world = SimWorld()
    sel, holds = seams(world)
    for tool, args in cover(RUNG3_GOALS, holds):
        world.execute(tool, args)
    sel2, holds2 = seams(world)
    check("a second pass over a satisfied goal emits no calls",
          cover(RUNG3_GOALS, holds2) == [])


def test_an_uncoverable_goal_fails_loudly_instead_of_improvising():
    """No tile, no program. A writer that guesses is worse than one that stops.

    The whole reason for moving generation out of the model is that this component does not
    invent steps — so the one thing it must never do is produce something plausible for a
    goal it cannot reach.
    """
    print("[honesty] an uncoverable goal raises rather than improvises")
    world = SimWorld()
    sel, holds = seams(world)
    impossible = [{"shape": "count", "select": {"kind": "vm", "name": "x",
                                                "os_type": "linux"}, "eq": 1}]
    try:
        cover(impossible, holds)
        check("no tile sets os_type, so this must not succeed", False)
    except Unsolvable as e:
        check(f"raises Unsolvable and names the goal ({str(e)[:40]}...)", True)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "tile solver"))


if __name__ == "__main__":
    main()
