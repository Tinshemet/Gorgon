"""rank.py — THE RANKER'S OWN DOOR, and nothing but ranking behind it.

# ⇒⇒ WHY A SEPARATE COMMAND (operator, 2026-08-24)
*"i am going to give it to someone else, or to me a day or two later after i forget so i
dont want to accidently open the grading version, just the ranking."*

`review <cases>` with no flag CERTIFIES — the grader's door. This module is the other one:
it can only rank. It never loads, shows, or writes verdicts; it never paints gold; the one
thing it opens besides the cases is `<cases>.rank.json`. Blind by construction stays blind
by COMMAND: the wrong tool cannot be opened by forgetting a flag.

    PYTHONPATH=. python3 -m tests.bench.read_eval.rank cases/v3-draft.jsonl            # rank
    PYTHONPATH=. python3 -m tests.bench.read_eval.rank cases/v3-draft.jsonl --status   # coverage

`review --rank` still works and lands in the same file — this is the same loop, not a fork.
"""
from typing import List, Optional

from .review import rank, rank_status
from .schema import load, validate


def main(argv: Optional[List[str]] = None) -> int:                # pragma: no cover
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    path = next((a for a in argv if not a.startswith("--")), None)
    if not path:
        print("usage: python3 -m tests.bench.read_eval.rank <cases.jsonl> [--status]")
        return 2
    cases = load(path)
    bad = validate(cases)
    if bad:
        print("\n".join(f"  ✗ {b}" for b in bad))
        print("\n  the case file is not valid — refusing to rank on broken cases")
        return 1
    if "--status" in argv:
        return rank_status(cases, path)
    return rank(cases, path)


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
