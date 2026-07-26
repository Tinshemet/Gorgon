"""ladder.py — run the complexity ladder against the real local model.

    PYTHONPATH=files python3 -m bench.ladder              # every rung, 1 run each
    PYTHONPATH=files python3 -m bench.ladder -r 4 -n 3    # rung 4, three runs
    PYTHONPATH=files python3 -m bench.ladder -v           # stream the plan tree

What is real here: the model (llama3.1:8b via Ollama), the tool schemas, the Engine and
every piece of reasoning scaffolding. What is simulated: the executor (bench.SimWorld), so
runs are fast, free, repeatable, and can't touch the operator's real ~/.gorgon.

Two deliberate departures from run_autonomous_live, both for measurement hygiene:
  • temperature 0 (config default is higher) — variance is the thing being measured, so it
    shouldn't come from sampling. Override with --temp.
  • the chat system prompt is NOT prepended. The live path's prompt injects the REAL host's
    Active Library, which would ground the model in the operator's actual VMs while the
    planner grounds it in the sim's — two contradicting states. The planner supplies its own
    node system prompt and sim-state context, which is the part under test.
Everything else (tool narrowing, findings, contract gate, verified completion) is live.
"""
import argparse
import json
import sys
from typing import Dict, List

import requests

from orchestrator.ai.chat.ollama_client import OLLAMA_URL, _OLLAMA

# PINNED, deliberately: the config's model, NOT the OLLAMA_MODEL env override the shell may
# carry. A ladder number is only meaningful against the model the previous numbers were run
# on — an ambient env var silently swapping the model would make every comparison a lie.
# Pass --model to compare a different one on purpose.
BENCH_MODEL = _OLLAMA["model"]
from orchestrator.ai.planner.autonomous import run_autonomous, make_tool_selector
from orchestrator.ai.tools import TOOLS

from .rungs import RUNGS
from .sim_world import SimWorld


def make_call_model(model: str, temperature: float, timeout: int):
    """The planner's call_model: a raw Ollama chat call with the offered tool set."""
    def call_model(messages: List[Dict], tools: List[Dict] = None) -> Dict:
        payload = {"model": model, "messages": messages,
                   "tools": TOOLS if tools is None else tools, "stream": False,
                   "options": {"temperature": temperature, "num_ctx": _OLLAMA["num_ctx"]}}
        resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    return call_model


def run_rung(rung, call_model, verbose: bool = False, diag: bool = False,
             paraphrase: bool = False) -> Dict:
    """One run of one rung against a FRESH world. Returns the row the report prints."""
    goal = (rung.paraphrase or rung.goal) if paraphrase else rung.goal
    world = SimWorld()
    if rung.setup:
        rung.setup(world)                # starting state; part of the problem, not scaffolding
        world.calls.clear()              # …so it isn't charged to the run's call count
    on_node = (lambda e: print(f"   · {e.get('kind'):5} {str(e.get('goal'))[:70]}")) if verbose else None
    r = None
    try:
        r = run_autonomous(
            goal,
            call_model=call_model,
            execute=world.execute,
            tools=TOOLS,
            vms_getter=world.vms_getter,
            select_tools=make_tool_selector(),   # the live path's per-node narrowing
            on_node=on_node,
            reward=10.0,          # an operator-scale reward, so the CE gate isn't the thing under test
        )
        root = (r.get("root") or {})
        status, disposition = root.get("status"), r.get("disposition")
    except Exception as e:                       # a crash is a result, not a stopped benchmark
        status, disposition = "error", f"{type(e).__name__}: {e}"
    if diag:
        _dump(rung, world, r)
    calls = len(world.calls)
    return {"rung": rung.n, "name": rung.name, "passed": bool(rung.check(world)),
            "status": status, "disposition": disposition,
            "calls": calls, "vms": len(world.vms), "nets": len(world.nets),
            "minimum": rung.minimum, "best": rung.best,
            # A cost REGRESSION is a separate verdict from pass/fail, deliberately: the
            # checker grades the world, and a rung that reaches the right world by a more
            # expensive route is still correct — just worse. Reporting them together would
            # invite tuning the harness to make a number go down, which is the one thing
            # the standing principle forbids.
            "cost_regressed": bool(rung.best is not None and calls > rung.best),
            "world": world.summary()}


def _dump(rung, world, result) -> None:
    """Everything needed to see WHY a rung failed: the calls it made, the state it left,
    and the plan tree with each node's verdict. A failing rung is only useful if the
    failure is legible."""
    print("\n   ── tool calls ──")
    for i, c in enumerate(world.calls, 1):
        print(f"   {i:3} {c['tool']:20} {json.dumps(c['args'])[:80]}")
    print("   ── world ──")
    for n, v in sorted(world.vms.items()):
        print(f"   {n}: status={v['status']} labels={sorted(v['labels'])} nets={sorted(v['nets'])}")
    print(f"   networks: {sorted(world.nets)}  |  CHECK={rung.check(world)}")
    if not result:
        return
    print("   ── plan tree ──")

    def walk(n, d=0):
        extra = n.get("reason") or n.get("satisfied") or ""
        print("   " + "  " * d + f"[{n.get('status')}] {str(n.get('goal'))[:72]}"
              + (f"  ({extra})" if extra else ""))
        for c in (n.get("children") or []):
            walk(c, d + 1)
    walk(result.get("root") or {})
    for f in (result.get("plans_failed") or []):
        print(f"   failed-plan: {f['why'][:100]}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Gorgon planner complexity ladder")
    p.add_argument("-r", "--rung", type=int, action="append", help="rung(s) to run (default: all)")
    p.add_argument("-n", "--runs", type=int, default=1, help="runs per rung (variance)")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("--timeout", type=int, default=_OLLAMA.get("timeout", 300))
    p.add_argument("-v", "--verbose", action="store_true", help="stream plan-tree nodes")
    p.add_argument("--json", action="store_true", help="emit rows as JSON")
    p.add_argument("-p", "--paraphrase", action="store_true",
                   help="run each rung's PARAPHRASE — same capability, different wording. "
                        "A gap between the two columns is a pattern masquerading as an ability.")
    p.add_argument("--cost-gate", action="store_true",
                   help="exit non-zero (2) when a rung exceeds its best measured cost, "
                        "even if every rung passes. For CI.")
    p.add_argument("-d", "--diag", action="store_true",
                   help="dump calls, final world and the plan tree for each run")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, a.timeout)
    print(f"ladder · model={a.model} temp={a.temp} runs={a.runs}\n")

    rows = []
    for rung in rungs:
        shown = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        print(f"── rung {rung.n} ({rung.name}) — {rung.why}\n   goal: {shown}")
        for i in range(a.runs):
            row = run_rung(rung, call_model, a.verbose, a.diag, a.paraphrase)
            rows.append(row)
            mark = "PASS" if row["passed"] else "FAIL"
            print(f"   [{mark}] run {i+1}/{a.runs} · {row['status']}/{row['disposition']} · {row['world']}")
            if row["best"] is not None:
                flag = "  <== COST REGRESSION" if row["cost_regressed"] else ""
                print(f"          cost: {row['calls']} calls "
                      f"(minimum {row['minimum']}, best measured {row['best']}){flag}")
        print()

    print("── summary")
    for rung in rungs:
        got = [r for r in rows if r["rung"] == rung.n]
        n_ok = sum(1 for r in got if r["passed"])
        cost = ""
        if got and got[0]["best"] is not None:
            cheapest = min(r["calls"] for r in got)
            cost = f"   cost {cheapest} (min {got[0]['minimum']}, best {got[0]['best']})"
            if any(r["cost_regressed"] for r in got):
                cost += "  REGRESSED"
        print(f"   rung {rung.n} {rung.name:17} {n_ok}/{len(got)}{cost}")

    regressed = sorted({r["rung"] for r in rows if r["cost_regressed"]})
    if regressed:
        print(f"\n   COST REGRESSION on rung(s) {', '.join(map(str, regressed))} — "
              f"the world is still correct, the route to it got more expensive.")
        print("   Investigate before treating the ladder score as unchanged; do NOT "
              "special-case a rung to bring the number back down.")
    if a.json:
        print(json.dumps(rows, indent=2))
    # Correctness decides the exit code. Cost regressions are reported loudly but do not
    # fail the run on their own unless --cost-gate is set (for CI, where silence is the
    # failure mode that let rung 4 drift from 17 to 35 unnoticed).
    if not all(r["passed"] for r in rows):
        return 1
    return 2 if (a.cost_gate and regressed) else 0


if __name__ == "__main__":
    sys.exit(main())
