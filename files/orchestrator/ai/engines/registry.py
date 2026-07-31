"""registry.py — what is mounted, and which of them claims a request.

The orchestrator's whole view of the system. It never learns what a VM is, what a snapshot
costs, or how a program is written — it knows a short list of names, one line each, and who
puts a hand up.

MOUNTING IS ADDITIVE AND CHEAP, which is the property the whole architecture rests on. The
old chat prompt carried every tool of every capability on every call: 53 schemas, 7,270
tokens, overflowing the model's context before the operator had typed anything (2026-07-31).
Here mounting an engine costs ONE LINE in the router's view, once, and the engine's own
surface is loaded only after it is chosen. Context stops growing with the system.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Engine, describe


class Registry:
    """The mount table. Deliberately small — it is a list and two questions."""

    def __init__(self):
        self._mounted: Dict[str, Engine] = {}

    HOST_ENGINES = frozenset({"medusa", "qemu"})

    def mount(self, engine: Engine) -> Engine:
        if not getattr(engine, "name", None):
            raise ValueError("an engine must have a name")
        if engine.name in self._mounted:
            raise ValueError(f"{engine.name} is already mounted")

        # THE HOST BOUNDARY, ENFORCED AT MOUNT TIME. Only Gorgon's own language and the thing
        # that makes machines may touch the host; everything else runs inside a VM. Checking
        # here rather than at call time means a misconfigured engine cannot be mounted at
        # all — a capability that reaches the internet does not get to fail safely on its
        # first request, it gets refused before it is listening.
        #
        # The NAME is the allowlist, deliberately, not a flag the engine sets about itself.
        # An engine declaring `runs_on = "host"` would be a capability granting itself the
        # host, which is the one thing this boundary exists to prevent.
        if getattr(engine, "runs_on", "guest") == "host" and engine.name not in self.HOST_ENGINES:
            raise ValueError(
                f"{engine.name} claims the host, and only {sorted(self.HOST_ENGINES)} may. "
                f"A guest engine's hands are injected by the host engine that made its "
                f"machine.")

        self._mounted[engine.name] = engine
        return engine

    def unmount(self, name: str) -> None:
        self._mounted.pop(name, None)

    def get(self, name: str) -> Optional[Engine]:
        return self._mounted.get(name)

    @property
    def engines(self) -> List[Engine]:
        # SORTED, so the router's view of the system is the same on every call and two runs
        # of one request cannot differ because a dict iterated differently.
        return [self._mounted[n] for n in sorted(self._mounted)]

    def claimants(self, request: str) -> List[Engine]:
        """Every engine that thinks it could answer. May be several; may be none.

        NONE IS A REAL ANSWER and must reach the operator as one — "nothing mounted can do
        that" is useful, where silently routing to the general engine and failing later is
        not.
        """
        return [e for e in self.engines if e.claims(request)]

    def menu(self) -> str:
        """The router's entire context. One line per engine."""
        return describe(self.engines)

    def sync(self, capabilities: Optional[List[str]] = None) -> Dict[str, Any]:
        """State from the engines a request actually implies — never from all of them.

        THE POINT OF THE `capabilities` ARGUMENT IS THAT IT IS USUALLY SHORT. Syncing every
        mounted engine on every prompt is the context overflow of 2026-07-31 one level up: it
        grows with the number of engines and nothing recomputes the budget, so mounting a
        fourth would silently degrade the other three. Passing None syncs everything and is
        for a bare `/sync` command, not for serving a request.
        """
        want = self.engines if capabilities is None else [
            e for e in self.engines if e.name in set(capabilities)]
        out: Dict[str, Any] = {}
        for e in want:
            try:
                w = e.world()
                out[e.name] = {"kinds": sorted((getattr(w, "kinds", {}) or {}).keys()),
                               "members": {k: len(v) for k, v in
                                           (getattr(w, "state", {}) or {}).items() if v}}
            except NotImplementedError:
                out[e.name] = {"kinds": [], "members": {}}
            except Exception as exc:
                # AN ENGINE THAT CANNOT BE SYNCED IS REPORTED, NOT SKIPPED. A missing engine
                # in the router's view reads as "it had nothing", which is a different claim
                # from "it could not be reached", and the second is the operator's problem.
                out[e.name] = {"error": f"{type(exc).__name__}: {exc}"}
        return out
