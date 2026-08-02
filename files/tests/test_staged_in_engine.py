"""test_staged_in_engine.py — STAGED LOWERING, as a thing the Medusa engine does.

WHERE IT SITS, AND WHY THAT IS THE WHOLE DESIGN. The ghost writer is deterministic and covers
every rung; handing a model the job it already does would trade a measured 13/13 for a
measured 4/13. So staged lowering is NOT a first choice. It is what happens when the writer
says `Unsolvable` — no tile, no rule, will not improvise — which was already the promotion
signal. Staged lowering is what a promotion BUYS.

    writer covers it            -> one program, no model, done
    writer refuses + no grant   -> promote: the orchestrator is ASKED
    writer refuses + tree grant -> open the goal until every leaf is ONE operator,
                                   emit each against ONE branch, fuse, and GRADE THE
                                   ASSEMBLED ARTIFACT BEFORE ANYTHING RUNS

The author and router are STUBBED here and deterministic. What is being tested is the
seam — that the engine reaches staged lowering only where it should, grades before running,
and refuses an artifact that cannot vouch for itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import MedusaEngine, Session, insession
from planner.model_world import World

_PASS = _FAIL = 0

# A kind whose members can be MADE and never changed — so "give every dish four servings"
# is genuinely unreachable and the writer refuses it. That refusal is the door.
KITCHEN = {
    "dish": {"key": "dish_name", "attrs": ["dish_name", "serves"], "nouns": ["dish"],
             "create": "create_dish", "setters": {}},
}


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _route(goal):
    """One split, then atomic leaves. Deterministic: no model, no ambiguity.

    A BRANCH MUST NAME ITS OPERATOR TOO, not only a leaf. `fuse` refuses a decomposing node
    that named none, and loudly: silently concatenating would turn a `foreach` the author
    meant into a flat sequence that runs once — which validates, executes, and does the
    wrong thing. `seq` is the plain sequence: its children run in order.
    """
    if goal.startswith("two dishes"):
        return {"atomic": False, "op": "seq",
                "steps": ["make risotto", "make paella"]}
    return {"atomic": True, "op": "call"}


def _author(leaf, schema, objection, context, ancestry):
    """One statement per leaf, from the leaf's own goal. A stand-in for the model.

    IT HONOURS THE LEAF'S OPERATOR, because a leaf is offered ONE operator's schema and an
    author that ignored it would be testing a decoder nobody ships. `ground` asks for an
    `achieve` leaf when the tree asserts nothing, and this answers that too.
    """
    if leaf.get("op") in ("achieve", "ensure"):
        # A WITNESS THAT COULD FAIL. `>= 1` would hold before the program ran — the seeded
        # dish alone satisfies it — and an assertion that cannot fail witnesses nothing.
        return {"op": leaf["op"],
                "predicate": {"shape": "count", "select": {"kind": "dish"}, "gte": 3}}
    name = leaf["goal"].split()[-1]
    return {"op": "call", "tool": "create_dish", "args": {"dish_name": name}}


def _ungrounded_author(leaf, schema, objection, context, ancestry):
    """Emits acts and REFUSES to author a verdict — the case `ground` cannot rescue."""
    if leaf.get("op") in ("achieve", "ensure"):
        return None
    return {"op": "call", "tool": "create_dish", "args": {"dish_name": "same"}}


def _rig(author=_author, route=_route, regime="tree", seed=("stew",)):
    world = World(KITCHEN)
    # A DISH THAT ALREADY EXISTS is what makes the goal unreachable. Over an EMPTY world
    # "every dish must serve four" is VACUOUSLY TRUE — no members, nothing to do — and the
    # writer closes it without complaint. The first version of this file tested that by
    # accident and proved nothing.
    for name in seed:
        world.execute("create_dish", {"dish_name": name})
    eng = MedusaEngine(world, author=author, route=route)
    sess = Session("two dishes", eng, intent="achieve")
    sess.regime = regime
    return eng, world, sess


# The goal carries the sentence it came from. Staged lowering opens PROSE; the writer covers
# structure, and manufacturing prose from structure would be writing the request.
UNREACHABLE = [{"every": {"kind": "dish"}, "must": {"serves": "4"}, "_goal": "two dishes"}]


def test_the_writer_is_tried_first_and_staged_lowering_is_not_reached():
    """A goal the writer CAN cover never touches the model, however loudly one is offered."""
    print("[staged] the deterministic path keeps its job")
    called = []

    def loud(leaf, schema, objection, context, ancestry):
        called.append(leaf)
        return {"op": "call", "tool": "create_dish", "args": {"dish_name": "x"}}

    eng, world, sess = _rig(author=loud)
    out = insession.drive(eng, [{"shape": "count",
                                 "select": {"kind": "dish", "dish_name": "risotto"},
                                 "eq": 1}], sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("the writer served it", out.get("ok"))
    check("and the author was never asked", not called)
    check("the dish exists", "risotto" in world.state["dish"])


def test_a_refusal_without_a_tree_grant_still_only_asks():
    """Staged lowering costs a model. Whoever holds the budget grants it, or it does not
    happen — the engine that wants it may not help itself."""
    print("[staged] no grant, no lowering — it asks, as before")
    called = []

    def loud(leaf, schema, objection, context, ancestry):
        called.append(leaf)
        return None

    eng, _, sess = _rig(author=loud, regime="translation")
    out = insession.drive(eng, UNREACHABLE, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("it asks for the tree regime", out.get("promote") == "tree")
    check("and spent nothing asking", not called)


def test_a_granted_promotion_buys_staged_lowering():
    """THE POINT. A promotion used to record itself and re-run the same writer; now it
    reaches a different mechanism."""
    print("[staged] the grant buys per-leaf authoring")
    eng, world, sess = _rig()
    out = insession.drive(eng, UNREACHABLE, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("it did not merely ask again", out.get("promote") is None)
    check("the goal was opened and every leaf emitted",
          any("staged:" in l for l in sess.log))
    check("and the work happened",
          set(world.state["dish"]) == {"stew", "risotto", "paella"})


def test_the_artifact_is_graded_before_anything_runs():
    """THE PROGRAM REGIME'S ADVANTAGE, KEPT. An inert artifact can be refused for free."""
    print("[staged] graded while it is still inert")

    eng, world, sess = _rig(author=_ungrounded_author)
    out = insession.drive(eng, UNREACHABLE, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("the grade was taken and recorded",
          any("grounded=" in l for l in sess.log))
    check("a program that vouches for nothing is refused",
          not out.get("ok") and "vouches for nothing" in (out.get("why") or ""))
    check("and it was refused BEFORE running — nothing new was made",
          set(world.state.get("dish") or ()) == {"stew"})


def test_decorative_grounding_is_refused():
    """#53, ARRIVING IN A NEW PLACE — and answered with a COMPUTATION, not a heuristic.

    `consent.vacuous` does not catch this and should not: it is deliberately narrow and
    refused a relevance test because a false accusation of vacuity is worse than a missed
    one. The ENGINE has something that check cannot have — the world as it is BEFORE the
    program runs — so it evaluates the witness against it and declines nothing.

    Measured on the first staged program ever built here: it closed with
    `ACHIEVE COUNT(dish) >= 1` over a world that already held one — true before the program
    ran, and therefore a witness to nothing. The cheapest way to satisfy a demand for
    grounding is decorative grounding, which matters most on the day the demand starts
    being enforced.
    """
    print("[staged] an assertion that cannot fail is not a witness")

    def decorative(leaf, schema, objection, context, ancestry):
        if leaf.get("op") in ("achieve", "ensure"):
            return {"op": leaf["op"],
                    "predicate": {"shape": "count", "select": {"kind": "dish"}, "gte": 1}}
        name = leaf["goal"].split()[-1]
        return {"op": "call", "tool": "create_dish", "args": {"dish_name": name}}

    eng, world, sess = _rig(author=decorative)
    out = insession.drive(eng, UNREACHABLE, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("it is refused", not out.get("ok"))
    check("and named as decorative rather than absent",
          "ALREADY HOLD" in (out.get("why") or ""))
    check("nothing ran", set(world.state.get("dish") or ()) == {"stew"})


def test_a_goal_with_no_sentence_behind_it_is_left_alone():
    """Staged lowering opens PROSE. Manufacturing a sentence from structure would be writing
    the request rather than serving it — the mistake #55 already recorded."""
    print("[staged] no prose, nothing to open")
    eng, _, sess = _rig()
    bare = [{"every": {"kind": "dish"}, "must": {"serves": "4"}}]
    out = insession.drive(eng, bare, sess, lambda st, s: insession.Verdict(insession.RUN))
    # ALREADY IN THE TREE, so there is nothing to ask for. What matters is that it did not
    # INVENT prose to decompose — it failed with the writer's own reason.
    check("it does not invent a goal to decompose", out.get("promote") is None)
    check("and carries the writer's refusal", "cannot be placed" in str(out.get("why") or "")
          or "nothing reaches" in str(out.get("why") or ""))


def test_an_engine_with_no_author_is_exactly_what_it_was():
    """13/13 rungs with no model at all, and that must stay true."""
    print("[staged] the seam is optional and absent by default")
    world = World(KITCHEN)
    world.execute("create_dish", {"dish_name": "stew"})
    eng = MedusaEngine(world)
    sess = Session("two dishes", eng, intent="achieve")
    sess.regime = "tree"
    out = insession.drive(eng, UNREACHABLE, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("no author means no staged lowering", not out.get("ok"))
    check("and no request for a regime it already holds", out.get("promote") is None)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "staged lowering in the engine"))


if __name__ == "__main__":
    main()
