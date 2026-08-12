"""test_select_seams_agree.py — THE THREE SELECT SEAMS ANSWER THE SAME QUESTION.

There are three implementations of "which members match this filter set":

    planner/program.py::_one        production — the Active Library
    planner/model_world.py::_match  the DRY RUN's scratch world
    tests/bench/seams.py::_matches  the bench

They must agree, because the dry run's whole job is to predict what production will do.
A program is proved LEGAL against the second and RUN against the first, so any divergence
between them is a false verdict by construction — and the bench decides whether we believe
either.

⇒ THE BUG THIS PINS, found 2026-08-13 and present in ALL THREE at once.

`not` was stripped as a structural key before the attribute loop, and the `any`/`all` group
loop recursed into that same function. So a `not` nested INSIDE a group was never applied,
and every group child was vacuously true:

    all:[{not:db},{not:log}]   production  ['a','db','log']   <- acted on what it must spare
                               dry run     []                 <- selected nobody
                               wanted      ['a']

Two different wrong answers from one cause, which is why it survived: neither seam looked
broken from inside the other. `schema.select_of` emits exactly that shape for several
carve-outs, so rung 8's "everything except db" family is what depends on it.

⇒ WHY THIS TEST IS A TABLE AND NOT THREE TESTS.

The defect was one blind spot copied three times, so a test per seam would have been written
three times from the same misunderstanding and passed three times. Asking the SAME question
of every seam in one loop is the only shape that fails when the copies agree with each other
and disagree with the language.
"""
from types import SimpleNamespace

from planner.model_world import World, seams as model_seams
from planner.program import make_select

_FAIL = 0


def check(label, ok):
    global _FAIL
    if not ok:
        _FAIL += 1
    print(f"    {'ok  ' if ok else 'FAIL'}  {label}")


# name -> row. Deliberately three members so a carve-out of two leaves exactly one, which
# tells a "matched everything" bug apart from a "matched nobody" one at a glance.
ROWS = {"a": {"name": "a"}, "db": {"name": "db"}, "log": {"name": "log"}}

CASES = [
    ("plain",            {"kind": "vm"},                                          ["a", "db", "log"]),
    ("one carve-out",    {"kind": "vm", "not": {"name": "db"}},                    ["a", "log"]),
    # THE REGRESSION. `select_of` emits this for two or more exclusions.
    ("two carve-outs",   {"kind": "vm", "all": [{"not": {"name": "db"}},
                                                 {"not": {"name": "log"}}]},        ["a"]),
    ("any group",        {"kind": "vm", "any": [{"name": "a"}, {"name": "db"}]},   ["a", "db"]),
    # A tautology: everything is either `a` or not `a`. It fails loudly if a nested `not`
    # is read as "always false" instead of as a negated sub-match.
    ("any of x, not-x",  {"kind": "vm", "any": [{"name": "a"},
                                                 {"not": {"name": "a"}}]},          ["a", "db", "log"]),
    ("all of one",       {"kind": "vm", "all": [{"not": {"name": "db"}}]},          ["a", "log"]),
]


def _production():
    return make_select(SimpleNamespace(_vms=dict(ROWS)))


def _dry_run():
    world = World(kinds={"vm": {"key": "name"}})
    world.state["vm"] = dict(ROWS)
    select, _holds = model_seams(world)
    return select


def test_every_seam_answers_the_same_select():
    """One question, asked of each seam, per case."""
    print("[seams] the same select, three implementations")
    for label, sel, wanted in CASES:
        for who, select in (("production", _production()), ("dry run", _dry_run())):
            got = select(sel)
            check(f"{label:16} {who:11} -> {got}", got == wanted)


def test_a_carve_out_is_the_same_fact_flat_or_nested():
    """`not: X` and `all: [{not: X}]` are the same request written two ways.

    This is the property the bug violated, stated directly rather than through a literal:
    if these two ever diverge, one of the forms has grown a meaning the other lacks — which
    is precisely how `select_of` acquired a shape no seam could answer.
    """
    print("[seams] flat and nested carve-outs mean the same thing")
    for who, select in (("production", _production()), ("dry run", _dry_run())):
        flat = select({"kind": "vm", "not": {"name": "db"}})
        nested = select({"kind": "vm", "all": [{"not": {"name": "db"}}]})
        check(f"{who:11} flat {flat} == nested {nested}", flat == nested)


if __name__ == "__main__":
    test_every_seam_answers_the_same_select()
    test_a_carve_out_is_the_same_fact_flat_or_nested()
    print(f"\n{_FAIL} failed")
