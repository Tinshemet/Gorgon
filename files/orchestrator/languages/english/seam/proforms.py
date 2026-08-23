"""proforms.py — A LATER MENTION BINDS BY NUMBER AGREEMENT (operator, 2026-08-23, ledger #18).

# ⇒⇒ THE RULING
*"'those' is plural, and the only plural here is '3 vms' — it should be paired based on the
plurality."* — on nl-0004: `create 3 vms named after musicians and a network called the
stadium and add those vms to it`. `those` → the only plural thing, `3 vms`; `it` → the only
singular one, `a network`. Until now three mechanisms bound a later mention and none looked
at number: the scan re-sighting the same NOUN (`vms`), the bare-pronoun rule taking the MOST
RECENT row, `resolve_proforms` matching a modifier's CONTENT. Recency got `it` right here by
luck; agreement gets it right by rule.

# ⇒ THE RULE, IN ORDER
  1 a mention carries a NUMBER — from the codex's SINGULAR_PROFORMS / PLURAL_PROFORMS, or
    from the demonstrative heading a phrase (`those vms` is many, `this network` is one)
  2 its candidates are the THINGS DECLARED BEFORE IT (an antecedent precedes)
  3 AGREEMENT filters: a row is many if it is a set, counted above one, or headed by a
    plural noun; otherwise one
  4 FIT breaks a tie among those that agree: the mention's noun names the row's kind
    (`those VMS`), or its modifier equals a value the row carries (`the BLUE ones`)
  5 exactly one best → BOUND: the row records the mention (text · offsets · number); the
    words join `references`, the older carrier. More than one → NOTHING is bound, and the
    conflict travels on every candidate with its hint — `'it' could be the vm or the
    network` — for ROUTE to ASK. The same shape as the leaf rule: fit, then tie → ASK.
  ✗ a mention that is already a ROW (`it` declared by the clause rule, `the blue ones` kept
    as its own certified span) is left to the rules that made it a row

# ⇒ WHAT IS REPORTED
A full-phrase mention (`those vms`, `the ones`) is a span of its own in the reading — nl-0004's
gold has five spans and the reader reported four. A BARE pronoun is bound but never reported
as a span: the gold points at the thing, never at the pointer (the 08-22 bare-pronoun rule).
"""
import re
from typing import Dict, List, Optional, Tuple

from . import schema as S
from ..codex import DEMONSTRATIVES, PLURAL_PROFORMS, RESTRICTORS, SINGULAR_PROFORMS


def _number_of_row(row: S.Declared) -> str:
    if row.is_set:
        return "many"
    c = row.count
    if isinstance(c, int) and c > 1:
        return "many"
    if isinstance(c, str) and c.lower() in ("all", "every", "each"):
        return "many"
    head = str(row.span or row.name).lower().split()
    if head and head[-1].endswith("s") and not head[-1].endswith("ss"):
        return "many"
    return "one"


def _mentions_in(request: str, rows: List[S.Declared], board) -> List[dict]:
    """Every pro-form occurrence that is not itself a row's span, with its number."""
    from .scan import _index
    low = str(request).lower()
    nouns = _index(board)
    taken = []
    for r in rows:
        span = str(r.span or r.name).lower()
        at = low.find(span)
        if at >= 0:
            taken.append((at, at + len(span)))
    out: List[dict] = []
    phrases = sorted(set(SINGULAR_PROFORMS) | set(PLURAL_PROFORMS) | set(DEMONSTRATIVES),
                     key=len, reverse=True)
    seen = set()
    for phrase in phrases:
        for m in re.finditer(r"\b%s\b" % re.escape(phrase), low):
            start, end = m.start(), m.end()
            head = phrase.split()[-1]
            text, number, bare, noun = phrase, None, True, None
            # a demonstrative heading a phrase: `those vms`, `this network`, `the blue ones`
            nxt = re.match(r"\s+([a-z][a-z'-]*)(\s+(ones?))?\b", low[end:])
            if head in DEMONSTRATIVES and nxt:
                w = nxt.group(1)
                if w in nouns or w in ("one", "ones"):
                    text = low[start:end + nxt.end(1)]
                    end = end + nxt.end(1)
                    number, bare, noun = DEMONSTRATIVES[head], False, (w if w in nouns else None)
                elif nxt.group(3):                         # `those blue ones`
                    text = low[start:end + nxt.end()]
                    end = end + nxt.end()
                    number, bare = DEMONSTRATIVES[head], False
                elif head in ("this", "that"):
                    continue                               # `that` relativiser / complementiser
                else:
                    number = DEMONSTRATIVES[head]
            elif head in DEMONSTRATIVES and head in ("this", "that"):
                continue
            elif head in DEMONSTRATIVES:
                number = DEMONSTRATIVES[head]
            if number is None:
                number = "one" if phrase in SINGULAR_PROFORMS else "many"
                bare = phrase.split()[0] not in ("the",)
            if any(a <= start < b or a < end <= b for a, b in taken):
                continue                                   # already a row's own span
            if head in ("one", "ones") and any(0 <= start - b <= 1 for _a, b in taken):
                continue                                   # `the blue ▸ones` — the phrase's own head
            if (start, end) in seen:
                continue
            # `it` heading a restriction is a description, not a reference
            after = low[end:end + 12].split()
            if bare and after and after[0].strip(".,") in RESTRICTORS:
                continue
            seen.add((start, end))
            out.append({"text": request[start:end], "start": start, "end": end,
                        "number": number, "bare": bare, "noun": noun,
                        "modifiers": [w for w in text.split()[1:-1]] if not bare else []})
    return sorted(out, key=lambda d: d["start"])


def bind_mentions(rows: List[S.Declared], request: str, board=None) -> List[S.Declared]:
    """The pass: each mention finds the thing it agrees with; a tie is carried, not guessed."""
    from planner.formula.legal import Board
    from .scan import _index
    board = board or Board()
    nouns = _index(board)
    low = str(request).lower()
    out = list(rows)
    for mention in _mentions_in(request, rows, board):
        things = [(i, r) for i, r in enumerate(out)
                  if r.object_type != S.VALUE_KIND
                  and 0 <= low.find(str(r.span or r.name).lower()) < mention["start"]]
        agree = [(i, r) for i, r in things if _number_of_row(r) == mention["number"]]
        if not agree:
            continue
        def fit(r: S.Declared) -> int:
            score = 0
            if mention["noun"] and nouns.get(mention["noun"]) == r.kind:
                score += 1
            vals = {str(v).lower().strip("'\"") for v in (r.where or {}).values()}
            if mention["modifiers"] and all(m.strip("'\"") in vals for m in mention["modifiers"]):
                score += 1
            return score
        best = max(fit(r) for _i, r in agree)
        winners = [(i, r) for i, r in agree if fit(r) == best]
        if len(winners) == 1:
            i, host = winners[0]
            out[i] = host._replace(
                references=list(host.references or []) + [mention["text"]],
                mentions=tuple(host.mentions or ()) + ({**mention, "bound": True},))
        else:
            names = [str(r.span or r.name) for _i, r in winners]
            hint = (f"'{mention['text']}' could be " + " or ".join(names)
                    + " — they agree in number and nothing picks one")
            conflict = {**mention, "bound": False, "conflict": tuple(names), "hint": hint}
            for i, r in winners:
                out[i] = r._replace(mentions=tuple(r.mentions or ()) + (conflict,))
    return out


def unbound(rows: List[S.Declared]) -> List[str]:
    """The conflicts, once each — for the gate that asks."""
    seen, out = set(), []
    for r in rows:
        for m in (r.mentions or ()):
            if not m.get("bound") and (m["start"], m["end"]) not in seen:
                seen.add((m["start"], m["end"]))
                out.append(m["hint"])
    return out
