"""THE FRONT DOOR — junk out ASAP, one layer down (the operator's ruling, 2026-08-19).

The v2 degradation run priced two cells and the operator ruled them ONE defect. A leading
filler killed 9 of 10 instructed acts — the imperative-shape test never fired because the
clause no longer opened on its verb. A typo'd CLOSED-SET marker (`no wati`, `i mesnt`,
`wehn you get a chance`) un-recognized its construct, and the debris became operation
targets — `stop_vm(sorry)`. Both are junk surviving past the entrance; every construct
downstream pays for it separately, so patching each consumer re-fights the same defect at
every reader forever. This module is the one pass instead: it runs BEFORE anything reads.

⇒⇒ WHAT IT PRODUCES — a working VIEW, never a rewrite of the request:
    text      what every construct reads from here on
    back      view offset -> original offset (len(text)+1), so every reported span still
              lands on the ORIGINAL bytes — gold offsets and frozen sets untouched
    notices   one line per fix, surfaced — recognition is visible, never silent

⇒⇒ WHAT IT MAY TOUCH — six passes, and EVERY candidate comes from a CLOSED set:
    0   unicode spaces -> ' ', one character for one character (announced since 09-17)
    0a  a SEPARATOR joining two known closed words -> a space (`db-down`), same length
    0b  a FUSED pair with no separator, split only where the fusion hides a closed word
    1   a FILLED PAUSE (`iso.FILLED_PAUSE`, exact match) dropped with its separator
    2   a typo'd word INSIDE a closed-set phrase read as the phrase word: every other
        word of the phrase exact, the odd word >=4 letters at Damerau distance 1. The
        phrases are the ones that already exist — `self_repair.CORRECTIONS/RETRACTIONS`,
        `speech_act.WRAPPERS/COURTESY` — one copy each, imported.
    3   a LONE typo'd word, by N2's SIM CHECK (see the ruling below)
    4   a missing CLAUSE BREAK restored where `pass2.merge_cut_points` votes (N3)

⇒⇒ **AN OPERATION VERB *IS* REPAIRABLE, and this list said the opposite for a month.**
    The 14:44 draft of this file (0f22b30, 2026-08-19) put an OPERATION VERB under NEVER
    TOUCHES. N2 landed at 21:42 THE SAME DAY (07d0301) carrying the operator's ruling —
    *"very distinct common words like thrm = them, OR EVEN VERBS — the system should try
    to correct it"* — and the sim check has licensed a clause-initial verb ever since.
    The stale line survived 14 commits to this file and was found by the property sweep
    on 2026-09-17. A verb repair needs its slot to vote (clause-initial, or after
    `then`/`and`/`but`) exactly like every other class.
    ⇒⇒ ⚠ AND THE EXAMPLE THAT LINE USED TO CARRY IS NOW WRONG, WHICH IS WHY IT IS RECORDED
      RATHER THAN QUIETLY SWAPPED. Until 2026-09-18 this said *"`restrt` stays only because no
      single declared print explains it"* — true then, and true for the wrong reason: `restart`
      was ABSENT FROM THE GRAMMAR'S VOCABULARY ENTIRELY, so there was no candidate to repair
      toward. With `restart` added to `scan._operation_words`, `restrt` repairs by one
      drop-vowel print, exactly as N2 licenses. A docstring's example is a claim like any other
      and this one went stale in a day.

⇒⇒ WHAT IT NEVER TOUCHES — the operator's rulings, structural here by construction:
    · a NAME — a typo'd name is the name (`alpah` stays `alpah`): every candidate is
      drawn from a closed set, so a name can never BE one
    · anything in QUOTES — evidence is opaque testimony
    · a lone unknown word whose SLOT does not vote — single-word recognition (N2, the
      operator's ruling) fixes sure hits and runs the SIM CHECK on the rest: candidates
      from our closed sets only, each tried in place, the surrounding grammar decides;
      ties and no-fits change nothing ('did you eveyr stop it' stays as typed)

Residual risk, accepted and documented: a real word one edit from a marker word in marker
position (`no want` ~ `no wait`) would be read as the marker. The notice is the guard —
the recognition is shown, and the eval prices the cell.
"""
import re
from typing import List, NamedTuple, Tuple


class View(NamedTuple):
    text: str
    back: List[int]
    notices: List[str]
    original: str


class Repair(NamedTuple):
    """What the sim check found. `word` is the repair ONLY when exactly one candidate was
    licensed by its slot; otherwise it is empty and `ask` says why, which is the operator's
    bounce/ask ruling (2026-09-09) made visible instead of silent."""
    word: str            # "" unless exactly one candidate fit its slot
    prints: tuple        # the declared evidence for that repair
    ask: str             # "" | "ambiguous" | "unlicensed"
    cands: tuple         # the candidates behind an ask


def _phrase_force(phrase: str) -> str:
    """What a closed phrase DOES — the reason the door may not create one by repair.

    ⇒ It is not decoration in the notice. ROUTE has to ask a question the operator can answer,
      and *"did you mean `forget it`?"* is a different question from *"did you mean to CANCEL
      the previous order?"*. The second is the one that matters.
    """
    from .speech_act import WRAPPERS as _W, COURTESY as _C
    from . import self_repair as _sr
    if phrase in set(_sr.RETRACTIONS):
        return f"'{phrase}' cancels what stands"
    if phrase in set(_sr.CORRECTIONS):
        return f"'{phrase}' redirects the request"
    if phrase in set(_W):
        return f"'{phrase}' turns an order into a question"
    if phrase in set(_C):
        return f"'{phrase}' raises the authority asked for"
    return f"'{phrase}' changes the act"


_UNICODE_SPACES = {0x00A0, 0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,
                   0x2007, 0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000}


def _despace(text: str) -> str:
    """A NON-BREAKING SPACE (and its kin) is a SPACE (2026-09-06). `vm\xa0stop\xa0biggest_vm` is
    what pasting from a web page or a rendered doc gives you — the tokenizer saw one long token and
    the patient was lost. Not the Serpent inventing noise: real people paste. One character for one
    character, so every offset stays byte-exact and this composes with every pass below."""
    if not any(ord(c) in _UNICODE_SPACES for c in text):
        return text
    return "".join(" " if ord(c) in _UNICODE_SPACES else c for c in text)


def read(request: str, board=None, known=None) -> View:
    """One pass, at the entrance. Clean text returns the identity view. `known` — extra standing
    object NAMES (the world's declared vms/networks) the SEPARATOR pass may treat as closed for
    de-fusing (`db-down` -> `db down`). They are fed ONLY to the separator pass, NEVER to typo
    recognition, so the operator's rule holds: a typo'd name is still the name (`alpah` stays)."""
    _req = str(request)
    text = _despace(_req)            # unicode spaces -> ' ' (same length, offsets byte-exact)
    # ⇒ AND IT SAYS SO (operator ruling 2026-09-17, found by the property sweep). The fold
    #   changes bytes, and *"recognition is visible, never silent"* admits no exception for a
    #   change that happens to be harmless: a request pasted from a rendered doc IS edited, and
    #   the operator has to be able to see that it was. ONE notice however many folded — the
    #   count carries the information and a line per character would be the noise that makes
    #   notices stop being read.
    _folded = sum(1 for a, b in zip(_req, text) if a != b)
    notes_d = [f"folded {_folded} unicode space{'' if _folded == 1 else 's'} to ' '"] if _folded else []
    # 0 · SEPARATOR-JOINED closed words -> spaces (2026-09-02): a hyphen/underscore joining two
    #     KNOWN closed words (or declared standing objects) is a fusion separator the tokenizer
    #     already sees but the text kept, so `do-not-stop-x`/`db-down` never fed the words apart.
    #     A single-char swap, so offsets stay byte-exact and compose through the passes below; an
    #     UNDECLARED name (never known) is never broken (`web-01`, `foo-bar` keep the name whole).
    edits_s, notes_s = _separator_pass(text, board, known)
    if edits_s:
        text = _apply(text, edits_s)[0]        # same-length -> offsets unchanged, maps stay 1:1
    # 0b · FUSED WORDS (no separator) — ledger #9, built against its measurement (9d59f14-*:
    #     4 spans, 3 acts, +3 halluc in 10 pairs, all where the fusion hides a CLOSED
    #     word). A split changes tokenization, so it runs before every other pass and
    #     the offset maps COMPOSE.
    edits0, notes0 = _split_pass(text, board, known)
    if edits0:
        text0, back0 = _apply(text, edits0)
        inner = _read_stages(text0, board)
        back = [back0[b] for b in inner.back]
        return View(inner.text, back, notes_d + notes_s + notes0 + inner.notices + _shape_pass(inner.text), _req)
    inner = _read_stages(text, board)
    return View(inner.text, inner.back, notes_d + notes_s + inner.notices + _shape_pass(inner.text), _req)


def defused(request: str, board=None, known=None) -> str:
    """The SEPARATOR-ONLY view of the original bytes (2026-09-06) — hyphen/underscore fusions of
    KNOWN closed words (and declared standing objects) opened to spaces, and NOTHING else.
    Every separator edit is a single-char swap, so the result is the SAME LENGTH as `request`
    and every offset into it is an offset into the original. That is what makes it safe as the
    RULE LAYER's text: annotate_roles regexes this string while the rows it labels carry ORIGINAL
    offsets, so the two must stay in the same coordinate space. `_split_pass` is deliberately NOT
    run here — it changes length, which would break that correspondence."""
    _req = _despace(str(request))
    edits, _ = _separator_pass(_req, board, known)
    return _apply(_req, edits)[0] if edits else _req


# ⇒ THE FUNCTION WORDS live in the codex — the SSOT for every English closed class
#   (`tests/test_language_layer.py` enforces that a seam module holds none of its own).
from ..codex import FUNCTION_WORDS as _FUNCTION_WORDS


# ⇒ A FLAG IS A CODE SHAPE (operator ruling 2026-09-14, extending the 2026-09-07 code-shape
#   ruling). A token that OBVIOUSLY begins with `-`/`--` and a letter is shell option syntax —
#   `--all-the-vms`, `-xzf`, `--no-color`. Recognising it is purely SYNTACTIC (no world), so the
#   front door leaves it BYTE-IDENTICAL and names it; whether it is a real option, and which vms,
#   is READ/ROUTE's call — the layer that has the world. "Obvious enough" is dash(es) + a letter at
#   a token start: `-5`, a bare `--`, and a mid-word hyphen never match, so a borderline token
#   flows downstream instead of the front door guessing.
_FLAG = re.compile(r"(?<!\S)--?[a-z][a-z0-9]*(?:-[a-z0-9]+)*", re.I)


def _shape_pass(text: str):
    """DETECT the code-world shapes; never rewrite them (operator rulings, 2026-09-07).

    A path is already decomposable by its own structure — `/etc/web/temp.cfg` is root -> etc ->
    web -> temp, type cfg — so it only needs to be RECOGNISED; whoever cares about it will take it
    apart, and a wrong path is caught downstream. camelCase, snake_case and a run-on are the same
    kind of thing: conventionally CODE, an identifier whose other side we cannot see. The
    orchestrator is language-independent and code-independent, so splitting one would inject a
    meaning we cannot justify — `getUserName` and `alphaSHOULDbERESTARTEDNOW` are the same shape
    and we genuinely cannot tell them apart. Detecting says what the token IS and leaves the
    decision to a layer that can ask.

    Emits notices only. Byte-identical output, so it composes with every pass and costs no offset.
    """
    out: List[str] = []
    seen = set()
    for tok in text.split():
        t = tok.strip(",;:!?\"'`")
        if len(t) < 3 or t.lower() in seen:
            continue
        if re.match(r"^[a-z][a-z0-9+.-]*://", t, re.I):        shape = "a url"
        elif "/" in t or "\\" in t:                            shape = "a path"
        elif re.search(r"\.[a-z]{2,4}$", t, re.I) and t.count(".") == 1:  shape = "a filename"
        elif re.search(r"[$|]|&&|[a-z]=[^ ]", t, re.I):          shape = "a shell expression"
        elif re.match(r"^--?[a-z]", t, re.I):                    shape = "a flag / option"
        elif re.search(r"[a-z][A-Z]", t):                        shape = "camelCase — an identifier"
        elif re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)+", t):       shape = "snake_case — an identifier"
        else:
            continue
        seen.add(t.lower())
        out.append(f"{t!r} looks like {shape} — left whole")
    return out


def _separator_pass(text: str, board=None, known_extra=None):
    """A hyphen or underscore JOINING two KNOWN words (closed-set, or a declared standing object in
    `known_extra`) is a fusion separator, read as a space (`do-not-stop` -> `do not stop`,
    `db-down` -> `db down`). Only a KNOWN-KNOWN pair splits (with the same particle+particle guard
    as `_split_pass`, so `back-up` stays `backup`), so an UNDECLARED name is never broken. A
    single-char replacement keeps every offset byte-exact. Sim-check principle for separators."""
    low = text.lower()
    opaque = _quoted(low)
    # a flag is a code shape (2026-09-14): opaque to the separator pass exactly like a quote, so the
    #   run inside `--all-the-vms` is never opened. Detecting it is syntactic; the decision is READ/ROUTE's.
    opaque = list(opaque) + [(m.start(), m.end()) for m in _FLAG.finditer(low)]
    _openers, _nouns, _ops, known = _vocab(board)
    if known_extra:
        known = known | {str(k).lower() for k in known_extra}
    from .scan import PARTICLES as _parts
    edits: List[Tuple[int, int, str]] = []
    notices: List[str] = []
    # ⇒ WHICH CHARACTERS JOIN (2026-09-07): a backslash and a plus fuse exactly as a hyphen and an
    #   underscore do — `virsh\\shutdown\\db`, `it+wld+bt+fr+web`. And a segment carrying a DIGIT
    #   (`over-2gb`, `to_16gb`) used to TERMINATE the run, so the separators either side of it never
    #   opened; digits are allowed inside a segment now. Name safety is unchanged: it rests on the
    #   evidence test below, not on the character class.
    #   `&` joins as the others do (`stop&restart_alpha`), and a RUN of separators is still one
    #   separator: `snapshot\\_alpha` puts TWO characters between the words, and requiring exactly
    #   one meant the whole run never matched and nothing was freed (2026-09-08).
    for m in re.finditer(r"[a-z0-9']+(?:[-_\\+&]+[a-z0-9']+)+", low):
        rs, re_ = m.start(), m.end()
        if any(qs <= rs and re_ <= qe for qs, qe in opaque):
            continue                                    # quoted: opaque
        # the PARTS class must match the RUN class, or the character between two parts is not the
        #   separator at all and the pass overwrites content: with a letters-only parts regex,
        #   `gr8+fr` replaced the DIGIT `8` with a space (caught by this rule's own control).
        parts = list(re.finditer(r"[a-z0-9']+", m.group(0)))
        # ⇒ THE RUN, NOT THE PAIR (2026-09-06, marathon family C). Splitting only ADJACENT
        #   known-known pairs left every chain with one unknown token in it half-fused, and the
        #   atom behind the block stayed lost: `which-vms-r-stopped` -> `which vms-r-stopped`
        #   (`r`, a typo of "are", freezes `stopped`), `delete-the-vms-over-4gb` stops at `4gb`,
        #   `show-me-alphas-logs` never split at all. TWO known words ANYWHERE in the run is the
        #   evidence that the run is a fused SENTENCE rather than a name — a name has at most one
        #   (`web-01` never even matches this pattern, `foo-bar-baz` has none), so the operator's
        #   ruling that a typo'd name is still the name holds. Below two, nothing changes.
        _kn = sum(1 for _p in parts if _p.group(0) in known)
        # ⇒ A FUNCTION WORD IS THE STRONGEST EVIDENCE OF A FUSED SENTENCE (2026-09-07). Two known
        #   words freed the long chains but refused the short ones — `un-doh-that` kept `that`
        #   glued because only one segment was known. A NAME never contains a proform, a
        #   determiner or a conjunction: `web-01`, `foo-bar-baz`, `alpah-01` carry none. So one
        #   closed-class FUNCTION word in the run is evidence a name can't produce, and it opens
        #   the run on its own.
        _fn = any(_p.group(0) in _FUNCTION_WORDS for _p in parts)
        # ⇒⇒ **AN IDENTIFIER SUFFIX MARKS THE WHOLE RUN AS A NAME** (2026-09-18). The pure-digit
        #   guard below is per-CUT-POINT, so it protected the separators either side of the digit
        #   and nothing else: `lab-core-2` lost its first separator and came back `lab core-2`,
        #   with `lab` and `core` both declared standing objects making the pair look like a
        #   fusion. That was the ENTIRE remaining false repair on the door corpus.
        #   ⇒ THE RULE IS THE ONE THE GUARD BELOW ALREADY STATES — *"a pure-digit segment is an
        #     identifier SUFFIX"*. A run that ENDS in one is a name: `web-01`, `vm-2`,
        #     `lab-core-2`. Completing a rule against its own stated reasoning, exactly as
        #     `CUT_NEGATION` was on 09-17.
        #   ⇒ **LAST SEGMENT, NOT ANY SEGMENT**, and the difference is measured: `stop-the-2-vms`
        #     is a fused SENTENCE whose `2` is a quantifier, not a suffix, and a run-level check
        #     would have frozen it. `delete-the-vms-over-4gb` is unaffected either way — `4gb`
        #     carries letters, so it is a value shape and never a bare index.
        if parts[-1].group(0).isdigit():
            continue
        for k in range(len(parts) - 1):
            a, b = parts[k].group(0), parts[k + 1].group(0)
            if a in _parts and b in _parts:
                continue                                # `back-up` stays `backup`
            # ⇒ A PURE-DIGIT SEGMENT IS AN IDENTIFIER SUFFIX, NEVER A WORD (2026-09-07):
            #   `web-01`, `test01-node`, `vm-2` — cutting either side of it breaks a NAME, which
            #   the operator's ruling forbids. `over-2gb` is untouched by this: `2gb` is a digit
            #   AND letters, a value shape, not a bare index.
            if a.isdigit() or b.isdigit():
                continue
            if _kn >= 2 or _fn or (a in known and b in known):
                # the separator may be more than one character; each becomes a space, so the
                #   replacement is the same LENGTH and every offset downstream still holds.
                s0 = rs + parts[k].end(); e0 = rs + parts[k + 1].start()
                edits.append((s0, e0, " " * (e0 - s0)))
                notices.append(f"read '{a}{text[s0:e0]}{b}' as '{a} {b}'")
    return edits, notices


def _split_pass(text: str, board=None, named=None):
    """An UNKNOWN token that splits into two known words is read apart — where the
    grammar votes (the operator's sim-check principle). Exactly one fitting split wins;
    ambiguity or no vote changes nothing (`cancel` never becomes `can cel`).

    ⇒⇒ **BOTH HALVES MUST BE WORDS THE SYSTEM KNOWS** (2026-09-17). Four of the six fit rules
      are asymmetric — they bind ONE half to a closed set and licensed the other from a
      NEIGHBOUR — and the free half was checked against nothing at all:

          a in openers and (b in nouns or nxt in nouns)     # nxt a noun -> b unconstrained
          b in nouns and (prev in openers or a in openers)  # prev an opener -> a unconstrained

      In `stop the X vm` the next token is `vm`, a noun, so EVERY word opening with `an`/`no`/
      `all`/`me` was torn whatever the remainder: `antiseptic` -> `an tiseptic`, `merchants` ->
      `me rchants`, `cabinet` -> `cabi net`. Measured over 6000 sampled dictionary words in that
      one frame: 188 damaged, 3.13%. The operator-visible ones were worse than the rate —
      `stopping` -> `stop ping` turns a status report into TWO operation verbs, `~/.gorgon/...`
      -> `~/.go rgon/...` corrupts a path, and `backer` -> `back` because the split feeds `er`
      to the filled-pause drop and the word is LOST rather than mangled.

    ⇒ THE CONSTRAINT IS THE DOCSTRING'S OWN FIRST LINE, ENFORCED: *two known words*. A closed
      word, or a DECLARED STANDING OBJECT — which is why `named` exists. The name half is what
      the asymmetric rules were FOR (`thedb vm`, `stopalpha`), and the world is the only thing
      that can say whether `db` is a machine. `_separator_pass` has been given the declared
      objects since 2026-09-02; this pass was not, and that asymmetry was the whole defect.

    ⇒ WHEN NOBODY PASSES `named` THE DOOR GETS STRICTER, NOT WRONGER: with no world in hand a
      split must be two closed words, which is rule 2. That is the safe direction — production
      calls `read()` without the lab today ([[gorgon-handover-2026-09-17]] D2), so it simply
      declines splits it cannot justify instead of guessing at them.
    """
    _named = {str(n).lower() for n in (named or ())}
    low = text.lower()
    opaque = _quoted(low)
    toks = [(w, s, e) for w, s, e in _tokens(low)
            if not any(qs <= s and e <= qe for qs, qe in opaque)]
    words = [t[0] for t in toks]
    openers, nouns, ops, known = _vocab(board)
    from .scan import BOUNDARIES, PARTICLES as _parts
    known = known | {b for b in BOUNDARIES if b.isalpha()} | {
        "not", "no", "these", "those", "this", "that", "there", "their", "they",
        "than", "have", "has", "had"}
    heads = {"if", "unless", "when", "whenever", "after", "once"}

    def _half(x: str) -> bool:
        """Is this side of the split a word the system knows? A closed word, or a declared
        standing object. Nothing else — a remainder nobody can name is evidence the token was
        never fused in the first place."""
        return x in known or x in _named

    edits, notices = [], []
    # ⇒ THE DECLARED NON-FUSIONS (codex, 2026-09-17). An English word that decomposes into two
    #   closed words is still one word, and no rule below can tell `beat` (`be at`) from `isnot`
    #   (`is not`) — both are function+function, both halves closed, and one must split. There is
    #   no structural signal, so the difference is DECLARED. 259 words, veto only.
    from ...english.codex import FALSE_FUSIONS as _solid
    for idx, (w, s_, e_) in enumerate(toks):
        if len(w) < 4 or "'" in w or w in known or w in _solid:
            continue
        prev = words[idx - 1] if idx > 0 else None
        nxt = words[idx + 1] if idx + 1 < len(words) else None
        seg_initial = (idx == 0 or prev in {"then", "and", "but"}
                       or text[:s_].rstrip()[-1:] in ".;!?")
        fits = []
        for i in range(1, len(w)):
            a, b = w[:i], w[i:]
            if len(b) < 2:
                continue
            if len(a) == 1:
                fit = a == "a" and b in known          # `achance` — the one 1-char word
            elif a in known and b in known:
                # `isnot` · `onthe` · `vmand` — but never particle+particle:
                # `backup` is a word, not `back` fused to `up` (found by the suite)
                fit = not (a in _parts and b in _parts)
            elif a in ops and seg_initial:
                fit = _half(b)                         # `stopalpha.` · `then launchbeta`
            elif a in openers and (b in nouns or nxt in nouns):
                fit = _half(b)                         # `thedb vm`
            elif b in nouns and (prev in openers or a in openers):
                fit = _half(a)                         # `the testvms`
            elif a in heads and seg_initial:
                fit = _half(b)                         # `ifalpha is stopped`
            else:
                fit = False
            if fit:
                fits.append(i)
        if len(fits) == 1:
            i = fits[0]
            # a pure INSERTION — nothing replaced, so every original byte keeps a
            # 1:1 mapped position and span edges stay byte-exact through the split
            edits.append((s_ + i, s_ + i, " "))
            notices.append(f"read '{w}' as '{w[:i]} {w[i:]}'")
    return edits, notices


def _read_stages(request: str, board=None) -> View:
    """Stages 1-3 (pauses · phrase and word typos · comma restore) over one text."""
    text = str(request)
    low = text.lower()
    opaque = _quoted(low)
    toks = [(w, s, e) for w, s, e in _tokens(low)
            if not any(qs <= s and e <= qe for qs, qe in opaque)]

    edits: List[Tuple[int, int, str]] = []
    notices: List[str] = []

    # 1 · filled pauses out, with one adjacent separator
    from . import iso as _iso
    for w, s, e in toks:
        if w in _iso.FILLED_PAUSE:
            m = re.match(r"[,\s]+", low[e:])
            if m:
                e = e + m.end()
            elif s > 0:                                   # pause at the very end
                m2 = re.search(r"[,\s]+$", low[:s])
                if m2:
                    s = m2.start()
            edits.append((s, e, ""))
            notices.append(f"dropped filled pause '{w}'")

    # 2 · a typo'd word inside a closed-set phrase, context-anchored
    from . import self_repair as _sr
    from .speech_act import WRAPPERS, COURTESY
    phrases = [p.split() for p in (tuple(_sr.CORRECTIONS) + tuple(_sr.RETRACTIONS)
                                   + WRAPPERS + COURTESY)
               if len(p.split()) >= 2]
    taken = [(s, e) for s, e, _ in edits]
    # ⇒⇒ **AN EXACT PHRASE IS NOT A TYPO OF A DIFFERENT PHRASE** (2026-09-17). `i mean` and
    #   `i meant` are BOTH declared corrections. The exact match produced no edit — correctly,
    #   there is nothing to repair — but it also left the span free, so the next phrase tried
    #   `mean` against `meant`, found one edit, and rewrote a valid closed phrase into another
    #   one. Claiming every exactly-matched phrase FIRST is the whole fix.
    for pwords in phrases:
        for i in range(len(toks) - len(pwords) + 1):
            window = toks[i:i + len(pwords)]
            if all(w == pw for (w, _s, _e), pw in zip(window, pwords)):
                taken.append((window[0][1], window[-1][2]))
    # ⇒⇒ **AND A WORD THE SYSTEM ALREADY KNOWS IS NEVER A TYPO OF ANYTHING** (2026-09-17). This
    #   loop had no `known` guard at all, so `take that snapshot` became `make that snapshot` —
    #   one declared OPERATION VERB rewritten into another, which changes the act. Stage 3 has
    #   carried this guard since 2026-09-08 ("a word in any declared closed class is a real word
    #   and a real word is never repaired"); stage 2 never got it.
    _, _, _, _known = _vocab(board)
    # ⇒ AND AN ENGLISH WORD IS NEVER A TYPO EITHER (codex, operator ruling 2026-09-17:
    #   *"forgot it stays as typed"*). 144 declared; veto only, never a licence.
    from ...english.codex import FALSE_TYPOS as _FALSE_TYPOS
    # ⇒⇒ **STAGE 2 NO LONGER REPAIRS. IT DECLINES AND CARRIES THE CANDIDATES.**
    #   OPERATOR CHARTER, 2026-09-19: *"the front door should only fix typos on obviously wrong /
    #   non-existent words, fix noise, add commas and spaces where obvious. If anything changes
    #   meaning it's not the door's job — if it CAN alter a meaning we move it to route to ask.
    #   I would rather not serve something than serve something the user didn't ask for."*
    #
    #   ⇒ **EVERY PHRASE IN THIS LOOP IS MEANING-BEARING. THAT IS WHAT A CLOSED PHRASE IS.**
    #     Measured over the 20 stage-2 cases in the door corpus on 2026-09-19:
    #         8  RETRACTION  — `forget it`, `cancel that`, `never mind` … CANCELS what stands
    #         8  CORRECTION  — `make that`, `i mean`, `no wait` …        REDIRECTS the target
    #         2  WRAPPER     — `tell me`, `let me know`                  order becomes a question
    #         2  COURTESY    — `when you get a chance` …                 ⚠ FLIPS FETCH -> ACHIEVE
    #     Not one survives the charter. The last two are the sharpest: the 2026-08-14 finding
    #     [[gorgon-courtesy-escalates-intent]] is that a pleasantry GRANTS WRITE AUTHORITY, so
    #     repairing one character in `wehn you get a chance` escalated a read into a write.
    #
    #   ⇒ **AND A FALSE RETRACTION FAILS SILENTLY, WHICH IS THE WORST DIRECTION.** Inventing
    #     `forget it` cancels an order the operator gave; they see a request that was accepted
    #     and did nothing. Declining costs a question. That trade is the charter.
    #
    #   ⇒ ALL CANDIDATES ARE CARRIED, not the first or the best (operator, 2026-09-19). One
    #     token may sit one edit from several declared phrases; picking among them is the same
    #     judgement the door is being told not to make, so ROUTE gets the whole set.
    _cands_at = {}                                        # (start, end) -> [(tok, phrase), …]
    for pwords in phrases:
        for i in range(len(toks) - len(pwords) + 1):
            window = toks[i:i + len(pwords)]
            fuzzy = None                                  # (tok, start, end, phrase word)
            for (w, s, e), pw in zip(window, pwords):
                if w == pw:
                    continue
                if (fuzzy is None and len(w) >= 4 and len(pw) >= 4
                        and w not in _known and w not in _FALSE_TYPOS
                        and _damerau1(w, pw)):
                    fuzzy = (w, s, e, pw)
                else:
                    fuzzy = False
                    break
            if not fuzzy:
                continue
            w, s, e, pw = fuzzy
            if any(not (e <= ts or te <= s) for ts, te in taken):
                continue
            _cands_at.setdefault((s, e), (w, [], []))[1].append(" ".join(pwords))
            _cands_at[(s, e)][2].append((window[0][1], window[-1][2]))
    for (s, e), (w, phs, _spans) in sorted(_cands_at.items()):
        _seen, _uniq = set(), []
        for ph in phs:                                    # stable order, no duplicates
            if ph not in _seen:
                _seen.add(ph); _uniq.append(ph)
        notices.append(
            f"could not apply '{w}' here — it is one edit from "
            f"{' or '.join(repr(x) for x in _uniq)}, and that would change what the request "
            f"does ({'; '.join(_phrase_force(x) for x in _uniq)}); ask")

    # 3 · single-word typo recognition — N2, the operator's ruling: sure hits fixed,
    #     ambiguity settled by the SIM CHECK (each candidate tried in place; the slot
    #     votes), ties or no fit left alone. Candidates come ONLY from our own closed
    #     sets — never the whole language, so a name can never be a candidate.
    # ⇒⇒ **A SPAN STAGE 2 DECLINED IS CLOSED TO STAGE 3.** Found the moment the decline was
    #   first run (2026-09-19): stage 2 refused to make `mkae that beta` into `make that beta`,
    #   and the sim check then repaired `mkae` -> `make` on its own — because `make` is an
    #   operation word and stage 3 judges words, not phrases. The phrase was reconstituted and
    #   the charter defeated by the very next pass. **A decline that a later pass can override
    #   is not a decline**, which is this project's dominant defect class pointed at a refusal
    #   instead of a feature.
    taken2 = [(s_, e_) for s_, e_, _ in edits] + list(_cands_at)
    for w, s_, e_ in toks:
        if len(w) < 4 or "'" in w:
            continue
        if any(not (e_ <= ts or te <= s_) for ts, te in taken2):
            continue
        got = _recognise(w, toks, s_, board)
        if got.word:
            taken2.append((s_, e_))
            edits.append((s_, e_, got.word))
            #   the notice carries WHY, not just what: a repair without its evidence is a guess
            #   that happens to be right.
            _why = " + ".join(got.prints) if got.prints else "exact"
            notices.append(f"read '{w}' as '{got.word}' ({_why})")
        elif got.ask == "ambiguous":
            notices.append(f"could not read '{w}' — it fits {' and '.join(got.cands)} equally; ask")
        elif got.ask == "unlicensed":
            notices.append(f"could not read '{w}' here — it looks like "
                           f"{' or '.join(got.cands)}, but nothing in this slot licenses the "
                           f"repair; ask")

    if edits:
        mid, back1 = _apply(text, edits)
    else:
        mid, back1 = text, list(range(len(text) + 1))

    # 4 · N3 (operator-approved) — RESTORE THE MISSING CLAUSE BREAK. The clause-merge
    #     rules already know where the comma belonged (`pass2.merge_cut_points` — one
    #     copy); the view puts it back so pass 1's span walk, iso, self_repair and both
    #     act channels all see the boundary. Sim-check principle: the rules only fire
    #     where a closed class votes — no vote, no comma. Computed on the STAGE-1 text
    #     so a dropped pause or fixed typo cannot hide a cut.
    # ⇒⇒ **A CUT INSIDE A DECLINED PHRASE IS SUPPRESSED** (2026-09-19, found by running the
    #   charter change). `wehn you get a chance stop alpha` used to be repaired to `when …`, and
    #   rule 1 then cut after the courtesy literal. With the repair declined, the literal no
    #   longer matches, rule 6 reads `get a chance` as a second imperative, and the door wrote
    #   `wehn you, get a chance stop alpha` — a comma in the middle of the very phrase it had
    #   just said it could not read.
    #   ⇒ THE RULE IS THE CHARTER'S OWN: commas go in *where it is obvious*. Inside a span the
    #     door has declared unreadable, nothing is obvious. The suppression is scoped to the
    #     candidate phrase's span, so a boundary elsewhere in the request is untouched.
    from .pass2 import merge_cut_points
    _mute = [sp for _k, (_w, _p, sps) in _cands_at.items() for sp in sps]
    cuts = [c for c in merge_cut_points(mid)
            if not any(a < c < b for a, b in _mute)]
    if not cuts:
        return View(mid, back1, notices, text)
    edits2 = []
    for at in cuts:
        if 0 < at <= len(mid) and mid[at - 1] == " ":
            edits2.append((at - 1, at, ", "))
        elif at < len(mid) and mid[at] == " ":
            edits2.append((at, at + 1, ", "))
        else:
            edits2.append((at, at, ", "))
        word = mid[at:].split()[0] if mid[at:].split() else ""
        notices.append(f"read a clause break before '{word}'")
    new, back2 = _apply(mid, edits2)
    back = [back1[b] for b in back2]
    return View(new, back, notices, text)


def _vocab(board):
    """The candidate sets and the known-word guard — closed sets ONLY, read not listed."""
    from .scan import OBJECT_OPENERS, GRAMMAR, _index, _operation_words, PARTICLES
    from . import self_repair as _sr, iso as _iso
    from .speech_act import WRAPPERS, COURTESY, AUXILIARIES, WH_WORDS
    nouns = set(_index(board) if board is not None else _index(_board()))
    ops = {w for w in _operation_words(None) if not w.endswith("s")}
    marker_words = {w for p in (tuple(_sr.CORRECTIONS) + tuple(_sr.RETRACTIONS)
                                + WRAPPERS + COURTESY) for w in p.split()}
    # ⇒ A WORD IN ANY DECLARED CLOSED CLASS IS A REAL WORD, AND A REAL WORD IS NEVER REPAIRED
    #   (2026-09-08). The guard held only the classes the seam happens to consume, so ordinary
    #   words the lab does not declare — `nope`, `lets`, `move` — were candidates for repair and
    #   got rewritten into declared ones. Every closed class the codex declares now guards.
    from ...english import codex as _CXk
    _closed_classes = set()
    for _n in ("NEGATION", "AFFIRMATION", "HEDGES", "EMPHATIC", "BACKCHANNEL", "APOLOGY",
               "TROUBLE", "FOCUS_PARTICLES", "LIGHT_VERBS", "TRANSFER_VERBS", "OBJECT_PRONOUNS",
               "SINGULAR_PROFORMS", "PLURAL_PROFORMS", "SELECTOR_PREPOSITIONS",
               "LOCATIVE_PREPOSITIONS", "CUT_DETERMINERS", "REASON_MARKER_WORDS",
               "DISTINCT", "PLURAL_PRONOUNS", "SIMILE", "ORDINALS"):
        _v = getattr(_CXk, _n, None)
        if _v:
            _closed_classes |= {str(x).lower() for x in _v}
    known = (set(OBJECT_OPENERS) | set(GRAMMAR) | nouns | ops | marker_words
             | set(AUXILIARIES) | set(WH_WORDS) | set(PARTICLES)
             | set(_iso.FILLED_PAUSE) | _closed_classes | {"vms", "vm's"})
    return OBJECT_OPENERS, nouns, ops, known


def _board():
    from planner.formula.legal import Board
    return Board()


def _statuses(board=None):
    """The manifest's declared STATUS values (`attr_values`) — the SSOT `scan` itself reads, so a
    typo'd status can be recognised (`dawn`->`down`, `stoppd`->`stopped`). SPARSE by design: only
    what the world names. Same shape scan uses; no dependency on the read_eval harness."""
    b = board if board is not None else _board()
    out = set()
    for _spec in (b.kinds or {}).values():
        for _vals in ((_spec or {}).get("attr_values") or {}).values():
            out |= {str(v).lower() for v in _vals}
        # ⇒ AND THE DECLARED VALUE ALIASES (2026-09-06). The manifest declares `up`->running and
        #   `down`->stopped in `value_aliases` — the operator's own row, 2026-08-05, whose doc says
        #   a declared synonym IS a manifest row. They are as much a declared status word as
        #   `running`, and `_manifest_states()` (the scorer's SSOT) has always counted them.
        #   Reading only `attr_values` was reading HALF the manifest: `dawn`->`down` could not be
        #   recognised, and the gap looked like a GOLD/MANIFEST mismatch when it was ours.
        for _amap in ((_spec or {}).get("value_aliases") or {}).values():
            out |= {str(k).lower() for k in (_amap or {})}
    return out


def _recognise(w, toks, at, board):
    """The sim check. Each closed-set candidate is tried in its slot; the grammar votes.

    opener  -> the next word is a noun (`eveyr vm` -> every; `did you eveyr stop` -> no)
    pronoun -> the previous word is an operation verb (`put thrm` -> them)
    verb    -> clause-initial position (`then launhc beta` -> launch)
    noun    -> an opener stands within the two words before it (`the dmz netwrk`)
    Exactly one fitting candidate wins; ties and no-fits change nothing.
    """
    from .scan import OBJECT_OPENERS
    openers, nouns, ops, known = _vocab(board)
    states = _statuses(board)                        # manifest STATUS values (running/stopped/up/down)
    # ⇒ A REAL WORD IS NEVER REPAIRED, and `known` was only ever Gorgon's half of that. The other
    #   half is English (codex, operator ruling 2026-09-17) — `made`, `boxes`, `dome` are not
    #   corrupt and have nothing to ask about, so they leave by the same door `known` does.
    from ...english.codex import FALSE_PRINTS as _english
    if w in known or w in _english:
        return Repair("", (), "", ())
    words = [t[0] for t in toks]
    i = next(j for j, t in enumerate(toks) if t[1] == at)
    prev = words[i - 1] if i > 0 else None
    nxt = words[i + 1] if i + 1 < len(words) else None
    _PRONOUNS = {"it", "them", "me", "us", "one", "ones", "everything"}
    _COPULAS = {"is", "are", "was", "were", "be", "been"}
    # ⇒ THE GATE IS THE CATALOGUE, NOT A DISTANCE (2026-09-07). `_damerau1` asked "is this within
    #   one edit" — a similarity score, which admits any near miss and refuses any real corruption
    #   that happens to carry two. The catalogue asks whether every edit is a DECLARED print, so a
    #   composition (27% of measured noise) is admitted WITH its evidence, and an undeclared edit is
    #   refused however close it looks. Candidates still come only from our own closed sets, so a
    #   NAME can never be one and the ruling that a typo'd name is the name holds structurally.
    from ..noise_prints import explain as _explain
    fits = {}
    explained = {}                          # every candidate the CATALOGUE explains, slot or no slot
    for cand in openers | nouns | ops | states:
        if len(cand) < 4 and cand not in _PRONOUNS:
            continue
        _prints = _explain(cand, w)
        if not _prints:                     # None = undeclared · () = identical, nothing to repair
            continue
        explained[cand] = _prints
        if cand in _PRONOUNS:
            if prev in ops:
                fits[cand] = _prints
        elif cand in states:
            # a STATUS sits after a copula in its clause: `is dawn` -> down, `is beta runnin`
            # -> running, `are the vms stoppd` -> stopped — a report, a polar query and a
            # relative clause all put a copula within the few words before the status.
            # ...but NEVER straight after a DETERMINER (2026-09-06): a status is a predicate,
            # never the head of a noun phrase, so `is the GOWN ready` is not `is the down ready`.
            # Adding the declared aliases `up`/`down` to the candidate set put `gown` one edit
            # from `down` and broke fix #3's own control; the determiner is the closed-class
            # discriminator that keeps it out. `is beta dawn` / `are the vms stoppd` are
            # untouched — their status word does not follow a determiner.
            from ..codex import CUT_DETERMINERS as _DETS
            # SLOT ONE — after a copula (`is beta dawn`, `are the vms stoppd`). A determiner
            #   directly before the word means it heads a noun phrase, not a predicate, so
            #   `is the GOWN ready` is refused here.
            if any(words[j] in _COPULAS for j in range(max(0, i - 3), i)) and prev not in _DETS:
                fits[cand] = _prints
            # SLOT TWO — PRE-NOMINAL, directly before a KIND noun (2026-09-07): `the RUNNIN vms`,
            #   `th STPPED vm`. A state modifies the kind it restricts, and that is as much a
            #   state slot as the copular one — the recogniser only licensed the copular half, so
            #   `restart the runnin VMs on lab` (no copula anywhere) went uncorrected. This is
            #   DENOISE, never inference: the slot licenses the class, the candidate must be a
            #   DECLARED status, and `_recognise` still changes nothing unless exactly one fits.
            #   A determiner before is normal here (`THE running vms`), so no determiner guard.
            elif nxt in nouns:
                fits[cand] = _prints
        elif cand in openers:
            if nxt in nouns:
                fits[cand] = _prints
        elif cand in nouns:
            if prev in openers or (i >= 2 and words[i - 2] in openers):
                fits[cand] = _prints
        elif cand in ops:
            if i == 0 or prev in {"then", "and", "but"}:
                fits[cand] = _prints
            # ⇒⇒ **AN INVERTED QUESTION PUTS ITS VERB BEHIND THE SUBJECT** (operator ruling
            #   2026-09-18, narrowest form, found by the first calibration sweep). The verb slot
            #   licensed two positions — clause-initial, and after `then`/`and`/`but` — so
            #   *"did you ktll it"* and *"can you stpo alpha"* were declined with "nothing in
            #   this slot licenses the repair", although the typo is unmistakably the verb. The
            #   shape is AUX + SUBJECT + VERB, never AUX + VERB, which is why widening to
            #   "previous word is an auxiliary" would have fixed nothing.
            #   ⇒ THREE CONDITIONS, ALL CLOSED CLASSES, AND THE THIRD IS THE OPERATOR'S NARROWING:
            #     the clause OPENS with an auxiliary · the previous word is a SUBJECT PRONOUN ·
            #     and the candidate is an OPERATION WORD, which this branch already guarantees.
            #     A noun- or opener-shaped typo in the same frame still asks.
            #   ⇒ THE SEAM ALREADY READS THIS FRAME ELSEWHERE — `_first_cut` refuses to cut a
            #     QUESTION SKIN on `words[0] in AUXILIARIES`. Same shape, same closed set.
            #   ⇒ **AND IT IS INFERENCE, NOT ENFORCEMENT.** Unlike `CUT_NEGATION`, `DUAL_CLASS`
            #     and the identifier suffix — each of which completed a rule against its own
            #     written reasoning — no docstring ever said this position was licensed. It is a
            #     new licence and it was ruled on as one.
            else:
                from .speech_act import AUXILIARIES as _AUXQ
                from ..codex import SUBJECT_PRONOUNS as _SUBJQ
                if words and words[0] in _AUXQ and prev in _SUBJQ:
                    fits[cand] = _prints
    #   THE SIMPLEST EXPLANATION WINS, AND ONLY IF IT IS STRICTLY SIMPLEST. Widening the gate from
    #   one edit to the catalogue admits a plural alongside its singular — `netwrk` is `network` by
    #   ONE print (drop-vowel) and `networks` by TWO (drop-vowel + truncate) — and calling that
    #   ambiguity refuses a reading nobody would call ambiguous. Fewer assumed corruptions is not
    #   inference about MEANING; it is declining to assume corruption that the evidence does not
    #   require. But a TIE stays a tie: `stpped` explains `stopped` and `stepped` at one print
    #   each, and that changes nothing — which is the ASK the caller will make.
    # ⇒ THE CATALOGUE'S TRICHOTOMY IS THE ASK-SIGNAL (2026-09-08), now SURFACED rather than
    #   swallowed (operator ruling 2026-09-09, `snaphot-it`): ONE licensed reading repairs with its
    #   evidence · TWO ask naming both · a word the catalogue DOES explain but NO slot licenses is
    #   unreadable HERE, and saying so is the bounce/ask. Returning a bare None made the third case
    #   indistinguishable from an ordinary unknown word, so `snapshot --create alpha snaphot-it`
    #   read as one silent patient blob and dropped `it`. The repair itself stays REFUSED — the
    #   clause-initial guard on a verb is what keeps a mid-clause NAME from being claimed.
    # only a SINGLE obvious corruption is actionable (2026-09-14): a multi-edit stretch is neither
    #   repaired nor asked about — it passes through, so `great` is not surfaced as "did you mean create".
    _unlic = tuple(sorted(c for c in explained if c not in fits and len(explained[c]) <= 1))
    if not fits:
        return Repair("", (), "unlicensed" if _unlic else "", _unlic)
    _least = min(len(v) for v in fits.values())
    # ⇒ ONE OBVIOUS CORRUPTION, OR NOTHING (operator ruling 2026-09-14). Typo correction is a
    #   never-ending cascade: to repair safely the front door would have to know every real word,
    #   which it deliberately does not. So it repairs only a SINGLE declared corruption print and
    #   passes a multi-edit stretch through UNTOUCHED — `great` -> `create` was substitute + truncate
    #   (2 prints), a common word pulled toward an operator. Left whole, READ reads it as a
    #   pleasantry and the world decides. Closed classes still guard the edit-distance-1 collisions
    #   the cap cannot tell apart (`last` -> `list`); this only refuses the STRETCHES.
    if _least > 1:
        return Repair("", (), "", ())
    _best = [(c, pr) for c, pr in fits.items() if len(pr) == _least]
    # ⇒⇒ **NUMBER AGREEMENT BREAKS A SINGULAR/PLURAL TIE** (operator ruling 2026-09-18, found by
    #   the first calibration sweep). A truncated plural sits one print from BOTH forms —
    #   `networ` explains `network` and `networks` equally — and the sim check declined every
    #   one of them. But the clause has already said which: *"the networ IS up"* is singular and
    #   *"the networs ARE up"* is plural. Asking there is declining to read a signal we hold.
    #   ⇒ THE SIGNAL IS A CLOSED CLASS AND IT IS ALREADY IN THIS FUNCTION — `_COPULAS`, split by
    #     the number each form carries. `be`/`been` carry none and decide nothing.
    #   ⇒ **ONLY A SINGULAR/PLURAL PAIR, AND ONLY A TWO-WAY TIE.** `yost` explains `host` and
    #     `most` equally and that is a REAL tie with nothing to resolve it — it still asks, as
    #     does any tie of three or more. The rule reaches exactly the class it was ruled for.
    if len(_best) == 2:
        _c1, _c2 = sorted(c for c, _ in _best)
        if _c2 == _c1 + "s":                       # a singular and its plural, nothing else
            _sing = {"is", "was"} & set(words)
            _plur = {"are", "were"} & set(words)
            if _sing and not _plur:
                _best = [(c, pr) for c, pr in _best if c == _c1]
            elif _plur and not _sing:
                _best = [(c, pr) for c, pr in _best if c == _c2]
    if len(_best) != 1:
        return Repair("", (), "ambiguous", tuple(sorted(c for c, _ in _best)))
    return Repair(_best[0][0], _best[0][1], "", ())


def _tokens(low: str):
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[a-z']+", low)]


def _quoted(low: str):
    """Quoted regions are opaque. The lookarounds keep apostrophes (don't) out of it."""
    spans = [(m.start(), m.end())
             for m in re.finditer(r"(?<![a-z])'[^']*'(?![a-z])", low)]
    spans += [(m.start(), m.end()) for m in re.finditer(r'"[^"]*"', low)]
    spans += [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`", low)]
    return spans


def _damerau1(a: str, b: str) -> bool:
    """Exactly one substitution, adjacent transposition, insertion or deletion."""
    if a == b:
        return False
    la, lb = len(a), len(b)
    if la == lb:
        diffs = [i for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        return (len(diffs) == 2 and diffs[1] == diffs[0] + 1
                and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]])
    if abs(la - lb) != 1:
        return False
    if la > lb:
        a, b, la = b, a, lb
    i = 0
    while i < la and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def _apply(text: str, edits: List[Tuple[int, int, str]]):
    """Apply non-overlapping edits; back[i] = original offset of view char i."""
    edits = sorted(edits)
    out: List[str] = []
    back: List[int] = []
    at = 0
    for s, e, rep in edits:
        out.append(text[at:s])
        back.extend(range(at, s))
        out.append(rep)
        # char-granular: the k-th repair byte maps to the k-th original byte while one
        # exists (same-length typo fixes stay byte-exact); the tail pins to the last
        back.extend(s + min(k, max(e - s - 1, 0)) for k in range(len(rep)))
        at = e
    out.append(text[at:])
    back.extend(range(at, len(text)))
    back.append(len(text))
    return "".join(out), back
