"""asking.py — A QUESTION THE OPERATOR CAN ANSWER, AND AN ANSWER THAT CAN FIND ITS QUESTION.

⇒⇒ **WHY B2 EXISTED AT ALL: AN ASK WAS PROSE.**

`gates12.report` ends `"asks": [f.says for f in found …]` — the finding knows its gate, its rule
and WHAT IT IS ABOUT, and all three are discarded the moment it becomes a question. So the chain
could ask *"what is a grubnash?"* and had nowhere to put the reply, because nothing tied the
words back to the row that wanted them. `run()` has no `answers` parameter for the same reason:
there was no key to accept answers against.

**THAT IS THE WHOLE OF THE BLOCKAGE.** Not the Encyclopedia's storage, not its lookup — the
Encyclopedia (B1) is a place to keep answers, and until now there were no answers to keep.

⇒ **THE KEY IS `about`, AND IT IS ALREADY THERE.** Every finding carries the declared name it
  concerns. For the unfamiliar-noun asks that is the WORD — `grubnash` — which is exactly what
  a global, model-independent store must key on: the same word asked twice is the same question,
  whoever asked it and whichever model was running.

⇒ **STRUCTURED HERE, RENDERED THERE.** `Run.asks` stays a list of strings so every existing
  reader keeps working, but it is DERIVED from these rather than built beside them — one
  authority with a rendered view, not two lists that drift. `surface.py` owns how a question
  reads; this owns what a question IS.

⇒ **AND AN ANSWER IS NOT A REPAIR.** Applying one settles a row the operator answered about and
  nothing else. A gate still does not repair itself ([[gorgon-gates-check-legality]]); this is
  the operator repairing, which is the one authority that was always allowed to.
"""
from typing import Dict, List, NamedTuple, Optional

# ⇒ WHAT AN ANSWER MUST BE, per rule. Declared rather than inferred at the call site, because a
#   caller that guesses wrong turns a clarification into a silent mis-settlement.
KIND, YES_NO, FREE = "kind", "yes-no", "free"

TAKES = {
    "kind-not-settled": KIND,      # "what is a grubnash?"        -> a kind name
    "no-such-kind": KIND,          # "this lab keeps no such thing"
    # ⇒ THE TWO COMMON ONES, ADDED 2026-08-13 AFTER AN END-TO-END DEMO FOUND THEM MISSING.
    #   The demo asked to *"launch every jumpbox"* — and `jumpbox` never needed a KIND answer,
    #   because `settle_by_affordance` typed it `vm` from the verb (only a vm can be launched).
    #   What survived was *"should it be created?"*, which had no entry here and no settler:
    #   **the write-back was wired to the rules that rarely fire.**
    "not-there": YES_NO,           # "… and the lab has none — should it be created?"
    "already-there": YES_NO,       # "… there is already one — use it, or did you mean a second?"
    "invented": FREE,
    "unestablished-referent": YES_NO,
    "destructive-confirm": YES_NO,
    "red-line": YES_NO,
    "goal-unreachable": FREE,
}


class Ask(NamedTuple):
    """One question, addressable.

    `about` is the KEY an answer binds to — the declared name or the word in question — and it
    is what the Encyclopedia will file the answer under.
    """
    rule: str
    about: str
    says: str

    @property
    def takes(self) -> str:
        return TAKES.get(self.rule, FREE)

    @property
    def key(self) -> str:
        """What an answer is addressed to. Case-folded, because a question about `DB` and one
        about `db` are the same question and an operator should not have to match our casing."""
        return f"{self.rule}:{str(self.about).strip().lower()}"

    def __repr__(self):
        return self.says


def asks_of(findings, extra: Optional[List[str]] = None) -> List[Ask]:
    """Gate findings -> addressable questions, keeping the identity the finding already had."""
    out = [Ask(getattr(f, "kind", "") or getattr(f, "rule", ""), getattr(f, "about", ""), f.says)
           for f in (findings or ())]
    # ⇒ A QUESTION WITH NO FINDING BEHIND IT IS STILL A QUESTION. Gate 4's asks arrive as prose
    #   and have no `about` yet, so they are carried unaddressed rather than dropped — visible,
    #   answerable by a person, and not yet answerable by a key. Narrowing that is the next step,
    #   not a reason to lose them here.
    out += [Ask("", "", s) for s in (extra or ())]
    return out


def answered(asks: List[Ask], answers: Optional[Dict[str, str]]) -> Dict[str, tuple]:
    """The answers that match a question actually asked -> {row: (RULE, what they said)}.

    ⇒ **THE RULE TRAVELS WITH THE ANSWER**, because what an answer MEANS depends on what was
      asked. *"Yes"* to *"should it be created?"* sets an existence; *"a vm"* to *"what is it?"*
      sets a kind. Handing the settler bare text and letting it infer which question it answers
      would be a guess in the one place a person has already been explicit.

    ⇒ **AN ANSWER TO A QUESTION NOBODY ASKED IS IGNORED, NOT APPLIED.** The operator may hold a
      standing answer — from the Encyclopedia — for a hundred words this request never mentions.
      Applying those would settle rows on evidence this request never produced, which is
      indistinguishable from guessing.

    ⇒⇒ **AN OPERATOR ANSWERS ABOUT A WORD; A ROW IS NAMED BY A PHRASE.** Measured the moment this
      was first wired: the question came back about `'a grubnash named alpha'` — the whole span —
      while the answer was filed under `grubnash`, so an exactly-correct answer bound to nothing.
      **The word is what is reusable** (it is what the Encyclopedia keys on, across requests and
      models); the phrase is an artefact of how this sentence happened to be cut.

    ⇒ SO A KEY MATCHES A QUESTION WHEN IT IS THE WHOLE `about` OR A WORD INSIDE IT, and matching
      is on WORD BOUNDARIES: `db` must not answer a question about `dbf`, and a substring test
      would have let it.
    """
    if not answers:
        return {}
    lowered = {str(k).strip().lower(): v for k, v in answers.items()}
    out: Dict[str, str] = {}
    for a in asks:
        if not a.about:
            continue
        about = str(a.about).strip().lower()
        words = {w.strip(".,'\"()") for w in about.split()}
        # the rule-qualified key is the most specific answer and wins outright
        if a.key in lowered:
            out[about] = (a.rule, lowered[a.key])
            continue
        hit = next((lowered[k] for k in (about,) if k in lowered), None)
        if hit is None:
            hit = next((lowered[w] for w in words if w in lowered), None)
        if hit is not None:
            out[about] = (a.rule, hit)
    return out
