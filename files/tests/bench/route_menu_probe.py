"""
route_menu_probe.py — is `new` vs `call` a model limit, or a withheld menu?

THE DEFECT THIS MEASURES. The atomicity router names the right operator 4/10, and the
errors that cost whole rungs are all one shape: it answers `new` for a goal that acts on
something ALREADY THERE. Rung 3's 'put web on lab' produced `NEW vm FROM $web` with the
correct `add_vm_to_network` demoted into the failure branch — a spurious clone from a
program that validated. Rungs 6 and 10 do the same thing.

TWO THINGS THE ROUTER IS NOT TOLD, both of which the AUTHOR already gets:

  SIBLINGS   what earlier steps produced, so it can know a thing already exists. The
             emitter gained exactly this in `50b6b6d` and the pipeline went 0/13 -> 4/13.
  TOOLS      `call`'s entire manifest doc is 36 characters — "invoke one tool. Fields:
             tool, args." — and no tool is ever named. The author is handed all sixteen as
             a schema enum, derived from the world's own handlers. The router gets the
             three words.

So this is the schema-withholding lens pointed at the ROUTER rather than the author: audit
what is offered before calling a low score a ceiling. Four arms, because the interesting
question is not whether each helps but whether they COMPOSE.

    PYTHONPATH=. python3 -m tests.bench.route_menu_probe -n 3

RECORDED 2026-07-29, llama3.1:8b, temp 0, n=3, 7 cells (4 `call`, 3 `new` controls):

    blind 9/21  ·  siblings 12/21  ·  tools 12/21  ·  both 13/21

AND THE TOTAL IS THE LEAST INFORMATIVE PART OF IT. Read the columns:

  * Each aid ALONE is safe and weak — every `new` control held 3/3, and each fixed exactly
    one `call` cell. They fix DIFFERENT ones: siblings got 'launch the last new vm', tools
    got 'move resource to new network'.
  * TOGETHER they fix three of the four `call` cells unanimously — and BREAK TWO CONTROLS.
    'clone golden into a new vm' goes 3/3 `new` -> 0/3 `call`; 'create a vm labelled red'
    goes 3/3 -> 1/3.

So the confusion is SYMMETRIC and prose-tunable in either direction: tell the model more
about acting and it stops creating. That is not a fix, it is a rebalancing of the same
uncertainty, and it is the 0/12 schema-gate lesson in a new costume — guidance that reads
as obviously correct and measures as a trade.

THE READING: `new` vs `call` will not be settled by describing the menu better. It wants a
DISCRIMINATOR that decides structurally, the way the quantifier router decides all/any/
single/not — unrepresentable beats rejected. Nothing here is wired into `tree_probe`; this
file exists to keep the negative result reproducible.
"""
import argparse
import collections
import json
import sys

from planner.ir import config

from . import pinned
from .author_probe import _OLLAMA_CTX, _TOOLS
from .ladder import BENCH_MODEL
from .tree_probe import _ALL_OPS, _post

# goal, the operator that is RIGHT, the parent it sits under, what earlier siblings did.
# The four `call` cells are the measured failures; the three `new` cells are controls, and
# they are the half that catches an aid which merely moves the bias.
CELLS = [
    ("put web on lab", "call",
     "create a network called lab and a vm named web, then put web on lab",
     ["create a network called lab", "create a vm named web"]),
    ("move resource to new network", "call",
     "put the red ones together on their own network",
     ["create a new network for the red resources"]),
    ("launch the new vm", "call",
     "clone golden into 3 new vms and launch all of them",
     ["clone golden into a new vm"]),
    ("launch the last new vm", "call",
     "clone golden into 3 new vms and launch all of them",
     ["clone golden into a new vm", "clone golden into another new vm"]),
    ("create a network called lab", "new",
     "create a network called lab and a vm named web, then put web on lab", []),
    ("create a vm labelled 'red'", "new",
     "create 3 vms labelled 'red' and 2 vms labelled 'blue'", []),
    ("clone golden into a new vm", "new",
     "clone golden into 3 new vms and launch all of them", []),
]

ARMS = (("blind", False, False), ("siblings", True, False),
        ("tools", False, True), ("both", True, True))


def _menu(name_tools: bool) -> dict:
    """The routing tool, with `call` optionally told what a tool IS.

    The tool list is `SimWorld.tools()` by way of `author_probe._TOOLS` — read off the
    world's own handlers, never listed twice, so the router cannot be offered something
    that has no implementation behind it.
    """
    lines = []
    for op in _ALL_OPS:
        doc = (config.OPS[op].get("doc") or "").split(".")[0]
        if op == "call" and name_tools:
            doc += (" — acting on something that ALREADY EXISTS. The tools are: "
                    + ", ".join(_TOOLS))
        lines.append(f"  {op} — {doc}")
    return {"type": "function", "function": {
        "name": "route",
        "description": ("Decide whether a goal is ONE statement or must be broken up.\n"
                        "A loop over a set is ONE statement, not one per member. An "
                        "end-state to make true is ONE statement however much work it "
                        "implies.\n\nThe operators:\n" + "\n".join(lines)),
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


def route(goal, model, parent=None, done=None, siblings=False, name_tools=False):
    """One routing call. Returns the operator named, or None — and None is a CHANNEL
    failure, kept distinct from a wrong answer because they have different owners."""
    content = goal
    if siblings and parent:
        content += f"\n\nThis step is part of: {parent}"
    if siblings and done:
        content += ("\n\nEarlier steps have ALREADY done:\n"
                    + "\n".join(f"  - {d}" for d in done)
                    + "\nSo anything they produced ALREADY EXISTS.")
    reply = _post({"model": model, "stream": False, "tools": [_menu(name_tools)],
                   "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(),
                   "messages": [{"role": "system", "content":
                                 "You are given a goal. Call `route` exactly once."},
                                {"role": "user", "content": content}]})
    for tc in ((reply.get("message") or {}).get("tool_calls") or []):
        args = (tc.get("function") or {}).get("arguments") or {}
        if isinstance(args, str):
            args = json.loads(args)
        return args.get("op")
    return None


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="new-vs-call: menu, not model?")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-n", "--repeats", type=int, default=3)
    a = p.parse_args(argv)

    print(f"route menu probe · model={a.model} · n={a.repeats}\n")
    header = f"{'goal':<32}{'want':<6}" + "".join(f"{n.upper():<14}" for n, _, _ in ARMS)
    print(header)
    score = collections.Counter()
    for goal, want, parent, done in CELLS:
        row = {}
        for name, sib, tools in ARMS:
            got = [route(goal, a.model, parent, done, sib, tools)
                   for _ in range(a.repeats)]
            row[name] = got
            score[name] += sum(1 for o in got if o == want)
            score[f"{name}:channel"] += sum(1 for o in got if o is None)
        score["n"] += a.repeats

        def cell(got):
            hit = sum(1 for o in got if o == want)
            common = collections.Counter(got).most_common(1)[0][0]
            return f"{hit}/{a.repeats} {common}"
        print(f"{goal[:31]:<32}{want:<6}"
              + "".join(f"{cell(row[n]):<14}" for n, _, _ in ARMS))

    print(f"\nCORRECT OPERATOR out of {score['n']}:")
    for name, _, _ in ARMS:
        ch = score[f"{name}:channel"]
        print(f"   {name:<10} {score[name]:>3}"
              + (f"   ({ch} channel failure(s))" if ch else ""))
    print("\nRead the CONTROLS, not the total: an aid that raises the score by trading "
          "\n`new` recall for `call` recall has moved the bias, not removed it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
