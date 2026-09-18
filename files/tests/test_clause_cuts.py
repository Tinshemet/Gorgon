"""test_clause_cuts.py — the clause-cut spec, in CI, with its open disagreements DECLARED.

⇒⇒ **A SPEC THAT ONLY RUNS WHEN SOMEBODY REMEMBERS TO RUN IT IS A DOCUMENT, NOT A SPEC.**
`tests/bench/cut_eval` holds 29 cases written from English — for each of `_first_cut`'s eight
rules, the construction it exists to catch AND the construction where the same closed-class words
appear and English has no boundary. This file runs them on every invocation and holds the result
to a DECLARED set of open disagreements, so:

    a NEW disagreement          turns this red — a rule regressed, or a case was added
    a FIXED disagreement        ALSO turns this red — the manifest is stale, say so
    nothing is open right now   — the dict is empty and all 29 agree

That is the same shape as the eval/production parity manifest: the open list is data, in the
repo, and drifting from it is an error rather than a thing somebody notices later.

⇒ **AND THE NEGATION GUARD IS ASSERTED AGAINST ITS OWN SSOT.** `codex.CUT_NEGATION` is what stops
rule 6 reading a negated verb as a fresh imperative. It held four forms of fourteen until
2026-09-17, and `dont stop the web vm stop the db vm` became `dont, stop the web vm, stop the db
vm` — a prohibition turned into a bare `dont` and two unqualified orders. It cannot reference
`NEG_DO`/`NEG_MODALS` from where it is declared (the codex is sectioned by consumer and those
sets belong to other readers), so the containment is enforced HERE instead.

MODEL-FREE. `merge_cut_points` is grammar over closed classes; nothing probabilistic runs.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english import codex
from orchestrator.languages.english.seam.pass2 import merge_cut_points

CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "bench", "cut_eval", "cases.jsonl")

# ⇒ THE OPEN LIST, and every entry carries WHY it is still open. Closing one means deleting its
#   line here in the same commit — which is what makes a fix visible instead of silent.
KNOWN_DISAGREEMENTS = {
    # ⇒ EMPTY, AND THAT IS THE STATE — all 29 cases agree, 11/11 must_cut and 18/18 must_not_cut.
    #   c7-04 closed 2026-09-17 (`predicate_end`'s modal arm now checks its head is a verb).
    #   c3-01 closed 2026-09-17 — it was MY gold that was wrong, not the rule.
    #   c6-02 closed 2026-09-18 — `snapshot` admitted through `codex.DUAL_CLASS_VERBS`.
    #   A dict rather than a set so the next open case arrives with its reason attached.
}

# Every negator form that can negate a following verb, by spelling. `nope`/`nah` are excluded on
# purpose — a standalone refusal does not negate a following verb — and so is copular `isn't`.
_NEGATOR_FRAMES = ("don't", "dont", "doesn't", "doesnt", "didn't", "didnt",
                   "can't", "cant", "cannot", "won't", "wont", "couldn't", "couldnt",
                   "wouldn't", "wouldnt", "never", "no", "neither")


def _cases() -> list:
    assert os.path.exists(CASES), f"no cut corpus at {CASES} — run build_cases"
    return [json.loads(l) for l in open(CASES) if l.strip()]


def _words_after(text: str, pts: list) -> list:
    out = []
    for p in pts:
        tail = text[p:].lstrip(" ,")
        out.append(tail.split()[0] if tail.split() else "")
    return out


def test_the_cut_negation_set_contains_every_verb_negating_form():
    """`CUT_NEGATION` must cover `NEG_DO` and `NEG_MODALS`, both spellings of each."""
    want = set(codex.NEG_DO) | set(codex.NEG_MODALS)
    want |= {w.replace("'", "") for w in want}
    missing = sorted(want - set(codex.CUT_NEGATION))
    assert not missing, (
        f"{len(missing)} verb-negating forms are declared elsewhere in the codex but absent "
        f"from CUT_NEGATION: {missing}\n"
        f"  Rule 6 will read the verb behind each of these as a FRESH IMPERATIVE and cut the "
        f"negation away from it.")


def test_no_declared_negator_is_cut_away_from_its_verb():
    """The safety case, over every form, behaviourally."""
    split = []
    for neg in _NEGATOR_FRAMES:
        text = f"{neg} stop the web vm stop the db vm"
        # a cut inside or immediately after the negator separates it from `stop`
        if any(p <= len(neg) + 1 for p in merge_cut_points(text)):
            split.append(text)
    assert len(_NEGATOR_FRAMES) >= 15, "the frame list shrank — this test stopped probing"
    assert not split, (
        f"{len(split)} negators were cut away from the verb they negate — a prohibition becomes "
        f"a bare negator plus unqualified imperatives: {split[:4]}")


def test_the_second_imperative_still_cuts_behind_a_negator():
    """The capability rule 6 exists for must survive the guard: the SECOND clause still opens."""
    for neg in ("dont", "don't", "cant", "never"):
        text = f"{neg} stop the web vm stop the db vm"
        got = _words_after(text, merge_cut_points(text))
        assert got == ["stop"], f"{text!r} lost its second clause — cuts before {got}"


def test_the_declared_duals_are_grounded_in_the_manifest():
    """`DUAL_CLASS_VERBS` must be derivable, not a hand-picked list that drifts.

    ⇒ THE DERIVATION, and it is the whole justification for admitting a noun segment as a verb:
      a kind is DUAL when the manifest declares a `creators` entry for it — something makes one —
      AND the vm relates to it, which is what makes *"X the vm"* natural shorthand. `snapshot`
      (vm `acts: snapshots`) and `template` (vm `creators: from_template`) qualify. `profile` is a
      spec ASSIGNED to a vm rather than derived from one, `file` declares no creators at all, and
      `network` relates only through a SETTER. If the manifest changes, this test says so.

    ⇒ AND EVERY MEMBER MUST STILL NEED ADMITTING. A dual that is no longer subtracted by
      `NON_VERB_SEGMENTS` is a dead entry carrying weight for nothing.
    """
    from planner.ir import config as _cfg
    kinds = _cfg.KINDS or {}
    assert codex.DUAL_CLASS_VERBS, "the dual set is empty — rule 6 is blind to every kind verb"
    ungrounded = sorted(w for w in codex.DUAL_CLASS_VERBS
                        if not ((kinds.get(w) or {}).get("creators")))
    assert not ungrounded, (
        f"{ungrounded} are declared dual but the manifest declares no `creators` for them — "
        f"nothing makes one, so \"X the vm\" is not shorthand for anything.")
    dead = sorted(w for w in codex.DUAL_CLASS_VERBS if w not in codex.NON_VERB_SEGMENTS)
    assert not dead, (
        f"{dead} are declared dual but are NOT subtracted by NON_VERB_SEGMENTS, so admitting "
        f"them changes nothing — dead entries.")


def test_a_dual_is_a_verb_by_POSITION_and_a_noun_otherwise():
    """The admission is safe only because rule 6 judges by position. Assert it still does."""
    for word in sorted(codex.DUAL_CLASS_VERBS):
        verb = f"stop the web vm {word} the db vm"
        assert merge_cut_points(verb), f"{verb!r} — the dual was not read as a second imperative"
        for noun in (f"delete the {word}", f"take a {word} of the db vm",
                     f"stop the {word} vm", f"restore the {word} the operator made"):
            assert not merge_cut_points(noun), (
                f"{noun!r} cut — the NOUN reading fired. The position test (next word a "
                f"determiner, previous word not one) stopped discriminating.")


def test_the_spec_matches_its_declared_open_list():
    rows = _cases()
    assert len(rows) >= 29, f"only {len(rows)} cases — the corpus shrank"
    disagree = {}
    for r in rows:
        got = _words_after(r["text"], merge_cut_points(r["text"]))
        want = [w.split()[0] for w in r["before"]]
        if got != want:
            disagree[r["id"]] = (r["text"], want, got)

    new = sorted(set(disagree) - set(KNOWN_DISAGREEMENTS))
    fixed = sorted(set(KNOWN_DISAGREEMENTS) - set(disagree))
    assert not new, (
        "NEW clause-cut disagreements — a rule regressed, or a case was added without deciding "
        "it:\n" + "\n".join(f"    {i}  {disagree[i][0]!r}\n        expect cut before "
                            f"{disagree[i][1] or 'NOTHING'}, got {disagree[i][2] or 'NOTHING'}"
                            for i in new))
    assert not fixed, (
        f"these disagreements are FIXED and the manifest is stale: {fixed}\n"
        f"  Delete their lines from KNOWN_DISAGREEMENTS in the same commit as the fix — that is "
        f"what makes the fix visible.")


def test_the_safety_bucket_is_completely_clean():
    """must_not_cut is the safety axis: a spurious cut splits a clause silently.

    ⇒ ASSERTED EMPTY, NOT "within the declared list". It was the weaker form while `c7-04` was
      open; the moment rule 7 stopped reading an order as testimony the bucket went to 18/18,
      and leaving the subset test in place would have let the NEXT spurious cut hide behind a
      declared disagreement in a different bucket.
    """
    rows = [r for r in _cases() if r["bucket"] == "must_not_cut"]
    assert len(rows) >= 18, f"only {len(rows)} must_not_cut cases"
    fired = [(r["id"], r["text"]) for r in rows if merge_cut_points(r["text"])]
    assert not fired, f"a spurious cut fired where English has no clause boundary: {fired}"


# THE ENTRY POINT BELONGS AT THE BOTTOM — `main()` ends in `sys.exit`, so anything defined below
# this guard is never defined when the suite runs.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the clause-cut spec"))


if __name__ == "__main__":
    main()
