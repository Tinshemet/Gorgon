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

from planner.ir.parse import ParseError, parse
from planner.ir.render import render

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
    _render = importlib.import_module("planner.ir.render")
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

    THE PROPERTY THAT MATTERS is that it produces EXACTLY the call the class already says it
    is — no second execution path, no method meaning something a tool call cannot. The round
    trip is asserted separately, below: since 2026-08-04 this is the form `render` PRINTS, so
    the two directions have to meet.
    """
    print("[parse] a method is the call its class already declares")
    body = """PROCEDURE p() {
  STORE v = NEW CALL create_vm(name: box1, os_type: linux);
  STORE lab = NEW CALL create_network(net_name: lab);
  $v.launch();
  $v.stop();
  $v.label(prod);
  $lab.add_vm($v);
  $v.delete();
  PUBLISH(v);
}"""
    calls = [(st["tool"], st["args"]) for st in parse(body)["body"] if st["op"] == "call"]
    check("a fixed-value setter takes no argument",
          ("launch_vm", {"name": "$v"}) in calls and ("stop_vm", {"name": "$v"}) in calls)
    check("a valued setter takes one, POSITIONALLY — the manifest names the slot",
          ("add_label", {"name": "$v", "label": "prod"}) in calls)
    # THE RECEIVER ARGUMENT IS THE MANIFEST'S, NOT A GUESS. `add_vm_to_network` calls the
    # machine `vm_name` and the network `net_name`, and assuming one spelling would be a
    # second authority for something already stated per setter.
    #
    # AND THE RECEIVER IS THE NETWORK — the operator's ruling, 2026-08-04. A relation has one
    # end that owns it, because ONE call has ONE rendering; the end that does not own it would
    # be a spelling you could type and never save.
    check("and a relation is a method of the thing being joined",
          ("add_vm_to_network", {"net_name": "$lab", "vm_name": "$v"}) in calls)
    check("a destructor is a method too", ("delete_vm", {"name": "$v"}) in calls)

    for bad, why in (("PROCEDURE p() {\n  $nope.launch();\n}", "an unbound receiver"),
                     ("PROCEDURE p() {\n  STORE v = NEW CALL create_vm(name: b, os_type: linux);"
                      "\n  $v.fly();\n}", "a method the kind does not have")):
        try:
            parse(bad)
            check(f"{why} is refused", False)
        except ParseError as exc:
            check(f"{why} is refused, and says what is available ({str(exc)[:40]}…)", True)


def test_the_method_form_is_the_only_way_in_and_it_survives_being_saved():
    """THE OPERATOR'S RULING, 2026-08-04: *"the only way you can access a vm's method is
    through calling it with the method, $vm.method()"*.

    AND IT COST NOTHING UNTIL IT ROUND-TRIPPED. Before this, `$box.launch()` parsed and then
    rendered back as `CALL launch_vm(name: $box)` — so a file that used the method form
    FAILED `verify_file`'s round trip, which is fatal. The whole class surface was write-only:
    usable in a program you throw away, never in one you keep. A restriction on a form nobody
    could save would have been a restriction on nothing.
    """
    print("[parse] the method form is what is written, and what is read back")
    src = """PROCEDURE p() {
  STORE lab = NEW CALL create_network(net_name: lab);
  STORE box = NEW CALL create_vm(os_type: linux, name: web);
  $lab.add_vm($box);
  $box.launch();
  $box.label(prod);
  ENSURE COUNT(SELECT vm WHERE name = 'web' AND status = 'running') = 1;
}"""
    ir = parse(src)
    check("what the renderer prints is the method form", render(ir).strip() == src.strip())
    check("and it reads back as the same program", parse(render(ir)) == ir)

    # THE LONG FORM IS REFUSED WHERE THE PROGRAM HOLDS THE RECEIVER, and NOWHERE ELSE. The
    # limit is the rule: a name this program does not hold has no receiver to go through.
    held = ("PROCEDURE p() {\n  STORE box = NEW CALL create_vm(name: web);\n"
            "  CALL launch_vm(name: $box);\n}")
    try:
        parse(held)
        check("the long form on a bound receiver is refused", False)
    except ParseError as exc:
        check(f"the long form on a bound receiver is refused, and says the form to use "
              f"($box.launch()) ({'$box.launch()' in str(exc)})",
              "$box.launch()" in str(exc))

    for ok_src, why in (
            ("PROCEDURE p() {\n  CALL launch_vm(name: web);\n}",
             "a literal name — nothing to be a receiver"),
            ("PROCEDURE p(STRING box) {\n  CALL launch_vm(name: $box);\n}",
             "a parameter — a name handed in, not a member held"),
            ("PROCEDURE p() {\n  STORE box = NEW CALL create_vm(name: web);\n"
             "  CALL launch_vm(name: $box, display: none);\n}",
             "an argument the method cannot carry")):
        try:
            parse(ok_src)
            check(f"{why} is still a plain call", True)
        except ParseError as exc:
            check(f"{why} is still a plain call ({exc})", False)


def test_the_loop_variable_is_a_receiver_inside_the_loop_and_nowhere_else():
    """`FOREACH $item IN SELECT vm` — inside the body, `$item` IS a vm.

    THE KIND IS READ, not assumed: off the select, or off the binding when the loop walks a
    set an earlier line made. A loop over a LITERAL LIST binds nothing, because a list of
    strings says what its members are called and not what they are.

    AND IT IS SCOPED, which is the one place this parser scopes anything. `$item` does not
    exist after the loop, and leaving it bound would let a later line print as a method on a
    variable the runtime has nothing for.
    """
    print("[parse] the loop variable is a member of what the loop ranges over")
    src = """PROCEDURE p() {
  STORE lab = NEW CALL create_network(net_name: lab);
  FOREACH $item IN SELECT vm WHERE status = 'running' {
    $item.stop();
    $lab.add_vm($item);
  }
  FOREACH $item IN [a, b] {
    CALL launch_vm(name: $item);
  }
  ENSURE COUNT(SELECT vm WHERE status = 'stopped') >= 1;
}"""
    ir = parse(src)
    check("a loop over a SELECT makes its member a receiver",
          render(ir).strip() == src.strip())
    check("and it reads back as the same program", parse(render(ir)) == ir)
    check("a loop over a literal list binds nothing, so the call stays a call",
          "CALL launch_vm(name: $item);" in render(ir))

    try:
        parse("PROCEDURE p() {\n  FOREACH $item IN SELECT vm { $item.stop(); }\n"
              "  $item.launch();\n}")
        check("the loop variable does not leak past the loop", False)
    except ParseError as exc:
        check(f"the loop variable does not leak past the loop ({str(exc)[:44]}…)",
              "not bound" in str(exc))


def test_a_name_knows_whether_it_holds_ONE_or_SEVERAL():
    """THE FIRST PIECE OF MEDUSA'S VALUE MODEL, and it arrived as a bug.

    The visitor writes `scope[var] = names[0] if n == 1 else names`, so an amount above one
    binds a LIST — and nothing recorded that. `STORE five = NEW AMOUNT(5) …` followed by
    `$five.launch()` parsed straight into `launch_vm(name: $five)`: five machines made, one
    name slot, a list poured into it. A `FETCH SELECT` binds a set for the same reason and
    recorded it just as little, so `FOREACH $item IN $reds` could not give `$item` a kind.
    """
    print("[parse] one, or several, and the difference is in the language")
    from planner.ir import classes
    src = """PROCEDURE p() {
  STORE reds = FETCH SELECT vm WHERE label = 'red';
  STORE blues = FETCH SELECT vm WHERE label = 'blue';
  FOREACH $item IN $reds {
    $item.stop();
  }
  ENSURE DISJOINT($reds, $blues);
}"""
    ir = parse(src)
    check("a set bound by FETCH gives its members their kind inside a loop",
          render(ir).strip() == src.strip() and parse(render(ir)) == ir)

    for bad, why in (
            ("PROCEDURE p() {\n  STORE five = NEW AMOUNT(5) CALL create_vm(os_type: linux);"
             "\n  $five.launch();\n}", "several created"),
            ("PROCEDURE p() {\n  STORE reds = FETCH SELECT vm WHERE label = 'red';"
             "\n  $reds.stop();\n}", "several fetched")):
        try:
            parse(bad)
            check(f"a set is refused as a receiver ({why})", False)
        except ParseError as exc:
            check(f"a set is refused as a receiver ({why}), and the loop is offered",
                  "SEVERAL" in str(exc) and "FOREACH" in str(exc))

    # A COUNT IS A NUMBER, WHICH IS NEITHER. Binding it as a set would make `$n.launch()`
    # complain about the wrong thing.
    try:
        parse("PROCEDURE p() {\n  STORE n = FETCH COUNT(SELECT vm);\n  $n.launch();\n}")
        check("a count is not a set", False)
    except ParseError as exc:
        check("a count binds a number, so it is not bound to a kind at all",
              "not bound to anything" in str(exc))
    check("and the marker never collides with a real kind",
          classes.in_set("vm") is None and classes.in_set(classes.set_of("vm")) == "vm")


def test_select_within_a_set_the_program_holds():
    """`SELECT vm WHERE label = 'red' IN $hosts` — the operator's instruction, 2026-08-04:
    *"it should be allowed, its a set of set, group theory allows it"*, and the answer to
    *"how do you select the reds just from hosts"*, which had none.

    IT IS A SPELLING AND NOTHING MORE, which is exactly why it is safe. A set holds the
    NAMES of its members, so "within this set" is membership of the KEY — a filter the
    selector already carried and the seams already evaluate. Nothing new runs.

    AND THE OTHER SPELLING IS REFUSED, because `INCLUDE name = $hosts` builds the identical
    selector: two ways in means the renderer prints one and the other is a form you can type
    and cannot save.
    """
    print("[parse] select within a set you already hold")
    src = """PROCEDURE p() {
  STORE hosts = FETCH SELECT vm WHERE label = 'host';
  STORE reds = FETCH SELECT vm WHERE label = 'red' IN $hosts;
  ENSURE COUNT(SELECT vm WHERE label = 'red' IN $hosts) = 2;
}"""
    ir = parse(src)
    check("it parses to membership of the key",
          ir["body"][1]["select"] == {"kind": "vm", "label": "red",
                                      "name": {"in": "$hosts"}})
    check("and round trips", render(ir).strip() == src.strip())
    check("and reads back as the same program", parse(render(ir)) == ir)
    try:
        parse("ENSURE COUNT(SELECT vm INCLUDE name = $hosts) = 1;")
        check("the second spelling is refused", False)
    except ParseError as exc:
        check("the second spelling is refused, and names the first",
              "IN $hosts" in str(exc))
    # MEMBERSHIP OF ANOTHER ATTRIBUTE IS STILL AN ORDINARY INCLUDE. `IN` is about the set of
    # MEMBERS; a list of labels is a different question and keeps its own word.
    other = parse("ENSURE COUNT(SELECT vm INCLUDE label = [red, blue]) = 2;")
    check("membership of a non-key attribute is untouched",
          render(other).strip() == "ENSURE COUNT(SELECT vm INCLUDE label = [red, blue]) = 2;")


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


def test_a_dotted_reference_is_one_operand():
    """RESULT-BRANCHING WAS IN THE LANGUAGE AND UNUSABLE, and this is the check that says so.

    `IS($answer.alive) = true` is what the RENDERER emits for a program that branches on a
    call's result. The parser read a single token for the operand, stopped at the `.`, and
    raised — so such a program rendered correctly, VALIDATED, and then failed `verify_file`'s
    round-trip on the way back in. Never loadable, so never used.

    THE SECOND TIME THIS EXACT BUG HAS BEEN FOUND. `PROCEDURE Class.method` had it, and every
    class file on disk failed to load. `refs` already defines the shape — `$answer.alive` is
    ONE reference whose root is `answer` — so a single-token read was the parser disagreeing
    with the module that owns what a reference means.
    """
    print("[parse] a dotted reference survives the round trip")
    from planner.ir import render as _render, validate as _validate
    prog = {"name": "t", "params": {}, "body": [
        {"op": "call", "tool": "guest_ping", "args": {"name": "alpha"}, "graft": "answer"},
        {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": True},
         "then": [{"op": "call", "tool": "stop_vm", "args": {"name": "alpha"}}]},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "status": "running"},
                                       "eq": 0}},
        {"op": "publish", "fact": "done"}]}
    src = _render(prog)
    check("it validates", _validate(prog)[0])
    try:
        back = parse(src)
    except Exception as e:
        check(f"it re-parses (got {type(e).__name__}: {e})", False)
        return
    check("it re-parses", True)
    check("and RENDERS BACK TO ITSELF — the check `verify_file` runs", _render(back) == src)
    got = back["body"][1]["cond"]
    check("the whole dotted path survives, not just its root", got.get("of") == "$answer.alive")

# THE ENTRY POINT BELONGS AT THE BOTTOM, and this is not style: `main()` ends in `sys.exit`,
# so every test defined BELOW this guard was never even defined when the suite was run
# directly — silently absent from the count, and from `run_all.py`. Found 2026-08-04 by a
# sweep after the same trap was hit in `test_extract.py`; three suites carried it and eleven
# tests had never run. `_suite.py` discovers by definition order, so placement is the only
# thing keeping a test alive.
def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "parse"))


if __name__ == "__main__":
    main()
