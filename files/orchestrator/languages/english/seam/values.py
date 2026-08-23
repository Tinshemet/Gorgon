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
  3 PLACE  a value INSIDE an existing phrase behind a SELECTOR_PREPOSITION selects and stays
           where it is (`the vm at 10.0.0.5`, `every vm with over 6gb of ram` — that is
           `where`'s and `magnitudes_in`'s); every other value is ASSIGNED and becomes a
           VALUE_KIND row of its own, lifted OUT of whatever phrase swallowed it
           (`the db vm 16gb` -> `the db vm` + `16gb`; `a vm with 4` -> `a vm` + `4 cores`)
  4 CLEAN  a kindless row that is the value itself or its attribute word (`8gb`, `ram`,
           `the cpu`) is not a thing — it is consumed by the value that explains it
  5 ASSIGN (step 3, 08-23) the value to its TARGET — the owner-class row in the clause.
           The owner scrutinises the bytes (`Board.accept`, read off `attr_classes`): a NEW
           target takes the accepted value into `where`, which is what its creator reads
           (`create a vm with 4 cores and 8gb of ram` -> create_vm cpu_cores=4 memory_mb=8192);
           an EXISTING target takes it only if the manifest declares a SETTER for that
           attribute — otherwise the value is REFUSED with the owner's reason, and gate 4
           tells the operator, never the model ([[gorgon-can-the-world-satisfy-it]])
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
from ..codex import (ATTRIBUTE_LINKERS, DEFINITE, INDEFINITE, SELECTOR_PREPOSITIONS,
                     VALUE_CONNECTORS)

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


def _lift(row: S.Declared, cand: dict, request: str, board) -> Optional[S.Declared]:
    """The row with the value cut out of its phrase; None if nothing is left of it."""
    low = str(request).lower()
    span = str(row.span or "")
    at = low.find(span.lower())
    if at < 0:
        return row
    s0, e0 = at, at + len(span)
    if cand["end"] <= s0 or cand["start"] >= e0:
        return row                                  # the value is not in this phrase
    # keep the side of the phrase that does not hold the value (the value never sits mid-phrase
    # with content on both sides that belongs to the thing — if it does, keep the head side)
    left = request[s0:max(s0, cand["start"])].rstrip()
    right = request[min(e0, cand["end"]):e0].lstrip()
    kept = left if left.strip() else right
    words = kept.split()
    while words and words[-1].strip(".,'\"").lower() in VALUE_CONNECTORS:
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
                              excludes=row.excludes, unroutable=row.unroutable)


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
    cands = _candidates(request, board, archive)
    if not cands:
        return rows
    if any(r.object_type == S.VALUE_KIND for r in rows):
        return rows                                 # already read
    out = list(rows)
    values: List[S.Declared] = []
    for cand in cands:
        if _selects(cand, out, request):
            continue
        scores = rank_owners(cand, out, request, archive)
        if not scores:
            continue
        best = max(scores.values())
        winners = sorted(o for o, sc in scores.items() if sc == best)
        if len(winners) == 1:
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
        values.append(S.Declared(name=cand["text"], object_type=S.VALUE_KIND, where={},
                                 existence=S.EXISTING, settled="read", span=cand["text"],
                                 value=value))
    # the values take their place in request order, after the things
    values = sorted(values, key=lambda v: str(request).find(v.span))
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
        target_ix = _target_of(v, out, request, owner, archive)
        if target_ix is None:
            done.append(v._replace(value={**info, "target": None}, references=claims))
            continue
        target = out[target_ix]
        accepted, reason = board.accept(target.kind if target.kind in board.kinds else owner,
                                        attribute, v.span)
        info["target"] = target.span
        if reason:
            info["refused"] = reason
        elif target.existence == S.NEW:
            info["accepted"] = accepted
            where = dict(target.where or {})
            where[attribute] = accepted          # the creator reads `where`; one copy, typed
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
