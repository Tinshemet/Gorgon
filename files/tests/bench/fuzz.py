"""fuzz.py — random worlds, random goals, and a ground truth that cannot be argued with.

THIRTEEN RUNGS ARE THIRTEEN CASES. They were chosen by people, which means they test what
those people thought of, and a writer that passes all of them may still be a writer that was
shaped to pass them. This generates worlds and goals nobody chose.

THE GROUND TRUTH IS THE GOAL ITSELF, which is what makes this possible at all. There is no
"expected program" to compare against — programs are not unique — but there IS an exact
question: after running what the writer produced, do the goals HOLD? That is answered by the
same `holds` the language uses, so the test cannot grade itself leniently.

TWO LEVELS, and they answer different questions:
    writer   random goals -> program -> do the goals hold?          no model, thousands of cases
    round    random goals -> ENGLISH -> extract -> program -> ?     the model, and the harder claim

The round trip is the real test of the operator's design: the goals are generated FIRST, so
what the extractor should have produced is known exactly. A mismatch is not a matter of
opinion — it names which goal was lost or invented.

SEEDED, ALWAYS. A failing case that cannot be reproduced is a rumour, and this codebase has
spent enough days on results that moved. Every run prints its seed and every case is derived
from it.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from orchestrator.ai.planner.ir import config

from .seams import seams
from .sim_world import SimWorld

NAMES = ["web", "db", "cache", "api", "edge", "worker", "queue", "store",
         "auth", "log", "mail", "cdn"]
LABELS = ["prod", "staging", "dev", "fleet", "red", "blue", "canary"]
NETS = ["core", "lab", "dmz", "mesh", "backbone", "sandbox"]


def random_world(rng: random.Random) -> SimWorld:
    """A lab nobody designed. Machines, some labelled, some running, some networked."""
    w = SimWorld()
    for name in rng.sample(NAMES, rng.randint(2, 6)):
        w.execute("create_vm", {"name": name, "os_type": "linux"})
        if rng.random() < 0.4:
            w.execute("launch_vm", {"name": name})
        if rng.random() < 0.4:
            w.execute("add_label", {"name": name, "label": rng.choice(LABELS)})
    for net in rng.sample(NETS, rng.randint(0, 2)):
        w.execute("create_network", {"net_name": net})
        for vm in list(w.vms):
            if rng.random() < 0.3:
                w.execute("add_vm_to_network", {"vm_name": vm, "net_name": net})
    return w


def random_goal(rng: random.Random, w: SimWorld) -> Tuple[Dict[str, Any], str]:
    """One goal, and the English an operator might have used for it.

    THE ENGLISH IS GENERATED FROM THE GOAL, not the other way round, so the intended meaning
    is known exactly. Several phrasings per shape, because a pipeline that only understands
    one way of asking has learned the corpus rather than the request — the same reason the
    ladder carries a paraphrase column.
    """
    shape = rng.choice(["count", "every", "observe", "per", "reach"])
    label, net = rng.choice(LABELS), rng.choice(NETS)

    if shape == "count":
        n = rng.randint(1, 4)
        if rng.random() < 0.5:
            return ({"shape": "count", "select": {"kind": "vm", "label": label}, "eq": n},
                    rng.choice([
                        f"make sure exactly {n} vms carry the '{label}' label",
                        f"there should end up being precisely {n} machines tagged {label}",
                        f"I want {n} vms labelled {label}, no more and no fewer",
                    ]))
        return ({"shape": "count", "select": {"kind": "vm"}, "eq": n},
                rng.choice([f"make sure there are {n} vms in total",
                            f"end up with exactly {n} machines"]))

    if shape == "every":
        if rng.random() < 0.5:
            return ({"every": {"kind": "vm"}, "must": {"network": net}},
                    rng.choice([f"put every vm on a network called {net}",
                                f"connect all the machines to a network named {net}",
                                f"wire them all together on {net}"]))
        return ({"every": {"kind": "vm", "label": label}, "must": {"status": "running"}},
                rng.choice([f"launch every vm labelled {label}",
                            f"start up all the machines tagged {label}"]))

    if shape == "observe":
        return ({"observe": {"kind": "vm"}, "fact": "alive"},
                rng.choice(["ping every vm", "check which machines respond",
                            "ask each machine if it is alive"]))

    if shape == "per":
        return ({"per": {"kind": "vm", "status": "running"}, "make": "snapshot",
                 "link": "vm"},
                rng.choice(["take a snapshot of every running vm",
                            "make a restore point for each machine that is currently up"]))

    members = max(2, min(3, len(w.vms)))
    return ({"shape": "reach", "select": {"kind": "vm"}, "min": members},
            rng.choice(["make sure all the vms can ping each other",
                        "confirm every machine can reach the others"]))


def random_case(seed: int) -> Tuple[SimWorld, List[Dict[str, Any]], str]:
    """A world, the goals that must end up true in it, and the request that means them."""
    rng = random.Random(seed)
    w = random_world(rng)
    goals, lines = [], []
    for _ in range(rng.randint(1, 3)):
        g, text = random_goal(rng, w)
        # A DUPLICATE GOAL IS NOT A HARDER CASE, just a noisier one — and two contradictory
        # counts over the same set would make the case unsatisfiable through no fault of
        # anything under test.
        if any(_same_subject(g, prior) for prior in goals):
            continue
        goals.append(g)
        lines.append(text)
    return w, goals, ", and ".join(lines)


def _same_subject(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    key = lambda g: (tuple(sorted((g.get("select") or g.get("every") or g.get("per")
                                   or g.get("observe") or {}).items(), key=str)),
                     "every" in g, "per" in g, "observe" in g, g.get("shape"))
    return key(a) == key(b)


def holds_all(goals: List[Dict[str, Any]], world: SimWorld) -> Tuple[bool, str]:
    """Do the goals hold in this world? The verdict, through the language's own evaluator."""
    from .ghost_writer import _holds
    sel, holds = seams(world)
    for g in goals:
        if "observe" in g:
            continue                     # an observation is a thing done, not a state
        ok, why = _holds(g, holds, sel)
        if not ok:
            return False, f"{why} :: {g}"
    return True, "all goals hold"


# ── THE TAXONOMY ───────────────────────────────────────────────────────────────────────
# Named the same way `ladder_gate` names layers, and for the same reason: a single FAIL
# collapses four different diseases into one word, and the day that word hides a translation
# error behind a writing error is the day the numbers stop meaning anything.
#
#   VERIFIED     the goals hold afterwards, checked by the language's own evaluator
#   MISSING      an intended goal has no counterpart in what was extracted — dropped
#   INVENTED     an extracted goal answers to nothing that was asked — added
#   DISTORTED    a counterpart exists and disagrees: wrong count, wrong value, wrong set
#   UNSOLVABLE   the writer refused, honestly. A GAP IN THE RULES, not a wrong answer
#   BROKEN       it built and ran, and the goals still do not hold — the WRITER's fault
#   IMPOSSIBLE   the case contradicts itself, so nothing could satisfy it. The generator's
#                fault, and it must be named rather than counted as a failure of anything
#                under test — a fuzzer that scores its own bad cases against the code is
#                measuring noise and calling it signal.
#   CRASHED      the harness

def contradictory(goals: List[Dict[str, Any]]) -> bool:
    """Can no world satisfy these? Then the CASE is bad, not the code.

    Two counts over the same set demanding different numbers is the shape the generator can
    produce, and scoring it as a failure would quietly inflate the error rate with cases
    nobody could pass.
    """
    seen: Dict[str, int] = {}
    for g in goals:
        if g.get("shape") != "count":
            continue
        key = str(sorted((g.get("select") or {}).items(), key=str))
        if key in seen and seen[key] != g.get("eq"):
            return True
        seen[key] = g.get("eq")
    return False


def _fingerprint(g: Dict[str, Any]) -> Tuple:
    """What a goal is ABOUT, ignoring the number it demands.

    Two goals with the same fingerprint are answers to the same question, so they are
    counterparts; whether they AGREE is the separate question `DISTORTED` asks. Comparing
    whole dicts would make every near-miss look like a drop plus an invention, which reads
    as two failures where there is one.
    """
    for tag in ("every", "per", "observe"):
        if tag in g:
            return (tag, str(sorted((g[tag] or {}).items(), key=str)))
    sel = g.get("select") or {}
    return (g.get("shape"), str(sorted(sel.items(), key=str)))


def diagnose(intended: List[Dict[str, Any]],
             extracted: List[Dict[str, Any]]) -> Dict[str, list]:
    """What the extraction lost, added, or got wrong — goal by goal.

    Only possible because the space is CLOSED. Against a whole program there is no such
    comparison to make: two different programs can both be right, so a diff says nothing.
    Against components, the intended set is known exactly and every difference is nameable.
    """
    want = {_fingerprint(g): g for g in intended}
    got = {_fingerprint(g): g for g in extracted}
    missing = [want[k] for k in want if k not in got]
    invented = [got[k] for k in got if k not in want]
    distorted = [(want[k], got[k]) for k in want if k in got and want[k] != got[k]]
    return {"missing": missing, "invented": invented, "distorted": distorted}
