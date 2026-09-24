"""pass1_eval.py — the pass-1 test harness. Loads a frozen READ dataset and exposes, per turn,
everything the two metrics are computed from — so we can SEE what pass 1 emits before deciding
how to score it.

A dataset row (as the marathon freezes it in results.jsonl) carries:
    said     the operator text pass 1 read
    atoms    [(word, kind, verdict)]   verdict ∈ ok | GORGON-DROP | SERPENT-DROP
             ⇒ the PRESERVATION signal: did READ keep each piece the request carried
    struct   [structural flags]  ([] == a clean turn)
             ⇒ the ACCURACY signal: did READ structure the turn without breakage
    spans    [(span, role)]      the reading, for inspection

    PYTHONPATH=. python3 -m tests.bench.read_eval.pass1_eval [dataset.jsonl]
"""
import json
import os
import sys
from collections import Counter

_DEFAULT = os.path.join(os.path.dirname(__file__), "marathon", "results.jsonl")


def load(path: str = _DEFAULT):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def signals(rows):
    """The raw counts both metrics read — printed, not yet turned into a rate, so the scoring
    definition is chosen against what is actually here."""
    atoms = Counter()          # verdict -> n
    drop_kind = Counter()      # GORGON-DROP by atom kind
    flags = Counter()          # structural flag class -> n
    clean = 0
    for r in rows:
        for a in (r.get("atoms") or []):
            if isinstance(a, (list, tuple)) and len(a) >= 3:
                atoms[a[2]] += 1
                if a[2] == "GORGON-DROP":
                    drop_kind[a[1]] += 1
        st = r.get("struct") or []
        if not st:
            clean += 1
        for f in st:
            flags[f.split("[")[0].split(":")[0]] += 1
    return {"turns": len(rows), "clean": clean, "atoms": atoms,
            "drop_kind": drop_kind, "flags": flags}


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT
    rows = load(path)
    s = signals(rows)
    ok, gd, sd = s["atoms"]["ok"], s["atoms"]["GORGON-DROP"], s["atoms"]["SERPENT-DROP"]
    print(f"dataset: {os.path.relpath(path)}   turns={s['turns']}")
    print(f"\nPRESERVATION signal (atoms):  ok={ok}  GORGON-DROP={gd}  SERPENT-DROP={sd}")
    print(f"   candidate metric: ok / (ok+GORGON-DROP) = {ok}/{ok+gd} = {100*ok/(ok+gd):.2f}%   (SERPENT-DROP excluded — not READ's loss)")
    print(f"\nACCURACY signal (turns):  clean={s['clean']}/{s['turns']}")
    print(f"   candidate metric: clean / turns = {100*s['clean']/s['turns']:.2f}%")
    print(f"\nGORGON-DROP by kind: {dict(s['drop_kind'].most_common())}")
    print(f"structural flags by class: {dict(s['flags'].most_common())}")
