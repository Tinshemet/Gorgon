"""ANCHOR AND SCAN — the AI points at a thing; the code reads the phrase around it.

    The operator, 2026-08-08: *"we do heuristics — the AI picks an anchor, and scans around
    for enumerator, descriptors, etc. For us a bare item and a full one with descriptors and
    enumerators are the same, until the world tells us it's a reference."*

# WHY THIS AND NOT MORE QUESTIONS

Pass 1 asked the model four things and got three of them wrong. Measured over 14 requests:
names 14/14, kinds 12/14, conditions 12/14 with 16 invented, and the COUNT was never asked for
at all — so half the rungs could not have been expressed even if every answer were right.

And the reason was visible in what it produced. Asked to *"list the things"*, it returned
`a vm` · `named` · `alpha` — the PARTS OF ONE NOUN PHRASE. It was chunking at the phrase's
internal boundaries, which are exactly where its parts divide:

        [comparator]  [enumerator]  [descriptors]  NOUN  [descriptors / restrictors]
         exactly       two                         machines  left
                       a                           vm        named alpha
                       every         running       vm
                       3                           vms       labelled 'red'

Every one of those parts is a field we were asking a separate question for. So stop asking.
**The model points at an anchor — the one thing it does reliably — and everything else is read
off the request by scanning outward.**

    THE MODEL POINTS  ·  THE CODE READS  ·  THE WORLD DECIDES

The last of those is the operator's other point: a bare `golden` and a full `a vm named alpha`
come out the SAME SHAPE here — an anchor with zero or more modifiers. Nothing in this file
decides whether a thing is a reference or a new thing. Only the lab can say that, and it says
it at gate 2.

# WHAT IS CLOSED, AND WHY THAT MATTERS

`COMPARATORS` and `ENUMERATORS` are closed classes of English, not lab vocabulary — the same
kind of list as the determiners in `schema.expand`, which held on 20 held-out requests. The
NOUNS are the manifest's own, so a kind added tomorrow is scanned for without an edit here.
"""
import re
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board

# ⇒ THE COMPARATOR IS PART OF THE ENUMERATOR REGION, and it is the `(eq, 3)` the program needs.
#   Longest first, so "no more than" wins over "no".
COMPARATORS: Dict[str, str] = {
    "no more than": "max", "at most": "max", "not more than": "max", "up to": "max",
    "no fewer than": "min", "at least": "min",
    "exactly": "eq", "precisely": "eq", "just": "eq",
}

ENUMERATORS: Dict[str, object] = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "both": 2, "no": 0,
    "every": "all", "all": "all", "each": "all", "any": "all",
}

# a clause ends here, and a span may never cross one
BOUNDARIES = {",", ";", ".", "and", "then", "but", "—"}


class Scanned(NamedTuple):
    anchor: str
    span: str                       # the whole noun phrase, as the request wrote it
    start: int                      # where the span begins in the request
    end: int                        # and ends — so two spans can be compared
    count: object                   # 5 · "all" · None
    comparator: Optional[str]       # eq · min · max · None
    kind: Optional[str]             # from the manifest's nouns, or None if the anchor is bare
    modifiers: str                  # everything that is not the enumerator or the noun

    def collides(self, other: "Scanned") -> bool:
        """Do these two spans cover the same ground?

        ⇒ **COLLISION IS THE STRONGEST FOLD SIGNAL WE HAVE, and it needs no key.** Anchored on
          `lab` and on `network`, the request *"create a network called lab"* yields the SAME
          span both times — so they are the same object, provably, whether or not the model
          extracted an identifying attribute for either.

        ⇒ **AND IT IS ONLY VALID BETWEEN DECLARATIONS — never between references.** In
          *"then put web on lab"* BOTH anchors scan to the same clause, so `web` and `lab`
          collide there while being plainly different objects. A reference's span is the clause
          it appears in, not the thing it names. Compare first occurrences only.
        """
        return self.start < other.end and other.start < self.end


def _index(board: Board) -> Dict[str, str]:
    """Every declared noun and its plural, pointing at its kind. READ, never hand-listed."""
    out: Dict[str, str] = {}
    for kind in board.kinds:
        for noun in [kind] + list((board.kinds[kind] or {}).get("nouns") or []):
            word = str(noun).lower()
            out[word] = kind
            out[word + "s"] = kind
    return out


def _tokens(text: str):
    """Words AND punctuation, with positions. Punctuation must survive — a span that crosses
    a comma is the bug that made 'create 5 vms, put them all in a network' one phrase."""
    return [(m.group(0).lower(), m.start(), m.end())
            for m in re.finditer(r"[\w']+|[,;.]", text)]


def scan_all(anchor: str, request: str,
             board: Optional[Board] = None) -> List[Scanned]:
    """EVERY occurrence, in order. The first DECLARES; the rest are REFERENCES to it.

    ⇒ `scan` alone was blind to this. *"create a network called lab and a vm named web, then
      put web on lab"* mentions `web` at 43 and 57 and `lab` at 24 and 64 — and `find()` sees
      only the first, so the reference was invisible. That is the operator's ordering rule
      ([[gorgon-twopass-item-3]]) applied to spans instead of to names.
    """
    low, target = request.lower(), str(anchor).strip().lower()
    out: List[Scanned] = []
    at = low.find(target)
    while at >= 0:
        got = scan(anchor, request, board, at=at)
        if got:
            out.append(got)
        at = low.find(target, at + max(len(target), 1))
    return out


def scan(anchor: str, request: str, board: Optional[Board] = None,
         at: Optional[int] = None) -> Optional[Scanned]:
    """Find the anchor, then read outward to the edges of its clause."""
    board = board or Board()
    nouns = _index(board)
    low = request.lower()
    if at is None:
        at = low.find(str(anchor).strip().lower())
    if at < 0:
        return None

    toks = _tokens(request)
    if not toks:
        return None
    first = next((i for i, t in enumerate(toks) if t[2] > at), 0)
    last = next((i for i, t in enumerate(toks) if t[1] >= at + len(anchor)), len(toks))

    # ── LEFT: descriptors, then the enumerator, then the comparator in front of it
    left, count, comparator = first, None, None
    while left > 0 and toks[left - 1][0] not in BOUNDARIES:
        word = toks[left - 1][0]
        if word in ENUMERATORS or word.isdigit():
            count = int(word) if word.isdigit() else ENUMERATORS[word]
            left -= 1
            comparator, left = _comparator_before(toks, left)
            break
        left -= 1
    if count is None:                       # a comparator can sit alone: "no more than two"
        comparator, left = _comparator_before(toks, left)

    # ── RIGHT: modifiers and restrictors, to the end of the clause
    right = last
    while right < len(toks) and toks[right][0] not in BOUNDARIES:
        right += 1

    span_words = [t[0] for t in toks[left:right] if t[0] not in BOUNDARIES]
    # ⇒ THE KIND IS LOOKED FOR AT OR BEFORE THE ANCHOR, NEVER AFTER IT. A noun precedes its
    #   modifiers — "a VM named alpha" — so reaching rightward finds the wrong sentence's noun:
    #   anchored on `golden`, "clone golden into 3 new vms" was answering `vm`. A bare name has
    #   no kind here, and that is correct: only the lab can say what `golden` is.
    head = [t[0] for t in toks[left:last] if t[0] not in BOUNDARIES]
    kind = _kind_of(head, nouns)
    comparator_words = {w for phrase in COMPARATORS for w in phrase.split()}
    # a word that names ANY kind is never a modifier — otherwise a bare anchor whose own kind
    # is unknown picks up the next clause's noun and stops reporting itself bare.
    modifiers = [w for w in span_words
                 if w not in ENUMERATORS and not w.isdigit()
                 and w not in comparator_words and w not in nouns]
    lo = toks[left][1] if right > left else at
    hi = toks[right - 1][2] if right > left else at + len(anchor)
    return Scanned(anchor=anchor, span=request[lo:hi], start=lo, end=hi,
                   count=count, comparator=comparator, kind=kind,
                   modifiers=" ".join(modifiers))


def _comparator_before(toks, left):
    """A comparator may be one word or three, and sits in front of the enumerator."""
    for size in (3, 2, 1):
        if left - size < 0:
            continue
        phrase = " ".join(t[0] for t in toks[left - size:left])
        if phrase in COMPARATORS:
            return COMPARATORS[phrase], left - size
    return None, left


def _kind_of(words: List[str], nouns: Dict[str, str]) -> Optional[str]:
    """Longest noun wins — 'restore point' before 'point'."""
    for i in range(len(words) - 1):
        pair = f"{words[i]} {words[i + 1]}"
        if pair in nouns:
            return nouns[pair]
    return next((nouns[w] for w in words if w in nouns), None)
