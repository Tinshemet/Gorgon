#!/usr/bin/env python3
"""
test_declared_params.py — the operator declares a procedure's signature; nothing infers it.

WHY THE FEATURE EXISTS. Asked for a procedure that "takes a name and os type from the user",
the system produced `create_vm(os_type: user input os type, name: $name)` — the model put
the operator's prose in the slot, because a PARAMETER is a fact about the procedure and the
extractor translates English into goals about the WORLD. There was nothing there to
translate. So the signature is written by the operator, in the same grammar the file uses,
and the model never sees it:

    procedure test(STRING name, STRING os_type): create a vm

WHY THIS SUITE IS MOSTLY ABOUT WHAT MUST *NOT* HAPPEN. The first version of the binding rule
substituted a declared parameter into every argument of the same name, and it was measured
doing something far worse than not working. `create a vm` translated to an UNFILTERED
`count(vm) = 1`; against a nine-machine lab the writer planned EIGHT deletions to get down
to one; and every one of them had its target rewritten to `$name`. Eight specific machines
the planner had chosen became *delete whatever the caller passes, eight times*.

THE RULE THAT REPLACED IT is the one `_parameterise` already keeps: a creator's arguments
DESCRIBE WHAT TO MAKE, and every other tool's arguments NAME SOMETHING THAT ALREADY EXISTS
and was chosen by reading the world. A parameter may only touch the first, and may follow
that literal elsewhere. The deletion case below is the regression guard and should be the
last test anybody deletes.

Run:  PYTHONPATH=. python3 -m tests.test_declared_params
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.orchestrator import _declare
from planner.ir import effects
from planner.ir.parse import ParseError, signature
from planner.procedures import declared_in

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _args(program, tool):
    return [st.get("args") for st in program["body"] if st.get("tool") == tool]


def test_the_signature_is_read_by_the_files_own_parser():
    """ONE GRAMMAR. A second reader would mean the operator types what the reference showed
    them and the request refuses it, the day a type is added to the manifest."""
    print("[declare] the request and the file share one signature reader")
    check("a signature parses", signature("(STRING name, STRING os_type)")
          == {"name": "string", "os_type": "string"})
    check("an empty one is empty", signature("()") == {})
    check("every declared type is available",
          signature("(INT n, DURATION d, SET s)")
          == {"n": "int", "d": "duration", "s": "set"})
    # A DECLARATION NOBODY CAN CHECK IS NOT A DECLARATION. `_params` forgives an unknown type
    # when READING A FILE, because refusing would lose an existing program; a signature being
    # typed for the first time is the opposite case, and `STIRNG` is a typo.
    for bad in ("(STIRNG name)", "(NOTATYPE x)"):
        try:
            signature(bad)
            check(f"{bad} is refused", False)
        except ParseError as e:
            check(f"{bad} is refused, and the real types are listed", "STRING" in str(e))


def test_the_declaration_comes_off_the_request():
    """The signature is stripped with the name and never reaches the translator."""
    print("[declare] the model never sees it")
    name, params, rest = declared_in(
        "procedure test(STRING name, STRING os_type): create a vm")
    check("the name is taken", name == "test")
    check("the parameters are taken", params == {"name": "string", "os_type": "string"})
    check("and what is left is the REQUEST alone", rest == "create a vm")

    check("a bare declaration still works",
          declared_in("procedure t: x") == ("t", {}, "x"))
    check("an ordinary request is untouched",
          declared_in("make a vm called box1") == (None, {}, "make a vm called box1"))
    # A MALFORMED SIGNATURE MUST NOT FALL THROUGH AND RUN. The operator asked for this work
    # to be KEPT; doing it instead is the one outcome they did not ask for.
    try:
        declared_in("procedure t(STIRNG x): delete everything")
        check("a malformed signature raises rather than running the work", False)
    except ParseError:
        check("a malformed signature raises rather than running the work", True)


def test_a_parameter_binds_a_creation_and_follows_what_it_made():
    """The intended case, end to end over one program."""
    print("[declare] a creation is parameterised, and its label follows it")
    prog = {"name": "t",
            "achieves": {"shape": "count",
                         "select": {"kind": "vm", "name": "box1"}, "eq": 1},
            "body": [{"op": "new", "kind": "vm", "var": "vm1", "tool": "create_vm",
                      "args": {"os_type": "linux", "name": "box1"}},
                     {"op": "call", "tool": "add_label",
                      "args": {"name": "box1", "label": "prod"}}]}
    unused = _declare(prog, {"name": "string", "os_type": "string"})
    check("the creation takes both parameters",
          _args(prog, "create_vm") == [{"os_type": "$os_type", "name": "$name"}])
    check("and the label follows the machine it labels",
          _args(prog, "add_label") == [{"name": "$name", "label": "prod"}])
    # THE CONTRACT MOVES TOO. `achieves` is what the writer matches a future goal against, so
    # a body taking `$name` under a contract still claiming `box1` would advertise a promise
    # narrower than it keeps and never be reached for again.
    check("the contract generalises with it",
          prog["achieves"]["select"]["name"] == "$name")
    check("the signature is on the program", prog["params"]
          == {"name": "string", "os_type": "string"})
    check("nothing is reported unused", unused == [])


def test_a_parameter_NEVER_rewrites_a_target_the_planner_CHOSE():
    """THE REGRESSION GUARD. Measured 2026-08-02; do not delete this test.

    `create a vm` translated to an unfiltered `count(vm) = 1`. Against a nine-machine lab
    the writer planned eight deletions, and the first binding rule rewrote every target to
    `$name` — turning eight specific machines into "delete whatever the caller passes".
    """
    print("[declare] a deletion the planner chose is NEVER parameterised")
    prog = {"name": "t",
            "achieves": {"shape": "count", "select": {"kind": "vm"}, "eq": 1},
            "body": [{"op": "call", "tool": "delete_vm", "args": {"name": f"web{i}"}}
                     for i in range(8)]}
    unused = _declare(prog, {"name": "string", "os_type": "string"})
    check("every deletion keeps the machine it named",
          _args(prog, "delete_vm") == [{"name": f"web{i}"} for i in range(8)])
    check("and both parameters are reported unused, not silently bound",
          unused == ["name", "os_type"])

    # THE MIXED CASE, which is the one a single-pass rule gets wrong most quietly: a program
    # that creates one machine and deletes another must parameterise only what it created.
    mixed = {"name": "t",
             "body": [{"op": "new", "kind": "vm", "var": "v", "tool": "create_vm",
                       "args": {"os_type": "linux", "name": "box1"}},
                      {"op": "call", "tool": "delete_vm", "args": {"name": "web9"}}]}
    _declare(mixed, {"name": "string"})
    check("the creation is parameterised",
          _args(mixed, "create_vm") == [{"os_type": "linux", "name": "$name"}])
    check("and the unrelated deletion is not",
          _args(mixed, "delete_vm") == [{"name": "web9"}])


def test_the_creator_set_is_derived_from_the_manifest():
    """A hand-kept list of creators would drift the first time a kind was added — silently,
    in the direction of treating a creation as an ordinary call."""
    print("[declare] which tools create is read, never listed")
    made = effects.creators()
    check("create_vm creates a vm", made.get("create_vm") == "vm")
    check("clone_vm does too, because the manifest says so", made.get("clone_vm") == "vm")
    check("delete_vm does NOT", "delete_vm" not in made)
    check("a setter does NOT", "add_label" not in made)
    # THE MIRROR IS ALREADY THERE, and the two must not overlap.
    check("nothing is both a creator and a deleter",
          not (set(made) & set(effects.deleters())))


def test_an_exact_name_or_nothing():
    """`STRING os` does not bind, and that is the decision rather than an oversight.

    An alias table mapping `os` -> `os_type` is a vocabulary keyed to nouns — a row per kind
    per synonym, maintained by whoever remembers — which is the thing the language exists to
    delete. Being strict costs the operator one word.
    """
    print("[declare] exact match, and it declines rather than guesses")
    prog = {"name": "t",
            "body": [{"op": "new", "kind": "vm", "var": "v", "tool": "create_vm",
                      "args": {"os_type": "linux", "name": "box1"}}]}
    unused = _declare(prog, {"os": "string"})
    check("a near-miss binds nothing", _args(prog, "create_vm")
          == [{"os_type": "linux", "name": "box1"}])
    check("and it is REPORTED rather than swallowed", unused == ["os"])
    check("the parameter is still on the signature, because the operator declared it",
          prog["params"] == {"os": "string"})


def test_declaring_nothing_changes_nothing():
    """The path every ordinary request takes must be untouched."""
    print("[declare] no declaration, no change")
    body = [{"op": "new", "kind": "vm", "var": "v", "tool": "create_vm",
             "args": {"os_type": "linux", "name": "box1"}}]
    prog = {"name": "t", "body": [dict(s) for s in body]}
    check("an empty declaration is a no-op", _declare(prog, {}) == [])
    check("and the body is untouched", prog["body"] == body)
    check("None is a no-op too", _declare(prog, None) == [])


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "declared parameters"))


if __name__ == "__main__":
    main()
