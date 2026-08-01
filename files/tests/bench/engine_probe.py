"""engine_probe.py — the PRODUCTION PATH on the ladder, served as ACHIEVE.

#9 asked for the tree path behind `ladder_gate`. That was written when the tree was the
model-driven decomposer measured at 4/13, and it means something different now: `achieve`
maps to the TREE regime, and the tree is served by the orchestrator — claim, sync, route,
in-session, per-goal verdicts, a closing witness over the whole request.

WHAT THIS MEASURES THAT NOTHING ELSE DOES. `author_probe` measures a model AUTHORING.
`test_medusa_rungs` measures the engine path with the channel STUBBED, which is the writer
and the wiring with no front seam. This is the whole thing end to end, with the real
extractor at the front and the real orchestrator behind it — and it is the only arm whose
number answers "what happens when somebody types this".

THE OUTCOME CODES ARE THE ORCHESTRATOR'S OWN, because that is what a reader of this path
sees. UNTRANSLATED is not a failure of the engine and must not be counted as one; it names
the front seam, which is the whole point of a code that says which layer owns it.

    PYTHONPATH=. python3 -m tests.bench.engine_probe [-n 3] [-r 4] [-p]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from orchestrator.ai.engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     insession)
from orchestrator.ai.engines.channel import Answer
from orchestrator.ai.engines import extract as _extract
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld


class _Lab(MedusaEngine):
    name = "medusa"


def one(rung, paraphrase: bool, intent: str = "achieve"):
    """One rung, through the production path. Returns (outcome, calls, checker)."""
    text = (rung.paraphrase or rung.goal) if paraphrase else rung.goal
    world = SimWorld()
    if rung.setup:
        rung.setup(world)

    def translate(request, w=None):
        try:
            raw = _extract.extract(str(request))
        except Exception as exc:
            return Answer(None, "extractor", f"{type(exc).__name__}: {exc}")
        goals = _extract.to_goals(raw, str(request))
        return (Answer(goals, "extractor", "") if goals
                else Answer(None, "extractor", "no usable goal"))
    translate.name = "extractor"

    registry = Registry()
    registry.mount(_Lab(world))
    orch = Orchestrator(registry, Channel([translate]),
                        decide=lambda st, s: insession.Verdict(insession.RUN))
    try:
        out = orch.handle(text, intent=intent)
    except Exception as exc:
        # A CRASH IS ALWAYS THE HARNESS'S FAULT TO REPORT, never a quiet zero.
        return f"CRASHED:{type(exc).__name__}", 0, False
    return out["outcome"], len(out.get("calls") or []), bool(rung.check(world))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=1)
    ap.add_argument("-r", "--rung", type=int, action="append")
    ap.add_argument("-p", "--paraphrase", action="store_true")
    ap.add_argument("-i", "--intent", default="achieve",
                    choices=["fetch", "ensure", "achieve"])
    a = ap.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    tally, achieved = Counter(), 0
    total = 0
    for rung in rungs:
        for i in range(a.repeats):
            outcome, calls, held = one(rung, a.paraphrase, a.intent)
            total += 1
            # WHAT COUNTS IS THE WORLD, not the outcome word. A run that closed DONE over a
            # goal that does not hold is the failure this whole session has been about.
            good = outcome == "DONE" and held
            achieved += 1 if good else 0
            tally[outcome if held or outcome != "DONE" else "DONE_BUT_FALSE"] += 1
            print(f"  rung {rung.n:>2} [{i + 1}/{a.repeats}] {outcome:<14} "
                  f"{calls:>3} calls  checker={held}", flush=True)

    print(f"\n── the production path · intent={a.intent} · "
          f"{'paraphrase' if a.paraphrase else 'literal'} · n={a.repeats}")
    print(f"  ACHIEVED FOR REAL {achieved}/{total}")
    for outcome, n in tally.most_common():
        print(f"    {n:>3}  {outcome}")
    if tally.get("DONE_BUT_FALSE"):
        print("\n  *** DONE_BUT_FALSE is the only unacceptable outcome here: the run said it "
              "finished and the world disagrees. ***")
    return 1 if tally.get("DONE_BUT_FALSE") else 0


if __name__ == "__main__":
    sys.exit(main())
