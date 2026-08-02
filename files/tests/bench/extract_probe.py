"""extract_probe.py — the WHOLE pipeline against the ladder: AI translates, code writes.

    English -> extract.extract (the only model call) -> ghost_writer.cover -> run -> checker

Same 13 rungs, same two columns, same `rung.check` that grades the whole-program author, so
the numbers sit beside each other honestly.

WHAT A FAILURE MEANS HERE, and this is the reason the split exists. The ghost writer covers
all 13 rungs from hand-written components, so a cell that fails now failed in TRANSLATION —
the model misread the request. There is no second explanation. Under the whole-program path
a red cell could mean the goal was misread OR the writing fumbled, and nothing distinguished
them; a day was spent on that ambiguity.

Outcomes name the layer the same way `ladder_gate` does:
    EXTRACT_EMPTY   the model returned no usable goal at all
    EXTRACT_WRONG   goals came back, but the writer could not build them (`Unsolvable`)
    GOAL_UNMET      it built and ran, and the program's own checks failed
    CHECKER_FAIL    it ran and vouched for itself, and the rung disagrees — a MISREADING
                    that produced a coherent program for a different request

Run:  PYTHONPATH=. python3 -m tests.bench.extract_probe -n 1
      PYTHONPATH=. python3 -m tests.bench.extract_probe -n 3 -p
"""
import argparse
import json
import sys
from collections import Counter

from planner.ir import consent, render, validate
from planner.ir import run as ir_run

from engines import extract as _extract
from .ghost_writer import Unsolvable, as_program, cover
from .ladder import BENCH_MODEL
from .rungs import RUNGS
from .seams import seams
from .sim_world import SimWorld


def one(rung, paraphrase: bool, model: str, verbose: bool):
    text = (rung.paraphrase or rung.goal) if paraphrase else rung.goal
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    try:
        raw = _extract.extract(text, model)
    except Exception as e:
        return "EXTRACT_EMPTY", f"{type(e).__name__}: {e}", 0
    said_no = _extract.declined(raw)
    goals = _extract.to_goals(raw, text)
    if said_no and not goals:
        # A REFUSAL IS ITS OWN OUTCOME, not an empty extraction. "I cannot express this"
        # is a different event from "I tried and produced nothing", and on the rungs — all
        # of which ARE expressible — it is a failure worth naming separately.
        return "DECLINED", said_no[:120], 0
    if verbose:
        print(f"        extracted: {json.dumps(goals)[:300]}")
    if not goals:
        return "EXTRACT_EMPTY", json.dumps(raw)[:120], 0
    try:
        plan = cover(goals, world)
    except Unsolvable as e:
        return "EXTRACT_WRONG", str(e)[:120], 0
    except Exception as e:
        return "CRASHED", f"{type(e).__name__}: {e}", 0
    prog = as_program(plan, goals, world)
    if verbose:
        print("        " + "\n        ".join(render(prog).splitlines()))
    ok, problems = validate(prog, known_names=world.names())
    if not ok:
        # The writer emitting an invalid program would be a defect in the WRITER, not the
        # model — worth its own code so it can never be read as a translation failure.
        return "WRITER_INVALID", (problems or ["?"])[0][:120], len(plan)
    sel, holds = seams(world)
    res = ir_run(prog, world.execute, select=sel, holds=holds,
                 known_names=world.names(), consent=True, intent="achieve")
    if not res["ok"]:
        return "GOAL_UNMET", str(res.get("why") or res.get("failed"))[:120], len(plan)
    if not rung.check(world):
        return "CHECKER_FAIL", "built and vouched for itself; the rung disagrees", len(plan)
    return "PASS", None, len(plan)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("-n", "--repeats", type=int, default=1)
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-p", "--paraphrase", action="store_true")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    # VERIFY THE MECHANISM FIRED BEFORE BELIEVING ANY NUMBER. The whole of 2026-07-31 came
    # from a grammar that was accepted and ignored, so this asks a question whose answer
    # cannot be JSON and refuses to run if JSON comes back anyway.
    if not _extract.assert_enforced(a.model):
        print("REFUSING TO RUN: the schema is not being enforced — a result measured now "
              "would be measuring free generation, exactly as the ladder did for weeks.")
        return 2
    print(f"extract probe · model={a.model} · constrained decoding VERIFIED · "
          f"schema {len(json.dumps(_extract.SCHEMA))} chars · prompt {len(_extract.PROMPT)} chars"
          + (" · PARAPHRASE" if a.paraphrase else ""))

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    cells, calls = {}, {}
    for r in rungs:
        got = Counter()
        for i in range(a.repeats):
            outcome, why, n = one(r, a.paraphrase, a.model, a.verbose)
            got[outcome] += 1
            calls.setdefault(r.n, []).append(n)
            tail = f"  {why}" if why else ""
            print(f"  rung {r.n:>2} [{i + 1}/{a.repeats}] {outcome:<14} {n:>3} calls{tail}")
        cells[r.n] = got

    total = sum(sum(c.values()) for c in cells.values())
    good = sum(c.get("PASS", 0) for c in cells.values())
    print("\n── summary")
    for n in sorted(cells):
        best = next(r.best for r in RUNGS if r.n == n)
        print(f"  rung {n:>2}  {dict(cells[n])}  calls={calls[n]}  best={best}")
    layers = Counter()
    for c in cells.values():
        for k, v in c.items():
            if k != "PASS":
                layers[k] += v
    print(f"\n  RUNS {total} · GOAL ACHIEVED {good}/{total}")
    print(f"  failures: {dict(layers) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
