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
    # ⇒⇒ **AND THE WORD MAY NAME A PROPERTY RATHER THAN A THING.** The operator, 2026-08-16:
    #   *"the ram and cores — its because the AI needs to correlate ram with an encyclopedia
    #   entry as well as it being an attribute."* The manifest aliases the property words it
    #   happens to know; `vram`, `nics` and `disk size` it does not, and until this field the
    #   archive could only teach *"X is a KIND"* — so a word naming a property was unteachable.
    #   ⇒ SYMMETRIC WITH `kind` ON PURPOSE, including the class walk: `vram is memory` plus
    #     `memory` being the attribute reaches the manifest through two ordinary sentences.
    attribute: Optional[str] = None
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

    def attribute_of(self, word: str, _seen=None) -> Optional[str]:
        """The manifest ATTRIBUTE this word resolves to — through its classes, like `kind_of`.

        ⇒ **RATIFIED-AND-TOLD ONLY**, through `known`, which is the archive's whole safety
          property: a proposal DESCRIBES and never PERMITS. An unsigned *"vram is memory"*
          settles nothing.
        ⇒ ⚠ CYCLE-SAFE BY CONSTRUCTION, for the reason `kind_of` states: two true-sounding
          sentences must not hang the seam.
        """
        word = str(word).strip().lower()
        seen = _seen or set()
        if word in seen:
            return None
        seen.add(word)
        entry = self.known(word)
        if entry is None:
            return None
        if entry.attribute:
            return entry.attribute
        for other in entry.classes:
            got = self.attribute_of(other, seen)
            if got:
                return got
        return None

    def kind_of(self, word: str, _seen=None) -> Optional[str]:
        """The manifest kind this word resolves to — THROUGH ITS CLASSES, not only directly.

        ⇒⇒ **`kaya is a printer` HAS TO MEAN SOMETHING, AND IT ONLY CAN IF `printer` IS ALSO AN
          ENTRY.** The operator, 2026-08-16. A word that resolves only when the predicate
          happens to name a MANIFEST kind is a store that can learn `kaya is a vm` and nothing
          else — and the whole design is *a manifest-shaped row for a noun the manifest does
          not have*. So an entry may name a CLASS, and the class may be another entry:

              kaya    -> classes ('printer',)
              printer -> kind 'vm'
              ⇒ kaya resolves to vm, and everything the lab can do to a vm it can do to kaya

        ⇒ **A DIRECT KIND STILL WINS, AND THE WALK IS THE FALLBACK.** `kaya is a vm` needs no
          chain, and a chain must never override something said plainly.

        ⇒ ⚠ **CYCLE-SAFE BY CONSTRUCTION.** *"a is a b"* and *"b is an a"* are both sayable, and
          two true-sounding sentences must not hang the seam. `_seen` is the whole guard.

        ⇒ A NEGATIVE ENTRY ANSWERS None AND THAT IS NOT THE SAME AS SILENCE. *"routers are not
          a thing this lab keeps"* is a ratified fact; `holds` False says the question is
          settled and the answer is no. A caller that needs to tell the two apart asks `known`.
        """
        entry = self.known(word)
        if entry is None or not entry.holds:
            return None
        if entry.kind:
            return entry.kind
        seen = set(_seen or ())
        seen.add(str(word).strip().lower())
        for cls in entry.classes:
            cls = str(cls).strip().lower()
            if cls in seen:
                continue                       # "a is a b, b is an a" — say nothing, do not hang
            found = self.kind_of(cls, seen)
            if found:
                return found
        return None

    def classes_of(self, word: str) -> Tuple[str, ...]:
        """The chain of classes this word belongs to, nearest first. Empty when it has none."""
        out: List[str] = []
        seen = set()
        cur = str(word).strip().lower()
        while cur and cur not in seen:
            seen.add(cur)
            entry = self.known(cur)
            if entry is None or not entry.holds or not entry.classes:
                break
            cur = str(entry.classes[0]).strip().lower()
            out.append(cur)
        return tuple(out)

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

    def retract(self, word: str) -> Optional[Entry]:
        """WITHDRAW a ratified entry. It stops routing; the record stays.

        ⇒⇒ **THE STORE COULD BE CHANGED AND NOT UNSAID, AND THAT IS THE WRONG HALF TO HAVE.**
          `ratify` supersedes the old entry when a new one replaces it, and `reject` drops a
          PENDING proposal — so a wrong fact could be overwritten but never simply withdrawn.
          The operator asked the question directly and it had no answer.

        ⇒ **IT IS THE EXACT RISK THIS STORE WAS DESIGNED AROUND**, in its own words: *"the real
          risk is one misspoken answer becoming permanent and silent."* A signature you cannot
          take back is not a signature, it is a trapdoor — and an archive is meant to be the
          repairable SSOT, the one whose wrong entries are fixable BY TEACHING. Unfixable
          entries would make it the other kind of list.

        ⇒ AND NOTHING IS DELETED, for the same reason supersession keeps the old row: *who told
          it that, and when did we take it back* has to stay answerable.
        """
        word = str(word).strip().lower()
        gone = self.known(word)
        if gone is None:
            return None
        self._rows = [e._replace(status=SUPERSEDED) if e is gone else e for e in self._rows]
        return gone

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


# ⇒⇒ WHAT A STATEMENT ASKS THE ARCHIVE TO DO. One vocabulary for the four effects, so a caller
#   routes on a value rather than re-reading the sentence.
TEACH, FORGET, CONTRADICTS = "teach", "forget", "contradicts"

from ..codex import FORGET_VERBS
OPERATION_VERBS: Dict[str, Tuple[str, ...]] = {
    FORGET: FORGET_VERBS,
}

# ⇒⇒ **AND WHERE THE TWO REMOVALS MEET, THE OBJECT DECIDES — AND WHEN IT CANNOT, WE ASK.**
#   The operator: *"we can also use context to understand what the user is demanding but we can
#   also ASK."* `delete kaya` is one sentence and two operations:
#
#       delete kaya   kaya is a MACHINE the lab holds     -> destroy the thing (the lab's)
#       delete kaya   kaya is only a WORD we were taught  -> ambiguous. It could be either, and
#                                                            one of them cannot be undone.
#
#   ⇒ **SO A LAB DELETER OVER AN ARCHIVE-ONLY WORD IS A QUESTION, NEVER A GUESS.** The same
#     asymmetry as every gate here: forgetting a word you meant to delete costs a re-teach;
#     deleting a machine you meant to forget cannot be taken back.
AMBIGUOUS_REMOVAL = "ambiguous-removal"


def effect_of(request: str, board=None, world=None, store=None) -> List[dict]:
    """Every `words` operation this request performs IN SENTENCE FORM.

    ⇒⇒ **THE OPERATOR'S OWN SPEC, 2026-08-16:** *"in a statement sentence you can do all the
      commands `words` do … all `words` commands are reachable in sentence form."*

        from now on kaya means a vm    TEACH        a new entry
        kaya is now a network          TEACH        changing a declared fact
        kaya isn't a vm                CONTRADICTS  disagrees with what is on file -> ASK
        kaya doesn't exist             FORGET
        forget kaya                    FORGET

    ⇒⇒ **AND IT IS SIGNED IMMEDIATELY, WHICH CORRECTS A POSITION I ARGUED.** I wrote that
      ratification must never be automatic. Wrong as stated: the danger was never *a person
      stating a fact*, it was an IMPORTED or INFERRED entry routing with nobody answering for
      it — and `Entry.source` already draws exactly that line. **The signature is not the
      ceremony, it is who spoke.** The operator's own words ARE the signing; a bulk lexicon
      still needs a person.

    ⇒ **THE ASK MOVES FROM ASSERTION TO CONTRADICTION**, which is kinder and no weaker: do not
      interrupt someone teaching you something new — interrupt them when the new fact disagrees
      with one already on file. `known(word)` is exactly that test, and it is the only case
      worth a question.

    ⇒ ⚠ **WHAT IS STRUCTURAL HERE AND WHAT IS NOT, SAID PLAINLY.** The teach and contradict
      readings are closed-class throughout — a copula, a negation, a determiner. The REMOVAL
      needs a verb, and two of the three (`delete`, `remove`) are the manifest's own destructive
      verbs while `forget` is one word that is not. That is a one-entry English list and it is
      declared rather than hidden; it is the smallest thing that makes the operator's own
      phrasing work, and [[gorgon-open-list]]'s A3 is the standing warning about growing it.
    """
    from planner.formula.legal import Board
    from . import speech_act
    from .issues import word_of
    from .reading_answers import NEGATION

    board = board or Board()
    archive = ARCHIVE if store is None else store
    out: List[dict] = []

    # ⇒ TWO SOURCES, EACH ANSWERING FOR ITS OWN STORE: the manifest's deleters say how the LAB
    #   removes something, and `OPERATION_VERBS` says how the ARCHIVE does. Neither is guessed
    #   and neither is a fact about English — see the note at the declaration.
    from planner.ir import config as _config, effects as _effects
    lab_removers = {str(t).split("_")[0].lower() for t in _effects.deleters(_config.KINDS)}
    ours = set(OPERATION_VERBS[FORGET])
    removers = lab_removers | ours

    for clause, act in speech_act.read(request, board, world):
        words = speech_act.words_of(clause)
        if not words:
            continue
        negated = any(w in NEGATION for w in words)
        head = speech_act._after_openers(words)
        head = head[0] if head else ""

        # ⇒ 1 · REMOVAL BY IMPERATIVE — *"forget kaya"*. The object is a word, not a lab thing,
        #   which is what makes it addressed to the archive at all.
        if head in removers:
            word = word_of(" ".join(w for w in words if w not in removers), board)
            if word:
                # ⇒ AN ARCHIVE VERB IS UNAMBIGUOUS; A LAB DELETER OVER A WORD WE WERE ONLY
                #   TAUGHT is two operations wearing one sentence — see `AMBIGUOUS_REMOVAL`.
                if head in ours:
                    out.append({"op": FORGET, "word": word, "said": clause.strip()})
                elif archive.known(word) is not None:
                    out.append({"op": AMBIGUOUS_REMOVAL, "word": word,
                                "said": clause.strip()})
            continue

        # ⇒⇒ 2/3 · A DENIAL, AND **WHAT IT NAMES DECIDES WHICH KIND IT IS.** No word list at
        #   all — the first cut needed one for *"exist"*, and the split is structural:
        #
        #       kaya isn't a vm        the denial NAMES A KIND     -> CONTRADICTS the entry
        #       kaya doesn't exist     the denial names NOTHING    -> WITHDRAWS the word
        #
        #   ⇒ AND EITHER WAY, ONLY WHEN SOMETHING IS ON FILE TO DENY. A denial about a word
        #     nobody ever taught is not a correction, it is noise.
        #   ⇒ ⚠ **AND IT IS NOT GATED ON A COPULA.** The first cut required one, so *"kaya
        #     doesn't exist"* — which predicates with a lexical verb over the auxiliary `does`
        #     — fell through unread. What identifies a denial is the NEGATION plus a subject
        #     already on file; the copula was a proxy for that and a leaky one.
        #   ⇒ **A DIRECTIVE IS EXCLUDED, THOUGH**, because *"don't delete kaya"* is a
        #     prohibition about the LAB and not a statement about the word.
        if negated and act not in (speech_act.DIRECTIVE_ACT, speech_act.DIRECTIVE_INFORM):
            word = word_of(" ".join(w for w in words if w not in NEGATION), board)
            on_file = archive.known(word) if word else None
            if on_file is not None:
                from .scan import _index
                index = _index(board)
                rest = [w for w in words
                        if w not in NEGATION and w not in speech_act.COPULA and w != word]
                names_a_kind = any(w in index or archive.known(w) for w in rest)
                if names_a_kind:
                    out.append({"op": CONTRADICTS, "word": word, "said": clause.strip(),
                                "on_file": on_file.description})
                else:
                    out.append({"op": FORGET, "word": word, "said": clause.strip()})
            continue

        # ⇒ 4 · TEACHING — the assertive reader owns it, and this adds nothing to that rule.
        if act == speech_act.ASSERTIVE:
            for proposal in taught_by(clause, board, world):
                out.append({"op": TEACH, **proposal})
    return out


def apply_effects(effects: List[dict], who: str = "operator", store=None) -> List[str]:
    """Carry out what a statement asked for, and say what happened in the operator's terms.

    ⇒ **TEACH AND FORGET ARE PERFORMED; CONTRADICTS IS NEVER PERFORMED.** A disagreement is a
      question, and answering it by picking one of the two facts is exactly the guessing every
      gate in this seam exists to avoid.
    """
    archive = ARCHIVE if store is None else store
    said: List[str] = []
    for eff in effects:
        word = eff.get("word")
        if eff["op"] == TEACH:
            archive.propose(word, eff.get("description", ""), kind=eff.get("kind"),
                            classes=eff.get("classes") or (), said=eff.get("said", ""),
                            who=who, source=TOLD)
            entry = archive.ratify(word, who=who)          # THE OPERATOR'S OWN WORDS SIGN IT
            said.append(f"noted — {word!r} is {eff.get('description','')}"
                        + (f" (kind {entry.kind})" if entry and entry.kind else ""))
        elif eff["op"] == FORGET:
            gone = archive.retract(word)
            archive.reject(word)
            said.append(f"forgotten — {word!r}" if gone
                        else f"nothing on file for {word!r}")
        elif eff["op"] == AMBIGUOUS_REMOVAL:
            said.append(f"{word!r} is a word you taught me, and {eff.get('said')!r} could mean "
                        f"forget the word or delete the thing. Nothing was done — which?")
        elif eff["op"] == CONTRADICTS:
            said.append(f"you told me {word!r} is {eff.get('on_file')!r}, and this says "
                        f"otherwise — which stands?")
    return said


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


def asked_about(request: str, board=None, world=None, store=None) -> List[str]:
    """Answers to *"what is X?"* — read straight out of the archive, with no program at all.

    ⇒⇒ **THE ONE QUESTION SHAPE THAT NEEDS NO QUERY.** *"how many vms are running"* becomes a
      program the engine runs against the lab. *"what is kaya?"* is answered by a lookup here
      and nothing else — there is no select to write, because `kaya` is not a thing the lab
      keeps, it is a WORD the lab was taught.

    ⇒ **AND `nothing on file` IS AN ANSWER, NOT A FAILURE.** It is the honest reply, it is
      instant, and it tells the operator exactly what to do about it — which is the same
      three-valued honesty a kindless row already has.

    ⇒ IT READS THE RATIFIED STORE ONLY, so a pending proposal does not answer as though it were
      known. A question must not be answered with something nobody signed.
    """
    from planner.formula.legal import Board
    from . import speech_act
    from .issues import word_of

    board = board or Board()
    archive = ARCHIVE if store is None else store
    out: List[str] = []
    for clause, act in speech_act.read(request, board, world):
        if act != speech_act.DIRECTIVE_INFORM:
            continue
        if speech_act.answer_shape(clause, board) != speech_act.MEANING:
            continue
        # ⇒⇒ **THE INTERROGATIVE FRAME COMES OFF FIRST, AND ONLY THEN THE SUBTRACTION.**
        #   `word_of` was written for a declarative phrase — *"a jumpbox named alpha"* — and
        #   knows nothing about wh-words, so asked directly it answered `'what'` for every
        #   question. Stripping the frame is not a second rule: it is the SAME closed classes
        #   `speech_act` already reads, removed before the ledger's rule runs on what is left.
        #   ⇒ Then `word_of` takes the HEAD of the remainder, which is the word being asked
        #     about — *"what is kaya now?"* leaves `kaya now` and answers `kaya`.
        frame = (speech_act.WH_WORDS | speech_act.AUXILIARIES | speech_act.OPENERS)
        rest = " ".join(w for w in speech_act.words_of(clause) if w not in frame)
        word = word_of(rest, board)
        if not word:
            continue
        entry = archive.known(word)
        if entry is None:
            out.append(f"nothing on file for {word!r} — say what it is and I will remember it")
        elif not entry.holds:
            # ⇒ THE DESCRIPTION IS ONLY ADDED WHEN IT SAYS SOMETHING THE SENTENCE DOES NOT.
            #   A negative entry's own text is usually *"not a thing this lab keeps"*, and
            #   printing both reads as a stutter.
            extra = entry.description.strip()
            said = f"{word!r} is not a thing this lab keeps"
            out.append(f"{said} — {extra}" if extra and extra.lower() not in said.lower()
                       else said)
        else:
            out.append(f"{word!r} is {entry.description}"
                       + (f" (kind {entry.kind})" if entry.kind else ""))
    return out


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
        # ⇒⇒ **A CONDITION IS NOT AN ASSERTION.** *"IF the vm is stopped, launch it"* predicates
        #   exactly like a statement and asserts nothing — it names the case in which to act.
        #   Filing it would teach *"a vm is stopped"* as a permanent fact from a sentence that
        #   said no such thing.
        #   ⇒ ⚠ **IT WAS ALREADY SAFE, BY ACCIDENT, AND THAT IS WHY THIS IS EXPLICIT.** `if`
        #     survives the determiner strip and made the subject two words, so the one-word
        #     test declined it. A guard that holds because of an unrelated rule is a guard that
        #     disappears the first time the unrelated rule changes.
        if words and words[0] in speech_act.CONJUNCTIONS:
            continue
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
        # ⇒⇒ **AND WHEN THE PREDICATE NAMES NO MANIFEST KIND, IT NAMES A CLASS.** *"kaya is a
        #   printer"* binds `kaya` to `printer`, and `printer` may be an entry of its own with
        #   its own kind, methods and attributes. Without this the store could learn *"kaya is
        #   a vm"* and nothing else — and the design is a manifest-shaped row for a noun the
        #   manifest does NOT have.
        #   ⇒ THE HEAD OF THE PREDICATE, by the same subtraction the rest of the seam uses:
        #     determiners off, and never the word itself (*"a vm is a vm"* is not a class).
        classes: Tuple[str, ...] = ()
        if kind is None:
            head = [w for w in predicate if w not in determiners]
            if head and head[0] != subject[0]:
                classes = (head[0],)
        out.append({"word": subject[0],
                    "description": " ".join(predicate),
                    "kind": kind,
                    "classes": classes,
                    "said": clause.strip()})
    return out
