"""repair_ab.py — A/B two versions of the extractor's REPAIRS on identical model answers.

WHY THIS EXISTS RATHER THAN RUNNING THE PROBE TWICE. Temperature 0 is not deterministic —
`pinned.py` records that — so two probe runs differ by the model as well as by the code, and
attributing the difference to your change is exactly the mistake
[[ladder-is-not-a-feedback-loop]] names. Here ONE model call per cell feeds BOTH arms, so the
only difference between them is `to_goals`.

IT ALSO HALVES THE GPU TIME, which is the smaller reason and the one that gets noticed first.

    OLD=/path/to/old/extract.py PYTHONPATH=. python3 -m tests.bench.repair_ab 3

`OLD` is any earlier copy of `tests/bench/extract.py` — `git show <rev>:./tests/bench/
extract.py > /tmp/old.py` — with its relative imports rewritten (see `_load`). The point is
to compare against a version that was MEASURED, not against your memory of one.

WHAT TO READ. The PASS delta is the headline and the FLIP TABLE is the answer: a change that
moves cells from EXTRACT_WRONG to PASS is doing what it claims, one that moves PASS to
anything is a regression whatever the total says, and one that moves CHECKER_FAIL to
EXTRACT_EMPTY is usually the most valuable of all — that is a case where the model hedged and
the old code ACTED on the hedge.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import Counter

from planner.ghost_writer import Unsolvable, as_program, cover
from planner.ir import run as _run
from planner.ir import validate as _validate
from engines import extract as NEW
from tests.bench.rungs import RUNGS
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld


def _load(path: str):
    """An older `extract.py`, imported standalone.

    Its `from . import pinned` lines cannot resolve outside the package, so they are rewritten
    to absolute ones in memory. Editing the file on disk would be worse: the whole value of
    this comparison is that the old arm is the code that was measured, unmodified.
    """
    src = open(path).read()
    src = re.sub(r"^from \.(\w+) import", r"from tests.bench.\1 import", src, flags=re.M)
    src = re.sub(r"^from \. import", "from tests.bench import", src, flags=re.M)
    spec = importlib.util.spec_from_loader("extract_old", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__["__file__"] = path
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def grade(goals, rung) -> str:
    """One outcome code for one conversion. The same ladder the probe uses."""
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    if not goals:
        return "EXTRACT_EMPTY"
    try:
        plan = cover(goals, world)
    except Unsolvable:
        return "EXTRACT_WRONG"
    except Exception as exc:
        return f"CRASHED:{type(exc).__name__}"
    program = as_program(plan, goals, world)
    ok, _problems = _validate(program, known_names=world.names())
    if not ok:
        return "WRITER_INVALID"
    select, holds = seams(world)
    result = _run(program, world.execute, select=select, holds=holds,
                  known_names=world.names(), consent=True, intent="achieve")
    if not result["ok"]:
        return "GOAL_UNMET"
    return "PASS" if rung.check(world) else "CHECKER_FAIL"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repeats", nargs="?", type=int, default=3)
    ap.add_argument("--old", default=os.environ.get("OLD"))
    ap.add_argument("-r", "--rung", type=int, action="append")
    ap.add_argument("--capture", metavar="PATH",
                    help="also write every raw model answer to PATH as JSONL — a corpus the "
                         "repairs can be replayed against with NO MODEL, forever")
    a = ap.parse_args(argv)
    if not a.old:
        print("REFUSING TO RUN: --old (or $OLD) must name an earlier extract.py. "
              "Comparing against nothing is not a comparison.")
        return 2

    OLD = _load(a.old)
    tally = {"old": Counter(), "new": Counter()}
    flips = []
    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]

    for para in (False, True):
        column = "para" if para else "lit "
        for rung in rungs:
            text = (rung.paraphrase or rung.goal) if para else rung.goal
            for i in range(a.repeats):
                try:
                    raw = NEW.extract(text)
                except Exception as exc:
                    print(f"{column} rung {rung.n} [{i + 1}] EXTRACT ERROR {exc}")
                    continue
                before = grade(OLD.to_goals(raw, text), rung)
                after = grade(NEW.to_goals(raw, text), rung)
                tally["old"][before] += 1
                tally["new"][after] += 1
                if before != after:
                    flips.append((column, rung.n, i + 1, before, after, json.dumps(raw)))
                if a.capture:
                    # EVERY ANSWER, NOT JUST THE INTERESTING ONES. A corpus of only the cells
                    # that flipped would be a corpus of the cases that already worked out —
                    # exactly the sample that cannot catch the next regression.
                    with open(a.capture, "a") as fh:
                        fh.write(json.dumps({"rung": rung.n, "column": column.strip(),
                                             "request": text, "raw": raw,
                                             "outcome": after}) + "\n")
                print(f"{column} rung {rung.n:>2} [{i + 1}/{a.repeats}] "
                      f"old={before:<14} new={after:<14}"
                      + ("  <-- FLIP" if before != after else ""), flush=True)

    print("\n── A/B on identical raw answers")
    print(f"  old: {dict(sorted(tally['old'].items()))}")
    print(f"  new: {dict(sorted(tally['new'].items()))}")
    print(f"  PASS  old {tally['old']['PASS']}  ->  new {tally['new']['PASS']}")
    lost = [f for f in flips if f[3] == "PASS"]
    print(f"  REGRESSIONS (a cell that used to pass): {len(lost)}")
    kinds = Counter(f"{f[3]} -> {f[4]}" for f in flips)
    print(f"\n  {len(flips)} cell(s) changed:")
    for shape, n in kinds.most_common():
        print(f"    {n:3}  {shape}")
    for column, n, i, before, after, raw in flips:
        print(f"\n    {column} rung {n} [{i}]  {before} -> {after}\n        {raw[:220]}")
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
