"""revision.py — what a repair must not throw away while answering an objection.

A repair is given a rejected program and a complaint, and it may rewrite freely. Nothing
checked that the rewrite still did what the first attempt was trying to do, and the failure
mode that exposes is specific and expensive: THE REPAIR DELETES THE LOGIC INSTEAD OF FIXING
IT, and the result validates, so every downstream check says the program is fine.

RUNG 11, measured 2026-07-30. The goal is *"ping every vm and stop the ones that do not
answer"*. The author wrote an `else` as a statement of its own; the objection said so,
correctly, and asked for it to be restructured — *"put those statements in that if's
`else`. Better still ... IF X THEN {} ELSE {Y} is the same program as IF NOT(X) THEN {Y}"*.
The repair came back with:

    FOREACH $item IN SELECT vm { STORE answer = guest_ping(name: $item); stop_vm(name: $item); }

Legal, valid, and it stops EVERY machine including the ones that answered. The condition is
simply gone. The objection named the right defect and the repair was worse than the first
attempt, which is the shape worth catching: a rejection is supposed to move a program
toward the goal, and this moved it away while satisfying the letter of the complaint.

WHY THE TEST IS "ZERO GUARDS LEFT" RATHER THAN "FEWER THAN BEFORE". No objection in this
language's vocabulary asks an author to DELETE a condition — they ask to invert it, to move
it into a field, to fill an empty branch. Restructuring can legitimately change how many
`if`s there are (two branches become one `IF NOT`), so a count comparison would fire on
correct repairs. Losing the last one cannot be a restructuring.

AND WHY IT IS NOT SPELLED "the objection did not mention `if`". That was the first version
and it does not fire here: the `else` objection mentions both `if` and `else` at length,
because it is explaining the fix. What matters is not which words the complaint used, it is
whether the answer kept the logic.

IT ADDS AN OBJECTION, IT DOES NOT REJECT. The repair loop simply gets told what it lost and
tries again, which costs one more round and can only ever be paid in calls — cheap, and the
alternative is a program that quietly does the wrong thing to every machine in the lab.

A FILTERED SELECT COUNTS AS A GUARD. `FOREACH $item IN SELECT vm WHERE alive = false` is a
perfectly good way to act on only some members and contains no `if` at all. Demanding an
`if` would be demanding a SHAPE rather than a result, and that is how a check starts
grading the program we expected instead of the program that works.
"""
from typing import Any, Dict, List, Optional

from .consent import _walk
from .validate import coerce_body

# The ops that carry a condition. `if` is the explicit one; a `foreach` whose `select`
# narrows the set is the implicit one, and both are legitimate answers to "act on only
# some of them".
_BRANCH = "if"


def guards(program: Any) -> List[Dict[str, Any]]:
    """Every statement in `program` that makes an action conditional.

    Two shapes count, because both are correct language for "only some of them":

      * an `if`, which guards its block
      * a `foreach` over a NARROWED set — a `select` carrying any filter beyond the bare
        kind, or an `in` naming a computed set. A loop over `SELECT vm` with no filter is
        not a guard: it acts on everything.
    """
    out: List[Dict[str, Any]] = []
    for st in _walk(coerce_body(program) or []):
        op = st.get("op")
        if op == _BRANCH:
            out.append(st)
        elif op == "foreach":
            sel = st.get("select")
            if isinstance(sel, dict) and [k for k in sel if k != "kind"]:
                out.append(st)
    return out


def lost_guard(before: Any, after: Any) -> Optional[str]:
    """An objection if the repair dropped the last condition, else None.

    Silent when the rejected program had no guard to lose — this only ever reports work
    that went missing, never demands work that was never there. A repair is not required
    to INVENT a condition; it is required not to throw one away.
    """
    had = guards(before)
    if not had:
        return None
    if guards(after):
        return None
    return ("your first attempt acted on only SOME members and this one acts on ALL of "
            "them — the condition is gone. Answer the objection WITHOUT dropping it: keep "
            "the check and restructure it. A check and its opposite are one decision, so "
            "write only the side that ACTS — `IF NOT(cond) THEN {work}` — or narrow the "
            "set instead, with `FOREACH $item IN SELECT <kind> WHERE <cond>`.")
