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

from . import config, consent as _consent, refs
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


def evaluate(pred: Dict, scope: Dict, leaf: Optional[Callable]) -> Tuple[bool, str]:
    """A predicate's verdict: composites and grafted values here, world queries delegated.

    Module-level ON PURPOSE. This lived inside run()'s closure, which meant only the
    visitor could use it — so every OTHER caller that needed a verdict (the bench's goal
    re-check, any harness re-testing a goal after a revision) called the injected leaf
    evaluator directly and silently lost composites and IS(). They came back "unevaluated
    shape all", which a postcondition then counted as FAILED. Logic that more than one
    caller needs cannot live in a closure.

      not/all/any  pure logic over other verdicts — no world access, so the language
                   answers them and no evaluator has to reimplement boolean algebra
      is           reads a grafted result out of scope, not the world
      everything   delegated to `leaf`, which is the registry or the findings ledger
    """
    spec = config.PREDICATES.get(pred.get("shape")) or {}

    if spec.get("source") == "composite":
        shape = pred.get("shape")
        kids = pred.get("of") or []
        kids = kids if isinstance(kids, list) else [kids]
        verdicts = [evaluate(k, scope, leaf) for k in kids if isinstance(k, dict)]
        if not verdicts:
            return False, f"{shape} has nothing to combine"
        if shape == "not":
            good, why = verdicts[0]
            return (not good), f"NOT({why})"
        if shape == "all":
            bad = [w for g, w in verdicts if not g]
            return (not bad), ("all held" if not bad else "; ".join(bad))
        if shape == "any":
            good = any(g for g, _ in verdicts)
            return good, ("one held" if good
                          else "none held: " + "; ".join(w for _, w in verdicts))
        return False, f"unknown composite {shape}"

    if spec.get("arity") == "value":
        ref = str(pred.get("of", ""))[len(config.SIGIL):]
        name, _, path = ref.partition(".")
        val = scope.get(name)
        for part in filter(None, path.split(".")):
            val = val.get(part) if isinstance(val, dict) else None
        want = next((pred[c] for c in spec["comparators"] if c in pred), None)
        return val == want, f"{pred.get('of')} is {val!r}, wanted {want!r}"

    if leaf is None:
        return False, "no predicate evaluator"
    return leaf(pred, scope)


def run(program: Any, execute: Callable[[str, Dict], Any], *,
        select: Optional[Callable[[Dict], List[str]]] = None,
        holds: Optional[Callable[[Dict, Dict], Tuple[bool, str]]] = None,
        params: Optional[Dict[str, Any]] = None,
        known_names: Optional[set] = None,
        consent: Any = None) -> Dict[str, Any]:
    """Run a program. Returns {ok, scope, calls, failed}.

    `select` answers a registry query (kind + attribute filters) -> member names, and
    `holds` answers a predicate -> (bool, why). Both are INJECTED rather than implemented
    here: the registry lives in the Active Library and reachability lives in the findings
    ledger, and this module has no business reaching into either. It also means the bench
    world can drive the same visitor the orchestrator does.
    """
    ok, problems = validate(program, known_names=known_names)
    if not ok:
        return {"ok": False, "failed": "invalid", "problems": problems,
                "scope": {}, "calls": []}

    # GROUNDING. A program that changes the world and never checks it needs the
    # operator's word first — see consent.py. Refused BEFORE the first call, because a
    # question asked halfway through is not a question, it is a notification.
    if not _consent.granted(program, consent):
        return {"ok": False, "failed": "ungrounded", "why": _consent.question(program),
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
        """This program's predicate verdict — the shared evaluator, bound to the
        injected leaf reader."""
        return evaluate(pred, scope, holds)

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
            inner = st.get("call")
            block = st.get("do")
            for m in members:
                if inner is not None:
                    _do(inner["tool"],
                        _resolve(inner.get("args") or {}, {**scope, config.LOOP_VAR: m}))
                    continue
                # A BLOCK body, scoped per iteration. The member is bound for the pass and
                # anything the body binds is discarded at the end of it — so `graft` inside
                # a loop names THIS member's answer, and the next pass cannot read the last
                # one's. The alternative, accumulating a list, is a different feature; a
                # per-item conditional needs this one, and quietly providing the other
                # would make `IF IS($answer.alive)` mean "the answer from some earlier
                # machine", which is worse than not having it.
                outer = dict(scope)
                scope[config.LOOP_VAR] = m
                bad = _block(block)
                scope.clear()
                scope.update(outer)
                if bad is not None:
                    return bad

        elif op in ("ensure", "achieve"):
            if holds is None:
                return {"ok": False, "failed": "no predicate evaluator",
                        "scope": scope, "calls": calls}
            # `nonlocal`, or this binds a fresh local that dies with the call and the
            # outer flag stays False forever. It did: the "with an ENSURE present its
            # verdict stands" rule three lines from here has never once fired, so a
            # grounded program that tolerated a failed call — the ordinary shape of a
            # RE-RUN, where creation fails because the thing already exists — was
            # reported as calls_failed anyway. The passing postcondition was computed,
            # believed, and then ignored.
            nonlocal asserted
            asserted = True
            # `_holds`, not the injected `holds`. The ensure branch called the evaluator
            # DIRECTLY, so it skipped the language's own predicate handling entirely:
            # composites came back "unevaluated shape all" and `IS(...)` could not read a
            # grafted result at all. Only `if` went through _holds, which is why the gap
            # stayed hidden — the conditional worked and the postcondition did not.
            good, why = _holds(_resolve(st["predicate"], scope), scope)
            if not good:
                # A failed check is a PLAN failure with a reason, not a crash — the caller
                # routes it to revision the way an unverified close already is. WHICH
                # failure it is decides who answers it, and that is the whole point of
                # having two words:
                #
                #   ensure  — a ground check. The world is not what the program assumed,
                #             so the plan was built on something false. A model rethinks.
                #   achieve — the goal. The end state is short of what was asked, which is
                #             usually arithmetic, and the harness closes the difference
                #             (derive.py) because the model provably cannot: it oscillated
                #             6->5->7->5 with the state and the objection in hand.
                return {"ok": False,
                        "failed": "unachieved" if op == "achieve" else "unsatisfied",
                        "why": why, "predicate": st["predicate"], "scope": scope,
                        "calls": calls, "failures": failures}
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
