"""score.py — the clause-cut spec against `merge_cut_points`. Prints DISAGREEMENTS, not a verdict.

Each disagreement is a rule defect or a gold error and the operator rules on which. Provenance
(corpus sha, git sha, model: none) so any number read back is attributable to exact bytes.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
from orchestrator.languages.english.seam.pass2 import merge_cut_points

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases.jsonl")


def _sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def _git():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                              capture_output=True, text=True).stdout.strip() or "?"
    except Exception:
        return "?"


def _words_after(text, pts):
    """What each restored comma precedes — the gold's unit, never an offset."""
    out = []
    for p in pts:
        tail = text[p:].lstrip(" ,")
        out.append(tail.split()[0] if tail.split() else "")
    return out


def run(show_all=False):
    rows = [json.loads(l) for l in open(CASES) if l.strip()]
    out, by = [], {}
    for r in rows:
        got = _words_after(r["text"], merge_cut_points(r["text"]))
        # gold entries may name more than one word ("stop the db"); match on the first
        want = [w.split()[0] for w in r["before"]]
        ok = got == want
        out.append(dict(r, got=got, ok=ok))
        b = by.setdefault(r["bucket"], {"n": 0, "ok": 0}); b["n"] += 1; b["ok"] += ok
        rb = by.setdefault(f"rule {r['rule']}", {"n": 0, "ok": 0}); rb["n"] += 1; rb["ok"] += ok
    print(f"corpus cases.jsonl  sha {_sha(CASES)}  git {_git()}  model: none")
    for k in ("must_cut", "must_not_cut"):
        b = by.get(k)
        if b:
            print(f"  {k:<14}{b['ok']:>3}/{b['n']:<3} {100*b['ok']/b['n']:>4.0f}%")
    mnc = by.get("must_not_cut", {"n": 1, "ok": 1})
    print(f"  FALSE-CUT RATE: {mnc['n']-mnc['ok']}/{mnc['n']} = "
          f"{100*(mnc['n']-mnc['ok'])/mnc['n']:.1f}%")
    print("  " + "  ".join(f"r{k.split()[1]}:{v['ok']}/{v['n']}"
                           for k, v in sorted(by.items()) if k.startswith("rule")))
    bad = [r for r in out if not r["ok"]]
    print(f"\nDISAGREEMENTS — {len(bad)} of {len(out)}")
    for r in (out if show_all else bad):
        print(f"\n[{'ok ' if r['ok'] else 'DIFF'}] {r['id']}  rule {r['rule']}  ({r['bucket']})")
        print(f"      text   {r['text']!r}")
        print(f"      expect cut before {r['before'] or 'NOTHING'}")
        print(f"      got    cut before {r['got'] or 'NOTHING'}")
        print(f"      why    {r['why']}")
    return {"cases": out, "by": by}


if __name__ == "__main__":
    run("--all" in sys.argv)
