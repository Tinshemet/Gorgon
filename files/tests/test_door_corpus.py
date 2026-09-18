"""test_door_corpus.py — the front door's 156 frozen cases, in CI, with its open list DECLARED.

⇒⇒ **THIS CORPUS HAD NEVER RUN IN CI.** It was scored by hand every time since 2026-09-17 while
the clause-cut spec beside it has had `test_clause_cuts.py` from the day it was written. A
measurement nobody runs automatically is a measurement that goes stale the first afternoon
somebody is busy — and this one is the front door's entire evidence base.

⇒ **THE OPEN LIST IS DATA, EXACTLY AS IT IS FOR THE CUT SPEC.** A NEW disagreement turns this red;
so does a silently FIXED one, which is what keeps a fix from landing without a note. The dict is
empty today: 56/56 · 69/69 · 31/31.

⇒⇒ **AND THE `ambiguous` GOLD IS CHECKED AGAINST THE CATALOGUE, NOT AGAINST THE DOOR.** That
bucket was rebuilt on 2026-09-18 by sweeping for inputs the door declines — which is how you FIND
instances and would be circular as a way to write GOLD. So the third test below re-derives each
case from `noise_prints.explain` and the candidate sets: a case whose gold says TIE must have two
candidates explained at one print; one that says UNLICENSED must have at least one; one that says
SILENT must have none, or a word already declared safe. The door's own output is never consulted.
That is the difference between choosing a case and writing its answer.

⇒ THE THREE ANSWERS A DECLINE CAN GIVE, and the scorer checks WHICH, not merely that the text
  survived: `ambiguous` (a tie) · `unlicensed` (explained, but no slot votes) · `""` (silence —
  a multi-edit stretch is never surfaced). Until the kind was checked, this bucket asserted
  nothing `must_not_touch` did not already assert.

MODEL-FREE. `front_door` makes no model call.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english import codex
from orchestrator.languages.english.seam import front_door as FD
from orchestrator.languages.english.noise_prints import explain as _explain
from tests.bench.door_eval.score import WORLD, _ask_kind

CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "bench", "door_eval", "cases.jsonl")

# ⇒ EMPTY, AND THAT IS THE STATE. An entry here must carry WHY it is open; closing one means
#   deleting its line in the same commit as the fix, which is what makes the fix visible.
KNOWN_DISAGREEMENTS: dict = {}


def _cases() -> list:
    assert os.path.exists(CASES), f"no door corpus at {CASES} — run build_cases"
    return [json.loads(l) for l in open(CASES) if l.strip()]


def _judged_token(text: str, known: set):
    """The token under judgement — the one the reader does not already know."""
    for w in re.findall(r"[a-z']+", text.lower()):
        if len(w) >= 4 and w not in known:
            return w
    return None


def test_every_bucket_matches_its_declared_open_list():
    rows = _cases()
    assert len(rows) >= 156, f"only {len(rows)} cases — the corpus shrank"
    disagree = {}
    for r in rows:
        v = FD.read(r["text"], known=WORLD)
        ok = v.text == r["expect"]
        if r.get("ask"):
            ok = ok and _ask_kind(v.notices) == r["ask"]
        if not ok:
            disagree[r["id"]] = (r["text"], r["expect"], v.text,
                                 r.get("ask"), _ask_kind(v.notices))
    new = sorted(set(disagree) - set(KNOWN_DISAGREEMENTS))
    fixed = sorted(set(KNOWN_DISAGREEMENTS) - set(disagree))
    assert not new, (
        "NEW door-corpus disagreements:\n"
        + "\n".join(f"    {i}  {disagree[i][0]!r}\n        expect {disagree[i][1]!r} "
                    f"ask={disagree[i][3]!r}\n        got    {disagree[i][2]!r} "
                    f"ask={disagree[i][4]!r}" for i in new))
    assert not fixed, (
        f"these disagreements are FIXED and the manifest is stale: {fixed}\n"
        f"  Delete their lines in the same commit as the fix.")


def test_the_safety_bucket_is_completely_clean():
    """`must_not_touch` is the safety axis — a wrong repair changes meaning silently."""
    rows = [r for r in _cases() if r["bucket"] == "must_not_touch"]
    assert len(rows) >= 69, f"only {len(rows)} must_not_touch cases"
    damaged = [(r["id"], r["text"], FD.read(r["text"], known=WORLD).text)
               for r in rows if FD.read(r["text"], known=WORLD).text != r["text"]]
    assert not damaged, f"text that must survive byte-identical was edited: {damaged}"


def test_the_ambiguous_gold_is_derivable_without_the_door():
    """Each declined case must be a tie / unlicensed / silent BY THE CATALOGUE.

    ⇒ THE ANTI-CIRCULARITY CHECK. The bucket's instances were FOUND by sweeping for inputs the
      door declines; its ANSWERS must not come from the same place, or the corpus grades the
      door against itself and can never fail. So each case is re-derived here from
      `noise_prints.explain` over the candidate sets, and `FD.read` is never called.
    """
    openers, nouns, ops, known = FD._vocab(None)
    cands = openers | nouns | ops | FD._statuses(None)
    safe = set(codex.FALSE_PRINTS) | set(codex.FALSE_FUSIONS) | set(codex.FALSE_TYPOS)
    rows = [r for r in _cases() if r["bucket"] == "ambiguous"]
    assert len(rows) >= 30, (
        f"only {len(rows)} ambiguous cases — the plan called for ~30 and calibration is the one "
        f"axis with no external authority, so a thin bucket measures nothing")
    bad = []
    for r in rows:
        w = _judged_token(r["text"], known)
        if w is None:
            if r["ask"]:
                bad.append((r["id"], "no token under judgement, yet the gold expects an ask"))
            continue
        one = sorted(c for c in cands
                     if (lambda p: p and len(p) <= 1)(_explain(c, w)))
        if r["ask"] == "ambiguous" and len(one) < 2:
            bad.append((r["id"], f"gold says TIE but only {one} explain {w!r} at one print"))
        elif r["ask"] == "unlicensed" and not one:
            bad.append((r["id"], f"gold says UNLICENSED but nothing explains {w!r}"))
        elif r["ask"] == "" and one and w not in safe:
            bad.append((r["id"], f"gold says SILENT but {one} explain {w!r} at one print"))
    assert not bad, (
        "ambiguous gold that cannot be derived from the catalogue — it was read off the door:\n"
        + "\n".join(f"    {i}  {why}" for i, why in bad))


def test_the_three_ask_kinds_are_all_exercised():
    """A bucket that only ever sees one kind of decline is not measuring calibration."""
    from collections import Counter
    kinds = Counter(r.get("ask") or "" for r in _cases() if r["bucket"] == "ambiguous")
    for kind in ("ambiguous", "unlicensed", ""):
        assert kinds.get(kind, 0) >= 3, (
            f"only {kinds.get(kind, 0)} cases declare ask={kind!r} — the bucket stopped probing "
            f"that answer, so a regression in it would pass unseen. Kinds present: {dict(kinds)}")


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the front door's corpus"))


if __name__ == "__main__":
    main()
