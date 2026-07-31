#!/usr/bin/env python3
"""
test_ghost_writer.py — can code alone write the program? Steps 2 and 3 of #61.

Rungs 3, 4 and 5, each graded by THE RUNG'S OWN CHECKER — the same function that grades the
model — so none of this is a private definition of success invented to be passed.

The three rungs were chosen because they fail differently:
    3   a DEPENDENCY. Attaching is stated last but must happen last for a reason nobody
        states: its preconditions come first. Ordering must be derived.
    5   a FILTER. `db` is already running, so a writer that launches everything still
        passes and one that launches nothing does not. The set must be resolved, not
        assumed.
    4   COLLECTIVE work plus a FINDING. Five machines the request never named, one network
        it never named, and a reach claim that no tool's success flag can establish.

WHAT IS UNDER TEST IS THE WRITING HALF ONLY. Goals arrive as predicates — what the operator's
design has the AI extract — and whether a model produces them is a separate measurement.
That separation is the point: today a wrong program could mean the goal was misread OR the
writing fumbled, and nothing distinguished them.

Run:  PYTHONPATH=. python3 -m tests.test_ghost_writer
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir import consent, render, validate
from orchestrator.ai.planner.ir import run as ir_run
from tests.bench.ghost_writer import Unsolvable, as_program, cover
from tests.bench.rungs import RUNGS
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld

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


# Rung 3's goals are given in the order the SENTENCE says them — network, vm, then attach.
# Emitting them that way is still wrong, because attaching is stated last while what it
# needs comes first. The order in the program has to be earned.
GOALS = {
    3: [{"shape": "count", "select": {"kind": "network", "net_name": "lab"}, "eq": 1},
        {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1},
        {"shape": "count", "select": {"kind": "vm", "name": "web", "network": "lab"}, "eq": 1}],
    4: [{"shape": "count", "select": {"kind": "vm"}, "eq": 5},
        {"shape": "count", "select": {"kind": "vm", "network": "lab"}, "eq": 5},
        {"shape": "count", "select": {"kind": "vm", "label": "fleet"}, "eq": 5},
        {"shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}],
    5: [{"shape": "count", "select": {"kind": "vm", "status": "stopped"}, "eq": 0}],
}


def _write(n):
    rung = next(r for r in RUNGS if r.n == n)
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    plan = cover(GOALS[n], world)
    prog = as_program(plan, GOALS[n])
    return rung, world, plan, prog


def _run_rung(n):
    rung, world, plan, prog = _write(n)
    print("      " + "\n      ".join(render(prog).splitlines()))
    ok, problems = validate(prog, known_names=world.names())
    check(f"rung {n}: structurally valid", ok and not problems)
    if problems:
        print(f"      {problems[0]}")
    sel, holds = seams(world)
    res = ir_run(prog, world.execute, select=sel, holds=holds,
                 known_names=world.names(), consent=True, intent="achieve")
    check(f"rung {n}: runs and its own checks hold ({res.get('failed') or 'ok'})", res["ok"])
    check(f"rung {n}: THE RUNG'S OWN CHECKER PASSES", bool(rung.check(world)))
    return rung, plan, res


def test_rung_3_derives_the_order_nobody_stated():
    print("[rung 3] a dependency")
    rung, plan, res = _run_rung(3)
    tools = [t for t, _ in plan]
    check("creates the network before attaching to it",
          tools.index("create_network") < tools.index("add_vm_to_network"))
    check("creates the vm before attaching it",
          tools.index("create_vm") < tools.index("add_vm_to_network"))


def test_rung_5_resolves_the_filter_and_leaves_the_rest_alone():
    """`db` was already running. Touching it would still pass the checker — and would be a
    worse program, so the test asserts what the CHECKER cannot."""
    print("[rung 5] a filter")
    rung, plan, res = _run_rung(5)
    launched = {a["name"] for t, a in plan if t == "launch_vm"}
    check("launches exactly the two that were stopped", launched == {"web", "cache"})
    check("and does NOT touch the one already running", "db" not in launched)
    check(f"in {len(plan)} calls", len(plan) == 2)


def test_rung_4_does_collective_work_and_establishes_a_finding():
    """The rung the model has never passed inside its budget — OVER_BUDGET 3/3, both
    columns, every ladder run of 2026-07-31."""
    print("[rung 4] collective work plus a finding")
    rung, plan, res = _run_rung(4)
    tools = [t for t, _ in plan]
    check("names the five machines the request never named",
          sum(1 for t in tools if t == "create_vm") == 5)
    check("creates ONE network, not five",
          sum(1 for t in tools if t == "create_network") == 1)
    # REACH IS A FINDING. No tool's success flag establishes it — somebody has to ask, and
    # the manifest records who (`observed.alive.by`). A writer that skipped this would leave
    # a program whose own ENSURE reports "reach is unestablished".
    check("probes every member, because reach is a finding and never an inference",
          sum(1 for t in tools if t == "guest_ping") == 5)
    check(f"at {len(plan)} calls vs the recorded best {rung.best}",
          len(plan) <= (rung.best or 99))


def test_every_written_program_is_grounded_without_anyone_asking():
    """The property 60 of 78 model-written programs lacked, on all three rungs.

    2026-07-31 measured both alternatives: ASKING left 60 programs vouching for nothing, and
    DEMANDING it in the prompt took the ladder 7/78 -> 6/78 while breaking the decoder. Here
    the goal simply becomes the witness.
    """
    print("[grounding] the writer cannot produce an ungrounded program")
    for n in (3, 4, 5):
        _, _, _, prog = _write(n)
        s = consent.survey(prog)
        check(f"rung {n}: acts and is grounded", s["acts"] > 0 and s["grounded"] is True)
        check(f"rung {n}: no assertion of it is vacuous", s["vacuous"] == 0)
        check(f"rung {n}: the operator is never asked", consent.question(prog) is None)


def test_a_finished_world_gets_the_empty_program():
    """Re-running a satisfied goal writes nothing — `already_satisfied` for the program
    regime (#21), as a consequence of tiles rather than a feature anyone built."""
    print("[idempotence] nothing to do means nothing written")
    for n in (3, 4, 5):
        rung, world, plan, _ = _write(n)
        for tool, args in plan:
            world.execute(tool, args)
        check(f"rung {n}: a second pass emits no calls", cover(GOALS[n], world) == [])


def test_it_stops_instead_of_improvising():
    """No tile, no lowering rule, no program.

    The whole reason to move generation out of the model is that this component does not
    invent steps, so producing something plausible for a goal it cannot reach is the one
    thing it must never do. `Unsolvable` is also the design's own signal: the request goes
    back for decomposition rather than forward as a guess.
    """
    print("[honesty] an unreachable goal raises rather than improvises")
    world = SimWorld()
    for label, goal in (
        ("no tool sets os_type",
         {"shape": "count", "select": {"kind": "vm", "name": "x", "os_type": "linux"}, "eq": 1}),
        # THREE-VALUED ATTRIBUTES ARE GENUINELY AMBIGUOUS. "no machine may be stopped" only
        # says what to do when there is exactly one other state; `complement` declines
        # otherwise, and declining must surface as a refusal rather than a pick.
        ("a kind with no key",
         {"shape": "count", "select": {"kind": "snapshot"}, "eq": 3}),
    ):
        try:
            cover([goal], world)
            check(f"{label}: must not succeed", False)
        except Unsolvable:
            check(f"{label}: raises Unsolvable", True)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "ghost writer"))


if __name__ == "__main__":
    main()
