"""repair.py — COMPUTE THE FIX WHERE THE MANIFEST NAMES EXACTLY ONE. Never guess, never ask.

⇒⇒ **THE STAGE THAT WAS MISSING, AND ITS ABSENCE WAS COSTING RUNGS.**

The chain could DETECT and it could ASK. It could not FIX:

    sanitize   remove what does nothing            BUILT   (planner/ir/sanitize.py)
    repair     compute the fix where we know it    THIS
    ask        hand it back to the model           the retry — was the first and only move

Gate 3 says *"a snapshot is made from a vm, and 'snapshot' is a snapshot — aim it at what it is
made FROM"*. **That objection already names its own remedy**, and the remedy is a manifest
lookup: `snapshot.create_args = {"vm": "name"}`, computed by `Board.makeable`. We were spending
a model call to ask a question we could answer ourselves — and then judging the reply on a rule
that could throw the answer away (see the harvest note in `pipeline.py`).

⇒ **A GATE STILL DOES NOT REPAIR, AND THIS IS NOT A GATE.** `gate3`'s own header draws that
  line: it says the step is illegal and why, and does not choose a legal operator. This module
  is the separate consumer of that finding — the same split the sanitiser has, one regime over.

⇒ **AND IT ONLY MOVES WHEN THE ANSWER IS UNIQUE.** Two candidates is not a fix, it is a guess
  with better odds, and a guess is what the whole front seam exists to refuse
  ([[gorgon-deterministic-rules]]: compute, decline when unsure). Where it declines, the
  finding survives untouched and the model gets its turn exactly as before.

⇒⇒ **EVERY REPAIR IS REPORTED, BECAUSE THIS CHANGES WHAT THE PROGRAM DOES.** The sanitiser may
  be quiet — it only removes what cannot run. This re-aims a step, so the operator must be able
  to see that the program they are reading is not the one the author wrote. A silent correction
  is how a harness starts lying on the author's behalf.

⇒ WHY SUBTRACTIVE IS THE RIGHT SHAPE, MEASURED. Asked WHY it aimed `create_snapshot` at
  `snapshot`, the model answered identically 3/3 — *"it is more specific and directly related"*
  — a rationalisation of a SPELLING COLLISION between the operator and the row. Asked how many
  snapshots `create_snapshot(running_vms)` makes over four machines it said FIVE, 3/3: there is
  no per-member semantics in its head to appeal to. **But asked to choose between the two steps
  it picks correctly 3/3.** So removing the illegal target is what works, and explaining is not.
"""
from typing import List, NamedTuple, Optional, Tuple

from ..formula.legal import Board
from . import gate3
from .effects import Operation


class Repaired(NamedTuple):
    """One correction, in the operator's terms."""
    rule: str                  # the gate-3 finding this answers
    operator: str
    was: Optional[str]
    now: Optional[str]
    why: str

    def __repr__(self):
        return f"{self.operator}: {self.was!r} -> {self.now!r} — {self.why}"


# ⇒ WHAT THIS MODULE OWNS. One name per rule it can answer, so a rule that grows a repair is
#   a line here and a function below — and a rule NOT in this set is guaranteed to reach the
#   model untouched. Mirrors gate 3's own `OWNS`, for the same reason: a repair nobody declared
#   is a repair nobody can audit.
OWNS = frozenset({"wrong-creation-source"})


def _sole_legal_target(step: Operation, table, board: Board) -> Optional[str]:
    """The ONE declared handle a creator could legally be aimed at, or None.

    None covers three different situations on purpose — no candidate, several candidates, and
    a manifest that constrains nothing — because the caller does the same thing in all three:
    leaves the step alone and lets the model answer.
    """
    made = gate3._made_kind(step.operator, board)
    if not made:
        return None
    sources = gate3._creation_sources(made, board)
    if not sources:
        return None                       # made from nothing — no target to be wrong about
    fits = [s.handle for s in table if s.row.kind in sources]
    return fits[0] if len(fits) == 1 else None


def repair(operations: List[Operation], findings: List[gate3.Illegal], table, board: Board
           ) -> Tuple[List[Operation], List[Repaired]]:
    """Apply every fix the manifest determines. Returns the operations and what was changed.

    The findings are gate 3's, unmodified — this reads them and never re-derives them, so the
    two can not drift into disagreeing about what is wrong.
    """
    fixed_at = {}
    notes: List[Repaired] = []
    for bad in findings:
        if bad.rule not in OWNS:
            continue
        target = _sole_legal_target(bad.step, table, board)
        if not target or target == bad.step.on:
            continue                      # ambiguous, or already right — decline, do not guess
        fixed_at[id(bad.step)] = target
        notes.append(Repaired(
            bad.rule, bad.step.operator, bad.step.on, target,
            f"the manifest allows exactly one source for a "
            f"{gate3._made_kind(bad.step.operator, board)}, and {target!r} is the only "
            f"declaration of that kind"))
    if not fixed_at:
        return operations, []
    return ([op._replace(on=fixed_at[id(op)]) if id(op) in fixed_at else op
             for op in operations], notes)
