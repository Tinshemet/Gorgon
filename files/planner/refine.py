"""refine.py — rehearse the program, grade what it WOULD do, keep the best reading.

## THE HALF THE DESIGN NOTE PROMISED AND NOBODY BUILT

2026-07-28, on why the program regime was chosen over the tree:

> *"its artifact is complete and INERT before anything runs — so it can be graded at every
> granularity at once, CORRECTED, AND RESUBMITTED, at zero risk."*

Graded shipped 2026-08-06 (`dry_run.py`). **Corrected and resubmitted did not**, which is the
same shape as every other gap found that day: the detection half built, the loop half absent.

## WHAT IS ACTUALLY FREE HERE, AND WHAT IS NOT — do not overclaim this

    FREE      the dry run: `cover` already executes every placed tile on a scratch world,
              so the predicted end state is a by-product of planning
    FREE      grading it against the request — `dry_run.unaddressed`, no model
    NOT FREE  producing a BETTER reading. `cover` has already closed every gap `derive`
              can see, so by the time a program is planned there is no arithmetic left to
              correct. A different reading costs another draw.

**SO THE LOOP IS NOT "CORRECT THE PROGRAM". IT IS "REHEARSE SEVERAL READINGS AND KEEP THE
ONE THAT DOES WHAT WAS ASKED."** The draws cost model calls; the rehearsal and the judging
cost nothing, which is the right way round — you can afford to rehearse far more often than
you can afford to act.

## WHY THE PREDICTED EFFECT BEATS EVERY OTHER RANKING WE HAVE

`extract.best_of` ranks by what was DROPPED and by whether the plan's TEXT mentions a
clause's anchors. The ledger concedes that second one is thin: *"the plan mentions the token,
which is not the same as addressing the demand."* A rehearsal answers the stronger question —
**did the world move, and did it move where the request pointed** — and it is the only
evidence available that is not derived from the goals being judged.

## THE RATCHET, WHICH IS WHAT MAKES THIS SAFE

A candidate is only preferred when it grades STRICTLY BETTER. A reading that rehearses no
better than the first is not adopted, so the worst case is the behaviour that existed before
this file. **Selection may promote a reading; it may never invent one**, and it may never
promote one the referee likes less.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from planner import dry_run


class Rehearsal:
    """One reading, planned and run against a copy of the world. Nothing real is touched."""

    def __init__(self, goals: List[Dict[str, Any]], plan=None, program=None,
                 diff: Optional[Dict[str, Any]] = None,
                 faults: Optional[List[Dict[str, str]]] = None,
                 unsolvable: str = ""):
        self.goals = goals
        self.plan = plan or []
        self.program = program
        self.diff = diff or {}
        self.faults = faults or []
        self.unsolvable = unsolvable

    @property
    def inert(self) -> bool:
        """It plans, and rehearsing it moves NOTHING.

        NOT A FAULT BY ITSELF, and that distinction is the whole reason this is separate
        from `clean`. *"Make sure exactly 3 carry prod"* against a lab where 3 already do is
        a legitimate no-op: the world was already right and the correct program does nothing.
        Rung 11's false success is the same SHAPE — four pings, one true assertion, nothing
        moved — and the two are told apart by what the assertion is ABOUT, which is the
        invented-name guard's job and not this one's.

        So this is reported and never refused here. The gate decides.
        """
        return bool(self.plan) and not self.unsolvable and dry_run.empty(self.diff)

    @property
    def clean(self) -> bool:
        """Plannable, and nothing the rehearsal can PROVE wrong. `inert` is asked separately."""
        return bool(self.goals) and not self.unsolvable and not self.faults

    def rank(self):
        """Higher is better, compared lexicographically. Every key is computed, none judged.

        ORDER MATTERS AND IT IS ARGUED, not chosen:

          1  IT PLANS AT ALL. A reading the writer refuses is not a reading.
          2  IT DOES SOMETHING. An acting request whose rehearsal changes nothing is the
             exact shape of rung 11's false success — four pings, one true assertion about a
             machine nobody named, DONE reported, nothing stopped.
          3  FEWEST CLAUSES LEFT UNTOUCHED, by the world rather than by the plan's text.
          4  FEWER CALLS, last and only as a tie-break: between two readings that do the
             same thing, the cheaper is better, and it must never outrank doing the RIGHT
             thing — which is why it sits below every other key.
        """
        return (bool(self.plan) and not self.unsolvable,
                not dry_run.empty(self.diff),
                -len(self.faults),
                -len(self.plan))


def rehearse(goals: List[Dict[str, Any]], world, request: str = "") -> Rehearsal:
    """Plan `goals`, run them on a COPY, and report what they would do. Never touches `world`.

    THE COPY IS THE WRITER'S OWN. `cover` plans against `_scratch_of(world)` precisely so a
    lab whose `execute` reaches outside itself is never driven by planning — a bug found on
    2026-08-01 when planning a goal CREATED a machine. This asks for that same scratch back
    rather than making a second one, so the rehearsal is the plan's own arithmetic and cannot
    disagree with it.
    """
    from planner.ghost_writer import Unsolvable, as_program, cover
    before = dry_run.snapshot(world)
    predicted: List = []
    try:
        plan = cover(goals, world, temps=[], predicted=predicted)
    except Unsolvable as exc:
        return Rehearsal(goals, unsolvable=str(exc))
    except Exception as exc:
        return Rehearsal(goals, unsolvable=f"{type(exc).__name__}: {exc}")
    after = dry_run.snapshot(predicted[0]) if predicted else before
    change = dry_run.diff(before, after)
    faults: List[Dict[str, str]] = []
    if request:
        known = dry_run.identifiers(before, after)
        faults = dry_run.unaddressed(request, change, known)
    try:
        program = as_program(plan, goals, world, temps=[])
    except Exception:
        program = None
    return Rehearsal(goals, plan=plan, program=program, diff=change, faults=faults)


def best(candidates: List[List[Dict[str, Any]]], world, request: str = ""):
    """Rehearse every reading and return the one that best does what was asked.

    Returns `(rehearsal, all_rehearsals)` so a caller can report what it passed over — a
    selection nobody can inspect is a verdict, and this file's whole argument is that a
    verdict without its evidence is what we already had too much of.

    THE FIRST CANDIDATE WINS A TIE, always, so the same request against the same world
    yields the same program twice. Determinism is not a nicety here: it is what makes a
    failing run debuggable at all.
    """
    runs = [rehearse(goals, world, request) for goals in candidates if goals]
    if not runs:
        return Rehearsal([]), []
    top = max(range(len(runs)), key=lambda i: (runs[i].rank(), -i))
    return runs[top], runs


def report(r: Rehearsal) -> str:
    """What the rehearsal saw, in the operator's terms. Empty when it saw nothing wrong."""
    if r.unsolvable:
        return f"it cannot be planned: {r.unsolvable}"
    lines: List[str] = []
    if dry_run.empty(r.diff):
        lines.append("rehearsing it changes nothing in the lab")
    for fault in r.faults:
        clause = fault.get("clause") or ""
        lines.append(f"{fault.get('why', '')} — {clause!r}" if clause else fault.get("why", ""))
    return "; ".join(x for x in lines if x)
