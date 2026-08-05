"""rig.py — THE PRODUCTION MOUNT, in one place a test can build.

WHY THIS FILE EXISTS. Four times in one session a capability was BUILT AND NOT WIRED: the
reporter had no narrator, staged lowering had no author or router, publications never reached
the findings, and the tree keeper recorded nothing. Every one of them looked finished — the
code was there, the tests were green, and the seam it hung on was `None`.

They share a shape. An injectable seam that defaults to `None` is INVISIBLE when nobody
injects it: the feature does not fail, it does not run, and nothing distinguishes "granted a
tree session and decomposed it" from "granted a tree session and found no decomposer".

SO THE MOUNT IS ASSEMBLED HERE AND ASSERTED THERE. `tests/test_rig.py` builds exactly what
the chat shortcut builds and checks that every seam has somebody behind it. That cannot prove
a seam WORKS — only a measurement does that — but it does prove nobody shipped a `None` and
called it done, which is the failure that actually kept happening.
"""
from __future__ import annotations

import os as _os

from typing import Any, Callable, Dict, Optional, Tuple


def staged_seams(model: str = None) -> Tuple[Optional[Callable], Optional[Callable]]:
    """`(author, route)` for staged lowering, or `(None, None)` if the bench is absent.

    THEY LIVE IN THE BENCH DELIBERATELY, and it is a measurement rather than an accident: the
    model-driven tree scores 4/13 where the deterministic writer scores 13/13. Moving them
    into production would say they had arrived. They are the FALLBACK for a goal the writer
    REFUSES — reached only after `Unsolvable`, only inside a granted tree session — so their
    cost is paid by whoever holds the budget rather than by every request.
    """
    try:
        from tests.bench.sim_world import SimWorld
        from tests.bench.tree_probe import make_emit, make_route
    except Exception:
        return None, None
    from .channel import _model as _configured
    stats: Dict[str, int] = {"route_calls": 0, "emit_calls": 0,
                             "route_channel": 0, "emit_channel": 0}
    # THE WORLD THOSE BUILDERS DESCRIBE IS A MODEL OF THE LAB, never the lab. A decomposer
    # that could reach the real executor would be a second door.
    scratch = SimWorld()
    name = model or _configured()
    return make_emit(name, scratch, None, stats), make_route(name, scratch, stats)


def translator() -> Callable:
    """English -> goals. The front seam, and the one still measured at the wall."""
    from . import extract as _extract
    from .channel import Answer

    def translate(gap, world=None):
        try:
            raw = _extract.extract(str(gap))
        except Exception as exc:
            return Answer(None, "extractor", f"{type(exc).__name__}: {exc}")
        # A DECLINE IS AN ANSWER AND IT CARRIES ITS OWN REASON. `declined()` existed and was
        # called from the bench ONLY — production flattened `{"cannot": "too vague"}` into the
        # same "no usable goal" it reports for a garbled reply. Those are different events: one
        # is the translator saying the request cannot be read, in its own words, and the other
        # is the translator failing to be read. Reporting them alike throws away the one piece
        # of information the operator can act on, which is WHY.
        # A REFUSAL WINS OVER GOALS THE SAME ANSWER CARRIED, and that is asserted here
        # rather than assumed: this returns BEFORE `to_goals` runs, so a model that says "I
        # cannot do this part" while translating the rest has its goals DISCARDED. Measured
        # on 2026-08-05 at 2 of 66 readings, and `coverage_probe` counts it on every run so
        # the rate is visible rather than remembered. It is the safe direction — half a
        # request planned and closed DONE is the DONE_BUT_FALSE this seam exists to stop —
        # but it is a CHOICE, and the day it stops being the right one it should be one that
        # was made on purpose.
        said_no = _extract.declined(raw)
        if said_no:
            return Answer(None, "extractor", f"cannot translate: {said_no}")
        # WHAT DID NOT SURVIVE IS PART OF THE ANSWER. A request whose second clause was
        # refused by one of `to_goals`' rules used to arrive here indistinguishable from one
        # that had no second clause — so the writer covered the half that made it, every
        # layer below was honest about that half, and the run closed DONE over a request it
        # had only partly read. See `to_goals`' own docstring for the measurement (rung 2).
        lost: list = []
        goals = _extract.to_goals(raw, str(gap), dropped=lost, world=world)
        # THE CLAUSE SPLIT, ADDITIVE AND OFF BY DEFAULT. Each clause of the request is asked
        # for on its own and the readings are unioned — see `extract.by_clause` for why a
        # narrower ASK with the same CONTEXT is the one lever the record supports.
        #
        # BEHIND A SWITCH BECAUSE IT IS AN EXPERIMENT AND COSTS A CALL PER CLAUSE. Off, this
        # path is byte-identical to the measured baseline; on, the difference is one union.
        # It is an env var rather than a manifest row on purpose — the manifest is for things
        # that have been decided, and this has been measured once at most.
        if _os.environ.get("GORGON_CLAUSE_SPLIT") == "1":
            extra = _extract.by_clause(str(gap), world=world)
            if extra:
                goals = _extract.merge(goals, extra)
                # `lost` IS NOT CLEARED, though a clause the whole-request pass dropped may
                # well have been answered by its own call. Clearing it would suppress the
                # half-a-request rule, and suppressing that rule is precisely how the
                # withdrawn derived-set repair turned an honest UNTRANSLATED into
                # DONE_BUT_FALSE 3/3 on 2026-08-06. Matching a loss report to the goal that
                # answered it needs a correspondence nothing here has, so the safe reading
                # stands: the run is refused, and the recovery shows up as goals nobody used.
        if not goals:
            return Answer(None, "extractor", "; ".join(lost) or "no usable goal",
                          dropped=lost)
        return Answer(goals, "extractor", "", dropped=lost)
    translate.name = "extractor"
    return translate


def floor_first(request, menu, engines):
    """Route to the executor when it is mounted. GRAVITY POINTS DOWN.

    The router is the one decision a model makes in this path and there is no model in it
    yet, so the rule is the ladder's own: try the cheapest regime, and let an engine that
    cannot serve a request say so cheaply.
    """
    return next((e.name for e in engines if e.name == "executor"),
                engines[0].name if engines else None)


def packages(findings=None) -> Tuple:
    """Capabilities a Medusa program may CALL, loaded into the world engine.

    A PACKAGE IS NOT MOUNTED AND CANNOT BE ROUTED TO — it has no `run` and no `intents`, so
    the orchestrator has no way to send a request here. What loading one does is join its
    KINDS to the engine's manifest, which is what lets the extractor NAME a search and the
    writer PLAN one.

    LOADING IT IS WHAT MAKES IT ASKABLE. Before this, mounting the engine extended what the
    system could DO and never what it could be ASKED for: the schema and the prompt are built
    from the manifest in force, so a package that never joined it was invisible to the front
    seam however complete its own code was.
    """
    try:
        from packages.camoufox import CamoufoxPackage
    except Exception:
        return ()
    # THE LEDGER GOES TO THE PACKAGE, so an observed answer lands where PUBLISH and the
    # reporter will look for it rather than in a dict only the package can see. It is the
    # SAME object the engine plans against — one ledger, or the thing that wrote the answer
    # and the thing that reports it are looking at different worlds.
    return (CamoufoxPackage(findings=findings),)


def build(execute: Callable, library=None, narrate: bool = True,
          decide: Optional[Callable] = None,
          consent: Optional[Callable] = None,
          permit: Optional[Callable] = None) -> Any:
    """The whole production mount: two engines, a channel, a reporter, a router.

    `execute` is the caller's GUARDED executor — the same door a single tool call goes
    through. Building one here would be a second door, which is the thing the engine layer
    exists to prevent.

    `consent` IS THE OPERATOR'S SURFACE, and it is the caller's for the same reason `execute`
    is: this module knows how to assemble a mount, not who is at the terminal. Left `None` it
    is the unattended answer, which `consent.granted` reads as no — and the fifth seam this
    file exists to keep visible.

    `permit(banned) -> bool` IS THE SIXTH, and it is the only one that asks WHO rather than
    WHETHER: a program naming a red-lined tool does not run until the operator lifts it with
    their password. Left `None`, a red line simply refuses — which is the right unattended
    answer, and the reason this is a seam rather than a prompt built in here.
    """
    from orchestrator.ai.active_library import LIBRARY

    from . import reporter as _reporter
    from .channel import Channel
    from .executor import ExecutorEngine
    from .orchestrator import Orchestrator
    from .qemu import QemuEngine
    from .registry import Registry

    lib = LIBRARY if library is None else library
    author, route = staged_seams()

    registry = Registry()
    # BOTH LOAD-BEARING ENGINES. The executor provides the box — one call, one answer — and
    # Medusa turns a prompt into a program when one call is not enough. Mounting only the
    # planner sent every request, however small, to the thing that writes programs.
    # ONE FINDINGS LEDGER for the whole mount. The engine plans and checks against it, the
    # package records observations into it, and the reporter is handed what it holds — three
    # readers of one book. Two books is how a program comes to assert a fact nobody can find.
    from planner.findings import Findings
    found = Findings()

    registry.mount(ExecutorEngine(lib, execute))
    registry.mount(QemuEngine(lib, execute, findings=found, author=author, route=route,
                              packages=packages(findings=found)))

    return Orchestrator(registry, Channel([translator()]), decide=decide,
                        route=floor_first, consent=consent, permit=permit,
                        narrate=_reporter.narrator() if narrate else None)
