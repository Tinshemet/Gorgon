#!/usr/bin/env python3
"""
test_parse.py — the text IS the program: `parse(render(ir)) == ir`, for every op.

WHY A ROUND-TRIP AND NOT A LIST OF EXPECTED PARSES. A parser tested against hand-written
expectations tests the author's idea of the surface. Tested against the RENDERER it tests the
actual one, and the property it proves is the one the operator asked for: *"i dont want it
there because it makes the snippet have 2 SSOTs."* If every program the system writes reads
back identically, the `-- medusa:ir` trailer has nothing left to be the source of truth FOR.

THE COVERAGE ASSERTION IS THE POINT OF THE FILE. It is easy to round-trip the three ops you
thought of; the failure mode is an op that renders to something unreadable and is never tried.
So the corpus is checked against the renderer's own branch list, and a new op with no case
here FAILS THIS SUITE rather than silently going unread.

Run:  PYTHONPATH=. python3 -m tests.test_parse
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir.parse import ParseError, parse
from orchestrator.ai.planner.ir.render import render

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


# EVERY OP THE RENDERER CAN EMIT, and the awkward values that broke it. Each entry is an IR
# program; the test renders it, parses it back, and demands the same object.
CORPUS = {
    "new": {"body": [{"op": "new", "var": "box1", "kind": "vm",
                      "args": {"os_type": "linux", "name": "box1"}}]},
    "new + publish (the two-line form)": {
        "name": "build_vm_disc",
        "body": [{"op": "new", "var": "box1", "kind": "vm",
                  "args": {"os_type": "linux", "name": "box1"}},
                 {"op": "publish", "fact": "box1"}]},
    "new with an amount": {"body": [{"op": "new", "var": "v", "kind": "vm", "amount": 3,
                                     "args": {"os_type": "linux"}}]},
    "new with a shortfall": {"body": [{"op": "new", "var": "v", "kind": "vm",
                                       "amount": {"minus": [5, 2]},
                                       "args": {"os_type": "linux"}}]},
    "call": {"body": [{"op": "call", "tool": "launch_vm", "args": {"name": "web"}}]},
    "call with no args": {"body": [{"op": "call", "tool": "list_vms", "args": {}}]},
    "call bound to a name": {"body": [{"op": "call", "tool": "guest_ping",
                                       "args": {"name": "web"}, "graft": "alive"}]},
    "ensure": {"body": [{"op": "ensure", "predicate": {
        "shape": "count", "select": {"kind": "vm", "os_type": "linux"}, "eq": 3}}]},
    "achieve": {"body": [{"op": "achieve", "predicate": {
        "shape": "count", "select": {"kind": "vm"}, "gte": 2}}]},
    "a check with no comparator": {"body": [{"op": "ensure", "predicate": {
        "shape": "reach", "select": {"kind": "vm"}}}]},
    "publish": {"body": [{"op": "publish", "fact": "done"}]},
    "fetch": {"body": [{"op": "fetch", "var": "n", "count": {"kind": "vm"}}]},
    "fetch of a set": {"body": [{"op": "fetch", "var": "all", "select": {"kind": "vm"}}]},
    "foreach over a set": {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
        {"op": "call", "tool": "launch_vm", "args": {"name": "$item"}}]}]},
    "foreach over a literal list": {"body": [{"op": "foreach", "in": ["a", "b"], "do": [
        {"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}]}]},
    "if / else": {"body": [{"op": "if",
                            "cond": {"shape": "count", "select": {"kind": "vm"}, "gte": 1},
                            "then": [{"op": "publish", "fact": "ok"}],
                            "else": [{"op": "publish", "fact": "none"}]}]},
    "ifails": {"body": [{"op": "call", "tool": "launch_vm", "args": {"name": "web"},
                         "ifails": [{"op": "publish", "fact": "recovered"}]}]},
    "AND of two checks": {"body": [{"op": "ensure", "predicate": {"shape": "all", "of": [
        {"shape": "count", "select": {"kind": "vm"}, "eq": 1},
        {"shape": "count", "select": {"kind": "network"}, "eq": 1}]}}]},
    "NOT of one": {"body": [{"op": "ensure", "predicate": {"shape": "not", "of": {
        "shape": "count", "select": {"kind": "vm"}, "eq": 0}}}]},
    "EXCEPT": {"body": [{"op": "ensure", "predicate": {
        "shape": "count", "select": {"kind": "vm", "not": {"name": "db"}}, "eq": 2}}]},
    "INCLUDE": {"body": [{"op": "ensure", "predicate": {
        "shape": "count", "select": {"kind": "vm", "name": {"in": ["a", "b"]}}, "eq": 2}}]},
    "a procedure with parameters": {
        "name": "boot", "params": {"n": "int", "os": "string"},
        "body": [{"op": "publish", "fact": "done"}]},
    "imports": {"name": "crawl", "imports": ["camoufox"],
                "body": [{"op": "publish", "fact": "done"}]},
    # A SCHEDULE IS THE ONE THING THE BODY CANNOT SAY, so it is the one thing that needed a
    # new word. A contract does not: a creation already states what it makes.
    "a routine's span": {"name": "sweep", "every": "1h",
                         "body": [{"op": "publish", "fact": "done"}]},
    "a trigger's condition": {"name": "watch", "when": {
        "shape": "count", "select": {"kind": "vm"}, "gte": 3},
        "body": [{"op": "publish", "fact": "done"}]},
    "both, with parameters": {"name": "both", "every": "30s", "params": {"n": "int"},
                              "when": {"shape": "count", "select": {"kind": "vm"}, "eq": 1},
                              "body": [{"op": "publish", "fact": "x"}]},
}

# THE VALUES THAT BROKE IT, kept as their own group because each one is a bug that shipped.
AWKWARD = {
    "a query is a sentence, with punctuation": {"body": [{
        "op": "call", "tool": "camoufox_search",
        "args": {"query": "how fast is lighting?"}}]},
    "a URL is not a sentence": {"body": [{
        "op": "call", "tool": "t", "args": {"url": "https://x.com/a?b=1"}}]},
    "a value containing a comma": {"body": [{
        "op": "call", "tool": "t", "args": {"c": "a, b"}}]},
    "a string that looks like a number keeps its type": {"body": [{
        "op": "call", "tool": "t", "args": {"n": 3, "s": "3"}}]},
    "a string that looks like a boolean": {"body": [{
        "op": "call", "tool": "t", "args": {"t": True, "u": "true"}}]},
    "a date, a size and a duration": {"body": [{
        "op": "call", "tool": "t",
        "args": {"a": "2026-08-02", "b": "512MB", "c": "30s"}}]},
    # A SELECTOR VALUE THAT LOOKS LIKE SOMETHING ELSE. `render._select` quotes every term, so
    # coercing them all rewrote the ones that matter: `template = 'true'` became a boolean
    # where the manifest writes the string "true", and the selector stopped matching anything.
    # Found by hand-writing a procedure; the corpus had no such value.
    "a selector value that looks like a boolean": {"body": [{
        "op": "ensure", "predicate": {"shape": "count", "eq": 1,
                                      "select": {"kind": "vm", "template": "true"}}}]},
    "a selector value that looks like a number": {"body": [{
        "op": "ensure", "predicate": {"shape": "count", "eq": 1,
                                      "select": {"kind": "vm", "name": "3"}}}]},
}


def _round_trip(name, ir):
    text = render(ir)
    try:
        back = parse(text)
    except ParseError as exc:
        check(f"{name} — {exc}", False)
        return
    if back != ir:
        check(f"{name} — {text!r} -> {back!r}", False)
        return
    check(name, True)


def test_every_op_round_trips():
    print("[parse] every op the renderer can emit reads back as itself")
    for name, ir in CORPUS.items():
        _round_trip(name, ir)


def test_the_values_that_broke_it():
    """EACH OF THESE IS A BUG THAT SHIPPED, kept so it cannot ship twice."""
    print("[parse] the awkward values")
    for name, ir in AWKWARD.items():
        _round_trip(name, ir)


def test_no_op_renders_to_something_unreadable():
    """THE COVERAGE ASSERTION. An op with no case above fails here rather than going unread.

    Read from the RENDERER'S SOURCE rather than from a list written here, for the same reason
    the parser reads its keywords from `config.SURFACE`: a list of ops maintained by hand is
    the second vocabulary, one layer up.
    """
    print("[parse] and no op is missing from the corpus")
    import importlib
    import inspect

    # `import_module`, NOT `from ... import render` — the `ir` package re-exports `render` the
    # FUNCTION, which shadows `render` the MODULE. It is a five-minute confusion every time
    # and the reason `tests/shared.py` shadowing is already on the untested-seams list.
    _render = importlib.import_module("orchestrator.ai.planner.ir.render")
    src = inspect.getsource(_render._statement)
    emitted = set()
    for line in src.splitlines():
        line = line.strip()
        if line.startswith("if op == ") or line.startswith("if op in "):
            for piece in line.split('"')[1::2]:
                emitted.add(piece)
    covered = {st.get("op")
               for ir in list(CORPUS.values()) + list(AWKWARD.values())
               for st in ir["body"]}
    # Blocks nest, so an op that only ever appears INSIDE one still counts as covered.
    for ir in CORPUS.values():
        for st in ir["body"]:
            for key in ("then", "else", "do", "ifails"):
                covered |= {k.get("op") for k in (st.get(key) or [])}
    missing = sorted(emitted - covered)
    check(f"every rendered op has a round-trip case ({missing or 'all covered'})",
          not missing)


def test_a_file_still_carrying_the_old_ir_trailer_reads():
    """THE MIGRATION CASE. Every procedure on disk today has a `-- medusa:ir` line under it.

    A parser that choked on them would mean deleting the store to adopt this, which is a
    migration nobody should have to do for a comment.
    """
    print("[parse] the old trailer is a comment, and comments are ignored")
    ir = {"name": "build_vm_disc",
          "body": [{"op": "new", "var": "box1", "kind": "vm",
                    "args": {"os_type": "linux", "name": "box1"}},
                   {"op": "publish", "fact": "box1"}]}
    text = render(ir) + '\n\n-- medusa:ir {"body": [{"op": "publish"}], "name": "x"}\n'
    check("a stored file with its old trailer parses to the TEXT, not the trailer",
          parse(text) == ir)


def test_a_method_desugars_to_the_call_its_class_says_it_is():
    """`source.launch()` — the operator's own line, 2026-08-02.

    NOT COVERED BY THE ROUND TRIP, and that is why it has its own test: this is SUGAR, so
    `render` prints the desugared call and `parse(render(ir))` never sees the method form.
    The property that matters is not that it round-trips but that it produces EXACTLY the call
    the class already says it is — no second execution path, no method meaning something a
    tool call cannot.
    """
    print("[parse] a method is the call its class already declares")
    body = """PROCEDURE p() {
  STORE v = NEW CALL create_vm(name: box1, os_type: linux);
  v.launch();
  v.stop();
  v.label(prod);
  v.network(lab);
  v.delete();
  PUBLISH(v);
}"""
    calls = [(st["tool"], st["args"]) for st in parse(body)["body"] if st["op"] == "call"]
    check("a fixed-value setter takes no argument",
          ("launch_vm", {"name": "$v"}) in calls and ("stop_vm", {"name": "$v"}) in calls)
    check("a valued setter takes one, POSITIONALLY — the manifest names the slot",
          ("add_label", {"name": "$v", "label": "prod"}) in calls)
    # THE RECEIVER ARGUMENT IS THE MANIFEST'S, NOT A GUESS. `add_vm_to_network` calls it
    # `vm_name` where `add_label` calls it `name`, and assuming one spelling would be a second
    # authority for something already stated per setter.
    check("and the receiver argument is whatever THAT setter calls it",
          ("add_vm_to_network", {"vm_name": "$v", "net_name": "lab"}) in calls)
    check("a destructor is a method too", ("delete_vm", {"name": "$v"}) in calls)

    for bad, why in (("PROCEDURE p() {\n  nope.launch();\n}", "an unbound receiver"),
                     ("PROCEDURE p() {\n  STORE v = NEW CALL create_vm(name: b, os_type: linux);"
                      "\n  v.fly();\n}", "a method the kind does not have")):
        try:
            parse(bad)
            check(f"{why} is refused", False)
        except ParseError as exc:
            check(f"{why} is refused, and says what is available ({str(exc)[:40]}…)", True)


def test_a_broken_file_says_where():
    print("[parse] a failure names the line")
    for text, why in (("PROCEDURE p( {\n  PUBLISH(x);\n}", "a malformed signature"),
                      ("ENSURE COUNT(SELECT vm = 3;", "an unclosed check"),
                      ("WOBBLE x;", "a word that is not a statement")):
        try:
            parse(text)
            check(f"{why} is refused", False)
        except ParseError as exc:
            check(f"{why} is refused, with a line ({exc.line})", exc.line > 0)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "parse"))


if __name__ == "__main__":
    main()
