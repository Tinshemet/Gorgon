"""THE SPAN-GRAIN RESIDUE CHECK — a word inside a declaration that no field consumed.

    THE OPERATOR, 2026-08-09: *"the GATE assumes all residue is needed, so we need to filter
    unneeded stuff"* · *"maybe if they correlate to world? a grubnash isn't a descriptor that
    correlates to anything, at best, a name or label."*

# ⇒ WHY THE EXISTING CHECK CANNOT SEE THIS

Gate 1 asks which words of the REQUEST no span claimed. That catches a dropped clause, and it
is structurally blind to a word swallowed INSIDE a span:

    'create a grubnash vm and add it to a grubnash network'
      a grubnash vm        vm       —      <- modifiers 'grubnash', conditions {}
      a grubnash network   network  —      <- modifiers 'grubnash', conditions {}
      BOTH GATES RETURN NOTHING

The spans cover `grubnash` at both positions, so nothing is left over and nothing bounces. Two
objects were invented out of a word that means nothing, and every check passed.

⇒ **SO THE LEFTOVER CHECK RUNS AT TWO GRAINS.** The request grain asks *which words did no
  SPAN claim*; the span grain asks *which words inside a span did no CONDITION claim*. Same
  rule — nothing may be left over — applied one level down.

# ⇒⇒ AND THE FILTER IS THE SLOT, NEVER THE MEANING

The gate must not start judging what words mean ([[gorgon-gates-check-legality]]). It does not
have to. **A word is junk when the slot it landed in has a CLOSED list of legal fillers and it
is not one of them** — which is a lookup, not an opinion:

    NAMING SLOT      'a vm named grubnash'   OPEN     any string is a legal name   -> silent
    DESCRIPTOR SLOT  'a grubnash vm'         CLOSED   attributes and their values  -> ASK
    OPERATION SLOT   'grubnash the vm'       CLOSED   the manifest's verbs         -> ASK

Same word, three positions, three verdicts, and nothing ever asks what `grubnash` means.

# ⇒ THE THREE DESTINATIONS, WHICH IS THE POINT THE OPERATOR WAS MAKING

    BOUNCE      the word correlates — quoted as a value here, a declared value, or an object
                the lab actually has. The reading missed a clause it had already read, so it
                goes BACK TO THE MODEL.
    ASK         nothing correlates. Only an OPEN slot could hold it, so only the operator can
                say — *"a name, a label, or noise"* — and it is a CLOSED CHOICE (rule W7b),
                never *"what does this mean"*.
    RELATIONAL  the word carries a SET OPERATION rather than a description. Pass 2's.

⇒ **AND BOUNCING JUNK WOULD BE WORSE THAN SILENCE.** Told *"you did not account for
  grubnash"*, the model will find it a job, because it always can. Every hole closed here has
  moved rather than shut ([[gorgon-hallucination-was-load-bearing]]); routing by slot is what
  stops this one moving.
"""
import re
from typing import Dict, List, NamedTuple, Optional, Tuple

from planner.formula.legal import Board
from orchestrator.seam import pass1, schema as S
from orchestrator.seam.scan import (COMPARATORS, GRAMMAR, LINKING, NAMING_CUES, _operation_words, _stem, scan)

BOUNCE, ASK, RELATIONAL, REJECT = "BOUNCE", "ASK", "RELATIONAL", "REJECT"

# ⇒ A CLOSED CLASS OF ENGLISH, AND IT IS THE WEAKEST THING IN THIS FILE — SAID OUT LOUD.
#   `except`, `instead`, `together` carry a set operation, so they are neither descriptors nor
#   junk; they belong to pass 2, and rung 8's `except` is already a known-open gate 3 question.
#   This is the same KIND of list as `COMPARATORS` and `ENUMERATORS` — closed English, not lab
#   vocabulary — but unlike those two it has no manifest behind it. When pass 2 declares its
#   set operations, THIS LIST IS DELETED AND READ FROM THERE (rule W5).
RELATIONAL_WORDS = frozenset({
    "except", "excluding", "besides", "instead", "rather",
    "together", "apart", "separately", "own", "different", "same",
})


class Residue(NamedTuple):
    word: str
    row: str                 # the declaration it was found inside
    kind: str
    verdict: str
    why: str

    def __repr__(self):
        return f"{self.word!r} in {self.row!r}: {self.verdict} — {self.why}"


def slots_of(kind: str) -> Tuple[Dict[str, List[str]], Dict[str, str], List[str]]:
    """Every attribute of a kind, sorted by WHAT COULD FILL IT. Read, never hand-listed.

    ⇒ **THE MANIFEST ALREADY DECLARES ALL THREE AND NO TYPE SYSTEM HAD TO BE ADDED.**

        CLOSED     `attr_values` gives the set          {status: [running, stopped]}
        REFERENCE  a setter says the attribute `refs`   add_vm_to_network -> refs 'network'
        OPEN TEXT  everything else                      name · label · description
    """
    from planner.ir import config as _config
    spec = _config.KINDS.get(kind) or {}
    closed = {attr: [str(v).lower() for v in values]
              for attr, values in (spec.get("attr_values") or {}).items()}
    reference: Dict[str, str] = {}
    for group in ("setters", "unsetters"):
        for meta in (spec.get(group) or {}).values():
            if isinstance(meta, dict) and meta.get("refs") and meta.get("attr"):
                reference[meta["attr"]] = meta["refs"]
    open_text = [a for a in (spec.get("attrs") or [])
                 if a not in closed and a not in reference]
    return closed, reference, open_text


def _consumed_by_a_field(row: S.Declared, board: Board) -> set:
    """Words already accounted for by a field of the declaration — so not descriptors at all.

    ⇒ **EACH ENTRY NAMES THE FIELD THAT ATE IT, AND THAT IS WHAT KEEPS THIS FROM BEING A
      STOPLIST.** A comparator word is spent on `comparator`; an existence word on
      `existence`; a pro-form is the head of its own phrase; the row's own name is the thing
      rather than a description of it. Nothing is exempt for being common.
    """
    out = {str(v).lower() for v in (row.where or {}).values()}          # -> where
    out |= {w.strip(".,'\"") for w in str(row.identity or "").lower().split()}   # -> identity
    out |= set(pass1.PLURAL_PRONOUNS) | {p.lower() for p in S.PRONOUNS}  # -> the head
    out |= {S.NEW, S.EXISTING}                                          # -> existence
    if row.comparator:                                                  # -> comparator
        for phrase in COMPARATORS:
            out |= set(phrase.split())
    return out


def unread(row: S.Declared, request: str, board: Optional[Board] = None) -> List[str]:
    """The words inside this declaration's span that nothing consumed. Deduplicated, in order.

    ⇒ **A KINDLESS ROW IS SKIPPED ENTIRELY.** `conditions_from` needs a kind before it can read
      anything, so every modifier of a `?` row looks unread and the check would shout about
      rows gate 2 is already asking about. Item 0 owns that case.
    """
    board = board or Board()
    if row.object_type == S.UNKNOWN_KIND:
        return []
    located = scan(row.span or row.name, request, board)
    if not located or not located.modifiers:
        return []

    from planner.ir import config as _config
    spec = _config.KINDS.get(row.kind) or {}
    attrs = set(spec.get("attrs") or []) | set((spec.get("aliases") or {}).keys())
    attrs |= set((spec.get("observed") or {}).keys())
    doc_words = set()
    for meta in (spec.get("observed") or {}).values():
        doc_words |= {_stem(w.strip(".,'")) for w in str(meta.get("doc") or "").lower().split()
                      if len(w) > 5}

    spent = _consumed_by_a_field(row, board) | GRAMMAR | LINKING | NAMING_CUES
    verbs = _operation_words(board)

    out: List[str] = []
    for token in located.modifiers.split():
        word = token.strip(".,'\"")
        if not word or word in out or word in spent or word in verbs:
            continue
        if word in attrs or _stem(word) in attrs:
            continue
        if any(a.startswith(_stem(word)) for a in attrs if len(a) >= 4 and len(_stem(word)) >= 3):
            continue
        if _stem(word) in doc_words:
            continue
        out.append(word)
    return out


def lab_has(word: str, world, prefer: Optional[List[str]] = None,
            board: Optional[Board] = None) -> Optional[str]:
    """Does the lab hold ANYTHING carrying this word as its key? Returns the kind, or None.

    ⇒ **THE PLAINEST FORM OF THE OPERATOR'S TEST — *does it correlate to the world?*** The
      first version asked a much narrower question and got nothing: given an unread `orion` on
      a vm row it consulted the vm's REFERENCE attributes, so it asked the lab whether there
      was a NETWORK called orion. There was a vm called orion. A word that names anything the
      lab has is a reference the reading missed, whatever slot it was found beside.

    ⇒ **AND BY EACH KIND'S OWN KEY.** A network's key is `net_name`, a snapshot's is
      `snap_name`. Asking for `name` everywhere queries a column that is not there, and the
      exception reads as "not found" — the silent-wrong answer.
    """
    if world is None:
        return None
    from planner.gates import claims as _claims
    board = board or Board()
    order = list(prefer or []) + [k for k in board.kinds if k not in (prefer or [])]
    for kind in order:
        key = _claims.key_of(kind, board.kinds)
        if not key:
            continue
        try:
            if world.select({"kind": kind, key: word}):
                return kind
        except Exception:
            continue
    return None


def classify(word: str, kind: str, request: str, world=None) -> Tuple[str, str]:
    """What could hold this word? Manifest, then request, then — if there is one — the lab."""
    closed, reference, open_text = slots_of(kind)
    w = word.lower()

    if w in RELATIONAL_WORDS:
        return RELATIONAL, "a set operation, not a description — pass 2's"

    # ⇒ THE REQUEST'S OWN BINDING COUNTS AS CORRELATION. "3 vms labelled 'edge'" binds `edge`
    #   to a value, so an unread `edge` later in the SAME request is a missed clause and not a
    #   mystery — no manifest list has to contain it.
    if re.search(rf"['\"]{re.escape(w)}['\"]", request.lower()):
        return BOUNCE, "quoted as a value in this request"

    # ⇒ A NAMING CUE IS THE REQUEST BINDING THE WORD ITSELF. *"a network called core"* names
    #   the network; if no declaration carries it, the model dropped a whole object and the
    #   words to find it are right there — so this is a MISS, not a mystery. Rung 8 asked the
    #   operator what `core` was while the request said it in as many words.
    if re.search(rf"\b({'|'.join(NAMING_CUES)})\s+(a\s+|an\s+|the\s+)?['\"]?{re.escape(w)}\b",
                 request.lower()):
        return BOUNCE, "the request names it outright — no declaration carries it"

    for attr, allowed in closed.items():
        if w in allowed:
            return BOUNCE, f"a declared value of {kind}.{attr}"

    # ⇒ ONLY THE LAB CAN SETTLE A REFERENCE, which is why this arm takes a world and stays
    #   quiet without one rather than guessing. Same hook `conflicts()` already uses.
    found = lab_has(word, world, prefer=list(reference.values()))
    if found:
        return BOUNCE, f"the lab has a {found} called {word!r} — it is a reference, not a word"

    if open_text:
        unchecked = (f" (a lab would also check {', '.join(reference)})" if reference and
                     world is None else "")
        return ASK, (f"nothing declared can hold {word!r} — at best "
                     f"{kind}.{' or '.join(open_text[:2])}{unchecked}")
    # ⇒ UNREACHABLE IN THIS MANIFEST AND SAID SO RATHER THAN LEFT LOOKING TESTED: every kind
    #   declared today has at least one open-text attribute, so no word ever falls this far.
    #   It exists for a kind whose attributes are all closed or all references.
    return REJECT, f"a {kind} has no slot that could hold {word!r}"


def _relational_in(row: S.Declared, request: str, board: Board) -> List[str]:
    """Set-operation words, found even in a KINDLESS row.

    ⇒ `unread` skips a `?` row on purpose — with no kind there are no conditions, so every
      word looks unread. But a set operation does not need a kind to be recognised, and
      *"except orion — orion goes on lab instead"* is exactly the clause that arrives kindless.
      Skipping the row wholesale made the exclusion invisible, so this one test runs anyway.
    """
    located = scan(row.span or row.name, request, board)
    words = (located.modifiers if located else "").split()
    out = []
    for token in words:
        word = token.strip(".,'\"")
        if word in RELATIONAL_WORDS and word not in out:
            out.append(word)
    return out


def _reference_values(rows: List[S.Declared], request: str, board: Board,
                      world=None) -> List[Residue]:
    """A CONDITION VALUE FILLING A REFERENCE SLOT MUST NAME SOMETHING THAT EXISTS.

    ⇒ **THIS IS WHERE THE JUNK WENT WHEN THE FIRST VERSION CLOSED THE OTHER DOOR.**
      *"put every vm on a wibblesome network"* does not leave `wibblesome` unread — it PROMOTES
      it, because `conditions_from` sees the attribute word `network` and takes its neighbour
      as the value. The result is `network = wibblesome`: a confidently wrong filter rather
      than a missing one, and both gates pass it. Gate 1 sees a value the operator did say;
      gate 2 finds no closed value set on `network` to test it against.

    ⇒ **AND WHAT SETTLES IT IS THE SYMBOL TABLE FIRST, THE LAB SECOND** (rule D1). `mesh` in
      *"create a network called mesh and put orion on it"* is declared right there in the same
      request, so it resolves with no lab at all. `wibblesome` is declared nowhere, names no
      object the lab has, and is quoted nowhere — so nothing can hold it.
    """
    from planner.gates import claims as _claims
    out: List[Residue] = []
    for row in rows:
        _closed, reference, _open = slots_of(row.kind)
        for attr, refs in (reference or {}).items():
            value = (row.where or {}).get(attr)
            if value in (None, ""):
                continue
            word = str(value)
            declared = False
            for other in rows:
                if other.kind != refs:
                    continue
                key = _claims.key_of(refs, board.kinds)
                if (str((other.where or {}).get(key, "")).lower() == word.lower()
                        or str(other.identity or "").lower() == word.lower()
                        or word.lower() in str(other.name).lower()):
                    declared = True
                    break
            if declared:
                continue
            there = lab_has(word, world, prefer=[refs], board=board)
            if there == refs:
                continue          # the lab has it — the reference resolves, nothing to say
            verdict, why = classify(word, refs, request, world)
            if there:
                verdict = BOUNCE
                why = (f"{row.kind}.{attr} refers to a {refs}, and the lab's {word!r} "
                       f"is a {there}")
            elif verdict == ASK:
                why = (f"{row.kind}.{attr} refers to a {refs}, and nothing declares a {refs} "
                       f"called {word!r}")
            out.append(Residue(word, row.name, refs, verdict, why))
    return out


def _names_declared_here(rows: List[S.Declared], board: Board) -> set:
    """Words that IDENTIFY a declared row — its key value, or its candidate identity.

    ⇒ **THE CHECK DID NOT CONSULT THE OTHER DECLARATIONS, AND SO IT LIED.** Rung 8 says
      *"except db — db goes on a network called dmz"*. The second `db` falls inside the dmz
      network's span, and the check reported it as an unread reference — while `db` was
      declared as its own row two lines above. A word that names a declared object is a
      REFERENCE to it, not a residue.

    ⇒ **AND IT IS THE KEY VALUE ONLY, WHICH IS THE WHOLE PRECISION OF THIS.** `db` is a vm's
      `name`, so it identifies an object and a later mention points at it. `red` in rung 6 is a
      `label` — an ordinary attribute value, not an identity — so a later *"the red ones"*
      still owes a condition and must still be caught. Exempting every value alike would have
      thrown that away.
    """
    from planner.gates import claims as _claims
    out: set = set()
    for row in rows:
        if row.identity:
            out.add(str(row.identity).lower())
        key_attr = _claims.key_of(row.kind, board.kinds) if row.kind in board.kinds else None
        value = (row.where or {}).get(key_attr) if key_attr else None
        if value:
            out.add(str(value).lower())
    return out


def report(rows: List[S.Declared], request: str, board: Optional[Board] = None,
           world=None) -> List[Residue]:
    """Every word in every declaration that nothing can account for, with its verdict."""
    board = board or Board()
    identified = _names_declared_here(rows, board)
    out: List[Residue] = []
    for row in rows:
        for word in unread(row, request, board):
            if word.lower() in identified:
                continue          # it names a row declared elsewhere — a reference, not residue
            verdict, why = classify(word, row.kind, request, world)
            out.append(Residue(word, row.name, row.kind, verdict, why))
        if row.object_type == S.UNKNOWN_KIND:
            for word in _relational_in(row, request, board):
                out.append(Residue(word, row.name, row.kind, RELATIONAL,
                                   "a set operation, not a description — pass 2's"))
    out += _reference_values(rows, request, board, world)
    return out


# ⇒ `asks()` LIVED HERE AND WAS DELETED THE SAME TURN IT WAS WRITTEN. `gates12.residues` builds
#   the operator's question, so this was a second place phrasing the same thing and NOTHING
#   CALLED IT — the dominant defect class in this project, produced again inside a file arguing
#   for care. Grepping for callers is what caught it (rule W1).
