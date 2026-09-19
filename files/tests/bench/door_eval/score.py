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

# ⇒⇒ THE LAB THE CORPUS ASSUMES. The door's behaviour legitimately depends on which standing
#   objects the world declares — `thedb vm` is a fusion only if `db` names something. Scoring
#   name-fusion cases against an EMPTY world tests the wrong thing: it asks whether the door
#   guesses at names it was never told about, and the answer should be no.
#   ⇒ FOUND 2026-09-17, by the split-pass fix: two must_repair cases "regressed" purely because
#     nothing here declared `alpha` or `test`. Passing the world restored both while every
#     precision fix held. Production calls `read()` with no world at all (divergence D2), which
#     is a separate defect this line does not paper over — it makes the corpus honest, not the
#     product correct.
WORLD = ("alpha", "beta", "web", "db", "core", "lab", "test", "grubnash", "dmz")


def _sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def _git() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                              capture_output=True, text=True).stdout.strip() or "?"
    except Exception:
        return "?"


def _ask_kind(notices) -> str:
    """Which ASK the door made, read off its own notices — "" when it said nothing.

    ⇒⇒ **THE `ambiguous` BUCKET MEASURED NOTHING UNTIL 2026-09-18.** The scorer compared TEXT
      only, so its two cases asserted "text unchanged" — which is precisely what
      `must_not_touch` asserts — and the `ask` field was loaded from the corpus and never read.
      `ambiguous 2/2 = 100%` was doubly meaningless: two cases, neither checking the thing the
      bucket exists for. Calibration is *does it DECLINE instead of guessing*, and a decline is
      only a decline if it SAYS so; silence and an ask are different answers.
    """
    for n in notices:
        if "could not read" not in n:
            continue
        if "equally" in n:
            return "ambiguous"          # two candidates fit their slot; a tie
        if "licenses the repair" in n:
            return "unlicensed"         # explained by the catalogue, but no slot votes
    for n in notices:
        # ⇒ THE CHARTER DECLINE (operator, 2026-09-19): the repair was available and REFUSED
        #   because applying it would change what the request does. Distinct from `ambiguous`
        #   (two candidates, no way to choose) and `unlicensed` (no slot votes): here the door
        #   could have chosen and is not allowed to.
        if "could not apply" in n and "change what the request does" in n:
            return "meaning"
    return ""                            # silent — a multi-edit stretch, or nothing to say


def run(show_all: bool = False) -> dict:
    rows = [json.loads(l) for l in open(CASES) if l.strip()]
    out, buckets = [], {}
    for r in rows:
        v = FD.read(r["text"], known=WORLD)
        ok = v.text == r["expect"]
        # ⇒ AND THE ASK KIND, WHERE THE CORPUS DECLARES ONE. A case that names an ask is scored
        #   on BOTH: the text must be untouched AND the door must have declined the way the gold
        #   says. Cases with no declared ask are scored on text alone, exactly as before.
        if r.get("ask"):
            ok = ok and _ask_kind(v.notices) == r["ask"]
        rec = dict(r, got=v.text, notices=list(v.notices), got_ask=_ask_kind(v.notices), ok=ok)
        out.append(rec)
        b = buckets.setdefault(r["bucket"], {"n": 0, "ok": 0})
        b["n"] += 1
        b["ok"] += int(ok)

    print(f"corpus {os.path.basename(CASES)}  sha {_sha(CASES)}  git {_git()}  model: none  world: {len(WORLD)} declared")
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
        if r.get("ask") or r.get("got_ask"):
            print(f"      ask    expect {r.get('ask') or 'SILENT'!r}  got {r.get('got_ask') or 'SILENT'!r}")
        if r["notices"]:
            for n in r["notices"]:
                print(f"      notice {n}")
        print(f"      why    {r['why']}")
    return {"cases": out, "buckets": buckets,
            "provenance": {"corpus_sha": _sha(CASES), "git": _git(), "model": None}}


if __name__ == "__main__":
    run("--all" in sys.argv)
