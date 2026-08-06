"""hallucination_probe.py — WHAT does the model invent, and how often? A profile, not a score.

Every guard at this seam was built against a hallucination somebody had SEEN — a name from
nowhere, a schema word echoed into a slot, prose where an identity belongs. That is how each
of them ended up narrow, and it is why closing one relocated the pressure rather than removing
it: `reach` -> `per` -> `count` with an invented name, three shapes and one clause
([[gorgon-hallucination-was-load-bearing]]).

**SO THIS COUNTS THE SHAPES BEFORE ANYONE FIXES ONE.** It classifies raw extractor output
against the manifest and the request, deterministically, with no model in the judging — the
only thing a model does here is produce the answers being classified.

    PYTHONPATH=. python3 tests/bench/hallucination_probe.py [-n 2] [--corpus]

WHAT IT CLASSIFIES, and every class is decidable without asking anyone:

    invented-name     a selector commits to an identity the request never contains
    echoed-word       a slot holds a word from the SCHEMA — `every`, `reach`, `count`
    prose             a slot holds a phrase, not an identifier
    unknown-attr      an attribute the kind does not declare
    unknown-value     a value outside the attribute's declared enumeration
    impossible-count  several members pinned to one identity
    unasked-kind      a kind the request never mentions and the world has none of

A SHAPE WITH A HIGH COUNT IS NOT AUTOMATICALLY THE ONE TO FIX. The record's own lesson is
that the pressure moves: a shape that vanishes when another is closed was never the disease.
Read this beside the guards that already fire, not instead of them.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict

from engines import extract
from planner.ir import config
from tests.bench.rungs import RUNGS

_WORD = re.compile(r"[A-Za-z0-9_.-]+")

# THE SCHEMA'S OWN VOCABULARY, read from the schema rather than listed. A slot holding one of
# these is the model handing its instructions back — measured as `name: 'reach'` and
# `name: 'every'`, both of which `_repair_unusable` exists for.
def _schema_words() -> set:
    out = {"count", "every", "per", "observe", "reach", "select", "make", "attr", "value",
           "goal", "amount", "name", "kind", "where", "except"}
    out |= {str(k) for k in (config.KINDS or {})}
    return {w.lower() for w in out}


def _identities(goal: dict):
    """Every value a selector COMMITS TO an identity with, as `(kind, key, value)`."""
    for slot in ("select", "every", "per", "observe"):
        sel = goal.get(slot)
        if not isinstance(sel, dict):
            continue
        kind = sel.get("kind")
        key = ((config.KINDS or {}).get(kind) or {}).get("key")
        if key and isinstance(sel.get(key), (str, int, float)):
            yield kind, key, str(sel[key])


def classify(goal: dict, request: str) -> list:
    """Every hallucination shape in one goal. Deterministic; the manifest is the authority."""
    said = {w.lower() for w in _WORD.findall(request or "")}
    words = _schema_words()
    out = []
    for kind, key, value in _identities(goal):
        low = value.strip().lower()
        if not low:
            continue
        if low in words:
            out.append(("echoed-word", f"{key}={value!r}"))
        elif len(low.split()) > 1:
            out.append(("prose", f"{key}={value!r}"))
        elif low not in said:
            out.append(("invented-name", f"{key}={value!r}"))
    for slot in ("select", "every", "per", "observe"):
        sel = goal.get(slot)
        if not isinstance(sel, dict):
            continue
        spec = (config.KINDS or {}).get(sel.get("kind")) or {}
        attrs = set(spec.get("attrs") or ()) | set((spec.get("aliases") or {}).keys())
        attrs |= set((spec.get("observed") or {}).keys()) | {"kind", "not", "any", "all"}
        for attr, value in sel.items():
            if attr not in attrs:
                out.append(("unknown-attr", f"{sel.get('kind')}.{attr}"))
                continue
            enum = (spec.get("attr_values") or {}).get(attr)
            if enum and isinstance(value, str) and value not in enum:
                out.append(("unknown-value", f"{attr}={value!r}"))
    if isinstance(goal.get("eq"), int) and goal["eq"] > 1:
        for kind, key, value in _identities(goal):
            out.append(("impossible-count", f"{goal['eq']} x {key}={value!r}"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=2)
    ap.add_argument("-r", "--rung", type=int, action="append")
    args = ap.parse_args(argv)

    wanted = set(args.rung or [r.n for r in RUNGS])
    shapes = Counter()
    examples = defaultdict(list)
    goals_seen = draws = 0

    for rung in RUNGS:
        if rung.n not in wanted:
            continue
        for arm, request in (("lit", rung.goal), ("par", rung.paraphrase)):
            if not request:
                continue
            for _ in range(args.repeats):
                try:
                    raw = extract.extract(request)
                except Exception as exc:
                    print(f"  rung {rung.n} {arm}: {type(exc).__name__}")
                    continue
                draws += 1
                # THE RAW ANSWER, before `to_goals` repairs or refuses anything — the point is
                # what the MODEL produced, not what survived the guards.
                for g in (raw or {}).get("goals") or []:
                    if not isinstance(g, dict):
                        continue
                    goals_seen += 1
                    shaped = {"select": extract._to_select(g.get("select") or {}),
                              **{k: v for k, v in g.items() if k != "select"}}
                    for kind, detail in classify(shaped, request):
                        shapes[kind] += 1
                        if len(examples[kind]) < 4:
                            examples[kind].append(f"rung {rung.n} {arm}: {detail}")

    print(f"\n── {draws} draw(s), {goals_seen} goal(s)")
    if not shapes:
        print("   nothing classified — either it is clean or the classifier is blind")
    for kind, count in shapes.most_common():
        share = 100.0 * count / max(1, goals_seen)
        print(f"   {kind:18} {count:4}  ({share:.0f}% of goals)")
        for line in examples[kind]:
            print(f"      {line}")
    print("\n   A HIGH COUNT IS NOT AUTOMATICALLY THE ONE TO FIX. The pressure MOVES: a shape"
          "\n   that vanishes when another is closed was never the disease.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
