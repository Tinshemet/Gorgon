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
    · single-word phrases — no context, no licence; fuzzy needs the phrase around it

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


def read(request: str) -> View:
    """One pass, at the entrance. Clean text returns the identity view."""
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

    if not edits:
        return View(text, list(range(len(text) + 1)), [], text)
    new, back = _apply(text, edits)
    return View(new, back, notices, text)


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
        back.extend([s] * len(rep))
        at = e
    out.append(text[at:])
    back.extend(range(at, len(text)))
    back.append(len(text))
    return "".join(out), back
