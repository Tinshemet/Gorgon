"""test_tree_sessions.py — ACHIEVE MEANS MAKE IT SO, and the tree is what makes that true.

    FETCH    tell me           TOOL         one call, one answer, close
    ENSURE   confirm it is so  TRANSLATION  components -> program -> run -> close
    ACHIEVE  make it so        TREE         autonomous, CORRECTS, cost accrues

That table has been in `session.py` since the day it was written, and `INTENT_REGIME` mapped
`achieve` to TRANSLATION anyway — so an achieve session got ONE program, ran it, and closed.
A goal the program did not reach came back UNMET rather than being corrected, which is
exactly the difference between `ensure` and `achieve`. CORRECTING IS THE WHOLE OF WHAT THE
THIRD REGIME BUYS, and nothing was buying it.

WHAT "ACTUALLY ACHIEVES" MEANS HERE, and it is the operator's phrase: at close, the goal
HOLDS — checked against the world, not against the program's own account of itself. A run
that made every call it planned and left the goal false is a failed achieve however cleanly
it reported.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import (Channel, MedusaEngine, Orchestrator, Registry, Session,
                                     insession)
from orchestrator.ai.engines.channel import Answer
from orchestrator.ai.engines.session import INTENT_REGIME
from tests.bench import fuzz
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


class Lab(MedusaEngine):
    name = "medusa"


def _serve(goals, world, intent="achieve", decide=None):
    reg = Registry()
    reg.mount(Lab(world))

    def translate(request, w=None):
        return Answer(goals, "table", "")
    translate.name = "table"
    orch = Orchestrator(reg, Channel([translate]),
                        decide=decide or (lambda st, s: insession.Verdict(insession.RUN)))
    return orch.handle("do it", intent=intent)


def test_achieve_starts_in_the_tree():
    """The mapping and the table now say the same thing."""
    print("[tree] the intent ladder agrees with itself")
    check("achieve is a tree", INTENT_REGIME["achieve"] == "tree")
    check("ensure is a translation", INTENT_REGIME["ensure"] == "translation")
    check("fetch is a tool", INTENT_REGIME["fetch"] == "tool")

    world = SimWorld()
    out = _serve([{"shape": "count", "select": {"kind": "vm", "name": "a"}, "eq": 1}], world)
    check("and a session opened with achieve reports the tree regime",
          out["regime"] == "tree")


def test_achieve_actually_achieves_every_rung():
    """THE OPERATOR'S TEST: at close, the goal HOLDS — checked against the world, not against
    the program's account of itself."""
    print("[tree] all 13 rungs, served as ACHIEVE, graded by their own checkers")
    failed = []
    for rung in RUNGS:
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        out = _serve(GOALS[rung.n], world, intent="achieve")
        if out["outcome"] != "DONE" or not rung.check(world):
            failed.append(f"rung {rung.n}: {out['outcome']}, checker={rung.check(world)}")
    check(f"{len(RUNGS) - len(failed)}/{len(RUNGS)} achieved for real ({failed or 'all'})",
          not failed)


def test_a_tree_asks_per_goal_and_closes_with_a_witness():
    """The grain is the regime's, and the parent's witness is what makes a tree correct
    rather than merely finer."""
    print("[tree] one exchange per goal, then the request as a whole")
    world = SimWorld()
    seen = []
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "a"}, "eq": 1},
             {"shape": "count", "select": {"kind": "vm", "name": "b"}, "eq": 1}]
    _serve(goals, world, decide=lambda st, s: (seen.append(st.why)
                                               or insession.Verdict(insession.RUN)))
    check("one exchange per goal", seen[:2] == ["one goal", "one goal"])
    check("and a closing witness over the whole request",
          seen[-1].endswith("witness"))
    check("the work happened", set(world.vms) == {"a", "b"})


def test_a_tree_corrects_a_goal_a_single_pass_would_have_left_unmet():
    """THE DIFFERENCE BETWEEN ENSURE AND ACHIEVE, made concrete. The set moves underneath the
    split — a machine appears while the goals are being served — and the closing witness
    re-plans against the world as it now is."""
    print("[tree] it corrects; a single pass would not have")
    world = SimWorld()
    for name in ("one", "two"):
        world.execute("create_vm", {"name": name, "os_type": "linux"})
    goals = [{"every": {"kind": "vm"}, "must": {"label": "audit"}}]
    added = [False]

    def meddle(step, session):
        if not added[0] and step.why == "one goal":
            added[0] = True
            world.execute("create_vm", {"name": "late", "os_type": "linux"})
        return insession.Verdict(insession.RUN)

    out = _serve(goals, world, decide=meddle)
    check("it still closes DONE", out["outcome"] == "DONE")
    check("and the machine that arrived LATE carries the label too",
          "audit" in world.vms["late"]["labels"])
    check("the keeper recorded that the world moved",
          (out.get("tree") or {}).get("verdict") == "infected")


def test_new_reaches_its_goal_rather_than_merely_running():
    """"if you call achieve and new they actually achieve their goals." A creation that ran
    and left the member absent is not a creation."""
    print("[tree] a creation is judged by what exists afterwards")
    world = SimWorld()
    goals = [{"shape": "count",
              "select": {"kind": "vm", "name": "made", "status": "running"}, "eq": 1}]
    out = _serve(goals, world)
    check("it closed DONE", out["outcome"] == "DONE")
    check("the machine exists", "made" in world.vms)
    check("and is in the state that was asked for",
          world.vms["made"]["status"] == "running")


def test_a_tree_never_reports_done_over_a_goal_that_does_not_hold():
    """Across generated cases, because this is the property a tree can break in ways nobody
    would think to write a case for."""
    print("[tree] 400 generated requests, served as ACHIEVE")
    lied = []
    for seed in range(400):
        world, goals, _text = fuzz.random_case(seed)
        out = _serve(goals, world, intent="achieve")
        if out["outcome"] == "DONE" and not fuzz.holds_all(goals, world)[0]:
            lied.append(seed)
    check(f"no achieve claimed success over a false goal ({lied[:4] or 'none'})", not lied)


def test_a_creation_that_did_not_happen_is_caught_by_the_world():
    """#20's first half — "NEW's internal ACHIEVE" — and it already exists, as the WITNESS.

    A creator that returns `success: False` is a tool saying it failed, and a program that
    believed tools would be trusting exactly the flag decision 6 forbids. It does not: the
    writer grounds every goal it plans, so the closing ENSURE asks the WORLD whether the
    machine is there and the run fails with `count is 0, wanted == 1`.

    THAT IS WHY IT NEEDS NO SEPARATE MECHANISM. An "internal achieve" on `new` would be a
    second check of the same fact, and the one that already exists is the stronger of the
    two: it asks the registry rather than the caller.
    """
    print("[tree] a creation is proven by the world, not by the tool's return")
    from planner.ir import run as ir_run
    from planner.ir import validate
    from tests.bench.seams import seams as vm_seams

    world = SimWorld()
    attempted = []

    def refuses(tool, args):
        attempted.append(tool)
        return {"success": False, "error": "disk full"}

    program = {"body": [
        {"op": "new", "var": "a", "kind": "vm", "amount": 1,
         "args": {"name": "a", "os_type": "linux"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "name": "a"}, "eq": 1}}]}
    ok, problems = validate(program, known_names=world.names())
    check("the program is well formed", ok and not problems)

    select, holds = vm_seams(world)
    result = ir_run(program, refuses, select=select, holds=holds,
                    known_names=world.names(), consent=True, intent="achieve")
    check("the creator was attempted", attempted == ["create_vm"])
    check("the run FAILS rather than believing the tool",
          not result.get("ok"))
    check("and the reason is what the WORLD says, not what the tool returned",
          "count is 0" in str(result.get("why") or result.get("failed")))
    check("nothing was created", not world.vms)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "tree sessions"))


if __name__ == "__main__":
    main()
