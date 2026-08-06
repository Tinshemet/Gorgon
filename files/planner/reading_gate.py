"""reading_gate.py — did we understand the request? Graded, logged, and answerable.

## NOT `ir/gate.py`, AND THE SPLIT IS THE SAME ONE THAT FILE ALREADY DRAWS

    ir/gate.py       should this authored PROGRAM be allowed to run?   — form and risk
    reading_gate.py  did we READ THE REQUEST RIGHT?                    — meaning

A program can be perfectly formed, perfectly safe, and answer a question nobody asked. That
is `DONE_BUT_FALSE`, and no gate about form can see it.

## WHY A GATE AND NOT A BETTER TRANSLATION

The operator, 2026-08-06: *"an autonomous translation is worthless if it's wrong... it can
make it measurable because we see what the gate catches."*

**AND THE ARGUMENT WAS ALREADY WRITTEN IN OUR OWN CONFIG.** `chat/config.json` explains why
the engine path defaults OFF: *"the front seam scores 17/39 literal and 6/39 paraphrase on
the production probe, and the failure is not refusal but DONE_BUT_FALSE."* The chat path
ships because it is gated (`chat/gates/context.py`); the engine path does not because it is
not. **The difference between the path that ships and the path that does not is a gate, not
a better model** — and nobody had drawn that conclusion.

So the translation does not have to be right. It has to be CAUGHT.

## AND THE GATE IS THE MEASUREMENT

The ladder needs a hand-written checker per rung, so it can only ever measure fourteen
requests. This needs no oracle: it fires or it does not, on every request an operator
actually makes. **What it catches, and how often, is the metric** — and unlike a benchmark it
gets better as the gate gets better rather than as somebody authors more truth in advance.

## THE GRADING IS `chat/gates/context.py`'s, AND SO IS ITS HARDEST LESSON

That gate has run in production for a long time and its code carries the finding this seam
re-learned on 2026-08-06 at the cost of a measurement:

> *"Hallucinated required field — ask the user directly (the model ignores the hint if we
> just re-prompt it)."*

Re-prompting a model with its own fault was measured here the same day: told in as many words
that it had invented the name `unresponsive`, it returned the same class of error. **So an
invented value is ASKED, never re-prompted.** A misread shape may be re-planned; a value the
operator never gave can only come from the operator.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from planner import dry_run, refine

# THE VERDICTS, and they are graded rather than binary because the FAULTS are. Refusing
# everything the gate notices would throw away correct programs; passing everything is what
# we have now.
PROCEED = "proceed"          # nothing caught — run it
ASK = "ask"                  # a specific question only the operator can answer
REFUSE = "refuse"            # nothing to ask about; it cannot be planned at all


class Verdict:
    """What the gate decided, WHY, and what it would ask. Always inspectable.

    `caught` is the machine-readable reason code and it is what gets counted. A gate whose
    firings cannot be tallied by cause is a gate nobody can improve.
    """

    def __init__(self, outcome: str, caught: str = "", question: str = "",
                 detail: str = ""):
        self.outcome = outcome
        self.caught = caught
        self.question = question
        self.detail = detail

    def __bool__(self) -> bool:
        return self.outcome == PROCEED

    def __repr__(self) -> str:
        return f"<Verdict {self.outcome}{' ' + self.caught if self.caught else ''}>"


def judge(request: str, rehearsal: "refine.Rehearsal",
          lost: Optional[List[str]] = None,
          warnings: Optional[List[str]] = None) -> Verdict:
    """Grade one reading. Deterministic, no model call, before anything runs.

    ORDER IS MOST-SPECIFIC FIRST, so the operator is told the most useful thing rather than
    the first true thing.
    """
    lost = [str(x).strip() for x in (lost or []) if str(x).strip()]

    # 0 — THE ASSISTANT SPOKE. A contradiction or a high-stakes flag is about DANGER rather
    # than about meaning, so it outranks everything below: the operator should be asked
    # before a program that force-stops or deletes disks is run, whatever else is true of it.
    if warnings:
        return Verdict(ASK, "assistant",
                       question=" ".join(str(w) for w in warnings),
                       detail="; ".join(str(w) for w in warnings))

    # 1 — IT CANNOT BE PLANNED. There is no question to ask: the writer has already proven
    # no sequence of tools reaches this, so asking the operator to choose between readings
    # of something unreachable wastes the one interruption budget we have.
    if rehearsal.unsolvable:
        return Verdict(REFUSE, "unplannable", detail=rehearsal.unsolvable)

    # 2 — SOMETHING WAS INVENTED OR DROPPED AT THE SEAM. `to_goals` already computed the
    # reason in the operator's terms; this asks it rather than paraphrasing it, because a
    # question the operator has to decode is a question they will answer wrongly.
    if lost:
        return Verdict(ASK, "invented-or-dropped",
                       question=("I could not read part of this. "
                                 + "; ".join(lost) + ". What did you mean?"),
                       detail="; ".join(lost))

    # 3 — ⇒ `clause-untouched` WAS A GATING RULE AND IS NOW ONLY A REPORT. WITHDRAWN
    #     2026-08-06 ON THE FIRST WIRING, which is exactly what wiring it was for.
    #
    # It accused 2 of 13 known-good rungs:
    #
    #     rung  9  "make sure n1, n2 and n3 can all ping each other"
    #              -> nothing mentions 'n1'. The program PROBES, and a probe records a
    #                 FINDING rather than changing a record — invisible to a registry diff.
    #     rung 10  "clone golden into 3 new vms"
    #              -> nothing mentions 'golden'. Correct, and irrelevant: golden is the
    #                 SOURCE. A clause naming a thing to be READ is not a clause about a
    #                 thing to be CHANGED, and nothing here can tell those apart.
    #
    # THE PROBE HALF IS FIXED (`dry_run.observations`); THE SOURCE HALF IS NOT, and no rule
    # that cannot distinguish a source from a target belongs in front of a run. A gate that
    # refuses correct programs is worse than no gate — it teaches the operator to ignore it.
    #
    # THE SIGNAL IS KEPT ON THE REHEARSAL where a caller can read it, because it is real
    # evidence about a reading; what it is not is sufficient to STOP one.

    # 4 — IT WOULD DO NOTHING. Deliberately a QUESTION and never a refusal: "make sure
    # exactly 3 carry prod" against a lab where 3 already do is a correct program that
    # changes nothing, and it is indistinguishable from rung 11's false success by shape
    # alone. The operator settles it in one word; no mechanism here can.
    if rehearsal.inert:
        return Verdict(ASK, "inert",
                       question=("Running this would change nothing in the lab. Either it is "
                                 "already as you asked, or I have misread you — which?"),
                       detail="the rehearsal moved nothing")

    return Verdict(PROCEED)


def tally(verdicts: List[Verdict]) -> Dict[str, int]:
    """How often the gate fired and for what — THE MEASUREMENT.

    No oracle anywhere in it, which is the point: this counts real requests rather than the
    fourteen somebody wrote a checker for.
    """
    out: Dict[str, int] = {"total": len(verdicts), PROCEED: 0, ASK: 0, REFUSE: 0}
    for v in verdicts:
        out[v.outcome] = out.get(v.outcome, 0) + 1
        if v.caught:
            out[v.caught] = out.get(v.caught, 0) + 1
    return out
