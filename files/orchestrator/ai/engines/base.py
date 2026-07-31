"""base.py — what an ENGINE is. The mount contract, and nothing more.

An engine is a capability the orchestrator can route to: the executor drives machines,
Medusa writes and runs Gorgon's own programs, an OpenCV engine would answer questions about
footage. The orchestrator does not know what any of them do — it knows who is mounted, who
claims a request, and what to do when one asks for help.

NOT `planner/engine.py`. That is the POLICY BUNDLE the score engine threads (gate, verify,
watchdog, killswitch); it is a bag of dependencies, not a mounted capability. Two different
things wearing one word, and the older one keeps the name it has earned in a hundred call
sites.

THE CONTRACT IS TWO THINGS, because that is all the ghost writer ever needed:

    a MANIFEST   kinds, keys, attributes, and which tool creates / deletes / sets / unsets
                 each one. Postconditions are DERIVED from it — never written twice.
    an ADAPTER   `seams()` to read the world, `execute()` to act on it.

Proven 2026-08-01: a kitchen became mountable in ~25 lines of manifest and no code, and the
same writer planned against it. That is what makes "every engine must be Medusa-compatible"
a morning's work rather than a tax — and it is why this file is short. A large mount contract
would be a claim that engines are hard to write; they are not.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class Engine:
    """A mounted capability. Subclass, or duck-type — nothing here checks a base class."""

    name: str = "unnamed"
    # ONE LINE, and it is the only thing the router ever reads about this engine. Written
    # for a model choosing between four options, not for a developer: say what requests it
    # can answer, in the words an operator would use.
    description: str = ""
    # Which intents this engine can serve. An engine that only ANSWERS declares `fetch`; one
    # that acts declares `achieve`. The router uses it to pick a REGIME, not just an engine.
    intents: Tuple[str, ...] = ("fetch",)

    @property
    def manifest(self) -> Dict[str, Any]:
        """The kinds this engine deals in. `{}` means it has no world to plan over."""
        return {}

    def world(self):
        """The thing to plan against — anything carrying `kinds`, `seams` and `execute`."""
        raise NotImplementedError

    def claims(self, request: str) -> bool:
        """Could this engine answer that request? A CHEAP, HONEST GUESS.

        Deliberately not a promise. The router asks every mounted engine and a model breaks
        ties; the real answer comes from trying, and `Unsolvable` is how an engine says no
        after looking properly. An engine that over-claims costs one failed attempt; one
        that under-claims is never tried at all, so when in doubt, claim.
        """
        return False

    def run(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        """Do the work. Returns `{ok, calls, findings, promote?, why}`.

        `promote` is the engine ASKING for a regime it does not have — never taking one.
        The orchestrator owns the budget, so only the orchestrator can grant it.
        """
        raise NotImplementedError


def describe(engines: List[Engine]) -> str:
    """The router's entire view of the system. One line per engine.

    THIS IS WHY CONTEXT STOPS GROWING. The old chat prompt carried 53 tool schemas — 7,270
    tokens — on every call, and mounting anything made every call more expensive. Here a new
    engine costs ONE LINE, once, and the engine's own surface is loaded only after it has
    been chosen. Blinders stop being a mechanism to build: there is nothing to withhold
    because nothing else was ever loaded.
    """
    return "\n".join(f"  {e.name}: {e.description}" for e in engines)
