"""effects.py — what a tool MAKES TRUE, as a Medusa predicate.

A tool's postcondition, written in the language the GOALS are written in. That last part is
the whole point: once a tool can say "after me, `COUNT(SELECT vm WHERE name = X) = 1`", a
deterministic writer can chain tools toward a goal by matching postconditions against it,
and `derive()` closes whatever gap is left. Nothing here calls a model.

WHY THIS IS NOT `TOOL_EFFECTS`. The executor already carries an `effect` per tool, and
`create_vm`'s is `["vm_reload"]` — a CACHE INVALIDATION HINT. It says the registry should be
re-read, not what became true. Useful, and a different fact; conflating them would give the
writer a hint where it needs a claim.

MOST POSTCONDITIONS ARE DERIVED, NOT DECLARED. The manifest already says, per kind, which
tool CREATES it, which DELETES it, and what its KEY is — so a creator's postcondition is a
consequence of facts already recorded, and writing it out again would be a second authority
to drift from the first. Only the SETTERS needed new data (`kinds.<k>.setters`), because
which attribute a tool writes was genuinely nowhere.

THE TEST THAT MATTERS is not that these parse. It is that they are TRUE: run the tool
against the sim, evaluate the predicate through the same seams the language uses, and it must
hold. A postcondition that is merely well-formed is the 2026-07-31 failure mode one level up
— a mechanism that looks wired and asserts nothing.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import config


def _kind_of(tool: str) -> Optional[str]:
    """Which kind this tool acts on, from the manifest alone."""
    for kind, spec in (config.KINDS or {}).items():
        if tool == spec.get("create") or tool == spec.get("delete"):
            return kind
        if tool in (spec.get("setters") or {}):
            return kind
        if any(c.get("tool") == tool for c in (spec.get("creators") or {}).values()):
            return kind
    return None


def _exists(kind: str, key_attr: str, value: Any, count: int = 1) -> Dict[str, Any]:
    return {"shape": "count", "select": {"kind": kind, key_attr: value}, "eq": count}


def postcondition(tool: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The predicate that must hold after `tool` succeeds, or None if unknown.

    NONE MEANS UNKNOWN AND MUST STAY THAT WAY — the writer treats an unknown postcondition as
    "this tool proves nothing", which is the safe reading. Guessing one would let a solver
    believe a goal was reached because a tool it does not understand returned ok, which is
    precisely the "unverified is not done" rule the language is built on, broken from the
    inside.
    """
    kind = _kind_of(tool)
    if not kind:
        return None
    spec = (config.KINDS or {}).get(kind) or {}
    key = spec.get("key")

    setter = (spec.get("setters") or {}).get(tool)
    if setter:
        member = args.get(setter.get("member_arg"))
        value = (args.get(setter["value_arg"]) if "value_arg" in setter
                 else setter.get("value"))
        if member is None or value is None:
            return None
        # BOTH halves, because either alone is satisfiable by the wrong world: the member
        # filter without the attribute says only that the machine exists, and the attribute
        # without the member says only that SOMETHING carries it.
        return {"shape": "count",
                "select": {"kind": kind, key: member, setter["attr"]: value},
                "eq": 1}

    # CREATORS AND DELETERS, derived from the manifest. `creators` may name a different key
    # argument (clone_vm writes `new_name`), so it is read rather than assumed.
    for c in (spec.get("creators") or {}).values():
        if c.get("tool") == tool:
            name = args.get(c.get("key") or key)
            return _exists(kind, key, name) if name is not None else None
    if tool == spec.get("create"):
        name = args.get(key)
        return _exists(kind, key, name) if name is not None else None
    if tool == spec.get("delete"):
        name = args.get(key)
        # NOT the negation of "exists" — a count of ZERO. Medusa has `not` for selects, and
        # writing it that way would make the deleter's claim a different shape from the
        # creator's for no reason. Same predicate, different number.
        return _exists(kind, key, name, count=0) if name is not None else None
    return None


def declared() -> Dict[str, str]:
    """Every tool that carries a postcondition, mapped to its kind — for drift tests."""
    out: Dict[str, str] = {}
    for kind, spec in (config.KINDS or {}).items():
        for t in (spec.get("setters") or {}):
            out[t] = kind
        for c in (spec.get("creators") or {}).values():
            if c.get("tool"):
                out[c["tool"]] = kind
        for field in ("create", "delete"):
            if spec.get(field):
                out[spec[field]] = kind
    return out
