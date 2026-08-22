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

from planner.formula.legal import Board

from ..codex import COMPARATORS

from ..codex import ENUMERATORS

from ..codex import BOUNDARY_WORDS as BOUNDARIES


class Scanned(NamedTuple):
    anchor: str
    span: str                       # the whole noun phrase, as the request wrote it
    start: int                      # where the span begins in the request
    end: int                        # and ends — so two spans can be compared
    count: object                   # 5 · "all" · None
    comparator: Optional[str]       # eq · min · max · None
    kind: Optional[str]             # from the manifest's nouns, or None if the anchor is bare
    modifiers: str                  # everything that is not the enumerator or the noun
    identity: Optional[str] = None  # a CANDIDATE name — only the lab can confirm it

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


from ..codex import PARTICLES

from ..codex import OBJECT_OPENERS
from ..codex import SHAPE_NEGATION as _SHAPE_NEG


def opens_imperative(words: List[str], board: Optional[Board] = None) -> bool:
    """Does this clause open on a verb-position word taking an object NP?

    ⇒⇒ WITH OR WITHOUT ITS ARTICLE — terse noise drops articles, and the old test
      (`words[1] in dets`) billed 4 of the 7 terse act losses on the certified v2 run:
      `restart db vm` read as nothing. The article-less arm demands a MANIFEST NOUN
      heading the object (read from the board, never hand-listed), so a bare NP, a
      rule, testimony and a question all still refuse the shape.
    """
    words = [str(w).strip(".,;:—–\"") for w in words]
    if len(words) < 2:
        return False
    from .speech_act import AUXILIARIES, WH_WORDS
    w0 = words[0]
    if (w0 in GRAMMAR or w0 in OBJECT_OPENERS or w0 in _SHAPE_NEG
            or w0 in AUXILIARIES or w0 in WH_WORDS):
        return False
    if words[1] in OBJECT_OPENERS:
        return True
    nouns = _index(board or Board())
    at = 2 if words[1] in PARTICLES else 1
    return any(w in nouns for w in words[at:at + 3])


def _index(board: Board) -> Dict[str, str]:
    """Every declared noun and its plural, pointing at its kind. READ, never hand-listed."""
    out: Dict[str, str] = {}
    for kind in board.kinds:
        for noun in [kind] + list((board.kinds[kind] or {}).get("nouns") or []):
            word = str(noun).lower()
            out[word] = kind
            out[word + "s"] = kind
    return out


def _cue_hit(word: str, cue: str) -> bool:
    """Does `word` name the declared attribute `cue`?  ONE test, used in TWO places.

    MATCH IN BOTH DIRECTIONS. "labelled" stems to "labell", which no cue starts with; "named"
    stems to "nam", which is shorter than any cue. One-way prefixing missed both, and those are
    the two commonest descriptors in the corpus.

    ⇒ PREFIX MATCHING ONLY WHERE THE CUE IS LONG ENOUGH TO MEAN SOMETHING. The manifest aliases
      `on` to `network`, and a 3-char prefix let `ones` match it — *"the ones that do not
      answer"* came back as `network = not`. A two-letter cue must match exactly.
    ⇒ **AND IT LIVES HERE BECAUSE `scan` NEEDS THE SAME QUESTION.** Deciding whether `4` in
      *"a 4 core vm"* is a count or a value is the same lookup as reading the value off `core`,
      and the copy that answered only one of them is why the count won.
    """
    stem = _stem(word)
    return word == cue or stem == cue or (
        len(cue) >= 4 and len(stem) >= 3
        and (cue.startswith(stem) or stem.startswith(cue)))


def _tokens(text: str):
    """Words AND punctuation, with positions. Punctuation must survive — a span that crosses
    a comma is the bug that made 'create 5 vms, put them all in a network' one phrase.

    ⇒ **AND THE DASH MUST SURVIVE TOO. `BOUNDARIES` HAS LISTED `—` SINCE IT WAS WRITTEN AND
      THIS PATTERN COULD NEVER EMIT IT**, so the boundary was declared and dead. Rung 8's
      `db` scanned from `except` to the end of the sentence — 51 characters, both `db`
      mentions and the dmz network in one span — and the fold then merged the lot into a
      single `network` row. A rule that cannot fire is worse than a missing one: it reads as
      handled.

      The ASCII hyphen is deliberately NOT here. `[\\w']+` matches first, so adding `-` would
      split `well-known` into two spans; an em- or en-dash never appears inside a word.

    ⇒ ⚠ **AND A CLOCK TIME IS ONE TOKEN, MATCHED BEFORE ANYTHING ELSE.** `[\\w']+` cannot cross
      a colon, so *"arrive by 24:30"* tokenised to `24` and `30` — two bare numerals, the first
      of which the enumerator loop then read as a COUNT. 127 `leaveat`/`arriveby` values were
      lost this way on MultiWOZ, and *"snapshot every vm at 21:30"* loses its hour the same
      way. The alternation must come first or `[\\w']+` claims the `24` and leaves `:30`.
    """
    return [(m.group(0).lower(), m.start(), m.end())
            for m in re.finditer(r"\d{1,2}:\d{2}|[\w']+|[,;.]|[—–]", text)]


def verb_position_words(request: str, board: Optional[Board] = None) -> set:
    """Kind words whose EVERY occurrence sits in verb position — E1's grammar mark
    (clause-initial, a determiner next, a DIFFERENT kind or a pro-form in the object).

    ⇒ FOR THE ANCHOR GATE, by the ghost rule: E1 frees `snapshot` from the vm-row's
      span, so the reading that freed it must OWN it — otherwise the model's anchor
      re-declares the verb as a thing (`snapshot the web vm` came back as TWO rows the
      hour E1 landed). Every-occurrence, so *"create a SNAPSHOT of..."* keeps its noun.
    """
    low = str(request).lower()
    toks = _tokens(low)
    words = [t[0] for t in toks]
    nouns = _index(board or Board())
    dets = {"a", "an", "the", "every", "each", "all", "any", "both", "no",
            "it", "them"}                     # a pronoun OBJECT is the same grammar
                                              # mark: `snapshot IT` frees the verb
    out = set()
    for w in set(words):
        if w not in nouns:
            continue
        occs = [i for i, x in enumerate(words) if x == w]
        ok = bool(occs)
        for i in occs:
            initial = i == 0 or words[i - 1] in BOUNDARIES
            if not (initial and i + 1 < len(words) and words[i + 1] in dets):
                ok = False
                break
            clash, j = False, i + 1
            if words[i + 1] in {"it", "them"}:
                clash = True                  # a DIRECT pronoun object IS the whole
                                              # object — `snapshot IT` frees the verb
            while not clash and j < len(words) and words[j] not in BOUNDARIES:
                if words[j] in nouns and nouns[words[j]] != nouns[w]:
                    clash = True
                    break
                if j == i + 2 and words[j] in {"one", "ones", "it", "them"}:
                    clash = True
                    break
                j += 1
            if not clash:
                ok = False
                break
        if ok:
            out.add(w)
    return out


def anchors_in(request: str, board: Optional[Board] = None) -> List[str]:
    """EVERY DECLARED NOUN THE REQUEST USES — anchors found without asking anyone.

    ⇒ The naming question returns paraphrases: *"make sure there are exactly two machines
      left"* came back as `sentence` / `things` / `group`, none of which are IN the request, so
      nothing could be scanned and the whole reading was empty. But the manifest already lists
      the words that name a thing, so the anchors can be READ.

    The model is still needed for what the manifest cannot list — a pronoun-headed set like
    *"the ones that do not answer"* — so its answers are added to these, never replaced by them.

    ⇒⇒ ⚠ **A DECLARED NOUN MAY BE MORE THAN ONE WORD, AND THIS SCANNED SINGLE TOKENS.** The
      manifest declares `restore point`, `hardware profile` and `golden image`, and none of the
      three could ever be found — `[\\w']+` cannot match across a space. `_kind_of` was written
      for exactly this case and says so in its own docstring — *"longest noun wins, 'restore
      point' before 'point'"* — and **that branch was unreachable from here**, which is the
      built-and-never-called defect in its purest form.

      What it cost, on the manifest we ship:
        *"delete every restore point older than a week"*   -> ZERO anchors. Read as NOTHING.
        *"clone the golden image into 3 vms"*              -> template `identity = image`,
                                                              so the template is CALLED image
      The first is a destructive request that reads as empty; the second is a confidently
      wrong name. Neither reports a problem.

    ⇒ **LONGEST WINS, AND ONE PASS DOES IT.** The alternation is sorted longest-first and
      Python's `|` is leftmost-first, so `golden image` is claimed whole and the `image` inside
      it is never offered a second time. Request order is preserved because `finditer` walks
      left to right — the clause split downstream depends on it.
    """
    board = board or Board()
    nouns = _index(board)
    if not nouns:
        return []
    low = request.lower()
    pattern = re.compile(r"(?<![\w'])(" + "|".join(
        re.escape(n) for n in sorted(nouns, key=len, reverse=True)) + r")(?![\w'])")
    found: List[str] = []
    for match in pattern.finditer(low):
        word = match.group(1)
        if word not in found:
            found.append(word)
    return found


def clause_around(request: str, span: str) -> str:
    """The whole clause a span sits in — from the boundary before it to the boundary after.

    ⇒⇒ **BECAUSE A SPAN IS NOT A WINDOW BIG ENOUGH TO HOLD ITS OWN EVIDENCE.** `pass1`'s
      contextual kind lets a noun-less span inherit the request's kind, but only on proof of a
      pro-form — and it asked `_has_pronoun` about the SPAN. *"create a vm named alpha. give it
      4 cores."* draws that row's span as `4 cores`, because the left walk stops at the
      enumerator, so `give it` was never in the window and the row stayed `?` with an empty
      `where`. The pronoun that licenses the whole rule was one word outside the only place
      anybody looked.

    ⇒ **AND THE CLAUSE IS THE RIGHT WINDOW, NOT THE REQUEST.** Widening to the whole request
      would let any pronoun anywhere license any kindless span — which is the laundering the
      pro-form guard exists to stop. `BOUNDARIES` already marks where one clause ends; the
      evidence for a clause is what that clause says.
    """
    low, target = str(request).lower(), str(span).strip().lower()
    at = low.find(target)
    if at < 0:
        return str(request)
    toks = _tokens(request)
    first = next((i for i, t in enumerate(toks) if t[2] > at), 0)
    last = next((i for i, t in enumerate(toks) if t[1] >= at + len(target)), len(toks))
    left = first
    while left > 0 and toks[left - 1][0] not in BOUNDARIES:
        left -= 1
    right = last
    while right < len(toks) and toks[right][0] not in BOUNDARIES:
        right += 1
    if right <= left:
        return str(span)
    return request[toks[left][1]:toks[right - 1][2]]


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


from ..codex import GRAMMAR


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
    # ⇒ D5's root, closed 2026-08-18: `re.findall` shreds `add_vm_to_network` into
    #   segments and every segment became a "verb" — `to`, `as`, `of` let *"it boots TO a
    #   blue screen"* pass a does-this-clause-command-anything test, and 13 wrong-choice
    #   acts traced back through this set. Function words are a closed class; the noun
    #   segments and their plurals were already half-subtracted.
    return out - NON_VERB_SEGMENTS


from ..codex import NON_VERB_SEGMENTS


from ..codex import INDEFINITE
from ..codex import DEFINITE
from ..codex import UNIVERSAL

from ..codex import PARTIAL
from ..codex import NOVEL


def existence_from_determiner(span: str) -> Optional[str]:
    """NEW, EXISTING, or None when the span's determiner does not settle it.

    ⇒ **NONE IS A REAL ANSWER AND MOST SPANS GET IT.** A bare name (`db`, `golden`, `n1`) and a
      bare plural (`5 vms`) carry no determiner at all, and this returns None so the model's
      answer stands. So the rule is STRICTLY NO-WORSE by construction: it can only replace a
      guess with a reading, never remove a reading that was already there.

    ⇒ **AND A CONTESTED SPAN IS UNDECIDED RATHER THAN GUESSED.** `their own network` is novel
      (a network not mentioned before) while `the different ones` is contrastive selection over
      things that already exist — same two word-classes, opposite readings, and nothing in the
      determiner alone separates them. Rather than invent a precedence rule I cannot defend,
      a span carrying BOTH a definite and a contrastive word returns None and falls back.
      Rung 6 does not need it: *"a different network"* has no definite determiner at all.
    """
    from . import schema as S
    words = re.findall(r"[a-z']+", (span or "").lower())
    novel = any(w in NOVEL for w in words)
    known = any(w in DEFINITE or w in UNIVERSAL for w in words)
    if novel and known:
        return None                       # contested — the model's answer stands
    if novel:
        return S.NEW
    for word in words:                    # otherwise the FIRST determiner decides
        if word in INDEFINITE:
            return S.NEW
        if word in DEFINITE or word in UNIVERSAL:
            return S.EXISTING
    return None


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
         at: Optional[int] = None, kind_hint: Optional[str] = None) -> Optional[Scanned]:
    """Find the anchor, then read outward to the edges of its clause.

    ⇒⇒ **`kind_hint` IS FOR A SPAN WHOSE KIND IS IN A DIFFERENT CLAUSE, AND FOR NOTHING ELSE.**
      *"create a vm named alpha. give it 4 cores."* has no noun in its second clause, so this
      function returns `kind=None` — and everything downstream of the kind then goes wrong in
      the same direction: the demotion rule cannot ask whether `cores` is a declared attribute,
      so `4` is taken as an ENUMERATOR, and the row reads as FOUR MACHINES.

      `pass1` already resolves that kind from the pro-form, but it did so by patching the field
      on a row that had been READ without it. **Setting a kind is not the same as reading with
      one.** Supplying it here lets the rules that were already written do their job, instead
      of a second copy of them living in `pass1`.

    ⇒ ⚠ **IT NEVER OVERRIDES A KIND THE REQUEST STATES.** A noun in the span wins; the hint
      only fills a hole. Otherwise a caller could rename a thing the operator named.
    """
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
    #
    # ⇒⇒ **THE WALK STOPS AT AN OPERATION VERB — the verb is the ACT, never part of the
    #   THING.** Measured on the certified baseline (2026-08-18): boundary-exact sat at 27%
    #   while detection was 84%, uniform across every stratum, and the cause was single —
    #   *"stop the web vm"* span'd as `stop the web vm`, because nothing but a BOUNDARY or an
    #   ENUMERATOR ever ended the walk. An enumerator sentence (*"create A vm"*) was exact by
    #   luck; a determiner sentence (*"stop THE web vm"*) walked straight through `the` into
    #   the verb. The manifest's own operation words are the stop — READ, never listed.
    left, count, comparator, matched = first, None, None, ""
    count_at: Optional[int] = None
    verbs = _operation_words(board)
    # ⇒⇒ **A QUESTION'S SKIN IS NOT PART OF THE THING — the certified eval's last two
    #   clean-single misses (2026-08-18).** *"IS alpha RUNNING"* span'd as the whole clause:
    #   the fronting auxiliary walked in from the left and the asked predicate from the
    #   right, so the row said `is alpha running` where the thing is `alpha`. Inversion and
    #   wh-fronting are GRAMMAR (the scatter the answer re-gathers — the operator's
    #   "quirk of how we read" finding), and both marks are closed classes:
    #     · the clause OPENS on an auxiliary or a wh-word  ->  it is a question
    #     · the clause-initial AUXILIARY is excluded from the span (the wh-word STAYS —
    #       `which vms` keeps its determiner exactly as `every vm` does)
    #     · the right walk stops at an auxiliary or at a bare DECLARED VALUE — `running` is
    #       the asked property, not a descriptor of the machine
    from .speech_act import AUXILIARIES as _AUX, WH_WORDS as _WH
    clause_first = first
    while clause_first > 0 and toks[clause_first - 1][0] not in BOUNDARIES:
        clause_first -= 1
    question = bool(toks) and clause_first < len(toks) and         toks[clause_first][0] in (_AUX | _WH)
    asked_values = set()
    if question:
        for _kind, _spec in (board.kinds or {}).items():
            for _vals in ((_spec or {}).get("attr_values") or {}).values():
                asked_values |= {str(v).lower() for v in _vals}
    # the phrasal PARTICLES a stopped verb strands on the span's edge — `go OVER the event
    # log`, `spin DOWN the render vms` — a closed class, plus `sure`: the ensure-idiom's
    # second half (`make SURE the lab network exists`), exactly one word, documented here.
    _PARTICLES = PARTICLES
    # DETERMINERS for the imperative rule below — closed, and `that` is deliberately absent
    _DETS = {"a", "an", "the", "every", "each", "all", "any", "both", "no"}
    # ⇒ E5, THE PARTITIVE: a QUANTIFIER + `of` + NP is ONE thing — `most of the vms`
    #   lost its quantifier to the of-boundary (certified exact, qual-0003). Closed
    #   quantifiers only; `a snapshot OF every vm` still cuts — `snapshot` is no
    #   quantifier and the two-things reading stands.
    _QUANT = {"most", "some", "all", "none", "half", "few", "many", "each",
              "both", "any", "one"}
    _TRANSFER = {"put", "add", "move", "place", "clone", "give", "attach"}
    while left > 0 and (toks[left - 1][0] not in BOUNDARIES
                        or (toks[left - 1][0] == "of" and left >= 2
                            and toks[left - 2][0] in _QUANT)):
        word = toks[left - 1][0]
        if question and left - 1 == clause_first and word in _AUX:
            break                             # the fronted auxiliary is the question's skin
        # ⇒ E4 — universal left edges (certified exact misses, 08-20): an object
        #   PRONOUN is its own NP (`them ON THE DMZ NETWORK` · `me WHICH VMS`); a
        #   participle after an auxiliary is the PREDICATE (`you have checked | THE
        #   OTHERS`); a testimony frame's `with` hands over the patient (`something is
        #   wrong with | THE DMZ NETWORK` — a restrictive `with` sits after a noun and
        #   is untouched); a TRANSFER verb's preposition heads the verb's own argument
        #   (`put ... on | THE LAB NETWORK`).
        if word in {"me", "us"}:
            break                             # a RECIPIENT pronoun is its own NP
                                              # (`me | which vms`); `it`/`them` stay —
                                              # the predication over them feeds the fold
                                              # (`make IT RUNNING` reaches alpha's row),
                                              # and the transfer-preposition stop below
                                              # already owns `them ON the dmz network`
        if word.endswith("ed") and left >= 2 and toks[left - 2][0] in _AUX:
            break
        if (word == "with" and left >= 2 and toks[left - 2][0] not in nouns
                and toks[left - 2][0] not in _DETS):
            break
        if (word in {"on", "in", "into", "to", "at"}
                and toks[clause_first][0] in _TRANSFER):
            break
        if word in verbs and word not in nouns:
            break                             # `snapshot` the noun still walks; the verb stops
        if word in {"if", "unless", "because", "though", "although", "whenever", "when",
                    "after", "once", "before"}:
            break                             # an anchor INSIDE a tail stays inside it —
                                              # `if ALPHA is stopped` fused the whole clause
                                              # and is WHY conditionals-exact sat at 0/7
        # ⇒ **AN IMPERATIVE OPENS ON ITS VERB, AND THE MANIFEST DOES NOT KNOW EVERY VERB.**
        #   `restart` / `clone` / `list` have no manifest operation, so the verb-stop above
        #   never fired and the row fused (`restart the web vm` — the certified eval's
        #   coordination cell). The GRAMMAR mark: the clause-initial word, when what follows
        #   it is a DETERMINER, is the verb of an imperative — `restart THE…`, `clone THE…`.
        #   `alpha won't…` keeps alpha (aux follows, not a determiner); `the web vm, …`
        #   keeps `the` (it IS a determiner, not followed-by one).
        # ⇒ AND A KIND WORD IN VERB POSITION IS THE VERB when what follows cannot join
        #   it in one noun phrase — `snapshot the db VM` carries two different kinds,
        #   and one NP cannot; `snapshot the ONES` opens a referential pro-form. Five
        #   of the certified exact misses, one grammar mark. `vms the operator built`
        #   has no second kind after its determiner and stays a noun.
        _kindclash = False
        if word in nouns and left - 1 == clause_first and left < len(toks) \
                and toks[left][0] in _DETS:
            _j = left
            while _j < len(toks) and toks[_j][0] not in BOUNDARIES:
                _w2 = toks[_j][0]
                if _w2 in nouns and nouns.get(_w2) != nouns.get(word):
                    _kindclash = True
                    break
                if _j == left + 1 and _w2 in {"one", "ones", "it", "them"}:
                    _kindclash = True
                    break
                _j += 1
        if (left - 1 == clause_first and (word not in nouns or _kindclash)
                and word not in ENUMERATORS and word not in _WH
                and left < len(toks)
                and toks[left][0] in _DETS):
            break
        # a word followed by an OBJECT PRONOUN is a verb even when the manifest also knows
        # it as a noun — `snapshot IT` cannot be a noun phrase, by grammar.
        # ⇒ UNLESS the word is an ATTRIBUTE CUE: `LABEL it prod` needs `label` in the
        #   modifiers or conditions_from cannot read the value — the certified set lost
        #   {label: prod} to this exact release (the fixture that priced it: ana-0001's
        #   sibling). The cue's reading outranks the release.
        if (left - 1 == clause_first and left < len(toks)
                and toks[left][0] in {"it", "them", "me", "us"}
                and word not in ENUMERATORS and word not in _WH
                and not any(_cue_hit(word, c)
                            for spec in (board.kinds or {}).values()
                            for c in list((spec or {}).get("attrs") or [])
                            + list(((spec or {}).get("aliases") or {}).keys()))):
            break
        if word in ENUMERATORS or word.isdigit():
            count = int(word) if word.isdigit() else ENUMERATORS[word]
            count_at = left - 1
            left -= 1
            comparator, matched, left = _comparator_before(toks, left)
            break
        left -= 1
    if count is None:                       # a comparator can sit alone: "no more than two"
        comparator, matched, left = _comparator_before(toks, left)
    # the stranded particle: the walk broke at `go`/`spin`/`make`, leaving `over`/`down`/
    # `sure` on the edge — the particle belongs to the VERB, never to the thing
    while (left < first and toks[left][0] in _PARTICLES
           and left > 0 and toks[left - 1][0] in verbs):
        left += 1

    # ── RIGHT: modifiers and restrictors, to the end of the clause
    # ⇒ AND IN A TESTIMONY CLAUSE THE WALK STOPS AT THE MALFUNCTION AUX — *"vm2 is not
    #   working"* fused into ONE row on the certified baseline; the patient is the thing,
    #   the symptom is `testimony`'s to read (D1's front door, 08-18).
    pred_first = None
    if not question and toks:
        from . import testimony as _T
        clause_end = last
        while clause_end < len(toks) and toks[clause_end][0] not in BOUNDARIES:
            clause_end += 1
        _hit = _T._of_clause(
            request[toks[clause_first][1]:toks[clause_end - 1][2]])
        if _hit:
            pred_first = _hit.predicate.split()[0]
        if pred_first is None:
            # ⇒ and the EMBEDDED CONDITION is not part of the thing either — *"spin down the
            #   render vms AFTER THE JOB FINISHES"* kept the trigger inside the row while
            #   `condition_tail` was reading it. One reading, one owner.
            from . import iso as _iso
            try:
                _tail = _iso.condition_tail(
                    request[toks[clause_first][1]:toks[clause_end - 1][2]], board)
            except Exception:
                _tail = None
            if _tail:
                pred_first = _tail.split()[0]
                # an anchor INSIDE the tail gets the condition-clause treatment below —
                # `only if THE LAB NETWORK is up`: the copula opens the tested state
                _tw0 = _tail.split()[0]
                _tail_tok = next((_j for _j in range(clause_first, clause_end)
                                  if toks[_j][0] == _tw0), None)
                if _tail_tok is not None and first > _tail_tok:
                    _cond_anchor = True
        if pred_first is None:
            # the ADJUNCT heads stop the span the same way — *"stop the test vms EVEN
            #   THOUGH alpha is busy"* kept the concession inside the row. Span-only:
            #   these are reasons, never triggers, and nothing here flags them as one.
            for _i in range(clause_first + 1, clause_end):
                if toks[_i][0] in {"because", "though", "although", "unless"}:
                    pred_first = (toks[_i - 1][0]
                                  if _i > clause_first and toks[_i - 1][0] == "even"
                                  else toks[_i][0])
                    break
        if pred_first is None:
            # ⇒ the DEONTIC split, same mechanic: *"every vm MUST CARRY a label"* fused into
            #   one row. A deontic modal with a subject before it and no relativizer opens
            #   the RULE'S predicate — the governed thing is the row, the obligation is the
            #   rule reading's. `speech_act.DEONTIC` is the declared class.
            from .speech_act import DEONTIC as _DEONTIC
            for _i in range(clause_first + 1, clause_end):
                if toks[_i][0] in _DEONTIC and not any(
                        toks[_j][0] in {"that", "which", "who"}
                        for _j in range(clause_first, _i)):
                    pred_first = toks[_i][0]
                    break
    _cond_anchor = locals().get("_cond_anchor", False)
    _cond_clause = (toks and toks[clause_first][0] in {"if", "unless", "when", "whenever"}
                    ) or _cond_anchor
    right = last
    _rel_seen = False
    _VALUE_VERBS = {"label", "tag", "call", "name", "give"}
    from .temporal import CLOCK as _CLOCK
    while right < len(toks) and toks[right][0] not in BOUNDARIES:
        _rw = toks[right][0]
        if _rw in {"that", "which", "who"}:
            _rel_seen = True                  # a relative clause is INSIDE the span —
                                              # `the ones THAT are still running` holds
        if question and (_rw in _AUX or _rw in asked_values):
            break                             # `are stopped` / `running` — the ASKED property
        # ⇒ E2/E3 — universal right edges (certified exact misses, 08-20), all skipped
        #   inside a relative clause:
        if not _rel_seen:
            if _rw in {"is", "are", "was", "were"}:
                break                         # a following predicate is not the thing
            if (_rw.endswith(("s", "ed")) and _rw not in nouns and _rw not in _DETS
                    and _rw not in asked_values
                    and (right + 1 >= len(toks) or toks[right + 1][0] in BOUNDARIES)):
                break                         # clause-final event verb: `exists` ·
                                              # `finishes` · `restarted`
            if (_rw in {"it", "them", "me", "us"}
                    and right + 1 < len(toks)
                    and toks[right + 1][0].endswith(("ed", "s"))
                    and toks[right + 1][0] not in nouns):
                break                         # a pronoun WITH A FINITE VERB after it
                                              # opens a new clause (`which vms | it
                                              # skipped`); `label it prod` holds — no
                                              # verb follows, the predication is ours
            if _rw in _DETS and right > 0 and toks[right - 1][0] in nouns:
                break                         # a determiner DIRECTLY after a noun opens
                                              # a NEW thing (`the lab network | every
                                              # vm`); after a preposition it is the
                                              # noun's own PP (`the notes from THE
                                              # meeting` holds)
            if (_rw == "to" and right + 1 < len(toks)
                    and toks[right + 1][0] not in _DETS
                    and toks[right + 1][0] not in nouns):
                break                         # purpose infinitive: `to free up memory`
            if (_rw in {"on", "in", "into", "to", "at"}
                    and toks[clause_first][0] in _TRANSFER):
                break                         # the transfer verb's own argument PP
            if (toks[clause_first][0] in _VALUE_VERBS
                    and (_rw.startswith("'") or _rw.isdigit()
                         or (_rw not in nouns and _rw not in _DETS
                             and _rw not in {"on", "in", "with", "and", "of"}
                             and right + 1 >= len(toks)))):
                break                         # the VALUE belongs to the verb: `'ready'`
                                              # · `test` · `4 cores`
            if _rw == "at" and right + 1 < len(toks) and (
                    _CLOCK.match(toks[right + 1][0])
                    or toks[right + 1][0] in {"noon", "midnight"}):
                break                         # the clock adjunct is the trigger's
            if " ".join(t[0] for t in toks[right:right + 4]) in {"one at a time",
                                                                 "all at once"}:
                break                         # manner is HOW, never part of the thing
        if _cond_clause and toks[right][0] in {"is", "are", "was", "were"}:
            break                             # a condition TESTS a state — `alpha | is
                                              # stopped`, `the web vm | is down`: the copula
                                              # opens the tested predicate, never the thing
        if (_cond_clause and right + 1 < len(toks)
                and (right + 1 >= len(toks) or toks[right + 1][0] in BOUNDARIES)
                and not any(toks[_k][0] in {"is", "are", "was", "were"}
                            for _k in range(first, right + 1))):
            # a copula-less condition ends on its EVENT VERB — `when the backup FINISHES`:
            # the clause-final verb is the trigger's, by the events_in shape
            break
        if pred_first and toks[right][0] == pred_first and right >= last:
            break                             # the symptom belongs to the testimony reading
        right += 1

    # POSITIONS KEPT. Which digit was spent as the enumerator is a fact about a POSITION, and
    # a bare list of words cannot express it — see the modifiers filter below.
    span_at = [i for i in range(left, right) if toks[i][0] not in BOUNDARIES]
    span_words = [toks[i][0] for i in span_at]
    # ⇒ THE KIND IS LOOKED FOR AT OR BEFORE THE ANCHOR, NEVER AFTER IT. A noun precedes its
    #   modifiers — "a VM named alpha" — so reaching rightward finds the wrong sentence's noun:
    #   anchored on `golden`, "clone golden into 3 new vms" was answering `vm`. A bare name has
    #   no kind here, and that is correct: only the lab can say what `golden` is.
    head = [t[0] for t in toks[left:last] if t[0] not in BOUNDARIES]
    kind = _kind_of(head, nouns) or kind_hint      # a stated noun always wins; the hint fills a hole

    # ⇒⇒ **A NUMERAL IN FRONT OF A DECLARED ATTRIBUTE IS THAT ATTRIBUTE'S VALUE, NOT A COUNT.**
    #   *"a 4 star hotel"* is ONE hotel rated four, and *"a 4 core vm"* is ONE machine with
    #   four cores — but the enumerator loop walks left and takes the first digit it meets, so
    #   both came back `count=4` with the digit deleted from the modifiers. The attribute was
    #   then read off the wrong neighbour: `stars = please`.
    #
    #   ⇒ **THE MANIFEST DECIDES, NOT A WORD LIST.** `star` is a declared alias of `stars` and
    #     `core` of `cpu_cores`, so the demotion is a lookup. `4 vms` keeps its count because
    #     `vms` is a NOUN, not an attribute — the same test that separates the two readings.
    if count_at is not None and kind:
        _spec = _config_kinds().get(kind) or {}
        _cues = set(_spec.get("attrs") or ()) | set((_spec.get("aliases") or {}).keys())
        _next = toks[count_at + 1][0] if count_at + 1 < len(toks) else ""
        if _next and _next not in nouns and any(_cue_hit(_next, c) for c in _cues):
            count, count_at = None, None

    # ⇒ A NUMERAL BEFORE A NOUN COUNTS; AFTER ONE IT NAMES. "3 vms" is three machines and
    #   "network 1" is one network called `network 1`. Without this the `1` was dropped, so
    #   `network 1` and `network 2` produced the SAME span and the fold merged two distinct
    #   networks into one — a confidently wrong program, not a visible error.
    identity = None
    # ⇒ **A DECLARED ANCHOR'S OWN WORDS ARE THE HEAD, NEVER MODIFIERS OF IT.** A one-word
    #   declared anchor was already covered by the `not in nouns` test below, which cannot see
    #   `hardware` or `restore` — only the whole PHRASE is declared — so *"a hardware profile
    #   called fast"* offered `hardware` as a descriptor of itself.
    # ⇒ ⚠ **AND THE TEST IS *DECLARED*, NOT *MULTI-WORD*.** An anchor the manifest does not
    #   know is a NAME the operator typed, and stripping it deleted the very word the naming
    #   cue points at: `scan("alpha", "create a vm named alpha")` came back `named`, so
    #   `name = alpha` could never be read again. `web server one` fails the same way.
    anchored = str(anchor).strip().lower() in nouns
    spent_at: set = set(range(first, last)) if anchored else set()
    if count_at is not None:
        spent_at.add(count_at)
    if kind:
        noun_at = next((i for i in range(left, right)
                        if toks[i][0] in nouns and nouns[toks[i][0]] == kind), None)
        if noun_at is not None:
            tail = noun_at + 1
            while (tail < right and tail < len(toks)
                   and (toks[tail][0].isdigit() or
                        (len(toks[tail][0]) <= 3 and any(c.isdigit() for c in toks[tail][0])))):
                tail += 1
            if tail > noun_at + 1:
                identity = request[toks[noun_at][1]:toks[tail - 1][2]]
                spent_at.update(range(noun_at + 1, tail))   # `network 1` — the 1 is the name
            elif count is None and comparator is None and not (anchored and last - first > 1):
                # ⇒ **BUT NEVER A DECLARED PHRASE.** One is fully specified by the
                #   manifest and cannot also be somebody's name: *"clone the golden image"*
                #   took `image` as the template's identity, so the reading said the template
                #   is CALLED image and the operator's actual word `golden` was a modifier.
                # ⇒ A BARE NOUN-WORD MAY BE A NAME. `box` is a declared noun for `vm` AND a
                #   plausible machine name, and nothing in the request settles which — only the
                #   lab does. Carry it as a CANDIDATE so gate 2 can ask; deciding here would be
                #   guessing, and throwing it away is what stopped gate 2 ever being asked.
                identity = toks[noun_at][0]
    # ⇒ ONLY STRIP A COMPARATOR WORD WHERE A COMPARATOR WAS ACTUALLY FOUND. Stripping every
    #   word that appears in any comparator phrase deleted `not` — because "not more than" is
    #   one — and *"the ones that do not answer"* became *"the ones that do answer"*. Negation
    #   is the difference between the two halves of rung 11.
    comparator_words = set(matched.split())
    # a word that names ANY kind is never a modifier — otherwise a bare anchor whose own kind
    # is unknown picks up the next clause's noun and stops reporting itself bare.
    # ⇒⇒ **ONLY THE DIGIT THAT WAS ACTUALLY SPENT IS DROPPED.** This read `not w.isdigit()` and
    #   so deleted EVERY numeral in the span, spent or not — *"leaving at 24:30"* came out of
    #   the scanner as `leaving from the at`, count `None`, the hour simply gone. A count is
    #   taken at most ONCE, from ONE position; every other numeral is a value somebody typed
    #   and is the reader's whole job. `spent_at` also holds the digits folded into an
    #   `identity`, so `network 1` still does not offer a stray `1` as a condition.
    modifiers = [toks[i][0] for i in span_at
                 if i not in spent_at and toks[i][0] not in ENUMERATORS
                 and toks[i][0] not in comparator_words and toks[i][0] not in nouns]
    lo = toks[left][1] if right > left else at
    hi = toks[right - 1][2] if right > left else at + len(anchor)
    return Scanned(anchor=anchor, span=request[lo:hi], start=lo, end=hi,
                   count=count, comparator=comparator, kind=kind,
                   modifiers=" ".join(modifiers), identity=identity)


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


from ..codex import LINKING


def _stem(word: str) -> str:
    for suffix in ("ed", "ing", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


from ..codex import NAMING_CUES


def _config_kinds():
    from planner.ir import config as _config
    return _config.KINDS or {}


# ⇒ ⚠ **AN APOSTROPHE INSIDE A WORD IS NOT A QUOTE, AND THE FIRST CUT OF THIS MISSED IT.**
#   `won't boot, the error says 'cannot allocate memory'` matched from the apostrophe in
#   `won't` to the one opening the real quotation, and reported *"t boot, the error says"* as
#   evidence. **Measured end to end, not by the unit test** — whose examples all happened to
#   avoid contractions. So a single quote counts only when a letter does not stand on the
#   inside of it: `won't` and `alpha's` are words, `'cannot allocate memory'` is a quotation.
_QUOTED = re.compile(r"(?<![A-Za-z])'([^']{2,})'(?![A-Za-z])" + r'|"([^"]{2,})"')


def quoted_clauses(request: str) -> tuple:
    """Quoted spans of MORE THAN ONE WORD — data the operator is handing us, not values.

    ⇒⇒ **QUOTES ALREADY MEAN *A VALUE* HERE, AND THAT IS RIGHT FOR ONE WORD.**
      `residue.classify` bounces on a quoted word — *"3 vms labelled 'red'"* binds `red` — and
      every quoted span in the fourteen rungs is a single word.

    ⇒ **A QUOTED CLAUSE IS A DIFFERENT ACT.** *"the error says 'cannot allocate memory'"* is
      EVIDENCE: it correlates with no kind, no member and no archive entry — the exact profile
      of something unrelated — and it is what a diagnosis would run on. Read as a value it
      becomes a machine name; read as nothing it is the most important part of the sentence,
      discarded.

    ⇒ **THE DISCRIMINATOR IS LENGTH AND IT IS STRUCTURAL** — no vocabulary, and it matches the
      corpus exactly. One word is a value; two or more is a quotation.
    ⇒ ⚠ **BUT LENGTH DECIDES ONLY WHERE NO SLOT CLAIMS IT.** `conditions_from` overrides this
      when a CUE governs the quote — *"a vm named 'web server one'"* is a name, not evidence,
      however many words it runs to. That is the operator's own rule ([[slot-decides-junk]]):
      the slot decides, never the length and never the meaning.
    """
    return tuple(q for q in _quoted_runs(request) if len(q.split()) > 1)


def _quoted_runs(request: str) -> tuple:
    """EVERY quoted run, whatever its length — the operator's own boundary marks, read raw."""
    out = []
    for m in _QUOTED.finditer(str(request)):
        span = (m.group(1) or m.group(2) or "").strip()
        if span:
            out.append(span)
    return tuple(out)


def attribute_words(board: Optional[Board] = None) -> Dict[str, str]:
    """Every word the manifest uses to name a PROPERTY, pointing at the real attribute.

    ⇒⇒ **THE MANIFEST ALREADY KNEW AND NOTHING ASKED IT.** `vm.aliases` declares
      `ram -> memory_mb`, `cores -> cpu_cores`, `tag -> label`, `on -> network` — and
      `_index` indexes declared NOUNS only, so no reader ever said *this word names a property,
      not a thing*. `stop every vm with over 6gb of ram` therefore declared A MACHINE CALLED
      `ram` and asked whether to create it.

    ⇒ **READ, NEVER LISTED** (rule W5), so a manifest that gains an alias gains it here.
    ⇒ ⚠ **AND A KIND IS NEVER AN ATTRIBUTE, however property-ish it reads.** `network` is a
      declared kind AND a declared attribute of `vm`; the kind wins, because a row typed as a
      network is a thing the lab keeps and dropping it would delete rung 3.
    """
    from planner.ir import config as _config
    board = board or Board()
    nouns = set(_index(board))
    out: Dict[str, str] = {}
    for kind in board.kinds:
        spec = _config.KINDS.get(kind) or {}
        for a in (spec.get("attrs") or ()):
            out[str(a).lower()] = str(a)
        for alias, real in (spec.get("aliases") or {}).items():
            out[str(alias).lower()] = str(real)
    return {w: a for w, a in out.items() if w not in nouns}


from ..codex import MAGNITUDE

# ⇒ A QUANTITY WITH A UNIT GLUED TO IT — `6gb`, `500mb`, `2x`. One token to a person and two to
#   a naive tokenizer, which is how `9pm` came to be read as the number 9 at the door.
_QUANTITY = re.compile(r"\b(\d+)\s*([a-z]+)?\b")


def magnitudes_in(request: str, board: Optional[Board] = None) -> tuple:
    """Numeric comparisons the request makes — (comparator, amount, unit, attribute).

    ⇒⇒ **`where` HOLDS ONE VALUE PER ATTRIBUTE AND CANNOT HOLD A COMPARISON**, so this READS
      the comparison and does not try to store it. That is the whole point: *"stop every vm
      with over 6gb of ram"* currently loses `over` and `6gb` into the residue check and
      declares A MACHINE CALLED `ram`, because `ram` is a declared ALIAS and pass 1 read it as
      a member name. Naming the comparison is what lets somebody say so.

    ⇒ **THE ATTRIBUTE IS THE MANIFEST'S**, found through `attrs` and `aliases` — `ram` and
      `memory` both resolve to `memory_mb`, `cores` to `cpu_cores`. Nothing is guessed: a
      comparison whose attribute is not declared is not returned at all.
    """
    from planner.ir import config as _config
    board = board or Board()
    low = str(request).lower()
    attrs: Dict[str, str] = {}
    for kind in board.kinds:
        spec = _config.KINDS.get(kind) or {}
        for a in (spec.get("attrs") or ()):
            attrs[str(a).lower()] = str(a)
        for alias, real in (spec.get("aliases") or {}).items():
            attrs[str(alias).lower()] = str(real)

    out = []
    for phrase, how in sorted(MAGNITUDE.items(), key=lambda kv: -len(kv[0])):
        at = low.find(f" {phrase} ")
        if at < 0 and not low.startswith(f"{phrase} "):
            continue
        tail = low[max(at, 0) + len(phrase) + 1:]
        m = _QUANTITY.search(tail)
        if not m:
            continue
        # ⇒ THE ATTRIBUTE IS THE FIRST DECLARED ONE AFTER THE AMOUNT — *"over 6gb of RAM"* —
        #   and the UNIT itself counts when it names one, as `cores` does.
        after = [w.strip(".,'\"") for w in tail[m.end():].split()]
        unit = m.group(2) or ""
        attr = next((attrs[w] for w in ([unit] + after) if w in attrs), None)
        if attr:
            out.append((how, int(m.group(1)), unit, attr))
    return tuple(out)


from ..codex import NEGATOR_TOKENS as NEGATORS


def _negates(words: List[str], at: int, values: Dict[str, tuple]) -> bool:
    """Is the value at `at` under a negation OF ITS OWN?

    ⇒ **SCOPED BY ADJACENCY, WHICH IS THE ONLY SCOPE AVAILABLE WITHOUT A PARSE.** A negator
      binds the nearest value after it, so another declared value standing between them ends
      its reach — *"not running and labelled prod"* negates `running` and leaves `prod` alone.
      Crude, and strictly better than the clause-wide flag it replaces.
    """
    for j in range(at - 1, -1, -1):
        if words[j] in values:
            return False                     # a nearer value already took that negator
        if words[j] in NEGATORS:
            return True
    return False


def conditions_from(modifiers: str, kind: Optional[str],
                    board: Optional[Board] = None, span: str = "") -> Dict[str, object]:
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

    # ⇒⇒ **A QUOTED RUN IS ONE VALUE, AND THE WORDS INSIDE IT ARE NOT CUES.** The operator's
    #   quotes ARE the boundary, and reading past them is not a judgement call — yet
    #   *"a vm named 'web server one'"* came back `name = web`, so the machine would have been
    #   created under a name nobody typed. Worse, *"a network called 'core net'"* returned
    #   `{name: core, network: core}`: `net` inside the quotes prefix-matched the `network`
    #   alias and MINTED A SECOND CONDITION out of the operator's own literal.
    #
    #   ⇒ `quoted_clauses` has read these since it was written and `span` has been a parameter
    #     here since gate 1 — the two were never joined. `_tokens` drops the quote marks, so by
    #     the time `modifiers` exists the boundary is gone; the SPAN is the only place it
    #     survives.
    #   ⇒ **AND THIS DOES NOT CONTRADICT THE LENGTH RULE, IT BOUNDS IT.** A long quote with no
    #     cue over it is still evidence. A quote a CUE governs is that cue's value, because the
    #     slot decides — never the length, never the meaning.
    runs = [q.lower() for q in _quoted_runs(span or "") if q.split()]
    literal = {w for q in runs for w in q.split()[1:]}      # every word but each run's first

    def _whole(pick: Optional[str]) -> Optional[str]:
        """The whole quoted run a picked value opens, or the pick unchanged."""
        return next((q for q in runs if q.split()[0] == pick), pick)

    # ⇒⇒ **A PRO-FORM REFERS; IT NEVER NAMES A VALUE.** *"create a vm named alpha and label
    #   it prod"* came back `{label: it}` — the reading took the PRONOUN as the label and
    #   dropped `prod`, so the machine would carry a tag spelled `it`. `ANAPHORA` and
    #   `PRONOUNS` are declared closed classes and this function had never consulted either;
    #   it is the same rule as *a noun is never a value*, one word class over.
    #   Imported in the function because `speech_act` imports this module at top level.
    # ⇒ **AND A DISTINCTNESS MARKER IS NOT A VALUE EITHER — IT CONTRASTS.** Rung 6's *"put
    #   the red ones together on THEIR OWN network"* produced `network = own`, so a machine
    #   group was constrained to a network named `own`. `DISTINCT` is a closed class that
    #   `pass1` has owned since rung 6 was fixed the first time, and it says precisely that
    #   these words point AWAY from a thing rather than naming one.
    from .pass1 import DISTINCT as _DISTINCT
    from .speech_act import ANAPHORA as _ANAPHORA, PRONOUNS as _PRONOUNS
    _refers = set(_ANAPHORA) | set(_PRONOUNS) | {w for w in _DISTINCT if " " not in w}

    from planner.gates import claims as _claims
    key_attr = _claims.key_of(kind, board.kinds)
    nouns_here = {}
    for kind_name, spec_ in (_config_kinds().items() if True else []):
        for noun in [kind_name] + list((spec_ or {}).get("nouns") or []):
            nouns_here[str(noun).lower()] = kind_name
            nouns_here[str(noun).lower() + "s"] = kind_name

    named_by_cue: set = set()
    for i, word in enumerate(words):                      # 0 · a naming cue names the KEY
        if word not in NAMING_CUES or not key_attr:
            continue
        # ⇒ ONLY IF THE CUE IS NAMING *THIS* THING. "every vm on a network CALLED core" names
        #   the NETWORK, not the machine — and applying the span's key gave `name = core` on a
        #   vm, which is a confidently wrong condition rather than a missing one. The nearest
        #   noun before the cue says whose name it is.
        # THE SPAN, NOT THE MODIFIERS. Noun-words are stripped out of the modifiers, so the
        # very evidence this guard needs — "on a NETWORK called core" — is not in them.
        look = [w.strip("'\".,") for w in (span or modifiers).lower().split()]
        cue_at = next((j for j, w in enumerate(look) if w in NAMING_CUES), len(look))
        nearest = next((nouns_here[w] for w in reversed(look[:cue_at]) if w in nouns_here),
                       None)
        if nearest is not None and nearest != kind:
            continue
        nxt = next((w for w in words[i + 1:]
                    if w not in LINKING and w not in NAMING_CUES and w not in literal
                    and w not in _refers), None)
        if nxt:
            out[key_attr] = _whole(nxt)
            named_by_cue.add(key_attr)
            break

    # ⇒⇒ **RULE 2 MUST NOT CLOBBER RULE 0's KEY — re-armed 2026-08-18.** `named` stems to
    #   `nam`, a vm's key is `name`, so `_cue_hit` fires on the very cue rule 0 just spent,
    #   and the descriptor arm overwrote the naming arm's answer with a single word. The
    #   guard was first written during the rejected unquoted-name extension and was LOST in
    #   that revert — `git checkout` took the guard down with the change it guarded. Latent
    #   ever since (both arms currently emit the same word) and priced at twenty minutes of
    #   "the fix isn't firing" the first time it bit. The arm that OWNS a slot keeps it.
    for i, word in enumerate(words):
        if word in values:                                   # 1 · a value names its attribute
            attr, value = values[word]
            # ⇒⇒ **A NEGATION SELECTS THE COMPLEMENT, AND THE MANIFEST MAKES THAT EXACT.**
            #   Until 2026-08-16 this rule ignored `not` entirely, so *"every vm that is NOT
            #   running"* came back `{status: running}` — **the exact set the operator
            #   excluded**, from a sentence that reads as perfectly understood. `negated` was
            #   already computed here and spent only on the observed arm below.
            #
            #   ⇒ `attr_values` DECLARES the closed set, so with exactly two members the
            #     complement of one IS the other. Nothing is inferred and no new field is
            #     needed — `where` still holds one value.
            #   ⇒ ⚠ **WITH MORE THAN TWO IT DECLINES**, because the complement is then a SET
            #     and this dict cannot hold one. Saying nothing leaves gate 2 to ask; naming
            #     one of three would be confidently wrong.
            #   ⇒ **AND THE NEGATOR MUST BE THIS VALUE'S OWN.** `negated` is clause-wide, so
            #     *"not running and labelled prod"* would negate the label too. The negator
            #     counts only when no OTHER declared value stands between it and this word.
            if _negates(words, i, values):
                allowed = [str(v).lower() for v in (spec.get("attr_values") or {}).get(attr, ())]
                if len(allowed) != 2:
                    continue                  # the complement is a set — decline, do not guess
                value = next(v for v in allowed if v != str(value).lower())
            out[attr] = value
            continue
        if word in literal:                   # inside the operator's quotes — a literal, not a cue
            continue
        for cue, real in attrs.items():                      # 2 · an attribute takes a value
            if real in named_by_cue:      # the naming arm owns this slot — never trimmed back
                continue
            if _cue_hit(word, cue):                          #     (the test is `_cue_hit`)
                # LOOK BOTH WAYS. English puts the value either side of the attribute word —
                # *"labelled 'red'"* but *"the 'prod' label"* — and taking only the next word
                # lost every request phrased the second way.
                # ⇒ **AND A NOUN IS NEVER A VALUE — IT IS THE HEAD.** *"a 4 core vm"* reaches
                #   here with `after = vm`, and `vm` was taken as the value of `cpu_cores`
                #   while the real value `4` sat one word to the LEFT and was passed over.
                #   The noun of the phrase is the thing being described; it cannot also be
                #   what one of its own attributes equals.
                after = next((w for w in words[i + 1:]
                              if w not in LINKING and w not in attrs
                              and w not in nouns_here and w not in literal
                              and w not in _refers), None)
                before = next((w for w in reversed(words[:i])
                               if w not in LINKING and w not in attrs
                               and w not in nouns_here and w not in literal
                               and w not in _refers), None)
                pick = after if (after and after not in values) else (
                    before if (before and before not in values) else None)
                if pick:
                    out[real] = _whole(pick)
                break

    for attr, meta in (spec.get("observed") or {}).items():   # 3 · observed, through its doc
        doc = {_stem(w.strip(".,'")) for w in str(meta.get("doc") or "").lower().split()
               if len(w) > 5}
        if doc & {_stem(w) for w in words}:
            out[attr] = not negated
    return out
