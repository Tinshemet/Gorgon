"""score.py — run the frozen gold against the front door and print the DISAGREEMENTS.

⇒ THE OUTPUT IS A LIST, NOT A NUMBER. Every disagreement is one of two things — a door defect or
  a gold error — and only the operator can say which. The rates are printed so the shape is
  visible; the rows are printed so the shape can be argued with.

⇒ THE THREE RATES ANSWER THREE DIFFERENT QUESTIONS, and averaging them would destroy all three:

    must_repair      RECALL          how much declared junk it removes
    must_not_touch   FALSE REPAIR    how often it damages text it must not touch  <- SAFETY
    ambiguous        CALIBRATION     whether it declines instead of guessing

⇒ PROVENANCE ON EVERY RUN (the 09-17 rule): the corpus SHA, the git SHA, and the fact that no
  model is involved are written into the results, so a number read back in a month can be
  attributed to exact bytes and exact code. A rate whose corpus is unknown is not a rate.

Usage:  PYTHONPATH=. python3 -m tests.bench.door_eval.score [--all]
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

from orchestrator.languages.english.seam import front_door as FD

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.jsonl")


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _git() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                              capture_output=True, text=True).stdout.strip() or "?"
    except Exception:
        return "?"


def run(show_all: bool = False) -> dict:
    rows = [json.loads(l) for l in open(CASES) if l.strip()]
    out, buckets = [], {}
    for r in rows:
        v = FD.read(r["text"])
        ok = v.text == r["expect"]
        rec = dict(r, got=v.text, notices=list(v.notices), ok=ok)
        out.append(rec)
        b = buckets.setdefault(r["bucket"], {"n": 0, "ok": 0})
        b["n"] += 1
        b["ok"] += int(ok)

    print(f"corpus {os.path.basename(CASES)}  sha {_sha(CASES)}  git {_git()}  model: none")
    print(f"{'bucket':<18}{'n':>5}{'agree':>7}{'rate':>8}   the question it answers")
    Q = {"must_repair": "RECALL — declared junk removed",
         "must_not_touch": "FALSE REPAIR — text damaged that must not be (SAFETY)",
         "ambiguous": "CALIBRATION — declines instead of guessing"}
    for name in ("must_repair", "must_not_touch", "ambiguous"):
        b = buckets.get(name)
        if not b:
            continue
        print(f"{name:<18}{b['n']:>5}{b['ok']:>7}{100 * b['ok'] / b['n']:>7.0f}%   {Q[name]}")
    mnt = buckets.get("must_not_touch", {"n": 1, "ok": 1})
    print(f"\n  FALSE-REPAIR RATE: {mnt['n'] - mnt['ok']}/{mnt['n']} "
          f"= {100 * (mnt['n'] - mnt['ok']) / mnt['n']:.1f}%")

    bad = [r for r in out if not r["ok"]]
    print(f"\n{'=' * 78}\nDISAGREEMENTS — {len(bad)} of {len(out)}. Each is a door defect OR a "
          f"gold error;\nthe operator rules on which. Nothing here is a verdict.\n{'=' * 78}")
    for r in (out if show_all else bad):
        mark = "ok " if r["ok"] else "DIFF"
        print(f"\n[{mark}] {r['id']}  ({r['bucket']})")
        print(f"      in     {r['text']!r}")
        print(f"      expect {r['expect']!r}")
        print(f"      got    {r['got']!r}")
        if r["notices"]:
            for n in r["notices"]:
                print(f"      notice {n}")
        print(f"      why    {r['why']}")
    return {"cases": out, "buckets": buckets,
            "provenance": {"corpus_sha": _sha(CASES), "git": _git(), "model": None}}


if __name__ == "__main__":
    run("--all" in sys.argv)
