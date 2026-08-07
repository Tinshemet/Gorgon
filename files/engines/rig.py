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

from planner.gates import completeness as _completeness
from planner.gates import reasoning as _reasoning
from planner.gates import truth as _truth
from planner.gates import viability as _viability

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

    # THE MODEL NOT ANSWERING IS NOT THE FRONT SEAM GETTING IT WRONG. A timeout, a dropped
    # connection or a truncated reply is the CHANNEL failing, and it arrived here as
    # `Answer(None, "extractor", ...)` — which the orchestrator closes as UNTRANSLATED,
    # scoring an infra failure as a translation failure.
    #
    # THAT IS THE EXACT ATTRIBUTION ERROR `engine_probe` EXISTS TO PREVENT: *"confusing it
    # with an engine failure is how a day gets spent debugging the wrong half."* The same
    # sentence applies one layer further out, and the spilled KV cache makes these real —
    # two timeouts turned up in a single probe run on 2026-08-06.
    #
    # NAMED, NOT SWALLOWED. The answer still fails; what changes is that a reader can tell a
    # request the seam could not read from one the model never answered.
    _INFRA = (TimeoutError, ConnectionError, OSError, ValueError)

    def translate(gap, world=None):
        try:
            raw = _extract.extract(str(gap))
        except Exception as exc:
            layer = "channel" if isinstance(exc, _INFRA) else "extractor"
            return Answer(None, layer, f"{type(exc).__name__}: {exc}")
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
        # ⇒ GATE 1, ON THE RAW ANSWER, AND THIS IS THE ONLY PLACE IT CAN WORK.
        #
        # `to_goals` is a legality checker in its own right, and it DISCARDS what it refuses:
        # an invented name goes into `lost` and the goal carrying it is thrown away. Run gate 1
        # after that and it finds nothing — measured, 0 mutations and 0 inventions across all
        # 78 recorded readings, on a corpus that visibly contains 'fives' and 'fleetsize'. It
        # was auditing a room the evidence had been removed from. Moved here, the same rules
        # catch 32 of 57. **The placement was worth ten times the rules.**
        #
        # IT DOES NOT VOTE YET. Its findings ride on `Answer.illegal`, which nothing refuses
        # on — see that field for why merging it into `dropped` would refuse 1 in 21 currently
        # passing runs.
        try:
            illegal = _completeness.inspect_raw(
                str(gap), raw, schema=_extract.schema()).findings()
        except Exception:
            # A GATE THAT RAISES MUST NOT TAKE THE TRANSLATION WITH IT. It is an observer here
            # and an observer that can fail the thing it observes is not one.
            illegal = []
        lost: list = []
        goals = _extract.to_goals(raw, str(gap), dropped=lost, world=world)
        # AND THE HALF OF GATE 1 THAT NEEDS THE GOALS RATHER THAN THE RAW ANSWER.
        #
        # `DROPPED` asks whether a value the operator QUOTED survived into the reading, and
        # that can only be answered once there IS a reading — the raw answer is the wrong
        # subject for it, because a clause the model never wrote is exactly what is being
        # looked for. The other three checks are the reverse and belong upstream, on the raw
        # answer, before `to_goals` discards the evidence.
        #
        # ONE GATE, TWO SUBJECTS, and each check is asked of the artifact that can answer it.
        whole = None
        try:
            whole = _completeness.inspect(str(gap), goals or [])
            illegal += [f for f in whole.findings() if f not in illegal]
        except Exception:
            pass
        # ⇒ GATE 2, HERE AND NOT IN THE ENGINE, because the world is already in hand.
        #
        # It needs a WORLD, which looked like it forced the call site into `engines/medusa` —
        # off limits until the orchestrator level is finished. It does not: `translate` is
        # HANDED a world (`orchestrator.py` calls `channel.ask(request, engine.world())`) and
        # passes it to `to_goals` already. Gate 2 asks the same object the same way.
        #
        # ITS `fetch` AND `settled` ARE NOT FAULTS AND MUST NOT TRAVEL AS ONE. A probe the
        # reading needs, and a goal that already holds, are both things the caller should KNOW
        # — neither is a reason to doubt the reading. Folding them into `illegal` would make
        # the one gate that knows how to RESOLVE something look like the one complaining most.
        fetch: list = []
        asks: list = []
        verdicts: dict = {}
        try:
            verdict = _truth.inspect(goals or [], world)
            illegal += [f for f in verdict.findings() if f not in illegal]
            fetch = verdict.questions()
            # ⇒ AND THE FETCH IS SUPPLIED, NOT MERELY NAMED. A reading that FILTERS on `alive`
            #   without ever asking is missing a precondition nothing else provides, so gate 2
            #   says the missing claim out loud — `observe(vm) alive` — and it is PREPENDED,
            #   because the observation has to happen before the goals that read it.
            #
            #   IT IS A READ AND ONLY A READ. `consent.survey` counts a probe as not acting,
            #   so this cannot turn an inert reading into one that changes the lab; the worst
            #   case is a question asked that nobody needed the answer to.
            supplied = verdict.supply()
            if supplied and goals:
                goals = supplied + list(goals)
            # ⇒ GATE 3, AND IT IS HANDED GATE 2'S ANSWER RATHER THAN RE-DERIVING IT.
            #
            # `settled` is the whole reason `inert` can be a check here at all. An empty
            # program has two causes — the goals ALREADY HOLD, or the reading does nothing —
            # and the single gate could not tell them apart, which is why `inert` was demoted
            # to a report on 2026-08-06. Gate 2 owns already-true now, so passing its verdict
            # forward is the architecture working: each gate guarantees something to the next.
            #
            # IT PLANS, WHICH COSTS A `cover` THE ENGINE WILL RUN AGAIN. Deterministic and
            # model-free, so it is milliseconds against a model call's seconds — worth saying
            # out loud rather than discovering later, but not worth contorting the wire for.
            reasoned = _reasoning.inspect(goals or [], world,
                                          settled=bool(verdict.settled))
            illegal += [f for f in reasoned.findings() if f not in illegal]
            asks = reasoned.questions()
            # ⇒ AND THE THREE VERDICTS TRAVEL, because gate 4 judges what the OTHER GATES DID
            #   rather than what the reading says. Each of them RESOLVES something locally —
            #   gate 1 restores a mangled value, gate 2 supplies a missing probe, gate 3 asks —
            #   and three reasonable local repairs can compound into something the operator
            #   never asked for. That composition is invisible to every gate that only sees
            #   its own question, which is the whole reason gate 4 is not a fourth check in a
            #   row.
            verdicts = {"completeness": whole, "truth": verdict, "reasoning": reasoned}
            # ⇒ GATE 4, OVER THE OTHER THREE. One reading cannot be unstable, so the
            #   disagreement half is free here and silent — it only has content where somebody
            #   paid for a second draw, which is `_restandardise`'s territory. What DOES fire
            #   on a single reading is the compounding check: two gates that both RESOLVED
            #   something have moved the artifact in two independent ways and nobody has
            #   looked at the sum.
            whole_verdict = _viability.inspect([goals or []], verdicts)
            illegal += [f for f in whole_verdict.findings() if f not in illegal]
            asks += [q for q in whole_verdict.questions() if q not in asks]
        except Exception:
            # A GATE THAT RAISES MUST NOT TAKE THE TRANSLATION WITH IT — the same rule the
            # gate 1 call above follows, and for the same reason: an observer that can fail
            # the thing it observes is not one.
            pass
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
                          dropped=lost, illegal=illegal, fetch=fetch, asks=asks)
        return Answer(goals, "extractor", "", dropped=lost, illegal=illegal,
                      fetch=fetch, asks=asks)
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
