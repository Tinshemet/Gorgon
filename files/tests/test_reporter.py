#!/usr/bin/env python3
"""
test_reporter.py — the last seam, and the only one nothing downstream checks.

A bad extraction produces a program that fails. A bad program fails its own ENSURE. A bad
REPORT is the last thing anyone sees, and it is fluent by construction: the failure mode is a
sentence that reads exactly like a true one.

So the property under test is not "does it read well" — it is whether an INVENTED claim is
caught. Every assertion here is about grounding, and the model is stubbed, because what is
being tested is the CHECK rather than any particular model's honesty.

Run:  PYTHONPATH=. python3 -m tests.test_reporter
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import reporter

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


FINDINGS = [
    {"kind": "vm", "name": "alpha", "alive": True, "at": "01:14"},
    {"kind": "vm", "name": "beta", "alive": False, "at": "01:15"},
    {"scanned": 340, "seen": 12},
]


def _says(text, mentions=None):
    """A stubbed reporter that declares its claims, as the schema requires."""
    return lambda prompt, payload: {"answer": text,
                                    "mentions": [] if mentions is None else mentions}


def test_a_supported_answer_passes():
    print("[grounding] every word backed by a finding")
    got = reporter.report(FINDINGS, _says("alpha answered at 01:14; beta did not.",
                                          ["alpha", "01:14", "beta"]))
    check("it is grounded", got["grounded"] is True)
    check("nothing is unsupported", got["unsupported"] == [])


def test_an_invented_machine_is_caught():
    """The failure this file exists for: a name no finding carries."""
    print("[grounding] a name nobody observed")
    got = reporter.report(FINDINGS, _says("alpha answered, and gamma did not respond.",
                                          ["alpha", "gamma"]))
    check("it is NOT grounded", got["grounded"] is False)
    check("and the invented name is named", "gamma" in got["unsupported"])


def test_an_invented_NUMBER_is_caught():
    """"Spotted between 1am and 2am" is exactly the claim this polices.

    A timestamp is a number the ledger either carries or does not, so numbers are checked
    strictly — they are the sharpest kind of invention and the most persuasive.
    """
    print("[grounding] a number nobody measured")
    got = reporter.report(FINDINGS, _says("alpha answered at 04:52.", ["alpha", "04:52"]))
    check("the wrong time is caught", got["grounded"] is False)
    check("and it is the time that is flagged",
          any("04" in u for u in got["unsupported"]))
    ok = reporter.report(FINDINGS, _says("340 were scanned and 12 seen.", ["340", "12"]))
    check("but a number that IS in the findings passes", ok["grounded"] is True)


def test_no_findings_needs_no_model():
    """Asking a model to describe an empty ledger is asking it to invent something."""
    print("[honesty] nothing found is an answer")
    called = []

    def must_not(prompt, payload):
        called.append(1)
        return {"answer": "I found several machines.", "mentions": []}

    got = reporter.report([], must_not)
    check("no model was called", not called)
    check("and it says so plainly", got["answer"] == "Nothing was found.")
    check("grounded", got["grounded"] is True)


def test_an_ungrounded_answer_is_returned_flagged_not_swallowed():
    """Both facts go back: what it said, and what it could not support.

    Suppressing the answer leaves the operator with silence where there was one; returning it
    silently is the hallucination this file exists to prevent.
    """
    print("[honesty] flagged, not hidden")
    got = reporter.report(FINDINGS, _says("delta was unreachable.", ["delta"]))
    check("the answer still comes back", bool(got["answer"]))
    check("with grounded False", got["grounded"] is False)
    check("and the reason listed", bool(got["unsupported"]))


def test_a_failing_model_is_reported_not_raised():
    print("[honesty] a broken channel is an outcome")

    def boom(prompt, payload):
        raise TimeoutError("no answer")

    got = reporter.report(FINDINGS, boom)
    check("no exception escapes", isinstance(got, dict))
    check("the answer is None", got["answer"] is None)
    check("and the source names the failure", "TimeoutError" in got["source"])


def test_the_reporter_is_never_shown_the_request():
    """The property that separates describing evidence from answering a question.

    A model that can see what was ASKED writes a fluent answer to the question. One that can
    see only what was FOUND can only describe the evidence. `report()` takes findings and a
    channel — there is no parameter for the request, which is the enforcement.
    """
    print("[design] findings only, by signature")
    import inspect
    params = set(inspect.signature(reporter.report).parameters)
    check("no request parameter exists", not ({"request", "goal", "prompt", "components"}
                                              & params))
    seen = {}

    def capture(prompt, payload):
        seen["payload"] = payload
        return {"answer": "alpha answered.", "mentions": ["alpha"]}

    reporter.report(FINDINGS, capture)
    check("the model is handed the findings and nothing else",
          seen["payload"] == FINDINGS)


def test_ordinary_english_is_not_flagged_as_invention():
    """A check that flags normal words would be useless, and then ignored.

    This is the failure mode of every over-eager guard: it fires on correct output, people
    stop reading it, and it protects nothing.
    """
    print("[usability] the check must not cry wolf")
    got = reporter.report(FINDINGS,
                          _says("The findings show that alpha answered and beta did not.",
                                ["alpha", "beta"]))
    check("plain connective English passes", got["grounded"] is True)
    check("because only DECLARED claims are checked, not every word",
          got["unsupported"] == [])

    # AND PROSE WITH NO DECLARATION IS UNVERIFIABLE, NOT CLEAN. A reporter that returns a
    # bare sentence has made claims nobody can check, and calling that grounded would be the
    # check quietly passing everything it cannot see.
    bare = reporter.report(FINDINGS, lambda p, f: "alpha answered.")
    check("an undeclared answer is not called grounded", bare["grounded"] is False)
    check("and it says why", "unverifiable" in bare["source"])


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "reporter"))


if __name__ == "__main__":
    main()
