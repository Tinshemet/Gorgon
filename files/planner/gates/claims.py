"""claims.py — THE ONE READER. What does a goal actually assert, atom by atom?

    claims(goal) -> [Claim(kind, key, name, stance, attr, value)]

## WHY THIS EXISTS, AND IT IS A MEASURED FAILURE RATHER THAN A TIDY-UP

`to_goals` FOLDS. "create a vm named beta and then launch it" comes back from the model as two
goals and arrives at the writer as ONE:

    {"shape": "count", "select": {"kind": "vm", "name": "beta", "status": "running"}, "eq": 1}

Gate 2 read that fold as a CONSTRAINT on a machine — a reference — when it is a CREATION with
a property attached. Against the fresh corpus that accused readings which PASSED, and the fix
was one line in one gate. **Gates 3 and 4 would each have hit the same fold and each needed
their own version of that line**, and the first one to get it slightly differently would put
the codebase back where it was on 2026-08-06: several rules disagreeing about what a goal
means, each correct about its own half.

⇒ **SO SHAPE IS READ IN ONE PLACE AND THE ANSWER IS SHARED.** A gate asks what a goal claims;
it never works it out.

## ⇒ IT READS. IT DOES NOT REWRITE, AND THAT IS THE WHOLE DESIGN

The obvious alternative was to UNFOLD the goals — derive the leaves as real goals and let the
gates judge those. It was rejected for two reasons, both of which this codebase has already
paid for once:

**TWO REPRESENTATIONS DRIFT.** Today the extraction schema says `amount` is required while
`to_goals` declares absent-means-one, and the schema declares no `value` on `count` while the
reader accepts one. Two authorities on the same question, disagreeing, found by measurement.
A folded form for the writer and an unfolded form for the gates would be a third instance.

**AND THE WRITER PLANS FROM THE FOLDED FORM.** Gates judging an unfolded goal set would be
grading something that never runs — which is the exact shape of DONE_BUT_FALSE.

So the goals are untouched and this returns a VIEW of them. One artifact, one authority.

## THE STANCES, AND THE RULE FOR EACH

    CREATES   a `count ... = N` pinned on the kind's KEY. It brings the member into being,
              WHATEVER ELSE the selector carries — extra attributes are properties to
              establish, not filters presupposing a member.
    REMOVES   a `count ... = 0` on the key. The one count shape that cannot be a creation.
    REFERS    `every` / `per` / `observe` over a selector pinned to the key. It constrains a
              member that must already be there.
    ASSERTS   an attribute a goal requires to hold — from a `must`, or from an extra
              attribute folded into a `count` selector.
    OBSERVES  a fact the reading establishes by asking the world.

`must` VALUES ARE NOT REFERENCES. *"A selector REFERS — the name must be given; a `must`
ASSIGNS — the name may be minted"* ([[gorgon-reading-names-writing-mints]]). `every vm must
network=core` does not claim `core` exists; the writer mints it.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

CREATES = "creates"
REMOVES = "removes"
REFERS = "refers"
ASSERTS = "asserts"
OBSERVES = "observes"

_STRUCTURAL = ("kind", "not", "any", "all", "except")


class Claim:
    """One atomic thing a goal says. A goal may say several."""

    __slots__ = ("kind", "key", "name", "stance", "attr", "value", "goal")

    def __init__(self, kind, stance, key=None, name=None, attr=None, value=None, goal=None):
        self.kind = kind
        self.stance = stance
        self.key = key
        self.name = name
        self.attr = attr
        self.value = value
        self.goal = goal

    @property
    def identity(self):
        """The member this claim is about, or None if it speaks about a whole group."""
        return None if self.name is None else str(self.name)

    def __repr__(self) -> str:
        bit = f" {self.name!r}" if self.name is not None else " (group)"
        attr = f" {self.attr}={self.value!r}" if self.attr else ""
        return f"<{self.stance} {self.kind}{bit}{attr}>"


def _table(kinds=None) -> Dict[str, Any]:
    from planner.ir import config as _config
    return kinds if kinds is not None else (_config.KINDS or {})


def key_of(kind: str, kinds=None) -> Optional[str]:
    return ((_table(kinds).get(kind) or {}).get("key")) if kind else None


def refers_to(attr: str, kinds=None) -> Optional[str]:
    """The kind an attribute POINTS AT, from the manifest's own `refs`, or None.

    DECLARED, NOT INFERRED. `vm.setters.add_vm_to_network` carries `refs: "network"`, so a
    kind added later is covered without an edit here.
    """
    for spec in _table(kinds).values():
        if not isinstance(spec, dict):
            continue
        for setter in (spec.get("setters") or {}).values():
            if isinstance(setter, dict) and setter.get("attr") == attr:
                return setter.get("refs")
    return None


def claims(goal: Dict[str, Any], kinds=None) -> List[Claim]:
    """Every atomic assertion in one goal. THE ONLY PLACE THIS IS WORKED OUT."""
    kinds = _table(kinds)
    out: List[Claim] = []
    if not isinstance(goal, dict):
        return out

    # ── the quantified shapes: they CONSTRAIN what is already there ──────────────────────
    for field in ("every", "per", "observe"):
        sel = goal.get(field)
        if not isinstance(sel, dict):
            continue
        kind = sel.get("kind")
        k = key_of(kind, kinds)
        if k and isinstance(sel.get(k), (str, int)):
            out.append(Claim(kind, REFERS, key=k, name=sel[k], goal=goal))
        if field == "observe" and goal.get("fact"):
            out.append(Claim(kind, OBSERVES, attr=str(goal["fact"]), goal=goal))

    # ── count / reach: the shape that MAKES a member, or removes one ─────────────────────
    if str(goal.get("shape") or "") in ("count", "reach"):
        sel = goal.get("select") or {}
        kind = sel.get("kind")
        k = key_of(kind, kinds)
        if k and isinstance(sel.get(k), (str, int)):
            stance = REMOVES if goal.get("eq") == 0 else CREATES
            out.append(Claim(kind, stance, key=k, name=sel[k], goal=goal))
            # ⇒ THE FOLD, UNPACKED. An attribute beside the key in a `count` selector is a
            #   PROPERTY THE MEMBER MUST END UP WITH — `to_goals` folds "create beta and
            #   launch it" to `count(vm WHERE name=beta AND status=running) = 1`. Reading it
            #   as a filter is what accused passing readings of constraining a machine they
            #   were in the middle of building.
            if stance == CREATES:
                for attr, value in sel.items():
                    if attr in _STRUCTURAL or attr == k:
                        continue
                    out.append(Claim(kind, ASSERTS, key=k, name=sel[k],
                                     attr=attr, value=value, goal=goal))

    # ── a `must` ASSIGNS, and where it names another kind that member may be MINTED ──────
    must = goal.get("must")
    if isinstance(must, dict):
        sel = goal.get("every") or goal.get("select") or {}
        subject = sel.get("kind")
        for attr, value in must.items():
            out.append(Claim(subject, ASSERTS, attr=attr, value=value, goal=goal))
            ref = refers_to(attr, kinds)
            if ref and isinstance(value, str):
                # ⇒ MINTABLE ONLY IF THE KIND CAN BE MADE. A `must` ASSIGNS and the writer
                #   mints the member — but only where the manifest declares a creator. A kind
                #   with no `create` cannot be brought into being by assigning to it, so
                #   naming an absent one there REFERS, and refers to nothing.
                creatable = bool((_table(kinds).get(ref) or {}).get("create"))
                out.append(Claim(ref, CREATES if creatable else REFERS,
                                 key=key_of(ref, kinds) or "name", name=value, goal=goal))
    return out


def over(goals: Iterable[Dict[str, Any]], kinds=None) -> List[Claim]:
    """Every claim in a whole reading, in order.

    A READING IS A CONJUNCTION OF CLAIMS ABOUT THE END STATE, never a sequence of lookups —
    so a reference is judged against the world PLUS whatever the reading itself mints. Reading
    goals one at a time is what made "create beta and then launch it" look like a reference to
    a machine that does not exist.
    """
    out: List[Claim] = []
    for goal in goals or ():
        out += claims(goal, kinds)
    return out


def minted(goals: Iterable[Dict[str, Any]], kinds=None) -> Dict[str, set]:
    """kind -> the identities this reading brings into existence."""
    out: Dict[str, set] = {}
    for claim in over(goals, kinds):
        if claim.stance == CREATES and claim.identity is not None:
            out.setdefault(claim.kind, set()).add(claim.identity)
    return out
