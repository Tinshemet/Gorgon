#!/usr/bin/env python3
"""
test_intent_ladder.py — FETCH, ENSURE and ACHIEVE do the three things they promise.

    FETCH     "how many are there? list them."   reads and reports VALUES
    ENSURE    "verify this. ground me."          reads and reports a VERDICT
    ACHIEVE   "do this, and make sure it is done."  the only autonomous one

`ir/intent.py` has said that since the day it was written and nothing had ever asked
whether it was true END TO END. It was not, and the two lower rungs were the ones that did
not work:

  * A FETCH COULD NOT READ ANYTHING. Every observation the writer makes is spelled
    `CALL <probe>`, and `call` was absent from FETCH's op set, so "how many machines are up"
    was refused for reaching above a fetch — on statement one, for every phrasing.
  * AN ENSURE WROTE A CORRECTION AND WAS THEN REFUSED FOR IT. `cover` is the ACHIEVE engine:
    it closes whatever gap it finds. Called for every intent, it turned "are there nine
    machines?" against a lab holding four into a program that CREATES FIVE, which the gate
    then refused. The operator asked whether something was so and was told they were not
    allowed to ask.
  * AND A CHECK THAT SAID NO WAS A FAILED RUN. `run` reports an unsatisfied ENSURE as
    `failed: unsatisfied`, which is right for an ACHIEVE — there the assertion is a
    precondition the plan was built on. Under an `ensure` the assertion IS THE REQUEST, and
    "count is 4, wanted == 9" is the answer.

None of it was visible while intent was unenforced, because the engine ran every program
with `intent="achieve"` hardcoded.

NO MODEL. The channel is stubbed with the goals a translator would produce, which is the
same discipline `test_medusa_rungs` uses: this proves the LADDER, not the extractor.

Run:  PYTHONPATH=. python3 -m tests.test_intent_ladder
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     insession)
from orchestrator.ai.engines.channel import Answer
from orchestrator.ai.engines.session import Session
from orchestrator.ai.planner.ir import effects as _effects
from tests.bench.sim_world import SimWorld

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class Lab(MedusaEngine):
    """Medusa over the VM sim. Claims everything, so a routing miss cannot hide here."""

    def claims(self, request):
        return True


def _world(names=("alpha", "beta", "gamma", "delta"), unreachable=("beta", "delta")):
    w = SimWorld()
    for n in names:
        w.execute("create_vm", {"name": n, "os_type": "linux"})
    w.unreachable = set(unreachable)
    return w


def _serve(goals, intent, world=None, regime="translation"):
    world = _world() if world is None else world

    def translate(request, w=None):
        return Answer(goals, "table", "")
    translate.name = "table"

    reg = Registry()
    reg.mount(Lab(world))
    out = Orchestrator(reg, Channel([translate])).handle(
        "the request", intent=intent, regime=regime)
    return out, world


def _values(out):
    return {f["fact"]: f["value"] for f in (out.get("findings") or []) if "fact" in f}


HOW_MANY_ARE_UP = [{"observe": {"kind": "vm"}, "fact": "alive"}]
FOUR_MACHINES = [{"shape": "count", "select": {"kind": "vm"}, "eq": 4}]
NINE_MACHINES = [{"shape": "count", "select": {"kind": "vm"}, "eq": 9}]


def test_a_fetch_reads_and_reports_and_changes_nothing():
    """The bottom rung, and it was the one that could not run at all."""
    print("[ladder] fetch: the numbers and the names, and nothing else")
    out, world = _serve(HOW_MANY_ARE_UP, "fetch")
    check(f"it closes DONE ({out.get('why')})", out["outcome"] == "DONE")
    check("it asked every machine", len(out["calls"]) == 4)

    got = _values(out)
    check("and reports what each one ANSWERED, not that it was asked",
          got.get("reachable(alpha)") is True and got.get("reachable(beta)") is False)
    check("all four are answered for",
          len([k for k in got if k.startswith("reachable(")]) == 4)

    check("nothing in the lab moved",
          sorted(world.vms) == ["alpha", "beta", "delta", "gamma"])
    check("and not one call was an act",
          not [t for t, _ in out["calls"] if t in _effects.actors(None)])


def test_a_fetch_passes_judgement_on_nothing():
    """A VERDICT IS THE RUNG ABOVE. `_PERMITS` does not license a fetch an `ensure`, so a
    fetch program that carried one would be refused by its own authority — which is how a
    correct request comes to fail on a rule nobody meant to apply to it."""
    print("[ladder] fetch: reads, never judges")
    out, _ = _serve(HOW_MANY_ARE_UP, "fetch")
    check("the program it wrote contains no assertion",
          "ENSURE" not in (out.get("rendered") or ""))
    check("and it still publishes what it found", "PUBLISH" in (out.get("rendered") or ""))


def test_an_ensure_answers_yes():
    print("[ladder] ensure: a verdict, and this one is yes")
    out, world = _serve(FOUR_MACHINES, "ensure")
    check("it closes DONE", out["outcome"] == "DONE")
    check("the verdict is true", _values(out).get("holds") is True)
    check("nothing was called", not out["calls"])
    check("and nothing in the lab moved", len(world.vms) == 4)


def test_an_ensure_answers_no_and_that_is_not_a_failure():
    """THE ONE THAT WAS REPORTED AS REFUSED. An operator asking whether something is so and
    being told they lack the authority to ask is the ladder failing at its own job."""
    print("[ladder] ensure: a verdict, and this one is no")
    out, world = _serve(NINE_MACHINES, "ensure")
    check(f"it closes DONE, not REFUSED or UNMET ({out['outcome']})",
          out["outcome"] == "DONE")
    check("the verdict is false", _values(out).get("holds") is False)
    check("and it says what it found", "count is 4" in (out.get("why") or ""))
    check("NOTHING WAS CREATED — the whole point", len(world.vms) == 4)
    check("no call was made at all", not out["calls"])


def test_an_ensure_still_asks_what_it_has_to_ask():
    """A CHECK ABOUT AN OBSERVED ATTRIBUTE HAS TO PROBE. Withholding the probe would answer
    `unknown` and call it a verdict — which is decision 6's whole complaint, one level up."""
    print("[ladder] ensure: a check may still ask")
    # BOTH COMPONENTS, which is what rung 11 actually is: ask, and then say what must be
    # true of the answers. A rule about an observed attribute with no `observe` beside it is
    # a rule about a set nobody looked at, and it resolves to empty under EVERY intent.
    goals = [{"observe": {"kind": "vm"}, "fact": "alive"},
             {"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}}]
    out, world = _serve(goals, "ensure")
    probes = [t for t, _ in out["calls"] if t in _effects.askers(None)]
    check(f"it probed ({len(probes)} time(s))", bool(probes))
    check("and every call it made was a probe", len(probes) == len(out["calls"]))
    # ASSERTED ON THE CALLS, NOT THE STATUS. The sim creates machines stopped, so "none of
    # them is stopped" is a claim about the fixture rather than about the run — the shape of
    # assertion that passes for the wrong reason.
    check("and it stopped nothing",
          not [t for t, _ in out["calls"] if t == "stop_vm"])


def test_an_achieve_closes_the_gap():
    """The top rung, unchanged — and the control for every claim above."""
    print("[ladder] achieve: make it so")
    out, world = _serve(NINE_MACHINES, "achieve")
    check("it closes DONE", out["outcome"] == "DONE")
    check("it created the difference and only the difference", len(world.vms) == 9)
    check("five calls, not nine", len(out["calls"]) == 5)


def test_the_same_request_at_three_rungs_gives_three_answers():
    """THE LADDER IN ONE TEST. One set of goals, three intents, three different behaviours —
    and the difference is the operator's word, which is the entire design."""
    print("[ladder] one request, three rungs")
    shapes = {}
    for want in ("fetch", "ensure", "achieve"):
        out, world = _serve(NINE_MACHINES, want)
        shapes[want] = (out["outcome"], len(world.vms), len(out["calls"]))
    check(f"a fetch changes nothing ({shapes['fetch']})", shapes["fetch"][1] == 4)
    check(f"an ensure changes nothing ({shapes['ensure']})", shapes["ensure"][1] == 4)
    check(f"an achieve closes it ({shapes['achieve']})", shapes["achieve"][1] == 9)
    check("and none of the three is an error",
          {s[0] for s in shapes.values()} == {"DONE"})


def test_achieve_corrects_itself_and_derive_is_the_first_engine():
    """ACHIEVE HAS TWO ENGINES AND PRODUCTION RAN NEITHER.

        derive()   deterministic, free, auditable, no model call   FIRST
        tree       bounded, scoped by the gap                      where derive returns None

    `derive` has been the deterministic half of ACHIEVE since it was written and
    `ir/__init__` exports it — and NO PRODUCTION MODULE CALLED IT. Only the two bench probes
    did, so the correction loop the ladder measures was a property of the bench rather than
    of the system: an ACHIEVE whose witness failed came back UNMET with the gap uncomputed.

    DRIVEN THROUGH A SHORT PLAN, deliberately. The writer plans the whole gap up front, so a
    program it wrote does not normally under-deliver — which is exactly why this seam had
    never run. A plan that falls short is what a moving world produces, and it is the case
    the corrector exists for.
    """
    print("[achieve] the gap is computed, not asked about")
    world = _world(names=("alpha",))
    eng = Lab(world)
    sess = Session("five machines", eng, intent="achieve", regime="translation")

    goal = {"shape": "count", "select": {"kind": "vm"}, "eq": 5}
    short = {"ok": True,
             "plan": [("create_vm", {"name": "vm1", "os_type": "linux"})],
             "program": {"body": [
                 {"op": "call", "tool": "create_vm",
                  "args": {"name": "vm1", "os_type": "linux"}},
                 {"op": "achieve", "predicate": goal},
                 {"op": "publish", "fact": "done"}]}}

    out = eng._execute_plan(short, [goal], sess)
    check(f"the run closes ok ({out.get('why')})", out["ok"] is True)
    check("the world reaches what was asked for", len(world.vms) == 5)
    check(f"every call is on the bill, the first pass included ({len(out['calls'])})",
          len([t for t, _ in out["calls"] if t == "create_vm"]) == 4)
    check("and the session records that it was DERIVED, not authored",
          any("derived a correction" in line for line in sess.log))


def test_a_gap_that_is_not_arithmetic_asks_for_the_second_engine():
    """WHERE `derive` RETURNS None THE GAP IS NOT COMPUTABLE, and that is a doorway rather
    than a failure. The engine sets `promote`; it never opens a tree itself, because a tree
    accrues cost and the thing asking for more is never the thing that should approve it."""
    print("[achieve] a gap nobody can compute is handed upward")
    world = _world(names=("alpha", "beta"))
    eng = Lab(world)
    sess = Session("keep them apart", eng, intent="achieve", regime="translation")

    # `disjoint` IS ONE OF `derive`'s NINE REFUSALS — there is no way to know which side of a
    # shared network should move, so it declines rather than guessing.
    goal = {"shape": "disjoint", "sets": ["$a", "$b"]}
    planned = {"ok": True, "plan": [],
               "program": {"body": [
                   # THE SETS MUST ACTUALLY OVERLAP, or the goal holds and the deriver is
                   # never asked — a test that proves a refusal by never reaching it. Both
                   # names bind the SAME set, so `disjoint` is false and unclosable: there
                   # is no way to know which side should move.
                   {"op": "fetch", "var": "a", "select": {"kind": "vm"}},
                   {"op": "fetch", "var": "b", "select": {"kind": "vm"}},
                   {"op": "achieve", "predicate": goal},
                   {"op": "publish", "fact": "done"}]}}
    out = eng._execute_plan(planned, [goal], sess)
    check(f"it does not report success ({out.get('why')})", not out["ok"])
    check("it asks for the tree", out.get("promote") == "tree")
    check("and says why, in the deriver's own words",
          "not arithmetic" in (out.get("why") or ""))


def test_a_correction_may_not_reach_above_the_rung_it_was_granted():
    """THE ONE DOOR NOBODY WAS WATCHING. A derived fix is computed, not authored, so it is
    the easiest place for creation to arrive under an authority that never licensed it. The
    corrective run meets the same ladder the first one did."""
    print("[achieve] a derived fix is still bound by the intent")
    world = _world(names=("alpha",))
    eng = Lab(world)
    goal = {"shape": "count", "select": {"kind": "vm"}, "eq": 5}
    planned = {"ok": True, "plan": [],
               "program": {"body": [{"op": "achieve", "predicate": goal},
                                    {"op": "publish", "fact": "done"}]}}
    # AN `ensure` SESSION NEVER REACHES THIS PROGRAM in production — the planner writes a
    # check — so the assertion is that the corrector does not become a second way in.
    sess = Session("five", eng, intent="ensure", regime="translation")
    eng._execute_plan(planned, [goal], sess)
    check("nothing was created under an ensure", len(world.vms) == 1)


def test_the_gate_is_still_behind_the_planner():
    """THE PLANNER SHAPES; THE GATE REFUSES. Two readings of one rule, and the second is not
    made redundant by the first — an engine with no intent-aware planner still has to be
    stopped, which is what the floor engine is."""
    print("[ladder] the backstop is still there")
    from orchestrator.ai.engines import ExecutorEngine
    from tests.test_engines import FakeLab

    world = _world()
    eng = ExecutorEngine(FakeLab(world), world.execute)
    sess = Session("delete alpha", eng, intent="fetch")
    seen = []
    out = insession.drive(
        eng, [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 0}],
        sess, lambda st, s: (seen.append(st) or insession.Verdict(insession.RUN)))
    check("the floor is refused", out.get("refused") is True)
    check("before the decider is asked", not seen)
    check("and alpha is still there", "alpha" in world.vms)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "intent ladder"))


if __name__ == "__main__":
    main()
