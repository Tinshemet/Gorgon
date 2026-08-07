"""capture_corpus.py — record what the model REALLY answers, so deterministic code can be
measured without it.

    PYTHONPATH=. python3 -m tests.bench.capture_corpus [-n 3] [-o PATH]

## WHY A FROZEN CORPUS IS WORTH A GPU HOUR

Temperature 0 is not deterministic here, and the ladder's run-to-run noise EXCEEDS the effects
being measured — ±2 cells on byte-identical input, and one rung swung 3/3 false to 5/5 honest
on the same code ([[gorgon-ladder-noise-exceeds-the-effect]]). So two live runs differ by the
MODEL as well as by the CODE, and attributing the difference to your change is the mistake
[[ladder-is-not-a-feedback-loop]] is named after.

A recorded corpus removes the model from the comparison entirely. `to_goals`, the gates and
every repair can then be replayed against exactly what a real model really said, in
milliseconds, on every commit. Gate 1 was measured this way — 32 of 57 — in seconds rather
than an hour, and deterministically.

## WHY THIS EXISTS SEPARATELY FROM `repair_ab.py`

`repair_ab --capture` writes the same rows, but it REFUSES TO RUN without `--old`: it is an
A/B harness and comparing against nothing is not a comparison. Capturing a corpus is not an
A/B — there is only one arm, today's code — so demanding a second one meant the only way to
refresh the corpus was to fake a comparison. This is that job on its own.

## READ THIS BEFORE TRUSTING THE OUTCOME COLUMN

`outcome` is the FULL LADDER's verdict — cover, write, validate, run, then the rung's own
checker — not a judgement about the reading. So:

**A READING THAT DIFFERS FROM THE HAND-WRITTEN `GOALS` CAN STILL PASS, and 15 of 21 do.** The
hand-written table is ONE correct reading, never the only one. Anything comparing against it
is measuring agreement with a fixture, not correctness — which is why the PASS rows here are
the better false-alarm test for a gate.

## AND THE CORPUS IS A SNAPSHOT, NOT A TARGET

It is captured from a run of the CURRENT code, so its numbers are a record rather than a goal.
A later change that moves them has to be READ, not tuned against — commit the corpus, then
change the code ([[gorgon-deterministic-rules]]).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from engines import extract
from tests.bench.repair_ab import grade
from tests.bench.rungs import RUNGS

_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "corpus", "extract_raw.jsonl")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-n", "--repeats", type=int, default=3)
    ap.add_argument("-o", "--out", default=_DEFAULT)
    ap.add_argument("-r", "--rung", type=int, action="append")
    a = ap.parse_args(argv)

    rungs = [r for r in RUNGS if not a.rung or r.n in a.rung]
    # WRITTEN BESIDE THE TARGET AND MOVED AT THE END. A capture that dies halfway through
    # would otherwise leave a HALF corpus under the committed name — and a half corpus reads
    # exactly like a whole one to every replay that follows.
    tmp = a.out + ".partial"
    if os.path.exists(tmp):
        os.remove(tmp)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)

    tally: Counter = Counter()
    total = len(rungs) * 2 * a.repeats
    done = 0
    for para in (False, True):
        column = "para" if para else "lit"
        for rung in rungs:
            text = (rung.paraphrase or rung.goal) if para else rung.goal
            for i in range(a.repeats):
                done += 1
                try:
                    raw = extract.extract(text)
                except Exception as exc:
                    print(f"[{done}/{total}] {column} rung {rung.n} EXTRACT ERROR "
                          f"{type(exc).__name__}: {exc}", flush=True)
                    continue
                try:
                    outcome = grade(extract.to_goals(raw, text), rung)
                except Exception as exc:
                    outcome = f"CRASHED:{type(exc).__name__}"
                tally[outcome] += 1
                with open(tmp, "a") as fh:
                    fh.write(json.dumps({"rung": rung.n, "column": column,
                                         "request": text, "raw": raw,
                                         "outcome": outcome}) + "\n")
                print(f"[{done}/{total}] {column:<5} rung {rung.n:>2} "
                      f"[{i + 1}/{a.repeats}]  {outcome}", flush=True)

    os.replace(tmp, a.out)
    print(f"\n── captured {sum(tally.values())} readings -> {a.out}")
    for outcome, n in tally.most_common():
        print(f"   {n:4} ({100 * n // max(sum(tally.values()), 1):3}%)  {outcome}")
    print("\n  THIS IS A RECORD, NOT A TARGET. A later change that moves these numbers has to")
    print("  be read, not tuned against.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
