"""base.py — what a PACKAGE is. Kinds and tools that run INSIDE a world engine.

    ENGINE    a HOST-level capability. Medusa is one, the executor is one, and you can
              build your own — an FSMO-style role, a scheduler, whatever the host needs.
              Engines are MOUNTED and the orchestrator routes to them.

    PACKAGE   a capability that runs INSIDE a world engine: crawling, vision, scanning.
              Packages are LOADED by an engine, never mounted, and never routed to.

THE BOUNDARY IS STRUCTURAL, NOT A FLAG. An earlier version of this had engines carry
`runs_on = "host" | "guest"` and the registry refuse a guest claiming the host. That worked,
but it made the safety property a CHECK — something that could be forgotten, or bypassed by
a subclass, or true of one code path and not another. Here a package is simply not a
mountable thing: there is no method by which it could be routed to, so there is nothing to
enforce. A capability that reaches the internet cannot get the host because it is not the
kind of object that has one.

The manifest already knew about this. Every kind carries `package` — `vm`, `network` and
`snapshot` are all `core` — so the vocabulary was half-present before the word was.

WHAT A PACKAGE SUPPLIES is exactly what an engine supplies minus the mounting: a MANIFEST
FRAGMENT (its own kinds) and TOOLS. The engine that loads it owns execution, which is why a
package never holds its own executor — its work reaches the world through the same gauntlet
a VM operation does. One door, not two.
"""
from __future__ import annotations

from typing import Any, Dict, List


class Package:
    """Kinds and tools an engine can load. Not mountable, by construction."""

    name: str = "unnamed"
    # One line, for the operator and for whoever is deciding what a program may reach for.
    description: str = ""
    # WHERE IT RUNS, as a fact about the package rather than a permission it asks for.
    # `guest` means inside a machine the executor provides; `world` means inside the world
    # engine itself. Nothing reads this to grant anything — it is documentation for a human
    # and a hint for the router about whether a machine is needed first.
    runs_in: str = "guest"

    @property
    def manifest(self) -> Dict[str, Any]:
        """This package's kinds. Merged into the loading engine's manifest under its name."""
        return {}

    def tools(self) -> List[str]:
        """Every tool this package's manifest names — derived, never listed twice."""
        from ..planner.ir import effects
        return sorted(effects.tools_of(self.manifest))

    def claims(self, request: str) -> bool:
        """Might a program need this? A HINT for what to offer, never a routing decision.

        A package is never chosen INSTEAD of an engine — it is loaded so that a Medusa
        program has the vocabulary to call it once it has somewhere to run it.
        """
        return False

    def hands(self, execute):
        """What this package's tools MEAN, given the engine's executor. `None` = not runnable.

        THE MISSING HALF OF LOADING. A package supplied a manifest and a tool list, both of
        which were honoured — the kinds joined the engine's manifest, the writer planned the
        whole chain in the right order — and then the program said `camoufox_launch(...)` and
        the world answered `Unknown tool`. Measured on the lab: the machine was created and
        launched for a browser that could never start.

        `execute` IS THE ENGINE'S, and passing it in rather than letting the package keep one
        is what makes the guest boundary structural. The package decides what its tool means;
        the engine decides what running anything means. A package that built its own executor
        would be the second door the whole layer exists to prevent.

        RETURNING `None` IS A REAL ANSWER — a package may contribute vocabulary that some
        other component executes, and one that cannot run its own tools should say so rather
        than raise when the first one is called.
        """
        return None


def merge(*manifests: Dict[str, Any]) -> Dict[str, Any]:
    """Combine manifests, refusing collisions rather than letting one win silently.

    Two packages both declaring a `page` kind is a real conflict — the writer would plan
    against whichever happened to load second, and the resulting program would be correct
    for a manifest nobody wrote down. Refusing costs a startup error; silently merging costs
    a debugging session.
    """
    out: Dict[str, Any] = {}
    for m in manifests:
        for kind, spec in (m or {}).items():
            if kind in out and out[kind] is not spec:
                raise ValueError(
                    f"two packages both define the kind {kind!r} — a program planned against "
                    f"a merged manifest would be correct for one of them and wrong for the "
                    f"other, and nothing would say which")
            out[kind] = spec
    return out
