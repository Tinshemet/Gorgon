"""coverage_probe.py — can the front seam SAY what a request means? Nothing runs.

    PYTHONPATH=. python3 -m tests.bench.coverage_probe [-n 3] [-v] [--only decline]

WHAT THIS MEASURES THAT THE LADDER DOES NOT. The ladder asks "did the world end up right",
over 14 requests written to the shapes the goal language already has. This asks "could the
request be stated at all", over a corpus written from the domain — including rows I believe
are UNSTATEABLE. See `coverage_corpus` for why a third of it is meant to be impossible.

THREE BUCKETS, AND ONLY ONE OF THEM IS BAD:

    TRANSLATED   goals came back and they mean the request
    DECLINED     no goals, and a reason — the system saying what it cannot say
    FORCED       goals came back and they do NOT mean the request

FORCED IS THE HEADLINE. It is the precursor of DONE_BUT_FALSE: a request bent into the
nearest shape, which then plans, runs and closes DONE over a world nobody asked for. A high
DECLINED count is not a failure — it is the map of the vocabulary's edge, and it is only
worth having because the corpus contains rows that SHOULD land there.

HOW "MEANS THE REQUEST" IS DECIDED WITHOUT A JUDGE. Two questions, both answerable from data
written before any run:

    SHAPES   does the reading make the claim the English makes? A request to snapshot each
             member is a `per`; read as a `count` it is a different request.
    NAMES    every identifier the request states must appear, and none that it does not.
             An invented name is the failure mode `extract._not_an_identity` and the
             `unusable` guards exist for, seen from the outside.

Neither is a model call and neither is an opinion formed after seeing the output.

TEMPERATURE 0 IS NOT DETERMINISTIC — `pinned.py` records it — so `-n` repeats and a row is
reported by its WORST outcome across the repeats. A request that translates twice and is
forced once is a request that can be forced.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from typing import Any, Dict, List

from engines.extract import declined, extract, to_goals
from tests.bench.coverage_corpus import CORPUS

TRANSLATED, DECLINED, FORCED, BROKE = "TRANSLATED", "DECLINED", "FORCED", "BROKE"

# WORST FIRST. A row is reported by the worst thing it did across repeats, so the summary
# cannot be improved by a lucky sample.
_RANK = {BROKE: 0, FORCED: 1, DECLINED: 2, TRANSLATED: 3}


def shapes_of(goals: List[Dict[str, Any]]) -> set:
    """Which goal shapes a reading used. `shape` for the predicate forms, the key itself for
    the component forms — the same split `ghost_writer._short` reads."""
    out = set()
    for g in goals or ():
        for word in ("every", "per", "observe"):
            if word in g:
                out.add(word)
        if g.get("shape"):
            out.add(g["shape"])
    return out


def names_of(goals: List[Dict[str, Any]]) -> set:
    """Every identifier a reading commits to.

    THE KEY AND THE REFERENCES, which is the same convention `unusable` and `_named_in`
    already use: a kind's key IS a member's name, and an attribute named for a kind refers to
    a member of it. A membership list names several.
    """
    from planner.ir import config
    out: set = set()

    def _add(v: Any) -> None:
        if isinstance(v, dict) and isinstance(v.get("in"), list):
            for one in v["in"]:
                _add(one)
        elif isinstance(v, str) and v.strip():
            out.add(v.strip().lower())

    for g in goals or ():
        for holder in ("select", "every", "observe", "per"):
            sel = g.get(holder)
            if not isinstance(sel, dict):
                continue
            kind = sel.get("kind")
            key = ((config.KINDS or {}).get(kind) or {}).get("key")
            for attr, value in sel.items():
                if attr == key or attr in (config.KINDS or {}):
                    _add(value)
        must = g.get("must")
        if isinstance(must, dict):
            for attr, value in must.items():
                if attr in (config.KINDS or {}):
                    _add(value)
    return out


def judge(row: Dict[str, Any], goals: List[Dict[str, Any]], cannot,
          dropped: List[str] = None) -> tuple:
    """`(bucket, why)` for one reading of one request."""
    if not goals:
        # DECLINING IS AN ANSWER, and a bare empty result is not the same thing. A reading
        # that returns nothing and says nothing has not declined — it has failed silently,
        # which is the one outcome that must not be counted as honesty.
        if cannot:
            return (DECLINED, str(cannot)) if row["expect"] == "decline" else \
                   (DECLINED, f"declined a request I judged stateable: {cannot}")
        # THE PROBE WAS THROWING AWAY THE ANSWER TO ITS OWN QUESTION. `to_goals` records why
        # each component died, and this passed `[]` for that list and then reported "no
        # reason" — so a translation discarded for a specific, nameable cause was displayed
        # identically to a model that said nothing at all. `clone-fleet` read as silence for
        # a whole day; the real cause was the subject guard firing on "the golden IMAGE"
        # with every goal about machines, which `dropped` had said all along.
        #
        # STILL BROKE, and deliberately: the SEAM produced no usable answer either way. What
        # changes is that the line now names which of the two failures it was.
        if dropped:
            return BROKE, f"no goals — {'; '.join(dropped)}"
        return BROKE, "no goals and no reason — silence is not a refusal"

    if row["expect"] == "decline":
        return FORCED, (f"stated a request I judged unstateable, as "
                        f"{sorted(shapes_of(goals))}")

    # A COUNT ABOVE ONE PINNED TO THE KEY CANNOT BE MET, ever: a kind has one member per
    # key, so "two machines called attacker" describes no world. It is not a matter of
    # taste and it is not visible to a shape check — the reading uses the right shape and
    # says something impossible with it.
    from planner.ir import config
    for g in goals or ():
        sel = g.get("select")
        if not isinstance(sel, dict) or not isinstance(g.get("eq"), int) or g["eq"] <= 1:
            continue
        key = ((config.KINDS or {}).get(sel.get("kind")) or {}).get("key")
        if key and isinstance(sel.get(key), str):
            return FORCED, (f"{g['eq']} {sel.get('kind')}s pinned to one "
                            f"{key} ({sel[key]!r}) — no world has that")

    # A REMOVAL THAT DOES NOT ASK FOR ZERO IS THE OPPOSITE OF THE REQUEST, and neither the
    # shape check nor the name check can see it — both pass on the identical goal with the
    # count flipped. That blindness hid a create-on-delete bug: "delete every machine
    # labelled scratch" came back as `count(vm WHERE label=scratch) = 1`, which against a
    # clean lab CREATES a machine and labels it scratch. Scored, before this, as merely the
    # wrong shape. See `coverage_corpus.R`'s `empties`.
    for kind in sorted(row.get("empties") or ()):
        asked = [g for g in goals or ()
                 if g.get("shape") == "count"
                 and ((g.get("select") or {}).get("kind") == kind)]
        if not asked:
            return FORCED, f"nothing here says how many {kind}s must remain"
        if not any(g.get("eq") == 0 for g in asked):
            return FORCED, (f"the request removes {kind}s and this asks for "
                            f"{sorted({g.get('eq') for g in asked})} of them, not 0")

    got_shapes, got_names = shapes_of(goals), names_of(goals)
    missing = row["shapes"] - got_shapes
    if missing:
        return FORCED, (f"read it as {sorted(got_shapes)}, and the request needs "
                        f"{sorted(missing)}")
    invented = {n for n in got_names
                if n not in {x.lower() for x in row["names"]}}
    if invented:
        return FORCED, f"invented {sorted(invented)}"
    lost = {x.lower() for x in row["names"]} - got_names
    if lost:
        return FORCED, f"dropped {sorted(lost)}, which the request names"
    return TRANSLATED, ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--repeats", type=int, default=1)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--only", choices=("translate", "decline"))
    # NAMED ROWS, FOR BISECTING A CHANGE AND NOTHING ELSE. A full n=3 pass is 66 model calls
    # and the better part of an hour, which is too slow to ask "did THIS edit cause THAT
    # regression" — the question every measurement here ends up asking. A subset is not a
    # result and must never be reported as one; the summary says so on its own line.
    ap.add_argument("--rows", help="comma-separated row ids — a bisect, NOT a measurement")
    args = ap.parse_args(argv)

    rows = [r for r in CORPUS if not args.only or r["expect"] == args.only]
    if args.rows:
        want = {r.strip() for r in args.rows.split(",") if r.strip()}
        unknown = want - {r["id"] for r in CORPUS}
        if unknown:
            print(f"no such row: {', '.join(sorted(unknown))}")
            return 2
        rows = [r for r in rows if r["id"] in want]
    verdicts: Dict[str, tuple] = {}
    # HOW OFTEN IT REFUSED WHILE STILL ANSWERING. `rig.translator` returns on a refusal
    # BEFORE it builds goals, so a model that says "I can do this part but not that one" has
    # its goals THROWN AWAY in production — and this probe, which judges on goals, shows
    # nothing at all. Found while measuring the withdrawn span-anchored refusal (2 of 66
    # readings, 2026-08-05) and kept because the seam is unchanged: the discard is a real
    # choice `rig` makes on every request, and a rate nobody counts is a rate nobody knows.
    both = 0
    for row in rows:
        worst = None
        for _ in range(args.repeats):
            try:
                raw = extract(row["request"])
                lost: List[str] = []
                goals = to_goals(raw, row["request"], lost)
                # THE PROBE ASKED THE RAW FIELD AND MUST NOT. It read `raw["cannot"]`
                # directly, which counts a refusal the production seam would throw away —
                # so a change to what COUNTS as a decline would have moved this number
                # without moving anything an operator sees. `declined` is the one authority,
                # and the bench asking a different question than production is the defect
                # this codebase keeps finding under other names.
                said_no = declined(raw)
                if said_no and goals:
                    both += 1
                got = judge(row, goals, said_no, lost)
            except Exception as exc:                    # a seam that cannot answer is not
                got = (BROKE, f"{type(exc).__name__}: {exc}")   # evidence about the model
            if worst is None or _RANK[got[0]] < _RANK[worst[0]]:
                worst = got
        verdicts[row["id"]] = worst
        mark = {TRANSLATED: "ok  ", DECLINED: "said no", FORCED: "FORCED", BROKE: "BROKE"}
        print(f"  {mark[worst[0]]:8} {row['id']:20} {worst[1][:88]}")

    tally = Counter(v[0] for v in verdicts.values())
    stateable = [r for r in rows if r["expect"] == "translate"]
    unstateable = [r for r in rows if r["expect"] == "decline"]
    print(f"\n── coverage · {len(rows)} requests · n={args.repeats}"
          + ("   *** A SUBSET. Not a coverage result." if args.rows or args.only else ""))
    for bucket in (TRANSLATED, DECLINED, FORCED, BROKE):
        if tally.get(bucket):
            print(f"  {tally[bucket]:3}  {bucket}")
    forced = [i for i, v in verdicts.items() if v[0] == FORCED]
    print(f"\n  of {len(stateable)} I judged STATEABLE: "
          f"{sum(1 for r in stateable if verdicts[r['id']][0] == TRANSLATED)} translated")
    print(f"  of {len(unstateable)} I judged UNSTATEABLE: "
          f"{sum(1 for r in unstateable if verdicts[r['id']][0] == DECLINED)} declined")
    if both:
        print(f"  {both} reading(s) refused AND produced goals — which `rig.translator` "
              f"resolves by discarding the goals")
    if forced:
        print(f"\n  *** FORCED is the only unacceptable outcome here: the request was bent "
              f"into a shape it does not fit, and that is what a DONE_BUT_FALSE is made of. "
              f"({', '.join(forced)})")
    return 1 if forced or tally.get(BROKE) else 0


if __name__ == "__main__":
    sys.exit(main())
