"""test_rung_shape.py — WHAT EACH RUNG EXERCISES. The ladder as coverage, not a scoreboard.

#48: *the ladder is a regression suite, not a capability target.* `ladder_gate` answers the
regression half — rates, bands, reason codes that name the layer. This answers the other
half, and it is the one that decides whether a number MEANS anything: 9/13 says nothing
about which capabilities are covered, and a ladder nobody can read that way becomes a target
by default, because a number is the only thing it offers.

EVERY FIGURE HERE IS COMPUTED FROM THE WRITER'S OWN PLAN, deterministically, with no model.
Complexity is not scored — a rung is not "harder" by some weight I chose — it is DESCRIBED:
how many goals, how deep the lowering went, which kinds it touched, whether it had to ask
the world anything, whether it destroys.

WHAT IT ASSERTS is coverage, not difficulty: every goal shape the extractor can emit is
exercised by some rung, every operator the writer can place appears somewhere, and the
destructive path is exercised at all. A vocabulary with an untested corner is how `disjoint`
sat declared-and-unevaluable for weeks.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner import ghost_writer as gw
from orchestrator.ai.planner.ir import effects
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld
from tests.test_ghost_writer import GOALS

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _shape(n):
    """One rung, described. Nothing here is a judgement — every field is counted."""
    rung = next(r for r in RUNGS if r.n == n)
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    depth = {"max": 0}

    def trace(line):
        depth["max"] = max(depth["max"], (len(line) - len(line.lstrip())) // 2)

    class Say(list):
        def append(self, line):
            trace(line)
            list.append(self, line)

    plan = gw.cover(GOALS[n], world, trace=Say())
    kinds, shapes = set(), Counter()
    for g in GOALS[n]:
        for holder in ("select", "every", "observe", "per"):
            sel = g.get(holder)
            if isinstance(sel, dict) and sel.get("kind"):
                kinds.add(sel["kind"])
                shapes[holder if holder != "select" else g.get("shape", "count")] += 1
        if isinstance(g.get("make"), str):
            kinds.add(g["make"])
    tools = {t for t, _ in plan}
    deleters = set(effects.deleters(None))
    probes = {o["by"] for spec in (effects._K(None) or {}).values()
              for o in (spec.get("observed") or {}).values() if o.get("by")}
    return {"n": n, "goals": len(GOALS[n]), "calls": len(plan), "depth": depth["max"],
            "kinds": sorted(kinds), "shapes": dict(shapes), "tools": len(tools),
            "asks": bool(tools & probes), "destroys": bool(tools & deleters),
            "setup": rung.setup is not None}


def test_the_ladder_describes_what_it_covers():
    print("[shape] what each rung exercises")
    print(f"       {'rung':>4} {'goals':>5} {'calls':>5} {'depth':>5} {'tools':>5} "
          f"{'asks':>5} {'kills':>5}  kinds / shapes")
    for n in sorted(GOALS):
        s = _shape(n)
        print(f"       {s['n']:>4} {s['goals']:>5} {s['calls']:>5} {s['depth']:>5} "
              f"{s['tools']:>5} {str(s['asks']):>5} {str(s['destroys']):>5}  "
              f"{','.join(s['kinds'])} / {','.join(sorted(s['shapes']))}")
    check(f"all {len(GOALS)} rungs describe themselves from the writer's own plan",
          len([_shape(n) for n in sorted(GOALS)]) == len(GOALS))


def test_every_goal_shape_is_exercised_somewhere():
    """A vocabulary with an untested corner is how `disjoint` sat declared and unevaluable
    for weeks — offered by the schema, accepted by the validator, printed by the renderer,
    and impossible to satisfy."""
    print("[shape] the goal vocabulary has no untouched corner")
    from orchestrator.ai.engines.extract import SCHEMA

    offered = set(SCHEMA["properties"]["goals"]["items"]["properties"]["goal"]["enum"])
    seen = set()
    for n in sorted(GOALS):
        for shape in _shape(n)["shapes"]:
            seen.add(shape)
    missing = offered - seen
    check(f"every shape the extractor can emit is exercised ({sorted(missing) or 'none'} "
          f"missing)", not missing)


def test_the_dangerous_paths_are_exercised_at_all():
    """Coverage of the two things that cannot be un-done or un-asked."""
    print("[shape] destruction and observation are both on the ladder")
    shapes = [_shape(n) for n in sorted(GOALS)]
    kills = [s["n"] for s in shapes if s["destroys"]]
    asks = [s["n"] for s in shapes if s["asks"]]

    # THE HOLE IS CLOSED, AND THE NOTE IS REWRITTEN — which is what encoding it as a check
    # rather than a comment was for.
    #
    # For thirteen rungs no rung deleted anything: the one act that cannot be undone was
    # never exercised, found by this file on its first run. Rung 14 closes it with the very
    # request the old note cited — *"make sure there are exactly two machines"*, which
    # against the real lab plans seven deletions including vm-orchestrator.
    #
    # ADDING IT VOIDED EVERY RECORDED BASELINE, which is why the old note declined to do it
    # unasked. It is on the operator's own list as #88, and the baseline was re-recorded.
    #
    # WHAT IT FOUND IMMEDIATELY, and this is the argument for coverage instruments: the
    # writer emitted `delete_vm` on a RUNNING machine. `delete_requires` says it must be
    # stopped first, and the TEARDOWN path derived that — added the day a program's own
    # scaffolding survived every run — while the ordinary path never asked. So the fix
    # written for the program's own litter had never been applied to the operator's own
    # request.
    check(f"deletion is covered by rung(s) {kills}", bool(kills))
    check(f"some rung has to ASK the world ({asks or 'NONE'})", bool(asks))
    starts = [s["n"] for s in shapes if s["setup"]]
    check(f"some rung starts from a world that is already populated ({starts or 'NONE'})",
          bool(starts))


def test_complexity_is_described_rather_than_scored():
    """No weight, no total, no ranking. A rung is not 'harder' by a number I chose — and a
    single figure is exactly what turns a regression suite into a target."""
    print("[shape] there is no score here, deliberately")
    shapes = [_shape(n) for n in sorted(GOALS)]
    check("the spread of CALLS is real and wide",
          max(s["calls"] for s in shapes) >= 10 * max(1, min(s["calls"] for s in shapes)))
    check("lowering depth varies too",
          len({s["depth"] for s in shapes}) > 1)
    check("and no field here is a weighted total",
          not any(k in shapes[0] for k in ("score", "difficulty", "weight")))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "rung shape"))


if __name__ == "__main__":
    main()
