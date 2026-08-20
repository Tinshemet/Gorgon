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

⇒⇒ WHAT IT MAY TOUCH — exactly two things, both closed:
    1. a FILLED PAUSE (`iso.FILLED_PAUSE`, exact match) is dropped with its separator
    2. a typo'd word INSIDE a closed-set phrase is read as the phrase word: every other
       word of the phrase exact, the odd word >=4 letters at Damerau distance 1. The
       phrases are the ones that already exist — `self_repair.CORRECTIONS/RETRACTIONS`,
       `speech_act.WRAPPERS/COURTESY` — one copy each, imported.

⇒⇒ WHAT IT NEVER TOUCHES — the operator's rulings, structural here by construction:
    · a NAME — a typo'd name is the name (`alpah` stays `alpah`); only words sitting
      inside a matched closed phrase can ever be edited, and names cannot sit there
    · an OPERATION VERB — `restrt` measured as recoverable: imperative shape still
      routes it and translation is the model's job
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


def read(request: str, board=None) -> View:
    """One pass, at the entrance. Clean text returns the identity view."""
    text = str(request)
    # 0 · FUSED WORDS FIRST — ledger #9, built against its measurement (9d59f14-*:
    #     4 spans, 3 acts, +3 halluc in 10 pairs, all where the fusion hides a CLOSED
    #     word). A split changes tokenization, so it runs before every other pass and
    #     the offset maps COMPOSE.
    edits0, notes0 = _split_pass(text, board)
    if edits0:
        text0, back0 = _apply(text, edits0)
        inner = _read_stages(text0, board)
        back = [back0[b] for b in inner.back]
        return View(inner.text, back, notes0 + inner.notices, text)
    return _read_stages(text, board)


def _split_pass(text: str, board=None):
    """An UNKNOWN token that splits into two known words is read apart — where the
    grammar votes (the operator's sim-check principle). Exactly one fitting split wins;
    ambiguity or no vote changes nothing (`cancel` never becomes `can cel`)."""
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
    edits, notices = [], []
    for idx, (w, s_, e_) in enumerate(toks):
        if len(w) < 4 or "'" in w or w in known:
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
                fit = True                             # `stopalpha.` · `then launchbeta`
            elif a in openers and (b in nouns or nxt in nouns):
                fit = True                             # `thedb vm`
            elif b in nouns and (prev in openers or a in openers):
                fit = True                             # `the testvms`
            elif a in heads and seg_initial:
                fit = True                             # `ifalpha is stopped`
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
    for pwords in phrases:
        for i in range(len(toks) - len(pwords) + 1):
            window = toks[i:i + len(pwords)]
            fuzzy = None                                  # (tok, start, end, phrase word)
            for (w, s, e), pw in zip(window, pwords):
                if w == pw:
                    continue
                if (fuzzy is None and len(w) >= 4 and len(pw) >= 4
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
            taken.append((s, e))
            edits.append((s, e, pw))
            notices.append(f"read '{w}' as '{pw}' ({' '.join(pwords)})")

    # 3 · single-word typo recognition — N2, the operator's ruling: sure hits fixed,
    #     ambiguity settled by the SIM CHECK (each candidate tried in place; the slot
    #     votes), ties or no fit left alone. Candidates come ONLY from our own closed
    #     sets — never the whole language, so a name can never be a candidate.
    taken2 = [(s_, e_) for s_, e_, _ in edits]
    for w, s_, e_ in toks:
        if len(w) < 4 or "'" in w:
            continue
        if any(not (e_ <= ts or te <= s_) for ts, te in taken2):
            continue
        got = _recognise(w, toks, s_, board)
        if got:
            taken2.append((s_, e_))
            edits.append((s_, e_, got))
            notices.append(f"read '{w}' as '{got}'")

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
    from .pass2 import merge_cut_points
    cuts = merge_cut_points(mid)
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
    known = (set(OBJECT_OPENERS) | set(GRAMMAR) | nouns | ops | marker_words
             | set(AUXILIARIES) | set(WH_WORDS) | set(PARTICLES)
             | set(_iso.FILLED_PAUSE) | {"vms", "vm's"})
    return OBJECT_OPENERS, nouns, ops, known


def _board():
    from planner.formula.legal import Board
    return Board()


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
    if w in known:
        return None
    words = [t[0] for t in toks]
    i = next(j for j, t in enumerate(toks) if t[1] == at)
    prev = words[i - 1] if i > 0 else None
    nxt = words[i + 1] if i + 1 < len(words) else None
    _PRONOUNS = {"it", "them", "me", "us", "one", "ones", "everything"}
    fits = set()
    for cand in openers | nouns | ops:
        if not _damerau1(w, cand) or len(cand) < 4 and cand not in _PRONOUNS:
            continue
        if cand in _PRONOUNS:
            if prev in ops:
                fits.add(cand)
        elif cand in openers:
            if nxt in nouns:
                fits.add(cand)
        elif cand in nouns:
            if prev in openers or (i >= 2 and words[i - 2] in openers):
                fits.add(cand)
        elif cand in ops:
            if i == 0 or prev in {"then", "and", "but"}:
                fits.add(cand)
    return fits.pop() if len(fits) == 1 else None


def _tokens(low: str):
    return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"[a-z']+", low)]


def _quoted(low: str):
    """Quoted regions are opaque. The lookarounds keep apostrophes (don't) out of it."""
    spans = [(m.start(), m.end())
             for m in re.finditer(r"(?<![a-z])'[^']*'(?![a-z])", low)]
    spans += [(m.start(), m.end()) for m in re.finditer(r'"[^"]*"', low)]
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
