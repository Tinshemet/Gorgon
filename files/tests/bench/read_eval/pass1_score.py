"""pass1_score.py — the pass-1 scorer. THREE numbers, kept distinct on purpose, over a frozen
READ dataset (no model call — reads what the marathon already captured).

    PRESERVATION   ok / (ok + GORGON-DROP)          did READ keep each piece?     [SERPENT-DROP excluded]
    ACCURACY       clean-structure turns / turns    did READ structure it right?  [orthogonal to preservation]
    PERFECT        (no flag AND no drop) / turns     both at once — the marathon's old "clean" headline

⇒ WHY THREE, NOT ONE. A turn can keep every atom and still be mis-structured, or be cleanly
  structured and still drop one. The marathon's "clean turns" fused the two (line 60 of
  marathon_read: flagged = has-struct OR has-drop), which read as a single ~72% and hid that
  preservation is really ~98% and structural accuracy ~75%. This scorer never fuses them.

⇒ THE NEGATION CREDIT IS RE-APPLIED HERE. `results.jsonl` was frozen before the 2026-09-24 fix
  that credits a prohibition read as an `excluded` role (broken_telephone.recover). Stored
  verdicts still mark those 22 atoms GORGON-DROP; this scorer re-applies the same rule from the
  stored spans, so it reports the CURRENT code's numbers. A fresh marathon bakes it in and this
  correction becomes a no-op.

    PYTHONPATH=. python3 -m tests.bench.read_eval.pass1_score [dataset.jsonl]
"""
import os
import sys
from collections import Counter

from tests.bench.read_eval import pass1_eval


def _roles(row):
    return {sp[1] for sp in (row.get("spans") or []) if isinstance(sp, (list, tuple)) and len(sp) >= 2}


def score(rows):
    ok = gd = sd = clean_struct = perfect = 0
    drop_kind = Counter()
    for r in rows:
        roles = _roles(r)
        has_drop = False
        for a in (r.get("atoms") or []):
            if not (isinstance(a, (list, tuple)) and len(a) >= 3):
                continue
            w, k, v = a[0], a[1], a[2]
            # re-apply the negation credit (SSOT rule: a prohibition realised as `excluded` is kept)
            if k == "negation" and v == "GORGON-DROP" and "excluded" in roles:
                v = "ok"
            if v == "ok":
                ok += 1
            elif v == "SERPENT-DROP":
                sd += 1
            elif v == "GORGON-DROP":
                gd += 1
                drop_kind[k] += 1
                has_drop = True
        no_flag = not (r.get("struct") or [])
        clean_struct += no_flag
        perfect += no_flag and not has_drop
    n = len(rows) or 1
    return {"turns": len(rows), "ok": ok, "gorgon_drop": gd, "serpent_drop": sd,
            "preservation": 100 * ok / max(ok + gd, 1),
            "accuracy": 100 * clean_struct / n,
            "perfect": 100 * perfect / n,
            "drop_kind": dict(drop_kind.most_common())}


def report(m):
    print(f"turns={m['turns']}")
    print(f"  PRESERVATION  {m['preservation']:6.2f}%   ok {m['ok']} / {m['ok']+m['gorgon_drop']}  (SERPENT-DROP {m['serpent_drop']} excluded)")
    print(f"  ACCURACY      {m['accuracy']:6.2f}%   clean-structure turns")
    print(f"  PERFECT       {m['perfect']:6.2f}%   no flag AND no drop")
    print(f"  GORGON-DROP by kind: {m['drop_kind']}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else pass1_eval._DEFAULT
    print(f"dataset: {os.path.relpath(path)}")
    report(score(pass1_eval.load(path)))
