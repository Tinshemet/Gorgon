"""vectors.py — FULL VECTOR DECONSTRUCTION PER WORD: the gold's third layer (schema v3.0).

# ⇒⇒ THE RULING (operator, 2026-08-24)
*"decomp every single sentence to its based components and compute it as a vector (mood,
plurality, etc) … the final gold i have to grade would be not just each word and its vector
but the overall vector as well, so i can see if the verdict is right AND WHICH WORDS FLIP IT
THE WRONG WAY and figure out why, this is the final form of this READ: full vector
deconstruction per word."* And on scope: same 110 sentences — v4 IS v3, the gold deepened,
ONE grading pass.

# ⇒ DISCRETE, NEVER LEARNED. Every cell is a fact somebody DECLARED — a codex closed class,
#   a manifest attribute, a gold span — so a flipped cell is a RULING with an owner, never a
#   gradient. "Like real LLMs" in shape (per-word vectors + a fold), unlike them in licence.
# ⇒ COMPUTED, NEVER AUTHORED. The emitter fills every cell from the seam's REAL readers
#   (the codex, the manifest, names_an_attribute, act_of, clock_in, the code-only reading) —
#   a naive word-list tagger read `let's` as a genitive; the readers know better. The
#   operator certifies BY EXCEPTION: a flip in review is a per-cell reject, and the fix is
#   made where the cell was computed — then re-emitted, like any gold.
# ⇒ THE FOLD IS A FUNCTION OF THE CELLS, told to the operator 08-24: authored separately it
#   could disagree with its own words; graded, a fold flip rules the FOLD RULE, every case
#   with that shape at once.

The vector rides the case as an OPTIONAL key — a file without it (sealed v1/v2/v21) stays
valid and its verdict hashes stay warm. Where it IS present, review._hash binds it: the
seal covers everything judged (the 08-22 lesson).
"""
import re
from typing import Dict, List, Optional

from orchestrator.languages.english import codex as C
from orchestrator.languages.english.seam import speech_act as SA, temporal as T

# ── the declared dimensions — the schema the operator rules on ──────────────────────
# per WORD (sparse: absent = not this):
WORD_DIMENSIONS = (
    "class",   # closed-class tags, sorted: det:def/indef/univ · neg · aux · wh · prep:sel
               #   · clitic · contraction · proform:one/many · comparator · adj:sup
               #   · quant:card (`two`, qty carries the number) · quant:part (`half`)
               #   · adj:sup (superlative, ordinal) · adj:cmp (comparative, selector)
               #   · cue:name · sub · fallback · hedge · emph · excl · hort
    "wh",      # WHAT IS SOUGHT (the operator's cells): which→pick-member · what→meaning
               #   · who/whom→object-ref · whose→owner · why→reason · when→time
               #   · where→place · how→manner · how many→count · how much→amount
    "kind",    # the noun's declared kind, off the manifest index
    "num",     # one|many — surface number of a kind/proform word
    "attr",    # attribute word → its canonical name (ram→memory_mb)
    "state",   # a declared attribute VALUE or alias (up→status=running)
    "verb",    # the operations this word names, off the manifest (stop→stop_vm)
    "qty",     # a quantity token (8gb, 4) — step 1's licence
    "ident",   # an identifier: the declared shape it matches (ip·mac·serial) or `unshaped`
    "span",    # gold: which span holds this word + its role (s0:patient) — the certified
    "action",  # gold: which action holds it (a0, +q when the action is a query)
)
# per SENTENCE (the fold — computed FROM the words + the code-only reading):
FOLD_DIMENSIONS = (
    "act",     # speech act (act_of) — the producer's channel
    "shape",   # answer_shape: count · members · meaning · -
    "mood",    # DO | ACHIEVE (the mood channel's markers)
    "clock",   # instant | recurrence | -
    "neg",     # how many negation cells fired
    "reads",   # the code-only reading's channel census: i/q/t/r counts (instructs·queries
               #   ·triggers·rules+reports) — what the seam DID with it, model stubbed
    "words",   # token count
    "tone",    # v3.1 (operator 08-25): the emotional MOOD HINT READ produces for
               #   ROUTE/RESOLVE — bland · affirmation · deference · urgency · hedge · apology
    "priority",  # v3.1: the PACING hint — `deferrable` when a meta-control availability
                 #   marker is present (`when you have a sec`), else `normal`. For ROUTE.
)

from orchestrator.languages.english.codex import PARTIAL as _PARTIAL
from orchestrator.languages.english.codex import (AFFIRMATION as _AFFIRM, APOLOGY as _APOL,
                                                  EMPHATIC as _EMPH, HEDGES as _HEDGE)


def _mood_hint(sentence: str, words) -> str:
    """The overall mood READ hands ROUTE/RESOLVE. Closed-class markers, first match wins;
    nothing matched = bland (operator 08-25: 'if it has no pretexts its bland')."""
    toks = {w["w"].strip(".,;:!?'\"").lower() for w in words}
    low = str(sentence).lower()
    if toks & _APOL:
        return "apology"
    if "!!" in sentence or toks & _EMPH:
        return "urgency"
    if "please" in toks or "kindly" in toks:
        return "deference"
    if toks & _HEDGE:
        return "hedge"
    if toks & _AFFIRM:
        return "affirmation"
    return "bland"


_DEFER = ("when you have a sec", "when you have a second", "when you get a chance",
          "when you're free", "when youre free", "when you are free", "when you're done",
          "when youre done", "when you are done", "no rush", "no hurry", "whenever you can")


def _priority_hint(sentence: str) -> str:
    """`deferrable` when the turn defers to the AGENT's availability (a pacing meta-control
    on self — operator 08-25), else `normal`. A closed list of self-availability markers."""
    low = str(sentence).lower()
    return "deferrable" if any(m in low for m in _DEFER) else "normal"

_WH_SOUGHT = {"which": "pick-member", "what": "meaning", "who": "object-ref",
              "whom": "object-ref", "whose": "owner", "why": "reason", "when": "time",
              "where": "place", "how": "manner"}
_FALLBACK = frozenset({"otherwise", "else"})


def _maps(board):
    from orchestrator.languages.english.seam.scan import _index, _operation_words
    nouns = _index(board)
    states: Dict[str, str] = {}
    for kind, spec in (board.kinds or {}).items():
        for attr, vals in ((spec or {}).get("attr_values") or {}).items():
            for v in vals or ():
                states.setdefault(str(v).lower(), f"{attr}={v}")
        for attr, alias in ((spec or {}).get("value_aliases") or {}).items():
            for a, v in (alias or {}).items():
                states.setdefault(str(a).lower(), f"{attr}={v}")
    shapes = []
    for kind, spec in (board.kinds or {}).items():
        for attr, cls in ((spec or {}).get("attr_classes") or {}).items():
            if isinstance(cls, dict) and cls.get("shape"):
                shapes.append((attr, re.compile(str(cls["shape"]))))
    comparator_words = set()
    for phrase in list(C.COMPARATORS) + list(C.MAGNITUDE):
        comparator_words |= set(str(phrase).split())
    return nouns, states, shapes, _operation_words(board), comparator_words


_NUM_UNIT = re.compile(r"\d+(?:\.\d+)?[a-z]*$")


def _comparative(t: str, nxt: Optional[str]) -> bool:
    """The comparative FORM (`smaller`, `bigger`, `older`) — RELATIONAL, needs a reference,
    so it FILTERS (a selector), unlike the superlative which ranks-and-picks (ordinal).
    Morphology with the 3+ stem guard, plus more/less heading the next word."""
    t = t.strip(".,;:!?'\"").lower()
    # a closed list — English -er comparatives that appear in the lab domain; morphology
    # alone catches `prefer`/`rather`/`cluster`, so this is a WORD LIST not a suffix rule
    return t in ("more", "less", "smaller", "bigger", "larger", "older", "newer", "younger",
                 "faster", "slower", "higher", "lower", "greater", "fewer", "cheaper")


def _superlative(t: str, nxt: Optional[str]) -> bool:
    """The superlative FORM — a fact about the word, not the world (ledger #23: `oldest`
    is an attribute/adjective; WHICH attribute orders it is RESOLVE's question). Morphology
    with a guard: `-est` only over a stem of 3+ (`test`, `rest`, `west` never fire —
    `the test vms` is cap-0002), or `most`/`least` heading the next word."""
    if t in ("most", "least") and nxt:
        return True
    return t.endswith("est") and len(t) >= 6 and t[:-3].isalpha()


def word_cells(tok: str, nxt: Optional[str], case: dict, start: int, end: int,
               board, maps) -> Dict[str, object]:
    """Every cell one word earns. Sparse, deterministic, declared-facts only."""
    from orchestrator.languages.english.seam.pass1 import names_an_attribute
    nouns, states, shapes, opwords, compwords = maps
    raw = tok
    t = tok.strip(".,;:!?'\"").lower()
    low = tok.lower()
    cells: Dict[str, object] = {}
    tags: List[str] = []
    if t in C.DEFINITE: tags.append("det:def")
    if t in C.INDEFINITE: tags.append("det:indef")
    if t in C.UNIVERSAL: tags.append("det:univ")
    if t in C.NEGATION: tags.append("neg")
    if t in C.AUXILIARIES: tags.append("aux")
    if t in C.WH_WORDS: tags.append("wh")
    if t in C.SELECTOR_PREPOSITIONS: tags.append("prep:sel")
    if t in C.SUBORDINATING: tags.append("sub")
    if t in _FALLBACK: tags.append("fallback")
    if t in C.HEDGES: tags.append("hedge")
    if t in C.EMPHATIC: tags.append("emph")
    if t in C.SINGULAR_PROFORMS: tags.append("proform"); cells["num"] = "one"
    if t in C.PLURAL_PROFORMS: tags.append("proform"); cells["num"] = "many"
    if t in compwords: tags.append("comparator")
    if _superlative(t, nxt): tags.append("adj:sup")
    if _comparative(t, nxt): tags.append("adj:cmp")
    if t in C.NAMING_CUES: tags.append("cue:name")
    if low in C.CONTRACTIONS:
        tags.append("contraction")
        if C.CONTRACTIONS[low][0] == "let":
            tags.append("hort")
    else:
        bare = low.rstrip(".,;:!?\"")
        for cl in C.GENITIVE_CLITICS:
            if bare.endswith(cl) and len(bare) > len(cl):
                tags.append("clitic")
                break
    if tags:
        cells["class"] = sorted(set(tags))
    if t in C.WH_WORDS:
        if t == "how" and nxt in ("many", "much"):
            cells["wh"] = "count" if nxt == "many" else "amount"
        else:
            cells["wh"] = _WH_SOUGHT.get(t, t)
    stem = t[:-2] if "clitic" in tags and t.endswith("'s") else t
    if stem in nouns:
        cells["kind"] = nouns[stem]
        cells.setdefault("num", "many" if (stem.endswith("s") and stem[:-1] in nouns) else "one")
    a = names_an_attribute(stem, board)
    if a:
        cells["attr"] = a
    if t in states:
        cells["state"] = states[t]
    ops = SA._verb_ops(t, board)
    if ops:
        cells["verb"] = sorted(ops)
    if _NUM_UNIT.fullmatch(t) or t.isdigit():
        cells["qty"] = t
    elif t in C.ENUMERATORS and str(C.ENUMERATORS[t]).isdigit():
        cells["qty"] = str(C.ENUMERATORS[t])            # `two` -> 2, the closed cardinals
        tags.append("quant:card"); cells["class"] = sorted(set(tags))
    elif t in _PARTIAL:
        tags.append("quant:part"); cells["class"] = sorted(set(tags))
    matched = next((attr for attr, rx in shapes if rx.fullmatch(t)), None)
    if matched:
        cells["ident"] = matched
    elif (len(t) >= 3 and (re.search(r"\d", t) or re.search(r"[:\-_@/]", t))
          and "qty" not in cells
          and not any(p in opwords or p in C.GRAMMAR for p in re.split(r"[-:.]", t) if p)):
        cells["ident"] = "unshaped"
    g = case.get("gold") or {}
    for si, sp in enumerate(g.get("spans") or ()):
        if sp["start"] <= start < sp["end"]:
            role = next((o["role"] for at in g.get("attachments") or ()
                         for o in at["objects"] if isinstance(o, dict) and o["span"] == si),
                        None)
            cells["span"] = f"s{si}" + (f":{role}" if role else "")
    queries = set()
    for ai, act in enumerate(g.get("actions") or ()):
        if act.get("kind") == "query":
            queries.add(ai)
        if act["start"] <= start < act["end"]:
            cells["action"] = f"a{ai}" + ("+q" if act.get("kind") == "query" else "")
    return cells


def fold_cells(case: dict, words: List[dict], board) -> Dict[str, str]:
    """The sentence's vector — a function of the words and the code-only reading."""
    import engines.channel as channel
    from .runner import read_case
    s = case["sentence"]
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    try:
        r = read_case(s, board=board)
    finally:
        channel.constrained = was
    neg = sum(1 for w in words if "neg" in (w["cells"].get("class") or ()))
    return {
        "act": SA.act_of(s, board) or "-",
        "shape": SA.answer_shape(s, board) or "-",
        "mood": "ACHIEVE" if any(m in s.lower() for m in C.ACHIEVE_MARKERS) else "DO",
        "clock": T.clock_in(s) or "-",
        "neg": str(neg),
        "reads": (f"i{len(r['instructs'])}·q{len(r['queries'])}·t{len(r['triggers'])}"
                  f"·r{len(r['rules']) + len(r['reports'])}"),
        "words": str(len(words)),
        "tone": _mood_hint(s, words),
        "priority": _priority_hint(s),
    }


def vector_of(case: dict, board=None) -> Dict[str, object]:
    from planner.formula.legal import Board
    board = board or Board()
    maps = _maps(board)
    toks = list(re.finditer(r"\S+", case["sentence"]))
    words = []
    for i, m in enumerate(toks):
        nxt = toks[i + 1].group(0).strip(".,;:!?'\"").lower() if i + 1 < len(toks) else None
        cells = word_cells(m.group(0), nxt, case, m.start(), m.end(), board, maps)
        words.append({"w": m.group(0), "cells": cells})
    return {"v": 1, "words": words, "fold": fold_cells(case, words, board)}


def attach(cases: List[dict], board=None) -> List[dict]:
    """The emitter's step: every case gains its computed vector. Idempotent by content."""
    from planner.formula.legal import Board
    board = board or Board()
    for case in cases:
        case["vector"] = vector_of(case, board)
    return cases
