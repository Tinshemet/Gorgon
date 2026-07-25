"""The complexity ladder: goals of strictly increasing reasoning load, each with an
objective checker read off the SimWorld.

The ladder exists to locate the CLIFF — the rung where the weak local model stops coping —
so the harness work has a measurement instead of an impression. Rungs 1-3 are the control
(they should stay green; a regression there means a fix broke something that worked). Rung
4 is the target: the collective loop the whole reasoning-scaffolding track is aimed at.

STANDING PRINCIPLE (the user's, explicit): this is a BENCHMARK OF PROGRESS, NOT A TARGET.
Never game it — no scripting the loop, no seeding sub_goals, no swapping in a bigger model
to make a rung go green. Improve the system genuinely and let the ladder measure.
"""
from typing import Callable, List, NamedTuple

from .sim_world import SimWorld


class Rung(NamedTuple):
    n: int
    name: str
    goal: str
    check: Callable[[SimWorld], bool]     # objective pass/fail, read off world state
    why: str                              # what reasoning load this rung adds


def _r1(w: SimWorld) -> bool:
    return "alpha" in w.vms


def _r2(w: SimWorld) -> bool:
    return w.vms.get("beta", {}).get("status") == "running"


def _r3(w: SimWorld) -> bool:
    return "lab" in w.nets and "lab" in w.vms.get("web", {}).get("nets", set())


def _r4(w: SimWorld) -> bool:
    """The TIGHTENED checker: the world's own reach predicate, not two independent counts.
    ≥5 VMs carrying 'fleet' AND all of them on one COMMON network. The loose version
    (count netted, count labelled) passed 5-on-netA + 5-on-netB — zero reachable pairs."""
    return w.reach("fleet", minimum=5)


RUNGS: List[Rung] = [
    Rung(1, "single", "create a vm named alpha", _r1,
         "one action, fully specified"),
    Rung(2, "sequential", "create a vm named beta and then launch it", _r2,
         "two ordered actions on one entity"),
    Rung(3, "dependency-chain", "create a network called lab and a vm named web, then put web on lab", _r3,
         "an action whose prerequisite must exist first"),
    Rung(4, "collective-loop",
         "create 5 vms, put them all in a network, give them all the 'fleet' label, "
         "and make sure they all ping each other", _r4,
         "an unnamed set, three distributive ops over it, and an assurance clause"),
]
