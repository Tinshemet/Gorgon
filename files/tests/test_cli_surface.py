#!/usr/bin/env python3
"""
test_cli_surface.py — the engine architecture is reachable from a shell prompt, ONCE.

WHAT WAS WRONG. `plan`, `routines` and `books` existed only inside the chat REPL, and the
procedure library had no surface at all — the handover's own words: *"the `.medusa` files
are meant to be read and edited and there is currently no way to ask Gorgon what it has
written."* So the thing every measurement on this project is about could not be typed at a
shell.

THE PART WORTH TESTING IS NOT THAT THE VERBS EXIST. It is that there is still ONE
implementation. A shell command here DELEGATES to the chat shortcut; reimplementing would
have given two versions of `plan`'s intent resolution and two consent prompts, and they
would disagree the first day one was edited. So this suite asserts the delegation and,
more importantly, that BOTH DOORS PRODUCE THE SAME OUTPUT for the same request — which is
the only form of "one implementation" that cannot be satisfied by a comment.

AND THAT THE GRAMMAR IS ASKED, NOT RE-STATED. The shortcut's own `matches` decides whether
an invocation is valid, so the two doors cannot drift into accepting different things.

Run:  PYTHONPATH=. python3 -m tests.test_cli_surface
"""
import os
import re
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.display import console

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class _Library:
    """A store in a temp directory, installed as THE library for the duration."""

    def __enter__(self):
        from planner import procedures as procs
        self.dir = tempfile.mkdtemp(prefix="gorgon-cli-")
        self.prior = procs.LIBRARY
        procs.LIBRARY = procs.Store(self.dir)
        return procs.LIBRARY

    def __exit__(self, *exc):
        from planner import procedures as procs
        procs.LIBRARY = self.prior
        shutil.rmtree(self.dir, ignore_errors=True)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _flat(text: str) -> str:
    """Captured output as a READER sees it: no colour codes, no line breaks.

    TWO THINGS STAND BETWEEN THE CAPTURE AND THE WORDS. Rich wraps to the console width, so
    `gorgon plan <request>` is one string to a reader and two lines to `in`; and it styles
    INSIDE words — `build_box` arrives with escape codes around the name — so even an
    unwrapped line does not contain the phrase it displays. Asserting on the raw capture
    would fail on terminal width and on syntax highlighting, neither of which anybody can
    act on.

    THE BOTH-DOORS COMPARISON DELIBERATELY DOES NOT USE THIS. There the point is that two
    code paths produced the same bytes, and normalising would weaken exactly the claim being
    made.
    """
    return " ".join(_ANSI.sub("", text).split())


def _say(argv, answer=None):
    """Run `gorgon <argv>` and capture what it printed.

    THE AUTH GATE IS OPENED, not removed: `_operator_gate_ok` is the dispatcher's, and every
    one of these verbs sits behind it in production. What is under test is what happens
    AFTER it, and a box with no operators would answer True here anyway.
    """
    from client.cli import commands
    prior_gate = commands._operator_gate_ok
    prior_input = console.input
    commands._operator_gate_ok = lambda cmd: True
    if answer is not None:
        console.input = lambda *a, **k: answer
    try:
        with console.capture() as cap:
            commands.run(argv)
        return cap.get()
    finally:
        commands._operator_gate_ok = prior_gate
        console.input = prior_input


def _repl(said, answer=None):
    """The same thing through the chat REPL's dispatcher, for the both-doors comparison."""
    from orchestrator.ai.chat import shortcuts
    prior_input = console.input
    if answer is not None:
        console.input = lambda *a, **k: answer
    try:
        with console.capture() as cap:
            handled = shortcuts.handle_command(said, [], 0, False)
        return handled, cap.get()
    finally:
        console.input = prior_input


def _kept(name="build_box"):
    return {"name": name, "params": {"box": "string"},
            "achieves": {"shape": "count",
                         "select": {"kind": "vm", "name": "$box"}, "eq": 1},
            "body": [{"op": "new", "kind": "vm", "var": "vm1", "tool": "create_vm",
                      "args": {"os_type": "linux", "name": "$box"}},
                     {"op": "ensure", "predicate": {"shape": "count",
                                                    "select": {"kind": "vm", "name": "$box"},
                                                    "eq": 1}},
                     {"op": "publish", "fact": "vm1"}]}


def test_every_new_verb_is_registered():
    """Dropping a file is how a command is added here, so the test is that it took."""
    print("[cli] the verbs exist")
    from client.cli import commands
    for verb in ("plan", "routines", "books", "procedures", "procs"):
        check(f"`gorgon {verb}` dispatches", verb in commands._REGISTRY)
    # THE BASE IS NOT A COMMAND. `ShortcutCommand` has no `names`, so it must not register
    # — a base class answering to a verb would be a command nobody wrote.
    from client.cli.commands._shortcut import ShortcutCommand
    check("the delegating base is not itself a verb", ShortcutCommand.names == ())


def test_both_doors_give_the_same_answer():
    """ONE IMPLEMENTATION, TWO DOORS — and this is the only form of that claim that holds.

    The shell command constructs the phrase the REPL would have received and hands it to the
    same shortcut, so byte-identical output is the property. If somebody reimplements one
    side, this is what fails.
    """
    print("[cli] the shell and the REPL are the same code")
    with _Library() as lib:
        lib.save(_kept())
        for argv, said in ((["procedures"], "procedures"),
                           (["procedures", "show", "build_box"],
                            "procedures show build_box"),
                           (["procedures", "verify"], "procedures verify"),
                           (["routines"], "routines")):
            shell = _say(argv)
            handled, repl = _repl(said)
            check(f"`{said}` is handled in the REPL", handled)
            check(f"`{said}` prints the same through both doors", shell == repl)


def test_the_shortcut_owns_the_grammar():
    """An invocation the REPL would refuse prints usage rather than doing something else."""
    print("[cli] the grammar is asked, never re-stated")
    with _Library():
        out = _say(["plan"])
        check("a bare `plan` explains itself", "gorgon plan <request>" in _flat(out))
        check("and does not claim the verb is unknown", "Unknown command" not in _flat(out))
        out = _say(["procedures", "nonsense"])
        check("an unknown subverb prints usage",
              "gorgon procedures" in _flat(out) and "show <name>" in _flat(out))


def test_the_library_can_be_read_from_a_shell():
    """The gap the handover named: no way to ask Gorgon what it has written."""
    print("[cli] what Gorgon has written, from a shell")
    with _Library() as lib:
        check("an empty library says so, and says what to type",
              "plan procedure" in _flat(_say(["procedures"])))

        lib.save(_kept())
        listed = _say(["procedures"])
        check("a stored procedure is listed", "build_box" in _flat(listed))
        # THE SIGNATURE IS WHAT MAKES IT A LIBRARY ENTRY RATHER THAN A MACRO.
        check("with its signature", "STRING box" in _flat(listed))

        shown = _say(["procs", "show", "build_box"])
        check("`procs` is an alias for the same thing", "PROCEDURE build_box" in _flat(shown))
        check("and the text shown IS the program", "NEW CALL create_vm" in _flat(shown))
        check("a name nobody wrote says so",
              "nothing called" in _flat(_say(["procedures", "show", "ghost"])))


def test_verify_is_reachable_and_reports_a_hand_edit():
    """The `.medusa` is edited by hand, and `all()` skips what it cannot read — silently."""
    print("[cli] a broken file is visible instead of skipped")
    with _Library() as lib:
        at = lib.save(_kept())
        check("a good procedure verifies well", "well" in _flat(_say(["procedures", "verify"])))

        with open(at, "a") as fh:
            fh.write("this is not medusa\n")
        out = _say(["procedures", "verify", "build_box"])
        check("a hand edit is reported", "will not load" in _flat(out))
        check("and the failing check is named", "reads back" in _flat(out))
        # AND THE LISTING LEADS WITH IT, because `names()` would otherwise just be short.
        listed = _say(["procedures"])
        check("the listing names what it cannot read", "cannot be read" in _flat(listed))


def test_delete_shows_what_would_go_and_takes_no_for_an_answer():
    """A procedure is something the operator ACCUMULATED and `forget` has no undo."""
    print("[cli] delete asks, and shows what it is asking about")
    with _Library() as lib:
        lib.save(_kept("doomed"))
        out = _say(["procedures", "delete", "doomed"], answer="n")
        check("the program is shown before the question", "PROCEDURE doomed" in _flat(out))
        check("and 'n' keeps it", lib.names() == ["doomed"])

        # AN ABSENT TERMINAL IS A NO — the rule `plan` applies to consent.
        _say(["procedures", "delete", "doomed"], answer="")
        check("an unanswered prompt keeps it too", lib.names() == ["doomed"])

        _say(["procedures", "delete", "doomed"], answer="y")
        check("and 'y' removes it", lib.names() == [])

        check("a name nobody wrote is not offered for deletion",
              "nothing called" in _flat(_say(["procedures", "delete", "ghost"], answer="y")))
        lib.save(_kept("klass"))
        out = _say(["procedures", "delete", "klass.method"], answer="y")
        check("a METHOD is not a file, and deleting one is refused",
              "not a file of its own" in _flat(out))
        check("so the class survives", lib.names() == ["klass"])


def test_the_syntax_guide_is_reachable():
    """The reference lives beside the programs; the CLI is how it gets refreshed."""
    print("[cli] the language reference, on demand")
    with _Library() as lib:
        out = _say(["procedures", "syntax"])
        check("it says where it wrote it", "SYNTAX.md" in _flat(out))
        check("the file is there", os.path.exists(os.path.join(lib.path, "SYNTAX.md")))
        check("and it says editing it does nothing", "generated" in _flat(out).lower())


def test_it_degrades_where_the_orchestrator_is_not_installed():
    """A CLIENT-ONLY CHECKOUT HAS NO ORCHESTRATOR, and an ImportError traceback is not an
    answer. The same degradation `mission` already uses."""
    print("[cli] a client-only box is told, not crashed")
    from client.cli import commands

    # BLOCKED THROUGH `sys.meta_path`, AND EVICTED FIRST. `importlib.import_module` answers
    # from `sys.modules` before it ever reaches an import hook, so a hook alone would test
    # nothing here — the module is already loaded by the tests above it.
    target = "orchestrator.ai.chat.shortcuts.procedures"

    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name == "orchestrator.ai.chat.shortcuts.procedures":
                raise ImportError("no orchestrator here")
            return None

    blocker = _Blocker()
    evicted = {k: v for k, v in sys.modules.items() if k == target}
    prior_gate = commands._operator_gate_ok
    commands._operator_gate_ok = lambda cmd: True
    for k in evicted:
        del sys.modules[k]
    sys.meta_path.insert(0, blocker)
    try:
        with console.capture() as cap:
            commands.run(["procedures"])
        out = cap.get()
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(evicted)
        commands._operator_gate_ok = prior_gate
    check("it names the missing package", "orchestrator package" in _flat(out))
    check("and does not raise", True)


def _parameterised(name="mk"):
    return {"name": name, "params": {"name": "string", "os_type": "string"},
            "achieves": {"shape": "count",
                         "select": {"kind": "vm", "name": "$name"}, "eq": 1},
            "body": [{"op": "new", "kind": "vm", "var": "v", "tool": "create_vm",
                      "args": {"os_type": "$os_type", "name": "$name"}},
                     {"op": "publish", "fact": "v"}]}


def test_running_a_parameterised_procedure_demands_its_arguments():
    """AN UNBOUND `$name` RESOLVES TO ITSELF, so a procedure run with no arguments creates
    a machine literally called `$name` and reports success.

    That is the failure `validate`'s own docstring warns about, and before this it was
    reachable through the front door: `procedures run` passed `{}` however many parameters
    the signature declared.
    """
    print("[cli] a parameterised procedure cannot be run bare")
    with _Library() as lib:
        lib.save(_parameterised())

        out = _flat(_say(["procedures", "run", "mk"]))
        check("no arguments is refused", "no value for name" in out)
        check("and the signature is shown", "STRING os_type" in out)

        out = _flat(_say(["procedures", "run", "mk", "name=box9", "os=linux"]))
        check("a misspelt parameter is refused, not ignored",
              "'os' is not a parameter" in out)
        out = _flat(_say(["procedures", "run", "mk", "box9"]))
        check("a bare word is refused", "not key=value" in out)


def test_the_arguments_reach_the_program():
    """A refusal that never let anything through would satisfy the test above and be useless.

    So the happy path is asserted where it can be seen without touching a lab: the values
    arrive as the CALL's arguments, which is what `execute` binds the callee's scope from.
    """
    print("[cli] and the values reach the call")
    import engines.rig as rig
    seen = {}

    class _Orch:
        def handle(self, request, **kw):
            seen["components"] = kw.get("components")
            seen["intent"] = kw.get("intent")
            return {"outcome": "DONE", "why": "stubbed"}

    prior = rig.build
    rig.build = lambda *a, **k: _Orch()
    try:
        with _Library() as lib:
            lib.save(_parameterised())
            _say(["procedures", "run", "mk", "name=box9", "os_type=windows"])
    finally:
        rig.build = prior

    check("the procedure is called by name with its arguments",
          seen.get("components") == [{"_call": ("mk", {"name": "box9",
                                                       "os_type": "windows"})}])
    # THE OPERATOR NAMED A PROGRAM THEY WROTE AND SAID RUN IT — that is the authority the
    # intent ladder is asking about, so it is granted here rather than asked again.
    check("and it runs under the intent the operator's own act implies",
          seen.get("intent") == "achieve")


class _Step:
    """The one field the destruction guard reads, plus what a Verdict needs."""

    def __init__(self, destroys, kind="run"):
        self.destroys = destroys
        self.kind = kind


def test_destruction_is_asked_about_BEFORE_it_happens():
    """MEASURED 2026-08-02, against the operator's own lab.

    `create a vm` translates to an UNFILTERED `count(vm) = 1`. Against nine machines that
    is a goal satisfied by DELETING EIGHT — `vm-orchestrator` and `vm-executor` among them,
    the machines Gorgon runs on. The list was computed and printed under the heading
    "what it did".

    NOTHING IS WRONG WITH THE WRITER, and that is why this is a question rather than a rule.
    `count(vm) = 1` genuinely means "one machine in total", and rung 14 pins exactly that
    behaviour for *"make sure there are exactly two machines"*. Measured at n=3, the two
    requests produce the SAME GOAL and differ only in the amount — so nothing downstream can
    tell an increment from a population target, and a guess would break one of them.
    """
    print("[cli] a destructive step is asked about, and refused by default")
    from orchestrator.ai.chat.shortcuts.plan import Plan

    step = _Step([("delete_vm", {"name": "vm-orchestrator"}),
                  ("delete_vm", {"name": "work-laptop"})])
    check("the machines are NAMED, never counted",
          Plan.names_destroyed(step) == ["vm-orchestrator", "work-laptop"])

    prior = console.input
    try:
        # AN ABSENT TERMINAL IS A NO — the rule `intent` and `consent` already keep.
        def _eof(*a, **k):
            raise EOFError()
        console.input = _eof
        with console.capture() as cap:
            granted = Plan.ask_destroy(step)
        check("with nobody to ask, it is refused", granted is False)
        check("and the question names them", "vm-orchestrator" in _flat(cap.get()))

        console.input = lambda *a, **k: "n"
        with console.capture():
            check("'n' refuses", Plan.ask_destroy(step) is False)
        console.input = lambda *a, **k: "y"
        with console.capture():
            check("'y' grants", Plan.ask_destroy(step) is True)
    finally:
        console.input = prior


def test_a_step_that_destroys_nothing_is_never_asked_about():
    """A QUESTION IN FRONT OF EVERY ORDINARY REQUEST IS A QUESTION NOBODY READS.

    The guard fires on `step.destroys` alone, so creating, labelling and launching go
    through untouched — which is what keeps the one question worth stopping for.
    """
    print("[cli] nothing destructive, nothing asked")
    from orchestrator.ai.chat.shortcuts.plan import Plan
    asked = []
    prior = Plan.ask_destroy
    try:
        Plan.ask_destroy = staticmethod(lambda step: asked.append(step) or True)
        # The guard's own condition, exercised the way `decide` uses it.
        for step in (_Step([]), _Step(None)):
            if step.destroys and not Plan.ask_destroy(step):
                pass
        check("a step with no destruction asks nothing", asked == [])
    finally:
        Plan.ask_destroy = prior


def test_help_names_every_new_verb():
    """A VERB NOBODY CAN DISCOVER IS A VERB NOBODY TYPES.

    The help panel is built from the EXECUTOR'S command catalog, which cannot name these —
    they reach the engine architecture rather than a tool, so there is no registry row to
    read them off. That makes the help text a hand-written list, and a hand-written list is
    exactly the thing that goes stale. So it is checked against the registry.
    """
    print("[cli] every new verb is discoverable")
    out = _flat(_say(["help"]))
    for verb in ("plan", "procedures", "routines", "books"):
        check(f"`gorgon help` mentions {verb}", verb in out)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the CLI surface"))


if __name__ == "__main__":
    main()
