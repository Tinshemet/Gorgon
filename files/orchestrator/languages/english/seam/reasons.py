"""reasons.py — a REASON GIVEN WITH THE ACT: because · although · to/so-that, one reader.

# ⇒⇒ THE OPERATOR'S DESIGN (08-24, closing the 08-16 sweep's last hole)
*"purpose is constructed from 2 things which are already implemented in a 'sibling',
diagnosis, but on the other way around: we have a request and evidence/rule … this a ledger
entry, with a request attached … 'why is vm3 stopped?' -> 'vm3 was stopped due to it being
idle, reverse the decision?'"*

Diagnosis reads evidence and produces a decision; here the human DECIDES and hands the
evidence with the act. Three surface families, one relation:
  cause       `stop the vms BECAUSE they are stuck`     — a present symptom
  concession  `launch the fleet EVEN THOUGH … is slow`  — a counter-reason, overruled
  purpose     `stop the idle vms TO free memory`        — a future use
The clause is EVIDENCE by the certified 08-22 convention ("you do need to carry the evidence
… its a future reference"), carried by the act. Span convention, certified in the v3 gold:
a SUBORDINATING marker stays OUTSIDE its span (`they are stuck`); the purposive marker is
PART of it (`to free memory`, `so we can roll back`).

⇒ READ carries; it never judges the reason. The ledger entry + the why-answer live at
  ROUTE/RESOLVE (the operator's flow above) — future work, parked in the ledger.
⇒ THE `to` GUARDS (a preposition is not a purpose): a TRANSFER verb's `to` heads the verb's
  own argument (`move it TO the dmz`, scan's rule); a `to` followed by a determiner, a
  pronoun, a declared noun, a digit or a unit is a destination or a value (`to 4 cores`);
  what remains — `to` + a bare non-thing word — is the infinitive.
"""
import re
from typing import List, NamedTuple, Optional

from ..codex import (CUT_DETERMINERS, DEFINITE, INDEFINITE, OBJECT_PRONOUNS,
                     REASON_CAUSE, REASON_CONCESSION, REASON_MARKER_WORDS,
                     REASON_PURPOSE_SO, TRANSFER_VERBS)


class Reason(NamedTuple):
    family: str          # cause · concession · purpose
    span: str            # the evidence bytes, by the certified span convention
    start: int
    end: int


# the codex owns the classes ([[test_codex_is_the_only_home]]); these are its names
_CAUSE, _CONCESSION, _PURPOSE_SO = REASON_CAUSE, REASON_CONCESSION, REASON_PURPOSE_SO
_MARKER_WORDS, _TRANSFER = REASON_MARKER_WORDS, TRANSFER_VERBS
_DETS = set(DEFINITE) | set(INDEFINITE) | set(CUT_DETERMINERS)
_PRONOUNS = OBJECT_PRONOUNS


def _tail(text: str, at: int) -> str:
    out = text[at:].strip()
    return out.rstrip(".!?,;").strip()


def read(sentence: str, board=None) -> List[Reason]:
    """Every reason clause in the sentence, at its offsets. Deterministic, marker-driven."""
    from .scan import _index
    low = sentence.lower()
    nouns = _index(board) if board is not None else {}
    out: List[Reason] = []
    taken: List[tuple] = []

    def _claim(start: int, end: int) -> bool:
        if any(s < end and start < e for s, e in taken):
            return False
        taken.append((start, end))
        return True

    for fam, markers, keep in (("concession", _CONCESSION, False),
                               ("cause", _CAUSE, False),
                               ("purpose", _PURPOSE_SO, True)):
        for m in markers:
            for hit in re.finditer(r"(?<![\w])%s\b" % re.escape(m), low):
                body = _tail(sentence, hit.end())
                if not body or len(body.split()) < 2:
                    continue                       # `so` needs a clause, not a particle
                start = hit.start() if keep else hit.end() + (len(sentence[hit.end():])
                                                              - len(sentence[hit.end():].lstrip()))
                span = sentence[hit.start():].strip().rstrip(".!?,;") if keep else body
                if _claim(hit.start(), hit.start() + len(span)):
                    out.append(Reason(fam, span, start if not keep else hit.start(),
                                      (start if not keep else hit.start()) + len(span)))
    # the infinitival purpose — `to` + a bare non-thing word, never a transfer's argument
    for hit in re.finditer(r"(?<![\w])to\s+([a-z][\w-]*)", low):
        head = hit.group(1)
        if (head in _DETS or head in _PRONOUNS or head in nouns
                or head.isdigit() or re.fullmatch(r"\d+[a-z]*", head)):
            continue
        before = low[:hit.start()].split()
        if any(w in _TRANSFER for w in before[-3:]):
            continue                               # `move it to …` — the verb's argument
        body = _tail(sentence, hit.start())
        if len(body.split()) < 3:
            continue                               # `to free` alone is not a stated reason
        if _claim(hit.start(), hit.start() + len(body)):
            out.append(Reason("purpose", body, hit.start(), hit.start() + len(body)))
    return sorted(out, key=lambda r: r.start)


def strip(rows: List, request: str, board=None) -> List:
    """Subtractive: a row that swallowed a reason clause gives it back — the reason is the
    act's evidence, never a thing. A row fully inside a reason region is not a thing at all
    (`the fleet even though` — co-0002's junk, priced on the certified run)."""
    from . import schema as S
    reasons = read(request, board)
    if not reasons:
        return rows
    low = str(request).lower()
    regions = [(min(r.start for r in reasons), max(r.end for r in reasons))]
    regions = [(r.start, r.end) for r in reasons]
    out = []
    for row in rows:
        span = str(row.span or row.name)
        at = low.find(span.lower())
        if at < 0:
            out.append(row)
            continue
        s0, e0 = at, at + len(span)
        if any(rs <= s0 and e0 <= re_ for rs, re_ in regions):
            continue                               # fully inside the reason — not a thing
        cut = min((rs for rs, re_ in regions if s0 < rs < e0), default=None)
        if cut is None:
            # a marker word glued to the row's tail with the reason outside it
            words = span.split()
            while words and words[-1].lower() in _MARKER_WORDS:
                words.pop()
            new = " ".join(words)
            if new != span and new:
                row = S.declare_from(new, row.object_type, dict(row.where or {}),
                                     row.existence, board, references=list(row.references),
                                     count=row.count, comparator=row.comparator, span=new,
                                     identity=row.identity, sanctioned=row.sanctioned
                                     )._replace(excludes=row.excludes,
                                                unroutable=row.unroutable,
                                                mentions=row.mentions, assigned=row.assigned)
            out.append(row)
            continue
        new = request[s0:cut].strip().rstrip(",;")
        words = new.split()
        while words and words[-1].lower() in _MARKER_WORDS:
            words.pop()                    # a cause/concession marker is OUTSIDE its span,
        new = " ".join(words)              #   so the cut lands after it — pop it off the row
        if not new:
            continue
        out.append(S.declare_from(new, row.object_type, dict(row.where or {}),
                                  row.existence, board, references=list(row.references),
                                  count=row.count, comparator=row.comparator, span=new,
                                  identity=row.identity, sanctioned=row.sanctioned
                                  )._replace(excludes=row.excludes,
                                             unroutable=row.unroutable,
                                             mentions=row.mentions, assigned=row.assigned))
    # the same thing read twice (once whole, once glued) collapses to one row
    seen = set()
    deduped = []
    for row in out:
        key = str(row.span or row.name).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped
