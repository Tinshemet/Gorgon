#!/usr/bin/env python3
"""
test_chat_wiring.py — the chat modules must IMPORT, and must not have drifted.

WHY THIS EXISTS. On 2026-08-01 an edit left `cli.py` with a broken import and the full suite
stayed green, because nothing in `tests/` ever imported the chat REPL. The most user-facing
module in the system had no import coverage at all — a whole class of breakage that reaches
the operator before it reaches a test.

Importing is a low bar and that is the point: it is the bar nothing was clearing.

AND IT GUARDS THE SSOT (#26). The REPL and the HTTP chat are two prompt paths that have
drifted before — the mid-turn nudges were written twice with DIFFERENT WORDS, so one path
named example tools and the other did not. They were steering the model differently and
nothing said so, which means anything measured on one path would not have held on the other.
Both now read the same config; this asserts they still do.

Run:  PYTHONPATH=. python3 -m tests.test_chat_wiring
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


MODULES = [
    "orchestrator.ai.chat.cli",
    "orchestrator.ai.chat.http_chat",
    "orchestrator.ai.chat.ollama_client",
    "orchestrator.ai.chat.malformed",
    "orchestrator.ai.chat.shortcuts",
    "orchestrator.ai.engines",
    "orchestrator.ai.packages",
]


def test_every_chat_module_imports():
    """The bar nothing was clearing."""
    print("[imports] every chat and engine module loads")
    for name in MODULES:
        try:
            importlib.import_module(name)
            check(f"{name}", True)
        except Exception as e:
            check(f"{name} — {type(e).__name__}: {e}", False)


def test_the_two_prompt_paths_share_their_nudges():
    """#26. Mid-turn corrections are PROMPT CONTENT, and prompt content was measured
    expensive and load-bearing. Written twice, they had already diverged."""
    print("[ssot] one nudge text, two readers")
    cli = importlib.import_module("orchestrator.ai.chat.cli")
    htp = importlib.import_module("orchestrator.ai.chat.http_chat")
    check("both expose nudges", hasattr(cli, "_NUDGES") and hasattr(htp, "_NUDGES"))
    check("and the text is identical", cli._NUDGES == htp._NUDGES)
    check("read from config, not hardcoded",
          all(v.startswith("_INTERNAL_") for v in cli._NUDGES.values()))
    # NO STRAY COPIES. A literal nudge left inline is one that will drift again.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for path in ("orchestrator/ai/chat/cli.py", "orchestrator/ai/chat/http_chat.py"):
        body = open(os.path.join(here, path)).read()
        inline = body.count('"_INTERNAL_ Your last response')
        check(f"{os.path.basename(path)} has no inline copy", inline == 0)


def test_the_shortcut_registry_still_holds_plan():
    """The opt-in engine path is only reachable if its shortcut registered."""
    print("[wiring] the opt-in path is registered")
    sc = importlib.import_module("orchestrator.ai.chat.shortcuts")
    names = {type(s).__name__ for s in sc._REGISTRY}
    check("Plan is registered", "Plan" in names)
    plan = next(s for s in sc._REGISTRY if type(s).__name__ == "Plan")
    check("it matches `plan <request>`", plan.matches("plan create a vm named alpha"))
    check("and not a bare word", not plan.matches("plan"))
    check("and not an unrelated one", not plan.matches("planning the week"))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "chat wiring"))


if __name__ == "__main__":
    main()
