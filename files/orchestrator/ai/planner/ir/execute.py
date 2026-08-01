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

from . import config, consent as _consent, intent as _intent, refs
from .. import procedures as _procs
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


def _amount(raw: Any, scope: Dict[str, Any]) -> int:
    """How many to create: a number, a $reference, or the shortfall form.

    {"minus": [5, "$have"]} is "bring it up to five" — the ONLY arithmetic in the
    language, and it exists for one shape: read what the lab already has, create the
    difference. Clamped at zero, because a world that already exceeds the target needs
    nothing created, not a negative number of machines. Zero creates nothing and is a
    legal, expected outcome — it is what a satisfied re-run looks like.
    """
    if isinstance(raw, dict) and isinstance(raw.get("minus"), list):
        target, have = raw["minus"]
        got = _resolve(have, scope)
        got = got if isinstance(got, int) else (len(got) if isinstance(got, list) else 0)
        return max(0, int(target) - got)
    val = _resolve(raw, scope)
    if isinstance(val, bool):
        return 1
    if isinstance(val, int):
        return max(0, val)
    if isinstance(val, str) and val.lstrip("-").isdigit():
        return max(0, int(val))
    return 1


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


def follow_up(result: Dict[str, Any],
              correction: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The body to run after a correction: the fix, then the work that never ran.

    A correction closes the gap the PREDICATE named. It does not finish the program — the
    statements after the failed one were abandoned, and replaying only the correction
    leaves that work undone while the predicate now reports the goal as held. A green
    verdict over an unfinished program is the false-success class this system refuses
    everywhere else. Rung 4: the author put `ACHIEVE REACH(...)` before the
    `add_label(... fleet)` loop, the ACHIEVE failed, the tagging never happened, and the
    derived fix said the goal held.

    THE TAIL IS RESOLVED AGAINST THE SCOPE THE ABORTED RUN HELD, not carried as params.
    `FOREACH $item IN $machines` means nothing once `$machines` is gone, and `params`
    cannot express it — the declarable types are scalars, with no list among them. So the
    bound values are substituted in, exactly as `derive` already writes its corrections
    (`FOREACH $item IN [machines1, machines2, ...]`). `refs.resolve` leaves `$item` alone,
    because the loop variable is bound per iteration and is not the scope's to supply.

    One function because there are two correction paths — the whole-program probe and the
    tree probe — and two copies of this reasoning is how the seams and the standing-goal
    rule each came to have a stale twin.
    """
    remaining = [refs.resolve(st, result.get("scope") or {})
                 for st in (result.get("remaining") or [])]
    return {"body": list(correction) + remaining}


def run(program: Any, execute: Callable[[str, Dict], Any], *,
        select: Optional[Callable[[Dict], List[str]]] = None,
        holds: Optional[Callable[[Dict, Dict], Tuple[bool, str]]] = None,
        params: Optional[Dict[str, Any]] = None,
        known_names: Optional[set] = None,
        known_tools: Optional[set] = None,
        consent: Any = None,
        intent: Optional[str] = None,
        acting_tools: Optional[set] = None) -> Dict[str, Any]:
    """Run a program. Returns {ok, scope, calls, failed}.

    `select` answers a registry query (kind + attribute filters) -> member names, and
    `holds` answers a predicate -> (bool, why). Both are INJECTED rather than implemented
    here: the registry lives in the Active Library and reachability lives in the findings
    ledger, and this module has no business reaching into either. It also means the bench
    world can drive the same visitor the orchestrator does.
    """
    # `known_tools` reaches the LAST check too. This re-validates deliberately — a program
    # about to touch the world is the right place to look again — but it was checking
    # statements against the VM executor's registry regardless of who was running them, so a
    # second engine's program passed inspection and was then refused here as "invalid". A
    # gate that judges by a different standard than the one before it is worse than one
    # gate, because the disagreement is silent.
    # A STORED PROCEDURE IS A LEGAL CALL TARGET, and the validator has to be told or it
    # refuses the operator's own library as an unknown tool. Added rather than replaced:
    # a procedure EXTENDS what can be called and never licenses a tool that was refused.
    if known_tools is not None:
        known_tools = set(known_tools) | set(_procs.LIBRARY.names())
    ok, problems = validate(program, known_names=known_names, known_tools=known_tools)
    if not ok:
        return {"ok": False, "failed": "invalid", "problems": problems,
                "scope": {}, "calls": []}

    # AUTHORITY FIRST. A REQUEST was not given permission to change anything, so a
    # program written under one that contains an acting statement is refused outright —
    # before grounding, because "did you authorise this at all" precedes "did you check
    # your work". See intent.py: the operator decides, and it is enforced, not advised.
    promoted = None
    if intent is not None:
        # `acting_tools` TRAVELS BESIDE `known_tools` AND IS NOT THE SAME SET. One says what
        # may be called at all; this says which of them CHANGE something, and without it a
        # `fetch` cannot ask a question — every probe is a `CALL`, and the ladder is written
        # in ops. A caller holding a manifest supplies `effects.actors(manifest)`; one that
        # does not gets the fail-closed reading, where a call acts.
        exceeded = _intent.violations(program, intent, actors=acting_tools)
        if exceeded:
            return {"ok": False, "failed": "exceeds_authority", "problems": exceeded,
                    "why": exceeded[0], "scope": {}, "calls": []}
        # AND THE OTHER DIRECTION, which is not the same shape. Reaching ABOVE the granted
        # rung is a trespass and is refused; sitting BELOW it is a program that cannot
        # finish the job it was asked to do, and refusing that only costs a round.
        #
        # MEASURED 2026-07-30: granted ACHIEVE the author writes ENSURE for the standing
        # goal — a CHECK where it was licensed to CORRECT — and the whole convergence path
        # then becomes unreachable, because a failed non-achieve reports `unsatisfied` and
        # the deriver fires only for `unachieved`. Rung 7 shows it with nothing else
        # varying: the literal says "make sure", ACHIEVE's own phrase, and passes 3/3; the
        # paraphrase says "there should end up being" and fails 3/3.
        #
        # HERE rather than in each caller, because two probes and production would
        # otherwise each need their own copy — the stale-twin defect, invited. It runs
        # AFTER validation, so the promoted op is not a way to smuggle in a program the
        # validator would have refused.
        program, promoted = _intent.promote(program, intent)

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
        """Run statements in order. Returns a failure dict, or None if all ran.

        WHAT A NESTED BLOCK DROPS IS RECORDED. A failed predicate returns from here and
        every statement after it in this block is abandoned — and until 2026-08-01 nothing
        said so. The comment at the top-level loop CLAIMED these were "reported as
        unfinished"; they were not, which is this week's recurring defect arriving in the
        one place it is most expensive: a program can end having quietly not done most of
        its work while the result names only the top-level tail.

        THEY ARE NAMED, NOT RESUMED, and that is a real distinction rather than a
        limitation dressed up. A statement inside a `foreach` cannot be replayed by
        appending a suffix — its loop variable is gone, and so is the branch condition of
        an `if`. So the honest report is "this did not run and cannot simply be re-run",
        which is what an operator needs to decide what to do next.
        """
        for i, st in enumerate(stmts):
            bad = _one(st)
            if bad is not None:
                dropped = list(stmts[i + 1:])
                if dropped:
                    abandoned.extend(dropped)
                return bad
        return None

    # Statements inside a block that never ran because something before them failed. Kept
    # separate from `remaining`: that one is a resumable top-level tail, this one is not.
    abandoned: List[Dict[str, Any]] = []

    # WHAT THE PROGRAM ASKED TO SUBMIT. Carried out of the run so the engine can attach the
    # values it observed and hand them up — the upward half of the in-session protocol,
    # reaching it from the program rather than from an engine reading the ledger behind the
    # program's back.
    published: List[str] = []

    def _one(st: Dict) -> Optional[Dict]:
        op = st.get("op")
        before = len(failures)

        if op == "call" and _procs.LIBRARY.get(st.get("tool")) is not None:
            # A PROCEDURE IS A TOOL YOU WROTE, and this is where that stops being a slogan.
            # `CALL setup_temp_vm(template: ...)` runs the stored body with its parameters
            # bound, through THIS SAME VISITOR — so every statement inside meets the guarded
            # executor, the commit gate and the contract tier exactly as it did the day it
            # was written. Storing a program does not bless it.
            #
            # THE CALLER'S ARGUMENTS BECOME THE CALLEE'S SCOPE, and nothing else does. A
            # procedure that could read the caller's bindings would be a program whose
            # meaning depends on where it was called from, which is the opposite of the
            # reusability it exists for.
            proc = _procs.LIBRARY.get(st.get("tool"))
            inner_scope = dict(_resolve(st.get("args") or {}, scope))
            saved, scope_backup = dict(scope), dict(scope)
            scope.clear()
            scope.update(inner_scope)
            try:
                bad = _block(coerce_body(proc) or [])
            finally:
                scope.clear()
                scope.update(scope_backup)
            return bad

        if op == "publish":
            # NAMED HERE, VALUED BY THE ENGINE. This module has no findings ledger and should
            # not grow one — it records WHAT the program asked to submit, and whoever owns the
            # observations attaches what was actually seen. A program that could state its own
            # answer could state one it never obtained, which is the whole failure class this
            # layer exists to refuse.
            published.append(str(st.get("fact") or ""))
            return None

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
            n = _amount(st.get("amount", 1), scope)
            # Everything else the creator takes rides along — os_type, cpu_cores,
            # memory_mb. With count > 1 each resource is created with the SAME args,
            # which is the natural reading of "create 5 vms with 4GB each".
            extra = _resolve(st.get("args") or {}, scope)
            # THE AUTHOR'S OWN NAME WINS. Minting exists to supply a name when nobody
            # said one — not to overrule someone who did. This line used to read
            # `{**extra, key_arg: nm}` with `nm` always minted from the VARIABLE, so
            # `STORE core_net = NEW network(net_name: core)` created a network called
            # `core_net` and every later reference to `core` failed against a world that
            # had never contained it. Rung 8 died exactly there, twice: the model wrote a
            # correct statement, the executor silently renamed the resource, and the rung
            # was scored as the model's mistake. Silently discarding an argument the
            # author explicitly passed is the same defect class as the schema withholding
            # a construct the validator already implemented.
            supplied = extra.get(key_arg)
            # ...unless it is not a NAME. An unresolved `$reference` still carries the
            # sigil — the author wrote `NEW network(net_name: $blue_net)` with nothing
            # binding `blue_net`, `refs.resolve` correctly left the token alone, and the
            # world ended up holding machines called `$blues1` and a network called
            # `$blue_net`. A value that still has a sigil in it is not a name in any
            # program, so fall back to minting rather than create the nonsense. The
            # validator refuses this case outright now; this is the belt beside it,
            # because a parameter supplied at invocation is not knowable statically.
            if (isinstance(supplied, str) and supplied.strip()
                    and not refs.names(supplied)):
                base = supplied
            else:
                base = st["var"]
            names = [_mint(kind, base, i, n) for i in range(n)]
            for nm in names:
                call_args = {**extra, key_arg: nm}
                if source and chosen.get("from"):
                    call_args[chosen["from"]] = source
                _do(chosen["tool"], call_args)
            # One resource binds its name; several bind the LIST, so `foreach in` can
            # iterate what was just created — before it has any attribute to query by.
            scope[st["var"]] = names[0] if n == 1 else names
            # ── NEW's OWN ENSURE ────────────────────────────────────────────────────
            # `new` is the ONE op where the harness itself invents something: it mints
            # the name, chooses the creator, and supplies the key argument. A `call`
            # passes the author's arguments through and decides nothing. So `new` is the
            # only statement that can quietly produce something OTHER than what was
            # asked for — and it did, three separate ways in one day: the minted name
            # overrode an explicit `net_name` (a network called `core` came out as
            # `core_net`), an unresolved `$reference` became a literal resource name, and
            # a supplied base was suffixed. Every one of those reported success, because
            # the creator call genuinely succeeded — it just created the wrong thing.
            #
            # So the statement vouches for itself, which is the language's own rule
            # (a program needs a VERDICT) applied to the one op that needs it most.
            # Deliberately a POST-check: skipping a `new` whose effect already holds is
            # ADOPTING, and decision 2 refuses that outright — "if the user asks for new,
            # he means new". This asks "did I make what I said?", never "need I bother?".
            #
            # Costs one lister call per STATEMENT, not per resource, and needs no new
            # manifest data: every kind already declares `list` and `key`, which is what
            # the injected `select` reads.
            if select is not None and names:
                try:
                    present = set(select({"kind": kind}))
                except Exception as exc:                       # a seam that cannot answer
                    present, missing = None, []                # is not evidence of absence
                    failures.append({"tool": chosen["tool"], "args": {},
                                     "error": f"could not verify the new {kind}: {exc}"})
                else:
                    missing = [nm for nm in names if nm not in present]
                if missing:
                    asked = extra.get(key_arg)
                    failures.append({
                        "tool": chosen["tool"],
                        "args": {key_arg: missing[0]},
                        "error": (
                            f"{chosen['tool']} reported success but no {kind} named "
                            f"{', '.join(repr(m) for m in missing)} exists"
                            + (f" (the statement asked for {asked!r})"
                               if isinstance(asked, str) and asked not in names else "")
                            + ". The creator ran and made something else, or nothing.")})

        elif op == "call":
            result = _do(st["tool"], _resolve(st.get("args") or {}, scope))
            # A grafted result enters scope under its name, so a later statement — usually
            # an `if` — can read what the call actually said.
            if st.get("graft"):
                scope[st["graft"]] = result

        elif op == "fetch":
            # THE WORLD-READ. It goes through the SAME injected `select` seam every query
            # in the language already uses — the Active Library for registry attributes,
            # the findings ledger for what was observed. Nothing new had to be built to
            # answer it; it only had to be bound to a name.
            if select is None:
                return {"ok": False, "failed": "no select evaluator",
                        "scope": scope, "calls": calls}
            query = st.get("count") or st.get("select")
            found = select(_resolve(query, scope))
            scope[st["var"]] = len(found) if st.get("count") else found

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
                # A LONE ENSURE THAT FAILED is the one case worth naming, because it is
                # the likeliest mis-word in the language. "Make sure exactly 3 carry
                # prod" reads as both "verify that" and "bring that about", and the two
                # words are the only thing distinguishing them. A program that is
                # nothing but a check COULD NOT have acted — so if the operator wanted
                # convergence, the word is wrong, and saying so costs nothing while
                # leaving a genuine health check perfectly legal.
                hint = why
                if op == "ensure" and len(body) == 1 and not calls:
                    hint = (f"{why}. This program only VERIFIES — it has no work and no "
                            f"ACHIEVE, so nothing will change. If you meant to bring this "
                            f"about rather than check it, the word is ACHIEVE.")
                return {"ok": False,
                        "failed": "unachieved" if op == "achieve" else "unsatisfied",
                        "why": hint, "predicate": st["predicate"], "scope": scope,
                        "calls": calls, "failures": failures}
        # IFAILS: recovery runs only if THIS statement's calls actually failed. Scoping it
        # to one statement is why you know what broke — and the failure stays recorded, so
        # a recovery compensates rather than conceals.
        if len(failures) > before and st.get("ifails"):
            _block(st["ifails"])
        return None

    def _said(res: Dict[str, Any]) -> Dict[str, Any]:
        """Every result past the promotion point says whether one happened.

        The operator chose promotion over objection, so what RUNS is not always what was
        authored. A rewrite nobody reports is indistinguishable from the author having
        written it that way, and the next person debugging an ACHIEVE they never wrote would
        have nothing to go on.
        """
        out = {**res, "promoted": promoted} if promoted else dict(res)
        if abandoned:
            # SURFACED ON EVERY RESULT, including successful ones. A program whose loop body
            # was cut short can still end with its top-level checks passing — which is
            # precisely the case that must not read as a clean run.
            out["abandoned"] = list(abandoned)
        if published:
            out["published"] = list(published)
        return out

    for i, st in enumerate(body):
        bad = _one(st)
        if bad is not None:
            # WHAT NEVER RAN, reported rather than silently dropped. A failed predicate
            # returns from here, so every statement after it is abandoned — and nothing
            # said so. Rung 4 is the case that exposed it: the author put
            # `ACHIEVE REACH(...)` at statement 5 and the `add_label(... fleet)` loop at
            # statement 6, the ACHIEVE failed, and the tagging never happened. `derive`
            # then closed the PREDICATE's gap and reported the goal held, because it
            # computes the difference for one predicate and cannot know a tail was lost.
            # The world ended networked, probed and untagged, and the only thing that
            # noticed was the rung's own checker.
            #
            # TOP LEVEL ONLY, and that is a real limit rather than an oversight: a
            # statement abandoned inside a `foreach` or an `if` branch is not resumable by
            # replaying a suffix of the body, because its loop variable and its branch
            # condition are gone. Those are reported as unfinished, not silently resumed.
            #
            # CLEANUP RUNS ANYWAY — the program's `finally`. Everything after the failure is
            # abandoned, and the teardown of what this program MADE FOR ITSELF lives in that
            # tail, so every failed run leaked its own scaffolding: three machines in one
            # afternoon, each created for a search that could not run, each left for an
            # operator who never asked for a machine at all.
            #
            # ONLY WHAT THE WRITER MARKED. The mark means "this member is the program's own",
            # a judgement made where provenance is actually known; a runtime guessing which
            # trailing deletes are safe to force would eventually force one that is not.
            #
            # ITS FAILURES ARE RECORDED AND DO NOT REPLACE THE ORIGINAL. The run failed for
            # the reason it failed; a teardown that also could not complete is a second fact,
            # not a correction of the first.
            tail = list(body[i + 1:])
            cleanup = [st for st in tail if st.get("cleanup")]
            for st in cleanup:
                try:
                    _one(st)
                except Exception as exc:                       # noqa: BLE001
                    failures.append({"tool": st.get("tool"), "args": st.get("args") or {},
                                     "error": f"cleanup raised {type(exc).__name__}: {exc}"})
            return _said({**bad, "remaining": [st for st in tail if not st.get("cleanup")],
                          "cleaned_up": len(cleanup)})
    op = None

    if failures and not asserted:
        # Nothing vouched for the end state and calls failed: there is no basis for a
        # green close. With an ENSURE present its verdict stands — a failure it tolerated
        # is one that did not matter.
        return _said({"ok": False, "failed": "calls_failed", "scope": scope,
                      "calls": calls, "failures": failures,
                      "why": f"{len(failures)} call(s) failed and no ensure checked the "
                             f"result: "
                             + "; ".join(f"{f['tool']}: {f['error']}"
                                         for f in failures[:3])})
    return _said({"ok": True, "scope": scope, "calls": calls, "failed": None,
                  "failures": failures})
