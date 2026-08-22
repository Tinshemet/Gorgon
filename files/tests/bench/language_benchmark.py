"""language_benchmark.py — DOES THIS LANGUAGE PRODUCE THE COMPUTATIONAL MODEL? The 14 rungs, graded.

    PYTHONPATH=. python3 -m tests.bench.language_benchmark                       # english
    PYTHONPATH=. python3 -m tests.bench.language_benchmark --language hebrew --runs 3
    PYTHONPATH=. python3 -m tests.bench.language_benchmark --no-model            # the code-only floor
    ⚠ NEEDS THE MODEL unless --no-model. Vary PYTHONHASHSEED between invocations (rule V3).

# ⇒⇒ WHAT THIS MEASURES, AND WHAT IT DELIBERATELY DOES NOT

Gorgon's chain is plain text -> COMPUTATIONAL MODEL -> code, and only the first link is
language-dependent (orchestrator/languages/README.md). So the question for a second language
is not "does it read sentences" — it is **does its scaffold produce the same computational
model the English one does, on the requests the project already calls correct?** The operator,
2026-08-22: *"if it can produce a correct computational model on the 14 rungs it is a
candidate for the ability to port it over."*

The computational model of a reading is `pipeline.Run` reduced to what is LANGUAGE-NEUTRAL:

    steps   [(operator, SELECTOR, value)]   the operations, with every HANDLE resolved through
                                            the symbol table to what it selects — {kind, …where}
                                            — because handles are derived from the language's
                                            surface (`stopped_vms`, `the_ones_that_do_not_answer`
                                            for the same row on two runs) and a second language
                                            would never reproduce them
    goals   [{shape, select, …}]            the states an ACHIEVE request asks to hold — already
                                            the GOALS table shape, already neutral
    outcome SERVE · BOUNCE · ASK · REFUSE   reported beside the grade, never part of it

⇒ **THE JUDGE IS THE ANSWER KEY, NOT THE WORLD — and that is a limit, stated.** The honest
  judge would execute the reading against a SimWorld and run each rung's own checker
  (`tests/bench/rungs.py`), which is what `test_medusa_rungs` does with the channel stubbed to
  GOALS. But `Run -> executable program` is not wired (the translates-consumer debt), so today
  the model is graded by comparison. When that wiring lands, this file's grade should become
  `rung.check(world)` and the key below retires.

⇒ **ONLY UNAMBIGUOUS RUNGS ARE GRADED; THE REST ARE REPORTED.** Same discipline as `pass2.WANT`:
  a key is written where the correct model is not a judgement call, and a rung without one is
  shown so a regression is visible, never scored so a guess becomes a number. The key is
  `pass2.WANT` resolved to selectors (steps) + `test_ghost_writer.GOALS` where the seam's goal
  shape is directly comparable (goals). **Written down before the first run (rule V5).**

⇒ **PASS means: steps SET-EQUAL or EXACT to the key AND goals equal to the key, on EVERY run.**
  A rung that passes on two runs of three is not a pass — the model wobbles at temp 0 and a
  candidate language has to hold under that. CANDIDATE = every graded rung passes.

⇒ THE CONTROL. English is the reference scaffold: whatever it scores here is the ceiling a
  port is measured against, not a pass mark in itself. A language package with no scaffold is
  an ImportError, not a zero — the benchmark refuses to grade what it cannot run.

# ⇒ WHAT A LANGUAGE PACKAGE MUST PROVIDE (the benchmark's side of the contract)

    orchestrator/languages/<lang>/rungs.py          RUNGS: Dict[int, str] — the 14, natively
    orchestrator/languages/<lang>/seam/pipeline.py  run(request, board, world, model) -> Run
    orchestrator/languages/<lang>/seam/pass2.py     Symbol(handle, row) — the table Run carries
"""
import argparse
import importlib
import json
from typing import Any, Dict, List, Optional, Tuple

from planner.formula.legal import Board

# ── THE ANSWER KEY — neutral selectors, written before the first run ─────────────────────
#
#   A selector is {"kind": <manifest kind>, **where}; a named individual carries its name in
#   `where` the way the seam declares it. `value` is a selector when the operation points at a
#   second thing (add_vm_to_network's network) and a literal otherwise (a label).
VM = lambda **w: {"kind": "vm", **w}
NET = lambda **w: {"kind": "network", **w}

KEY_STEPS: Dict[int, List[Tuple[str, dict, Any]]] = {
    1:  [("create_vm", VM(name="alpha"), None)],
    2:  [("create_vm", VM(name="beta"), None), ("launch_vm", VM(name="beta"), None)],
    3:  [("create_network", NET(net_name="lab"), None), ("create_vm", VM(name="web"), None),
         ("add_vm_to_network", VM(name="web"), NET(net_name="lab"))],
    5:  [("launch_vm", VM(status="stopped"), None)],
    11: [("probe_alive", VM(), None), ("stop_vm", VM(alive=False), None)],
    12: [("create_snapshot", VM(status="running"), None)],
}
KEY_GOALS: Dict[int, List[dict]] = {
    7:  [{"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 3}],
    14: [{"shape": "count", "select": {"kind": "vm"}, "eq": 2}],
}
GRADED = sorted(set(KEY_STEPS) | set(KEY_GOALS))
# Rungs with a key on ONE side only are graded on that side; the other side is reported.


def load_language(name: str):
    """The three things the benchmark needs from a language package — or a clear refusal."""
    base = f"orchestrator.languages.{name}"
    try:
        rungs = importlib.import_module(f"{base}.rungs").RUNGS
        pipeline = importlib.import_module(f"{base}.seam.pipeline")
    except ModuleNotFoundError as exc:
        raise SystemExit(f"no scaffold for language {name!r}: {exc}\n"
                         f"  a language package needs rungs.py and seam/pipeline.py — "
                         f"see orchestrator/languages/README.md") from exc
    return rungs, pipeline


def _selector(symbol) -> dict:
    """What a handle SELECTS — kind plus the row's conditions; the set marker is not a kind."""
    row = symbol.row
    kind = str(row.object_type or "")
    if kind.endswith("_set"):
        kind = kind[:-4]
    out: Dict[str, Any] = {"kind": kind}
    out.update({k: v for k, v in dict(row.where or {}).items()})
    return out


def neutral(run) -> dict:
    """pipeline.Run -> the language-neutral computational model."""
    by_handle = {s.handle: s for s in run.table}
    steps = []
    for op in run.operations:
        on = _selector(by_handle[op.on]) if op.on in by_handle else {"unresolved": op.on}
        value = op.value
        if isinstance(value, str) and value in by_handle:
            value = _selector(by_handle[value])
        steps.append((op.operator, on, value))
    return {"steps": steps, "goals": list(run.goals or []), "outcome": run.outcome}


def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, default=str)


def grade_steps(got: List[tuple], want: List[tuple]) -> str:
    g = [_canon(s) for s in got]
    w = [_canon(s) for s in want]
    if g == w:
        return "EXACT"
    if sorted(g) == sorted(w):
        return "SET-EQUAL"
    return f"{len(set(g) & set(w))}/{len(w)} steps"


def grade_goals(got: List[dict], want: List[dict]) -> str:
    g = sorted(_canon(x) for x in got)
    w = sorted(_canon(x) for x in want)
    return "EQUAL" if g == w else f"{len(set(g) & set(w))}/{len(w)} goals"


def passed(step_grade: Optional[str], goal_grade: Optional[str]) -> bool:
    ok_steps = step_grade in (None, "EXACT", "SET-EQUAL")
    ok_goals = goal_grade in (None, "EQUAL")
    return ok_steps and ok_goals


def _show(sel) -> str:
    if isinstance(sel, dict):
        kind = sel.get("kind", "?")
        rest = ", ".join(f"{k}={v}" for k, v in sel.items() if k != "kind")
        return f"{kind}[{rest}]" if rest else kind
    return repr(sel)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", default="english")
    ap.add_argument("--runs", type=int, default=1, help="repeat every rung; PASS needs all")
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--no-model", action="store_true",
                    help="stub the model: what the CODE alone reads (the structure floor)")
    ap.add_argument("--no-lab", action="store_true", help="no world — bare names stay kindless")
    args = ap.parse_args()

    rungs, pipeline = load_language(args.language)
    from tests.bench.twopass.metrics import Lab
    board = Board()
    world = None if args.no_lab else Lab()
    if args.no_model:
        import engines.channel as channel
        channel.constrained = lambda *a, **k: {}

    print("=" * 100)
    print(f"LANGUAGE BENCHMARK · {args.language} · {len(rungs)} rungs · runs={args.runs}"
          f"{' · NO MODEL' if args.no_model else ''}{' · NO LAB' if args.no_lab else ''}")
    print("=" * 100)
    results: Dict[int, List[bool]] = {}
    for n in sorted(rungs):
        if args.only and n != args.only:
            continue
        request = rungs[n]
        print(f"\n{'─' * 100}\nrung {n:>2} · “{request[:80]}”")
        for i in range(args.runs):
            got = neutral(pipeline.run(request, board=board, world=world, model=args.model))
            sg = grade_steps(got["steps"], KEY_STEPS[n]) if n in KEY_STEPS else None
            gg = grade_goals(got["goals"], KEY_GOALS[n]) if n in KEY_GOALS else None
            ok = passed(sg, gg) if n in GRADED else None
            results.setdefault(n, []).append(bool(ok))
            tag = ("PASS" if ok else "FAIL") if n in GRADED else "reported"
            run_lbl = f"run {i + 1}  " if args.runs > 1 else ""
            print(f"    {run_lbl}steps   "
                  + (", ".join(f"{o}({_show(s)}{', ' + _show(v) if v is not None else ''})"
                               for o, s, v in got["steps"]) or "—"))
            if got["goals"]:
                print(f"    {' ' * len(run_lbl)}goals   {got['goals']}")
            print(f"    {' ' * len(run_lbl)}grade   steps {sg or '— no key'} · goals {gg or '— no key'}"
                  f" · outcome {got['outcome']}   ⇒ {tag}")

    graded = [n for n in GRADED if n in results]
    all_pass = [n for n in graded if all(results[n])]
    unstable = [n for n in graded if any(results[n]) and not all(results[n])]
    reported = [n for n in results if n not in GRADED]
    print(f"\n{'=' * 100}")
    print(f"  graded   {len(graded)} rungs {graded}")
    print(f"  PASS     {len(all_pass)}/{len(graded)} {all_pass}")
    if unstable:
        print(f"  UNSTABLE {unstable}   (passed some runs, not all — not a pass)")
    print(f"  reported {len(reported)} rungs {reported}   (no unambiguous key — shown, not scored)")
    candidate = bool(graded) and len(all_pass) == len(graded)
    print(f"  ⇒ {args.language}: {'CANDIDATE — every graded rung produced the computational model' if candidate else 'NOT a candidate'}")
    print("=" * 100)


if __name__ == "__main__":
    main()
