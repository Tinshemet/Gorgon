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

    def scratch(self):
        """A MODEL of the lab to plan against — never the lab.

        The ghost writer executes each placed tile on its scratch world to advance the
        virtual state, which is what makes lowering correct: "every stopped machine" must
        resolve against the world AS IT WILL BE. Against a real lab that would mean PLANNING
        PERFORMS THE ACTIONS, and it did — one goal created a machine on the way to producing
        the plan that would create it.

        So the scratch is a manifest-driven in-memory world seeded from what the lab holds
        now. The same simulator that runs a kitchen becomes the planning model for the lab,
        which is the payoff of having made the writer domain-free: there was no second
        simulator to write.

        It is a SNAPSHOT, deliberately. A plan is computed against the world as it was when
        planning began, and the program's own ENSUREs are what confirm the world it actually
        meets — which is the same division of labour `already_satisfied` relies on.
        """
        from tests.bench.generic_world import World as _Model
        model = _Model(self.kinds)
        # `vms` is a METHOD on ActiveLibrary, not an attribute — the second interface
        # mistake this mount made against a library it had never been pointed at. Called,
        # and guarded, because an unreachable library must not read as an empty lab.
        rows = self._library.vms()
        for name, rec in (rows or {}).items():
            row = {k: v for k, v in (rec or {}).items() if not str(k).startswith("_")}
            model.state.setdefault("vm", {})[name] = row
        return model

    def names(self) -> set:
        """Every name the lab already knows. `known_names`, not `names`.

        THIS WAS WRONG FROM THE DAY IT WAS WRITTEN and a bare `except Exception` hid it: the
        call was `self._library.names()`, which `ActiveLibrary` does not have, so it raised
        every time and the handler returned an empty set. Silently — so `known_names` was
        ALWAYS EMPTY, and every `$reference` check the validator makes was being answered
        against a lab that appeared to contain nothing.

        Found 2026-08-01 the first time this mount was pointed at a real library rather than
        the sim, which is precisely the risk of shipping a seam nobody has exercised. THE
        HANDLER IS GONE: a library that cannot answer this is a broken lab and must say so,
        because the failure it was swallowing is indistinguishable from an empty one.
        """
        return set(self._library.known_names())


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
