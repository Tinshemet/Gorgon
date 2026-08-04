"""coverage_corpus.py — requests written from the DOMAIN, not from the shapes.

WHY THIS EXISTS, AND WHY THE LADDER CANNOT ANSWER IT. Every one of the 14 rungs was written
to exercise a reasoning load the goal language already has a shape for, so 42/42 would say
the system handles the requests we wrote for it. The published result on exactly this is
blunt: benchmark success for the LLM-as-formalizer paradigm "may be overstated due to an
unrealistic design of standard benchmarks, namely that problem descriptions and ground-truth
code often have a one-to-one mapping, while in industrial use cases, succinct problem
descriptions often describe large problems" (arXiv:2603.23844, and the URVEL benchmark built
to break formalizers that score perfectly on the standard ones).

SO THIS MEASURES COVERAGE, NOT PASSES. Nothing here runs. Nothing here touches a world. The
only question asked is whether the FRONT SEAM can say what the request means, and the answer
is one of three:

    TRANSLATED   goals came back and they mean the request
    DECLINED     no goals and a reason — the system saying "I cannot say this"
    FORCED       goals came back and they DO NOT mean the request

FORCED IS THE WHOLE POINT. It is the precursor of DONE_BUT_FALSE: a request bent into the
nearest available shape, which then plans, runs and closes DONE over a world nobody asked
for. DECLINED is a SUCCESS here — a system that knows what it cannot say is the one property
that makes the other two trustworthy.

# THE RULE THAT MAKES THIS HONEST

**A THIRD OF THESE ARE MEANT TO BE IMPOSSIBLE.** A corpus of requests the language can
express measures nothing: every entry would translate, and "0 forced" would be an artefact of
the corpus rather than a fact about the system. The rows marked `expect="decline"` are
requests I believe NO combination of `count`, `reach`, `every`, `per` and `observe` can
state — ordering, timing, causation, comparison, negotiation. They are the rows that can
fail, and they are where the vocabulary's edge actually is.

**AND THE EXPECTATION IS WRITTEN FROM THE REQUEST, NEVER FROM A RUN.** Each row's `shapes`
and `names` were decided by reading the English and asking what a correct reading must claim
— before the harness was pointed at any of them. That ordering is this project's own
standing rule (`deterministic_rules`: commit the held-out corpus BEFORE tuning), and it is
the only thing stopping a coverage measure from becoming a description of current behaviour.

**THE DOMAIN IS THE OPERATOR'S**: a purple-team lab. Build it, isolate it, snapshot it,
inspect it, tear it down. Not one of these was reverse-engineered from a shape.
"""
from __future__ import annotations

from typing import Any, Dict, List


def R(id: str, request: str, expect: str, shapes=(), names=(), why: str = "") -> Dict[str, Any]:
    """One row.

    `shapes` — what a CORRECT reading must claim, as goal shapes. Judged from the English.
    `names`  — every MEMBER IDENTIFIER the request states: a machine, a network, a template.
               NOT an attribute value — `target` in "tag them target" is a label, and a
               label is not a name. A reading that invents an identifier is not this
               request; one that drops it has read half of it.
    `expect` — "translate" or "decline". `decline` means: I do not believe these five shapes
               can state this, so the honest answer is `cannot`.
    """
    return {"id": id, "request": request, "expect": expect,
            "shapes": set(shapes), "names": set(names), "why": why}


CORPUS: List[Dict[str, Any]] = [
    # ── things the shapes should cover ────────────────────────────────────────────────
    R("build-pair", "build me two machines called attacker and victim on a network called range",
      "translate", ("count", "every"), ("attacker", "victim", "range"),
      "the commonest real request: some named machines, one network"),
    R("isolate", "take the machine called payload-test off every network",
      "translate", ("every",), ("payload-test",),
      "removal of an attribute, not addition — the unsetter side"),
    R("label-fleet", "tag every windows machine as target",
      "translate", ("every",), (),
      "a filtered distributive write"),
    R("snapshot-before", "snapshot every machine on the range network",
      "translate", ("per",), ("range",),
      "a second kind, produced one per member"),
    R("count-check", "how many machines are on the dmz network",
      "translate", ("count",), ("dmz",),
      "a pure question — no acting at all"),
    R("teardown", "delete every machine labelled scratch",
      "translate", ("every", "count"), (),
      "destruction over a filtered set"),
    R("reachability", "confirm the machines on the range network can all see each other",
      "translate", ("reach",), ("range",),
      "the reach shape, said in the operator's own words"),
    R("clone-fleet", "make four copies of the golden image and label them all bench",
      "translate", ("count", "every"), ("golden",),
      "a derived set — the members do not exist until the program makes them"),
    R("ensure-running", "make sure every machine tagged core is running",
      "translate", ("every",), (),
      "convergence to a state over a filtered set"),
    R("probe-alive", "check which machines are answering",
      "translate", ("observe",), (),
      "an observation with no requirement on the answer"),
    R("named-state", "shut down web and db",
      "translate", ("every", "count"), ("web", "db"),
      "two named members, one state — the enumerated axis, small"),
    R("network-teardown", "get rid of the staging network",
      "translate", ("count",), ("staging",),
      "removal of a network, which only became sayable on 2026-08-04"),
    R("memory-spec", "give the machine called burner 8192 MB of memory",
      "translate", ("every", "count"), ("burner",),
      "an attribute that only became selectable on 2026-08-04"),
    R("mixed-kinds", "put web and db on a network called core and snapshot both of them",
      "translate", ("every", "per"), ("web", "db", "core"),
      "two kinds in one request, with the second derived from the first"),

    # ── things I do not believe these five shapes can state ───────────────────────────
    R("ordering", "snapshot db, then upgrade it, and if the upgrade fails roll the snapshot back",
      "decline", (), ("db",),
      "ORDER AND RECOVERY. A goal set is unordered and has no failure branch; Medusa has "
      "IFAILS but a GOAL cannot say it, so the request's whole point is unstateable"),
    R("timing", "restart the range machines one at a time, waiting for each to come back",
      "decline", (), ("range",),
      "SEQUENCING WITHIN A SET. `every` says what must hold of all members, never in what "
      "order or with what wait between them"),
    R("causation", "find out why db cannot reach web and fix whatever it is",
      "decline", (), ("db", "web"),
      "DIAGNOSIS AS AN OPEN QUESTION. rung 9 works because the END STATE is stateable; "
      "'why' asks for a cause, and no shape names one"),
    R("comparison", "make the staging network look like the production one",
      "decline", (), ("staging", "production"),
      "A GOAL ABOUT TWO SETS RELATIVE TO EACH OTHER. Every shape takes ONE selector; "
      "`disjoint` is the only two-set predicate and it is not in the goal language at all"),
    R("preference", "give me a lab that looks like a small corporate network",
      "decline", (), (),
      "UNDERSPECIFIED BY DESIGN. Nothing here names a member, a count or a state — a "
      "correct answer would be an invention, which is what `cannot` is for"),
    R("temporal", "keep three machines running at all times",
      "decline", (), (),
      "AN INVARIANT OVER TIME. A goal is checked once; 'at all times' is a routine's "
      "schedule, which lives in a PROCEDURE header and has no goal shape"),
    R("quantified-relation", "make sure no two machines share a network",
      "decline", (), (),
      "A RELATION OVER PAIRS. This is exactly DISJOINT, which Medusa evaluates and the "
      "GOAL language cannot say — the sixth shape, if there is to be one"),
    R("conditional", "if the range network already exists, add web to it, otherwise create it first",
      "decline", (), ("range", "web"),
      "A BRANCH. Medusa has IF; a goal set has no conditional, and an ACHIEVE already "
      "means 'make it so' — which is the answer, but it is not what was ASKED"),
]


def by_expectation(want: str) -> List[Dict[str, Any]]:
    return [r for r in CORPUS if r["expect"] == want]
