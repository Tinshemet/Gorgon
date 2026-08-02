"""
lower.py — STAGED LOWERING, step 01: node type, fusion rules, per-operator schemas.

The design note (2026-07-28, artifact b44bcae5) in one line: *"decompose to one-operator
leaves, emit per leaf, fuse upward — but grade the whole artifact before anything runs."*

THIS FILE IS THE DETERMINISTIC HALF AND CALLS NO MODEL. It holds the node type, the fusion
rules, and the schema generator that offers ONE operator instead of eleven. The build order
puts it first precisely because it can be written and tested with no model in the loop:
everything here is checkable in milliseconds, and the expensive, unreliable parts (routing,
leaf emission) plug into it afterwards.

## WHY ONE OPERATOR PER LEAF — and the correction the note needs

The note claims a per-leaf schema *"removes the construct that has been producing malformed
output"*. On 2026-07-28 that read as measured-FALSE: flattening the eleven-branch `oneOf`
into a single object with `op` as an enum produced byte-identical failures at the same
character positions.

**THAT MEASUREMENT TESTED THE WRONG THING, and 2026-07-29 says so.** Flattening eleven
branches is not the same as offering ONE. Measured that day:

  * every constraint shape held 5/5 in isolation at ONE or TWO branches — top-level
    `required`, nested `required`, nested `enum`, `required` inside array items, `$ref`,
    and self-recursive `$ref`.
  * under the real ELEVEN-branch schema the model emitted `{"op": "else": [...]}` — an op
    NO BRANCH PERMITS, `else` being a field of `if` and never a statement — and the bytes
    did not parse.

So the mechanism is not that `oneOf` is malformed-prone; it is that GRAMMAR ENFORCEMENT
DEGRADES WITH BRANCH COUNT. A leaf offered one operator's schema is one branch, which is
the regime where enforcement was observed to hold. That is a stronger argument than the
note makes, and it is what this step exists to test.

## WHAT IS DELIBERATELY NOT HERE

No routing (that is the atomicity router, measured separately at step 02 and already
passing), no leaf emission, no retry, no gates, no whole-artifact review. Each is its own
step, and the note is explicit that PER-LEAF RETRY MUST SHIP WITH EMISSION rather than
later — without it, splitting one draw into five multiplies exposure instead of containing
it. This file must not tempt anyone into emitting without it.
"""
from typing import Any, Dict, List, Optional, Tuple

from . import config, master, schema as _schema
from .validate import validate

# ── THE NODE ────────────────────────────────────────────────────────────────────────────
# A dict rather than a class, deliberately: every other IR object in this package is a
# plain dict over which `run`, `validate`, `derive` and `render` are pure functions, and a
# node that could not be JSON-dumped could not be logged, cached or replayed.
#
#   goal      the sub-goal this node is responsible for, in the operator's own words
#   op        the operator this node IS. A LEAF's op is what it emits; a BRANCH's op is
#             what its children fuse INTO — the note's open question #3: *"a decomposing
#             node has to name its own operator, not just its sub-goals — otherwise fusion
#             has nothing to attach to."*
#   children  sub-nodes; empty for a leaf
#   stmt      the emitted statement, for a leaf. None until emission runs.
#
# `op` is REQUIRED ON BOTH KINDS and that is the load-bearing rule of this file.


def node(goal: str, op: Optional[str] = None,
         children: Optional[List[dict]] = None, stmt: Optional[dict] = None) -> dict:
    """One node. A leaf has no children; a branch has children and must name its own op."""
    return {"goal": goal, "op": op, "children": list(children or []), "stmt": stmt}


def is_leaf(n: dict) -> bool:
    return not n.get("children")


def depth(n: dict) -> int:
    """Deepest path from here. The note requires a depth bound — *"a goal that keeps
    decomposing into itself never bottoms out"* — and a bound needs something to measure."""
    kids = n.get("children") or []
    return 1 + max((depth(k) for k in kids), default=0)


def leaves(n: dict) -> List[dict]:
    """Every leaf under this node, left to right — emission order."""
    if is_leaf(n):
        return [n]
    out: List[dict] = []
    for k in n["children"]:
        out += leaves(k)
    return out


# ── FUSION ──────────────────────────────────────────────────────────────────────────────
# HOW CHILDREN ATTACH IS A PROPERTY OF THE PARENT'S OPERATOR, and the manifest already
# states which field each op puts a body in. Reading it from `ops` rather than hardcoding
# keeps this from becoming the second place that knows the language's shape — the
# six-builders problem this package has been bitten by repeatedly.
#
#   foreach -> children become its `do` block
#   if      -> children become the `then` branch
#   anything else -> a plain sequence; children concatenate and the parent contributes
#                    its own statement first if it has one

_BODY_FIELD = {"foreach": "do", "if": "then"}


class FusionError(ValueError):
    """A tree that cannot be assembled. Raised rather than returned because a caller that
    ignored it would emit a program missing statements, which is the silent-loss class this
    codebase refuses everywhere else."""


def fuse(n: dict) -> List[dict]:
    """The statements this node contributes, children folded in by the node's operator.

    Returns a LIST because a plain sequence node contributes several. The root's list is
    the program body.
    """
    if is_leaf(n):
        if n.get("stmt") is None:
            raise FusionError(f"leaf has no statement: {n.get('goal')!r}")
        return [dict(n["stmt"])]

    op = n.get("op")
    if not op:
        # THE NOTE'S OPEN QUESTION #3, enforced. A branch that never named its operator has
        # nothing for its children to attach to, and the failure has to be loud: silently
        # concatenating would turn a `foreach` the author meant into a flat sequence that
        # runs once, which validates, executes, and does the wrong thing.
        raise FusionError(
            f"decomposing node named no operator: {n.get('goal')!r} — a branch must say "
            f"what its children fuse INTO")

    kids: List[dict] = []
    for k in n["children"]:
        kids += fuse(k)

    field = _BODY_FIELD.get(op)
    if field is None:
        # A SEQUENCE. The node's own statement, if it emitted one, comes first — it is the
        # setup its children depend on (`NEW` binding a name a later child reads).
        own = [dict(n["stmt"])] if n.get("stmt") else []
        return own + kids

    # A CONTAINER. The parent's statement is the frame and the children are its body; the
    # parent must have emitted something for there to be a frame at all.
    if n.get("stmt") is None:
        raise FusionError(
            f"`{op}` node has children but no statement of its own: {n.get('goal')!r} — "
            f"there is no frame to put them in")
    frame = dict(n["stmt"])
    frame[field] = kids
    # `call` is foreach's one-statement shorthand and cannot coexist with `do`; a frame that
    # arrived carrying one would silently drop the fused children.
    if op == "foreach":
        frame.pop("call", None)
    return [frame]


def assemble(root: dict) -> dict:
    """The finished program. Inert — nothing has run, which is the whole point: the artifact
    can be graded at every granularity before the world is touched."""
    return {"body": fuse(root)}


# ── PER-OPERATOR SCHEMA ─────────────────────────────────────────────────────────────────
def leaf_schema(op: str, want: Optional[str] = None,
                known: Optional[set] = None,
                quantifier: Optional[str] = None) -> Dict[str, Any]:
    """The schema for a leaf that is known to be `op` — ONE branch, not eleven.

    Built from the same manifest rows as the whole-program schema, so a leaf cannot be
    offered a different language from a program. The narrowing is the only difference, and
    it is the point: the decoder chooses FIELD VALUES, never a branch.

    Raises on an op the intent does not permit, rather than quietly returning an empty
    schema — a decoder handed nothing legal produces garbage, and it would look like a
    model failure.

    `quantifier` narrows the same way `want` does, and on a LEAF it is a better fit than
    anywhere else: a leaf is one clause, and the quantifier is a property OF a clause —
    which is exactly the mismatch E3 records for the whole-program path, where one answer
    has to cover a goal with several clauses in it. When the router refuses a leaf's op
    the error now names both narrowings, because "not offered under intent achieve" is a
    misleading thing to print when it was the quantifier that excluded it.
    """
    allowed = master.ops(want, quantifier)
    if op not in allowed:
        raise ValueError(f"{op!r} is not offered under intent {want!r} "
                         f"quantifier {quantifier!r} (allowed: {', '.join(allowed)})")
    spec = config.OPS[op]
    props: Dict[str, Any] = {
        "op": {"type": "string", "const": op, "description": spec["doc"]}}
    for f in spec["fields"]:
        props[f] = _schema._field(f, known)
    return {"type": "object", "properties": props,
            "required": ["op"] + list(spec.get("required") or ())}


# ── STEP 03: LEAF EMISSION, RETRY, FALLBACK ─────────────────────────────────────────────
# THE MODEL CALL IS INJECTED, exactly as `run()` injects `select` and `holds`. The policy —
# how many retries, what falls back to what, when to stop — is deterministic and lives
# here; the unreliable part is a callable the caller supplies. So every rule below is
# testable with a fake emitter in milliseconds, and only the emitter itself needs a model.
#
# PER-LEAF RETRY SHIPS HERE, NOT LATER. The design note is explicit and it is the one
# condition on the whole design: *"Without it, splitting one draw into five multiplies
# exposure instead of containing it, and the design is a regression."* At a measured ~8%
# decode failure rate, five independent draws without retry is 0.92^5 ≈ 66% against today's
# 92% for one. Retry is what converts "more decisions" into "less risk", and it is only
# possible BECAUSE failure became local.

MAX_DEPTH = 4          # the note requires a bound: "a goal that keeps decomposing into
                       # itself never bottoms out". 4 covers every ladder shape seen.
LEAF_RETRIES = 2       # attempts AFTER the first, per leaf.


class LoweringError(RuntimeError):
    """Emission could not produce a usable tree. Distinct from FusionError: that one means
    the tree is malformed, this one means a leaf never arrived."""


def _same(a, b) -> bool:
    """Two statements that are indistinguishable. A retry returning byte-identical output
    is the no-progress case, and burning the remaining budget on it is what
    `REPAIR_UNDELIVERED` already taught — rung 9's repair 'returned the SAME program,
    nothing further to try at this temperature'."""
    import json as _json
    try:
        return _json.dumps(a, sort_keys=True) == _json.dumps(b, sort_keys=True)
    except (TypeError, ValueError):
        return a == b


def emit_leaf(leaf: dict, emit, want: Optional[str] = None,
              known: Optional[set] = None, derive_fn=None,
              retries: int = LEAF_RETRIES, log=None,
              bound: Optional[set] = None,
              body: Optional[List[dict]] = None,
              context: Optional[List[dict]] = None,
              ancestry: Optional[List[str]] = None,
              known_tools: Optional[set] = None) -> dict:
    """Fill one leaf's `stmt`. Returns the leaf (mutated copy), or raises LoweringError.

    ORDER, and it is the reason-gate note's `sanitize -> repair -> ask` read backwards from
    the cheap end: try the model, retry it on failure, and only then fall back to computing
    the statement. Cheapest reliable thing last, because `derive()` can only answer for
    SOME leaves and the model can attempt all of them.

    A leaf that cannot be filled RAISES rather than returning an empty statement. A tree
    assembled with a hole in it is a program missing a statement — it validates, it runs,
    and it silently does less than the goal asked, which is the class this codebase refuses
    everywhere else.
    """
    op = leaf.get("op")
    if not op:
        raise LoweringError(f"leaf names no operator: {leaf.get('goal')!r}")
    schema = leaf_schema(op, want, known)
    attempts, last = [], None
    for i in range(retries + 1):
        try:
            # THE OBJECTION GOES BACK IN, and without it retry is worthless. Measured on
            # this file's first real run: a `new` leaf omitted `os_type`, the retry re-sent
            # IDENTICAL input, temp 0 returned the IDENTICAL statement, and the no-progress
            # guard killed a leaf the model could have fixed. The whole-program path already
            # knew this — `repair()` feeds the validator's complaint back — and a per-leaf
            # retry that does not is just a second draw at the same odds.
            # SIBLING CONTEXT. The note's open question #4 at the SEMANTIC level, and
            # measured: "put the red ones together" and "launch the last vm" mean nothing
            # alone, because their referent is a SIBLING's decision. Scope threading fixed
            # the BINDING half (`$item` resolves); this is the other half — a leaf is not
            # context-free in either sense, and lowering in true isolation asks the model to
            # name something it was never shown.
            stmt = emit(leaf, schema, attempts[-1] if attempts else None,
                        list(context or []), list(ancestry or []))
        except Exception as exc:                 # a decode failure IS the expected case
            if log:
                log(f"leaf {leaf.get('goal')!r} attempt {i + 1}: {type(exc).__name__}")
            continue
        if stmt is None:
            continue
        if last is not None and _same(stmt, last):
            # NO PROGRESS. The same draw again will not become a different one; stop
            # spending the budget and let the fallback have it.
            if log:
                log(f"leaf {leaf.get('goal')!r}: retry returned the same statement — stopping")
            break
        last = stmt
        # VALIDATE IN THE SCOPE THE LEAF WILL OCCUPY, not in isolation. The note's open
        # question #4: *"a statement that binds a name others read cannot be lowered in
        # complete isolation."* Hit on this file's first real test — a `call` inside a
        # foreach legitimately says `$item`, and judged alone it reports "never created",
        # so a correct leaf would be retried to exhaustion and then refused.
        #
        # `validate` already takes `bound` and already grants the loop variable inside a
        # foreach body; lowering just has to SUPPLY what is in scope. Nothing new is
        # invented here — the rule is the validator's own, applied one statement at a time.
        # A CONTAINER IS VALIDATED FUSED, NOT BARE. Second finding of the same kind as the
        # scope one, and found the same way: a bare `foreach` fails its own `one_of` rule
        # because `call`/`do` only arrive at FUSION. Judged alone, a perfectly good frame is
        # retried to exhaustion and refused. The note already puts container checks at the
        # fusion — *"sanitizer, reason gate and schema gate run on each fusion"* — so the
        # children (already emitted, the walk is bottom-up) go in before the verdict.
        subject = dict(stmt)
        field = _BODY_FIELD.get(stmt.get("op"))
        if body is not None and field:
            subject[field] = list(body)
            subject.pop("call", None) if stmt.get("op") == "foreach" else None
        # `known_tools` IS THE ENGINE'S, NOT THE DEFAULT REGISTRY'S. Without it this
        # validated every leaf against the VM executor's tools whatever engine was running —
        # so a kitchen's `create_dish` came back "no such tool" and every leaf was retried to
        # exhaustion and then refused. The whole-program path was threaded for this on
        # 2026-08-01 and staged lowering, written before engines existed, was not.
        ok, problems = validate({"body": [subject]}, bound=set(bound or ()),
                                known_tools=known_tools)
        if ok:
            out = dict(leaf); out["stmt"] = stmt
            return out
        attempts.append(problems[0] if problems else "invalid")
        if log:
            log(f"leaf {leaf.get('goal')!r} attempt {i + 1} invalid: {attempts[-1]}")

    # FALLBACK: compute what the model could not say. Only predicate-bearing leaves can be
    # derived — `derive()` answers "what statements would make this predicate hold", so it
    # has nothing to say about a `call` whose arguments nobody supplied. Being honest about
    # that is better than a fallback that appears general and silently covers one case.
    if derive_fn is not None and op in ("ensure", "achieve") and leaf.get("predicate"):
        derived = derive_fn(leaf["predicate"])
        if derived:
            out = dict(leaf); out["stmt"] = derived[0]
            if log:
                log(f"leaf {leaf.get('goal')!r}: filled by derive()")
            return out

    raise LoweringError(
        f"leaf {leaf.get('goal')!r} ({op}) produced no valid statement in "
        f"{retries + 1} attempt(s)" + (f": {attempts[-1]}" if attempts else ""))


def lower_tree(root: dict, emit, want: Optional[str] = None, known: Optional[set] = None,
               derive_fn=None, max_depth: int = MAX_DEPTH, log=None, route=None,
               known_tools: Optional[set] = None) -> dict:
    """Emit every leaf, bottom-up, and return a NEW tree with statements filled.

    Mutates nothing: review can send the tree back, and a second pass has to grade the same
    object the first one did.
    """
    d = depth(root)
    if d > max_depth:
        raise LoweringError(
            f"tree is {d} deep, bound is {max_depth} — a decomposition that keeps going "
            f"never bottoms out, so this is refused rather than followed")

    done_so_far: List[dict] = []          # every statement already emitted, in order

    def walk(n: dict, bound: set, ancestry: List[str]) -> dict:
        if is_leaf(n):
            # A THIN SUB-GOAL MEANS NOTHING WITHOUT WHAT IT SITS UNDER. Measured: "put the
            # red ones together" and "new vm1 with fleet label" are unauthorable alone —
            # the colour, the count and the label all live in the PARENT's wording. Sibling
            # context gave the leaf what was already DONE; ancestry gives it what it is
            # PART OF, and neither substitutes for the other.
            try:
                out = emit_leaf(n, emit, want, known, derive_fn, log=log, bound=bound,
                                context=done_so_far, ancestry=ancestry,
                                known_tools=known_tools)
            except LoweringError:
                # A LEAF THAT CANNOT BE EMITTED IS EVIDENCE THE ROUTER WAS WRONG ABOUT
                # ATOMICITY. Measured: rungs 8 and 11 handed the WHOLE goal to one leaf —
                # "put every vm on core, except db, db goes on dmz" is plainly two
                # statements, and no amount of retrying makes it one. Re-routing it is the
                # honest recovery, and it uses the channel that answers this question at
                # 10/10 rather than asking the decoder to do the impossible again.
                if route is None or len(ancestry) + 1 >= max_depth:
                    raise
                if log:
                    log(f"leaf would not emit — re-routing as a decomposition: "
                        f"{n.get('goal')[:52]!r}")
                sub = decompose(n["goal"], route, max_depth - len(ancestry), log)
                if is_leaf(sub):
                    raise          # the router still says atomic; nothing further to try
                return walk(sub, bound, ancestry)
            if out.get("stmt"):
                done_so_far.append(out["stmt"])
            return out
        out = dict(n)
        # SCOPE THREADS DOWN, AND IT IS A COPY AT EVERY LEVEL — the same rule `validate`
        # uses for nested blocks, which gives block scoping for free: a name bound inside a
        # loop is not visible after it.
        inner = set(bound)
        if n.get("op") == "foreach":
            inner.add(config.LOOP_VAR)     # `$item` exists for the body and only there
        kids = []
        for k in n["children"]:
            done = walk(k, inner, ancestry + [n.get("goal", "")])
            kids.append(done)
            # A SEQUENCE'S LATER CHILDREN SEE WHAT THE EARLIER ONES BOUND. `NEW` binds a
            # name the next statement reads, and lowering must not hide that from the
            # validator or every dependent leaf is judged unbound.
            var = (done.get("stmt") or {}).get("var")
            if var and _BODY_FIELD.get(n.get("op")) is None:
                inner.add(var)
        out["children"] = kids
        # A CONTAINER NEEDS ITS OWN FRAME. `foreach` and `if` put children inside a
        # statement, so the branch itself is emitted too — as a leaf would be, against its
        # own operator's schema. A plain sequence needs no frame and emits nothing.
        if _BODY_FIELD.get(n.get("op")) and out.get("stmt") is None:
            # The FRAME is emitted in the OUTER scope — a foreach's `select` cannot refer
            # to the loop variable it is about to introduce.
            fused: List[dict] = []
            for k in out["children"]:
                fused += fuse(k)
            out = emit_leaf(out, emit, want, known, derive_fn, log=log,
                            bound=bound, body=fused, context=done_so_far,
                            ancestry=ancestry, known_tools=known_tools)
        return out

    return walk(root, set(), [])


# ── STEP 04: GATES AT EVERY FUSION ──────────────────────────────────────────────────────
# The note's table is a RELOCATION list, not new work: *"the architecture mostly relocates
# checks to the resolution where they answer a question they can actually answer."* The
# validator already runs per leaf and per fused container (above). This adds the sanitiser
# at the same two points, so residue is dropped at the level it was produced rather than
# surviving into a finished artifact where its origin is lost.
#
# THE SANITISER STILL NEVER REWRITES. Same rule as everywhere else — it removes what
# provably cannot run and COUNTS what it removed. A pass that cleaned without counting
# would make the artifact rate unmeasurable, which is the failure this codebase keeps
# rediscovering.

def gate_fusion(stmts: List[dict], sanitize_fn=None) -> Tuple[List[dict], List[dict]]:
    """(statements, removals) for one fusion. Deterministic; no model."""
    if sanitize_fn is None:
        return list(stmts), []
    cleaned, removed = sanitize_fn({"body": list(stmts)})
    return (cleaned.get("body") if isinstance(cleaned, dict) else cleaned), list(removed or [])


# ── STEP 05: WHOLE-ARTIFACT REVIEW ──────────────────────────────────────────────────────
# THE ONLY PLACE A WRONG ROOT IS VISIBLE. Per-node gates are necessary and not sufficient:
# *"a wrong decomposition near the root is locally invisible — every child is a valid
# statement, every fusion is well-formed, and the program is still wrong."*
#
# DELIBERATELY DETERMINISTIC. The note warns twice about this step, and both warnings point
# the same way: *"the reviewer must never be the only thing standing between a program and
# the world, or a graded verdict quietly becomes a gate"*, and per-node p_self is only
# honest if *"the verdict at each node comes from something other than the model"*. A
# model-graded review would be the second bad draw on both counts. So every finding below
# is computed:
#
#   coverage    the CLAUSE LEDGER — demands recorded before authoring, reconciled after.
#               Catches "a clause of the goal that appears nowhere", the third row of the
#               note's whole-granularity table and the one no local check can see.
#   repetition  identical statements in distant branches — "work done twice". A GRADE on a
#               correct program, never a reason to refuse it: treating redundancy as a
#               defect would push toward fewer, larger decisions, which is the direction
#               that RAISES p_self risk.
#   grounding   the one soundness rule — a program needs at least one VERDICT.
#
# It RETURNS A REPORT AND CHANGES NOTHING. Sending the tree back is the caller's decision,
# and `revise_target` only names where.

REVIEW_ROUNDS = 2      # the note requires an explicit bound: a program that cannot satisfy
                       # its reviewer would otherwise be re-authored forever.


def review(root: dict, ledger=None, reconcile_fn=None) -> Dict[str, Any]:
    """Grade the assembled tree. Deterministic, no model, changes nothing."""
    prog = assemble(root)
    body = prog["body"]

    flat: List[dict] = []
    def walk(sts):
        for s in sts:
            flat.append(s)
            for f in ("do", "then", "else"):
                if isinstance(s.get(f), list):
                    walk(s[f])
    walk(body)

    import json as _json
    seen: Dict[str, int] = {}
    for s in flat:
        if s.get("op") in ("ensure", "achieve"):
            continue          # asserting the same thing twice is cheap and often correct
        k = _json.dumps({x: v for x, v in s.items()
                         if x not in ("do", "then", "else")}, sort_keys=True)
        seen[k] = seen.get(k, 0) + 1
    repeated = [k for k, n in seen.items() if n > 1]

    unaccounted = []
    if ledger is not None and reconcile_fn is not None:
        unaccounted = reconcile_fn(ledger, body)

    return {
        "grounded": any(s.get("op") in ("ensure", "achieve") for s in flat),
        "unaccounted": unaccounted,
        "repeated": repeated,
        "statements": len(flat),
    }


def revise_target(root: dict, report: Dict[str, Any]) -> Optional[str]:
    """WHERE to send the tree back, or None if nothing is wrong.

    Ordered by what only that level can fix, and coverage comes FIRST: a missing clause is
    a decomposition fault, and re-emitting a leaf cannot invent a branch that was never
    planned. Repetition is NOT a target — it is a grade on a correct program, removable by
    an optimisation pass that must stay downstream of correctness so "did fewer calls" can
    never be confused with "was more right".
    """
    if report.get("unaccounted"):
        return "decomposition"
    if not report.get("grounded"):
        return "root"
    return None


def review_loop(root: dict, rebuild, ledger=None, reconcile_fn=None,
                rounds: int = REVIEW_ROUNDS, log=None) -> Tuple[dict, Dict[str, Any]]:
    """Review, send back, review again — BOUNDED, with a no-progress guard.

    `rebuild(root, target)` returns a new tree or None if it cannot. Returns the best tree
    reached and its report; a tree the reviewer never accepted is returned ANYWAY, with its
    findings, because the reviewer must not be the only thing between a program and the
    world.
    """
    cur, rep = root, review(root, ledger, reconcile_fn)
    for i in range(rounds):
        target = revise_target(cur, rep)
        if target is None:
            return cur, rep
        nxt = rebuild(cur, target)
        if nxt is None or nxt == cur:
            if log:
                log(f"review round {i + 1}: no progress on {target} — stopping")
            break
        nrep = review(nxt, ledger, reconcile_fn)
        if nrep == rep:
            if log:
                log(f"review round {i + 1}: same findings after rebuild — stopping")
            cur = nxt
            break
        cur, rep = nxt, nrep
    return cur, rep


# ── THE DECOMPOSER — drive the router recursively until every leaf is one operator ──────
# The last piece: everything above assumes a tree, and nothing built one. The router itself
# is measured (step 02, 10/10 on the cells that carry information, and it names a parent
# operator 11/11) — this only has to DRIVE it, bound it, and refuse the shapes that would
# not terminate.
#
# ROUTE IS INJECTED, like `emit`. It takes a goal and returns either
#   {"atomic": True,  "op": "call"}                      a leaf, and which operator
#   {"atomic": False, "op": "foreach", "steps": [...]}   a branch, its operator, its sub-goals
# and the caller supplies whatever makes that call. Nothing here knows about a model.

def _intent_rank(op: Optional[str]) -> Optional[int]:
    """How much authority an intent op carries, or None if it is not an intent op.

    DERIVED FROM `intent.py`'s OWN LADDER, never from the order of a JSON list — the
    manifest groups the three words, it does not rank them, and a rank read off list order
    would be a second statement of the ladder free to disagree with the first.
    """
    from . import intent as _intent
    permits = _intent._PERMITS
    if op not in permits:
        return None
    allowed = permits[op]
    return len(config.OPS) + 1 if allowed is None else len(allowed)


def _keep_intent(parent_op: Optional[str], kid: dict, log=None) -> dict:
    """A LONE SUB-GOAL IS A RESTATEMENT, AND A RESTATEMENT MAY NOT LOWER THE INTENT.

    MEASURED on rung 7, 2026-07-29, where it cost the rung every run: "make sure exactly 3
    vms carry the 'prod' label" routed `achieve`, came back as the single sub-goal "ENSURE
    exactly 3 vms carry the 'prod' label", and that routed `ensure`. The program checked
    where the operator asked it to act — valid, grounded, and inert.

    WHY THE RULE IS ABOUT INTENT AND NOT ABOUT ARITY. The obvious fix is to call any
    one-step answer atomic and keep the parent's operator, and it is wrong: in the same run
    'launch the last new vm' routed `new`, its lone restatement 'launch the last vm' routed
    `call`, and `call` is RIGHT. A restatement may fix HOW; it may not lower WHAT FOR.

    ONLY LOWERING IS REFUSED. A sub-goal that asks for MORE authority is information, and
    refusing it here would duplicate `intent.violations()` — which owns that judgement and
    has the operator's consent behind it — in a place that has neither.
    """
    mine, theirs = _intent_rank(parent_op), _intent_rank(kid.get("op"))
    if mine is None or theirs is None or theirs >= mine:
        return kid
    if log:
        log(f"lone sub-goal lowered `{parent_op}` to `{kid.get('op')}` — "
            f"keeping `{parent_op}`: {str(kid.get('goal'))[:50]!r}")
    return dict(kid, op=parent_op)


class DecompositionError(RuntimeError):
    """A goal that cannot be turned into a tree."""


def decompose(goal: str, route, max_depth: int = MAX_DEPTH, log=None,
              _depth: int = 1, _seen: Optional[set] = None) -> dict:
    """A tree of nodes from one goal. Leaves carry an op and no statement yet.

    THREE WAYS THIS REFUSES, and each is a shape that would otherwise not terminate or
    would produce a tree fusion cannot assemble:

      * DEPTH. The note: *"a goal that keeps decomposing into itself never bottoms out."*
      * A SUB-GOAL IDENTICAL TO ITS PARENT. The commonest non-termination in practice — the
        router restates the goal instead of splitting it, and the next call restates it
        again. Cheaper to catch here than to discover at the depth bound.
      * A BRANCH THAT NAMED NO OPERATOR. The note's open question #3. Refusing at
        decomposition means the failure is attributed to the router, where it happened,
        rather than surfacing later as a FusionError with no idea which call produced it.
    """
    seen = set(_seen or ())
    if _depth > max_depth:
        raise DecompositionError(
            f"decomposition passed depth {max_depth} at {goal!r} — refused rather than "
            f"followed, because a goal that keeps decomposing into itself never bottoms out")

    answer = route(goal) or {}
    op = answer.get("op")
    if answer.get("atomic"):
        if not op:
            raise DecompositionError(f"router called {goal!r} atomic but named no operator")
        return node(goal, op=op)

    steps = [s for s in (answer.get("steps") or []) if isinstance(s, str) and s.strip()]
    if not steps:
        raise DecompositionError(f"router split {goal!r} into no sub-goals")
    # A NODE THAT DECOMPOSES INTO EXACTLY ITSELF IS ATOMIC. The router says "not atomic"
    # and then lists the goal back verbatim — the commonest thing it actually does when a
    # goal is one statement it does not want to commit to.
    #
    # MEASURED, and the first version of this guard CAUSED the failure it was meant to
    # prevent: taking the restatement as a CHILD carrying the parent's operator produced a
    # `foreach` inside a `foreach`, which the language forbids (one loop variable), and
    # rungs 5, 11 and 12 died on it. A parent and its only child cannot both be the same
    # container. Collapsing to one leaf is what the router's answer actually means.
    if all(s.strip() == goal.strip() for s in steps):
        if log:
            log(f"decomposes into itself — taking as atomic `{op}`: {goal[:50]!r}")
        return node(goal, op=op)
    if not op:
        raise DecompositionError(
            f"router split {goal!r} without naming its own operator — fusion would have "
            f"nothing to attach the children to")

    kids = []
    for s in steps:
        if s.strip() == goal.strip() or s.strip() in seen:
            # The router restated the goal instead of splitting it. Treating the restatement
            # as a LEAF is the honest recovery: it is one sub-goal, and the operator the
            # parent named is the best available guess at what it is.
            if log:
                log(f"sub-goal repeats its parent, taking it as a leaf: {s!r}")
            kids.append(node(s, op=op))
            continue
        kids.append(decompose(s, route, max_depth, log, _depth + 1, seen | {goal.strip()}))
    if len(kids) == 1:
        kids[0] = _keep_intent(op, kids[0], log)
    return node(goal, op=op, children=kids)


def ground(root: dict, emit, goal: str, want: Optional[str] = None,
           known: Optional[set] = None, log=None,
           known_tools: Optional[set] = None) -> dict:
    """Give an ungrounded tree a VERDICT, as one more leaf at the root.

    Medusa's one soundness rule: a program that acts and asserts nothing has established
    nothing, and `run()` refuses to execute it. The whole-program author writes a verdict
    because it sees the whole goal; A LEAF CANNOT — rung 1 really is one `new`, and there is
    no room inside one statement for a judgement about it.

    So the verdict is authored ONCE, at the root, against the ORIGINAL goal rather than any
    sub-goal — it is the only place the whole thing is visible. `review` already reports the
    gap and `revise_target` already answers "root"; this is what acts on it.

    Returns the tree unchanged when it is already grounded, and unchanged again if the
    verdict cannot be emitted: a program with no verdict is refused later by `run()`, which
    is the honest outcome, and inventing one here would be the harness vouching for work it
    did not check.
    """
    if review(root)["grounded"]:
        return root
    verdict = node(f"state what must hold at the end: {goal}", op="achieve")
    try:
        filled = emit_leaf(verdict, emit, want, known, log=log,
                           known_tools=known_tools)
    except LoweringError as exc:
        if log:
            log(f"could not author a verdict: {exc}")
        return root
    out = dict(root)
    if _BODY_FIELD.get(root.get("op")) or is_leaf(root):
        # A container or a lone leaf cannot take a sibling, so it becomes the first child
        # of a sequence that also holds the verdict.
        return node(root.get("goal", goal), op="sequence", children=[root, filled])
    out["children"] = list(root["children"]) + [filled]
    return out
