#!/usr/bin/env python3
"""
test_fuzz_writer.py — the ghost writer against worlds and goals nobody chose.

Thirteen rungs are thirteen cases, picked by people, so passing them all is consistent with
a writer that was shaped to pass them. This runs hundreds of generated cases with an exact
ground truth: after the program runs, do the goals HOLD — judged by the same evaluator the
language uses.

NO MODEL. This isolates the writing half completely, so any failure is the writer's and
nothing else's.

OUTCOMES NAME THE OWNER, the way `ladder_gate` names layers:
    VERIFIED    the goals hold afterwards
    BROKEN      it built and ran, and they do not — the writer's fault
    UNSOLVABLE  it refused, honestly — a GAP IN THE RULES, not a wrong answer
    IMPOSSIBLE  the case contradicts itself; the generator's fault, counted separately
    CRASHED     the harness

Run:  PYTHONPATH=. python3 -m tests.test_fuzz_writer
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir import consent, effects, master, validate
from orchestrator.ai.planner.ir import run as ir_run
from tests.bench import fuzz
from tests.bench.ghost_writer import Unsolvable, as_program, cover
from tests.bench.seams import seams

_PASS = 0
_FAIL = 0
CASES = int(os.environ.get("FUZZ_CASES", "300"))


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _one(seed):
    world, goals, _text = fuzz.random_case(seed)
    if not goals:
        return "IMPOSSIBLE", "no goals generated", None
    if fuzz.contradictory(goals):
        return "IMPOSSIBLE", "the case contradicts itself", None
    try:
        plan = cover(goals, world)
    except Unsolvable as e:
        return "UNSOLVABLE", str(e)[:110], None
    except Exception as e:
        return "CRASHED", f"{type(e).__name__}: {e}", None
    prog = as_program(plan, goals, world)
    if not prog["body"]:
        # THE EMPTY PROGRAM IS A LEGITIMATE ANSWER, not an invalid one. `validate` rejects a
        # body with no statements — correct for something a model wrote, wrong for a writer
        # that examined the world and found nothing owed. Judged on the goals instead, which
        # is the only question that matters.
        held, why = fuzz.holds_all(goals, world)
        return ("VERIFIED", f"nothing to do — {why}", prog) if held else ("BROKEN", why, prog)
    ok, problems = validate(prog, known_names=world.names())
    if not ok:
        return "BROKEN", f"invalid: {(problems or ['?'])[0][:90]}", prog
    sel, holds = seams(world)
    try:
        res = ir_run(prog, world.execute, select=sel, holds=holds,
                     known_names=world.names(), consent=True, intent="achieve")
    except Exception as e:
        return "CRASHED", f"{type(e).__name__}: {e}", prog
    if not res["ok"]:
        return "BROKEN", f"its own checks failed: {res.get('why')}", prog
    held, why = fuzz.holds_all(goals, world)
    return ("VERIFIED", why, prog) if held else ("BROKEN", why[:110], prog)


def test_random_cases_end_with_the_goals_holding():
    """The headline: a program the writer produced must make its goals true."""
    print(f"[fuzz] {CASES} generated cases, seeds 1..{CASES}")
    got, examples = Counter(), {}
    for seed in range(1, CASES + 1):
        outcome, why, _ = _one(seed)
        got[outcome] += 1
        examples.setdefault(outcome, (seed, why))
    for k in sorted(got):
        seed, why = examples[k]
        print(f"       {k:<11} {got[k]:>4}   e.g. seed {seed}: {why}")

    live = got["VERIFIED"] + got["BROKEN"] + got["UNSOLVABLE"] + got["CRASHED"]
    # IMPOSSIBLE CASES ARE EXCLUDED FROM THE DENOMINATOR, not counted as failures. Scoring
    # the code against cases the generator made unsatisfiable would inflate the error rate
    # with noise and call it signal.
    check(f"nothing crashes ({got['CRASHED']} crashes)", got["CRASHED"] == 0)
    check(f"nothing BROKEN — every program makes its goals true ({got['BROKEN']} broken)",
          got["BROKEN"] == 0)
    check(f"at least 9 in 10 solvable ({got['VERIFIED']}/{live})",
          live and got["VERIFIED"] / live >= 0.9)


def test_every_random_program_is_grounded_and_none_vouch_vacuously():
    """Grounding must survive contact with cases nobody designed.

    On the ladder this property was asked of a model and 60 of 78 programs lacked it. Here
    it is structural — but structural claims are exactly the ones worth fuzzing, because
    "it cannot happen" is what everyone believed about the schema that was never enforced.
    """
    print("[fuzz] grounding holds across generated cases")
    ungrounded, vacuous, seen = [], [], 0
    for seed in range(1, CASES + 1):
        outcome, _why, prog = _one(seed)
        if outcome != "VERIFIED" or prog is None:
            continue
        seen += 1
        s = consent.survey(prog)
        # AN OBSERVE-ONLY PROGRAM HAS NOTHING TO VOUCH FOR, so grounding does not apply.
        # `consent` counts a probe as an acting statement because acting-ness is decided per
        # OP and a probe is a `call` — conservative rather than dangerous for a reader that
        # holds nothing but the artifact, and its docstring says so.
        #
        # ASKED OF THE MANIFEST, NOT OF ONE TOOL'S NAME. This used to require every statement
        # to be a `guest_ping` call, which named a single tool and broke twice over: a probe
        # of any other kind counted as an act, and `PUBLISH done` — appended to every program
        # the writer emits — is not a call at all, so the exemption stopped matching anything
        # and 34 read-only programs were reported as ungrounded work.
        changes_nothing = not [st for st in consent._walk(prog["body"])
                               if master.statement_acts(st, effects.actors())]
        if s["acts"] and not s["grounded"] and not changes_nothing:
            ungrounded.append(seed)
        if s["vacuous"]:
            vacuous.append(seed)
    check(f"every acting program is grounded ({seen} checked)", not ungrounded)
    check("no witness is vacuous", not vacuous)


def test_running_it_twice_changes_nothing_the_second_time():
    """Idempotence on random cases — the property that stops a re-run duplicating work.

    Rung 13 exists because a 5 -> 10 -> 15 cascade was once measured. That was one case; this
    is every case, minus the ones whose goals begin with an observation, where re-asking is
    the point rather than a defect.
    """
    print("[fuzz] a second pass over a satisfied world writes nothing")
    bad = []
    for seed in range(1, CASES + 1):
        world, goals, _ = fuzz.random_case(seed)
        if not goals or fuzz.contradictory(goals):
            continue
        try:
            for tool, args in cover(goals, world):
                world.execute(tool, args)
            again = cover(goals, world)
        except Unsolvable:
            continue
        # THE MANIFEST DECIDES WHICH CALLS ARE WORK, not a tool name written here. This said
        # `c[0] != "guest_ping"`, which is the same single-tool assumption `_walk` above was
        # carrying: a probe added to any other kind would have counted as repeated work and
        # failed a correct writer.
        acting = [c for c in again if c[0] in effects.actors()]
        if acting:
            bad.append((seed, acting[:2]))
    check(f"no second pass repeats work ({len(bad)} that do)", not bad)
    if bad:
        print(f"       e.g. seed {bad[0][0]}: {bad[0][1]}")


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "fuzz"))


if __name__ == "__main__":
    main()
