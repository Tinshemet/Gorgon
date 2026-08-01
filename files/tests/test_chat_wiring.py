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


def test_plan_has_a_dry_run_and_it_does_not_act():
    """`plan --dry` — because this path is pointed at a REAL lab.

    The first thing it computed against one was that "exactly two machines" needs seven
    deletions, naming vm-orchestrator and vm-executor among them. That is a fine thing to be
    told and a poor thing to discover.
    """
    print("[plan] a dry run stops at the first step and names what it would destroy")
    from orchestrator.ai.chat.shortcuts.plan import Plan
    from orchestrator.ai.engines import (Channel, Orchestrator, QemuEngine, Registry,
                                         insession)
    from orchestrator.ai.engines.channel import Answer

    p = Plan()
    check("the flag is recognised", p.matches("plan --dry make sure there are two"))
    check("and a plain request still is", p.matches("plan create a vm named alpha"))

    class Boom(Exception):
        pass

    class FakeLibrary:
        def vms(self):
            return {n: {"name": n, "status": "stopped"} for n in ("a", "b", "c", "d")}

        def by_network(self):
            return {}

        def known_names(self):
            return {"a", "b", "c", "d"}

    def must_not_act(tool, args):
        raise Boom(f"{tool} ran during a dry run")

    def translate(gap, world=None):
        return Answer([{"shape": "count", "select": {"kind": "vm"}, "eq": 2}], "stub", "")
    translate.name = "stub"

    offered = []

    def decide(step, session):
        offered.append(step)
        return insession.Verdict(insession.STOP, "dry run — nothing was done")

    reg = Registry()
    reg.mount(QemuEngine(FakeLibrary(), must_not_act))
    # THE REQUEST HAS TO BE ONE THE ENGINE CLAIMS. "exactly two" alone is UNCLAIMED — the
    # router works off the manifest's nouns, so a request naming no kind reaches nobody. That
    # is the routing layer behaving correctly, and a test that did not say so would look like
    # a dry-run bug the first time it failed.
    out = Orchestrator(reg, Channel([translate]),
                       decide=decide).handle("make sure there are exactly two machines")
    check("it closes as a refusal, not a failure", out["outcome"] == "REFUSED")
    check("nothing ran — the executor would have raised", not out.get("calls"))
    check("and the step named every deletion",
          len(offered) == 1 and len(offered[0].destroys) == 2)
    check("by name, because a count does not stop anybody",
          {list(a.values())[0] for _, a in offered[0].destroys} <= {"a", "b", "c", "d"})


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "chat wiring"))


if __name__ == "__main__":
    main()
