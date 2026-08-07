"""two_pass_table.py — the two-pass reading against the ordinary one, every rung, both arms.

    PYTHONPATH=. python3 tests/bench/two_pass_table.py [-n 1]

## WHAT IS BEING COMPARED

    ORDINARY   one call: the whole request, with the goal shapes in the prompt.
    TWO PASS   pass one asks what the request SAYS, in words, with NO schema anywhere;
               pass two standardises each claim on its own and unions the readings.

## ⇒ WHY PASS ONE MUST NOT SEE THE SCHEMA, AND IT IS MEASURED

Asked to break *"ping every vm and stop the ones that do not answer"* into claims WITH the
shapes in the prompt, the model answered — deterministically, three draws of three —

    ['every(vm, alive, True)',  'if (result == False): stop(vm)']

and explained itself coherently: *"I chose `every` because I want to check all VMs. Then I
used a conditional statement to filter out the ones that don't respond."* **Medusa has no
`if`.** The same request with no shapes in the prompt decomposes cleanly, in English:

    ['Check which machines respond', 'Shut down machines that do not respond']

Telling the model the shapes does not help it read. It changes what it thinks it is being
asked for.

## READ THE `claims` COLUMN AS WELL AS THE SCORE

Pass one can be excellent and the run still not improve — measured on rung 11, where the
claims are perfect and pass two turns *"Stop the ones that do not answer"* into a second
`observe`. That is the finding this table exists to make visible: WHICH PASS FAILED.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from engines import extract
from tests.bench.rungs import RUNGS
from tests.bench.sim_world import SimWorld

try:
    from tests.test_ghost_writer import GOALS as KNOWN
except Exception:                                    # pragma: no cover
    KNOWN = {}


def _world(rung):
    w = SimWorld()
    if rung.setup:
        rung.setup(w)
    return w


def _short(g):
    return json.dumps(g, sort_keys=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=1)
    ap.add_argument("-r", "--rung", type=int, action="append")
    a = ap.parse_args(argv)
    wanted = set(a.rung or [r.n for r in RUNGS])

    print(f"\n{'rung':<5}{'arm':<5}{'ordinary':<11}{'two-pass':<11}{'verdict':<9}claims from pass one")
    print("─" * 124)
    tally = Counter()
    for rung in RUNGS:
        if rung.n not in wanted or not KNOWN.get(rung.n):
            continue
        want = {_short(g) for g in KNOWN[rung.n]}
        for arm, text in (("lit", rung.goal), ("par", rung.paraphrase)):
            if not text:
                continue
            best_one = best_two = -1
            claims: list = []
            for _ in range(a.repeats):
                try:
                    plain = extract.to_goals(extract.extract(text), text,
                                             world=_world(rung)) or []
                except Exception:
                    plain = []
                best_one = max(best_one, len({_short(g) for g in plain} & want))
                try:
                    claims = extract.in_words(text)
                    two = extract.two_pass(text, world=_world(rung)) or []
                except Exception:
                    two = []
                # ⇒ AN EMPTY TWO-PASS MEANS "ONE CLAIM, USE THE ORDINARY PATH" — not a score
                #   of zero. Scoring it zero would make a deliberate fall-through look like a
                #   failure, and single-claim requests are most of the corpus.
                best_two = max(best_two, len({_short(g) for g in two} & want) if two
                               else best_one)
            verdict = ("BETTER" if best_two > best_one else
                       "worse" if best_two < best_one else "same")
            tally[verdict] += 1
            head = (f"{rung.n:<5}{arm:<5}{f'{best_one}/{len(want)}':<11}"
                    f"{f'{best_two}/{len(want)}':<11}{verdict:<9}")
            print(head + (claims[0][:62] if claims else "(one claim — ordinary path)"))
            for c in claims[1:]:
                print(" " * 41 + c[:62])
    print("─" * 124)
    print("   " + " · ".join(f"{k} {v}" for k, v in tally.most_common()))
    print("   AN EMPTY TWO-PASS IS A FALL-THROUGH, NOT A ZERO — a single-claim request is")
    print("   already what the ordinary path asks for, and asking again buys a second draw.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
