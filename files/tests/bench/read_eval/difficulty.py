"""difficulty.py — THE STRUCTURAL AXIS: how hard a case is, COMPUTED FROM ITS GOLD.

    PYTHONPATH=. python3 -m tests.bench.read_eval.difficulty cases/v3-draft.jsonl
    PYTHONPATH=. python3 -m tests.bench.read_eval.difficulty cases/v3-draft.jsonl --json

# ⇒ TWO AXES, AND ONLY ONE IS A HUMAN'S JOB (operator's split, 08-22)
Difficulty has a STRUCTURAL axis and a READABILITY axis. Readability is a second person's
1-10 through `review.py --rank`, blind. This file is the other axis: every feature below is
a COUNT over the gold — nobody ranks it, so nobody can bias it. "Compute what can be
computed." It reads the case file only — never a verdict, a rank, or a results file.
Joining the three (structure · readability · score) is the analyst's step, after all are
complete, and it lives nowhere yet on purpose.

# ⇒ THE FEATURES — each one a thing the schema carries, counted
    spans        gold spans (objects + evidence)
    acts         gold actions
    asks         actions with a kind (query · rule · report) — not a plain imperative
    channels     trigger + manner channels on actions (v2.0)
    roles        role-tagged attachment members (v1.1)
    fan          attachments with more than one member (one act, several objects)
    anaphora     object spans whose text is a referring pronoun (`it`, `them`, `the ones`)
    nesting      action spans enclosed by another action span
    moods        mood spans (v2.4)
    context      1 if RESOLVE supplied context (v2.3) — readable only under it
    store        store entries (v2.0) — decoys the reading must not take
    empty        1 if the gold has NO action (outcome none/reject/testimony/context-needed)
`structural` is their SUM AT UNIT WEIGHT — declared, not fitted. A weighting is a judgement
and would belong to a ruling; until one exists the features are reported beside the sum so
nothing is hidden inside it.
"""
import json
import os
import sys
from typing import Dict, List, Optional

from .schema import load, members_of

FEATURES = ("spans", "acts", "asks", "channels", "roles", "fan", "anaphora", "nesting",
            "moods", "context", "store", "empty")


def _is_anaphor(text: str) -> bool:
    from orchestrator.languages.english.codex import REFERRING_PRONOUNS, PLURAL_PRONOUNS
    low = text.strip().lower()
    words = low.split()
    if low in REFERRING_PRONOUNS or low in PLURAL_PRONOUNS:
        return True
    # `the ones`, `the blue ones`, `those two`, `all of them` — the head is the pronoun
    return bool(words) and (words[-1] in PLURAL_PRONOUNS or words[-1] in REFERRING_PRONOUNS)


def structural(case: dict) -> Dict[str, int]:
    gold = case["gold"]
    spans, acts, atts = gold["spans"], gold["actions"], gold["attachments"]
    f: Dict[str, int] = {k: 0 for k in FEATURES}
    f["spans"] = len(spans)
    f["acts"] = len(acts)
    f["asks"] = sum(1 for a in acts if a.get("kind"))
    f["channels"] = sum(1 for a in acts for ch in ("trigger", "manner") if a.get(ch))
    f["roles"] = sum(1 for at in atts for _ix, role in members_of(at) if role)
    f["fan"] = sum(1 for at in atts if len(members_of(at)) > 1)
    f["anaphora"] = sum(1 for s in spans if s["type"] == "object" and _is_anaphor(s["text"]))
    f["nesting"] = sum(
        1 for i, a in enumerate(acts)
        if any(j != i and b["start"] <= a["start"] and a["end"] <= b["end"]
               and (b["start"], b["end"]) != (a["start"], a["end"])
               for j, b in enumerate(acts)))
    f["moods"] = len(gold.get("mood") or [])
    f["context"] = 1 if case.get("context") else 0
    f["store"] = len(case.get("store") or [])
    f["empty"] = 1 if not acts else 0
    f["structural"] = sum(f[k] for k in FEATURES)
    return f


def table(cases: List[dict]) -> str:
    rows = [(c["id"], c["stratum"], structural(c)) for c in cases]
    head = f"  {'id':14} {'stratum':22} {'S':>3}  " + " ".join(f"{k[:5]:>5}" for k in FEATURES)
    lines = [head]
    for cid, stratum, f in rows:
        lines.append(f"  {cid:14} {stratum:22} {f['structural']:>3}  "
                     + " ".join(f"{f[k]:>5}" for k in FEATURES))
    hist: Dict[int, int] = {}
    for _cid, _st, f in rows:
        hist[f["structural"]] = hist.get(f["structural"], 0) + 1
    lines.append("")
    lines.append("  structural: " + " · ".join(f"{s}:{hist[s]}" for s in sorted(hist)))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    argv = list(sys.argv[1:] if argv is None else argv)
    path = next((a for a in argv if not a.startswith("--")), None)
    if not path:
        print("usage: python3 -m tests.bench.read_eval.difficulty <cases.jsonl> [--json]")
        return 2
    if not os.path.isabs(path):
        here = os.path.dirname(os.path.abspath(__file__))
        path = path if os.path.exists(path) else os.path.join(here, path)
    cases = load(path)
    if "--json" in argv:
        json.dump({c["id"]: structural(c) for c in cases}, sys.stdout, indent=1, sort_keys=True)
        return 0
    print(table(cases))
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
