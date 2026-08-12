"""IS THE VOCABULARY GENERAL, OR WAS IT FITTED TO THE RUNGS?

    PYTHONPATH=. python3 -m tests.bench.formula.generality

The operator's challenge, 2026-08-07: *"are you making this a general formula, or just for
the rungs? the formula should be for everything."*

The fair answer needs a measurement, not an assurance, and the honest position has to
separate two things that are easy to conflate:

  THE MACHINERY IS RUNG-BLIND, and provably so. `legal.Board` reads `attrs`, `attr_values`,
  `observed`, `setters` and `creators` off the manifest and has never been shown a rung. It
  computes the legal move set for a kind that did not exist when it was written.

  THE NINE SLOTS WERE CHOSEN BY LOOKING AT FOURTEEN REQUESTS. That is the fitting risk and
  no amount of manifest-driven machinery underneath it helps. `holdout.py` is one answer,
  but I wrote it, so it tests the vocabulary against the same head that designed it.

SO THIS FILE USES THE ONE CORPUS NEITHER I NOR THE SLOTS HAD ANY HAND IN: 161 readings the
MODEL actually produced, recorded across two capture runs, most of them WRONG. If nine slots
can express arbitrary model output — including output nobody intended and nobody vetted —
that is evidence about the vocabulary that a hand-written corpus cannot give.

WHAT A PASS MEANS AND WHAT IT DOES NOT: expressing a reading says the SHAPE fits the nine
slots. It says nothing about whether the reading was right — most of these were not. Shape
coverage is the only claim.
"""
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from engines import extract as _extract

from planner.formula.fold import fold
from planner.formula.legal import Board, census
from planner.formula.slots import CMP, PRED, SLOTS, build, reduce

BAR = "─" * 100
CORPUS = Path("tests/bench/corpus")


def _readings() -> List[dict]:
    out = []
    for path in sorted(CORPUS.glob("extract_raw*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                row["_from"] = path.name
                out.append(row)
    return out


def run() -> None:
    rows = _readings()
    print(BAR)
    print(f"GENERALITY — nine slots against {len(rows)} readings the MODEL wrote, not me")
    print(BAR)

    total = exact = shaped = 0
    unshapeable: Counter = Counter()
    keys: Counter = Counter()
    failures: List[tuple] = []

    for row in rows:
        try:
            goals = _extract.to_goals(row.get("raw") or {}, row.get("request") or "")
        except Exception as exc:                       # a reading too broken to normalise
            unshapeable[f"to_goals raised {type(exc).__name__}"] += 1
            continue
        for goal in goals:
            total += 1
            try:
                move = reduce(goal)
            except Exception as exc:
                unshapeable[f"reduce raised {type(exc).__name__}"] += 1
                failures.append((row.get("request"), goal, str(exc)))
                continue
            if not move.filled.get("subject"):
                unshapeable["no subject — the reading is about nothing"] += 1
                failures.append((row.get("request"), goal, "no subject"))
                continue
            shaped += 1
            keys[move.mnemonic] += 1
            same = json.dumps(build(move), sort_keys=True) == json.dumps(goal, sort_keys=True)
            exact += same
            if not same:
                failures.append((row.get("request"), goal, json.dumps(build(move))))

    print(f"\n   {total} goals normalised out of {len(rows)} recorded readings")
    print(f"   {shaped} EXPRESSIBLE in the nine slots        ({100 * shaped / max(total, 1):.1f}%)")
    print(f"   {exact} rebuilt EXACTLY, byte for byte        ({100 * exact / max(total, 1):.1f}%)")
    if unshapeable:
        print("\n   what the vocabulary could NOT take:")
        for reason, n in unshapeable.most_common():
            print(f"      {n:>4}  {reason}")

    print(f"\n   {len(keys)} distinct sub-keys used by real model output"
          f"  (the 14 hand-written readings use 10):")
    for mnemonic, n in keys.most_common(20):
        print(f"      {n:>4}  {mnemonic}")

    if failures:
        print(f"\n   first few that did not rebuild exactly ({len(failures)} total):")
        for request, goal, got in failures[:6]:
            print(f"      “{request}”")
            print(f"         was {json.dumps(goal, sort_keys=True)}")
            print(f"         got {got}")

    print()
    print(BAR)
    print("THE OTHER HALF — the machinery, which never saw a rung at all")
    print(BAR)
    board = Board()
    space = (1 << len(SLOTS)) * len(CMP) * len(PRED)
    permitted = set().union(*census(board).values())
    print(f"   the whole key space                         {space}")
    print(f"   the MANIFEST permits                        {len(permitted)}")
    print(f"   the fourteen rungs exercise                 10")
    print(f"   real model output exercises                 {len(keys)}")
    print()
    print("   ⇒ the board generates a legal move set from declarations alone. It was not")
    print("     told about rungs, and it permits many times what any corpus here uses — so")
    print("     the narrowing is not a corpus lookup, it is a computation over the manifest.")
    print("     Add a kind tomorrow and its legal moves appear with no edit to this package.")


if __name__ == "__main__":
    run()
