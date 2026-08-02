"""hybrid_probe.py — STRUCTURE from a whole-program draft, EMISSION per leaf.

THE TWO PATHS FAIL IN COMPLEMENTARY WAYS, measured 2026-07-30/31:

    whole-program   channel 13 · model 1       decodes badly, REASONS WELL
    tree            0 decode fails in 404 ·    decodes perfectly, ROUTES BADLY
                    5 rungs BUILD FAILED

Every tree-path loss is the router: `'connect each node to '` with no object, `'launch the
last vm'` naming nothing, an action handed `ensure`. And the whole-program path's model
layer is down to ONE failure in 78 — it gets the shape right and fumbles the bytes.

So take each path's strength. **The draft supplies the structure — how many statements,
which operator each is, what each is for — and then every statement is RE-EMITTED against
one operator's schema**, which is the surface with zero decode failures across 404
emissions.

THIS REMOVES THE ROUTER ENTIRELY. `decompose` is not called; there is no atomicity
question, no sub-goal to phrase, nothing to hand a leaf a goal with no object. That is not
a side benefit — it is the whole reason this is worth building, because the router is where
staged lowering loses every one of its rungs.

WHAT IT CANNOT DO, stated before any number is quoted: a run whose DRAFT never decodes has
no structure to start from. Measured on the 64/78 ladder, the draft produced a program
69/78 = 88% of the time, so the ceiling here is 69/78 and the honest expected gain is +5.
`para:11` and `para:13` fail the draft 3/3 and are out of reach by construction.

THE CELL TO WATCH IS lit:11. Its draft decodes 3/3 and its REPAIR fails 3/3 — exactly the
shape this replaces, since per-leaf re-emission stands in for whole-program re-authoring.

Run:  PYTHONPATH=. python3 -m tests.bench.hybrid_probe -n 3
      PYTHONPATH=. python3 -m tests.bench.hybrid_probe -r 11 -p -v
"""
import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from planner.ir import config, lower, render, validate
# THE FUNCTION, not the module — `ir/__init__` re-exports `validate` as a callable,
# so `validate.coerce_body` raises. Same trap logged twice before; import it directly.
from planner.ir.validate import coerce_body
from planner.ir import derive as _derive
from planner.ir import execute as _ir_execute
from planner.ir import run as _run

from . import env_stamp
from .author_probe import author, _seams
from .ladder import BENCH_MODEL
from .rungs import RUNGS
from .seams import seams as _mkseams
from .sim_world import SimWorld
from .tree_probe import WANT, make_emit, _goal_predicate


def tree_from_draft(draft: Any, goal: str = "", log=None) -> dict:
    """A flat tree whose leaves ARE the draft's statements — no model call, no router.

    The draft already answered every question `decompose` asks and answers badly: how many
    statements, which operator each one is, and what each is for. Reading them off costs
    nothing and cannot produce a sub-goal with no object.

    EACH LEAF'S GOAL IS THE DRAFT STATEMENT ITSELF, rendered. That is the most precise
    sub-goal available — it was written by something that had the whole goal in view — and
    it is what the per-operator emitter is asked to write properly.

    FLAT, not nested. A program IS a sequence; the tree regime's depth exists to break a
    goal down, and there is nothing left to break down once a draft has done it.
    """
    def as_node(st):
        """One draft statement as a leaf, specified by its IR — NOT by its rendering.

        THIS WAS THE FIRST VERSION'S REAL DEFECT, and it took two wrong guesses to find.
        The leaf goal was the statement as RENDERED, and `render.py` says in its own
        docstring what that is: *"one direction only ... nothing parses it back."* It is a
        human view and it is lossy on purpose. Two ways that bit:

          * AMBIGUOUS — `FOREACH $item IN SELECT vm` is printed for BOTH `{"in": "$x"}` and
            `{"select": {...}}`, so the emitter could not tell which field to write and
            answered `in: "SELECT {name} FROM {vm}"`, rejected three times running.
          * LOSSY ON BAD INPUT — a draft carrying an invalid predicate renders as the
            placeholder `<unknown check 'in'>`, and the emitter was asked to reproduce a
            statement containing a hole.

        The IR is the precise form and the model already emits IR — that is the whole
        premise of this language. So the leaf is handed the JSON, and its job is to write
        the same statement properly against one operator's schema.
        """
        return lower.node(
            "write this exact step, correcting anything malformed in it: "
            + json.dumps(st, separators=(",", ":")),
            op=st["op"])

    body = coerce_body(draft) or []
    kids = [as_node(st) for st in body if isinstance(st, dict) and st.get("op")]
    if log:
        log(f"draft gave {len(kids)} statement(s): " + ", ".join(k["op"] for k in kids))
    # THE ROOT CARRIES THE REAL GOAL, so `lower_tree` passes it down as ancestry and each
    # leaf knows what the program as a whole is for. Without it a leaf sees one rendered
    # line and nothing else.
    return lower.node(goal or "the whole program", op="call", children=kids)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Draft for structure, per-leaf for emission")
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-n", "--repeats", type=int, default=1)
    p.add_argument("-p", "--paraphrase", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    log = (lambda m: print(f"      {m}")) if a.verbose else None
    print(f"hybrid probe · model={a.model} · n={a.repeats}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}")
    print(f"   under: {env_stamp.describe(env_stamp.stamp(a.model))}\n")

    passed = attempted = 0
    no_draft = 0
    totals = {"emit_calls": 0, "leaf_bad_json": 0, "route_channel": 0, "route_calls": 0}

    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        for _ in range(a.repeats):
            attempted += 1
            world = SimWorld()
            if rung.setup:
                rung.setup(world)
                world.calls.clear()
            stats = {k: 0 for k in totals}

            # ── 1. THE DRAFT: one call, for STRUCTURE only ──────────────────────────
            draft, problems = author(goal, a.model, 0.0, True,
                                     known_names=world.names(), world=world, want=WANT)
            if draft is None:
                no_draft += 1
                print(f"   rung {rung.n:2}  NO DRAFT  {(problems or ['?'])[0][:66]}")
                continue

            # ── 2. THE TREE, read off the draft. No router, no model call. ──────────
            try:
                tree = tree_from_draft(draft, goal=goal, log=log)
                if not (tree.get("children") or []):
                    print(f"   rung {rung.n:2}  EMPTY DRAFT")
                    continue
                emit = make_emit(a.model, world, WANT, stats, log)
                # ── 3. RE-EMIT every statement against ONE operator's schema ────────
                tree = lower.lower_tree(tree, emit, want=WANT, known=world.names(),
                                        log=log)
                prog = lower.assemble(tree)
            except Exception as exc:
                for k in totals:
                    totals[k] += stats[k]
                print(f"   rung {rung.n:2}  BUILD FAILED  {type(exc).__name__}: "
                      f"{str(exc)[:70]}")
                continue
            for k in totals:
                totals[k] += stats[k]

            ok, why = validate(prog, known_names=world.names())
            checker = None
            if ok:
                sel, holds = _seams(world)
                res = {}
                try:
                    res = _run(prog, world.execute, select=sel, holds=holds,
                               known_names=world.names(), consent=True, intent=WANT) or {}
                except Exception:
                    pass
                # Same convergence step the other two probes take — a failing ACHIEVE
                # comes back `unachieved` and the CALLER computes the difference.
                if res.get("failed") == "unachieved":
                    pred = _goal_predicate(prog)
                    fix = _derive(pred, sel, res.get("scope"), WANT) if pred else None
                    if fix:
                        try:
                            _run(_ir_execute.follow_up(res, fix), world.execute, select=sel,
                                 holds=holds, known_names=world.names(), consent=True,
                                 intent=WANT)
                        except Exception:
                            pass
                checker = rung.check(world)
                passed += 1 if checker else 0
            print(f"   rung {rung.n:2}  draft={len(coerce_body(draft) or [])}st "
                  f"emit={stats['emit_calls']} badjson={stats['leaf_bad_json']}  "
                  f"{'VALID' if ok else 'INVALID'}  "
                  f"checker={'PASS' if checker else ('FAIL' if ok else '-')}")
            if a.verbose:
                for line in render(prog).splitlines():
                    print(f"          | {line}")
                if not ok:
                    print(f"          - {why[0]}")

    print(f"\n── summary · harness=hybrid_probe · model={a.model} · n={a.repeats}")
    print(f"   CHECKER PASS       : {passed}/{attempted}")
    print(f"   NO DRAFT           : {no_draft}   <- the ceiling: no structure, no run")
    print(f"   leaf emissions     : {totals['emit_calls']}")
    print(f"   LEAF DECODE FAILS  : {totals['leaf_bad_json']}")
    print(f"   ROUTING CALLS      : 0   <- structure came from the draft, not a router")
    return 0


if __name__ == "__main__":
    sys.exit(main())
