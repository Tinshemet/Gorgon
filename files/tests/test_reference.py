#!/usr/bin/env python3
"""
test_reference.py — the syntax guide describes the language that exists.

WHAT THIS SUITE IS FOR. `ir/reference.py` writes the operator's Medusa reference into the
procedures folder, and it is GENERATED so that it cannot describe a grammar the parser does
not have. That argument is only worth anything if it is checked: a generator can still read
the wrong table, drop an op, or carry a worked example that stopped parsing two commits ago.

THE EXAMPLES ARE THE PART THAT CAN ROT. Everything else is copied from the language
definition and is true by construction; an example is a JUDGEMENT written by hand. So every
one of them is PARSED HERE, with the real parser, and a stale example fails the suite rather
than teaching somebody a shape the language stopped accepting.

Run:  PYTHONPATH=. python3 -m tests.test_reference
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.ir import config
from planner.ir.parse import parse_many
from planner.ir.reference import examples, render_reference

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_every_worked_example_parses():
    """A SHAPE THE LANGUAGE NO LONGER ACCEPTS IS WORSE THAN NO EXAMPLE.

    The reference is the first thing an operator reads before writing a program. An example
    that does not parse sends them to debug their own file for a mistake the guide made.
    """
    print("[reference] every worked example is a program the parser takes")
    for ex in examples():
        try:
            got = parse_many(ex["code"])
            check(f"{ex['title']!r} parses", bool(got))
        except Exception as e:
            check(f"{ex['title']!r} parses — {type(e).__name__}: {e}", False)


def test_every_example_is_explained():
    """An example with no WHY is a snippet to copy, which is how cargo-culting starts."""
    print("[reference] every example says why it is shaped that way")
    for ex in examples():
        check(f"{ex['title']!r} carries a reason", len((ex.get("why") or "").strip()) > 40)


def test_the_reference_names_every_op_and_check():
    """DERIVED, AND ASSERTED TO BE DERIVED. Adding an op must not silently leave it out.

    This is the whole claim of generating the guide rather than typing it, so it is the one
    thing worth failing over: a reference that is missing the op somebody just added is a
    second description of the grammar again.
    """
    print("[reference] nothing in the language is left out of the guide")
    text = render_reference()
    for op in config.OPS:
        word = config.SURFACE.get(op, op.upper())
        check(f"`{word}` is documented", f"`{word}`" in text)
    for pred in config.PREDICATES:
        check(f"the {pred.upper()} check is documented", f"`{pred.upper()}`" in text)
    for name, spec in config.PARAM_TYPES.items():
        check(f"the {spec.get('sql', name)} type is documented",
              f"`{spec.get('sql', name.upper())}`" in text)


def test_every_method_a_kind_has_is_in_the_guide():
    """THE SURFACE EXISTED FOR TWO DAYS AND APPEARED IN NO DOCUMENT ANYONE READS.

    `$box.launch()` parsed since 2026-08-02, and the generated reference — the only
    description of the language a person or a model ever sees — never mentioned it. That is
    the same defect the op table exists to prevent, one layer up: a capability nobody can
    discover is a capability nobody has.

    THE CONSTRUCTOR IS THE ONE THING DELIBERATELY ABSENT, because `$box.create()` is not a
    form the parser accepts and documenting a line that does not parse is worse than
    documenting nothing.
    """
    print("[reference] every method a kind has is written down")
    from planner.ir import classes
    text = render_reference()
    for kind, methods in classes.surface().items():
        for m in methods.values():
            written = f"`${kind}.{m.name}(" in text
            check(f"`${kind}.{m.name}()` is documented",
                  written if m.verb != classes.MAKE else not written)


def test_it_says_the_extension_the_store_actually_writes():
    """TWO ANSWERS TO "WHAT IS A MEDUSA FILE CALLED" IS HOW THIS WENT WRONG.

    `language.extension` read `.med` until 2026-08-02 while the store had always written
    `.medusa`, and NOTHING read the field — so the declared answer was unused and wrong at
    the same time. The reference reads it now, which is what makes the two able to disagree
    loudly instead of quietly.
    """
    print("[reference] the declared extension is the one on disk")
    from planner.procedures import Store
    check("the config declares .medusa", config.LANGUAGE.get("extension") == ".medusa")
    check("and the reference tells the operator that",
          f"`{config.LANGUAGE['extension']}`" in render_reference())
    # THE STORE IS THE AUTHORITY ON WHERE FILES GO, so it is asked rather than assumed.
    import tempfile
    S = Store(tempfile.mkdtemp(prefix="gorgon-ref-"))
    at = S.save({"name": "shape_check", "params": {},
                 "body": [{"op": "new", "kind": "vm", "var": "box1", "tool": "create_vm",
                           "args": {"os_type": "linux", "name": "box1"}},
                          {"op": "publish", "fact": "box1"}]})
    check("a saved program uses that extension",
          at.endswith(config.LANGUAGE["extension"]))


def test_the_guide_is_written_beside_the_programs_and_is_not_one():
    """`names()` LISTS EVERY `*.medusa` HERE, so the guide must not carry that extension.

    A reference file with the language's own extension would arrive in the library as a
    program, be handed to the parser, and be reported as broken — the guide breaking the
    thing it exists to explain.
    """
    print("[reference] the guide lives with the programs without becoming one")
    import tempfile
    from planner.procedures import Store
    S = Store(tempfile.mkdtemp(prefix="gorgon-ref-"))
    at = S.write_reference()
    check("it is written into the procedures folder", os.path.dirname(at) == S.path)
    check("it is not a .medusa", not at.endswith(".medusa"))
    check("so the library does not list it as a program", S.names() == [])
    check("and it says out loud that editing it does nothing",
          "GENERATED" in open(at).read())

    # AND A SAVE REFRESHES IT, which is what keeps it from going stale.
    os.remove(at)
    S.save({"name": "anything", "params": {},
            "body": [{"op": "new", "kind": "vm", "var": "b", "tool": "create_vm",
                      "args": {"os_type": "linux", "name": "b"}},
                     {"op": "publish", "fact": "b"}]})
    check("saving a program rewrites the guide", os.path.exists(at))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the syntax reference"))


if __name__ == "__main__":
    main()
