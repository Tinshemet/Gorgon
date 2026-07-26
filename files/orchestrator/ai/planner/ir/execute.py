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

from . import config
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
    """Substitute $references from scope; leave everything else alone."""
    if isinstance(value, str) and value.startswith(config.SIGIL):
        return scope.get(value[len(config.SIGIL):], value)
    if isinstance(value, dict):
        return {k: _resolve(v, scope) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, scope) for v in value]
    return value


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

    def _do(tool: str, args: Dict) -> Any:
        calls.append((tool, args))
        return execute(tool, args)

    for st in body:
        op = st.get("op")

        if op == "new":
            kind = st["kind"]
            spec = config.KINDS[kind]
            n = _resolve(st.get("count", 1), scope)
            n = int(n) if isinstance(n, (int, str)) and str(n).isdigit() else 1
            names = [_mint(kind, st["var"], i, n) for i in range(n)]
            # Everything else the creator takes rides along — os_type, cpu_cores,
            # memory_mb. With count > 1 each resource is created with the SAME args,
            # which is the natural reading of "create 5 vms with 4GB each".
            extra = _resolve(st.get("args") or {}, scope)
            for nm in names:
                _do(spec["create"], {**extra, spec["key"]: nm})
            # One resource binds its name; several bind the LIST, so `foreach in` can
            # iterate what was just created — before it has any attribute to query by.
            scope[st["var"]] = names[0] if n == 1 else names

        elif op == "call":
            _do(st["tool"], _resolve(st.get("args") or {}, scope))

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
            inner = st["call"]
            for m in members:
                _do(inner["tool"],
                    _resolve(inner.get("args") or {}, {**scope, config.LOOP_VAR: m}))

        elif op == "ensure":
            if holds is None:
                return {"ok": False, "failed": "no predicate evaluator",
                        "scope": scope, "calls": calls}
            good, why = holds(_resolve(st["predicate"], scope), scope)
            if not good:
                # A failed postcondition is a PLAN failure with a reason, not a crash —
                # the caller routes it to revision the way an unverified close already is.
                return {"ok": False, "failed": "unsatisfied", "why": why,
                        "predicate": st["predicate"], "scope": scope, "calls": calls}

    return {"ok": True, "scope": scope, "calls": calls, "failed": None}
