"""qemu.py — the QEMU engine: virtual machines, networks and snapshots.

THE MOUNT, NOT THE BACKEND. The `executor/` package is the thing that actually talks to QEMU;
this is its face to the orchestrator — a manifest and an adapter, the same contract a kitchen
satisfies in twenty-five lines. Keeping them apart matters: the orchestrator must be able to
route to a capability without importing a hypervisor, and the executor must be replaceable
without the orchestrator noticing.

WHY IT IS NAMED FOR WHAT IT DRIVES rather than for what it is. "Executor" says how it is
built; "qemu" says what it can do, and the router reads one line about each engine to choose
between them. An engine's name is part of its interface.

IT READS THE REAL WORLD. `planner/program.seams(library, findings)` is the production pair —
the Active Library for the registry and the findings ledger for observed facts — so this
engine plans against what is actually there rather than a simulation. That is the step most
likely to find something, because the ghost writer has only ever seen the sim.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..planner.ir import config as _config
from .base import Engine
from .medusa import MedusaEngine


class LabWorld:
    """The mount contract over the real lab: `kinds`, `seams`, `execute`, `names`.

    A thin object on purpose. Everything it exposes already existed — the manifest, the
    production seams, the guarded executor — and it exists only so the ghost writer can be
    handed ONE thing that answers the three questions it asks.
    """

    def __init__(self, library, execute, findings=None):
        self._library = library
        self._findings = findings
        self._execute = execute
        self.kinds = _config.KINDS

    @property
    def seams(self):
        from ..planner.program import seams as _prod_seams
        return _prod_seams(self._library, self._findings)

    def execute(self, tool: str, args: Dict[str, Any]):
        # THE CALLER'S GUARDED EXECUTOR, handed in rather than constructed. A program's
        # statements are not a trusted region: they reach the world through the same gauntlet
        # a single tool call meets — legal filter, commit gate, contract tier, watchdog,
        # killswitch. Building our own executor here would quietly create a second door.
        return self._execute(tool, args)

    def names(self) -> set:
        try:
            return set(self._library.names())
        except Exception:
            return set()


class QemuEngine(MedusaEngine):
    """Medusa's planner, pointed at the real lab.

    A SUBCLASS RATHER THAN A COPY, because the planning is identical — that is the whole
    claim the kitchen proved. What differs is the world, and the world is a constructor
    argument.
    """

    name = "qemu"
    description = ("create, launch, stop, network, label and snapshot virtual machines "
                   "in the lab")
    intents = ("fetch", "ensure", "achieve")

    def __init__(self, library, execute, findings=None):
        super().__init__(LabWorld(library, execute, findings))

    def claims(self, request: str) -> bool:
        """Claims anything naming a machine, a network or a snapshot — by the MANIFEST'S OWN
        NOUNS, never a list written here. `kinds.<k>.nouns` already records what an operator
        calls these things ("machine", "box", "subnet"), and a second list would drift from
        it by the end of the week."""
        words = {w.strip(".,!?;:'\"").lower() for w in request.split()}
        for kind, spec in (self.manifest or {}).items():
            if kind in words or (set(spec.get("nouns") or ()) & words):
                return True
            if {f"{kind}s", *(f"{n}s" for n in (spec.get("nouns") or ()))} & words:
                return True
        return False
