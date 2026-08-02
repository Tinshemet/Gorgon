#!/usr/bin/env python3
"""
test_confirm_answer.py — a confirmation must READ the answer. "cancel" must not run it.

WHY THIS EXISTS, MEASURED 2026-08-02. The chat asked *"create VM: test — Yes / Cancel"*, the
operator typed **cancel**, and the VM was created. The HTTP path never looked at the reply:
the client turned "a confirm is pending" into `auto_confirm=True` and the server executed the
pending tool on that flag alone. Every answer was a yes.

TWO KINDS OF TEST HERE, AND BOTH ARE NEEDED. The first half is the rule in isolation — cheap,
exhaustive, no server. The second half asserts THE RULE IS ASKED, by driving the real /chat
handler with a stubbed executor and checking whether the tool ran. A rule that is correct and
uncalled is [[gorgon-built-and-never-called]], the defect class that has cost this project
more than any other, and the original bug was exactly that shape one layer down: `safety.py`
had the rule right the whole time, on the door nobody was typing at.

Run:  PYTHONPATH=. python3 -m tests.test_confirm_answer
"""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.chat.gates import answer as _answer

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


def _yn(said):
    return _answer.reads_as_grant({"type": "confirm_yn", "proposed": "test"}, said)


def _name(said):
    return _answer.reads_as_grant({"type": "confirm_name", "proposed": "test"}, said)


def _critical(said):
    return _answer.reads_as_grant({"type": "confirm_critical", "proposed": "test"}, said)


def test_rule():
    print("\nthe rule — what an answer means")

    # THE BUG ITSELF.
    check("yes/no: 'cancel' does not grant", _yn("cancel") is False)
    check("yes/no: 'no' does not grant",     _yn("no") is False)
    check("yes/no: 'abort' does not grant",  _yn("abort") is False)

    # THE DEFAULT IS REFUSAL — an unrecognised answer is not a grant.
    check("yes/no: gibberish does not grant", _yn("asdf") is False)
    check("yes/no: empty does not grant",     _yn("") is False)
    check("yes/no: whitespace does not grant", _yn("   ") is False)
    # The old prompt printed "Type exactly: test" beside a Yes/Cancel menu. Typing the name
    # at a yes/no question answers a different question, and is not a yes.
    check("yes/no: the proposed name is not a yes", _yn("test") is False)

    check("yes/no: 'yes' grants",   _yn("yes") is True)
    check("yes/no: 'y' grants",     _yn("y") is True)
    check("yes/no: 'YES' grants",   _yn("YES") is True)
    check("yes/no: ' yes ' grants", _yn(" yes ") is True)

    # NAME CONFIRM — the exact name, which is the proof of intent.
    check("name: the exact name grants",  _name("test") is True)
    check("name: 'yes' does not grant",   _name("yes") is False)
    check("name: 'cancel' does not grant", _name("cancel") is False)
    check("name: a near miss does not grant", _name("tes") is False)
    check("name: wrong case does not grant",  _name("TEST") is False)

    # CRITICAL — the two-step name check downstream is the gate; this only lets a refusal
    # out of it, which is what the step-2 prompt has always promised and never honoured.
    check("critical: 'cancel' does not grant", _critical("cancel") is False)
    check("critical: a name passes through",   _critical("test") is True)

    # PREFLIGHT is a free-form choice, not a yes/no — but a refusal is still a refusal.
    pf = {"type": "preflight", "proposed": None}
    check("preflight: 'cancel' does not grant",
          _answer.reads_as_grant(pf, "cancel") is False)
    check("preflight: a choice passes through",
          _answer.reads_as_grant(pf, "use it anyway") is True)

    # A SESSION FROM BEFORE THIS EXISTED still refuses on the word that matters.
    check("no confirm block: 'cancel' does not grant",
          _answer.reads_as_grant(None, "cancel") is False)
    check("no confirm block: anything else passes through",
          _answer.reads_as_grant(None, "yes") is True)


def _drive(message, confirm, critical=False):
    """One /chat turn answering a pending confirm. Returns (executed_calls, reply)."""
    from orchestrator.http import chat_endpoint, session_store
    import orchestrator.executor_client as _exec

    calls = []
    real = _exec.execute_tool
    _exec.execute_tool = lambda tool, args, verbose=False: (
        calls.append((tool, args)) or {"success": True, "message": "stub"})
    try:
        sid = "test-confirm-session"
        session_store.SESSIONS[sid] = {
            "messages": [{"role": "user", "content": "create a windows vm named test"}],
            "pending_tool": {"tool_name": "create_vm", "args": {"name": "test"},
                             "critical": critical, "confirm": confirm},
            "critical_step2": False, "last_active": 9e9,
        }
        req = types.SimpleNamespace(message=message, session_id=sid,
                                    auto_confirm=True, verbose=False)
        out = chat_endpoint.handle_chat(req, None)
        return calls, out
    finally:
        _exec.execute_tool = real
        session_store.SESSIONS.pop("test-confirm-session", None)


def test_wired():
    print("\nthe rule is ASKED — the real /chat turn, stubbed executor")
    yn = {"type": "confirm_yn", "proposed": "test"}

    calls, out = _drive("cancel", yn)
    check("'cancel' runs no tool", calls == [])
    check("'cancel' says nothing was done", "othing was done" in (out.get("text") or ""))
    check("'cancel' clears the pending tool", out.get("needs_input") is None)
    check("'cancel' reports no tool results", out.get("tool_results") == [])

    calls, out = _drive("no", yn)
    check("'no' runs no tool", calls == [])

    calls, out = _drive("asdf", yn)
    check("an unrecognised answer runs no tool", calls == [])

    calls, out = _drive("yes", yn)
    check("'yes' still runs the tool", [t for t, _ in calls] == ["create_vm"])
    check("'yes' runs it with the confirmed args",
          calls and calls[0][1].get("name") == "test")

    # The name-confirm tier: only the name runs it.
    nm = {"type": "confirm_name", "proposed": "test"}
    calls, _ = _drive("yes", nm)
    check("name tier: 'yes' does not run it", calls == [])
    calls, _ = _drive("test", nm)
    check("name tier: the name runs it", [t for t, _ in calls] == ["create_vm"])

    # Critical: "cancel" gets out of the two-step, as its own prompt promises.
    crit = {"type": "confirm_critical", "proposed": "test"}
    calls, out = _drive("cancel", crit, critical=True)
    check("critical: 'cancel' runs no tool", calls == [])
    check("critical: 'cancel' does not re-ask", out.get("needs_input") is None)
    calls, out = _drive("test", crit, critical=True)
    check("critical: a name reaches the step-2 check", calls == [] and
          (out.get("needs_input") or {}).get("type") == "confirm_critical")


def main():
    test_rule()
    test_wired()
    total = _PASS + _FAIL
    print(f"\n{_PASS}/{total} passed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
