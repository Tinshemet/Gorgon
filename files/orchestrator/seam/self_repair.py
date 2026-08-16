"""self_repair.py — THE OPERATOR TAKING BACK WHAT THEY JUST SAID, WITHIN ONE TURN.

    stop alpha — sorry, i meant beta        a CORRECTION: alpha is withdrawn, beta replaces it
    stop the vms. actually, never mind      a RETRACTION: the request is withdrawn entirely

# ⇒⇒ WHY THIS IS ITS OWN MODULE AND NOT PART OF `repair.py`

`repair.py` computes a fix to a PROGRAM where the manifest names exactly one. This is about the
REQUEST — the operator amending their own contribution — which conversation analysis calls
SELF-REPAIR and ISO 24617-2 files under *Own Communication Management*. Two different things
called repair, and one name between them is how a term drifts.

# ⇒⇒ THE GRID, AND WE HAD ALREADY BUILT ONE CELL OF IT WITHOUT KNOWING

Schegloff, Jefferson & Sacks give four kinds, by WHO INITIATES and WHO REPAIRS:

    self-initiated  self-repair    *"stop alpha — sorry, i meant beta"*        THIS FILE
    self-initiated  other-repair   *"stop the… what's it called"*             not read
    other-initiated self-repair    **every gate-2 ASK** — *what is `n1`?*     BUILT, unnamed
    other-initiated other-repair   we correct them outright                   never, by design

⇒ **THE THIRD ROW IS THE ONE WORTH SAYING OUT LOUD.** Every question the seam puts to the
  operator is an other-initiated repair INITIATION: *I could not read this part, you fix it.*
  The machinery has existed for weeks and naming it that way is what showed the other three.

# ⇒⇒ THE TWO CASES GET DIFFERENT TREATMENTS, AND THE REASON IS SAFETY

    A RETRACTION IS UNAMBIGUOUS.   *"never mind"* withdraws, and withdrawing is a complete
                                   instruction. It is acted on: the request is HELD.
    A CORRECTION IS NOT.           *"stop alpha — sorry, i meant beta"* substitutes a
                                   CONSTITUENT, and knowing WHICH one needs alignment. Getting
                                   that wrong stops the wrong machine, which is the exact
                                   failure this file exists to prevent. **So it is reported and
                                   ASKED, never silently substituted.**

⇒ ⚠ **AND THE MEASURED HARM IS ON THE RETRACTION SIDE ALREADY.**
  [[gorgon-confirm-answer-rule]] — the word *cancel* once CREATED A VM. A rule now guards the
  confirm PROMPT; a retraction arriving as an ordinary turn has been unread ever since.

# ⇒ THE MARKERS ARE A CLOSED CLASS AND THE CUT-OFF IS STRUCTURAL

Repair markers are closed in the strong sense — English has these and gains none — which is the
same licence `speech_act.WH_WORDS` claims. And Schegloff notes that self-initiated repair is
launched by a NON-LEXICAL initiator as often as a lexical one: a cut-off, a dash, a
self-interruption. That half needs no vocabulary at all.

⇒ ⚠ **`sorry` IS NOT A MARKER ON ITS OWN AND MUST NOT BE.** *"sorry to bother you, restart
  alpha"* is an APOLOGY — ISO files it under Social Obligations Management — and treating it as
  a repair would hold a request nobody withdrew. The marker is `i mean` / `i meant`; `sorry`
  merely often precedes one.
"""
import re
from typing import NamedTuple, Optional

# ⇒ WHAT WITHDRAWS THE WHOLE REQUEST. Complete instructions in themselves.
RETRACTIONS = ("never mind", "nevermind", "forget it", "forget that", "cancel that",
               "disregard that", "disregard it", "ignore that", "scratch that",
               "belay that", "as you were")

# ⇒ WHAT REPLACES PART OF IT. `i mean` is the core; the rest are the frames it appears in.
#   ⇒ ⚠ `sorry` IS ABSENT ON PURPOSE — see the module note.
CORRECTIONS = ("i mean", "i meant", "no wait", "wait no", "rather", "correction",
               "make that", "or rather", "not that")

# ⇒ THE NON-LEXICAL INITIATOR. A dash or an ellipsis is a CUT-OFF — the speaker interrupting
#   themselves — and it is structure rather than vocabulary. It only counts BESIDE a marker;
#   a dash on its own is punctuation.
_CUTOFF = re.compile(r"[—–]|\.\.\.|--")

REPAIRED, RETRACTED = "repaired", "retracted"

# ⇒⇒ **A WORD THAT CANNOT END AN UTTERANCE.** A speaker who breaks off mid-constituent has
#   abandoned the phrase — `just at the`, `there's`, `i'll`, `and it's got a`. Determiners,
#   prepositions, auxiliaries and conjunctions all DEMAND a complement, so ending on one is
#   structure telling you the turn was cut short. No vocabulary of repair words is involved.
DANGLING = frozenset({
    "the", "a", "an", "this", "that", "these", "those", "my", "your", "its", "their",
    "at", "on", "in", "to", "of", "with", "from", "by", "for", "into", "onto", "over",
    "and", "or", "but", "so", "just", "very", "quite",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "will", "would", "can", "could", "shall", "should", "do", "does",
    "i'll", "i've", "i'm", "there's", "we're", "we'll", "you're", "it's", "that's",
})


class Mend(NamedTuple):
    """A repair the operator made to their own request, inside one turn."""
    kind: str          # repaired · retracted
    marker: str        # the phrase that signalled it
    withdrawn: str     # what is being taken back
    offered: str       # what replaces it — empty for a retraction

    def __repr__(self) -> str:
        if self.kind == RETRACTED:
            return f"RETRACTED via {self.marker!r}: {self.withdrawn!r}"
        return f"REPAIRED via {self.marker!r}: {self.withdrawn!r} -> {self.offered!r}"


def _trim(text: str) -> str:
    """The trouble source, without the apology or the cut-off that introduced the repair.

    ⇒ *"stop alpha — sorry"* is what the split leaves behind, and the operator reading the ASK
      should see *"stop alpha"*. The apology belongs to Social Obligations Management, not to
      the thing being withdrawn.
    """
    out = _CUTOFF.split(str(text))[0].strip(" ,.—–")
    return re.sub(r"[\s,]*\b(sorry|oops|my bad|apologies)\b[\s,]*$", "", out).strip(" ,.—–")


def _find(low: str, phrases) -> Optional[tuple]:
    """The EARLIEST marker and where it sits — earliest, because a repair applies to what came
    before it, and a later one would take the first repair's own words as its trouble source."""
    best = None
    for phrase in phrases:
        for m in re.finditer(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", low):
            if best is None or m.start() < best[1]:
                best = (phrase, m.start(), m.end())
    return best


def read(request: str) -> Optional[Mend]:
    """The repair this turn makes to itself, or None.

    ⇒ **RETRACTION IS TESTED FIRST**, because *"scratch that"* appears in both lists and
      withdrawing is the safer reading of an ambiguous marker: a request held is a question,
      and a request substituted wrongly is the wrong machine.
    """
    low = str(request).lower()
    got = _find(low, RETRACTIONS)
    if got:
        marker, at, _end = got
        return Mend(RETRACTED, marker, _trim(str(request)[:at]) or str(request).strip(), "")
    # ⇒ THE DISFLUENT FORM IS TESTED AFTER THE LEXICAL ONE, because *"stop alpha — sorry, i
    #   meant beta"* carries BOTH a cut-off and a marker, and the marker says more.
    got = _find(low, CORRECTIONS)
    if not got:
        by_shape = restarted(request)
        if by_shape:
            return by_shape
    if got:
        marker, at, end = got
        return Mend(REPAIRED, marker, _trim(str(request)[:at]),
                    str(request)[end:].strip(" ,.—–"))
    return None


def broke_off(segment: str) -> bool:
    """Did this segment stop mid-constituent? Structure, and no repair vocabulary at all.

    ⇒⇒ **MEASURED AND DELIBERATELY NOT USED ALONE, WHICH IS THE POINT OF THIS NOTE.** Against
      DialogBank's 31 gold self-corrections it catches 7 — 22% — and fires on 21 segments the
      gold files elsewhere, for a precision of 25%. **A detector that is wrong three times in
      four is worse than the zero it replaces**, so it is one half of a pair and never a rule.
    """
    from .scan import _tokens
    words = [w for w, _s, _e in _tokens(str(segment).lower())]
    return bool(words) and words[-1] in DANGLING


def restarted(request: str) -> Optional[Mend]:
    """A fragment the speaker ABANDONED and then redid, inside one turn.

    ⇒⇒ **THE OPERATOR, 2026-08-16: *"fix the self-correction, its fragments not markers."***
      Right, and the gold proves it: 27 of 31 self-corrections are `go`, `you're pass`,
      `vertically in line` — abandoned fragments, not *"sorry, i meant"*. The lexical reader
      built in Phase 4 scores **0 of 31** on real dialogue.

    ⇒ **THE SIGNAL IS THE RESTART, NOT THE FRAGMENT.** `go` alone is a complete imperative; it
      is a self-correction only because the speaker said it and then began again. So the pair
      is what is read: a clause that BREAKS OFF, immediately followed by one that RESUMES it —
      sharing its opening word, or picking up where it stopped.

    ⇒ ⚠ **AND THIS CANNOT BE MEASURED ON THE MAP TASK CORPUS, WHICH IS SAID HERE RATHER THAN
      DISCOVERED LATER.** DialogBank hands us ONE functional segment at a time, so the fragment
      and its restart arrive as two separate rows and the pair is never visible. It is
      detectable in what an OPERATOR TYPES — a whole turn — which is the input this system
      actually takes.
    """
    from .scan import _tokens
    # ⇒⇒ **THE SEPARATOR DECIDES HOW MUCH EVIDENCE A REPEAT IS**, and without that distinction
    #   *"stop alpha, stop beta"* — a perfectly ordinary two-clause request — reads as a
    #   disfluency. A CUT-OFF is the speaker interrupting themselves, so a repeat after one is
    #   a restart on its own; after a COMMA the head must also break off mid-constituent.
    pieces = re.split(r"([—–]|--|\.\.\.|,)", str(request))
    parts, seps = [], []
    for i, piece in enumerate(pieces):
        if i % 2 == 0:
            if piece.strip():
                parts.append(piece.strip())
                seps.append(pieces[i - 1] if i else "")
        # odd indices are the separators themselves
    for i in range(len(parts) - 1):
        head, tail = parts[i], parts[i + 1]
        cut = seps[i + 1] not in (",", "")
        if not (broke_off(head) or cut):
            continue
        hw = [w for w, _s, _e in _tokens(head.lower())]
        tw = [w for w, _s, _e in _tokens(tail.lower())]
        if not hw or not tw:
            continue
        # ⇒ A RESTART RESUMES: it opens on the same word the abandoned run opened on, or it
        #   repeats the word the speaker stalled on. Anything else is a new clause.
        if tw[0] == hw[0] or (len(hw) > 1 and tw[0] == hw[-2]):
            return Mend(REPAIRED, "restart", head, tail)
    return None


def cut_off(request: str) -> bool:
    """Did the speaker interrupt themselves? Structure, not vocabulary.

    ⇒ It does not signal a repair ON ITS OWN — a dash is punctuation — but beside a marker it
      is the non-lexical initiator conversation analysis names, and it is the half that costs
      no word list.
    """
    return bool(_CUTOFF.search(str(request)))
