"""
tree_probe.py — staged lowering END TO END against the ladder's goals.

decompose -> emit per leaf (one operator's schema, with retry) -> gate at fusion ->
review the whole artifact -> assemble -> run -> the rung's own checker.

THE COMPARISON THIS EXISTS FOR. Today's authoring asks for the whole program in one call
against an ELEVEN-branch `oneOf`, and the recorded baseline is 57/78 with 12 of 21 failures
in the channel. Measured 2026-07-29, that channel is not mysterious: under eleven branches
the model emitted `{"op": "else": ...}` — an op NO BRANCH PERMITS — while every constraint
shape held 5/5 at one or two branches. If branch count is the mechanism, a leaf offered ONE
operator's schema should not produce malformed output at all, and that is the claim this
probe tests.

WHAT IS BEING MEASURED, and it is not only the pass rate:

    decode failures   per LEAF rather than per program — the number that decides whether
                      the branch-count theory holds
    calls             routing + emission + retries. The design costs more calls on purpose;
                      the note is explicit that latency is a consequence, not the objective
    review findings   coverage / grounding / repetition on the assembled artifact

Run:  PYTHONPATH=. python3 -m tests.bench.tree_probe -n 1
      PYTHONPATH=. python3 -m tests.bench.tree_probe -r 8 -p -v
"""
import argparse
import json
import sys
import urllib.request
from typing import Any, Dict, List, Optional

from orchestrator.ai.planner import clause_ledger as _cl
from orchestrator.ai.planner.ir import config, lower, render, validate
from orchestrator.ai.planner.ir import derive as _derive
from orchestrator.ai.planner.ir import run as _run

from .author_probe import _OLLAMA, _OLLAMA_CTX, _seams, _messages
from .ladder import BENCH_MODEL
from .rungs import RUNGS
from .sim_world import SimWorld

_STRUCTURAL = list(config.OP_CATEGORIES["structural"])
_ALL_OPS = list(config.OPS.keys())


def _post(payload: Dict[str, Any], timeout: int = 300) -> Dict[str, Any]:
    r = urllib.request.urlopen(urllib.request.Request(
        _OLLAMA, json.dumps(payload).encode(), {"Content-Type": "application/json"}),
        timeout=timeout)
    return json.loads(r.read())


# ── the router: one operator, or decompose? ─────────────────────────────────────────────
def _route_tool() -> Dict[str, Any]:
    menu = "\n".join(f"  {o} — {(config.OPS[o].get('doc') or '').split('.')[0]}"
                     for o in _ALL_OPS)
    return {"type": "function", "function": {
        "name": "route",
        "description": ("Decide whether a goal is ONE statement or must be broken up.\n"
                        "A loop over a set is ONE statement, not one per member. An "
                        "end-state to make true is ONE statement however much work it "
                        "implies.\n\nThe operators:\n" + menu),
        "parameters": {"type": "object", "properties": {
            "atomic": {"type": "boolean",
                       "description": "true if ONE statement expresses the whole goal"},
            "op": {"type": "string", "enum": _ALL_OPS,
                   "description": "which operator this node IS. If it decomposes, the "
                                  "operator its sub-goals sit INSIDE (a loop is `foreach`; "
                                  "a plain ordered list is `call`)"},
            "steps": {"type": "array", "items": {"type": "string"},
                      "description": "when NOT atomic: the ordered sub-goals, plain English"},
        }, "required": ["atomic", "op"]}}}


def make_route(model: str, world: SimWorld, stats: Dict[str, int], log=None):
    def route(goal: str):
        stats["route_calls"] += 1
        reply = _post({"model": model, "stream": False, "tools": [_route_tool()],
                       "options": {"temperature": 0.0, "num_ctx": _OLLAMA_CTX},
                       "messages": [
                           {"role": "system", "content":
                            "You are given a goal. Call `route` exactly once."},
                           {"role": "user", "content": goal}]})
        msg = reply.get("message") or {}
        for tc in (msg.get("tool_calls") or []):
            args = (tc.get("function") or {}).get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            if log:
                log(f"route {goal[:44]!r} -> atomic={args.get('atomic')} "
                    f"op={args.get('op')} steps={len(args.get('steps') or [])}")
            return args
        stats["route_channel"] += 1
        raise lower.DecompositionError(f"router returned no call for {goal!r}")
    return route


# ── the emitter: ONE operator's schema per leaf ─────────────────────────────────────────
def make_emit(model: str, world: SimWorld, want: str, stats: Dict[str, int], log=None):
    def emit(leaf: dict, schema: Dict[str, Any], objection: Optional[str] = None):
        stats["emit_calls"] += 1
        msgs = _messages(leaf["goal"], True, world, want)
        msgs[-1]["content"] += (
            f"\n\nWrite EXACTLY ONE statement, and it is a `{leaf['op']}`. "
            f"Nothing else — this is one step of a larger program.")
        if objection:
            msgs[-1]["content"] += (
                f"\n\nYour last attempt was REJECTED: {objection}\nFix exactly that.")
        reply = _post({"model": model, "stream": False, "format": schema,
                       "options": {"temperature": 0.0, "num_ctx": _OLLAMA_CTX},
                       "messages": msgs})
        raw = (reply.get("message") or {}).get("content") or ""
        try:
            return json.loads(raw)
        except ValueError:
            # THE NUMBER THIS PROBE EXISTS FOR. A leaf that does not parse is a decode
            # failure at ONE branch — if the branch-count theory is right this should be
            # rare where the eleven-branch schema failed 12 times in 21.
            stats["leaf_bad_json"] += 1
            if log:
                log(f"  leaf decode FAILED ({len(raw)}b): {raw[:90]!r}")
            raise ValueError("leaf did not parse")
    return emit


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Staged lowering, end to end")
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-n", "--repeats", type=int, default=1)
    p.add_argument("-p", "--paraphrase", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    log = (lambda m: print(f"      {m}")) if a.verbose else None
    print(f"tree probe · model={a.model} · n={a.repeats}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}\n")

    passed = attempted = 0
    totals = {"route_calls": 0, "emit_calls": 0, "leaf_bad_json": 0, "route_channel": 0}

    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        for _ in range(a.repeats):
            attempted += 1
            world = SimWorld()
            if rung.setup:
                rung.setup(world)
                world.calls.clear()
            stats = {k: 0 for k in totals}
            try:
                route = make_route(a.model, world, stats, log)
                emit = make_emit(a.model, world, "achieve", stats, log)
                tree = lower.decompose(goal, route, log=log)
                tree = lower.lower_tree(tree, emit, want="achieve",
                                        known=world.names(), log=log)
                led = _cl.open_ledger(goal, rung.demands or [])
                report = lower.review(
                    tree, led if rung.demands else None,
                    (lambda l, b: _cl.unaccounted(_cl.reconcile(l, b)))
                    if rung.demands else None)
                prog = lower.assemble(tree)
            except Exception as exc:
                for k in totals:
                    totals[k] += stats[k]
                print(f"   rung {rung.n:2}  BUILD FAILED  {type(exc).__name__}: "
                      f"{str(exc)[:88]}")
                continue
            for k in totals:
                totals[k] += stats[k]

            ok, problems = validate(prog)
            checker = None
            if ok:
                sel, holds = _seams(world)
                try:
                    _run(prog, world.execute, select=sel, holds=holds)
                except Exception:
                    pass
                checker = rung.check(world)
                passed += 1 if checker else 0
            flags = []
            if not report.get("grounded"):
                flags.append("ungrounded")
            if report.get("unaccounted"):
                flags.append(f"{len(report['unaccounted'])} unaccounted")
            if report.get("repeated"):
                flags.append(f"{len(report['repeated'])} repeated")
            print(f"   rung {rung.n:2}  leaves={len(lower.leaves(tree))} "
                  f"calls={stats['route_calls']}r+{stats['emit_calls']}e "
                  f"badjson={stats['leaf_bad_json']}  "
                  f"{'VALID' if ok else 'INVALID'}  "
                  f"checker={'PASS' if checker else ('FAIL' if ok else '-')}"
                  + (f"  [{' · '.join(flags)}]" if flags else ""))
            if a.verbose:
                for line in render(prog).splitlines():
                    print(f"          | {line}")
                if not ok:
                    print(f"          - {problems[0]}")

    print(f"\n── summary · harness=tree_probe · model={a.model} · n={a.repeats}")
    print(f"   CHECKER PASS       : {passed}/{attempted}")
    print(f"   routing calls      : {totals['route_calls']}"
          f"   (channel failures: {totals['route_channel']})")
    print(f"   leaf emissions     : {totals['emit_calls']}")
    print(f"   LEAF DECODE FAILS  : {totals['leaf_bad_json']}"
          f"   <- the branch-count claim lives or dies here")
    print(f"\n   Baseline for comparison: whole-program authoring, 57/78 goal achieved,")
    print(f"   12 of 21 failures in the channel, on an ELEVEN-branch oneOf.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
