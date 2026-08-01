"""orchestrator.py — route a request to an engine, run a session, answer.

    user -> [ /sync -> route -> IN-SESSION: engine <-> orchestrator, until done ] -> answer

THE OPERATOR SEES THE ENDS, NEVER THE MIDDLE. Everything between the prompt and the answer is
the IN-SESSION: the engine reports what it could and could not close, the orchestrator decides
whether to grant more, and that repeats — a tree — until the work is done or abandoned. The
record of it comes back under `in_session` so a wrong result can be traced to the stage that
caused it, and so that nothing user-facing renders it by accident.

It knows three things and none of them are domain knowledge: who is mounted, who claims a
request, and what to do when an engine asks for help. It never learns what a VM is, what a
snapshot costs, or how a program is written.

WHERE THE MODEL APPEARS — three times, never in the middle:
    routing        which engine (a closed choice over a short list)
    translation    English -> components, through the channel
    reporting      findings -> English

Between those points nothing probabilistic touches the work. That is the entire architecture,
and it is why the router can be a small model with a 71-token view of the system: it decides
WHO and HOW HARD, never HOW.

THE ORCHESTRATOR OWNS THE BUDGET, which is the reason promotion is a request rather than an
act. An engine asked whether it would like more resources will always say yes.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .channel import Channel
from .registry import Registry
from .session import Session


class Orchestrator:
    """One registry, one channel, and the loop between them."""

    def __init__(self, registry: Registry, channel: Optional[Channel] = None,
                 route: Optional[Callable] = None, budget: Optional[int] = None,
                 narrate: Optional[Callable] = None):
        self.registry = registry
        self.channel = channel or Channel()
        self.budget = budget
        # THE REPORTER'S CHANNEL, separate from the extractor's and deliberately so. It is
        # handed findings and NOTHING ELSE — never the request, never the program — because a
        # model that can see what was asked writes a fluent answer to the question, and one
        # that sees only what was found can describe the evidence. Absent, findings come back
        # raw and the caller narrates them or does not.
        self._narrate = narrate
        # `route(request, menu, engines) -> name | None`. Injected because it is the one
        # decision a model makes here, and injecting it means the whole orchestrator is
        # testable with a function that picks the first claimant — the same discipline that
        # let the ghost writer be proven with hand-written goals.
        self._route = route or self._first_claimant

    @staticmethod
    def _first_claimant(request, menu, engines):
        return engines[0].name if engines else None

    def sync(self, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        return self.registry.sync(capabilities)

    def handle(self, request: str, intent: str = "ensure",
               components: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """One request, start to finish.

        `components` may be supplied directly — that is the stubbed channel, and it is how
        every result so far was measured. When absent the channel is asked, which is the only
        place English becomes structure.
        """
        # HOST ENGINES ONLY. Medusa turns the prompt into action; QEMU provides the box.
        # A guest capability — a crawler, a vision engine — is something a Medusa PROGRAM
        # calls once it has a machine, never somewhere the orchestrator sends a request.
        claimants = self.registry.claimants(request)
        if not claimants:
            # NOBODY CLAIMS IT, and that reaches the operator as an answer rather than a
            # crash. "Nothing mounted can do that" is useful; routing to the general engine
            # and failing three steps later is not.
            return {"outcome": "UNCLAIMED", "engine": None, "regime": None,
                    "why": "no mounted host engine claims this request",
                    "mounted": [e.name for e in self.registry.engines],
                    "capabilities": [p.name for p in self.registry.capabilities()]}

        chosen = self._route(request, self.registry.menu(), claimants)
        engine = self.registry.get(chosen) if chosen else None
        if engine is None:
            return {"outcome": "UNROUTED", "engine": None, "regime": None,
                    "why": f"the router named {chosen!r}, which is not mounted",
                    "mounted": [e.name for e in self.registry.engines]}

        session = Session(request, engine, intent=intent, budget=self.budget)
        session.record(f"routed to {engine.name} · regime {session.regime}")
        # SYNC ONLY WHAT WAS ROUTED TO. The flow says "/sync then route", and doing it in
        # that order would ask EVERY mounted engine for state on EVERY prompt — the context
        # overflow of 2026-07-31 one level up, growing with the number of engines while
        # nothing recomputes the budget. Syncing the CHOSEN engine costs one lookup and
        # answers the only question that matters: what is actually there, for the engine
        # about to act. The capability ledger is what would let the order be reversed safely.
        session.record(f"synced {engine.name}: "
                       f"{self.registry.sync([engine.name]).get(engine.name)}")

        if components is None:
            answer = self.channel.ask(request, engine.world())
            session.record(f"translated by {answer.source}: {len(answer.components)} goal(s)")
            if not answer:
                # A REQUEST NOBODY COULD TRANSLATE IS NOT A FAILED REQUEST — it is one that
                # never became a request. Naming the stage matters: this is the front seam,
                # and confusing it with an engine failure is how a day gets spent debugging
                # the wrong half.
                return session.close("UNTRANSLATED", answer.why)
            components = answer.components

        result = engine.run(components, session)
        session.calls = result.get("calls") or []

        # THE PROMOTION REQUEST, heard here and nowhere else — and then ACTED ON.
        #
        # This used to record the promotion and RE-RUN THE SAME ENGINE WITH THE SAME
        # COMPONENTS, which fails identically by construction. A recorded-but-inert
        # escalation is worse than none: the log says "promoted to tree" and nothing
        # happened, which is the shape of every defect this project has spent a week on.
        #
        # What a tree session actually is: the engine could not close a gap, so the gap goes
        # ON THE CHANNEL as its own question. Not the original request — that was already
        # translated, and asking it again gets the same answer. The GAP is a different and
        # much smaller question: "nothing reaches COUNT(SELECT vm WHERE ...) — what would?"
        while result.get("promote"):
            to = result["promote"]
            if not session.promote(to, result.get("why", "")):
                return session.close("PROMOTION_DECLINED", result.get("why", ""))
            if not session.rounds_left():
                return session.close("ABANDONED", "the gap did not close in the rounds "
                                                  "this session was allowed")
            gap = {"gap": result.get("why", ""), "request": request,
                   "have": components}
            answer = self.channel.ask(gap, engine.world())
            session.record(f"in-session asked about the gap -> {answer.source}: "
                           f"{len(answer.components)} component(s)")
            if not answer:
                # NOBODY COULD ANSWER THE GAP, so the session ends saying so rather than
                # looping. An escalation with no answerer behind it is a slower refusal, and
                # naming it as one is the only honest close.
                return session.close("UNMET", f"no answer for the gap: "
                                              f"{result.get('why', '')}")
            # THE NEW COMPONENTS ARE ADDED, NOT SUBSTITUTED. The original goals are still
            # what was asked; the answer is what unblocks them, and dropping the first would
            # quietly change the request.
            components = list(components) + [c for c in answer.components
                                             if c not in components]
            result = engine.run(components, session)
            session.calls = result.get("calls") or []

        if not result.get("ok"):
            return session.close("UNMET", str(result.get("why") or ""))

        session.findings = result.get("findings") or []
        out = session.close("DONE", result.get("why") or "")
        out["rendered"] = result.get("rendered", "")
        out["grounded"] = result.get("grounded")
        if self._narrate is not None:
            from . import reporter as _reporter
            said = _reporter.report(session.findings, self._narrate)
            out["answer"] = said["answer"]
            # THE VERDICT TRAVELS WITH THE SENTENCE. An answer whose claims are not supported
            # is still returned — suppressing it leaves silence where there was an answer —
            # but it never arrives looking clean.
            out["answer_grounded"] = said["grounded"]
            out["answer_unsupported"] = said["unsupported"]
        return out
