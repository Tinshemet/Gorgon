"""test_fuzz_insession.py — the in-session's invariants, over generated cases.

THIRTEEN RUNGS SAID THE GRAIN WAS SAFE AND THEY WERE WRONG. Every rung is a satisfiable
request whose goals do not fight each other, so serving them one node at a time gave the same
answer and the property looked proven. Two thousand generated cases found three defects the
rungs cannot express:

    the tree grain reported OK on a CONTRADICTORY request, having deleted two machines to
    get there — because each goal was planned and closed alone and nothing re-read the others

    a decomposed parent lost its closing witness, so the run stopped vouching for itself
    while still doing the work

    an empty manifest was read as "a domain with no kinds" rather than "the one in force",
    so `what would this destroy?` answered "nothing" for every Gorgon engine

THE INVARIANT IS NOT "THE SAME CALLS". It is that the grain may change how much a doomed
request costs before it is refused, and NOTHING ELSE: no grain may claim success the others
do not, and no grain may claim success at all while its goals are false.
"""
import sys

from orchestrator.ai.engines import MedusaEngine, Session
from orchestrator.ai.engines import insession as ins
from tests.bench import fuzz

_PASS = _FAIL = 0
CASES = 600


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _serve(seed, regime, greedy):
    world, goals, _ = fuzz.random_case(seed)
    eng = MedusaEngine(world)
    sess = Session("", eng, intent="ensure")
    sess.regime = regime
    out = ins.drive(eng, goals, sess, lambda st, s: ins.Verdict(
        ins.DECOMPOSE if (greedy and st.divisible) else ins.RUN))
    tag = "PROMOTE" if out.get("promote") else ("OK" if out.get("ok") else "OTHER")
    return tag, out, world, goals


GRAINS = (("translation", False), ("tree", False), ("translation", True))


def test_no_grain_ever_claims_a_success_its_goals_do_not_support():
    """The one that must never regress: a run that says OK and is false."""
    print(f"[fuzz] {CASES} cases x 3 grains — no false success")
    lies = []
    for seed in range(CASES):
        for regime, greedy in GRAINS:
            tag, _, world, goals = _serve(seed, regime, greedy)
            if tag == "OK" and not fuzz.holds_all(goals, world)[0]:
                lies.append((seed, regime, greedy))
    check(f"no grain claimed success while its goals were false ({len(lies)} did)", not lies)
    for seed, regime, greedy in lies[:5]:
        print(f"       seed {seed} · {regime} · opened={greedy}")


def test_the_grains_agree_on_the_outcome():
    """A request answered OK by one grain and refused by another is two systems."""
    print(f"[fuzz] {CASES} cases — one verdict, whatever the grain")
    split = []
    for seed in range(CASES):
        tags = {_serve(seed, r, g)[0] for r, g in GRAINS}
        if len(tags) > 1:
            split.append((seed, sorted(tags)))
    check(f"every case gets one outcome at every grain ({len(split)} split)", not split)
    for seed, tags in split[:5]:
        print(f"       seed {seed}: {tags}")


def test_the_cost_of_a_doomed_request_is_what_the_grain_changes():
    """The DIFFERENCE that is allowed, stated as a property rather than left implicit.

    A finer grain acts as it goes, so an impossible request costs it real work before it can
    know. That is the intent ladder's whole reason for pointing down, and it is why
    `Step.destroys` exists — the verdict is the only place to catch it.
    """
    print(f"[fuzz] {CASES} cases — where the grains are allowed to differ")
    acted_anyway, whole_touched = 0, 0
    for seed in range(CASES):
        whole = _serve(seed, "translation", False)
        opened = _serve(seed, "tree", False)
        if whole[0] != "PROMOTE":
            continue
        if opened[1].get("calls"):
            acted_anyway += 1
        # THE OTHER HALF OF THE CLAIM, and it has to be asserted rather than assumed: the
        # whole-program grain does not merely refuse, it refuses HAVING DONE NOTHING. A
        # `check(..., True)` here would have been a vacuous witness of exactly the kind
        # `consent.survey` refuses to count.
        if whole[1].get("calls"):
            whole_touched += 1
    check(f"the opened grain pays for its grain on doomed requests "
          f"({acted_anyway} acted before refusing)", acted_anyway > 0)
    check(f"the whole-program grain refused every one of them without acting "
          f"({whole_touched} touched the world)", whole_touched == 0)


def test_a_destructive_step_says_so_before_the_verdict():
    """Over generated cases, not one hand-built world."""
    print(f"[fuzz] {CASES} cases — every deletion is declared before it happens")
    from orchestrator.ai.planner.ir import effects

    undeclared = []
    for seed in range(CASES):
        world, goals, _ = fuzz.random_case(seed)
        eng = MedusaEngine(world)
        sess = Session("", eng, intent="ensure")
        sess.regime = "tree"
        deleters = set(effects.deleters(None))

        def decide(step, s):
            ran = [t for t, _ in step.destroys]
            if set(ran) - deleters:
                undeclared.append((seed, "declared a non-deleter"))
            return ins.Verdict(ins.RUN)

        before = set(world.vms)
        out = ins.drive(eng, goals, sess, decide)
        # ONLY DISAPPEARANCES COUNT. A shrinking count can also mean the run created fewer
        # than it removed, and an earlier version subtracted the two and reported CREATIONS
        # as undeclared destruction.
        gone = before - set(world.vms)
        declared = {a.get("name") for t, a in (out.get("calls") or []) if t in deleters}
        if gone - declared:
            undeclared.append((seed, f"{sorted(gone - declared)} vanished undeclared"))
    check(f"nothing was destroyed without a step naming it first "
          f"({len(undeclared)} slipped through)", not undeclared)
    for u in undeclared[:5]:
        print(f"       {u}")


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "fuzz in-session"))


if __name__ == "__main__":
    main()
