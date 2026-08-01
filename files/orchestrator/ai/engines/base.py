"""base.py — what an ENGINE is. The mount contract, and nothing more.

AN ENGINE RUNS THE HOST. Medusa writes and runs Gorgon's own programs; the executor drives
machines; you can build your own — an FSMO-style role, a scheduler, whatever the host
genuinely needs. Engines are MOUNTED and the orchestrator routes to them.

A PACKAGE IS THE OTHER THING (see `ai/packages/`): a capability that runs INSIDE a world
engine — crawling, vision, scanning. Packages are LOADED, never mounted, never routed to.

THE BOUNDARY IS STRUCTURAL RATHER THAN CHECKED, and that is the whole point. An earlier
version had engines carry `runs_on = "host" | "guest"` and the registry refuse a guest
claiming the host. It worked, and it made safety a CHECK — forgettable, subclassable, true on
one path and not another. A package simply has no mount method, so a capability that reaches
the internet cannot get the host because it is not the kind of object that has one.

The orchestrator does not know what any engine does — it knows who is mounted, who claims a
request, and what to do when one asks for help.

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
    #
    # THIS IS WHAT THE ENGINE CAN DO, NEVER WHAT IT MAY. The two were confused for as long as
    # this line existed alone: the executor declares `fetch` and ran `delete_vm` on request,
    # because nothing read the declaration as a limit and nothing else limited it either. What
    # the OPERATOR granted is `session.intent`, and it is enforced in `insession.drive` against
    # the `acts` a step declares — so AN ENGINE WITH A `steps()` GENERATOR MUST DECLARE WHAT
    # EACH STEP WOULD CHANGE. An undeclared step is taken at its word, exactly as an undeclared
    # `cost` is.
    intents: Tuple[str, ...] = ("fetch",)

    # CAN THIS ENGINE WRITE A PROGRAM DOWN WITHOUT RUNNING IT? An authoring request — "keep
    # this as a snippet" — needs a plan as an ARTIFACT, and an engine that inverts one goal
    # into one tool call has nothing to hand over. Declared rather than discovered: the
    # orchestrator called `engine._plan` on whichever engine the router picked, and the router
    # picks the FLOOR first, so the first real authoring request died on
    # `'ExecutorEngine' object has no attribute '_plan'`.
    authors: bool = False

    # Packages this engine has loaded. Their kinds join the engine's manifest and their
    # tools become callable by a program the engine runs — with execution staying the
    # ENGINE'S, so a package never holds hands of its own.
    packages: Tuple = ()

    @property
    def manifest(self) -> Dict[str, Any]:
        """The kinds this engine deals in, its packages' included."""
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

        DERIVED FROM THE MANIFEST'S OWN NOUNS, HERE, ONCE. `kinds.<k>.nouns` already records
        what an operator calls these things — "machine", "box", "subnet" — and it is the same
        list the extractor's schema is built from. Two engines had each hand-rolled this,
        differently, and a third would have made it three: a new engine gets claiming for
        free from the manifest it already had to write, which is the whole argument for the
        mount contract being two things.

        AN ENGINE MAY STILL OVERRIDE, and Medusa does — the general fallback claims anything
        about kinds it knows, on purpose. Overriding to WIDEN is a decision worth writing
        down; re-implementing the same noun match is not.
        """
        words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
        for kind, spec in (self.manifest or {}).items():
            names = {kind, *(spec.get("nouns") or ())}
            if names & words or {f"{n}s" for n in names} & words:
                return True
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
