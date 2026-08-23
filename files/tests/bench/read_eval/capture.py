"""capture.py — the MODEL-FREE CONTROL for a refactor of the seam.

    PYTHONPATH=. python3 -m tests.bench.read_eval.capture cases/v3-draft.jsonl > before.json
    ... change the code ...
    PYTHONPATH=. python3 -m tests.bench.read_eval.capture cases/v3-draft.jsonl > after.json
    PYTHONPATH=. python3 -m tests.bench.read_eval.capture --diff before.json after.json

# ⇒ WHY THIS AND NOT THE EVAL
The eval asks the model, and the model wobbles at temp 0 (08-17, 08-22: one case differed on
byte-identical inputs). A refactor's question is not "did the score move" but "did the code
hand the model the same question" — so this stubs `engines.channel.constrained` to RECORD
every (prompt, payload, schema) it is asked and answer {}, runs `read_case` over the file,
and hashes what each case asked plus what the code read without the model (the view, the
rows, the steps). Two captures equal ⇒ the change was behaviour-preserving on this corpus;
a diff names exactly which cases changed and in which field. Proved the seam move 65/65
identical on 08-22 — from a scratchpad script that did not survive the night, hence this.
"""
import hashlib
import json
import os
import sys
from typing import Dict, List, Optional

from .schema import load


def capture(cases: List[dict]) -> Dict[str, dict]:
    import engines.channel as channel
    from planner.formula.legal import Board
    from .runner import read_case
    asked: List[dict] = []
    was = channel.constrained

    def record(prompt, payload, schema, **kw):
        asked.append({"prompt": str(prompt), "payload": payload, "schema": schema})
        return {}
    channel.constrained = record
    out: Dict[str, dict] = {}
    try:
        board = Board()
        for case in cases:
            del asked[:]
            reading = read_case(case["sentence"], board=board)
            fields = {
                "asked": [hashlib.sha256(json.dumps(a, sort_keys=True, default=str)
                                         .encode()).hexdigest()[:16] for a in asked],
                "reading": hashlib.sha256(json.dumps(reading, sort_keys=True, default=str)
                                          .encode()).hexdigest()[:16],
            }
            out[case["id"]] = fields
    finally:
        channel.constrained = was
    return out


def diff(before: Dict[str, dict], after: Dict[str, dict]) -> List[str]:
    lines = []
    for cid in sorted(set(before) | set(after)):
        b, a = before.get(cid), after.get(cid)
        if b == a:
            continue
        if b is None or a is None:
            lines.append(f"{cid:14} {'added' if b is None else 'removed'}")
            continue
        changed = [k for k in sorted(set(b) | set(a)) if b.get(k) != a.get(k)]
        lines.append(f"{cid:14} {' '.join(changed)}")
    return lines


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--diff"]:
        with open(argv[1], encoding="utf-8") as fh:
            before = json.load(fh)
        with open(argv[2], encoding="utf-8") as fh:
            after = json.load(fh)
        lines = diff(before, after)
        same = len(set(before) & set(after)) - sum(1 for l in lines if not l.endswith(("added", "removed")))
        print(f"  {same}/{len(before)} identical" + (":" if lines else ""))
        print("\n".join(f"    {l}" for l in lines))
        return 1 if lines else 0
    path = argv[0]
    if not os.path.isabs(path):
        here = os.path.dirname(os.path.abspath(__file__))
        path = path if os.path.exists(path) else os.path.join(here, path)
    json.dump(capture(load(path)), sys.stdout, indent=1, sort_keys=True)
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
