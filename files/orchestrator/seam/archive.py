"""archive.py — THE KNOWLEDGE SSOT. What a word IS, and what can be done with the thing.

    the ladder it joins, and there is no model call anywhere in it:

        1  the manifest's `nouns`    the built-in vocabulary        lookup
        2  THE ARCHIVE               what is known / was told       lookup   <- this file
        3  the lab                   what exists right now          lookup
        4  the ASK                   the operator settles it        -> written back into 2

# ⇒⇒ WHY IT EXISTS, AND IT IS THE ONLY TEACHING CHANNEL THAT IS NOT THE CORPUS

The operator, 2026-08-13: *"ALL KNOWLEDGE THE AI MIGHT NEED LIVES THERE … in the form of an
ARCHIVE and PRACTICAL APPLICATION, so you can load this in 'times of peace' or when new data
needs to be taught to the AI WITHOUT MORE CORPUS. It's our data archive — that's why it's
global."*

**THE CORPUS IS SPENT.** Fourteen sentences examined for a full day with every rule written in
view of them; 12/14 is a fit, not a capability. More corpus re-fits the same fourteen. An entry
adds a FACT — no prompt change, no re-fit, no model change — and the next request that mentions
the word is answerable. It is the only lever measured on this project that grows capability by
adding DATA rather than by tuning a knob against one model, which is also why it survives a
model swap ([[gorgon-plug-and-play]]).

# ⇒⇒ THE ADMISSION TEST IS ONE QUESTION

**Is this a fact about ENGLISH, or a fact about THE WORLD?** English is refused — the model
knows it better than any list here ever will, and a wrong entry cannot be repaired by teaching
because the model already knows the language. The world is accepted — the model cannot know
this lab, and a wrong entry IS repairable, which is the whole reason a knowledge store is
allowed where a linguistics list is not ([[gorgon-open-list]]).

# ⇒ THE SHAPE, AND IT MIRRORS THE MANIFEST ON PURPOSE

    entry               printer
    description         what it is                          THE ARCHIVE HALF
    classes/methods/    what can be DONE with it            THE PRACTICAL-APPLICATION HALF
      attributes

**An entry is a manifest-shaped row for a noun the manifest does not have.** Mirroring the
shape is what makes a read-time merge trivial — and it is NOT a licence to write back: the
manifest is the operator's declared design and must stay reviewable, the archive is accumulated
knowledge. **Two stores, merged when read, never merged on disk.**

# ⇒⇒ NOTHING ROUTES UNTIL A PERSON SAYS SO

`known()` returns RATIFIED entries only. A proposal — from an assertive, from an answered ASK,
from a bulk import — describes and does not permit. That is group O's rule arriving from a
different direction: *an unratified entry may DESCRIBE but never PERMIT*. Without it a sentence
would be granting authority, which is [[gorgon-courtesy-escalates-intent]] one layer up: there,
a pleasantry decided the authority rung; here, an unratified sentence would decide what the lab
believes a word means.

⇒ **AND A POISONED SOURCE THEREFORE PRODUCES A BAD SUGGESTION, NEVER A BAD PROGRAM.** That is
  containment by construction rather than by trust, and it is what makes bulk import from an
  external lexicon safe to consider at all.

# ⇒ FOUR PROPERTIES CARRIED OVER FROM THE ISSUE LEDGER, EACH ALREADY PAID FOR

    KEYED BY THE WORD        never the phrase. *'a grubnash named alpha'* once filed an answer
                             under a phrase and bound it to nothing. The WORD is the reusable
                             unit across requests, sessions and models.
    THE WORLD OUTRANKS IT    a remembered fact may only fill a row nothing live settled. A stale
                             memory must never beat the lab.
    NO TIMER, NO SWEEP       `computers means vm` stays true after every vm is deleted, so
                             unlike the book keeper this needs no reconciliation and no lease.
                             Append-only with supersession.
    NEGATIVE ENTRIES COUNT   *"routers are not a thing this lab keeps"* is a valid entry — 7 of
                             20 measured words were that case, and next time the answer is
                             instant instead of another question.
"""
import json
import pathlib
import time
from typing import Dict, List, NamedTuple, Optional, Tuple

# ⇒ WHO SAID IT. Only TOLD entries may ever be ratified into routing; anything from an external
#   source is a SUGGESTION a person confirms. The ledger's own CLAIMED/SEEN split, one store on.
TOLD, IMPORTED = "told", "imported"

PENDING, RATIFIED, SUPERSEDED = "pending", "ratified", "superseded"


class Entry(NamedTuple):
    """One word, what it is, and what can be done with it."""
    word: str                                  # THE REUSABLE PART — never a phrase
    description: str = ""
    classes: Tuple[str, ...] = ()
    methods: Tuple[str, ...] = ()
    attributes: Tuple[str, ...] = ()
    # ⇒ THE KIND THIS WORD RESOLVES TO, when the lab has one. `jumpbox -> vm` is the whole
    #   point of an entry for the seam: it is what turns an unknown noun into a settled row.
    kind: Optional[str] = None
    # ⇒ **THE NEGATIVE ENTRY.** False means *this lab keeps no such thing* — a real answer, and
    #   the one that stops the same question being asked forever.
    holds: bool = True
    source: str = TOLD
    status: str = PENDING
    said: str = ""                             # the sentence it came from — provenance
    who: Optional[str] = None
    at: Optional[float] = None

    @property
    def routes(self) -> bool:
        """May this entry settle a reading? Only if a person ratified it AND it was told."""
        return self.status == RATIFIED and self.source == TOLD


class Archive:
    """The store. Append-only, superseded rather than overwritten, keyed by the word."""

    def __init__(self, path: Optional[str] = None):
        self.path = pathlib.Path(path) if path else None
        self._rows: List[Entry] = []
        if self.path and self.path.exists():
            self.load()

    # ── writing ──────────────────────────────────────────────────────────────────────────
    def propose(self, word: str, description: str = "", kind: Optional[str] = None,
                holds: bool = True, source: str = TOLD, said: str = "",
                who: Optional[str] = None, classes=(), methods=(), attributes=()) -> Entry:
        """File a PENDING entry. It describes; it does not yet permit.

        ⇒ SUPERSESSION RATHER THAN OVERWRITE: the previous ratified entry for a word stays on
          disk and is marked, because *"the real risk is one misspoken answer becoming permanent
          and silent"* and a store you cannot audit backwards cannot answer that.
        """
        word = str(word).strip().lower()
        entry = Entry(word=word, description=str(description).strip(), kind=kind,
                      holds=bool(holds), source=source, status=PENDING, said=str(said),
                      who=who, at=time.time(), classes=tuple(classes),
                      methods=tuple(methods), attributes=tuple(attributes))
        self._rows.append(entry)
        return entry

    def ratify(self, word: str, who: Optional[str] = None) -> Optional[Entry]:
        """The operator's signature. The newest pending entry for a word starts routing."""
        word = str(word).strip().lower()
        fresh = [e for e in self._rows if e.word == word and e.status == PENDING]
        if not fresh:
            return None
        keep = fresh[-1]
        out = []
        for e in self._rows:
            if e.word == word and e.status == RATIFIED:
                e = e._replace(status=SUPERSEDED)      # the old fact is kept, not deleted
            elif e is keep:
                e = e._replace(status=RATIFIED, who=who or e.who)
            elif e.word == word and e.status == PENDING:
                e = e._replace(status=SUPERSEDED)      # an older proposal never silently wins
            out.append(e)
        self._rows = out
        return self.known(word)

    # ── reading ──────────────────────────────────────────────────────────────────────────
    def known(self, word: str) -> Optional[Entry]:
        """The RATIFIED entry for this word, or None. The only reader anything may route on."""
        word = str(word).strip().lower()
        for e in reversed(self._rows):
            if e.word == word and e.routes:
                return e
        return None

    def kind_of(self, word: str) -> Optional[str]:
        """The manifest kind this word resolves to — step 2 of the settling ladder.

        ⇒ A NEGATIVE ENTRY ANSWERS None AND THAT IS NOT THE SAME AS SILENCE. *"routers are not
          a thing this lab keeps"* is a ratified fact; `holds` False says the question is
          settled and the answer is no. A caller that needs to tell the two apart asks `known`.
        """
        entry = self.known(word)
        return entry.kind if entry and entry.holds else None

    def reject(self, word: str) -> int:
        """Refuse every pending proposal for a word. Returns how many were dropped.

        ⇒ REFUSED, NOT DELETED — same reason as supersession. *"who told it that, and when
          did we say no"* is a question the store has to be able to answer.
        """
        word = str(word).strip().lower()
        n = 0
        out = []
        for e in self._rows:
            if e.word == word and e.status == PENDING:
                e, n = e._replace(status=SUPERSEDED), n + 1
            out.append(e)
        self._rows = out
        return n

    def pending(self) -> List[Entry]:
        """Everything waiting for a person. The audit surface reads this."""
        return [e for e in self._rows if e.status == PENDING]

    def ratified(self) -> List[Entry]:
        """Everything that currently routes. The other half of the audit surface."""
        return [e for e in self._rows if e.routes]

    def rows(self) -> List[Entry]:
        return list(self._rows)

    # ── persistence ──────────────────────────────────────────────────────────────────────
    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([e._asdict() for e in self._rows], indent=2))

    def load(self) -> None:
        try:
            rows = json.loads(self.path.read_text())
        except Exception:
            return
        self._rows = [Entry(**{**r, "classes": tuple(r.get("classes") or ()),
                               "methods": tuple(r.get("methods") or ()),
                               "attributes": tuple(r.get("attributes") or ())})
                      for r in rows if isinstance(r, dict) and r.get("word")]


def _home() -> str:
    """Where the archive lives. `GORGON_HOME` then `~/.gorgon`, the same convention the
    creation ledger uses — one storage root, asked rather than re-derived."""
    import os
    base = os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon")
    return os.path.join(base, "archive.json")


# ⇒ THE PROCESS-WIDE ARCHIVE, mirroring `books.LEDGER`. Loaded on first import and saved by
#   whoever writes — a store nobody can find is a store nobody audits, and the audit surface
#   is the point ([[gorgon-encyclopedia]]: *"the real risk is one misspoken answer becoming
#   permanent and silent"*).
ARCHIVE = Archive(_home())


# ── the first writer: an operator teaching, unprompted ───────────────────────────────
def taught_by(request: str, board=None, world=None) -> List[dict]:
    """What an ASSERTIVE in this request offers to teach. Proposals, never entries.

    ⇒⇒ **AN ASSERTIVE IS THE OPERATOR TEACHING, AND UNTIL NOW IT PRODUCED NOTHING.** *"n1 is
      the jumpbox"* was read correctly as a statement and then dropped on the floor — the
      highest-value input the system can receive, discarded because there was nowhere to put
      it. `speech_act` says which clauses are statements; this says what they offer.

    ⇒ **IT DECLINES FAR MORE THAN IT ACCEPTS, AND THAT IS THE DESIGN.** Every refusal below is
      a case where a guess would file a wrong fact permanently, and the store's whole value is
      that its entries are true:

        the subject is not ONE word     *"the red vms are the ones on mesh0"* defines a SET, not
                                        a word. Keyed by the word or not at all — the ledger
                                        paid for that rule already.
        the subject is a pronoun        *"yes, it's a label"* would key an entry on `it`.
        the predicate is DEONTIC        *"snapshots are never to be deleted without asking me"*
                                        is a RULE, not a fact. It belongs to the referendum,
                                        and filing it here would record an obligation as a
                                        description.
        the predicate is NEGATED        *"no, n1 is not a vm"* is an ANSWER, and
                                        `reading_answers.settle` owns those.

    ⇒ **AND WHAT IT RETURNS IS A PROPOSAL DICT, NOT AN ENTRY.** Nothing here touches a store:
      the caller decides whether to file, exactly as gate 4 returns findings rather than acting
      on them. Reading and writing stay separable.
    """
    from planner.formula.legal import Board
    from . import speech_act
    from .reading_answers import NEGATION
    from .scan import DEFINITE, INDEFINITE, NOVEL, UNIVERSAL

    board = board or Board()
    # ⇒ THE DEONTIC MARKERS — obligation, not description. Modals are the SAME closed auxiliary
    #   class `speech_act` already reads; `never`/`always` are frequency adverbs. Both closed,
    #   and both used here only to REFUSE, which is the safe direction for a marker set.
    deontic = {"must", "should", "shall", "may", "never", "always", "ought"}
    determiners = set(DEFINITE) | set(INDEFINITE) | set(UNIVERSAL) | set(NOVEL)

    out: List[dict] = []
    for clause, act in speech_act.read(request, board, world):
        if act != speech_act.ASSERTIVE:
            continue
        words = speech_act.words_of(clause)
        split = next((i for i, w in enumerate(words) if w in speech_act.COPULA), None)
        if split is None:
            continue
        subject = [w for w in words[:split] if w not in determiners]
        predicate = words[split + 1:]
        if len(subject) != 1 or subject[0] in speech_act.PRONOUNS:
            continue                       # a set, a phrase, or a pronoun — not a word
        if any(w in deontic for w in predicate) or any(w in NEGATION for w in words):
            continue                       # a rule, or an answer — neither is a description
        if not predicate:
            continue
        # ⇒ THE KIND, WHEN THE LAB ALREADY HAS ONE. `a jumpbox is a VM` binds the new word to a
        #   manifest kind, which is what makes the entry able to settle a reading later. When
        #   the predicate names no kind the entry is still worth keeping — it just describes.
        from .scan import _index
        index = _index(board)
        kind = next((index[w] for w in predicate if w in index), None)
        out.append({"word": subject[0],
                    "description": " ".join(predicate),
                    "kind": kind,
                    "said": clause.strip()})
    return out
