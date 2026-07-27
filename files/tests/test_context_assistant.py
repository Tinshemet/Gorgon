#!/usr/bin/env python3
"""
test_context_assistant.py — the deterministic pre/post assistant, held to its own promise.

WHY THIS EXISTS. The assistant's entire purpose is to stop the model inventing a field the
user never mentioned — its own docstring: "Did the AI invent a value for a field the user
never mentioned?" — and its guidance is injected into the prompt stamped **"GUIDANCE
(grounded, deterministic — trust it)"**.

It was inventing one itself. Slot keywords were matched by bare substring (`p in lower`),
so `mac` matched inside **machine**, the most natural English word for a VM:

    "spin up a machine and call it alpha"   -> os_type=mac
    "start up any machine that isn't running" -> os_type=mac

A false fact, asserted with more authority than the model could have claimed, on any goal
that says "machine". Nothing tested this module before today; it was found by running the
ladder's phrasings through it while investigating something else.

THE WIDER POINT, worth keeping with the tests: this module is a KEYWORD VOCABULARY, the
same kind the procedure language exists to replace, and it is phrasing-sensitive in the
way vocabularies always are. Measured over the ladder: nine phrasings of one goal produce
three to five DIFFERENT guidances, zero rungs identical; a typo silences it entirely. It
works in the micro regime it was built for (one prompt, one tool call) and does not
generalise to the macro one (a whole program under a schema). Do not port it upward
without measuring it there first.

Run:  PYTHONPATH=. python3 tests/test_context_assistant.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.chat.context_assistant import extract_slots, proactive_prep

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


def _slots(text):
    return {k: v for k, v in extract_slots(text).items() if v}


def test_a_keyword_is_a_whole_word():
    """`mac` inside `machine` is the case that mattered, but the class is general —
    `arch` inside "architecture", `win` inside a word, `mint` inside "minting"."""
    for text in ("spin up a machine and call it alpha",
                 "start up any machine that isn't already running",
                 "take a machine and label it prod",
                 "wire the machines together",
                 "check the architecture of the host"):
        check(f"no os_type invented from {text[:44]!r}",
              "os_type" not in _slots(text))


def test_a_real_mention_is_still_found():
    """The fix must not cost the extraction its job — a literal OS mention still counts."""
    for text, want in (("create a mac vm", "mac"),
                       ("create an ubuntu vm called dev", "ubuntu"),
                       ("make a windows box", "windows"),
                       ("spin up a debian server", "debian")):
        check(f"{want} is still extracted from {text[:40]!r}",
              _slots(text).get("os_type") == want)


def test_guidance_never_asserts_what_was_not_said():
    """The whole promise, end to end: what the assistant TELLS the model must be
    literally present in what the operator wrote. It says "trust it", so it has to be
    trustworthy — a wrong slot here outranks anything the model would have guessed."""
    for text in ("spin up a machine and call it alpha",
                 "start up any machine that isn't already running",
                 "put every machine on a network called core"):
        guidance = proactive_prep(text)
        check(f"guidance for {text[:40]!r} claims no os_type",
              "os_type" not in guidance)
    check("a real one still reaches the guidance",
          "os_type=ubuntu" in proactive_prep("create an ubuntu vm called dev"))


def test_it_is_a_vocabulary_and_that_shows():
    """Not a defect to fix — a PROPERTY to remember. This module is trigger words and slot
    regexes, so it is phrasing-sensitive by construction, and that is why it does not
    simply port to the program path. Recorded as a test so the property stays visible
    rather than being rediscovered."""
    base = "launch every vm that is currently stopped"
    typo = "alunch every vm that is currently stopped"
    check("a typo in the verb costs the tool hint",
          "launch_vm" in proactive_prep(base) and "launch_vm" not in proactive_prep(typo))
    check("and the base phrasing does produce one", bool(proactive_prep(base)))


def main():
    for fn in (test_a_keyword_is_a_whole_word,
               test_a_real_mention_is_still_found,
               test_guidance_never_asserts_what_was_not_said,
               test_it_is_a_vocabulary_and_that_shows):
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
