"""
export_drafts.py — the Medusa a failing cell ACTUALLY writes, before anything repairs it.

`export_failures.py` reports the program a run SCORED, which is the last one produced. That
is often not what the model wrote, and the difference has already cost two wrong diagnoses:

  * para:8's scored program puts app1/app2/app3 on dmz. THE DRAFT PUTS db ON dmz, correctly
    — the repair loop inverted it while answering an objection about something else.
  * lit:8 scores as "no program" because the decoder breaks. There IS a reply; it simply
    does not parse, and the bytes are worth reading.

So this re-authors each cell ONCE and renders the first draft, with no repair, no revision
and no sanitiser. When the draft does not parse it prints the RAW REPLY instead of a blank,
because for a channel failure the raw bytes are the evidence.

It calls the model, so it is not free and it is not deterministic — one draft is a sample,
not a verdict. Read it for SHAPE, and take pass rates from the ladder.

Run:  PYTHONPATH=. python3 -m tests.bench.export_drafts -o drafts.md
      PYTHONPATH=. python3 -m tests.bench.export_drafts -c para:8 -c lit:8
"""
import argparse
import json
import sys
import urllib.request
from typing import List, Optional, Tuple

from orchestrator.ai.planner.ir import render, validate

from . import pinned
from .author_probe import _OLLAMA, _OLLAMA_CTX, _messages, program_schema
from .ladder import BENCH_MODEL
from .rungs import RUNGS
from .sim_world import SimWorld

# The cells the ladder currently scores 0/3. Listed rather than discovered so this stays
# runnable against a build where a cell has gone green — the point is to look at specific
# failures, and a list that silently empties would look like success.
FAILING = ["lit:8", "para:8", "para:9", "para:7", "para:11", "lit:13", "para:13"]


def draft(rung, paraphrase: bool, model: str, timeout: int = 300) -> Tuple[Optional[dict], str]:
    """One authoring call, NO repair. Returns (program or None, raw content).

    Deliberately bypasses `author()`: that function sanitises and can repair, and both
    would hide the thing this file exists to show.
    """
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
        world.calls.clear()
    goal = (rung.paraphrase or rung.goal) if paraphrase else rung.goal
    req = {"model": model, "stream": False,
           "format": program_schema("achieve", world.names()),
           "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(),
           "messages": _messages(goal, True, world, "achieve")}
    r = urllib.request.urlopen(urllib.request.Request(
        _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
        timeout=timeout)
    raw = json.loads(r.read())["message"]["content"]
    try:
        return json.loads(raw), raw
    except ValueError:
        return None, raw


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="First-draft Medusa for each failing cell")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-c", "--cell", action="append", help="e.g. para:8 (default: all failing)")
    p.add_argument("-o", "--out", default="drafts.md")
    a = p.parse_args(argv)

    cells = a.cell or FAILING
    by_rung = {r.n: r for r in RUNGS}
    out: List[str] = []
    w = out.append
    w("# What each failing cell writes — the FIRST DRAFT")
    w("")
    w("One authoring call per cell, **no repair, no revision, no sanitiser**. This is the "
      "model's own program. The ladder scores what comes out the far end of the repair "
      "loop, which for `para:8` is a different and worse program.")
    w("")
    w("A single draft is a SAMPLE, not a pass rate — temp 0 is not deterministic here. "
      "Read it for shape; take rates from the ladder.")
    w("")

    for cell in cells:
        col, _, num = cell.partition(":")
        rung = by_rung.get(int(num))
        if not rung:
            continue
        para = col == "para"
        goal = (rung.paraphrase or rung.goal) if para else rung.goal
        print(f"  authoring {cell} …", flush=True)
        try:
            prog, raw = draft(rung, para, a.model)
        except Exception as exc:
            w(f"## {cell} — rung {rung.n}, {rung.name}\n")
            w(f"**ERROR:** `{type(exc).__name__}: {exc}`\n")
            w("---\n")
            continue

        w(f"## {cell} — rung {rung.n}, {rung.name}")
        w("")
        w(f"**Tests:** {rung.why}")
        w("")
        w(f"**Goal:** {goal}")
        w("")
        if prog is None:
            w("**The draft does not parse.** No Medusa exists — this is the channel "
              "failure, and the raw reply is the evidence:")
            w("")
            w("```")
            w(raw if len(raw) < 1600 else raw[:1600] + "\n…truncated…")
            w("```")
            w("")
            w(f"_{len(raw)} bytes returned._")
        else:
            body = prog.get("body") or []
            ok, problems = validate(prog)
            w(f"**Medusa** ({len(body)} statements, validator: "
              f"{'VALID' if ok else 'INVALID'}):")
            w("")
            w("```")
            w(render(prog).rstrip())
            w("```")
            if problems:
                w("")
                w("**Objections on this draft:**")
                w("")
                for pr in problems:
                    w(f"- `{pr}`")
            w("")
            w("<details><summary>as stored (IR)</summary>")
            w("")
            w("```json")
            w(json.dumps(body, indent=1))
            w("```")
            w("")
            w("</details>")
        w("")
        w("---")
        w("")

    open(a.out, "w").write("\n".join(out) + "\n")
    print(f"wrote {a.out} · {len(cells)} cell(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
