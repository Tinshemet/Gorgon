"""
derive.py — compute the statements that would satisfy an unmet predicate.

WHY THIS EXISTS, measured. Rung 7 is "make sure exactly 3 vms carry the 'prod' label"
against a world holding six. Given the right tool, the right construct, current state and
a precise objection every round, llama3.1 oscillated: 6 -> remove 2 -> 5 -> ADD 2 -> 7 ->
remove 3 -> 5. It never computed "six exist, three are wanted, remove three". That is a
capability limit, not an expressiveness one — no prompt or schema moves it.

The harness computes it in one line. So it should.

This is the design note's deferred option 3 — "when a procedure is nothing but ENSURE
clauses, the harness MAY derive the plan" — and rung 7 is the evidence for promoting it
from optional to load-bearing. It is also why the note insists ENSURE be a PREDICATE over
the registry rather than a boolean expression: a predicate can be inverted into actions,
an opaque boolean cannot.

WHAT IT IS NOT. It does not read English, so it does nothing for the paraphrase gap —
that is the authoring path's job and is already measured. Its input is a typed predicate
and current state; its output is statements. Those two facts are the whole contract.

ONE DERIVER PER PREDICATE SHAPE, and that is deliberate: the vocabulary is data (the
manifest says a shape exists) but the SEMANTICS are code (what closes the gap). A new
shape needs a deriver, the same way a new op needs a visitor case. Better that be an
explicit gap than a silently unclosable predicate.

Every derivation is CONSERVATIVE: when the fix is ambiguous — which three of six labels
to drop — it acts on a deterministic slice (sorted order) so a re-run derives the same
plan and is idempotent, rather than picking differently each time.
"""

from typing import Any, Callable, Dict, List, Optional

from . import config


def derive(predicate: Dict[str, Any], select: Callable[[Dict], List[str]],
           scope: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
    """Statements that would make `predicate` hold, or None if it cannot be derived.

    None is a real answer and must stay distinguishable from []: "I cannot close this
    gap" is not "nothing needs doing". The caller falls back to asking the model on None
    and stops on [].
    """
    if not isinstance(predicate, dict):
        return None
    shape = predicate.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return None
    fn = _DERIVERS.get(shape)
    return fn(predicate, select, scope or {}) if fn else None


def _derive_count(pred, select, scope) -> Optional[List[Dict[str, Any]]]:
    """COUNT(set) eq/gte/lte N — add or remove membership until the count is right.

    Membership here means a LABEL, which is the only count the manifest can currently
    act on: `label` is the one queryable attribute with a tool that both sets and clears
    it. A count over a kind's existence would mean creating or DELETING resources, and
    deriving a deletion from a predicate is not something to do without an operator
    saying so — so that case returns None rather than guessing.
    """
    sel = pred.get("select") or {}
    label = sel.get("label", sel.get("tag"))
    if not label:
        return None
    current = select(sel)
    n = len(current)
    for cmp_ in ("eq", "gte", "lte"):
        if cmp_ not in pred:
            continue
        want = int(pred[cmp_])
        if cmp_ == "gte" and n >= want:
            return []
        if cmp_ == "lte" and n <= want:
            return []
        if cmp_ == "eq" and n == want:
            return []
        if n > want:                       # too many: drop the surplus
            if cmp_ == "gte":
                return []
            surplus = sorted(current)[:n - want]
            return [{"op": "foreach", "in": surplus,
                     "call": {"tool": "remove_label",
                              "args": {"name": "$item", "label": label}}}]
        # too few: label candidates that do not carry it yet
        if cmp_ == "lte":
            return []
        pool = [x for x in select({"kind": sel.get("kind", "vm")}) if x not in current]
        need = want - n
        if len(pool) < need:
            # Not enough existing resources to satisfy it. Creating them is a bigger
            # decision than closing a gap, so leave it to the model.
            return None
        return [{"op": "foreach", "in": sorted(pool)[:need],
                 "call": {"tool": "add_label",
                          "args": {"name": "$item", "label": label}}}]
    return None


def _derive_reach(pred, select, scope) -> Optional[List[Dict[str, Any]]]:
    """REACH(set) >= N — put every member on one common network.

    Creates the network only if the program did not already bind one; otherwise it
    attaches to what exists, so a re-derivation does not mint a second network.
    """
    sel = pred.get("select") or {}
    members = select(sel)
    if len(members) < int(pred.get("min", 2)):
        return None                        # too few members: not a connectivity problem
    net = next((v for k, v in (scope or {}).items()
                if isinstance(v, str) and k.lower().startswith("net")), None)
    out: List[Dict[str, Any]] = []
    if not net:
        net = "net_derived"
        out.append({"op": "call", "tool": "create_network", "args": {"net_name": net}})
    out.append({"op": "foreach", "in": sorted(members),
                "call": {"tool": "add_vm_to_network",
                         "args": {"net_name": net, "vm_name": "$item"}}})
    # AND THEN ASK. Attaching machines to one network does not make them reachable, it
    # makes them ADDRESSABLE — reachability is a finding, which is why the manifest gives
    # this shape `source: findings` and why an observed attribute reads `unknown` until
    # something probes. A derivation that stopped at the attach closed the BENCH's reach
    # (which asks only whether a network is shared) and left production's unestablished,
    # so the harness would have declared a goal met on evidence it never gathered. The
    # probe is part of the fix, not a step after it.
    out.append({"op": "foreach", "in": sorted(members),
                "call": {"tool": "guest_ping", "args": {"name": "$item"}}})
    return out


def _derive_disjoint(pred, select, scope) -> Optional[List[Dict[str, Any]]]:
    """DISJOINT(a, b) — cannot be closed without knowing which side should move.

    Detaching the overlap from either set satisfies the predicate and they are not
    equivalent acts: one of them is probably what the operator wanted and the other is
    probably damage. Explicitly not guessed.
    """
    return None


_DERIVERS = {"count": _derive_count, "reach": _derive_reach, "disjoint": _derive_disjoint}
