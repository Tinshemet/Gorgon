"""The complexity ladder: goals of strictly increasing reasoning load, each with an
objective checker read off the SimWorld.

The ladder exists to locate the CLIFF — the rung where the weak local model stops coping —
so the harness work has a measurement instead of an impression. Rungs 1-3 are the control
(they should stay green; a regression there means a fix broke something that worked).
Rungs 4+ are the frontier.

Each rung names the reasoning load it ADDS over the one below:

  1  one action, fully specified
  2  two ordered actions on one entity
  3  an action whose prerequisite must exist first
  4  an unnamed set, distributive ops over it, and an assurance clause
  5  a FILTERED collective — act on the subset matching a condition, not on everything
  6  a PARTITION — two groups, treated differently, kept apart
  7  CONVERGENCE to a spec — diff current against desired and both add and remove
  8  a general rule with an EXCEPTION — "all of them, except this one"
  9  DIAGNOSIS — the goal states an end-state; find which member is wrong and fix it
 10  a derived set — clone from a source, then act on the results

A rung may seed starting state (`setup`); a goal about existing VMs needs VMs to exist.
The seeded state is part of the problem: rung 5 is only a filter if something is already
running, and rung 7 is only a convergence if some labels are already right.

STANDING PRINCIPLE (the user's, explicit): this is a BENCHMARK OF PROGRESS, NOT A TARGET.
Never game it — no scripting the loop, no seeding sub_goals, no swapping in a bigger model
to make a rung go green. Improve the system genuinely and let the ladder measure.
"""
from typing import Callable, List, NamedTuple, Optional

from .sim_world import SimWorld


class Rung(NamedTuple):
    n: int
    name: str
    goal: str
    check: Callable[[SimWorld], bool]     # objective pass/fail, read off world state
    why: str                              # what reasoning load this rung adds
    setup: Optional[Callable[[SimWorld], None]] = None    # starting state, if any


def _vm(w: SimWorld, name: str, status: str = "stopped", labels=(), nets=()):
    w.vms[name] = {"status": status, "labels": set(labels), "nets": set(nets)}
    for n in nets:
        w.nets.add(n)


# ── 1-4: the original ladder ──────────────────────────────────────────────────
def _r1(w): return "alpha" in w.vms
def _r2(w): return w.vms.get("beta", {}).get("status") == "running"
def _r3(w): return "lab" in w.nets and "lab" in w.vms.get("web", {}).get("nets", set())


def _r4(w):
    """The TIGHTENED checker: the world's own reach predicate, not two independent counts.
    ≥5 VMs carrying 'fleet' AND all of them on one COMMON network. The loose version
    (count netted, count labelled) passed 5-on-netA + 5-on-netB — zero reachable pairs."""
    return w.reach("fleet", minimum=5)


# ── 5: filtered collective ────────────────────────────────────────────────────
def _s5(w):
    _vm(w, "web", "stopped"); _vm(w, "db", "running"); _vm(w, "cache", "stopped")


def _r5(w):
    """Every VM running. The filter is the point: `db` was ALREADY running, so a model
    that launches everything indiscriminately still passes — but one that launches
    nothing, or only the first, does not."""
    return len(w.vms) >= 3 and all(v["status"] == "running" for v in w.vms.values())


# ── 6: partition ──────────────────────────────────────────────────────────────
def _r6(w):
    """Two groups, each internally reachable, and SEPARATE from each other. The
    separation is what makes this more than two rung-4s: putting all five on one network
    satisfies both reach checks and must still fail."""
    if not (w.reach("red", 3) and w.reach("blue", 2)):
        return False
    return not w.common_networks(w.members("red") + w.members("blue"))


# ── 7: convergence to a spec ──────────────────────────────────────────────────
def _s7(w):
    _vm(w, "one", labels=["prod"]); _vm(w, "two", labels=["prod"])
    _vm(w, "three"); _vm(w, "four")


def _r7(w):
    """EXACTLY three, from a starting point of two. Requires reading what is already
    true and adding only the difference — over-labelling all four fails."""
    return len(w.members("prod")) == 3


# ── 8: a rule with an exception ───────────────────────────────────────────────
def _s8(w):
    for n in ("app1", "app2", "app3", "db"):
        _vm(w, n)


def _r8(w):
    """Everything on `core` EXCEPT db, which belongs on `dmz` and not on core. The
    exception has to survive the distributive step that handles the rest."""
    others = [n for n in w.vms if n != "db"]
    if not others or not all("core" in w.vms[n]["nets"] for n in others):
        return False
    return "dmz" in w.vms.get("db", {}).get("nets", set()) and "core" not in w.vms["db"]["nets"]


# ── 9: diagnosis ──────────────────────────────────────────────────────────────
def _s9(w):
    w.nets.add("mesh0")
    _vm(w, "n1", nets=["mesh0"]); _vm(w, "n2", nets=["mesh0"]); _vm(w, "n3")


def _r9(w):
    """All three sharing one network. The goal names no culprit: two are already wired
    and the third is not, so the work is finding WHICH one is wrong."""
    return bool(w.common_networks(["n1", "n2", "n3"]))


# ── 10: a derived set ─────────────────────────────────────────────────────────
def _s10(w):
    _vm(w, "golden", "stopped")


def _r10(w):
    """Three clones of golden, all running. The set does not exist until the model makes
    it, and the follow-up action applies to members it chose the names for."""
    clones = [n for n in w.vms if n != "golden"]
    return len(clones) >= 3 and all(w.vms[n]["status"] == "running" for n in clones)


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
    Rung(5, "filtered-collective", "launch every vm that is currently stopped", _r5,
         "act on the SUBSET matching a condition, not on everything", _s5),
    Rung(6, "partition",
         "create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones together "
         "on their own network, and put the blue ones on a different network", _r6,
         "two groups, treated differently, and kept apart"),
    Rung(7, "convergence", "make sure exactly 3 vms carry the 'prod' label", _r7,
         "diff what IS against what is wanted, and change only the difference", _s7),
    Rung(8, "exception",
         "put every vm on a network called core, except db — db goes on a network "
         "called dmz instead", _r8,
         "a general rule with one carve-out that must survive it", _s8),
    Rung(9, "diagnosis", "make sure n1, n2 and n3 can all ping each other", _r9,
         "the goal names an end-state; find WHICH member breaks it", _s9),
    Rung(10, "derived-set", "clone golden into 3 new vms and launch all of them", _r10,
         "a set that does not exist until the model makes it, then acted on", _s10),
]
