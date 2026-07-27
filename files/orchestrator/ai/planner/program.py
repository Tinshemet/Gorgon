"""
program.py — the two seams that let a MEDUSA program run against the real lab.

`ir.run` takes its world through injection: `execute` issues tool calls, `select` answers
a query over current state, `holds` answers a predicate. The bench fills all three with a
simulator. This fills the two that need the orchestrator — and it lives HERE rather than
in `ir/` for the reason the design philosophy gives: a module that hard-depends on one
package belongs in that package. The language must never import the Active Library, or it
stops being a language and becomes part of the planner.

WHY `select` IS A NET DELETION, eventually. The design note (§05) says SELECT "REPLACES
hand-written Active Library accessors — `fleets()` is a GROUP BY on labels,
`by_network()` a join through membership". Those accessors still exist and still have
callers outside the planner (the context assistant reads them), so this does not delete
them today. It makes them EXPRESSIBLE, which is the precondition:

    fleets()[tag]     == select({"kind": "vm", "label": tag})
    by_os()[os]       == select({"kind": "vm", "os_type": os})
    by_network()[net] == select({"kind": "vm", "network": net})

Retiring them is a caller audit, not a language question, and claiming the deletion
without doing it would be the SSOT collapse this codebase keeps refusing — two query
paths over one registry.

THE ONE THING THIS FILE MUST NOT GET WRONG: it has to answer a query exactly as the bench
seam does, for every construct — equality, aliases, membership (INCLUDE), the carve-out
(EXCEPT), any/all groups, and observed attributes. A production select that quietly
disagrees with the one every rung was measured against would make the benchmark a
statement about a simulator. `tests/test_medusa_invariants.py` holds the two side by side
for exactly that reason.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .ir import config, evaluate, observe, refs


def _members_of(library, net: str) -> set:
    """Which VMs sit on a network. Membership lives in the network compartment, not on
    the VM record — the same split the bench mirrors deliberately."""
    rec = (getattr(library, "_networks", None) or {}).get(net) or {}
    return set(rec.get("members") or ())


def _networks_of(library, name: str) -> set:
    """The networks one VM is on — the join the VM record does not carry."""
    return {net for net, rec in (getattr(library, "_networks", None) or {}).items()
            if name in set((rec or {}).get("members") or ())}


def _carried(record: Dict[str, Any]) -> set:
    """A VM's tags: labels ∪ flags, the same union `fleets()` groups by. Two sources for
    one concept, joined here rather than making every caller remember both."""
    return set(record.get("labels") or ()) | set(record.get("flags") or ())


def make_select(library, findings=None) -> Callable[..., List[str]]:
    """A registry query -> the matching member names.

    Answers the whole filter language: equality, the harness's own synonyms, membership
    (`{"in": [...]}` or a bound set), the carve-out, `any`/`all` groups, and observed
    attributes read from the findings ledger rather than the registry.
    """
    def _value(kind: str, name: str, record: Dict[str, Any], attr: str):
        """One member's value for one attribute, or a SET for the multi-valued ones."""
        if attr == "name":
            return name
        if attr == "label":
            return _carried(record)
        if attr == "network":
            return _networks_of(library, name)
        return record.get(attr)

    def _one(kind: str, name: str, record: Dict[str, Any], filters: Dict[str, Any],
             scope: Optional[Dict[str, Any]]) -> bool:
        # GROUPS FIRST — `any` is OR, `all` an explicit AND, each branch a filter set
        # answered by this same function, so a group can never mean something the flat
        # form does not.
        for group, combine in (("any", any), ("all", all)):
            kids = filters.get(group)
            if isinstance(kids, list) and kids:
                if not combine(_one(kind, name, record, k, scope) for k in kids):
                    return False
        aliases = (config.KINDS.get(kind) or {}).get("aliases") or {}
        for raw, want in filters.items():
            if raw in ("kind", "not", "any", "all"):
                continue
            attr = aliases.get(raw, raw)
            # OBSERVED attributes come from the ledger, never the registry, and the rule
            # that `unknown` matches neither `true` nor `false` lives in ONE place so a
            # second seam cannot get it wrong — which is the whole point of observe.py.
            verdict = observe.matches(findings, kind, attr, name,
                                      want if not isinstance(want, dict) else "")
            if verdict is not None and not isinstance(want, dict):
                if not verdict:
                    return False
                continue
            got = _value(kind, name, record, attr)
            # MEMBERSHIP: the attribute is ANY of these.
            if isinstance(want, dict) and "in" in want:
                listed = want["in"]
                if isinstance(listed, str):
                    listed = refs.resolve(listed, scope or {})
                listed = set(listed if isinstance(listed, (list, tuple, set)) else [listed])
                if isinstance(got, set):
                    if not (got & listed):
                        return False
                elif got not in listed:
                    return False
                continue
            # EQUALITY. Written as equality even for the multi-valued ones, because that
            # is how an operator says it — "is it on core" — and a reader should not have
            # to learn which attributes happen to hold several values.
            if isinstance(got, set):
                if want not in got:
                    return False
            elif str(got) != str(want):
                return False
        return True

    def select(sel: Dict[str, Any], scope: Optional[Dict[str, Any]] = None) -> List[str]:
        if not isinstance(sel, dict):
            return []
        kind = sel.get("kind") or "vm"
        spec = config.KINDS.get(kind) or {}
        carve = sel.get("not") or {}
        if kind == "network":
            nets = sorted((getattr(library, "_networks", None) or {}))
            return [n for n in nets
                    if _one(kind, n, {"net_name": n,
                                      "members": sorted(_members_of(library, n))}, sel, scope)
                    and not (carve and _one(kind, n, {"net_name": n}, carve, scope))]
        records = getattr(library, f"_{kind}s", None)
        if records is None:
            records = getattr(library, "_vms", None) or {}
        return [n for n, r in sorted(records.items())
                if _one(kind, n, r, sel, scope)
                and not (carve and _one(kind, n, r, carve, scope))]

    return select


def make_holds(library, findings=None) -> Callable[[Dict, Dict], Tuple[bool, str]]:
    """A predicate -> (verdict, why).

    Only the shapes whose truth comes from the WORLD are answered here; composites and
    `is` are the language's own business and `evaluate()` handles them before this is
    ever called. Splitting it that way is what stopped composites from coming back
    "unevaluated" once already.
    """
    select = make_select(library, findings)

    def holds(pred: Dict[str, Any], scope: Dict[str, Any]) -> Tuple[bool, str]:
        shape = pred.get("shape")
        if shape == "count":
            n = len(select(pred.get("select") or {}, scope))
            for comparator, sym in (("eq", "=="), ("gte", ">="), ("lte", "<=")):
                if comparator in pred:
                    want = pred[comparator]
                    good = {"==": n == want, ">=": n >= want, "<=": n <= want}[sym]
                    return good, f"count is {n}, wanted {sym} {want}"
            return False, "count has no comparator"
        if shape == "reach":
            # REACHABILITY IS A FINDING, never an inference from a tool's success flag —
            # that is why the manifest gives this shape `source: findings` and why the
            # whole observed-attribute idea exists. A member nobody probed is UNKNOWN, and
            # unknown is not evidence of reach: unverified is not done.
            members = select(pred.get("select") or {}, scope)
            floor = int(pred.get("min", 2))
            if len(members) < floor:
                return False, f"reach over {len(members)} member(s), floor {floor}"
            unknown = [m for m in members
                       if observe.value(findings, "vm", "alive", m) == observe.unknown()]
            if unknown:
                return False, (f"reach is unestablished: {len(unknown)} of {len(members)} "
                               f"have not been probed ({', '.join(sorted(unknown)[:3])})")
            dead = [m for m in members
                    if observe.value(findings, "vm", "alive", m) == observe.FALSE]
            return (not dead), ("all members answered"
                                if not dead else f"no answer from {', '.join(sorted(dead))}")
        if shape == "disjoint":
            resolved, unbound = [], []
            for ref in (pred.get("sets") or []):
                val = refs.resolve(ref, scope) if isinstance(ref, str) else ref
                if isinstance(val, str) and refs.names(val):
                    unbound.append(ref)
                    continue
                resolved.append({val} if isinstance(val, str) else set(val or ()))
            if unbound or len(resolved) < 2:
                return False, (f"disjoint needs two or more bound sets; "
                               f"{', '.join(unbound) or 'too few'} not in scope")
            overlap = set()
            for i, a in enumerate(resolved):
                for b in resolved[i + 1:]:
                    overlap |= (a & b)
            return (not overlap), ("no shared member" if not overlap
                                   else f"shared: {', '.join(sorted(overlap))}")
        return False, f"unevaluated shape {shape}"

    return holds


def seams(library, findings=None):
    """Both seams at once — what a caller actually wants."""
    return make_select(library, findings), make_holds(library, findings)


def make_run_program(library, findings=None, known_names=None, consent=True,
                     intent=None, say=None):
    """The `run_program` hook the Engine takes: (args, node_goal, call) -> outcome.

    `call` is the ENGINE'S guarded executor, handed in rather than taken. That is the
    whole safety property: a program's statements reach the world only through the same
    gauntlet a leaf meets — legal filter, commit gate, reason gate, contract tier and its
    checkpoint, watchdog, killswitch — so "the program body is NOT a trusted region" is
    enforced by construction rather than promised in a comment.

    Returns `{"invalid": True, "problems": [...]}` when the program does not validate. The
    caller falls back to a primitive on that, which is the doctrine regime_probe states:
    a wrong regime choice is cheap, because the path that works today is still there.

    THE SCHEMA GATE SITS BETWEEN VALIDATE AND RUN, which is the only place it can: after
    the program is well-formed and before anything happens. `say` is the operator's
    surface and `reauthor` is the author's, both injected — the same pattern `consent` and
    `referendum` already use — so one gate serves the planner and the chat and they differ
    only in where the clarification happens.
    """
    from .ir import gate as _gate, render, run, validate

    select, holds = seams(library, findings)

    def run_program(args: Dict[str, Any], node_goal: str, call,
                    reauthor=None) -> Dict[str, Any]:
        ok, problems = validate(args, known_names=known_names)
        if not ok:
            return {"invalid": True, "problems": problems}

        args = _gated(args, node_goal, reauthor)
        if args is None:
            # A REFUSAL LANDS ON THE PATH THAT ALREADY EXISTS. `invalid` is what the
            # engine falls back to a primitive on, and a gate refusal is the same kind of
            # answer as a validation failure: this program is not the way to do it. Giving
            # the refusal its own outcome would have meant a second fallback path doing
            # the same thing.
            return {"invalid": True, "problems": _last_reasons[0]}

        result = run(args, call, select=select, holds=holds,
                     known_names=known_names, consent=consent, intent=intent)
        # `asserted` is what the node needs to tell DONE from UNVERIFIED: a program that
        # acted and vouched for nothing has established nothing, which is the language's
        # one soundness rule arriving at the tree.
        body = args.get("body") if isinstance(args, dict) else None
        result["asserted"] = any(
            isinstance(st, dict) and st.get("op") in ("ensure", "achieve")
            for st in (body or []))
        result["rendered"] = render(args)
        return result

    _last_reasons = [[]]

    def _gated(args, node_goal, reauthor):
        """The gate's verdict as a program to run, or None to refuse.

        NO REAUTHOR MEANS NO SUPPRESSION, and that asymmetry is deliberate. A caller with
        nobody to re-ask can still act on a REFUSAL — refusing needs no second opinion —
        but suppressing a CLARIFY it cannot fix would leave the operator with nothing at
        all, in exchange for a program that still has to pass its own ENSURE before
        anything is claimed. So the reasons are announced and the program runs. Being told
        "this looked thin and I ran it anyway" is worth more than silence plus a dead end.
        """
        verdict = _gate.score(args, node_goal, intent)
        _last_reasons[0] = verdict["reasons"] or ["the gate refused this program"]
        if verdict["band"] == _gate.PROCEED:
            return args
        if reauthor is None:
            if verdict["band"] == _gate.REFUSE:
                _gate._tell(say, _gate.MESSAGES[_gate.REFUSE].format(
                    reason="; ".join(_last_reasons[0]), score=verdict["score"]))
                return None
            _gate._tell(say, _gate.MESSAGES[_gate.CLARIFY].format(
                reason="; ".join(_last_reasons[0]) + " [nobody to re-ask]",
                score=verdict["score"]))
            return args
        out = _gate.clarify(args, node_goal, intent, reauthor, say=say)
        _last_reasons[0] = out["reasons"] or _last_reasons[0]
        return out["program"] if out["band"] == _gate.PROCEED else None

    return run_program
