#!/usr/bin/env python3
"""
test_malformed.py — a failed tool call must not reach the operator as an answer.

Observed 2026-07-31 on a real probe: asked "which vms are running?", the model returned

    CallCheck("Which VMs are running?", options=["Adams", "Becky", "Charlie", "Diana"])

with four invented machine names, and the chat printed it under "Assistant:". It is not an
answer, it is not true, and nothing had run.

THE RISK IN FIXING IT is the opposite failure: a check that hides a real answer. So most of
this suite is about what must PASS — prose that mentions a tool, a sentence with parentheses,
an ordinary reply. A false positive costs the operator their answer, which is worse than one
odd line.

Run:  PYTHONPATH=. python3 -m tests.test_malformed
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.chat import malformed

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


def test_the_observed_case_is_caught():
    """The exact string a real probe produced, invented machine names and all."""
    print("[caught] the case this exists for")
    got = malformed.looks_like_tool_call(
        'CallCheck("Which VMs are running?", options=["Adams", "Becky", "Charlie"])')
    check("it is recognised", bool(got))
    check("and the reason names the call", "CallCheck" in got)


def test_json_envelopes_are_caught():
    print("[caught] a tool call printed as JSON")
    for body in ('{"tool_call": {"name": "list_vms", "arguments": {}}}',
                 '{"function": {"name": "create_vm"}}',
                 '[{"name": "stop_vm", "arguments": {"name": "web"}}]'):
        check(f"caught: {body[:34]}…", bool(malformed.looks_like_tool_call(body)))
    check("and a truncated one too",
          bool(malformed.looks_like_tool_call('{"name": "create_vm", "parameters"')))


def test_real_answers_pass_untouched():
    """THE HALF THAT MATTERS MORE. A check that eats answers is worse than the defect."""
    print("[passes] anything that is actually an answer")
    for body in ("You have 3 VMs running: alpha, beta and gamma.",
                 "I ran create_vm (twice) and it worked.",
                 "There are no machines on the dmz network.",
                 "alpha is stopped; launch_vm would start it.",
                 "Done.",
                 "{ this is not json and never was",
                 ""):
        check(f"passes: {body[:38]!r}", malformed.looks_like_tool_call(body) is None)


def test_a_json_answer_that_is_not_an_envelope_passes():
    """Structured output is not automatically a failed call — only an ENVELOPE is."""
    print("[passes] JSON that is data, not a call")
    check("a plain object passes",
          malformed.looks_like_tool_call('{"running": 3, "stopped": 1}') is None)


def test_the_explanation_says_what_happened_and_hides_the_envelope():
    """The operator's problem is that nothing ran. The raw attempt is a debugging detail."""
    print("[display] what the operator is told")
    text = 'CallCheck("x")'
    said = malformed.explain(malformed.looks_like_tool_call(text), text)
    check("it says nothing ran", "Nothing has run" in said)
    check("it suggests what to do", "rephras" in said.lower())
    check("and the raw attempt is NOT shown by default", "CallCheck(" not in said)
    loud = malformed.explain(malformed.looks_like_tool_call(text), text, verbose=True)
    check("but verbose shows it", "CallCheck(" in loud)


def test_both_prompt_paths_use_this_module():
    """A display rule written twice is one that will differ by the end of the month.

    The REPL and the HTTP chat have drifted before (#26 tracks exactly that), so this asserts
    they import the same authority rather than each carrying a copy.
    """
    print("[ssot] one authority, two callers")
    for path in ("orchestrator/ai/chat/cli.py", "orchestrator/ai/chat/http_chat.py"):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        body = open(os.path.join(here, path)).read()
        check(f"{os.path.basename(path)} imports it", "malformed as _malformed" in body)
        check(f"{os.path.basename(path)} calls it", "looks_like_tool_call" in body)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "malformed"))


if __name__ == "__main__":
    main()
