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


def anchors_in(request: str, board: Optional[Board] = None) -> List[str]:
    """EVERY DECLARED NOUN THE REQUEST USES — anchors found without asking anyone.

    ⇒ The naming question returns paraphrases: *"make sure there are exactly two machines
      left"* came back as `sentence` / `things` / `group`, none of which are IN the request, so
      nothing could be scanned and the whole reading was empty. But the manifest already lists
      the words that name a thing, so the anchors can be READ.

    The model is still needed for what the manifest cannot list — a pronoun-headed set like
    *"the ones that do not answer"* — so its answers are added to these, never replaced by them.
    """
    board = board or Board()
    nouns = _index(board)
    low = request.lower()
    found: List[str] = []
    for match in re.finditer(r"[\w']+", low):
        word = match.group(0)
        if word in nouns and word not in found:
            found.append(word)
    return found


def uncovered(request: str, spans, board: Optional[Board] = None) -> List[str]:
    """Content words no span has claimed — CANDIDATE OBJECTS, and lost clauses, together.

    ⇒ **THE ANCHOR FINDER AND THE LEFTOVER CHECK ARE ONE MECHANISM.** A word the request uses
      that no declaration covers is either a thing nobody named or a clause nobody read, and
      until it is claimed we cannot tell which. `n1`, `golden`, `db`, `dmz` are found this way
      — none is a declared noun, so nothing else would ever reach them.

    Grammar, enumerators, comparators and the manifest's OPERATION words are exempt: a verb
    belongs to pass 2, and `and` belongs to nobody.
    """
    board = board or Board()
    nouns = _index(board)
    low = request.lower()
    covered = bytearray(len(low))
    for start, end in spans:
        for i in range(max(0, start), min(end, len(low))):
            covered[i] = 1
    out: List[str] = []
    for m in re.finditer(r"[\w']+", low):
        word = m.group(0)
        if covered[m.start()] or word in out:
            continue
        if word in GRAMMAR or word in ENUMERATORS or word in nouns:
            continue
        if any(word in phrase.split() for phrase in COMPARATORS):
            continue
        if word in _operation_words(board):
            continue
        out.append(word)
    return out


GRAMMAR = {"a", "an", "the", "of", "on", "in", "to", "for", "and", "then", "but", "with",
           "that", "which", "is", "are", "be", "it", "its", "them", "they", "their", "there",
           "should", "must", "can", "each", "other", "into", "from", "at", "by", "so", "do",
           "does", "not", "was", "were", "this", "those", "these", "up", "out", "all", "own",
           "same", "different", "already", "currently", "still", "also", "sure", "left"}


def _operation_words(board: Board) -> set:
    """Verbs the manifest names — they belong to pass 2, never to a declaration."""
    from planner.ir import config as _config
    out = set()
    for spec in (_config.KINDS or {}).values():
        if not isinstance(spec, dict):
            continue
        for group in ("creators", "setters", "acts", "observed"):
            for name in (spec.get(group) or {}):
                out.update(re.findall(r"[a-z]+", str(name).lower()))
        for word in ("delete", "list", "create"):
            if spec.get(word):
                out.update(re.findall(r"[a-z]+", str(spec[word]).lower()))
    out |= {"make", "put", "give", "take", "launch", "start", "stop", "ping", "clone", "check",
            "ensure", "confirm", "get", "run", "carry", "carries", "goes", "go", "answer",
            "answers", "respond", "responds", "reach", "connect", "wire", "spin", "boot"}
    return out - {"network", "snapshot", "template", "profile", "file", "vm"}


def kinds_named(request: str, board: Optional[Board] = None) -> List[str]:
    """Which kinds this request mentions at all — used to give a pronoun-headed set its kind."""
    board = board or Board()
    nouns = _index(board)
    out: List[str] = []
    for match in re.finditer(r"[\w']+", request.lower()):
        kind = nouns.get(match.group(0))
        if kind and kind not in out:
            out.append(kind)
    return out


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
    left, count, comparator, matched = first, None, None, ""
    while left > 0 and toks[left - 1][0] not in BOUNDARIES:
        word = toks[left - 1][0]
        if word in ENUMERATORS or word.isdigit():
            count = int(word) if word.isdigit() else ENUMERATORS[word]
            left -= 1
            comparator, matched, left = _comparator_before(toks, left)
            break
        left -= 1
    if count is None:                       # a comparator can sit alone: "no more than two"
        comparator, matched, left = _comparator_before(toks, left)

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
    # ⇒ ONLY STRIP A COMPARATOR WORD WHERE A COMPARATOR WAS ACTUALLY FOUND. Stripping every
    #   word that appears in any comparator phrase deleted `not` — because "not more than" is
    #   one — and *"the ones that do not answer"* became *"the ones that do answer"*. Negation
    #   is the difference between the two halves of rung 11.
    comparator_words = set(matched.split())
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
    """A comparator may be one word or three, and sits in front of the enumerator.

    Returns the MATCHED PHRASE as well as its meaning — looking the phrase back up by value
    finds whichever synonym is listed first, so "at most" was stripping "no more than".
    """
    for size in (3, 2, 1):
        if left - size < 0:
            continue
        phrase = " ".join(t[0] for t in toks[left - size:left])
        if phrase in COMPARATORS:
            return COMPARATORS[phrase], phrase, left - size
    return None, "", left


def _kind_of(words: List[str], nouns: Dict[str, str]) -> Optional[str]:
    """Longest noun wins — 'restore point' before 'point'."""
    for i in range(len(words) - 1):
        pair = f"{words[i]} {words[i + 1]}"
        if pair in nouns:
            return nouns[pair]
    return next((nouns[w] for w in words if w in nouns), None)


# ── MODIFIERS INTO CONDITIONS, where the manifest can settle it ────────────────────────
LINKING = {"called", "named", "labelled", "labeled", "tagged", "marked", "is", "are", "be",
           "the", "a", "an", "with", "on", "in", "to", "of", "that", "do", "does", "and",
           "currently", "already", "its", "their"}


def _stem(word: str) -> str:
    for suffix in ("ed", "ing", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def conditions_from(modifiers: str, kind: Optional[str],
                    board: Optional[Board] = None) -> Dict[str, object]:
    """Read a phrase like *"labelled 'red'"* into `{label: red}` — from the manifest alone.

    Three rules, in order, and every one of them consults a DECLARATION:

      1 A WORD THAT IS A DECLARED VALUE names its own attribute. `stopped` can only be
        `status`, because `attr_values` says so. Measured 2/2 on the closed sets.
      2 A WORD THAT NAMES AN ATTRIBUTE takes the next real word as its value —
        *"labelled 'red'"*, *"network called core"*. Linking words are stepped over, which is
        why `network called core` does not come back as `network = called`.
      3 AN OBSERVED ATTRIBUTE is matched through its own DOC. The manifest says `alive` is
        *"whether the machine answers its guest agent"*, so *"do not answer"* reaches it — and
        the `not` decides the value rather than being discarded.

    What it cannot settle is left for gate 2 to ask the model about, which is the operator's
    seam: everything here is a declaration lookup, and a judgement call is not.
    """
    board = board or Board()
    if not modifiers or not kind or kind not in board.kinds:
        return {}
    from planner.ir import config as _config
    spec = _config.KINDS.get(kind) or {}

    values: Dict[str, tuple] = {}
    for attr, allowed in (spec.get("attr_values") or {}).items():
        for value in allowed:
            values[str(value).lower()] = (attr, value)
    for attr, aliases in (spec.get("value_aliases") or {}).items():
        for word, value in aliases.items():
            values[str(word).lower()] = (attr, value)

    attrs = {a: a for a in (spec.get("attrs") or [])}
    attrs.update({alias: real for alias, real in (spec.get("aliases") or {}).items()})

    words = [w.strip("'\"") for w in modifiers.lower().split() if w.strip("'\"")]
    negated = "not" in words or "n't" in words
    out: Dict[str, object] = {}

    for i, word in enumerate(words):
        if word in values:                                   # 1 · a value names its attribute
            attr, value = values[word]
            out[attr] = value
            continue
        stem = _stem(word)                                   # 2 · an attribute takes a value
        for cue, real in attrs.items():
            # MATCH IN BOTH DIRECTIONS. "labelled" stems to "labell", which no cue starts
            # with; "named" stems to "nam", which is shorter than any cue. One-way prefixing
            # missed both, and those are the two commonest descriptors in the corpus.
            # ⇒ PREFIX MATCHING ONLY WHERE THE CUE IS LONG ENOUGH TO MEAN SOMETHING. The
            #   manifest aliases `on` to `network`, and a 3-char prefix let `ones` match it —
            #   *"the ones that do not answer"* came back as `network = not`. A two-letter cue
            #   must match exactly.
            if word == cue or stem == cue or (
                    len(cue) >= 4 and len(stem) >= 3
                    and (cue.startswith(stem) or stem.startswith(cue))):
                # LOOK BOTH WAYS. English puts the value either side of the attribute word —
                # *"labelled 'red'"* but *"the 'prod' label"* — and taking only the next word
                # lost every request phrased the second way.
                after = next((w for w in words[i + 1:]
                              if w not in LINKING and w not in attrs), None)
                before = next((w for w in reversed(words[:i])
                               if w not in LINKING and w not in attrs), None)
                pick = after if (after and after not in values) else (
                    before if (before and before not in values) else None)
                if pick:
                    out[real] = pick
                break

    for attr, meta in (spec.get("observed") or {}).items():   # 3 · observed, through its doc
        doc = {_stem(w.strip(".,'")) for w in str(meta.get("doc") or "").lower().split()
               if len(w) > 5}
        if doc & {_stem(w) for w in words}:
            out[attr] = not negated
    return out
