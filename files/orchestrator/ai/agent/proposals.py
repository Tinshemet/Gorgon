"""proposals.py — the referendum / amendment lifecycle: typed, weighted rule PROPOSALS.

A proposal is a would-be rule for the unified ``rules[]`` law, awaiting the operator's
consent + weight. Two origins:

  • REFERENDUM — the AI asks (during/after a mission): it hit a gate that blocks the goal
    and proposes a durable change of one kind (access / delegation / provisions / decree),
    with a PROPOSED weight it does NOT get to enact.
  • AMENDMENT — the human legislates directly (same shape, ``origin="human"``).

Either way it lands here as ``pending`` and only the operator's safeword + assigned weight
turns it into a rule (via ``forge.amend`` — a versioned, audited re-sign). The AI can
propose but never enact — consent of the governed, with the human as the final weight.

Stored per-agent at ``~/.gorgon/_agents/<agent>/referendums.json`` (id → proposal), apart
from the signed contract so a pending ask never silently alters the law.
"""
import json
import os
from typing import Any, Dict, List, Optional

from shared.bundle import Bundle
from .contract.rules import KINDS as _RULE_KINDS

_EFFECT_KINDS = ("access", "delegation", "provisions", "decree")


def _path(agent: Optional[str]) -> str:
    import re
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", agent or "default") or "default"
    return Bundle(safe).referendums_path


def _load(agent: Optional[str]) -> Dict[str, Dict[str, Any]]:
    try:
        with open(_path(agent)) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(agent: Optional[str], data: Dict[str, Dict[str, Any]]) -> None:
    p = _path(agent)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f"{p}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, p)


def validate(kind: str, effect: Optional[Dict[str, Any]]) -> Optional[str]:
    """Why a proposal is malformed, or None. A typed proposal must name a known kind and,
    for an enforceable kind, carry a non-empty effect of the right shape."""
    if kind not in _RULE_KINDS:
        return f"unknown kind {kind!r}; expected one of {_RULE_KINDS}"
    if kind not in _EFFECT_KINDS:
        return None                                     # documentary 'rule' needs no effect
    eff = effect or {}
    if not eff:
        return f"a {kind} proposal must declare an effect"
    ok = {"access": ("forbid", "allow"), "delegation": ("tier",),
          "provisions": ("reward_cost",), "decree": ("success_predicate",)}[kind]
    if not any(k in eff for k in ok):
        return f"a {kind} effect must set one of {ok}"
    return None


def propose(agent: Optional[str], *, kind: str, text: str, effect: Optional[Dict[str, Any]] = None,
            proposed_weight: int = 2, origin: str = "ai", prompted_by: Optional[str] = None,
            id: Optional[str] = None, at: Any = None) -> Dict[str, Any]:
    """File a pending proposal (referendum from the AI, or amendment from a human). Returns
    the stored proposal. Raises ValueError if the typed proposal is malformed — a
    referendum, like any rule, must be coherent before it can even be reviewed."""
    problem = validate(kind, effect)
    if problem:
        raise ValueError(f"invalid proposal: {problem}")
    pid = id or ("r-" + _short_id())
    prop = {"id": pid, "origin": origin, "kind": kind, "text": text,
            "effect": effect or {}, "proposed_weight": int(proposed_weight),
            "prompted_by": prompted_by, "status": "pending"}
    if at is not None:
        prop["at"] = at
    data = _load(agent)
    data[pid] = prop
    _save(agent, data)
    return prop


def pending(agent: Optional[str]) -> List[Dict[str, Any]]:
    """The proposals still awaiting the operator, newest-id-sorted."""
    return [p for _, p in sorted(_load(agent).items()) if p.get("status") == "pending"]


def get(agent: Optional[str], pid: str) -> Optional[Dict[str, Any]]:
    return _load(agent).get(pid)


def reject(agent: Optional[str], pid: str) -> bool:
    """Mark a proposal rejected (kept for the record). False if it isn't pending."""
    data = _load(agent)
    p = data.get(pid)
    if not p or p.get("status") != "pending":
        return False
    p["status"] = "rejected"
    _save(agent, data)
    return True


def to_rule(prop: Dict[str, Any], weight: int) -> Dict[str, Any]:
    """The RULE a proposal becomes once the operator assigns the final weight — the object
    inserted into the contract's ``rules[]``. The AI proposed a weight; the human decides."""
    return {"w": int(weight), "kind": prop["kind"], "text": prop["text"],
            "effect": prop.get("effect") or {}}


def mark_enacted(agent: Optional[str], pid: str, weight: int) -> bool:
    """Record that a proposal was enacted at `weight` (after the contract re-sign)."""
    data = _load(agent)
    p = data.get(pid)
    if not p:
        return False
    p["status"] = "enacted"
    p["enacted_weight"] = int(weight)
    _save(agent, data)
    return True


def _short_id() -> str:
    """A short, filesystem/URL-safe proposal id. Random so ids don't collide across runs."""
    import secrets
    return secrets.token_hex(3)
