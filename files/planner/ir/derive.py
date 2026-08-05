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
from .intent import ACHIEVE as _ACHIEVE


def derive(predicate: Dict[str, Any], select: Callable[[Dict], List[str]],
           scope: Optional[Dict[str, Any]] = None,
           intent: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """Statements that would make `predicate` hold, or None if it cannot be derived.

    None is a real answer and must stay distinguishable from []: "I cannot close this
    gap" is not "nothing needs doing". The caller falls back to asking the model on None
    and stops on [].

    `intent` is what the OPERATOR asked for, and it is what decides whether the world may
    be corrected DOWNWARD. ACHIEVE means MAKE SURE — the operator: *"creation and
    modifications and even deletions are allowed in achieve, given correct intent... it CAN
    CHANGE the world to meet the goal, that's the correction part of it."* So the gate is
    the intent, never the sign of the difference. Absent (None) is conservative and derives
    nothing destructive, because a caller that has not said what the operator wants has not
    established that removal was asked for.

    THIS IS NOT WHERE DELETION IS MADE SAFE. A derived call meets consent, the contract
    tier and delete_vm's double confirmation on its way to the world exactly as an authored
    one does. Refusing here duplicated a judgement that already has an owner and broke the
    language's own promise that an ACHIEVE is a legal way to state a goal.
    """
    if not isinstance(predicate, dict):
        return None
    shape = predicate.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return None
    fn = _DERIVERS.get(shape)
    return fn(predicate, select, scope or {}, intent) if fn else None


# The name a derived creation binds. Fixed rather than minted, so a re-derivation of the
# same gap produces the same program — the idempotence this module promises in its own
# docstring.
_MADE = "_derived"


def _creator_args(kind: str) -> Optional[Dict[str, Any]]:
    """What a DERIVED `NEW kind` passes to the creator, or None if it cannot be derived.

    `NEW` supplies the resource's own name, so only the OTHER required arguments matter.
    Each must be declared in the kind's `create_defaults`; a required argument with no
    declaration returns None and the gap goes to the author. That boundary is the whole
    point — a value in the manifest is the operator's declared intent, identical on every
    derivation and visible to anyone reading it, where a value invented here would differ
    per call and appear nowhere. See _create_defaults_doc.
    """
    try:
        from executor.command_catalog import REQUIRED_FIELDS
    except ImportError:                                    # pragma: no cover
        REQUIRED_FIELDS = {}
    spec = config.KINDS.get(kind) or {}
    key = spec.get("key", "name")
    defaults = spec.get("create_defaults") or {}
    # ONLY the resource's OWN name is excluded — that is what NEW supplies. Excluding the
    # literal "name" as well looked equivalent and is not: snapshot_create's `name` is the
    # SOURCE vm, so a kind that genuinely cannot be derived reported that it could.
    needed = [a for a in (REQUIRED_FIELDS.get(spec.get("create")) or [])
              if a != key]
    if any(a not in defaults for a in needed):
        return None
    return {a: defaults[a] for a in needed}


def _derive_count(pred, select, scope, intent=None) -> Optional[List[Dict[str, Any]]]:
    """COUNT(set) eq/gte/lte N — add or remove membership until the count is right.

    Membership here means a LABEL, which is the only count the manifest can currently
    act on: `label` is the one queryable attribute with a tool that both sets and clears
    it. A count over a kind's existence would mean creating or DELETING resources, and
    deriving a deletion from a predicate is not something to do without an operator
    saying so — so that case returns None rather than guessing.
    """
    sel = pred.get("select") or {}
    label = sel.get("label", sel.get("tag"))
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
        if n > want:                       # too many
            if cmp_ == "gte":
                return []
            # CORRECT DOWNWARD TOO, WHEN THE INTENT ALLOWS IT. ACHIEVE means MAKE
            # SURE, and making sure is symmetric: too few is closed by creating, too many
            # by removing. What decides whether removal is permitted is the OPERATOR'S
            # INTENT — under `fetch` or `ensure` nothing may act at all, under `achieve`
            # the world may be corrected. The sign of the difference decides nothing.
            #
            # Dropping a LABEL is not removing a resource, so that path (below) needs no
            # intent. Removing the resource itself does.
            if not label:
                if intent != _ACHIEVE:
                    return None
                tool = (config.KINDS.get(sel.get("kind", "vm")) or {}).get("delete")
                if not tool:
                    return None        # no destroyer declared — ask the author
                key = (config.KINDS.get(sel.get("kind", "vm")) or {}).get("key", "name")
                return [{"op": "foreach", "in": sorted(current)[:n - want],
                         "call": {"tool": tool,
                                  "args": {key: f"{config.SIGIL}{config.LOOP_VAR}"}}}]
            surplus = sorted(current)[:n - want]
            return [{"op": "foreach", "in": surplus,
                     "call": {"tool": "remove_label",
                              "args": {"name": "$item", "label": label}}}]
        # too few: use what exists, and CREATE the rest
        if cmp_ == "lte":
            return []
        kind = sel.get("kind", "vm")
        pool = ([x for x in select({"kind": kind}) if x not in current]
                if label else [])
        need = want - n
        from_pool = min(need, len(pool))
        to_create = need - from_pool
        stmts: List[Dict[str, Any]] = []
        if to_create:
            args = _creator_args(kind)
            if args is None:
                return None            # a required argument nobody declared — ask the author
            stmts.append({"op": "new", "var": _MADE, "kind": kind,
                          "amount": to_create, "args": args})
        if label:
            if from_pool:
                stmts.append({"op": "foreach", "in": sorted(pool)[:from_pool],
                              "call": {"tool": "add_label",
                                       "args": {"name": "$item", "label": label}}})
            if to_create:
                stmts.append({"op": "foreach", "in": f"{config.SIGIL}{_MADE}",
                              "call": {"tool": "add_label",
                                       "args": {"name": "$item", "label": label}}})
        return stmts
    return None


def _derive_reach(pred, select, scope, intent=None) -> Optional[List[Dict[str, Any]]]:
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


def _derive_disjoint(pred, select, scope, intent=None) -> Optional[List[Dict[str, Any]]]:
    """DISJOINT(a, b) — cannot be closed without knowing which side should move.

    Detaching the overlap from either set satisfies the predicate and they are not
    equivalent acts: one of them is probably what the operator wanted and the other is
    probably damage. Explicitly not guessed.
    """
    return None


def _touches(plan: List[Dict[str, Any]]) -> set:
    """Every name a derived plan acts ON — what two plans must not share to be concatenable.

    Deliberately over-broad: every member a `foreach` walks AND every string argument of
    every call, so a derived network name counts as a touch too. Two plans that both mint
    `net_derived` interfere just as surely as two that relabel the same machine, and an
    over-broad reading DECLINES a safe pair where a narrow one would CONCATENATE an unsafe
    one. Only one of those errs toward doing nothing.
    """
    out = set()
    for st in plan or ():
        if not isinstance(st, dict):
            continue
        walked = st.get("in")
        if isinstance(walked, list):
            out |= {str(m) for m in walked}
        elif isinstance(walked, str):
            out.add(walked)
        for holder in (st.get("call"), st):
            for value in ((holder or {}).get("args") or {}).values():
                if isinstance(value, str) and not value.startswith(config.SIGIL):
                    out.add(value)
        out |= _touches(st.get("do") or st.get("body") or [])
    return out


def _derive_all(pred, select, scope, intent=None) -> Optional[List[Dict[str, Any]]]:
    """ALL(a, b, …) — every child closed, but ONLY when their plans cannot interfere.

    THE RECORDED REASON THIS WAS UNDERIVABLE, and it is a real one: *"a composite is only as
    derivable as its children, and combining their plans is a scheduling problem this layer
    deliberately does not have."* Concatenating two plans is not generally sound — one may
    undo what the other just did, and nothing here orders them.

    **BUT THE SCHEDULING PROBLEM ONLY EXISTS WHERE THE PLANS MEET.** Two plans that act on
    disjoint sets of names commute: running them in either order, or interleaved, reaches the
    same world, so concatenation is correct and no scheduler is needed. That is decidable by
    looking at what each plan touches, which is arithmetic and not a judgement — so this
    closes the case the reason was about and declines the case it was FOR.

    ANY CHILD THAT CANNOT BE DERIVED SINKS THE WHOLE THING. A partial plan for a conjunction
    is worse than none: it acts, changes the world, and still leaves the assertion false.
    """
    children = pred.get("of")
    if not isinstance(children, list) or not children:
        return None
    plans: List[List[Dict[str, Any]]] = []
    for child in children:
        fix = derive(child, select, scope, intent)
        if fix is None:
            return None
        plans.append(fix)
    seen: set = set()
    for plan in plans:
        touched = _touches(plan)
        if touched & seen:
            return None                    # they meet — that IS the scheduling problem
        seen |= touched
    return [st for plan in plans for st in plan]


def _derive_not(pred, select, scope, intent=None) -> Optional[List[Dict[str, Any]]]:
    """NOT(COUNT … >= n) — the inversion, and ONLY where the order makes it determinate.

    THE RECORDED REASON, and it is right in general: *"satisfying NOT(x) means any world
    where x is false, and choosing one is a decision, not a computation."*

    **A COUNT IS TOTALLY ORDERED, SO ONE FAMILY OF NEGATIONS IS NOT A CHOICE.** `NOT(c >= n)`
    is `c <= n-1` and `NOT(c <= n)` is `c >= n+1` — each names one bound, and closing it is
    exactly what `_derive_count` already does for a bound an operator wrote directly. There
    is no decision here that writing `<=` by hand would not also have made, so refusing this
    while accepting that was never a consistent position.

    `eq` IS STILL A CHOICE and stays refused: `NOT(c = 3)` is satisfied by two and by four,
    the difference is creation versus deletion, and nothing in the predicate says which.
    Neither is a non-count child — the reason holds in full for anything without an order.

    `NOT(c >= 0)` INVERTS TO `c <= -1`, WHICH NO WORLD SATISFIES. Returning None says the gap
    cannot be closed, which is true, rather than deriving a plan that would delete everything
    and still fail.
    """
    inner = pred.get("of")
    if not isinstance(inner, dict) or inner.get("shape") != "count":
        return None
    flipped = dict(inner)
    if "gte" in inner:
        flipped.pop("gte")
        flipped["lte"] = int(inner["gte"]) - 1
    elif "lte" in inner:
        flipped.pop("lte")
        flipped["gte"] = int(inner["lte"]) + 1
    else:
        return None
    if int(flipped.get("lte", 0)) < 0:
        return None
    return _derive_count(flipped, select, scope, intent)


# `disjoint` IS DECLARED UNDERIVABLE RATHER THAN GIVEN A DERIVER THAT ALWAYS SAYS None.
# It had the stub, which passed `test_every_predicate_shape_declares_whether_it_can_be_derived`
# by HAVING an entry here — and that test exists to stop exactly this: *"a shape that silently
# cannot converge is indistinguishable from one nobody has written a deriver for yet."* A stub
# returning None unconditionally IS that shape, wearing a deriver's clothes. The reason it
# cannot be closed now lives in the manifest beside the other three, where the invariant reads
# it. See `_derive_disjoint` above, kept for the reason it records.
_DERIVERS = {"count": _derive_count, "reach": _derive_reach,
             "all": _derive_all, "not": _derive_not}
