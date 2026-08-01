"""test_writer_output_is_writable.py — could a PERSON have written what the writer emits?

THE HOLE THIS CLOSES, found by the operator reading a rendered program: the ghost writer
builds IR DIRECTLY. It never passes through the schema the MODEL is decoded against, so it
can emit statements the grammar forbids — and every suite stays green, because every suite
checks what the program DOES rather than whether it is sayable.

It happened immediately. Emitting `new` for creations put the member's KEY VALUE in the
variable slot:

    STORE http://x = NEW page(url: http://x);

`http://x` is a name for a thing in the world; a variable is an identifier in a program.
Different alphabets. Fed back in, or typed by hand, that program fails — and nothing noticed
because nothing was asking.

TWO PROPERTIES, AND THEY ARE NOT THE SAME:
    it VALIDATES   — `validate` accepts it, which every other suite already covers
    it is WRITABLE — the schema the model is held to would have accepted it too

The second is what makes a program readable back, editable by an operator, and comparable
against one a model produced. A generator held to weaker rules than the language's own users
is a generator that drifts out of the language.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner import ghost_writer as gw
from orchestrator.ai.planner.ir import config, schema as _schema, validate
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld
from tests.test_ghost_writer import GOALS

_PASS = _FAIL = 0

# WHAT A BOUND NAME MAY LOOK LIKE. The schema calls it "pronounceable"; this is that rule
# written where a test can apply it, and it is deliberately the SAME shape a person would
# accept — a word, not a URL and not a sentence.
_PRONOUNCEABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _walk(body):
    for st in body or ():
        yield st
        for field in ("do", "then", "else"):
            if isinstance(st.get(field), list):
                yield from _walk(st[field])


def _programs():
    for n in sorted(GOALS):
        rung = next(r for r in RUNGS if r.n == n)
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        plan = gw.cover(GOALS[n], world)
        yield n, gw.as_program(plan, GOALS[n], world)


def test_every_bound_name_is_a_name_a_person_could_type():
    """The one that would have caught `STORE http://x =`."""
    print("[writable] bindings are identifiers, not values")
    bad = []
    for n, program in _programs():
        for st in _walk(program["body"]):
            for slot in ("var", "graft"):
                name = st.get(slot)
                if name is not None and not _PRONOUNCEABLE.match(str(name)):
                    bad.append(f"rung {n}: {slot}={name!r}")
    check(f"no binding is unpronounceable ({bad or 'all clean'})", not bad)


def test_every_statement_names_an_operator_the_language_has():
    """A statement whose `op` is not one of the seven is not Medusa, whatever it does."""
    print("[writable] the operator set is closed")
    legal = set(_schema.OPS) if hasattr(_schema, "OPS") else {
        "new", "fetch", "call", "foreach", "ensure", "achieve", "if"}
    strays = []
    for n, program in _programs():
        for st in _walk(program["body"]):
            if st.get("op") not in legal:
                strays.append(f"rung {n}: op={st.get('op')!r}")
    check(f"every statement is one of {sorted(legal)} ({strays or 'all legal'})", not strays)


def test_every_program_the_writer_emits_validates():
    """The property the other suites already rely on, asserted where it belongs."""
    print("[writable] and the validator accepts all thirteen")
    bad = []
    for n, program in _programs():
        world = SimWorld()
        rung = next(r for r in RUNGS if r.n == n)
        if rung.setup:
            rung.setup(world)
        ok, problems = validate(program, known_names=world.names())
        if not ok:
            bad.append(f"rung {n}: {problems[:1]}")
    check(f"all thirteen validate ({bad or 'all clean'})", not bad)


def test_the_guard_actually_fires_on_the_shape_that_slipped_through():
    """A test that cannot fail is not a guard. This is the exact statement that shipped."""
    print("[writable] the guard is not decorative")
    offending = {"op": "new", "var": "http://x", "kind": "page", "args": {"url": "http://x"}}
    check("an unpronounceable binding is rejected",
          not _PRONOUNCEABLE.match(offending["var"]))
    check("and an ordinary one is not", bool(_PRONOUNCEABLE.match("page1")))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "writer output is writable"))


if __name__ == "__main__":
    main()
