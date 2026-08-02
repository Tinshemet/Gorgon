"""
regime_probe.py — does the model REACH for a program when it needs one?

The IR probe forces emission: it offers `emit_program` alone and asks for a program. That
answers "can it", but not the question the architecture actually rests on, which is
whether `emit_program` works as a THIRD META-TOOL beside `decompose` and the primitives.

The engine already makes this exact choice at every node — it offers `decompose`
alongside the primitives, and which the model picks IS the atomicity judgment. Adding
`emit_program` makes it a three-way judgment:

    one tool call        -> a primitive
    several steps        -> decompose
    structure: a set, an ordering, a postcondition   -> emit_program

Two things are graded, and the second matters more than the first:
    ROUTING   did it pick the regime the goal deserves?
    VALIDITY  when it chose a program, was the program any good?

A wrong choice is cheap — an invalid program falls back to decompose, which is the path
that works today. A model that never reaches for a program is not a failure of the
language; it means the regime never engages and the language is dead weight.

Run:  PYTHONPATH=. python3 -m tests.bench.regime_probe
      PYTHONPATH=. python3 -m tests.bench.regime_probe -m qwen2.5:14b
"""
import argparse
import sys

from planner.ir import EMIT_PROGRAM_TOOL, coerce_body, render, validate
from planner.score import DECOMPOSE_TOOL, _first_tool_call

from .ladder import BENCH_MODEL, make_call_model
from .rungs import RUNGS
from .sim_world import SimWorld

# What each rung DESERVES, judged by its shape, written down before any run so the
# grading cannot drift toward whatever the model happened to do.
#   primitive — one tool call and nothing else
#   decompose — several ordered steps, no set and no postcondition
#   program   — a set, a filter, or an end-state to assert
EXPECTED = {1: "primitive", 2: "decompose", 3: "decompose",
            4: "program", 5: "program", 6: "program", 7: "program",
            8: "program", 9: "program", 10: "program"}

_SIM_TOOLS = SimWorld.tools()


def _tool_schemas():
    """The primitives, plus the two meta-tools. Deliberately the same menu the engine
    offers at a node, with emit_program added — nothing about this probe is special."""
    prims = [{"type": "function",
              "function": {"name": t, "description": f"the {t} tool",
                           "parameters": {"type": "object", "properties": {}}}}
             for t in _SIM_TOOLS]
    return prims + [DECOMPOSE_TOOL, EMIT_PROGRAM_TOOL]


def _system() -> str:
    return (
        "You are given a goal and must choose HOW to handle it.\n"
        "  - If it is ONE action, call that tool directly.\n"
        "  - If it is several ordered steps, call `decompose`.\n"
        "  - If it involves a SET of things, a filter, or an end-state that must hold, "
        "call `emit_program` and express it as a program.\n"
        "Choose one. Do not explain."
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Does the model reach for a program?")
    p.add_argument("-r", "--rung", type=int, action="append")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("-p", "--paraphrase", action="store_true")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    call_model = make_call_model(a.model, a.temp, 300)
    tools = _tool_schemas()
    print(f"regime probe · model={a.model} temp={a.temp}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}\n")

    right = programs = valid = 0
    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        want = EXPECTED[rung.n]
        try:
            name, args = _first_tool_call(
                call_model([{"role": "system", "content": _system()},
                            {"role": "user", "content": goal}], tools))
        except Exception as e:
            print(f"   rung {rung.n:2}  ERROR  {type(e).__name__}")
            continue
        got = ("program" if name == "emit_program"
               else "decompose" if name == "decompose"
               else "primitive" if name else "none")
        ok = "OK " if got == want else "   "
        if got == want:
            right += 1
        print(f"   rung {rung.n:2}  want {want:9} got {got:9} {ok} {name or '(no call)'}")
        if got == "program":
            programs += 1
            body = coerce_body(args)
            good, problems = validate({"body": body}) if body else (False, ["no statements"])
            valid += 1 if good else 0
            print(f"            program: {'VALID' if good else 'INVALID'}"
                  f" ({len(body or [])} statements)")
            for why in problems[:3]:
                print(f"              - {why}")
            for line in (render({"body": body}) if body else "").splitlines():
                print(f"              | {line}")

    print(f"\n── summary\n   routed as intended : {right}/{len(rungs)}")
    print(f"   chose a program    : {programs}")
    print(f"   …of those, valid   : {valid}/{programs}" if programs else
          "   …of those, valid   : n/a — the regime never engaged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
