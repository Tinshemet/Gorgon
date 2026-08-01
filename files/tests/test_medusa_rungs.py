"""test_medusa_rungs.py — every rung, through the WHOLE ENGINE PATH, no model.

WHAT THIS IS NOT. `test_ghost_writer` calls `cover` and `as_program` directly, which proves
the WRITER. This proves the ENGINE: request -> orchestrator -> claim -> sync -> route ->
session -> in-session -> MedusaEngine -> the world, graded by each rung's own checker.

WHY BOTH EXIST. Every defect this project has spent a week on lived in the wiring rather than
the component — a reporter built and not called, a grammar accepted and ignored, a promotion
recorded and inert. A green writer says nothing about whether the thing above it runs.

FAIRLY, AND THAT IS A CONSTRAINT ON THIS FILE AS MUCH AS ON THE CODE. No rung-specific
branch, no goals hand-tuned per rung, no checker weakened to fit. The goals come from the
same GOALS table `test_ghost_writer` uses — the extractor's output shape, written by hand
because the extractor is the SEPARATE, still-failing half — and every rung is served by the
identical call. If a rung passes here it is because the engine served it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     insession)
from orchestrator.ai.engines.channel import Answer
from orchestrator.ai.planner.ir import config as _config
from tests.bench.rungs import RUNGS
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld
from tests.test_ghost_writer import GOALS

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class LabEngine(MedusaEngine):
    """The Medusa engine over the VM SIM — the same mount contract, a different world.

    `SimWorld` names its own seams, so nothing here teaches the engine anything about VMs.
    """

    name = "medusa"

    def claims(self, request: str) -> bool:
        # THE RUNG TEXTS ARE THE REQUESTS, and they are about machines. Claiming everything
        # would hide a routing failure behind a planning one.
        return True


# THE TOOLS THAT ASK RATHER THAN ACT, derived from the manifest's own `observed.<fact>.by`.
# A hand-written list would drift the first time a kind grows an observation.
_ASKING_TOOLS = {o["by"] for spec in (_config.KINDS or {}).values()
                 for o in (spec.get("observed") or {}).values() if o.get("by")}


def _reserve(rung):
    """Serve a rung twice and return the SECOND pass's calls."""
    world = _world(rung)
    engine = LabEngine(world)
    reg = Registry()
    reg.mount(engine)

    def translate(request, w=None):
        return Answer(GOALS[rung.n], "table", "")
    translate.name = "table"
    orch = Orchestrator(reg, Channel([translate]))
    orch.handle(rung.goal, intent="ensure")
    return orch.handle(rung.goal, intent="ensure").get("calls") or []


def _world(rung):
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    return world


def _serve(rung, regime="translation", open_everything=False):
    """One rung, through the orchestrator, exactly as a request would be."""
    world = _world(rung)
    engine = LabEngine(world)
    reg = Registry()
    reg.mount(engine)

    def translate(request, w=None):
        # THE CHANNEL IS STUBBED, NOT THE ENGINE. This stands in for the extractor, which is
        # measured separately and separately failing; everything downstream of it is real.
        return Answer(GOALS[rung.n], "table", "")
    translate.name = "table"

    decide = (lambda st, s: insession.Verdict(
        insession.DECOMPOSE if (open_everything and st.divisible) else insession.RUN))
    orch = Orchestrator(reg, Channel([translate]), decide=decide)
    return orch.handle(rung.goal, intent="ensure", regime=regime), world


def test_every_rung_is_served_by_the_engine():
    """THE HEADLINE. Thirteen requests, one orchestrator, each graded by its own rung."""
    print("[engine] all 13 rungs, request in / world checked")
    served = []
    for rung in RUNGS:
        out, world = _serve(rung)
        ok = out["outcome"] == "DONE" and rung.check(world)
        served.append(ok)
        if not ok:
            print(f"       rung {rung.n}: {out['outcome']} — {out.get('why')}")
    check(f"{sum(served)}/{len(RUNGS)} rungs served end to end", all(served))


def test_every_rung_vouches_for_itself():
    """A run that DID the work and cannot prove it is not a pass. #54's rule, applied here."""
    print("[engine] and every one of them grounded")
    ungrounded = [r.n for r in RUNGS if _serve(r)[0].get("grounded") is False]
    check(f"no rung finished ungrounded ({ungrounded or 'none'})", not ungrounded)


def test_the_engine_costs_what_the_writer_costs():
    """The engine must not add calls of its own — it is a wrapper, not a second planner."""
    print("[engine] the engine adds no calls of its own")
    off = []
    for rung in RUNGS:
        out, _ = _serve(rung)
        if rung.verified is not None and len(out.get("calls") or []) != rung.verified:
            off.append(f"rung {rung.n}: {len(out.get('calls') or [])} vs {rung.verified}")
    check(f"every rung costs its verified baseline ({off or 'all match'})", not off)


def test_the_rungs_survive_being_served_one_node_at_a_time():
    """TREE REGIME, and the grain must not change the answer — proven per rung rather than
    trusted from the fuzz corpus, because these are the requests that matter."""
    print("[engine] served as a tree, and opened all the way down")
    bad = []
    for rung in RUNGS:
        for regime, opened in (("tree", False), ("translation", True)):
            out, world = _serve(rung, regime, opened)
            if out["outcome"] != "DONE" or not rung.check(world):
                bad.append(f"rung {rung.n} [{regime}, opened={opened}]: {out['outcome']}")
    check(f"every rung survives every grain ({bad or 'all served'})", not bad)


def test_a_second_pass_does_nothing():
    """IDEMPOTENCE THROUGH THE ENGINE. Re-serving a satisfied request must make no calls —
    the property rung 13 tests for the writer, asked of the whole path."""
    print("[engine] a satisfied request costs nothing the second time")
    busy = []
    for rung in RUNGS:
        world = _world(rung)
        engine = LabEngine(world)
        reg = Registry()
        reg.mount(engine)

        def translate(request, w=None):
            return Answer(GOALS[rung.n], "table", "")
        translate.name = "table"
        orch = Orchestrator(reg, Channel([translate]))
        orch.handle(rung.goal, intent="ensure")
        again = orch.handle(rung.goal, intent="ensure")
        # A PROBE IS NEVER "ALREADY DONE". An observation is a thing done, not a thing that
        # becomes true, so re-serving a request that asks something re-asks it — that is the
        # only way to know, and calling it a repeat would make staleness the cheaper answer.
        # Rung 11 pings four machines on every pass and is right to.
        repeated = [(t, a) for t, a in (again.get("calls") or [])
                    if t not in _ASKING_TOOLS]
        if repeated:
            busy.append(f"rung {rung.n}: {len(repeated)} acting call(s) on the second pass")
    check(f"no ACTING call repeats work already done ({busy or 'all quiet'})", not busy)
    asked = sum(1 for r in RUNGS for t, _ in (_reserve(r) or []) if t in _ASKING_TOOLS)
    check(f"and asking still happens on a second pass ({asked} probe(s))", asked > 0)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "rungs through the engine"))


if __name__ == "__main__":
    main()
