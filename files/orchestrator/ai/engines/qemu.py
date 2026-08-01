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
        # WHAT THIS WORLD CANNOT ENUMERATE, said out loud. The library tracks machines and
        # networks; it has no snapshot listing, and `snapshot_list` is per-machine, so
        # building one would add a call per VM to every session start. Until that trade is
        # made deliberately, the honest answer to "what restore points exist?" is "I cannot
        # tell you" — not "none", which is what an unseeded kind silently becomes.
        self.unseeded = {k for k in (self.kinds or {}) if k not in ("vm", "network")}

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
        from ..planner.model_world import World as _Model
        model = _Model(self.kinds)
        # `vms` is a METHOD on ActiveLibrary, not an attribute — the second interface
        # mistake this mount made against a library it had never been pointed at. Called,
        # and guarded, because an unreachable library must not read as an empty lab.
        rows = self._library.vms()
        for name, rec in (rows or {}).items():
            model.state.setdefault("vm", {})[name] = self._as_manifest_row("vm", rec)

        # EVERY KIND THE LIBRARY CAN ANSWER FOR, not just the one somebody happened to seed.
        #
        # Only `vm` was seeded, so the model believed the lab had NO NETWORKS — and the
        # writer, asked to put machines on one, planned `create_network(network1)` over a lab
        # that already holds five. An empty set is not a neutral default when the plan's next
        # move is to CREATE what is missing.
        nets = getattr(self._library, "by_network", None)
        members_of = nets() if callable(nets) else {}
        for net, members in (members_of or {}).items():
            model.state.setdefault("network", {})[net] = {"net_name": net,
                                                          "members": set(members or ())}
            # THE MEMBERSHIP LIVES ON THE NETWORK RECORD AND THE FILTER ASKS THE MACHINE.
            # A vm record carries no network field at all, so `select(vm where network=x)`
            # could never match — the relation has to be inverted here, once, into the
            # attribute `add_vm_to_network` writes. Without it a `reach` goal over machines
            # ALREADY on a shared network plans the whole thing again.
            for m in members or ():
                row = model.state.get("vm", {}).get(m)
                if row is not None:
                    row.setdefault("network", set()).add(net)

        # SNAPSHOTS CANNOT BE SEEDED — the library does not track them, so the model would
        # say "there are none" to a question nobody asked. That is the difference between
        # UNKNOWN and EMPTY, and it is recorded rather than papered over: a `per ... make
        # snapshot` goal planned here will re-create restore points that may exist. Fixing
        # it needs a snapshot listing in the library, not a change to this file.
        model.unseeded = set(self.unseeded)
        return model

    def _as_manifest_row(self, kind: str, rec) -> dict:
        """One library record in the MANIFEST'S vocabulary.

        THE LIBRARY AND THE MANIFEST DO NOT SPELL THINGS THE SAME WAY, and copying rows
        verbatim meant every attribute filter silently matched NOTHING. The library says
        `labels`; the manifest's attribute is `label`, with `labels` listed as an alias — so
        `select(vm where label=benchfleet)` returned zero over a lab where two machines carry
        it, and the writer answered "nothing to do" rather than failing. A wrong answer that
        looks like a finished job is the worst shape this can take.

        THE ALIASES ARE ALREADY THE MAPPING. They exist so an operator may say `tag` or `os`,
        and the library's own field names are the same question asked from the other side.
        Reading them here rather than writing a second table is what stops the two drifting.

        A MULTI-VALUED ATTRIBUTE ARRIVES AS A LIST AND IS STORED AS A SET, because that is
        what the model's `_match` compares against for membership — the same shape its own
        setters produce, so a seeded row and a planned one are indistinguishable.
        """
        spec = (self.kinds or {}).get(kind) or {}
        alias = spec.get("aliases") or {}
        known = set(spec.get("attrs") or ())
        out = {}
        for field, value in (rec or {}).items():
            field = str(field)
            if field.startswith("_"):
                continue
            attr = alias.get(field, field)
            if attr not in known:
                # NOT A LIE, JUST NOT THE MANIFEST'S BUSINESS. `arch`, `memory_mb` and
                # `guest_agent` are real facts the planner has no predicate for, and they are
                # kept under their own names so anyone reading a scratch row sees the machine
                # rather than a redacted version of it.
                #
                # THEY ARE STILL MATCHABLE by a hand-written selector — `_match` compares
                # whatever attribute it is handed. Nothing in production can reach one, since
                # the extractor's attribute enum is the manifest's and closed, so this is a
                # property of the model rather than a hole in the language. Said plainly
                # because the first version of this comment claimed the opposite.
                out[field] = value
                continue
            out[attr] = set(value) if isinstance(value, (list, tuple, set)) else value
        return out

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
