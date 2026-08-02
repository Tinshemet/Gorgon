"""test_prompt_kinds.py — six kinds of prompt and two thousand random ones, through the
ORCHESTRATOR, with no model.

WHAT IS GRADED IS THE OUTCOME CODE, NOT THE ANSWER. Refusing a broken prompt is correct
behaviour; a confident program for one is not, however plausible it looks. Each case declares
a SET of acceptable outcomes, because more than one can be right — "create a vm" with no name
may reasonably be refused OR answered with a generated name. What it may never do is crash,
or invent a machine and report that the operator asked for it.

WHY THE CHANNEL IS STUBBED HERE. `tests/bench/prompt_matrix.py` runs the same six kinds
through a REAL model and measures the front seam. This measures the other half: given a
plausible translation — including "the model gave nothing" — does the path above it behave?
Those are different questions and the model-shaped one cannot be asked deterministically.

A CRASH IS ALWAYS WRONG. Somebody typing nonsense is entitled to a refusal, not a traceback.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines import Channel, MedusaEngine, Orchestrator, Registry, insession
from engines.channel import Answer
from planner.ir import config
from tests.bench import fuzz
from tests.bench.sim_world import SimWorld

_PASS = _FAIL = 0

# EVERY OUTCOME THE ORCHESTRATOR MAY PRODUCE. A code outside this set is a code nobody
# decided on, which is how "it returned something" becomes "it worked".
OUTCOMES = {"DONE", "REFUSED", "UNMET", "UNTRANSLATED", "UNCLAIMED", "UNROUTED",
            "PROMOTION_DECLINED", "ABANDONED"}


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class LabEngine(MedusaEngine):
    name = "medusa"


def _rig(answer):
    """An orchestrator over a one-machine lab, with the channel's reply fixed."""
    world = SimWorld()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    reg = Registry()
    reg.mount(LabEngine(world))

    def translate(request, w=None):
        return answer
    translate.name = "stub"
    return Orchestrator(reg, Channel([translate])), world


NOTHING = Answer(None, "stub", "nothing usable in that")

# One plausible translation per kind — including the model declining, which IS a translation
# result and the correct one for three of these.
CASES = [
    ("VALID", "create a vm named beta",
     Answer([{"shape": "count", "select": {"kind": "vm", "name": "beta"}, "eq": 1}],
            "stub", ""),
     {"DONE"}),

    ("SPELLING", "creat a vm nammed beta",
     Answer([{"shape": "count", "select": {"kind": "vm", "name": "beta"}, "eq": 1}],
            "stub", ""),
     {"DONE"}),

    ("MISSING", "create a vm", NOTHING,
     {"UNTRANSLATED"}),

    ("AMBIGUOUS", "clean up the lab", NOTHING,
     {"UNTRANSLATED", "UNCLAIMED"}),

    # WELL-FORMED AND UNREACHABLE. No tool changes os_type after birth, so the writer must
    # refuse rather than improvise — this is the case that separates "cannot" from "will not".
    ("IMPOSSIBLE", "change the operating system of alpha to windows",
     Answer([{"every": {"kind": "vm", "name": "alpha"}, "must": {"os_type": "windows"}}],
            "stub", ""),
     {"UNMET", "PROMOTION_DECLINED", "ABANDONED"}),

    ("BROKEN", "asdkjh qwe ;;; 42", NOTHING,
     {"UNTRANSLATED", "UNCLAIMED"}),
]


def test_every_kind_of_prompt_lands_on_a_named_outcome():
    print("[kinds] six kinds, and the code is what is graded")
    for kind, text, answer, allowed in CASES:
        orch, _ = _rig(answer)
        try:
            out = orch.handle(text)
        except Exception as exc:
            check(f"{kind}: {type(exc).__name__} — a crash is always wrong", False)
            continue
        got = out["outcome"]
        check(f"{kind}: {got} (of {sorted(allowed)})", got in allowed)


def test_an_impossible_request_never_reports_success():
    """The one that matters most: a well-formed request nothing can satisfy."""
    print("[kinds] unreachable is refused, not improvised")
    kind, text, answer, _ = CASES[4]
    orch, world = _rig(answer)
    out = orch.handle(text)
    check("it does not claim DONE", out["outcome"] != "DONE")
    check("and the machine was not touched",
          world.vms["alpha"] == {"status": "stopped", "labels": set(), "nets": set()})
    check("nothing ran at all", not out.get("calls"))


def test_a_broken_prompt_costs_nothing():
    """A refusal that spent calls is a system that acted on nonsense and then declined."""
    print("[kinds] nonsense is free")
    for kind, text, answer, _ in CASES:
        if kind not in ("BROKEN", "AMBIGUOUS"):
            continue
        orch, world = _rig(answer)
        out = orch.handle(text)
        check(f"{kind}: no calls", not out.get("calls"))
        check(f"{kind}: the lab is untouched", set(world.vms) == {"alpha"})


def test_two_thousand_random_requests_never_crash_and_never_lie():
    """RANDOMIZED, and the two properties are different.

    NEVER CRASHES — every generated request lands on a named outcome, because a traceback is
    not an answer.
    NEVER LIES — every DONE is backed by goals that actually hold. That is the property the
    whole system exists to keep, and it is the one a generator can attack from angles nobody
    thought to write a case for.
    """
    print("[random] 2000 generated requests through the orchestrator")
    crashed, unnamed, lied = [], [], []
    for seed in range(2000):
        world, goals, text = fuzz.random_case(seed)
        reg = Registry()
        reg.mount(LabEngine(world))

        def translate(request, w=None, _g=goals):
            return Answer(_g, "fuzz", "")
        translate.name = "fuzz"
        orch = Orchestrator(reg, Channel([translate]))
        try:
            out = orch.handle(text or "make it so")
        except Exception as exc:
            crashed.append((seed, f"{type(exc).__name__}: {exc}"))
            continue
        if out["outcome"] not in OUTCOMES:
            unnamed.append((seed, out["outcome"]))
        if out["outcome"] == "DONE" and not fuzz.holds_all(goals, world)[0]:
            lied.append(seed)
    check(f"nothing crashed ({len(crashed)} did)", not crashed)
    for seed, why in crashed[:5]:
        print(f"       seed {seed}: {why}")
    check(f"every outcome is one somebody decided on ({len(unnamed)} were not)", not unnamed)
    check(f"every DONE is true ({len(lied)} were not)", not lied)
    for seed in lied[:5]:
        print(f"       seed {seed}")


def test_a_random_request_that_cannot_be_translated_is_not_a_failure():
    """The front seam is a stage with its own name, and confusing it with an engine failure
    is how a day goes into debugging the wrong half."""
    print("[random] an untranslatable request names the seam it died at")
    for seed in range(200):
        world, _goals, text = fuzz.random_case(seed)
        reg = Registry()
        reg.mount(LabEngine(world))

        def translate(request, w=None):
            return Answer(None, "fuzz", "the model returned nothing")
        translate.name = "fuzz"
        out = Orchestrator(reg, Channel([translate])).handle(text or "make it so")
        if out["outcome"] != "UNTRANSLATED":
            check(f"seed {seed}: got {out['outcome']}", False)
            return
    check("200 untranslatable requests all close UNTRANSLATED", True)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "prompt kinds"))


if __name__ == "__main__":
    main()
