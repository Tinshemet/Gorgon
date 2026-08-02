#!/usr/bin/env python3
"""
test_chat_shortcuts.py — `plan` must mean the same thing in the chat as in a shell.

WHY THIS EXISTS, MEASURED 2026-08-02. `plan procedure test: a windows vm` was typed into the
chat three times. Every time the model read it as prose and answered that it had made a
machine — once truthfully, once falsely, and never once writing the procedure. The shortcut
existed, was correct, and was reachable from two doors the operator was not standing at.
[[gorgon-built-and-never-called]], in the shape where the code is fine and the door is missing.

WHAT IS ASSERTED HERE, and the second half is the one that matters: not just that the
classifier sorts strings correctly, but that a real /chat turn carrying `plan …` NEVER REACHES
THE MODEL. A rule that sorts correctly beside a path that ignores it is the original bug again.

AND THE BOUNDARY IS A TEST, NOT A COMMENT. The chat may run what cannot act — authoring and
dry runs — and must refuse what can. If someone later widens that, this fails.

Run:  PYTHONPATH=. python3 -m tests.test_chat_shortcuts
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.chat.shortcuts import headless

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


class _Stub:
    """Stands in for the shortcut registry: records the phrase, prints, returns handled."""

    def __init__(self, handled=True, prints="kept as test"):
        self.seen, self.handled, self.prints = [], handled, prints
        self.input_raised = None

    def __call__(self, ui, messages, drift, verbose):
        from shared.display import console
        self.seen.append(ui)
        try:
            console.input("are you there? ")
            self.input_raised = False
        except EOFError:
            self.input_raised = True
        console.print(self.prints)
        return self.handled


def _with_stub(stub, fn):
    from orchestrator.ai.chat import shortcuts as _pkg
    real = _pkg.handle_command
    _pkg.handle_command = stub
    try:
        return fn()
    finally:
        _pkg.handle_command = real


def test_boundary():
    print("\nwhat the chat may run — it may not act")

    acts = headless.acts_on_the_world
    check("a plain request acts",            acts("create a windows vm") is True)
    check("a declaration does not act",      acts("procedure test: a windows vm") is False)
    check("a signed declaration does not act",
          acts("procedure test(STRING name): a vm called $name") is False)
    check("--dry does not act",              acts("--dry create a windows vm") is False)
    check("-n does not act",                 acts("-n create a windows vm") is False)
    # A typo in the signature is refused BY `plan`, which prints the complaint and runs
    # nothing — so it must reach it rather than be turned away as an acting request.
    check("a malformed declaration does not act",
          acts("procedure t(STIRNG x): a vm") is False)
    # The word must be the declaration, not a mention of one.
    check("prose mentioning a procedure acts",
          acts("make a procedure for building vms") is True)


def test_routing():
    print("\nwhat headless.run claims, and what it hands back")

    check("ordinary prose is not ours", headless.run("make me a windows vm") is None)
    check("a sentence starting with the word is not ours",
          headless.run("planning a lab tomorrow") is None)

    refusal = headless.run("plan create a windows vm")
    check("an acting plan is refused", refusal is not None and "would ACT" in refusal)
    check("the refusal names the working command", "gorgon plan create a windows vm" in refusal)
    check("the refusal offers what DOES work here", "plan procedure NAME" in refusal)

    stub = _Stub()
    out = _with_stub(stub, lambda: headless.run("plan procedure test: a windows vm"))
    check("an authoring request runs the shortcut",
          stub.seen == ["plan procedure test: a windows vm"])
    check("its output comes back", "kept as test" in (out or ""))
    check("the shortcut found no terminal", stub.input_raised is True)

    stub = _Stub()
    out = _with_stub(stub, lambda: headless.run("plan --dry create a vm"))
    check("a dry run runs the shortcut", stub.seen == ["plan --dry create a vm"])

    stub = _Stub()
    out = _with_stub(stub, lambda: headless.run("procedures"))
    check("the library is readable from the chat", stub.seen == ["procedures"])

    # A phrase this module offered to run that the registry then declines must SAY so.
    stub = _Stub(handled=False)
    out = _with_stub(stub, lambda: headless.run("procedures nonsense verb"))
    check("an unhandled phrase does not read as success", "not a command" in (out or ""))


def test_console_restored():
    print("\nthe console is left as it was found")
    from shared.display import console
    import getpass

    before_input, before_getpass = console.input, getpass.getpass
    _with_stub(_Stub(), lambda: headless.run("plan procedure test: a vm"))
    check("console.input restored", console.input is before_input)
    check("getpass restored", getpass.getpass is before_getpass)

    # Even when the shortcut blows up mid-run.
    def _boom(*_a, **_kw):
        raise RuntimeError("shortcut exploded")
    try:
        _with_stub(_boom, lambda: headless.run("plan procedure test: a vm"))
    except RuntimeError:
        pass
    check("console.input restored after a crash", console.input is before_input)
    check("getpass restored after a crash", getpass.getpass is before_getpass)


def test_wired():
    print("\nthe real /chat turn — `plan` never reaches the model")
    from orchestrator.http import chat_endpoint, session_store
    from orchestrator.ai.chat import cli as _cli

    asked_model = []
    real_pm = _cli.process_message
    _cli.process_message = lambda **kw: (
        asked_model.append(kw.get("user_input")) or
        {"text": "", "messages": [], "tool_results": [], "needs_input": None,
         "pending_tool": None})

    def _turn(message, stub):
        sid = "test-shortcut-session"
        session_store.SESSIONS[sid] = {"messages": [], "pending_tool": None,
                                       "critical_step2": False, "last_active": 9e9}
        req = types.SimpleNamespace(message=message, session_id=sid,
                                    auto_confirm=False, verbose=False)
        try:
            return _with_stub(stub, lambda: chat_endpoint.handle_chat(req, None))
        finally:
            session_store.SESSIONS.pop(sid, None)

    try:
        stub = _Stub()
        out = _turn("plan procedure test(STRING name): a windows vm called $name", stub)
        check("the shortcut ran", len(stub.seen) == 1)
        check("the model was never asked", asked_model == [])
        check("the reply is the shortcut's output", "kept as test" in (out.get("text") or ""))
        check("no tool results are claimed", out.get("tool_results") == [])

        out = _turn("plan create a windows vm", _Stub())
        check("an acting plan is refused before the model", asked_model == [])
        check("and it says where to run it", "gorgon plan" in (out.get("text") or ""))

        out = _turn("make me a windows vm", _Stub())
        check("ordinary prose still reaches the model",
              asked_model == ["make me a windows vm"])
    finally:
        _cli.process_message = real_pm


def main():
    test_boundary()
    test_routing()
    test_console_restored()
    test_wired()
    total = _PASS + _FAIL
    print(f"\n{_PASS}/{total} passed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
