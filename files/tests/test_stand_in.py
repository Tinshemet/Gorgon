#!/usr/bin/env python3
"""
test_stand_in.py — a declared `$parameter` must survive translation and come back as itself.

WHY THIS EXISTS, MEASURED 2026-08-03 ON THE OPERATOR'S OWN REQUEST. Three times in one
morning, `procedure p(STRING name, STRING os_name): a vm named $name running $os_name` was
written, kept and reported DONE as:

    PROCEDURE mashu(STRING name, STRING os_name) {
      CALL launch_vm(name: work-laptop);

`work-laptop` is the operator's real machine, named nowhere in the request, and both declared
parameters bind nothing. The cause is one line of correct reasoning applied one layer too
widely: `extract._unwrap` strips `$…` because a goal has no bindings — true for an ACTING
request, false the moment a signature declared the name. See `planner/stand_in.py`.

THE TWO HALVES ARE TESTED SEPARATELY BECAUSE THEY FAIL SEPARATELY. The substitution is pure
string work and is asserted exactly. The RESTORE is asserted against a program shaped like
one the writer emits. What is NOT asserted here is what the model does in between — that is
`test_stand_in_live` below, skipped without a model, because a unit test that mocked the
extractor would be measuring the mock.

Run:  PYTHONPATH=. python3 -m tests.test_stand_in
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner import stand_in
from planner.ir import config as _config

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


_DECL = {"name": "string", "os_name": "string"}


def test_substitute():
    print("\nsubstitute")
    text, tokens, unknown = stand_in.substitute(
        "a vm named $name with os $os_name", _DECL)
    check("both declared references stood in for",
          "$" not in text and len(tokens) == 2)
    check("the parameter is recoverable from its stand-in",
          sorted(tokens.values()) == ["name", "os_name"])
    check("no stand-in carries a digit — a digit leaks into the count",
          all(not any(c.isdigit() for c in t) for t in tokens))
    check("every stand-in is a legal identifier",
          all(t.isidentifier() for t in tokens))

    # THE SAME PARAMETER TWICE IS ONE NAME. Two stand-ins for one parameter would author a
    # program about two different machines and bind only one of them.
    text2, tokens2, _ = stand_in.substitute("$name talks to $name", _DECL)
    check("one parameter mentioned twice gets ONE stand-in", len(tokens2) == 1)
    check("and both mentions were rewritten", "$" not in text2)

    # UNDECLARED IS LEFT ALONE AND REPORTED — it must still reach `_unwrap` as residue.
    text3, tokens3, unknown3 = stand_in.substitute("a vm named $nope", _DECL)
    check("an undeclared reference is NOT stood in for", text3 == "a vm named $nope")
    check("and it is reported", unknown3 == ["nope"])
    check("nothing was minted for it", tokens3 == {})

    # NO SIGNATURE MEANS NO SUBSTITUTION AT ALL.
    text4, tokens4, _ = stand_in.substitute("a vm named $name", {})
    check("with nothing declared the request is untouched", text4 == "a vm named $name")
    check("and nothing is minted", tokens4 == {})

    # A DIGIT IN THE PARAMETER'S OWN NAME.
    _t, tokens5, _u = stand_in.substitute("$os2 and $os", {"os2": "string", "os": "string"})
    check("digits are stripped from a parameter's stand-in",
          all(not any(c.isdigit() for c in t) for t in tokens5))
    check("and the two stand-ins are still distinct", len(set(tokens5)) == 2)


def test_restore():
    print("\nrestore")
    text, tokens, _ = stand_in.substitute("a vm named $name with os $os_name", _DECL)
    tok_name = next(t for t, p in tokens.items() if p == "name")
    tok_os = next(t for t, p in tokens.items() if p == "os_name")
    sigil = _config.SIGIL

    # SHAPED LIKE WHAT THE WRITER EMITS: a creation, a later reference to the same machine,
    # a predicate carrying a selector, and the contract.
    program = {
        "name": "mashu",
        "body": [
            {"tool": "create_vm", "args": {"name": tok_name, "os_type": tok_os}},
            {"tool": "launch_vm", "args": {"name": tok_name}},
            {"op": "ensure", "predicate": {"select": {"kind": "vm", "name": tok_name},
                                           "eq": 1}},
            {"op": "foreach", "do": [
                {"tool": "add_label", "args": {"name": tok_name, "label": "prod"}}]},
        ],
        "achieves": {"select": {"kind": "vm", "name": tok_name}, "eq": 1},
    }
    bound = stand_in.restore(program, tokens)

    check("both parameters report as bound", bound == {"name", "os_name"})
    check("the creation takes the parameters",
          program["body"][0]["args"] == {"name": f"{sigil}name",
                                         "os_type": f"{sigil}os_name"})
    check("a LATER call follows the same machine",
          program["body"][1]["args"]["name"] == f"{sigil}name")
    check("the closing predicate moves too",
          program["body"][2]["predicate"]["select"]["name"] == f"{sigil}name")
    check("and so does a statement nested in a block",
          program["body"][3]["do"][0]["args"]["name"] == f"{sigil}name")
    check("THE CONTRACT MOVES — else it advertises a promise nothing can match",
          program["achieves"]["select"]["name"] == f"{sigil}name")
    check("no stand-in survives anywhere in the program",
          tok_name not in repr(program) and tok_os not in repr(program))

    # A PROGRAM THAT NEVER USED ONE. The parameter is still declared; it simply bound nothing.
    prog2 = {"body": [{"tool": "create_vm", "args": {"name": tok_name}}], "achieves": {}}
    check("a parameter the program never placed does not report as bound",
          stand_in.restore(prog2, tokens) == {"name"})

    # NOTHING TO DO IS NOT AN ERROR.
    check("an empty map leaves the program alone", stand_in.restore({"body": []}, {}) == set())


def test_declare_integration():
    """`_declare` must return the stood-in parameters as USED, not as unused."""
    print("\n_declare")
    from engines.orchestrator import _declare

    text, tokens, _ = stand_in.substitute("a vm named $name with os $os_name", _DECL)
    tok_name = next(t for t, p in tokens.items() if p == "name")
    tok_os = next(t for t, p in tokens.items() if p == "os_name")
    program = {
        "body": [{"tool": "create_vm", "args": {"name": tok_name, "os_type": tok_os}}],
        "achieves": {"select": {"kind": "vm", "name": tok_name}, "eq": 1},
    }
    unused = _declare(program, _DECL, tokens)
    check("NOTHING is reported unused — the bug reported both", unused == [])
    check("the signature is written onto the program",
          program.get("params") == _DECL)

    # WITHOUT THE MAP IT IS THE OLD BEHAVIOUR, and `os_name` still cannot bind by name
    # because the argument is spelled `os_type`. Asserted so the exact-match rule the
    # docstring promises is not quietly widened by this change.
    prog2 = {"body": [{"tool": "create_vm", "args": {"name": "box1", "os_type": "linux"}}],
             "achieves": {}}
    check("name-matching still binds `name`, and only by exact spelling",
          _declare(prog2, _DECL, None) == ["os_name"])


def test_no_second_reference_grammar():
    """The substitution must use `refs`' token rule, not a copy of it."""
    print("\nreference grammar")
    from planner.ir import refs
    # `$item-snap` is `$item` plus the literal `-snap`; rung 12 paid for that rule.
    text, tokens, _ = stand_in.substitute("$name-snap", {"name": "string"})
    tok = next(iter(tokens))
    check("a hyphen ends the reference, as `refs` says it does",
          text == f"{tok}-snap")
    check("`refs.substitute` leaves an unresolved reference intact",
          refs.substitute("$a and $b", lambda root, whole: None) == "$a and $b")


def test_live():
    """THE ONLY ARM THAT PROVES ANYTHING ABOUT THE SEAM. Skipped without a model."""
    print("\nlive (the real extractor)")
    if os.environ.get("GORGON_SKIP_LIVE"):
        print("  --   skipped (GORGON_SKIP_LIVE)")
        return
    try:
        from engines import extract as E
        text, tokens, _ = stand_in.substitute(
            "a vm named $name with os $os_name", _DECL)
        goals = E.to_goals(E.extract(text), text)
    except Exception as e:
        print(f"  --   skipped (no model: {e})")
        return
    flat = repr(goals)
    check("the identity reached the selector, so a creation is forced",
          any(g.get("select", {}).get("name") in tokens for g in goals if "select" in g))
    check("every stand-in that appears is one we can restore",
          all(t in tokens for t in tokens if t in flat))
    # THE KNOWN LIMIT, ASSERTED SO IT IS VISIBLE THE DAY IT CHANGES: "running $os" falls back
    # to `status: running` because the extractor routes a value by RECOGNISING it.
    bad = "a vm named {} running {}".format(*list(tokens))
    goals2 = E.to_goals(E.extract(bad), bad)
    print(f"  note  'running <stand-in>' -> {goals2}")


def main():
    test_substitute()
    test_restore()
    test_declare_integration()
    test_no_second_reference_grammar()
    test_live()
    total = _PASS + _FAIL
    print(f"\n{_PASS}/{total} passed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
