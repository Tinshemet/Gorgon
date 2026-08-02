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

from planner.ir import config as _config
from planner.ir import observe as _observe
from .base import Engine
from .medusa import MedusaEngine


class LabWorld:
    """The mount contract over the real lab: `kinds`, `seams`, `execute`, `names`.

    A thin object on purpose. Everything it exposes already existed — the manifest, the
    production seams, the guarded executor — and it exists only so the ghost writer can be
    handed ONE thing that answers the three questions it asks.
    """

    def __init__(self, library, execute, findings=None, packages=()):
        self._library = library
        self._findings = findings
        self._execute = execute
        self._packages = tuple(packages or ())
        # WHAT THIS WORLD CANNOT ENUMERATE, said out loud. The library tracks machines and
        # networks; it has no snapshot listing, and `snapshot_list` is per-machine, so
        # building one would add a call per VM to every session start. Until that trade is
        # made deliberately, the honest answer to "what restore points exist?" is "I cannot
        # tell you" — not "none", which is what an unseeded kind silently becomes.

    @property
    def kinds(self) -> Dict[str, Any]:
        """THE MANIFEST IN FORCE, read at access — never a copy taken at construction.

        It was `self.kinds = _config.KINDS`, assigned in `__init__`, which runs when the rig is
        built and therefore outside every `use_kinds` scope. So a loaded package's kinds reached
        the SCHEMA and the PROMPT — the orchestrator scopes translation explicitly — and never
        reached the world the writer plans against. The model could name a search and the
        planner had never heard of one: `nothing reaches` on a goal whose whole dependency
        chain was sitting in the manifest one layer up.

        THIRD TIME FOR THIS EXACT DEFECT. The schema was frozen at import, then the prompt's
        domain line, now the world's kinds. Anything that reads the manifest must read it when
        it is used, because `use_kinds` is a dynamic scope and a value captured before it is a
        value from a different world.

        FOURTH TIME, 2026-08-02, AND THIS IS THE FIX FOR IT. Reading the live manifest is
        necessary and was not sufficient: a WORLD WITH PACKAGES MOUNTED IN IT still answered
        with only the core kinds, because the package manifests are merged by whoever ENTERS
        `use_kinds` and a caller that forgot got a world that had never heard of `search`. The
        writer then honestly reported `nothing reaches: count(search …) = 1` — no bug in the
        package, the manifest, the chain or the writer; the destination kind was invisible at
        the one moment it mattered.

        A WORLD KNOWS ITS OWN PACKAGES, so it can answer for their kinds without being told.
        That removes the requirement that four call sites remember a dynamic scope, which is
        what made this recur four times. The live scope still WINS where it is entered — this
        only ensures the packages mounted here are never missing from the answer.
        """
        live = _config.KINDS or {}
        if not self._packages:
            return live
        merged = dict(live)
        for pkg in self._packages:
            for kind, spec in (getattr(pkg, "manifest", None) or {}).items():
                merged.setdefault(kind, spec)
        return merged

    @property
    def unseeded(self) -> set:
        """Kinds this world cannot enumerate — derived, so a package's kinds are counted.

        A package contributes kinds the LIBRARY knows nothing about: it does not track
        browsers or searches and never will. Those would be `unseeded` — UNKNOWN, not empty —
        and computing this from the live manifest is what keeps that true as packages come and
        go.

        EXCEPT THAT A PACKAGE IS THE AUTHORITY FOR ITS OWN KINDS, and that is the whole
        distinction this attribute exists to draw. The library has NO IDEA whether a search
        exists; Camoufox KNOWS it holds none, the way an empty table knows it is empty. Both
        answer "zero" and only one of them is entitled to.

        Treating a package's kinds as unenumerable made the acceptance request fail with
        `nothing here can enumerate search` — the guard working perfectly against the wrong
        authority, refusing to plan the one kind of thing that is never pre-existing because
        the program is what creates it.
        """
        known = set()
        for p in self._packages:
            known |= set((getattr(p, "manifest", None) or {}).keys())
        # ASK THE LIBRARY WHAT IT HOLDS, rather than naming two kinds here. `("vm", "network")`
        # was written when those were the only tables, and it silently stopped being true:
        # `_refresh_templates` and `_refresh_profiles` have been filling `_templates` and
        # `_profiles` for as long as they have existed, and this line went on declaring both
        # unenumerable. So a check over a profile — a kind added precisely SO it could be
        # checked — closed UNMET with "nothing here can enumerate profile", and the tables that
        # would have answered were sitting right there.
        #
        # FOUND VIA `template`, which hit it the day it became a kind. The guard itself is
        # right and stays: unknown is not empty. What was wrong is WHICH kinds it called
        # unknown, and hardcoding that is what let the answer rot behind the code that fixed it.
        # `vm` AND `network` STAY UNCONDITIONAL: they are what a lab IS, and `select` reads
        # them through their own branches rather than a table lookup. Everything else earns
        # its way off this list by having a table the library actually fills.
        lib = self._library
        return {k for k in (self.kinds or {})
                if k not in ("vm", "network") and k not in known
                and getattr(lib, f"_{k}s", None) is None}

    def _ensure_built(self):
        """An UNBUILT LIBRARY IS UNKNOWN, NOT EMPTY — and it read as empty for a whole session.

        `ActiveLibrary` starts with `built = False` and empty tables, and `vms()`,
        `known_names()` and `by_network()` answer an unbuilt registry with `{}`. The REPL calls
        `snapshot()` at startup, so every interactive session was fine and NOTHING ELSE WAS.
        The `plan` shortcut, invoked directly, planned a nine-machine five-network lab as though
        it held nothing: the writer found zero members for `every vm`, `reach` had nothing to
        connect, and the run closed UNMET having emitted two vacuous ENSUREs over an empty
        selection. Not a wrong answer that looked wrong — a wrong answer that looked like a
        careful refusal.

        THIS IS THE SAME RULE `unseeded` ALREADY STATES one attribute below, applied to the
        registry itself rather than to one of its kinds. The mount is where a library becomes a
        world to plan against, so it is where the distinction has to be enforced.

        AND IT RAISES IF IT CANNOT. A lab that will not answer is broken, and the empty set it
        would otherwise return is indistinguishable from a lab with nothing in it — the exact
        confusion `names()` below records having been bitten by. Building here is idempotent
        and costs one local scan; being wrong about what the lab contains costs a plan that
        creates what already exists, or deletes on a count it computed from nothing.
        """
        # A LIBRARY WITH NO `built` ATTRIBUTE IS NOT MAKING A CLAIM, and that is different from
        # one claiming False. Test doubles and any future read-through registry simply hold what
        # they hold; only something that tracks its own builtness can be UNBUILT, and only that
        # is worth building. `None` rather than `False` as the default is what keeps this guard
        # from demanding `snapshot()` of every object that satisfies the rest of the contract.
        if getattr(self._library, "built", None) is not False:
            return
        self._library.snapshot()
        if not getattr(self._library, "built", False):
            raise RuntimeError(
                "the lab registry could not be built — refusing to plan against it, because "
                "an unreachable library is indistinguishable from an empty lab")

    @property
    def findings(self):
        """THE LEDGER, UNDER THE NAME EVERYTHING ELSE LOOKS FOR.

        It was `self._findings`, private, and `_findings_of` reads `world.findings` — so the
        engine could not see its own observations and fell through to listing what it had
        DONE. The acceptance run therefore published `answer(...) = unknown` on a search whose
        answer was sitting in the ledger, which is the exact conflation `_findings_of` exists
        to prevent, arriving through a spelling.
        """
        return self._findings

    @property
    def seams(self):
        """The lab's own seams, with a package's kinds answered by the package.

        A MEMBER OF A PACKAGE'S KIND IS INVISIBLE TO THE REGISTRY BY CONSTRUCTION. The lab
        tracks machines and networks; it has never heard of a browser or a search. So a
        program that ran a search perfectly still failed its own existence witness — `count
        is 0, wanted == 1` — and the production select, asked about a kind it did not know,
        answered with the nine MACHINES.

        Both halves of that are fixed here by the same rule: whoever owns the kind answers
        for it. `unseeded` already says a package is the authority for its kinds; this is
        what makes that claim true rather than merely asserted.
        """
        from planner.program import seams as _prod_seams
        select, holds = _prod_seams(self._library, self._findings)
        owned = {}
        for p in self._packages:
            for kind in (getattr(p, "manifest", None) or {}):
                owned[kind] = p
        if not owned:
            return select, holds

        def routed(sel, scope=None):
            pkg = owned.get((sel or {}).get("kind"))
            if pkg is None:
                return select(sel, scope) if scope is not None else select(sel)
            kind = sel["kind"]
            rows = (getattr(pkg, "state", None) or {}).get(kind) or {}
            spec = (getattr(pkg, "manifest", None) or {}).get(kind) or {}
            observed = spec.get("observed") or {}
            want = {k: v for k, v in (sel or {}).items() if k != "kind"}

            def value_of(name, row, attr):
                """One attribute of one member — from the LEDGER if it is an observed fact.

                AN OBSERVED ATTRIBUTE IS NOT A COLUMN ON THE ROW. `answered: yes` is a claim
                that a call ran; `answer(<query>)` is what the browser actually said, and it
                lives in the findings ledger because that is where things learned by ASKING
                go. Reading the row for it made `answer` permanently `unknown` — so the
                deliverable witness counted an unanswered search that had, in fact, answered.
                """
                obs = observed.get(attr)
                if not obs:
                    return row.get(attr, _observe.unknown())
                ledger = self._findings
                if ledger is None:
                    return _observe.unknown()
                fact = str(obs.get("fact") or f"{attr}({{{spec.get('key')}}})") \
                    .replace("{" + str(spec.get("key")) + "}", str(name)) \
                    .replace("{member}", str(name))
                has = getattr(ledger, "has", None)
                if callable(has) and not has(fact):
                    return _observe.unknown()
                got = ledger.get(fact) if hasattr(ledger, "get") else None
                # ANYTHING RECORDED IS AN ANSWER. What the value IS belongs to the reporter;
                # this seam only decides asked-or-not, which is what the witness asks.
                return _observe.unknown() if got in (None, "") else got

            out = []
            for name, row in rows.items():
                if all(str(value_of(name, row, k)) == str(v) for k, v in want.items()):
                    out.append(name)
            return out

        def judged(pred, scope=None):
            """A witness over a package's kind, answered by the package.

            ROUTING `select` WAS HALF THE JOB. An `ENSURE` is evaluated through `holds`, which
            runs its own registry query — so the writer PLANNED correctly against the package's
            books and then the closing witness asked the lab, which has never heard of a
            search, and the program failed `count is 0, wanted == 1` over a member sitting in
            the package's own state with `answered: yes`.

            The two seams have to agree about who owns a kind, or a program is judged against
            a different world than the one it was written for.
            """
            sel = (pred or {}).get("select") or {}
            if sel.get("kind") not in owned:
                return holds(pred, scope) if scope is not None else holds(pred, {})
            got = len(routed(sel))
            if "eq" in pred:
                want = pred["eq"]
                return got == want, f"count is {got}, wanted == {want}"
            if "min" in pred:
                want = pred["min"]
                return got >= want, f"count is {got}, wanted >= {want}"
            return False, f"cannot judge {pred.get('shape')} over {sel.get('kind')}"

        return routed, judged

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
        self._ensure_built()
        from planner.model_world import World as _Model
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
        self._ensure_built()
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

    def __init__(self, library, execute, findings=None,
                 author=None, route=None, packages=()):
        # `author`/`route` ARE STAGED LOWERING'S SEAMS, passed straight through. Without
        # them a granted promotion reaches for a decomposer that is not there —
        # recorded, inert, and indistinguishable from an escalation that worked.
        # THE PACKAGES GO TO THE WORLD TOO, not only to the engine. The engine needs them for
        # its manifest; the WORLD needs them to know which kinds have an authority behind
        # them — a package's own kinds are enumerable-by-somebody, where a snapshot is not.
        super().__init__(LabWorld(library, execute, findings, packages=packages),
                         author=author, route=route, packages=packages)

    # THE CONTRACT'S NOUN MATCH, NOT MEDUSA'S OVER-CLAIM, and it has to be said explicitly
    # because this class inherits from Medusa. Its own copy of the noun match was deleted as
    # a duplicate — correctly, the base does exactly that now — and deleting it silently
    # promoted this engine to the GENERAL FALLBACK, which claimed "bake a cake". Medusa
    # over-claims ON PURPOSE, being the thing that runs when nothing more specific fits; the
    # LAB engine is something specific, and it should be tried when a machine is mentioned.
    claims = Engine.claims


