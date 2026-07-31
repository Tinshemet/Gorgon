#!/usr/bin/env python3
"""
test_ghost_writer.py — every rung, written by code alone. #60/#61.

All thirteen, each graded by THE RUNG'S OWN CHECKER — the same function that grades the
model. No model is called anywhere in this suite.

WHAT IS UNDER TEST IS THE WRITING HALF ONLY. Goals arrive as predicates and components —
what the operator's design has the AI extract — and whether a model produces them is a
separate measurement. Keeping them apart is the point: today a wrong program could mean the
goal was misread OR the writing fumbled, and nothing distinguished them.

THE GOALS BELOW ARE THE INTERFACE. Two forms appear, and the difference is deliberate:
  * a PREDICATE (`count`, `reach`) — something the language already evaluates
  * a COMPONENT (`every`, `per`, `observe`) — a quantifier, a selector and a target state,
    which the predicate language has no shape for and does not need one for. The writer
    lowers a component into per-member predicates and grounds it as a count it can compute.

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


C = lambda k, **f: {"shape": "count", "select": {"kind": k, **f}}
GOALS = {
 1: [{**C("vm", name="alpha"), "eq": 1}],
 2: [{**C("vm", name="beta"), "eq": 1},
     {**C("vm", name="beta", status="running"), "eq": 1}],
 3: [{**C("network", net_name="lab"), "eq": 1},
     {**C("vm", name="web"), "eq": 1},
     {**C("vm", name="web", network="lab"), "eq": 1}],
 4: [{**C("vm"), "eq": 5},
     {"every": {"kind": "vm"}, "must": {"network": "lab"}},
     {"every": {"kind": "vm"}, "must": {"label": "fleet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}],
 5: [{**C("vm", status="stopped"), "eq": 0}],
 6: [{**C("vm", label="red"), "eq": 3},
     {**C("vm", label="blue", **{"not": {"label": "red"}}), "eq": 2},
     {"every": {"kind": "vm", "label": "red"}, "must": {"network": "rednet"}},
     {"every": {"kind": "vm", "label": "blue"}, "must": {"network": "bluenet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "red"}, "min": 3},
     {"shape": "reach", "select": {"kind": "vm", "label": "blue"}, "min": 2}],
 7: [{**C("vm", label="prod"), "eq": 3}],
 8: [{"every": {"kind": "vm", "not": {"name": "db"}}, "must": {"network": "core"}},
     {**C("vm", name="db", network="dmz"), "eq": 1}],
 9: [{"shape": "reach", "select": {"kind": "vm"}, "min": 3}],
10: [{**C("vm"), "eq": 4},
     {"every": {"kind": "vm", "not": {"name": "golden"}}, "must": {"status": "running"}}],
11: [{"observe": {"kind": "vm"}, "fact": "alive"},
     {"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}}],
12: [{"per": {"kind": "vm", "status": "running"}, "make": "snapshot", "link": "vm"}],
13: [{**C("vm"), "eq": 5},
     {"every": {"kind": "vm"}, "must": {"network": "net1"}},
     {"every": {"kind": "vm"}, "must": {"label": "fleet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}],
}



def _write(n):
    rung = next(r for r in RUNGS if r.n == n)
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    plan = cover(GOALS[n], world)
    return rung, world, plan, as_program(plan, GOALS[n], world)


def test_every_rung_is_written_by_code_and_passes_its_own_checker():
    """The headline. Thirteen rungs, no model, each graded by the benchmark's own function."""
    print("[all 13] written by code, graded by the rung")
    passed = 0
    for n in sorted(GOALS):
        rung, world, plan, prog = _write(n)
        ok, problems = validate(prog, known_names=world.names())
        sel, holds = seams(world)
        res = ir_run(prog, world.execute, select=sel, holds=holds,
                     known_names=world.names(), consent=True, intent="achieve")
        good = bool(rung.check(world))
        passed += good
        check(f"rung {n:>2}: valid={ok} ran={res['ok']} CHECKER={'PASS' if good else 'FAIL'} "
              f"({len(plan)} calls, best {rung.best})",
              ok and not problems and res["ok"] and good)
    check(f"ALL THIRTEEN: {passed}/13", passed == 13)


def test_it_never_writes_an_ungrounded_or_self_vouching_program():
    """The property 60 of 78 model-written programs lacked, on all thirteen.

    2026-07-31 measured both alternatives: ASKING left 60 programs vouching for nothing, and
    DEMANDING it in the prompt took the ladder 7/78 -> 6/78 while breaking the decoder. Here
    each goal simply becomes the witness — and `vacuous == 0` matters as much as `grounded`,
    since the cheap way to satisfy a grounding rule is a witness that cannot fail (#53).
    """
    print("[grounding] every program vouches for itself, with claims that could fail")
    for n in sorted(GOALS):
        _, _, _, prog = _write(n)
        s = consent.survey(prog)
        check(f"rung {n:>2}: grounded, {s['vacuous']} vacuous",
              s["grounded"] is True and s["vacuous"] == 0)


def test_a_finished_world_gets_the_empty_program():
    """`already_satisfied` for the program regime (#21), as a consequence rather than a feature.

    RUNG 13 IS THE INTERESTING EXCEPTION AND IT IS CORRECT. Its setup leaves the registry
    already satisfied — five labelled machines on one network — yet the writer still emits
    five calls the FIRST time, because nothing has been PROBED and reach is a finding, never
    an inference (decision 6, A5). "Nothing to do" is true of the registry and false of the
    findings. On the second pass, with the answers in hand, it writes nothing.
    """
    print("[idempotence] nothing to do means nothing written")
    for n in sorted(GOALS):
        rung, world, plan, _ = _write(n)
        for tool, args in plan:
            world.execute(tool, args)
        again = cover(GOALS[n], world)
        if n == 11:
            # RUNG 11 IS DELIBERATELY NOT IDEMPOTENT, and that is the correct behaviour. Its
            # goal begins with an OBSERVATION, and a finding goes stale: whether a machine
            # answers is not a fact the registry stores, so asking again is the whole point
            # of asking. What must NOT repeat is the acting — a second pass may re-probe and
            # must not re-stop anything.
            check("rung 11: a second pass re-probes but CHANGES NOTHING",
                  again and all(t == "guest_ping" for t, _ in again))
            continue
        check(f"rung {n:>2}: a second pass emits no calls", again == [])


def test_it_stops_instead_of_improvising():
    """No tile, no lowering rule, no program — deliberately with no fallback.

    The whole reason to move generation out of the model is that this component does not
    invent steps, so producing something plausible for a goal it cannot reach is the one
    thing it must never do. `Unsolvable` is also the design's own signal: the request goes
    back for decomposition rather than forward as a guess.
    """
    print("[honesty] an unreachable goal raises rather than improvises")
    # `os_type` on a NEW machine is reachable and should be — it is a creation argument, and
    # the writer learning to pass it is an improvement, not a regression. The unreachable
    # case is changing it on a machine that ALREADY EXISTS: no setter writes os_type, and
    # no amount of lowering invents one.
    existing = SimWorld()
    existing.execute("create_vm", {"name": "x", "os_type": "linux"})
    for world, label, goal in (
        (existing, "no tool CHANGES os_type once a machine exists",
         {"shape": "count", "select": {"kind": "vm", "name": "x", "os_type": "windows"}, "eq": 1}),
        (SimWorld(), "a kind with no creator",
         {"shape": "count", "select": {"kind": "nonesuch", "name": "x"}, "eq": 1}),
    ):
        try:
            cover([goal], world)
            check(f"{label}: must not succeed", False)
        except Unsolvable:
            check(f"{label}: raises Unsolvable", True)


def test_the_same_request_against_the_same_world_writes_the_same_program():
    """DETERMINISM, and it is the property everything else rests on.

    #28 recorded rung 6 flipping BUILD FAILED -> BUILD OK on byte-identical code. That was
    the TREE path, which calls a model — and `pinned.py` already states in its own comment
    that "temperature 0 is deterministic" is a false assumption. So it was never a bug to
    chase; it was the documented behaviour of a model-driven path.

    The writer makes it structurally impossible. Same goals, same world, same program, every
    time — which is what lets a failing case be reproduced from a seed, what makes the fuzz
    corpus meaningful, and what allows a destructive plan to be reviewed before it runs. A
    writer that varied would take all three away at once.
    """
    print("[determinism] the same request writes the same program")
    import json as _json
    for n in sorted(GOALS):
        rung = next(r for r in RUNGS if r.n == n)
        seen = set()
        for _ in range(4):
            world = SimWorld()
            if rung.setup:
                rung.setup(world)
            seen.add(_json.dumps(cover(GOALS[n], world), sort_keys=True))
        check(f"rung {n:>2}: one program over four runs", len(seen) == 1)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "ghost writer"))


if __name__ == "__main__":
    main()
