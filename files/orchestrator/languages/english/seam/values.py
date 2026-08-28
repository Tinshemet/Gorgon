"""values.py — ATTRIBUTES ARE LEAVES: an assigned value is its own span, and READ never reads it.

# ⇒⇒ THE RULING (operator, 2026-08-23 — [[gorgon-attributes-are-leaves]])
*"attributes are 'leaves' of the class world — meaningless technically to the AI … READ only
needs to understand that this is a 'learned' word that it's looking for in which context: if
a word appears in the correct context READ spans it, and if there is a conflict it gives it to
ROUTE for ASK with the hint 'X creates a conflict between ClassX and ClassY'."* · *"the unit
alone spans it if the class owns that unit."* · *"context and fit are both needed — if they
are the same it's a tie; if something is MORE correct we use the more correct one."*

So this file does FOUR things and refuses a fifth:
  1 FIND   a number + a learned UNIT or ATTRIBUTE word (`16gb`, `4 cores`, `8 gigs`), and
           the attribute word that may follow it (`8gb OF ram`) — from `archive.learned`,
           which serves the manifest's attr_classes and the told words through one lookup
  2 RANK   the word's owners by context (a row of that class — or a class inheriting from
           it — in the same clause) + fit (the class declares this unit / the linked
           attribute agrees). The best wins; a TIE is a conflict, carried on the row with
           its hint — READ does not pick
  3 PLACE  every value a class owns is its own VALUE_KIND row, lifted OUT of whatever
           phrase swallowed it (`the db vm 16gb` -> `the db vm` + `16gb`; `a vm with 4` ->
           `a vm` + `4 cores`). One that sits INSIDE an existing phrase behind a
           SELECTOR_PREPOSITION is a SELECTOR (`the vm at ▸10.0.0.5`, `every vm with over
           ▸6gb of ram`): it picks the thing rather than being given to it — the phrase keeps
           the filter in `where` (unless a comparator governs it, which `magnitudes_in`
           carries), and the span is the value's own. RULED 08-23: *"wouldn't this make
           sense that 10.0.0.5 is a different span since it's an attribute?"* — one rule.
  4 CLEAN  a kindless row that is the value itself or its attribute word (`8gb`, `ram`,
           `the cpu`) is not a thing — it is consumed by the value that explains it
  5 ASSIGN (step 3, 08-23) the value to its TARGET — the owner-class row in the clause.
           The owner scrutinises the bytes (`Board.accept`, read off `attr_classes`): a NEW
           target takes the accepted value into `where`, which is what its creator reads
           (`create a vm with 4 cores and 8gb of ram` -> create_vm cpu_cores=4 memory_mb=8192);
           an EXISTING target takes it only if the manifest declares a SETTER for that
           attribute — otherwise the value is REFUSED with the owner's reason, and gate 4
           tells the operator, never the model ([[gorgon-can-the-world-satisfy-it]])
  6 NAME   (step 4, ledger #17 — A NAME IS A LEAF) a naming cue on a NEW thing — `a vm
           NAMED alpha`, `two networks CALLED front and back` — makes the name(s) after it
           value rows of the thing's KEY attribute (`name` · `net_name`). A literal list is
           one leaf per name (a · b · c); a GENERATOR spec (`1-5`, `after musicians`) is
           itself the one leaf the owner runs (#11: one generative unit). A name on an
           EXISTING thing refers (`stop the vm named web`) and stays in its phrase.
  7 SHAPE  (step 5) a token matching a declared class's `shape` — an ip, a mac, a serial —
           is a value of that attribute wherever it stands: a selector behind `at`/`with`
           (the walk had cut `10.0.0.5` at the first `.`), a PREDICATE value in a question
           (`which vm has mac …` — its own span, nothing assigned, nothing refused), or
           assigned like any value (`give the web vm the ip …`).
  8 POSSESS (ledger #19, 08-23) a GENITIVE — `alpha'S snapshots`, `the web vm'S disk`,
           `the vmS' labels` — is owner + leaf, the relation `the cpu OF X` states with `of`.
           The leaf is its own VALUE row, lifted out of the phrase; the owner keeps the
           phrase minus the clitic and is re-typed by ITS head (`alpha` is not a
           `snapshot_set`). The grammar names the owner, so nothing is ranked — the only
           question is FIT, asked of the world in the settle order: a declared attribute or
           alias of the owner's kind (`alpha's ram`) · a taught word · a KIND whose attrs or
           refs name the owner's kind (`snapshot.vm` — so a vm owns `snapshots`: a declared
           fact read backwards, not an inference) · else an UNKNOWN leaf, still spanned (the
           slot decides) and REFUSED by the owner at ASSIGN, which gate 4 tells the operator
           — `beta has no 'disk'`. A leaf REFERS; it is never assigned, so no setter is
           needed. NOT read here: the copula contraction (`alpha's running` — `running` is a
           declared VALUE, so the split is refused) · possessive pronouns (proforms).
  9 SELECT-UNSHAPED (ledger #20, 08-23) a token in the SELECTOR SLOT of an existing
           phrase — `the vm at ▸8g:77q` — is an attribute value even when no class declares
           its shape. The operator, rejecting id-0005: *"8g:77q is an attribute the same way
           an ip is, so it should be treated the same."* READ spans it exactly as it spans an
           ip; the owner's scrutiny at ASSIGN is what differs — an attribute nobody declares
           is REFUSED, and gate 4 asks the operator which attribute it is (never a BOUNCE to
           the model, which cannot know). Overturns #17b's "stays in the phrase" clause.
           Only an identifier SHAPE (a digit or a separator in the token) claims the
           slot — a bare word may be a NAME (`on lab`, ba-0001) and stays in the phrase.
           Guarded: a declared shape (7's) · a quantity (1's) · English (cc-0007) · a clock
           (`at 21:30` — temporal's, already cut from the phrase) · a state · a thing (the
           vms ON THE LAB NETWORK, ba-0001) · an attribute word (`with SERIAL …`, context).
  ✗ NEVER  interpret the value HERE. The span stays the bytes `16gb`; the number 16384 is
           the owner's answer, recorded beside it, never in its place.

# ⇒ WHY A POST-PASS OVER ROWS, NOT A CHANGE TO THE NOUN-PHRASE WALK
The walk is the most-measured code in the seam (293/293 readings rebuilt byte-exact from
slots). Lifting a value out AFTER the walk is subtractive on the phrase and additive on the
table, and `capture.py` can price it to the case: the four units cases move, nothing else may.
"""
import re
from typing import Dict, List, Optional, Tuple

from . import schema as S
from ..codex import (ATTRIBUTE_LINKERS, CONTRACTIONS, CUT_DETERMINERS, DEFINITE,
                     GENITIVE_CLITICS, INDEFINITE, NAMING_CUES, NUMERAL_WORDS,
                     SELECTOR_PREPOSITIONS, VALUE_CONNECTORS)

# ⇒ a quantity is a DIGIT or a spelled-out NUMBER-WORD before a learned unit — `6gb`, `4 cores`,
#   AND `six gigabytes`, `four cores` (08-28). Was `\d+` only, so a worded magnitude scattered
#   and RESOLVE never saw a value to convert. Number-words from the codex SSOT, longest-first so
#   `seventeen` wins over `seven`. The `_learned` guard (group 2 must be a real unit) keeps
#   `six vms` from ever reading as a magnitude. (Compound `six thousand mb` still needs multi-
#   word number parsing — a separate, deeper fix.)
_NUM = r"\d+|" + "|".join(sorted(NUMERAL_WORDS, key=len, reverse=True))
_NUMBER_UNIT = re.compile(r"\b(%s)\s*([a-z]+)\b" % _NUM)
_DETS = set(DEFINITE) | set(INDEFINITE)          # the codex's, not a list of our own


def _learned(word: str, board, archive) -> list:
    return archive.learned(word, board)


def _attribute_named(word: str, board) -> Optional[str]:
    from .pass1 import names_an_attribute
    return names_an_attribute(word, board)


def _candidates(request: str, board, archive) -> List[dict]:
    """Every number + learned word in the request, with the attribute word that follows."""
    low = str(request).lower()
    out: List[dict] = []
    for m in _NUMBER_UNIT.finditer(low):
        word = m.group(2)
        entries = [e for e in _learned(word, board, archive)
                   if e.type in ("unit", "attribute") and e.owners]
        if not entries:
            continue
        start, end = m.start(), m.end()
        # a quantity is a WHOLE token: `8g` inside `8g:77q` is an identifier's piece, not
        # eight gigabytes (id-0005, the decoy no class owns — 08-23)
        if (start > 0 and low[start - 1] in ":-/_@.") or (end < len(low) and low[end] in ":-/_@"):
            continue
        # the attribute word that names which attribute a bare unit belongs to: `8gb OF ram`
        linked = None
        tail = re.match(r"\s+(%s)\s+(?:the\s+)?([a-z_]+)" % "|".join(ATTRIBUTE_LINKERS),
                        low[end:])
        if tail:
            linked = _attribute_named(tail.group(2), board)
        out.append({"text": request[start:end], "start": start, "end": end, "word": word,
                    "entries": entries, "linked": linked,
                    "linked_text": request[end:end + tail.end()] if tail and linked else ""})
    return out


_CUE = re.compile(r"\b(%s)(?:\s+as)?\b" % "|".join(sorted(NAMING_CUES, key=len, reverse=True)))
_RANGE = re.compile(r"^\d+\s*-\s*\d+$")
_BARE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")


def _stop_words(board) -> set:
    """The English the seam already knows — a name is never one of these words, so the
    first one AFTER the spec's head ends the spec: `dmz ▸ instead`, `core ▸ , except db`.
    The head itself is exempt: `named AFTER musicians`, `called THE stadium`."""
    from .scan import GRAMMAR, _operation_words
    from ..codex import EXCLUDERS, RELATIONAL_WORDS
    return (set(GRAMMAR) | set(RELATIONAL_WORDS) | set(EXCLUDERS) | set(CUT_DETERMINERS)
            | set(_DETS) | set(NAMING_CUES) | set(SELECTOR_PREPOSITIONS)
            | set(_operation_words(board)) | {"then", "but", "as"})


def _name_spec(low: str, at: int, board) -> Tuple[int, int]:
    """The naming spec after a cue at `at`: word by word until the clause ends or a word
    the codex knows appears — and across `,`/`and` only onto another bare name (`a, b AND
    c` goes on; `core, EXCEPT db`, `alpha AND launch it`, `musicians AND A network` stop)."""
    from .pass2 import CLAUSE_MARKS
    stop = _stop_words(board)
    marks = set(CLAUSE_MARKS) - {","}
    i, n = at, len(low)
    while i < n and low[i] in " ,":                 # a comma the front door may have restored
        i += 1
    start = i
    end = start
    first = True
    while i < n:
        if low[i] in marks:
            break
        if low[i] in " ,":
            m = re.match(r"[ ,]*(?:(and)\s+)?(\S+)", low[i:])
            if not m:
                break
            nxt = m.group(2).strip(".,'\"")
            sep = m.group(1) or "," in low[i:i + m.start(2)]
            if sep and (nxt in stop or not _BARE.match(nxt)):
                break
            if not sep and nxt in stop:
                break
            i += m.start(2)
            first = False
            continue
        m = re.match(r"\S+", low[i:])
        tok = m.group(0).strip(".,'\"")
        if not first and tok in stop:
            break
        end = i + len(m.group(0).rstrip(".,'\""))
        i += len(m.group(0))
        first = False
    text = low[start:end].rstrip(" ,")
    return start, start + len(text)


def _pieces(spec: str) -> List[Tuple[int, str]]:
    """(offset, text) per name — a LITERAL list splits on `,` and `and`; anything else
    (a range, a theme, a phrase) is one piece: the spec is the leaf."""
    seps = list(re.finditer(r"\s*(?:,|\band\b)\s*", spec))
    parts, at = [], 0
    for m in seps:
        parts.append((at, spec[at:m.start()]))
        at = m.end()
    parts.append((at, spec[at:]))
    out = []
    for off, text in parts:
        lead = len(text) - len(text.lstrip())
        if text.strip():
            out.append((off + lead, text.strip()))

    def literal(t: str) -> bool:
        w = t.split()
        if len(w) > 1 and w[0] in _DETS:            # `the stadium`; a bare `a` IS a name
            w = w[1:]
        return len(w) == 1 and bool(_BARE.match(w[0])) and not _RANGE.match(w[0])
    if out and all(literal(t) for _o, t in out):
        return out
    lead = len(spec) - len(spec.lstrip())
    return [(lead, spec.strip())]


def _creator_verbs(board) -> set:
    """The verbs the manifest's creators are named by — `create`, `clone` — read, never listed."""
    from ..codex import NON_VERB_SEGMENTS
    out = set()
    for spec in (board.kinds or {}).values():
        for c in ((spec or {}).get("creators") or {}).values():
            for seg in str((c or {}).get("tool") or "").lower().split("_"):
                if seg and seg not in NON_VERB_SEGMENTS:
                    out.add(seg)
    return out


def _created_here(row: S.Declared, request: str, board) -> bool:
    """THE VERB DECIDES: a phrase governed by a creator verb is NEW whatever the existence
    question answered — `create two networks called front and back` has no determiner, so
    existence was ASKED (85%, the model's weakest field) and a stub or a wobble says
    EXISTING. The verb already said."""
    from .scan import clause_around
    try:
        clause = str(clause_around(request, str(row.span or row.name))).lower()
    except Exception:
        return False
    words = [w.strip(".,'\"") for w in clause.split()]
    verbs = _creator_verbs(board)
    return any(w in verbs for w in words[:3])


def _naming_candidates(rows: List[S.Declared], request: str, board) -> List[dict]:
    """Every name a NEW thing is given — one candidate per leaf (rule 6)."""
    from planner.gates import claims as _claims
    low = str(request).lower()
    out: List[dict] = []
    things = [r for r in rows if r.object_type != S.VALUE_KIND]
    for m in _CUE.finditer(low):
        cue_s, cue_e = m.start(), m.end()
        # the thing this cue names: the row whose phrase holds the cue, else the nearest before
        holder = None
        for r in things:
            span = str(r.span or r.name).lower()
            at = low.find(span)
            if at >= 0 and at <= cue_s < at + len(span) + 1:
                holder = r
        if holder is None:
            before = [r for r in things if 0 <= low.find(str(r.span or r.name).lower()) < cue_s]
            holder = before[-1] if before else None
        if holder is None or not (holder.existence == S.NEW
                                  or _created_here(holder, request, board)):
            continue                                  # a name that REFERS stays (selector)
        spec_s, spec_e = _name_spec(low, cue_e, board)
        if spec_e <= spec_s:
            continue
        kind = holder.kind if holder.kind in board.kinds else None
        attribute = (_claims.key_of(kind, board.kinds) if kind else None) or "name"
        for off, text in _pieces(low[spec_s:spec_e]):
            start = spec_s + off
            out.append({"text": request[start:start + len(text)], "start": start,
                        "end": start + len(text), "word": m.group(1), "entries": [],
                        "linked": attribute, "linked_text": request[cue_s:cue_e],
                        "naming": True, "owner": kind or "?", "attribute": attribute,
                        "target_span": holder.span})
    return out


def _shape_candidates(request: str, board, archive) -> List[dict]:
    """Every token that fully matches a declared class's `shape` — rule 7."""
    low = str(request).lower()
    shapes = []
    for kind, spec in (board.kinds or {}).items():
        for attr, cls in ((spec or {}).get("attr_classes") or {}).items():
            if isinstance(cls, dict) and cls.get("shape"):
                shapes.append((kind, attr, re.compile(str(cls["shape"]))))
    out: List[dict] = []
    stop = _stop_words(board) if shapes else set()
    for m in re.finditer(r"\S+", low):
        tok = m.group(0).rstrip("?.,;:!'\"")
        if not tok or len(tok) < 3:
            continue
        # an identifier is never made of English: `read-only` fits the serial shape
        # (xxxx-xxxx) and is two words the codex knows (cc-0007, 08-23)
        if any(piece in stop for piece in re.split(r"[-:.]", tok) if piece):
            continue
        for kind, attr, rx in shapes:
            if not rx.fullmatch(tok):
                continue
            start, end = m.start(), m.start() + len(tok)
            entries = [e for e in _learned(attr, board, archive) if e.attribute == attr and e.owners]
            # the attribute word before it — `mac aa:…`, `the ip 10…`, `serial 7f3k-…` — is
            # context, and is claimed by the value (gate 1)
            linked_text = ""
            before = re.search(r"(?:(?:the|its|their|a)\s+)?([a-z_]+)\s+$", low[:start])
            if before and _attribute_named(before.group(1), board) == attr:
                linked_text = request[before.start():start].strip()
            out.append({"text": request[start:end], "start": start, "end": end, "word": attr,
                        "entries": entries, "linked": attr, "linked_text": linked_text,
                        "shaped": True, "owner": kind, "attribute": attr})
            break
    return out


_HAVE_FRAME = re.compile(
    r"\bhow (?:many|much)\s+(?P<leaf>\w+)\s+(?:does|do|did)\s+(?P<owner>\w+)\s+have\b")


def _have_frame_candidates(rows: List[S.Declared], request: str, board,
                           archive) -> List[dict]:
    """Rule 10 (ledger #21): `how many snapshots does alpha have?` is `alpha's snapshots`
    ASKED — the genitive with its owner named later. The same split by the same machinery:
    the wh-headed holder row becomes the leaf VALUE (bare, #21/#23), the owner stands as
    its own row, the COUNT stays the produced answer. The reading marks nothing set —
    a genitive leaf refers (id-0002's predicate convention holds one frame over)."""
    low = str(request).lower()
    out: List[dict] = []
    m = _HAVE_FRAME.search(low)
    if not m:
        return out
    leaf, owner_text = m.group("leaf"), m.group("owner")
    holder = next((r for r in rows if r.object_type != S.VALUE_KIND
                   and leaf in str(r.span or r.name).lower().split()), None)
    if holder is None:
        return out
    attribute, owner, of_kind = _leaf_fit([leaf], None, board, archive)
    start = m.start("leaf")
    out.append({"text": request[start:start + len(leaf)], "start": start,
                "end": start + len(leaf), "word": leaf, "entries": [],
                "linked": attribute, "linked_text": "", "genitive": True,
                "owner": owner or "?", "attribute": attribute, "of_kind": of_kind,
                "owner_text": request[m.start("owner"):m.end("owner")],
                "owner_type": S.UNKNOWN_KIND, "holder_span": str(holder.span or holder.name),
                "frame": (m.start(), m.end()),
                "target_span": request[m.start("owner"):m.end("owner")]})
    return out


def _unshaped_selector_candidates(rows: List[S.Declared], request: str, board,
                                  archive) -> List[dict]:
    """Rule 9 — the slot, not the shape, is the licence; the world answers at ASSIGN."""
    from .scan import _index
    from .temporal import clock_in
    low = str(request).lower()
    shapes = [re.compile(str(cls["shape"])) for spec in (board.kinds or {}).values()
              for cls in ((spec or {}).get("attr_classes") or {}).values()
              if isinstance(cls, dict) and cls.get("shape")]
    stop = _stop_words(board) | _dangling(board)     # `more than`, `over` — a comparator
    states = _declared_values(board)                 #   heads the value, it never IS one
    nouns = _index(board)
    preps = "|".join(sorted(SELECTOR_PREPOSITIONS, key=len, reverse=True))
    out: List[dict] = []
    for r in rows:
        if r.object_type == S.VALUE_KIND or r.existence != S.EXISTING:
            continue
        span = str(r.span or r.name)
        at = low.find(span.lower())
        if at < 0:
            continue
        for m in re.finditer(r"\b(%s)\s+(\S+)" % preps, span.lower()):
            tok = m.group(2).rstrip("?.,;:!'\"")
            if not tok or len(tok) < 3:
                continue
            if not (re.search(r"\d", tok) or re.search(r"[:\-_@./]", tok)):
                continue                        # a BARE WORD may be a NAME (`on lab`, ba-0001)
                                                #   — only an identifier SHAPE claims the slot
            if any(p in stop for p in re.split(r"[-:.]", tok) if p):
                continue                        # an identifier is never made of English
            if tok in states or tok in nouns or _attribute_named(tok, board):
                continue                        # a state, a thing, or the attribute WORD
            if any(rx.fullmatch(tok) for rx in shapes):
                continue                        # a declared shape — step 7 owns it
            if _NUMBER_UNIT.fullmatch(tok) or tok.replace(".", "").isdigit():
                continue                        # a quantity — step 1 owns it
            if clock_in(m.group(0)):
                continue                        # a time is the trigger's, not a selector
            start = at + m.start(2)
            out.append({"text": request[start:start + len(tok)], "start": start,
                        "end": start + len(tok), "word": tok, "entries": [],
                        "linked": None, "linked_text": "", "unshaped": True,
                        "owner": r.kind if r.kind in board.kinds else "?",
                        "attribute": None})
            break
    return out


def _superlative_word(t: str) -> bool:
    """The superlative FORM (ledger #23) — morphology with the 3+ stem guard (`test` is
    English), plus most/least. Mirrors vectors.py's cell; one rule, said twice is a bug."""
    t = t.strip(".,;:!?'\"").lower()
    return t in ("most", "least") or (t.endswith("est") and len(t) >= 6 and t[:-3].isalpha())


def _of_genitive_candidates(rows: List[S.Declared], request: str, board,
                            archive) -> List[dict]:
    """Rule 8's OF spelling (ledger #23): `the oldest snapshot OF alpha` is `alpha's oldest
    snapshot` — the leaf span is the BARE head (`snapshot`), the adjectives stay OUTSIDE
    the span and ride as ORDERING context (`oldest`), and the owner is the row after `of`.
    Fires only when the holder's head names a KIND (an attribute head — `the cpu of X` —
    is step 1/4's; a quantifier head — `two of the vms` — is the partitive, structural)."""
    from .scan import _index, _kind_of
    low = str(request).lower()
    nouns = _index(board)
    out: List[dict] = []
    for r in rows:
        if r.object_type == S.VALUE_KIND:
            continue
        span = str(r.span or r.name)
        at = low.find(span.lower())
        if at < 0:
            continue
        words = span.split()
        head = words[-1].strip(".,;:!?'\"").lower()
        if head not in nouns or _attribute_named(head, board):
            continue                                # a kind head only
        m = re.match(r"\s+of\s+(\S+)", low[at + len(span):])
        if not m:
            continue
        owner_text = m.group(1).strip(".,;:!?'\"")
        owner = next((o for o in rows if o is not r and o.object_type != S.VALUE_KIND
                      and str(o.span or o.name).lower() == owner_text), None)
        if owner is None:
            continue                                # the owner must be a thing the walk read
        owner_kind = owner.kind if owner.kind in board.kinds else None
        attribute, owner_cls, of_kind = _leaf_fit([head], owner_kind, board, archive)
        head_at = at + span.lower().rfind(head)
        ordering = next((w.strip(".,;:!?'\"").lower() for w in words
                         if _superlative_word(w)), None)
        out.append({"text": request[head_at:head_at + len(head)], "start": head_at,
                    "end": head_at + len(head), "word": head, "entries": [],
                    "linked": attribute, "linked_text": "", "genitive": True, "of": True,
                    "owner": owner_cls or "?", "attribute": attribute, "of_kind": of_kind,
                    "owner_text": str(owner.span or owner.name), "owner_type": None,
                    "holder_span": span, "ordering": ordering,
                    "target_span": str(owner.span or owner.name)})
    return out


_CLITICS = "|".join(re.escape(c) for c in sorted(GENITIVE_CLITICS, key=len, reverse=True))
_GENITIVE = re.compile(r"^(?P<owner>.+?)(?P<clitic>%s)(?:\s+(?P<leaf>\S.*))?$" % _CLITICS)


def _declared_values(board) -> set:
    """Every declared attribute VALUE and its aliases (`running`, `up`) — a word that can only
    be a STATE, never a leaf. `alpha's running` is the copula, not a possessive."""
    out: set = set()
    for spec in (board.kinds or {}).values():
        for vals in ((spec or {}).get("attr_values") or {}).values():
            out |= {str(v).lower() for v in (vals or ())}
        for aliases in ((spec or {}).get("value_aliases") or {}).values():
            out |= {str(a).lower() for a in (aliases or {})}
    return out


def _kinds_owned_by(owner: str, board) -> List[str]:
    """The kinds that declare a reference to `owner` — `snapshot.attrs` holds `vm`,
    `network.refs.members -> vm`. Read off the manifest, never listed."""
    out: List[str] = []
    for kind, spec in (board.kinds or {}).items():
        spec = spec or {}
        attrs = {str(a).lower() for a in (spec.get("attrs") or ())}
        refs = {str(v).lower() for v in (spec.get("refs") or {}).values()}
        if owner in attrs or owner in refs:
            out.append(kind)
    return out


def _leaf_fit(leaf_words: List[str], owner_kind: Optional[str], board,
              archive) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """(attribute, owner, of_kind) for a genitive leaf, in the settle order — or three Nones
    when nobody declares it. `owner` is the kind that owns the leaf: the owner phrase's own
    kind when it has one, else the kind the leaf's declaration names (the leaf decides what
    a bare name is, as the verb decides the noun)."""
    from .scan import _index, _kind_of
    head = leaf_words[-1].strip(".,;:!?'\"")
    # 1 · 2  a declared attribute/alias, or a taught word, of the owner's kind
    attr = _attribute_named(head, board)
    entries = [e for e in _learned(head, board, archive) if e.owners]
    owners = sorted({o for e in entries for o in e.owners})
    if attr or entries:
        attribute = attr or next((e.attribute for e in entries if e.attribute), None) or head
        if owner_kind and (owner_kind in owners or attr in (board._spec(owner_kind).get("attrs")
                                                             or ()) or attr in (
                                                                 board._spec(owner_kind).get("aliases") or {})):
            return attribute, owner_kind, None
        if owner_kind and owner_kind in board.kinds:
            return attribute, owner_kind, None         # the owner scrutinises at ASSIGN
        if owners:
            return attribute, owners[0], None
        return attribute, owner_kind, None
    # 3  a kind that declares a reference to the owner: the owner HAS those
    leaf_kind = _kind_of(leaf_words, _index(board))
    if leaf_kind:
        for owner in ([owner_kind] if owner_kind in board.kinds else list(board.kinds)):
            if leaf_kind in _kinds_owned_by(owner, board):
                return leaf_kind, owner, leaf_kind
    return None, owner_kind if owner_kind in board.kinds else None, None


def _genitive_candidates(rows: List[S.Declared], request: str, board,
                         archive) -> List[dict]:
    """Every `OWNER's LEAF` inside a declared phrase — rule 8. The clitic is read only INSIDE
    a row the walk declared, so `let's stop alpha` and `it's hot` are never split."""
    from .scan import _index, _kind_of
    low = str(request).lower()
    states = _declared_values(board)
    out: List[dict] = []
    for r in rows:
        if r.object_type == S.VALUE_KIND:
            continue
        span = str(r.span or r.name)
        m = _GENITIVE.match(span.lower())
        if not m:
            continue
        owner_text = m.group("owner")
        if m.group("clitic") == "s'":
            owner_text += "s"                           # `the vms'` — the s is the noun's
        owner_words = owner_text.split()
        at = low.find(span.lower())
        if at < 0 or not owner_words:
            continue
        # ⇒ D8's bare-name arm reaches the genitive too (08-25, po-0003): `SNAPSHOT beta's
        #   disk` — a clause-initial operation word heading the owner is the VERB, never
        #   the owner's first name. One word, clause start only.
        if len(owner_words) > 1 and at == 0:
            from .scan import _index as _idx, _operation_words
            head = owner_words[0].strip(".,;:!?'\"").lower()
            from .speech_act import _verb_ops as _ops
            if ((head in _operation_words(board) or _ops(head, board))
                    and owner_words[1] not in _idx(board)):
                owner_words = owner_words[1:]
                owner_text = " ".join(owner_words)     # the leaf offsets and the holder
                                                       #   span stay on the ORIGINAL bytes
        if m.group("leaf"):
            leaf_at, leaf_end = at + m.start("leaf"), at + m.end("leaf")
        else:
            # the walk cut at the apostrophe (`the vms'` | `labels`): the leaf is the row that
            # starts right after, else the words that do, up to the first word the seam knows
            after = at + len(span)
            nxt = next((o for o in rows if o is not r and o.object_type != S.VALUE_KIND
                        and low.find(str(o.span or o.name).lower()) == after + 1), None)
            if nxt is not None:
                leaf_at, leaf_end = after + 1, after + 1 + len(str(nxt.span or nxt.name))
            else:
                tail = re.match(r"\s+(\S+)", low[after:])
                if not tail:
                    continue
                leaf_at, leaf_end = after + tail.start(1), after + tail.end(1)
        leaf_words = low[leaf_at:leaf_end].split()
        if not leaf_words:
            continue
        if (owner_words[-1] + m.group("clitic") in CONTRACTIONS
                or owner_words[-1] in _stop_words(board) or owner_words[-1] in S.PRONOUNS):
            continue                                    # `let's`, `it's`, `that's` — the codex's
        if leaf_words[0].strip(".,;:!?'\"") in states:
            continue                                    # `alpha's running` — the copula
        owner_kind = _kind_of(owner_words, _index(board))
        plural = m.group("clitic") == "s'"
        attribute, owner, of_kind = _leaf_fit(leaf_words, owner_kind, board, archive)
        owner_type = ((owner_kind + (S.SET_SUFFIX if plural else "")) if owner_kind
                      else S.UNKNOWN_KIND)
        out.append({"text": request[leaf_at:leaf_end], "start": leaf_at, "end": leaf_end,
                    "word": leaf_words[-1].strip(".,;:!?'\""), "entries": [],
                    "linked": attribute, "linked_text": "", "genitive": True,
                    "owner": owner or "?", "attribute": attribute, "of_kind": of_kind,
                    "owner_text": request[at:at + len(owner_text)], "owner_type": owner_type,
                    "holder_span": span, "target_span": request[at:at + len(owner_text)]})
    return out


def _comparator_before(request: str, at: int) -> Optional[str]:
    """The MAGNITUDE phrase right before a value (`over`, `more than`) — a comparison
    `where` cannot hold; `magnitudes_in` carries it. Named here so the value row says so."""
    from ..codex import MAGNITUDE
    head = str(request).lower()[:at].rstrip()
    for phrase in sorted(MAGNITUDE, key=len, reverse=True):
        if head.endswith(phrase):
            return phrase
    return None


def _is_predicate(v: S.Declared, request: str) -> bool:
    """A value in a QUESTION or a statement of fact is a predicate's value, not an
    assignment — `which vm has mac …`, `alpha has ip …`: nothing to take, nothing to refuse."""
    from .speech_act import AUXILIARIES, WH_WORDS
    clause = _clause_of(request, v.span)
    words = [w.strip(".,'\"?") for w in clause.split()]
    return bool(words) and (words[0] in WH_WORDS or words[0] in AUXILIARIES)


def _clause_of(request: str, text: str) -> str:
    from .scan import clause_around
    try:
        return str(clause_around(request, text)).lower()
    except Exception:
        return str(request).lower()


def _inherits(kind: str, owner: str, archive) -> bool:
    kind, owner = str(kind or "").lower(), str(owner or "").lower()
    return bool(kind) and (kind == owner or owner in archive.ancestors(kind))


def rank_owners(cand: dict, rows: List[S.Declared], request: str, archive) -> Dict[str, int]:
    """owner -> score. Context: a row of that class (or a child) in the clause. Fit: the
    entry is a UNIT of a class that declares it, or the linked attribute word agrees."""
    clause = _clause_of(request, cand["text"])
    here = [r for r in rows if r.object_type not in (S.VALUE_KIND,)
            and str(r.span or r.name).lower() in clause]
    scores: Dict[str, int] = {}
    for e in cand["entries"]:
        for owner in e.owners:
            context = 1 if any(_inherits(r.kind, owner, archive) for r in here) else 0
            fit = 1 if e.type == "unit" else 0
            if cand["linked"] and e.attribute == cand["linked"]:
                fit += 1
            scores[owner] = max(scores.get(owner, 0), context + fit)
    return scores


def _selects(cand: dict, rows: List[S.Declared], request: str) -> bool:
    """Is this value INSIDE an existing phrase, behind a selector preposition? Then it
    restricts the thing and is not ours to lift."""
    low = str(request).lower()
    for r in rows:
        if r.object_type == S.VALUE_KIND or r.existence != S.EXISTING:
            continue
        span = str(r.span or "").lower()
        at = low.find(span)
        # the phrase may have swallowed only the NUMBER (`the vms with more than 2`) — the
        # value STARTS inside it, and that is the test; full containment would miss mg-0002
        if at < 0 or not (at <= cand["start"] < at + len(span)):
            continue
        between = low[at:cand["start"]].split()
        if any(w.strip(".,'\"") in SELECTOR_PREPOSITIONS for w in between):
            return True
    return False


def _dangling(board) -> set:
    """What a lifted value leaves hanging at a phrase's edge and takes with it: a connector
    or preposition (`with`, `at`, `of`), a naming cue (`named`), a comparator word (`over`,
    `more than`). An attribute word (`serial`, `ram`) is tested separately, by name."""
    from ..codex import MAGNITUDE
    out = set(VALUE_CONNECTORS) | set(NAMING_CUES) | set(SELECTOR_PREPOSITIONS) | {"as"}
    for phrase in MAGNITUDE:
        out |= set(str(phrase).split())
    return out


def _lift(row: S.Declared, cand: dict, request: str, board) -> Optional[S.Declared]:
    """The row with the value cut out of its phrase; None if nothing is left of it."""
    low = str(request).lower()
    span = str(row.span or "")
    if cand.get("frame"):
        # rule 10: the have-frame owns its whole question — a row inside it is the frame's
        # skin (`does alpha` · `have`), never a thing; the OWNER's own row stays
        fs, fe = cand["frame"]
        at0 = low.find(span.lower())
        if (at0 >= 0 and fs <= at0 and at0 + len(span) <= fe
                and span.lower() != str(cand["owner_text"]).lower()
                and span != cand.get("holder_span")):
            return None
    if cand.get("of") and cand.get("holder_span") == span:
        return None       # rule 8-of: `the oldest snapshot` IS the leaf — the value row
                          #   replaces it, and `alpha` already stands as its own row
    if cand.get("genitive") and cand.get("holder_span") == span:
        # rule 8: the phrase that held `OWNER's LEAF` becomes the OWNER, typed by its head
        new = str(cand["owner_text"])
        return S.declare_from(new, cand["owner_type"], dict(row.where or {}), row.existence,
                              board, references=list(row.references), count=row.count,
                              comparator=row.comparator, span=new, identity=row.identity,
                              sanctioned=row.sanctioned)._replace(
                                  excludes=row.excludes, unroutable=row.unroutable,
                                  mentions=row.mentions, assigned=row.assigned)
    at = low.find(span.lower())
    if at < 0:
        return row
    s0, e0 = at, at + len(span)
    if cand["end"] <= s0:
        return row                                  # the value is before this phrase
    if cand["start"] >= e0:
        # the value sits right AFTER the phrase: only a dangling cue/connector at the
        # phrase's end belongs to the value (`3 vms named ▸ after musicians`)
        gap = low[e0:cand["start"]].strip(" ,")
        if gap:
            return row                              # something else stands between
        words = span.split()
        dangling = _dangling(board)
        while words and (words[-1].strip(".,'\"").lower() in dangling
                         or _attribute_named(words[-1].strip(".,'\""), board)):
            words.pop()
        new = " ".join(words).strip(" ,")
        if not new or new == span or all(w.lower() in _DETS for w in new.split()):
            return row
        return S.declare_from(new, row.object_type, dict(row.where or {}), row.existence,
                              board, references=list(row.references), count=row.count,
                              comparator=row.comparator, span=new, identity=row.identity,
                              sanctioned=row.sanctioned)._replace(
                                  excludes=row.excludes, unroutable=row.unroutable,
                                  mentions=row.mentions, assigned=row.assigned)
    # keep the side of the phrase that does not hold the value (the value never sits mid-phrase
    # with content on both sides that belongs to the thing — if it does, keep the head side)
    left = request[s0:max(s0, cand["start"])].rstrip()
    right = request[min(e0, cand["end"]):e0].lstrip()
    kept = left if left.strip() else right
    words = kept.split()
    dangling = _dangling(board)
    while words and (words[-1].strip(".,'\"").lower() in dangling
                     or _attribute_named(words[-1].strip(".,'\""), board)):
        words.pop()
    while words and words[0].strip(".,'\"").lower() in VALUE_CONNECTORS:
        words.pop(0)
    new = " ".join(words).strip(" ,")
    if not new or all(w.lower() in _DETS for w in new.split()):
        return None
    if new == span:
        return row
    return S.declare_from(new, row.object_type, dict(row.where or {}), row.existence, board,
                          references=list(row.references), count=row.count,
                          comparator=row.comparator, span=new, identity=row.identity,
                          sanctioned=row.sanctioned)._replace(
                              excludes=row.excludes, unroutable=row.unroutable,
                              mentions=row.mentions, assigned=row.assigned)


def _is_consumed(row: S.Declared, cand: dict, request: str, board) -> bool:
    """A kindless row that IS the value, or names its attribute word, is explained by it."""
    if row.object_type != S.UNKNOWN_KIND:
        return False
    span = str(row.span or row.name).strip().lower()
    bare = " ".join(w for w in span.split()
                    if w not in _DETS and w.strip(".,'\"") not in VALUE_CONNECTORS)
    if not bare:
        return False
    if bare in cand["text"].lower():            # the row IS the value (`8gb`, `4 cores`)
        return True                             # — never a row that merely HOLDS it (`db 8gb`)
    attr = _attribute_named(bare, board)
    if attr and (attr == cand["attribute"] or attr == cand["linked"]):
        return True
    return False


def read_values(rows: List[S.Declared], request: str, board=None,
                archive=None) -> List[S.Declared]:
    """The post-pass. Idempotent: a request with no learned number+word returns rows as-is."""
    from planner.formula.legal import Board
    board = board or Board()
    if archive is None:
        from .archive import ARCHIVE as archive
    if any(r.object_type == S.VALUE_KIND for r in rows):
        return rows                                 # already read
    cands = (_candidates(request, board, archive) + _naming_candidates(rows, request, board)
             + _shape_candidates(request, board, archive)
             + _genitive_candidates(rows, request, board, archive)
             + _of_genitive_candidates(rows, request, board, archive)
             + _have_frame_candidates(rows, request, board, archive)
             + _unshaped_selector_candidates(rows, request, board, archive))
    if not cands:
        return rows
    cands.sort(key=lambda c: c["start"])
    out = list(rows)
    values: List[S.Declared] = []
    for cand in cands:
        cand["selector"] = _selects(cand, out, request)
        if (cand.get("naming") or cand.get("shaped") or cand.get("genitive")
                or cand.get("unshaped")):
            scores = {cand["owner"]: 2}
        else:
            scores = rank_owners(cand, out, request, archive)
        if not scores:
            continue
        best = max(scores.values())
        winners = sorted(o for o, sc in scores.items() if sc == best)
        if cand.get("naming"):
            owner, attribute = cand["owner"], cand["attribute"]
            value = {"word": cand["word"], "attribute": attribute, "owner": owner,
                     "linked": attribute, "linked_text": cand["linked_text"],
                     "naming": True, "target_span": cand["target_span"]}
        elif cand.get("shaped"):
            owner, attribute = cand["owner"], cand["attribute"]
            value = {"word": cand["word"], "attribute": attribute, "owner": owner,
                     "linked": attribute, "linked_text": cand["linked_text"], "shaped": True}
        elif cand.get("unshaped"):
            owner, attribute = cand["owner"], None
            thing = f"a {owner}" if owner != "?" else "the thing"
            value = {"word": cand["word"], "attribute": None, "owner": owner,
                     "linked": None, "linked_text": "", "unshaped": True,
                     "hint": (f"{cand['text']!r} picks {thing} by an attribute this lab "
                              f"does not declare — which is it?")}
        elif cand.get("genitive"):
            owner, attribute = cand["owner"], cand["attribute"]
            value = {"word": cand["word"], "attribute": attribute, "owner": owner,
                     "linked": attribute, "linked_text": "", "genitive": True,
                     "of_kind": cand["of_kind"], "target_span": cand["target_span"]}
            if cand.get("ordering"):
                value["ordering"] = cand["ordering"]   # `oldest` — the axis is RESOLVE's ask
            if attribute is None:
                value["hint"] = (f"{cand['target_span']!r} has no {cand['word']!r} — nothing in "
                                 f"the manifest or the archive declares it; teach the word "
                                 f"or name the attribute")
        elif len(winners) == 1:
            owner = winners[0]
            attribute = next((e.attribute for e in cand["entries"] if owner in e.owners
                              and (cand["linked"] is None or e.attribute == cand["linked"])),
                             None) or next(e.attribute for e in cand["entries"] if owner in e.owners)
            value = {"word": cand["word"], "attribute": attribute, "owner": owner,
                     "linked": cand["linked"], "linked_text": cand["linked_text"].strip()}
        else:
            attribute = None
            value = {"word": cand["word"], "attribute": None, "owner": None,
                     "conflict": tuple(winners), "linked": cand["linked"],
                     "linked_text": cand["linked_text"].strip(),
                     "hint": f"'{cand['word']}' creates a conflict between "
                             + " and ".join(w.capitalize() for w in winners)}
        cand["attribute"] = attribute
        if cand["selector"]:
            value["selector"] = True
            value["comparator"] = _comparator_before(request, cand["start"])
        lifted: List[S.Declared] = []
        consumed: List[str] = []
        for r in out:
            if r.object_type == S.VALUE_KIND:
                lifted.append(r)
                continue
            if _is_consumed(r, cand, request, board):
                consumed.append(str(r.span or r.name))   # `the cpu of` — claimed by the value
                continue
            kept = _lift(r, cand, request, board)
            if kept is not None:
                lifted.append(kept)
        out = lifted
        value["consumed"] = tuple(t for t in consumed if t.lower() != cand["text"].lower())
        value["start"] = cand["start"]           # request order — `a` is also inside `create`
        values.append(S.Declared(name=cand["text"], object_type=S.VALUE_KIND, where={},
                                 existence=S.EXISTING, settled="read", span=cand["text"],
                                 value=value))
    # the values take their place in request order, after the things
    values = sorted(values, key=lambda v: (v.value or {}).get("start", 0))
    return _assign(out, values, request, board, archive)


def _target_of(v: S.Declared, rows: List[S.Declared], request: str, owner: str,
               archive) -> Optional[int]:
    """The thing this value is assigned to, in the order the request binds it:
      1 an owner-class row (or a child's) named in the value's own clause
      2 any row named in that clause
      3 a row the clause REFERS to — `give IT 4 cores` after `create a vm named alpha`
      4 the nearest thing-row before the value — `create a vm with 4 cores AND 8gb of ram`
        puts `8gb` in a clause of its own, and the vm is the thing just before it."""
    low = str(request).lower()
    clause = _clause_of(request, v.span)
    things = [(i, r) for i, r in enumerate(rows) if r.object_type != S.VALUE_KIND]
    named = [(i, r) for i, r in things if str(r.span or r.name).lower() in clause]
    for i, r in named:
        if _inherits(r.kind, owner, archive):
            return i
    if named:
        return named[0][0]
    words = set(clause.split())
    for i, r in things:
        if any(str(ref).lower() in words for ref in (r.references or ())):
            return i
    at = low.find(str(v.span).lower())
    before = [(i, r) for i, r in things if 0 <= low.find(str(r.span or r.name).lower()) < at]
    return before[-1][0] if before else None


def _assign(things: List[S.Declared], values: List[S.Declared], request: str, board,
            archive) -> List[S.Declared]:
    """Step 3: each value finds its target and the owner says whether it can be taken."""
    out = list(things)
    done: List[S.Declared] = []
    values = list(values)
    for v in values:
        info = dict(v.value or {})
        owner, attribute = info.get("owner"), info.get("attribute")
        # what this value claims of the request beside its own span — the attribute phrase
        # (`of memory`) — so gate 1 counts those words as read
        claims = [t for t in [info.get("linked_text") or "", *(info.get("consumed") or ())]
                  if str(t).strip()]
        if info.get("unshaped"):
            # rule 9: the slot licensed the span; nobody declares the attribute — the
            # owner refuses, and gate 4 asks the operator (never the model)
            target_ix = _target_of(v, out, request, str(info.get("owner") or ""), archive)
            info["target"] = out[target_ix].span if target_ix is not None else None
            info["refused"] = info["hint"]
            done.append(v._replace(value=info, references=claims))
            continue
        if info.get("genitive"):
            # rule 8: the grammar named the target; the leaf REFERS, nothing is set
            target_ix = next((i for i, r in enumerate(out) if r.object_type != S.VALUE_KIND
                              and r.span == info.get("target_span")), None)
            target = out[target_ix] if target_ix is not None else None
            info["target"] = target.span if target is not None else None
            kind = (target.kind if target is not None and target.kind in board.kinds
                    else owner if owner in board.kinds else None)
            if not attribute:
                info["refused"] = info.get("hint") or (
                    f"{info.get('target_span')!r} has no {info.get('word')!r}")
            elif kind:
                accepted, reason = board.accept(kind, attribute, v.span)
                if reason:
                    info["malformed"] = reason
                else:
                    info["accepted"] = accepted
            else:
                info["accepted"] = v.span
            done.append(v._replace(value=info, references=claims))
            continue
        if not owner or not attribute:
            done.append(v._replace(references=claims))
            continue
        if info.get("naming"):
            target_ix = next((i for i, r in enumerate(out)
                              if r.object_type != S.VALUE_KIND
                              and (r.span == info.get("target_span")
                                   or str(info.get("target_span") or "").startswith(
                                       str(r.span or "") + " "))), None)
        else:
            target_ix = _target_of(v, out, request, owner, archive)
        if target_ix is None:
            done.append(v._replace(value={**info, "target": None}, references=claims))
            continue
        target = out[target_ix]
        accepted, reason = board.accept(target.kind if target.kind in board.kinds else owner,
                                        attribute, v.span)
        info["target"] = target.span
        if info.get("selector"):
            # it PICKS the thing: the phrase keeps the filter, nothing is given or refused
            if reason:
                info["malformed"] = reason
            else:
                info["accepted"] = accepted
                if not info.get("comparator"):
                    where = dict(target.where or {})
                    where[attribute] = accepted
                    out[target_ix] = target._replace(where=where)
            done.append(v._replace(value=info, references=claims))
            continue
        if _is_predicate(v, request):
            info["predicate"] = True                 # `which vm has mac …` — asked, not set
            if reason:
                info["malformed"] = reason
            done.append(v._replace(value=info, references=claims))
            continue
        if reason:
            info["refused"] = reason
        elif target.existence == S.NEW or (info.get("naming")
                                           and _created_here(target, request, board)):
            info["accepted"] = accepted
            where = dict(target.where or {})
            if info.get("naming"):
                # the phrase walk already read a name into `where` (`alpha`, `stadium`); keep
                # what it read. A partial read of a GENERATOR (`1` of `1-5`) is replaced by
                # the spec; a LIST leaves `where` alone — the names are the value rows.
                siblings = sum(1 for o in values if (o.value or {}).get("naming")
                               and (o.value or {}).get("target_span") == info.get("target_span"))
                had = str(where.get(attribute, ""))
                if siblings == 1 and (not had or (_RANGE.match(str(accepted))
                                                  and str(accepted).startswith(had))):
                    where[attribute] = accepted
            else:
                where[attribute] = accepted      # the creator reads `where`; one copy, typed
            out[target_ix] = target._replace(
                where=where, assigned=tuple(sorted(set(target.assigned) | {attribute})))
        elif attribute in board.settable(target.kind):
            info["accepted"] = accepted          # a setter exists — pass 2's to emit
        else:
            info["refused"] = (f"this lab cannot set {attribute} on an existing "
                               f"{target.kind} — {v.span!r} for {target.span!r} is not "
                               f"something it can do")
        done.append(v._replace(value=info, references=claims))
    return out + done
