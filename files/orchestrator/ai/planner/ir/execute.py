"""
execute.py — the visitor. One case per op, and that is the whole executor.

The design note's claim is that this is small: "one visitor, ~6 cases". It is.

WHAT THIS IS NOT: a trusted region. Every effect leaves through the `execute` callable
the caller supplies, which in production is the gated `execute_tool` — so contract gate,
checkpoint, ledger and audit apply per statement exactly as they do to a leaf today. A
`delete_vm` inside a program meets the same double confirmation it meets in chat.
Passing the bench world's `execute` instead is what makes the same visitor testable.

NAME MINTING. `new` has to produce a name before any tool runs, and the name must be
STABLE — a re-entry has to mint the same one, or a re-planned program duplicates
everything it already built. That is the 5→10→15 cascade the harness hit for real, and
the reason `_cardinal_create_steps` mints vm1..vmN deterministically rather than letting
the model invent names. Same rule here: position and index, never a counter or a clock.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from . import config, refs
from .validate import coerce_body, validate


class Unsatisfied(Exception):
    """An `ensure` did not hold. Carries the predicate so the caller can feed the
    OBJECTION into revision rather than just reporting failure — the existing
    self-correction path already takes a complaint."""

    def __init__(self, predicate, detail=""):
        super().__init__(detail or "postcondition not satisfied")
        self.predicate = predicate
        self.detail = detail


def _resolve(value: Any, scope: Dict[str, Any]) -> Any:
    """Substitute $references from scope; leave everything else alone.

    Delegated to `refs` so the visitor and the validator cannot disagree about what a
    reference is — see that module for why a string is a template, not a name.
    """
    return refs.resolve(value, scope)


def _mint(kind: str, var: str, i: int, n: int) -> str:
    """A stable name for the i-th resource `var` binds. Deterministic in (var, i) so a
    re-run mints the same names and the executor no-ops instead of duplicating."""
    return var if n == 1 else f"{var}{i + 1}"


def run(program: Any, execute: Callable[[str, Dict], Any], *,
        select: Optional[Callable[[Dict], List[str]]] = None,
        holds: Optional[Callable[[Dict, Dict], Tuple[bool, str]]] = None,
        params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run a program. Returns {ok, scope, calls, failed}.

    `select` answers a registry query (kind + attribute filters) -> member names, and
    `holds` answers a predicate -> (bool, why). Both are INJECTED rather than implemented
    here: the registry lives in the Active Library and reachability lives in the findings
    ledger, and this module has no business reaching into either. It also means the bench
    world can drive the same visitor the orchestrator does.
    """
    ok, problems = validate(program)
    if not ok:
        return {"ok": False, "failed": "invalid", "problems": problems,
                "scope": {}, "calls": []}

    body = coerce_body(program) or []
    scope: Dict[str, Any] = dict(params or {})
    calls: List[Tuple[str, Dict]] = []
    failures: List[Dict[str, Any]] = []
    asserted = False        # did any ENSURE actually vouch for the end state?

    def _do(tool: str, args: Dict) -> Any:
        """Run one call and NOTICE whether it worked.

        This discarded the result, so a program whose every call failed still reported
        ok — the false-success class living in the executor itself, which is the one
        thing the rest of this system is built to refuse. Found by rung 12: the model
        omitted a required argument, both snapshot calls were rejected by the world, and
        the program cheerfully closed green over zero snapshots.

        Failures are RECORDED, not fatal. A call can fail because its effect already
        exists, and that is not a broken run — which is why the authority on "did this
        work" is the ENSURE, not the call. But a program with failures and NO ensure has
        vouched for nothing, and is not allowed to pass: unverified is not done.
        """
        calls.append((tool, args))
        result = execute(tool, args)
        if isinstance(result, dict) and (result.get("success") is False or result.get("error")):
            failures.append({"tool": tool, "args": args,
                             "error": result.get("error") or "call reported failure"})
        return result

    def _holds(pred: Dict, scope: Dict) -> tuple:
        """A predicate's verdict. `is` reads a GRAFTED result out of scope; everything
        else asks the injected evaluator, which reads the world. Keeping that split here
        means the caller never has to know which predicates are about state and which are
        about what a call just said."""
        spec = config.PREDICATES.get(pred.get("shape")) or {}
        if spec.get("arity") == "value":
            ref = str(pred.get("of", ""))[len(config.SIGIL):]
            name, _, path = ref.partition(".")
            val = scope.get(name)
            for part in filter(None, path.split(".")):
                val = val.get(part) if isinstance(val, dict) else None
            want = next((pred[c] for c in spec["comparators"] if c in pred), None)
            return val == want, f"{pred.get('of')} is {val!r}, wanted {want!r}"
        if holds is None:
            return False, "no predicate evaluator"
        return holds(_resolve(pred, scope), scope)

    def _block(stmts: List[Dict]) -> Optional[Dict]:
        """Run statements in order. Returns a failure dict, or None if all ran."""
        for st in stmts:
            bad = _one(st)
            if bad is not None:
                return bad
        return None

    def _one(st: Dict) -> Optional[Dict]:
        op = st.get("op")
        before = len(failures)

        if op == "if":
            good, _why = _holds(st.get("cond") or {}, scope)
            return _block(st.get("then" if good else "else") or [])

        if op == "new":
            kind = st["kind"]
            spec = config.KINDS[kind]
            # Which creator runs is decided by whether `from` is present — a machine can
            # be built fresh or copied, and choosing between them by a field rather than a
            # keyword keeps the choice out of the language.
            creators = spec.get("creators") or {}
            source = _resolve(st.get("from"), scope) if st.get("from") else None
            chosen = (next((c for c in creators.values() if c.get("from")), None)
                      if source else None) or creators.get("create") or {"tool": spec.get("create")}
            key_arg = chosen.get("key") or spec["key"]
            n = _resolve(st.get("amount", 1), scope)
            n = int(n) if isinstance(n, (int, str)) and str(n).isdigit() else 1
            names = [_mint(kind, st["var"], i, n) for i in range(n)]
            # Everything else the creator takes rides along — os_type, cpu_cores,
            # memory_mb. With count > 1 each resource is created with the SAME args,
            # which is the natural reading of "create 5 vms with 4GB each".
            extra = _resolve(st.get("args") or {}, scope)
            for nm in names:
                call_args = {**extra, key_arg: nm}
                if source and chosen.get("from"):
                    call_args[chosen["from"]] = source
                _do(chosen["tool"], call_args)
            # One resource binds its name; several bind the LIST, so `foreach in` can
            # iterate what was just created — before it has any attribute to query by.
            scope[st["var"]] = names[0] if n == 1 else names

        elif op == "call":
            result = _do(st["tool"], _resolve(st.get("args") or {}, scope))
            # A grafted result enters scope under its name, so a later statement — usually
            # an `if` — can read what the call actually said.
            if st.get("graft"):
                scope[st["graft"]] = result

        elif op == "foreach":
            if st.get("in") is not None:
                # A literal list is already the members; a $reference resolves to them.
                members = _resolve(st["in"], scope)
                members = members if isinstance(members, list) else [members]
            else:
                if select is None:
                    return {"ok": False, "failed": "no select evaluator",
                            "scope": scope, "calls": calls}
                members = select(_resolve(st["select"], scope))
            # `async` is accepted and runs serially here. Concurrency is a real execution
            # change — it forces the query-freshness question, since a parallel loop can
            # mutate the set it is iterating — and shipping the FLAG before the semantics
            # would let programs be written against behaviour that does not exist yet.
            inner = st["call"]
            for m in members:
                _do(inner["tool"],
                    _resolve(inner.get("args") or {}, {**scope, config.LOOP_VAR: m}))

        elif op == "ensure":
            if holds is None:
                return {"ok": False, "failed": "no predicate evaluator",
                        "scope": scope, "calls": calls}
            asserted = True
            good, why = holds(_resolve(st["predicate"], scope), scope)
            if not good:
                # A failed postcondition is a PLAN failure with a reason, not a crash —
                # the caller routes it to revision the way an unverified close already is.
                return {"ok": False, "failed": "unsatisfied", "why": why,
                        "predicate": st["predicate"], "scope": scope, "calls": calls,
                        "failures": failures}
        # IFAILS: recovery runs only if THIS statement's calls actually failed. Scoping it
        # to one statement is why you know what broke — and the failure stays recorded, so
        # a recovery compensates rather than conceals.
        if len(failures) > before and st.get("ifails"):
            _block(st["ifails"])
        return None

    for st in body:
        bad = _one(st)
        if bad is not None:
            return bad
    op = None

    if failures and not asserted:
        # Nothing vouched for the end state and calls failed: there is no basis for a
        # green close. With an ENSURE present its verdict stands — a failure it tolerated
        # is one that did not matter.
        return {"ok": False, "failed": "calls_failed", "scope": scope, "calls": calls,
                "failures": failures,
                "why": f"{len(failures)} call(s) failed and no ensure checked the result: "
                       + "; ".join(f"{f['tool']}: {f['error']}" for f in failures[:3])}
    return {"ok": True, "scope": scope, "calls": calls, "failed": None,
            "failures": failures}
