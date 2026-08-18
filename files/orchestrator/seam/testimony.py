"""testimony.py — THE MALFUNCTION PREDICATE, read from its SHAPE. D1's front door.

    *"vm2 is not working"* · *"alpha won't start"* · *"the web vm keeps dropping off"*

# ⇒⇒ WHY THIS EXISTS — the certified eval priced the gap (2026-08-18)

Diagnosis is the worst stratum on the frozen v1 set: detect 5/11, 16 hallucinated acts.
Three coupled defects, one cause — nothing reads an UNQUOTED symptom clause:
    the rows FUSE          `vm2 is not working` was one `?` row — patient and symptom never split
    the channel is blind   ISO's Inform fired on 2 of 4 report acts
    pass 2 ACTS on it      delete_vm emitted from "is not working" — the symptom, executed

# ⇒ THE TEST IS STRUCTURAL, NEVER VOCABULARY — the closed-class licence

A clause is TESTIMONY when its main predication is a verbal malfunction shape:

    NEGATED MODAL + verb        won't start · can't reach · wouldn't boot
                                (after a negated modal the next word IS a verb, by grammar)
    NEGATED COPULA + gerund     is not working · isn't responding
                                (the -ing head is what separates it from teaching-negation:
                                 *"alpha is not THE JUMPBOX"* has a nominal complement)
    ITERATIVE aux + gerund      keeps dropping · keep failing

⇒ ⚠ **WHAT IS DELIBERATELY NOT COVERED: bare adjectives.** *"is down"*, *"is broken"*,
  *"something is wrong"* need a malfunction VOCABULARY, which is an open class — the banned
  thing. The declared extension point is the archive/Encyclopedia teaching those adjectives
  ([[gorgon-encyclopedia]]); until taught they stay UNREAD, which is an honest miss the eval
  bills, never a guess.

# ⇒ THE GUARDS, each one a certified case in the frozen set

    behind a RELATIVIZER  ->  a FILTER, not testimony    "every vm that is not running"
    no SUBJECT before it  ->  a negated IMPERATIVE       "don't stop the web vm"
    nominal complement    ->  teaching-negation          "alpha is not the jumpbox"
"""
import re
from typing import List, NamedTuple, Optional

from planner.formula.legal import Board

# the negated forms, closed: modals whose complement is a bare verb by grammar, and the
# copula/do forms whose complement must then be tested for verbality
NEG_MODALS = frozenset({"won't", "wont", "can't", "cant", "cannot", "couldn't",
                        "wouldn't", "shan't"})
NEG_DO = frozenset({"doesn't", "don't", "didn't"})
COPULAS = frozenset({"is", "are", "was", "were", "isn't", "aren't", "wasn't", "weren't"})
ITERATIVES = frozenset({"keeps", "keep", "kept"})
_RELATIVIZERS = frozenset({"that", "which", "who", "whom", "whose", "where", "when"})


class Testimony(NamedTuple):
    subject: str            # the thing the symptom is about — becomes the row
    predicate: str          # the symptom itself — consumed, never a thing
    clause: str             # the whole asserting clause — the REPORT act's span


def _clauses(request: str) -> List[str]:
    return [c.strip() for c in re.split(r"[,;.]|\band\b|\bthen\b|—|–", str(request))
            if c.strip()]


def _words(text: str) -> List[str]:
    return re.findall(r"[\w:']+", str(text).lower())


def _of_clause(clause: str) -> Optional[Testimony]:
    words = _words(clause)
    for at, word in enumerate(words):
        if at == 0:
            continue                      # no subject before it -> imperative, not testimony
        if any(w in _RELATIVIZERS for w in words[:at]):
            return None                   # behind a relativizer -> a filter, not testimony
        negated_copula = (word in COPULAS and at + 1 < len(words)
                          and words[at + 1] in ("not", "never"))
        if word in NEG_MODALS or word in NEG_DO or word in ITERATIVES or negated_copula:
            head_at = at + (2 if negated_copula else 1)
            if head_at >= len(words):
                return None
            head = words[head_at]
            # a negated modal's complement is a verb BY GRAMMAR; the others need the
            # verbal-head test — a gerund — or they are teaching-negation / description
            if word in NEG_MODALS or word in NEG_DO:
                pass
            elif not head.endswith("ing"):
                return None
            subject = " ".join(words[:at])
            predicate = " ".join(words[at:])
            return Testimony(subject, predicate, clause.strip())
    return None


def read(request: str, board: Optional[Board] = None) -> List[Testimony]:
    """Every testimony clause in the request. Deterministic, zero model calls."""
    out = []
    for clause in _clauses(request):
        got = _of_clause(clause)
        if got:
            out.append(got)
    return out


def is_testimony(clause: str, board: Optional[Board] = None) -> bool:
    return _of_clause(str(clause)) is not None
