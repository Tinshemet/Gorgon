"""insession.py — the back-and-forth an operator never sees.

    engine:        here is a node. DECOMPOSE it, or RUN it?
    orchestrator:  run it / decompose it / stop
    ...until the work is done or abandoned.

WHY THE ORCHESTRATOR IS ASKED PER NODE AND NOT ONLY ON FAILURE. An earlier version exchanged
only when an engine got stuck, which made the orchestrator an arbiter of COLLAPSES. But it is
the thing that owns the budget, the gates and the operator's consent, and those are decisions
about EVERY act, not only the ones that go wrong. A destructive node needs a verdict before it
runs, not after the engine has already decided to run it.

IT IS ALSO WHAT SEPARATES THE REGIMES, and that separation is now mechanical rather than
described:

    TRANSLATION  the ghost writer plans the WHOLE request, so the in-session is ONE exchange:
                 "here is the program — run it?" One question, one verdict, done.
    TREE         the goal is opened as nodes and each one is offered separately, so the
                 in-session is MANY exchanges. That is precisely why promotion COSTS: a tree
                 is not a cleverer regime, it is a more expensive conversation.

THE ENGINE PROPOSES; THE ORCHESTRATOR DISPOSES. An engine may not run a node it was not
granted, and may not decompose one it was told to run. Written as a generator because that is
what the shape actually is — the engine keeps its place while somebody else decides.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# What an engine can be asked to do with a node, and what an orchestrator can answer.
RUN = "run"
DECOMPOSE = "decompose"
STOP = "stop"


class Step:
    """One thing an engine wants a verdict on before it acts.

    `kind` is what the engine PROPOSES; the orchestrator may answer with something else. That
    asymmetry is the point — an engine that could only be told "yes" would be deciding.
    """

    def __init__(self, kind: str, node: Any, why: str = "", cost: int = 1,
                 divisible: bool = True):
        self.kind = kind
        self.node = node
        self.why = why
        # WHAT IT WILL COST IF GRANTED, declared before the verdict rather than discovered
        # after. A budget holder that learns the price afterwards is not holding a budget.
        self.cost = cost
        # WHETHER THERE IS ANYTHING FINER INSIDE IT — DECLARED, NOT GUESSED. The engine has
        # already planned this node, so it knows; making the orchestrator ask and then be
        # told no is the inference this project keeps replacing with a declaration. A decider
        # that reads this never asks for a split that cannot exist.
        self.divisible = divisible

    def __repr__(self) -> str:
        return (f"<Step {self.kind} cost={self.cost}"
                f"{'' if self.divisible else ' atomic'} {str(self.node)[:48]}>")


class Verdict:
    """What the orchestrator answers. `stop` ends the in-session.

    DELIBERATELY NOT FALSY. An earlier version gave this a `__bool__` returning False on STOP,
    which read well — `if not verdict: stop` — and immediately caused a bug: `verdict.why if
    verdict else "no verdict given"` discarded the operator's actual reason and reported that
    none was given. A DECLINE AND AN ABSENCE ARE DIFFERENT THINGS, and an object that answers
    "am I here?" with "no" whenever it says no will keep collapsing the two. Ask
    `verdict.action` — it is one word longer and cannot lie.
    """

    def __init__(self, action: str, why: str = ""):
        self.action = action
        self.why = why

    def __repr__(self) -> str:
        return f"<Verdict {self.action} {self.why[:40]}>"


def drive(engine, components: List[Dict[str, Any]], session, decide) -> Dict[str, Any]:
    """Run an engine's in-session to completion. Returns its final result.

    `decide(step, session) -> Verdict` is the orchestrator's judgement, injected — so the
    whole loop is testable with a function that always says RUN, which is exactly how the
    ghost writer was proven before any model touched it.

    A GENERATOR THAT DOES NOT OFFER STEPS IS NOT AN ERROR. An engine may simply do its work
    and return, and that is the tool regime: one call, one answer, no exchange. The protocol
    has to accommodate the floor or it stops being the floor.
    """
    steps = getattr(engine, "steps", None)
    if not callable(steps):
        return engine.run(components, session)

    gen = steps(components, session)
    verdict: Optional[Verdict] = None
    try:
        while True:
            step = gen.send(verdict) if verdict is not None else next(gen)
            if not session.afford(step.cost):
                # THE BUDGET REFUSES BEFORE THE ACT, not after. An engine told "yes" and then
                # billed for it would have spent money nobody agreed to.
                verdict = Verdict(STOP, f"budget: {step.cost} more than this session has")
                session.record(f"step {step.kind} REFUSED — {verdict.why}")
                continue
            verdict = decide(step, session)
            session.record(f"step {step.kind} -> {verdict.action}"
                           + (f" ({verdict.why})" if verdict.why else ""))
    except StopIteration as done:
        # The generator's return value is the engine's result. `StopIteration.value` is the
        # only way a generator says "finished, and here is what came of it".
        return done.value or {"ok": False, "why": "the engine returned nothing"}
