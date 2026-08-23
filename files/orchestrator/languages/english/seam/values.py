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
from ..codex import (ATTRIBUTE_LINKERS, CUT_DETERMINERS, DEFINITE, INDEFINITE, NAMING_CUES,
                     SELECTOR_PREPOSITIONS, VALUE_CONNECTORS)

_NUMBER_UNIT = re.compile(r"\b(\d+)\s*([a-z]+)\b")
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
             + _shape_candidates(request, board, archive))
    if not cands:
        return rows
    cands.sort(key=lambda c: c["start"])
    out = list(rows)
    values: List[S.Declared] = []
    for cand in cands:
        cand["selector"] = _selects(cand, out, request)
        if cand.get("naming") or cand.get("shaped"):
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
