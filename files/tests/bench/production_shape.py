"""production_shape.py — the gate against a world shaped like the REAL lab, not like the bench.

    PYTHONPATH=. python3 tests/bench/production_shape.py [request ...]

## WHY THIS EXISTS

Every bench in this repository runs on `SimWorld`, which exposes `.vms` and `.nets` as plain
attributes. **`LabWorld` — the real lab — exposes none of that.** Its whole contract is four
things: `kinds`, `seams`, `execute`, `names` (engines/qemu.py:28), and `seams` is a
**@property** returning the pair rather than a method.

That difference was not cosmetic. Until 2026-08-06 `dry_run._records` probed for `_<kind>s`,
`<kind>s` and `.state`, so against a real lab the BEFORE snapshot was EMPTY while the AFTER
snapshot — taken from the scratch, a `model_world.World` carrying `.state` — read fine. Every
existing machine looked newly created, the diff was never empty, and `Rehearsal.inert` could
not fire at all. **Every "the gate catches X" result was a bench-only result.**

So this harness answers a question no other probe here can: does the gate work on the SHAPE
production actually has? It touches no real machine — the state underneath is a `SimWorld` —
but everything the pipeline is allowed to see is the mount contract.

## AND THE REQUEST IT LEADS WITH IS THE POINT

The operator, 2026-08-06: *"'create a procedure that creates 10 vms' is legal but horribly
vague."* No OS, no names, no network, no sizes. **The program regime exists to ABSORB that** —
*"we take the vague shape and turn it into code"* — so a pipeline that REFUSES it is failing
at the regime's purpose, not succeeding at safety.

What this prints, per request: what was read, what the gate said, what would run, and — the
column that matters — WHICH UNSPECIFIED THINGS SOMETHING SUPPLIED, and which seam supplied
them.
"""
from __future__ import annotations

import sys

from engines.channel import Channel
from engines.orchestrator import Orchestrator
from engines.registry import Registry
from planner import dry_run
from tests.bench.sim_world import SimWorld

VAGUE = [
    "create a procedure that creates 10 vms",
    "create 10 vms",
    "set up an isolated network named lab, provision a machine called web, and connect web to it",
]


class MountShaped:
    """A world with LabWorld's contract and nothing else — `kinds`, `seams`, `execute`, `names`.

    THE STATE UNDERNEATH IS A `SimWorld`, so nothing real is touched. What is faithful is the
    INTERFACE: no `.vms`, no `.nets`, no `.state` reachable from outside, and `seams` is a
    PROPERTY. Anything that reads this world has to do it the way production must.
    """

    def __init__(self, sim: SimWorld):
        self._sim = sim

    @property
    def kinds(self):
        from planner.ir import config
        return config.KINDS

    @property
    def seams(self):
        """The bench seams, WRAPPED so they route by kind the way production's do.

        MEASURED 2026-08-06 — the bench seam does NOT discriminate:

            select({"kind": "vm"})              -> ['app1']
            select({"kind": "network"})         -> ['core']
            select({"kind": "__no_such_kind__"}) -> ['app1']     <- the machines

        That is precisely the defect `LabWorld.seams` records having FIXED on the production
        side: *"the production select, asked about a kind it did not know, answered with the
        nine MACHINES."* The fix never reached the bench, so **the bench seam is more
        permissive than production** — a harness that cannot notice kind confusion measuring
        a system that must.

        WRAPPED HERE RATHER THAN FIXED IN `tests/bench/seams.py`, because changing the seam
        every existing measurement was taken against would invalidate them all at once. The
        wrap is recorded and the defect is left where a reader will find it.
        """
        from planner.ir import config
        from tests.bench.seams import seams as _seams
        select, holds = _seams(self._sim)

        def routed(sel, scope=None):
            if (sel or {}).get("kind") not in (config.KINDS or {}):
                return []
            return select(sel, scope)

        return routed, holds

    @property
    def findings(self):
        return self._sim.findings

    def names(self) -> set:
        return set(self._sim.names()) if hasattr(self._sim, "names") else set(self._sim.vms)

    def execute(self, tool, args):
        return self._sim.execute(tool, args)

    def scratch(self):
        import copy
        return MountShaped(copy.deepcopy(self._sim))


def _seeded() -> SimWorld:
    world = SimWorld()
    for name in ("app1", "db"):
        world.vms[name] = world.blank_vm()
    return world


def run(request: str) -> None:
    sim = _seeded()
    world = MountShaped(sim)

    # CAN THE PIPELINE SEE THIS WORLD AT ALL? The question the whole harness exists for, and
    # the one that was silently answered NO in production until today.
    seen = dry_run.snapshot(world)
    print(f"\n{'═' * 92}\n  {request!r}")
    print(f"  the world, as the gate can see it: "
          f"{ {k: sorted(v) for k, v in seen.items()} or 'NOTHING — the gate is blind here'}")

    from engines.rig import translator
    registry = Registry()
    from engines.medusa.engine import MedusaEngine
    try:
        registry.mount(MedusaEngine(world))
    except Exception as exc:
        print(f"  could not mount: {type(exc).__name__}: {exc}")
        return
    orch = Orchestrator(registry, Channel([translator()]))
    before = dry_run.snapshot(world)
    try:
        out = orch.handle(request)
    except Exception as exc:
        print(f"  RAISED {type(exc).__name__}: {exc}")
        return
    after = dry_run.snapshot(world)

    print(f"  outcome : {out.get('outcome')}")
    if out.get("asked"):
        print(f"  ASKED   : {out['asked'][:150]}")
    if out.get("caught"):
        print(f"  caught  : {out['caught']}")
    why = str(out.get("why") or "")[:150]
    if why and not out.get("asked"):
        print(f"  why     : {why}")
    print(f"  rendered:")
    for line in str(out.get("rendered") or "").splitlines()[:12] or ["    (nothing)"]:
        print(f"    {line}")
    change = dry_run.diff(before, after)
    print(f"  the world moved: "
          f"{ {k: v for k, v in change.items() if v and k != 'born'} or 'NOTHING'}")


def main(argv=None) -> int:
    for request in (argv or sys.argv[1:] or VAGUE):
        run(request)
    print(f"\n{'═' * 92}")
    print("  A VAGUE REQUEST THAT IS REFUSED IS THE PROGRAM REGIME FAILING AT ITS PURPOSE.")
    print("  The regime exists to turn a vague shape into code — read every REFUSED above as")
    print("  a place something should have SUPPLIED, DERIVED, or ASKED, and did not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
