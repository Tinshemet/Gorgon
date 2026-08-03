"""test_goals.py — THE GOAL VOCABULARY, and the contract between the two halves that use it.

A goal is the only thing that crosses the front seam. The extractor EMITS them, the ghost
writer CONSUMES them, and until now nothing asserted the two agreed on what the set was.
That is the shape of every silent divergence this project has found: two components that
work, a vocabulary they each believe they share, and no test between them.

WHAT IS ASSERTED HERE

    the set is CLOSED and both halves know the same one — derived from the schema's own
    enum, so adding a shape to one side without the other fails here rather than in a
    ladder number three weeks later
    every shape the extractor can emit, the writer can plan
    every shape that CAN be witnessed IS witnessed, and the two that cannot say why
    a goal states one thing about one set, and the writer never has to guess a field

NO MODEL, NO WORLD STATE THAT MATTERS. These are properties of the vocabulary itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner import ghost_writer as gw
from planner.ir import config, effects
from engines import extract
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


def _emitted_shapes() -> set:
    """The goal names the SCHEMA lets a model choose — the extractor's side of the contract."""
    return set(extract.goal_shapes())


# One well-formed raw goal per shape the schema offers, as a model would send it.
RAW = {
    "count":   {"goal": "count", "select": {"kind": "vm"}, "amount": 2},
    "reach":   {"goal": "reach", "select": {"kind": "vm"}, "amount": 2},
    "every":   {"goal": "every", "select": {"kind": "vm"}, "attr": "status",
                "value": "running"},
    "per":     {"goal": "per", "select": {"kind": "vm"}, "make": "snapshot", "link": "vm"},
    "observe": {"goal": "observe", "select": {"kind": "vm"}, "fact": "alive"},
}
# THE REQUEST MUST JUSTIFY EVERY FIXTURE BELOW, because `to_goals` now refuses a goal the
# request gives no evidence for — a `reach` nobody asked about, and a `per` that MAKES a kind
# the request never mentions. Both guards read the sentence, so a fixture set exercised
# against a sentence that does not cover it is testing the guard, not the shape.
_ASKING = ("make sure the machines can reach each other and are up, and take a snapshot "
           "of each")


def _world():
    w = SimWorld()
    for name in ("alpha", "beta"):
        w.execute("create_vm", {"name": name, "os_type": "linux"})
    return w


def test_the_schema_and_the_fixtures_cover_the_same_set():
    """The fixtures below ARE this test's coverage claim, so they are checked against the
    schema rather than trusted. A shape added to the schema and not here would otherwise
    look tested."""
    print("[contract] every shape the model may choose is exercised")
    check(f"the schema offers {sorted(_emitted_shapes())}",
          _emitted_shapes() == set(RAW))


def test_every_shape_the_extractor_emits_the_writer_can_plan():
    """The seam itself: emitted -> converted -> planned, with nothing in between."""
    print("[contract] emitted, converted, planned")
    for shape, raw in sorted(RAW.items()):
        goals = extract.to_goals({"goals": [raw]}, _ASKING)
        check(f"{shape}: converts to exactly one goal", len(goals) == 1)
        if not goals:
            continue
        try:
            plan = gw.cover(goals, _world())
            planned = True
        except gw.Unsolvable as e:
            planned, plan = False, str(e)
        check(f"{shape}: the writer plans it ({len(plan) if planned else plan})", planned)


def test_a_goal_that_can_be_witnessed_is():
    """Grounding is not optional for anything that states a STATE."""
    print("[contract] states get a witness; acts say why they cannot")
    for shape, raw in sorted(RAW.items()):
        goals = extract.to_goals({"goals": [raw]}, _ASKING)
        if not goals:
            continue
        g = goals[0]
        world = _world()
        program = gw.as_program(gw.cover(goals, world), goals, world)
        ensures = [st for st in program["body"] if st.get("op") == "ensure"]
        if gw.groundable(g):
            check(f"{shape}: closes with a witness", bool(ensures))
        else:
            # AN OBSERVATION IS A THING DONE, NOT A THING THAT BECOMES TRUE. The language has
            # no predicate for "has been asked", and growing one to make this uniform would
            # be inventing a state to satisfy a shape.
            check(f"{shape}: is ungroundable, and that is not the same as ungrounded",
                  not ensures)


def test_the_writer_can_name_every_goal_it_accepts():
    """These strings appear in refusals and in the book keeper's report."""
    print("[contract] no goal renders as an unknown shape")
    for shape, raw in sorted(RAW.items()):
        goals = extract.to_goals({"goals": [raw]}, _ASKING)
        if not goals:
            continue
        said = gw._short(goals[0])
        check(f"{shape}: {said!r}", "?" not in said and "None" not in said)
    check("and an internal bare call names its tool",
          gw._short({"_call": ("guest_ping", {"name": "alpha"})}).startswith("call guest_ping"))


def test_a_goal_names_a_kind_the_manifest_declares():
    """A goal about a kind nobody declared is not a goal, and is dropped rather than planned
    against an empty spec."""
    print("[contract] the kind is the manifest's, not the model's")
    check("an undeclared kind is refused by the schema's own enum",
          set(extract.SCHEMA["properties"]["goals"]["items"]["oneOf"][0]["properties"]
              ["select"]["properties"]["kind"]["enum"]) == set(config.KINDS or {}))
    check("and a goal with no kind at all is dropped",
          not extract.to_goals({"goals": [{"goal": "count", "select": {}}]}))


def test_every_goal_reduces_to_a_tool_the_manifest_names():
    """The floor of the whole design: a goal is only ever satisfied by a declared tool."""
    print("[contract] planning never invents a tool")
    known = effects.tools_of(None)
    for shape, raw in sorted(RAW.items()):
        goals = extract.to_goals({"goals": [raw]}, _ASKING)
        if not goals:
            continue
        used = {tool for tool, _ in gw.cover(goals, _world())}
        check(f"{shape}: uses only declared tools {sorted(used) or '(none needed)'}",
              used <= known)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "goal vocabulary"))


if __name__ == "__main__":
    main()
