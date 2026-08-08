"""GATES 1 AND 2, ON DECLARATIONS — the confirm step between pass 1 and pass 2.

Item 4. Deterministic: no model call, so the suite owns it.

    GATE 1   DID YOU SAY THIS?      every declared name and every condition VALUE must trace
                                    to the request. A name tracing to nothing was invented.
    GATE 2   CAN THE WORLD HOLD IT? is the kind declared, the attribute real, the value legal,
                                    the reference resolvable — all from the manifest.

# ⇒ WHY THIS IS WHERE THE OPERATOR'S DECOUPLING ARRIVES FOR FREE

The standing rule was that every gate except 3 and 4 should be indifferent to Medusa changing.
The old gates broke it — gate 1 had 9 direct IR-shape reads and gate 2 had 12 — because they
ran on a PROGRAM. These run on a DECLARATION LIST. **There is no program shape here to read,**
so they cannot be coupled to it. The split did the decoupling; no refactor was needed.

# ⇒ WHAT THEY DO NOT DO

**NEITHER GATE REPAIRS.** Gate 1 says a name was invented; it does not invent a better one.
Gate 2 says a value is illegal; it does not choose a legal one. Everything they find becomes a
QUESTION, because we cannot know what the operator meant and it is theirs to say
([[gorgon-gates-check-legality]]).

**AND GATE 2'S WORLD ARM NEEDS A WORLD.** The manifest says what is POSSIBLE; only the lab says
what is THERE. `conflicts()` takes an optional world and is the arm that catches the operator's
own scenario — *"you asked me to create web and there is already a web"* — which is exactly
where pass 1's 85% existence answer gets checked rather than trusted.
"""
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
from . import schema as S


class Finding(NamedTuple):
    gate: int
    kind: str                # invented · unknown-kind · no-such-attribute · illegal-value · …
    about: str               # the declared name it concerns
    says: str                # the question, in the operator's terms

    def __repr__(self):
        return f"[gate {self.gate}] {self.about}: {self.says}"


def _words(text: str) -> set:
    return {w.strip(".,'\"!?:;()[]").lower() for w in str(text).split() if w.strip(".,'\"!?:;()")}


def _traces(value, request: str) -> bool:
    """Does this value appear in the request, allowing for the operator's own wording?"""
    token = str(value).strip().lower()
    if token in ("true", "false", ""):
        return True                       # a boolean is a reading of the words, not a quote
    if token in request.lower():
        return True
    return any(token in w or w in token for w in _words(request) if len(w) > 3)


# ── GATE 1 · did you say this? ────────────────────────────────────────────────────────
def gate1(rows: List[S.Declared], request: str) -> List[Finding]:
    """Every name and every VALUE must trace to the request.

    THE ATTRIBUTE IS NOT CHECKED — it comes from a closed enum the manifest supplied, so it
    could not have been invented. Only what the model chose freely can be.
    """
    out: List[Finding] = []
    for row in rows:
        if not _traces(row.name, request):
            out.append(Finding(1, "invented", row.name,
                               f"nothing in the request says {row.name!r} — did you mean it?"))
        for attr, value in (row.where or {}).items():
            if not _traces(value, request):
                out.append(Finding(1, "invented-value", row.name,
                                   f"the request never says {attr} is {value!r} — "
                                   f"did you mean that?"))
    return out


# ── GATE 2 · can the world hold it? ───────────────────────────────────────────────────
def gate2(rows: List[S.Declared], board: Optional[Board] = None) -> List[Finding]:
    """Legality against the manifest. Nothing here needs the lab to be running."""
    board = board or Board()
    out: List[Finding] = []
    for row in rows:
        if row.kind not in board.kinds:
            out.append(Finding(2, "unknown-kind", row.name,
                               f"this lab has no {row.kind!r}"))
            continue
        for attr, value in (row.where or {}).items():
            if attr not in board.filterable(row.kind):
                out.append(Finding(2, "no-such-attribute", row.name,
                                   f"a {row.kind} has no {attr!r}"))
                continue
            allowed = board.values(row.kind, attr)
            if allowed and str(value).lower() not in [a.lower() for a in allowed]:
                out.append(Finding(2, "illegal-value", row.name,
                                   f"{row.kind}.{attr} cannot be {value!r} — "
                                   f"it must be one of {allowed}"))
        # A SET DEFINED BY A PROBE CANNOT BE CREATED — you can only go and look.
        if row.residual and row.existence == S.NEW:
            out.append(Finding(2, "cannot-be-made", row.name,
                               f"{row.name!r} is decided by asking the machines, so it cannot "
                               f"be created — only found"))
    return out


def conflicts(rows: List[S.Declared], world, board: Optional[Board] = None) -> List[Finding]:
    """GATE 2'S WORLD ARM — the operator's own scenario, and it needs a lab to answer.

    *"What if a resource exists so fetch is triggered, but the user asks for creation anyway?
    Gate 2 has to know the difference based on the information from the AI."*

    Pass 1 states an intent at 85%, with every measured error toward `new`. This is where that
    intent is CHECKED rather than trusted, and the disagreement becomes a question.
    """
    board = board or Board()
    out: List[Finding] = []
    if world is None:
        return out
    from planner.gates import claims as _claims

    for row in rows:
        key_attr = _claims.key_of(row.kind, board.kinds)
        value = (row.where or {}).get(key_attr) if key_attr else None
        if not value:
            continue
        try:
            there = bool(world.select({"kind": row.kind, key_attr: value}))
        except Exception:
            continue
        if row.existence == S.NEW and there:
            out.append(Finding(2, "already-there", row.name,
                               f"you asked to create {value!r} and there is already one — "
                               f"use it, or did you mean a second?"))
        if row.existence == S.EXISTING and not there:
            out.append(Finding(2, "not-there", row.name,
                               f"{value!r} is referred to as if it exists and the lab has "
                               f"none — should it be created?"))
    return out


def report(rows: List[S.Declared], request: str, board: Optional[Board] = None,
           world=None) -> Dict[str, object]:
    """Both gates over one symbol table. NOTHING IS REPAIRED — findings are questions."""
    board = board or Board()
    found = gate1(rows, request) + gate2(rows, board) + conflicts(rows, world, board)
    return {
        "findings": found,
        "asks": [f.says for f in found],
        "legal": not found,
        "by_gate": {1: [f for f in found if f.gate == 1],
                    2: [f for f in found if f.gate == 2]},
    }
