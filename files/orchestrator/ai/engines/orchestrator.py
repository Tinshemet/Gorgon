"""orchestrator.py — route a request to an engine, run a session, answer.

    user -> /sync -> which engine -> in-session -> [promote?] -> findings -> answer

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
                 route: Optional[Callable] = None, budget: Optional[int] = None):
        self.registry = registry
        self.channel = channel or Channel()
        self.budget = budget
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

        # THE PROMOTION REQUEST, heard here and nowhere else.
        if result.get("promote"):
            to = result["promote"]
            if session.promote(to, result.get("why", "")):
                result = engine.run(components, session)
                session.calls = result.get("calls") or []
            else:
                return session.close("PROMOTION_DECLINED", result.get("why", ""))

        if not result.get("ok"):
            return session.close("UNMET", str(result.get("why") or ""))

        session.findings = result.get("findings") or []
        out = session.close("DONE", result.get("why") or "")
        out["rendered"] = result.get("rendered", "")
        out["grounded"] = result.get("grounded")
        return out
