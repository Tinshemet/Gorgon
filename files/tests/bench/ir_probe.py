"""
ir_probe.py — can the local model emit valid IR for the ladder's goals?

This is the one step the design note says carries real risk. Everything else about the
procedure language is cheap or reversible; this is the bet. If llama3.1:8b can emit
well-formed, grounded IR for rungs 4-7, thirty-three vocabularies collapse into one
schema. If it cannot, we learn it for the price of an afternoon rather than two weeks,
and the Python-shaped front-end remains available — feeding the SAME IR, so nothing
downstream changes.

It grades the two questions a machine can answer, and refuses to guess at the third:

    WELL-FORMED   right shape? (ir.validate — structure)
    GROUNDED      real tools, real kinds, no dangling $refs? (ir.validate — catalog)
    MEANINGFUL    does it say what the goal meant?  <- printed, never scored

The third is deliberately left to a human reading the rendered program. Scoring it
automatically would need a second definition of what each goal means, and disagreeing
with itself is how a benchmark starts measuring its own grader. The renderer exists so
that reading is quick.

Run:  PYTHONPATH=. python3 -m tests.bench.ir_probe              # rungs 4-7, literal
      PYTHONPATH=. python3 -m tests.bench.ir_probe -p           # paraphrase wording
      PYTHONPATH=. python3 -m tests.bench.ir_probe -r 4 -n 3    # variance on one rung
"""
import argparse
import json
import sys

from orchestrator.ai.planner.ir import (
    EMIT_PROGRAM_TOOL, coerce_body, render, system_prompt, validate)
from orchestrator.ai.planner.ir import config as ir_config
from orchestrator.ai.planner.score import _first_tool_call

from .ladder import BENCH_MODEL, make_call_model
from .sim_world import SimWorld
from .rungs import RUNGS

# The tools offered to the model: exactly what the sim world can actually run, read off
# SimWorld's own handlers. This was a hand-written list of thirteen names, which could
# drift from the world it is supposed to describe — and a probe offering an unrunnable
# tool measures the wrong thing while looking like a model failure.
_SIM_TOOLS = SimWorld.tools()


def _system() -> str:
    """The prompt, assembled from the IR manifest — see ir/config/ir.defaults.json.

    Deliberately NOT written here: the prompt and the validator must describe the same
    language, and the only way to guarantee that is to build both from one table."""
    return system_prompt(_SIM_TOOLS)


def _attempt(messages, call_model) -> tuple:
    """(body, why_not) for one model call."""
    try:
        name, args = _first_tool_call(call_model(messages, [EMIT_PROGRAM_TOOL]))
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if name != "emit_program":
        return None, f"called {name!r}, not emit_program"
    body = coerce_body(args)
    return (body, None) if body is not None else (None, "no statements")


def probe(goal: str, call_model, retries: int = 1) -> dict:
    """One goal -> one row: the program, whether it validates, and why not.

    On an invalid program the VALIDATION ERRORS ARE FED BACK and the model tries again.
    Not a probe convenience — it is how the design says the real path works: an invalid
    program is "rejected before execution, a plan failure not a crash", which routes to
    the existing revision loop with the reason attached. Measuring only the first attempt
    would understate the system by leaving out its correction step.
    """
    messages = [{"role": "system", "content": _system()},
                {"role": "user", "content": goal}]
    attempts = []
    for i in range(retries + 1):
        body, why = _attempt(messages, call_model)
        if body is None:
            attempts.append({"valid": False, "why": why, "body": None})
            if i < retries:
                messages.append({"role": "user", "content":
                     ir_config.PROMPT["retry_no_program"]})
            continue
        ok, problems = validate({"body": body})
        attempts.append({"valid": ok, "problems": problems, "body": body, "n": len(body)})
        if ok or i == retries:
            break
        messages.append({"role": "user", "content":
ir_config.PROMPT["retry_rejected"] + "\n"
                         + "\n".join(f"  - {x}" for x in problems)
                         + "\n" + ir_config.PROMPT["retry_fix"]})
    last = attempts[-1]
    return {"emitted": last.get("body") is not None, "why": last.get("why"),
            "valid": last.get("valid", False), "problems": last.get("problems", []),
            "body": last.get("body"), "n": last.get("n", 0),
            "tries": len(attempts), "first_ok": attempts[0].get("valid", False)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Can the local model emit valid IR?")
    p.add_argument("-r", "--rung", type=int, action="append", help="rung(s), default 4-7")
    p.add_argument("-n", "--runs", type=int, default=1, help="runs per goal (variance)")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("-p", "--paraphrase", action="store_true",
                   help="use each rung's paraphrase — the honest column")
    p.add_argument("--retries", type=int, default=1,
                   help="feed validation errors back and retry (default 1) — the design's "
                        "own path: a rejected program is a plan failure, not a crash, and "
                        "routes to revision with the reason attached.")
    p.add_argument("--json", action="store_true", help="dump the raw programs")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if r.n in (a.rung or [4, 5, 6, 7])]
    call_model = make_call_model(a.model, a.temp, 300)
    print(f"IR probe · model={a.model} temp={a.temp} runs={a.runs}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}\n")

    emitted = valid = total = first_ok = 0
    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        print(f"── rung {rung.n} ({rung.name})\n   goal: {goal}")
        for i in range(a.runs):
            row = probe(goal, call_model, retries=a.retries)
            total += 1
            if not row["emitted"]:
                print(f"   [NO PROGRAM] run {i+1}: {row['why']}")
                continue
            emitted += 1
            mark = "VALID" if row["valid"] else "INVALID"
            tries = "" if row["tries"] == 1 else f" · {row['tries']} tries"
            print(f"   [{mark}] run {i+1}/{a.runs} · {row['n']} statements{tries}")
            if row["valid"]:
                valid += 1
            if row["first_ok"]:
                first_ok += 1
            for why in row["problems"][:6]:
                print(f"          - {why}")
            # The rendered form is the point: read it and judge whether it MEANS the goal.
            for line in render({"body": row["body"]}).splitlines():
                print(f"          | {line}")
            if a.json:
                print(json.dumps(row["body"], indent=2))
        print()

    print("── summary")
    print(f"   emitted a program    : {emitted}/{total}")
    print(f"   valid on FIRST try   : {first_ok}/{total}")
    print(f"   valid after feedback : {valid}/{total}")
    print("\n   Whether each one MEANS its goal is not scored here — read the rendered\n"
          "   programs above. Grading that automatically needs a second definition of\n"
          "   every goal, which is how a benchmark starts measuring its own grader.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
