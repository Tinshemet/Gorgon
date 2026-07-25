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


def run_rung(rung, call_model, verbose: bool = False, diag: bool = False) -> Dict:
    """One run of one rung against a FRESH world. Returns the row the report prints."""
    world = SimWorld()
    if rung.setup:
        rung.setup(world)                # starting state; part of the problem, not scaffolding
        world.calls.clear()              # …so it isn't charged to the run's call count
    on_node = (lambda e: print(f"   · {e.get('kind'):5} {str(e.get('goal'))[:70]}")) if verbose else None
    r = None
    try:
        r = run_autonomous(
            rung.goal,
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
    return {"rung": rung.n, "name": rung.name, "passed": bool(rung.check(world)),
            "status": status, "disposition": disposition,
            "calls": len(world.calls), "vms": len(world.vms), "nets": len(world.nets),
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
    p.add_argument("-d", "--diag", action="store_true",
                   help="dump calls, final world and the plan tree for each run")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, a.timeout)
    print(f"ladder · model={a.model} temp={a.temp} runs={a.runs}\n")

    rows = []
    for rung in rungs:
        print(f"── rung {rung.n} ({rung.name}) — {rung.why}\n   goal: {rung.goal}")
        for i in range(a.runs):
            row = run_rung(rung, call_model, a.verbose, a.diag)
            rows.append(row)
            mark = "PASS" if row["passed"] else "FAIL"
            print(f"   [{mark}] run {i+1}/{a.runs} · {row['status']}/{row['disposition']} · {row['world']}")
        print()

    print("── summary")
    for rung in rungs:
        got = [r for r in rows if r["rung"] == rung.n]
        n_ok = sum(1 for r in got if r["passed"])
        print(f"   rung {rung.n} {rung.name:17} {n_ok}/{len(got)}")
    if a.json:
        print(json.dumps(rows, indent=2))
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
