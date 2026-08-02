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
# WAIT — NOT NOW, ASK ME AGAIN. The node goes to the back of the queue and is re-offered
# after the others have had their turn.
#
# WHY A THIRD ANSWER AND NOT A REFUSAL. Until this existed a node could only run, split, or
# die, so anything not ready YET had to be treated as something that would never be ready.
# That is wrong wherever a record precedes the object it names — a machine that has been
# created and is not up, a snapshot still being written, an answer the channel has been asked
# for and has not given. Refusing those loses work that was about to become possible; running
# them acts on something that is not there.
#
# THE WAIT IS NOT A SLEEP. A yielded node is RE-PLANNED against the world as it is when it
# comes round again, so "waiting" means exactly "the plan may be different next time" — which
# is the only kind of waiting that can end. An in-session that blocked would be holding the
# budget hostage on somebody else's clock.
YIELD = "yield"


class Step:
    """One thing an engine wants a verdict on before it acts.

    `kind` is what the engine PROPOSES; the orchestrator may answer with something else. That
    asymmetry is the point — an engine that could only be told "yes" would be deciding.
    """

    def __init__(self, kind: str, node: Any, why: str = "", cost: int = 1,
                 divisible: bool = True, destroys: Optional[List] = None,
                 acts: Optional[List] = None):
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
        # WHAT IT WOULD DESTROY IF GRANTED — [(tool, args), ...], empty when nothing.
        #
        # THIS IS WHY THE PROTOCOL ASKS PER NODE AT ALL. The claim was that "a destructive
        # node gets a verdict of its own rather than riding in on the back of a program
        # granted as a whole" — and until this field existed the step said nothing about
        # which nodes those were, so the claim was unenforceable by anyone reading it.
        #
        # MEASURED, on the fuzz corpus: a request that CANNOT be satisfied ("every machine
        # can reach the others, and end up with exactly one machine") is refused by the
        # whole-program grain WITHOUT TOUCHING ANYTHING, because `cover` reviews an inert
        # artifact before it runs. The opened grain reaches the same refusal having already
        # deleted two machines, because it acts as it goes. That is not a defect in the
        # opened grain; it is what the ladder means by "gravity points down", and the only
        # place to catch it is here, before the verdict.
        self.destroys = list(destroys or ())
        # WHAT IT WOULD CHANGE IF GRANTED — [(tool, args), ...], and `destroys` is a subset of
        # it. DECLARED BY THE ENGINE for the same reason `cost` and `divisible` are: the engine
        # has already planned this node, so it knows, and the alternative is the in-session
        # inferring effects from a node whose shape differs per engine (a whole program here,
        # one tool call there).
        #
        # IT IS WHAT MAKES THE INTENT LADDER ENFORCEABLE ABOVE THE LANGUAGE. `intent.violations`
        # refuses a PROGRAM that reaches above its rung, which covers Medusa and says nothing
        # about the executor engine — the floor, routed to FIRST, declaring `intents =
        # ("fetch",)` and running `delete_vm` on request. One field, one gate, both engines.
        self.acts = list(acts if acts is not None else self.destroys)

    def __repr__(self) -> str:
        return (f"<Step {self.kind} cost={self.cost}"
                f"{'' if self.divisible else ' atomic'}"
                f"{f' acts={len(self.acts)}' if self.acts else ''}"
                f"{f' destroys={len(self.destroys)}' if self.destroys else ''}"
                f" {str(self.node)[:48]}>")


class Publish:
    """WHAT AN ENGINE SUBMITS UPWARD. The other half of the protocol.

        down:  Step     "this node — run it, or decompose it?"     -> Verdict
        up:    Publish  "here is something I found / claim / made"  -> kept, or forwarded

    IT DOES NOT PRINT. That is the whole distinction: an engine PUBLISHES a claim and the
    orchestrator decides whether to keep it internal or move it to the operator, because the
    orchestrator is the thing that owns the boundary — it already separates `in_session` from
    `answer` for exactly this reason. An engine that wrote to the operator directly would be
    deciding what the operator sees, which is the one thing the in-session exists to prevent.

    WHY THIS REPLACES READING THE WORLD'S LEDGER. Findings used to travel up implicitly: the
    orchestrator reached into the world and took what it found there. That works while an
    engine's world HAS a ledger and quietly returns nothing when it does not — a second
    engine would have had to grow one to be heard. A publication is a thing an engine SAYS,
    so any engine can say it, including one whose world is somebody else's API.

    A PUBLICATION NEEDS NO VERDICT. Submitting is not asking, so `drive` records it and lets
    the engine carry on — an engine that had to wait for permission to SPEAK would be
    blocked on the orchestrator for something the orchestrator cannot refuse.
    """

    def __init__(self, what: str, value: Any = None, why: str = ""):
        self.what = what
        self.value = value
        self.why = why

    def as_finding(self) -> Dict[str, Any]:
        """The shape the reporter is handed. A publication IS a finding once it is forwarded;
        keeping two vocabularies for one thing is how the two drift."""
        out: Dict[str, Any] = {"fact": self.what, "value": self.value}
        if self.why:
            out["why"] = self.why
        return out

    def __repr__(self) -> str:
        return f"<Publish {self.what}={str(self.value)[:40]}>"


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


def _above_authority(step: Step, session) -> Optional[str]:
    """Why this step exceeds what the operator granted, or None.

    ONE RULE, BOTH ENGINES, and it is the ladder's own: `fetch` reads, `ensure` judges, and
    only `achieve` may change anything. `intent.permits` is the single authority for that —
    asking it here rather than restating it means a rung added to the ladder is enforced in
    the in-session without an edit.

    NO INTENT SUPPLIED REFUSES NOTHING, which is `intent.violations`' documented meaning of
    absence and not a loophole: the safe default belongs where the operator is ASKED — the
    front seam — because a default buried here would be a fourth place that decides what
    somebody meant.
    """
    if not step.acts:
        return None
    granted = getattr(session, "intent", None)
    if granted is None:
        return None
    from planner.ir import intent as _intent
    if _intent.permits(granted):
        return None
    tools = sorted({t for t, _ in step.acts})
    return (f"a {granted} may not change the lab, and this would: "
            f"{', '.join(tools[:3])}"
            f"{f' and {len(tools) - 3} more' if len(tools) > 3 else ''}. "
            f"Say `achieve:` if you meant to act.")


def drive(engine, components: List[Dict[str, Any]], session, decide) -> Dict[str, Any]:
    """Run an engine's in-session to completion. Returns its final result.

    `decide(step, session) -> Verdict` is the orchestrator's judgement, injected — so the
    whole loop is testable with a function that always says RUN, which is exactly how the
    ghost writer was proven before any model touched it.

    AN ENGINE THAT OFFERS NO STEPS RUNS UNASKED, AND THAT IS THE PRICE OF THIS FALLBACK.
    It exists so an engine is not FORCED to implement a generator — a pure reader has nothing
    to ask about. But an engine that ACTS and offers no in-session acts with no verdict, no
    budget check and no dry run, which was found the hard way: the executor engine shipped
    without `steps()` and `plan --dry` created a machine on the real lab while claiming to
    preview one.

    So the rule is not "the floor needs no exchange" — it is that ASKING IS THE PRICE OF
    ACTING, whatever regime you are in. An engine that only answers may skip it.
    """
    steps = getattr(engine, "steps", None)
    if not callable(steps):
        return engine.run(components, session)

    gen = steps(components, session)
    verdict: Optional[Verdict] = None
    try:
        while True:
            step = gen.send(verdict) if verdict is not None else next(gen)
            if isinstance(step, Publish):
                # SUBMITTED, NOT ASKED. The engine keeps its place and carries on; whether
                # this reaches the operator is decided later, by the thing that owns the
                # boundary between the middle and the ends.
                session.publish(step)
                verdict = None
                continue
            if not session.afford(step.cost):
                # THE BUDGET REFUSES BEFORE THE ACT, not after. An engine told "yes" and then
                # billed for it would have spent money nobody agreed to.
                verdict = Verdict(STOP, f"budget: {step.cost} more than this session has")
                session.record(f"step {step.kind} REFUSED — {verdict.why}")
                continue
            trespass = _above_authority(step, session)
            if trespass:
                # AUTHORITY REFUSES BEFORE THE ACT, exactly as the budget does, and BEFORE the
                # decider is consulted — because what the operator granted is not a policy the
                # orchestrator gets to weigh. A gate the decider could overrule would make the
                # intent ladder advisory, and `intent.py` is explicit that it is enforced.
                verdict = Verdict(STOP, trespass)
                session.record(f"step {step.kind} REFUSED — {trespass}", level="warn")
                continue
            verdict = decide(step, session)
            session.record(f"step {step.kind} -> {verdict.action}"
                           + (f" ({verdict.why})" if verdict.why else ""))
    except StopIteration as done:
        # The generator's return value is the engine's result. `StopIteration.value` is the
        # only way a generator says "finished, and here is what came of it".
        return done.value or {"ok": False, "why": "the engine returned nothing"}
