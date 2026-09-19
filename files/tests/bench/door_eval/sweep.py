"""sweep.py — the two RATE numbers in the seal, reproducible.

⇒⇒ **THEY WERE RECORDED WITHOUT A SCRIPT, AND ONE OF THEM WAS WRONG.** The seal carried
*"6,000 sampled dictionary words — 0/6000 · 0.00%"* and *"3,000 random English sentences —
0/3000"* from an ad-hoc measurement in a session. Nothing in the repo reproduced either, so
nothing could contradict them. Re-derived on 2026-09-19 the dictionary sweep is **1/6000**, and
the miss (`stop the anyway vm` -> `stop the, anyway vm`) predates every commit of the last two
days — checked at `9af44f5`. **The number was wrong when it was written and stayed wrong because
it was unfalsifiable.**

⇒ A CORPUS IS A COUNT, A SWEEP IS A RATE, and the seal keeps them in separate rows for a reason:
  the corpus's denominator is the author's imagination, this one's is a defined population.

⇒ WHY IT IS NOT A pytest TEST. It samples thousands of inputs and takes a minute; the properties
  already guard the door per-commit over 608 inputs. This is the instrument that DISCOVERS —
  run it when the closed classes or the veto sets move, and paste what it says into the seal.

    PYTHONPATH=. python3 tests/bench/door_eval/sweep.py
"""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))))

from orchestrator.languages.english.seam import front_door as FD   # noqa: E402

LAB = ("alpha", "beta", "web", "db", "test", "vm2", "core", "lab", "dmz")
DICT_PATH = "/usr/share/dict/american-english"

# ⇒ THE SIX FRAMES ARE THE SLOTS A WORD CAN LAND IN, not decoration: a word is damaged or not
#   DEPENDING ON ITS SLOT, which is the whole design of the sim check. One frame measures one
#   slot and would call the door clean while another tore the same word in half.
FRAMES = ("stop the {} vm", "the {} is up", "can you {} alpha", "{} the web vm",
          "stop alpha and {} beta", "is the {} running")


def _words() -> list:
    return [w.strip().lower() for w in open(DICT_PATH)
            if w.strip().isalpha() and len(w.strip()) >= 4]


def dictionary_sweep(n: int = 6000, seed: int = 20260917) -> list:
    """One frame, n sampled words — the original measurement's shape."""
    sample = random.Random(seed).sample(_words(), n)
    out = []
    for w in sample:
        t = f"stop the {w} vm"
        got = FD.read(t, known=LAB).text
        if got != t:
            out.append((t, got))
    return out


def frame_sweep(n: int = 3000, seed: int = 20260918) -> list:
    """Six frames over sampled words — a word's slot decides whether it survives."""
    rng = random.Random(seed)
    words = _words()
    out = []
    for _ in range(n):
        t = rng.choice(FRAMES).format(rng.choice(words))
        got = FD.read(t, known=LAB).text
        if got != t:
            out.append((t, got))
    return out


def main() -> int:
    for label, run, n in (("6,000 dictionary words, one frame", dictionary_sweep, 6000),
                          ("3,000 sampled sentences, six frames", frame_sweep, 3000)):
        bad = run()
        print(f"\n  {label}")
        print(f"     damaged {len(bad)}/{n} = {len(bad) / n * 100:.2f}%")
        for a, b in bad[:10]:
            print(f"       {a!r} -> {b!r}")
        if len(bad) > 10:
            print(f"       … and {len(bad) - 10} more")
    print("\n  Paste these into SEAL-front-door.md §3. They are RATES, not counts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
