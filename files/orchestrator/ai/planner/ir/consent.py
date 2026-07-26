"""Does running this program need the operator's word first?

ENSURE is Medusa's safety net, and the language leans on it: it is the only thing that
says what the program was FOR, the only witness the closure audit will accept, and the
only reason a re-run can tell "already done" from "did nothing". A program that changes
the world and never checks it has vouched for nothing — the executor cannot report it
honestly, and nobody can re-run it safely.

The operator's ruling: that is not a warning. A warning nobody can silence is noise
people learn to scroll past, and this one would appear on exactly the programs that most
need reading. It is a question, asked before anything runs — *this code has no grounding,
are you sure?* — and the answer is a yes or a no.

Kept separate from validate.py on purpose. An ungrounded program is not malformed; it is
a policy question, and the two must not be answered by the same function. Merging them
would mean either that a legitimate one-shot cannot be written at all, or that a real
structural error and a request for consent arrive as the same kind of complaint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Ops that CHANGE the world. `ensure` and `if` are excluded because neither acts on its
# own: an `if` is only as consequential as the block it runs, and that block's own
# statements are counted when the walk reaches them.
_ACTING = {"new", "call", "foreach"}

# Where a statement can carry more statements. Read from the field catalogue rather than
# listed here, so a construct added to the manifest is walked without an edit — the same
# claim the rest of the language makes.
_BLOCK_FIELDS = ("do", "then", "else", "ifails")


def _walk(body: Any) -> List[Dict[str, Any]]:
    """Every statement in the program, nested blocks included."""
    out: List[Dict[str, Any]] = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        out.append(st)
        for field in _BLOCK_FIELDS:
            kids = st.get(field)
            if isinstance(kids, list):
                out += _walk(kids)
    return out


def survey(program: Any) -> Dict[str, Any]:
    """What this program does and whether anything checks it.

    Returns {acts, asserts, grounded}. `acts` counts world-changing statements ANYWHERE,
    including inside a loop body or a recovery block — a program whose only effect is in
    an IFAILS is still a program with effects.
    """
    from .validate import coerce_body
    body = coerce_body(program) or []
    stmts = _walk(body)
    acts = sum(1 for st in stmts if st.get("op") in _ACTING)
    # Both words ground a program. `achieve` is the stronger of the two — it states what
    # the whole thing was for — so a program carrying one is grounded by definition.
    asserts = sum(1 for st in stmts if st.get("op") in ("ensure", "achieve"))
    return {"acts": acts, "asserts": asserts, "grounded": acts == 0 or asserts > 0}


def question(program: Any) -> Optional[str]:
    """The operator's question, or None if the program grounds itself.

    Names the number of acting statements rather than saying "this program makes
    changes", because the count is the part that decides the answer: consenting to one
    unverified label is not consenting to sixteen.
    """
    s = survey(program)
    if s["grounded"]:
        return None
    n = s["acts"]
    return (f"This program has no grounding: {n} statement{'s' if n != 1 else ''} "
            f"change{'' if n != 1 else 's'} the world and no ENSURE checks the result. "
            f"Nothing will vouch for what it did. Run it anyway?")


def granted(program: Any, consent: Any) -> bool:
    """Has running this been authorised?

    `consent` is True (granted outright), a callable asked with the question, or anything
    else — including the default None, meaning no operator is present.

    Absent an operator the answer is NO. Fail-closed is the standing rule for every other
    high-impact act here and there is no reason for programs to be the exception: the
    alternative is that an unattended run quietly grants itself the permission a person
    was supposed to give.
    """
    if question(program) is None:
        return True
    if consent is True:
        return True
    if callable(consent):
        return bool(consent(question(program)))
    return False
