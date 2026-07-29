"""
test_lower.py — staged lowering's deterministic half, tested with no model.

Step 01 of the design note is deliberately the part that needs no model, so it can be held
to the same standard as the rest of the language: pure functions over dicts, checked in
milliseconds. Everything expensive and unreliable — routing, leaf emission, retry — plugs
into this afterwards and is measured separately.
"""
import pytest

from orchestrator.ai.planner.ir import config, lower, render, validate

N = lower.node


def _leaf(goal, op, stmt):
    return N(goal, op=op, stmt=stmt)


NEW = {"op": "new", "var": "made", "kind": "vm", "amount": 5,
       "args": {"os_type": "linux"}}
CALL = {"op": "call", "tool": "add_vm_to_network",
        "args": {"net_name": "lab", "vm_name": "$item"}}
FOREACH = {"op": "foreach", "select": {"kind": "vm"}}


def test_the_notes_worked_example_assembles():
    """`create 5 vms and add them to a network` — the tree in the design note's own figure.
    If this shape does not fuse, nothing else in the design matters."""
    root = N("create 5 vms and add them to a network", op="sequence", children=[
        _leaf("create 5 vms", "new", NEW),
        N("add them to a network", op="foreach", stmt=FOREACH,
          children=[_leaf("add to the network", "call", CALL)]),
    ])
    prog = lower.assemble(root)
    assert len(prog["body"]) == 2
    assert prog["body"][0]["op"] == "new"
    assert prog["body"][1]["op"] == "foreach"
    assert prog["body"][1]["do"] == [CALL], "children must become the foreach's `do` body"
    ok, problems = validate(prog)
    assert "FOREACH" in render(prog) and "add_vm_to_network" in render(prog)


def test_children_attach_by_the_PARENTS_operator():
    """The note's open question #3. `foreach` puts them in `do`, `if` in `then`, and a
    plain sequence concatenates — so the parent's op is what decides, not the children's."""
    kid = _leaf("act", "call", CALL)
    fe = lower.fuse(N("loop", op="foreach", stmt=dict(FOREACH), children=[kid]))
    assert fe[0]["do"] == [CALL]
    iff = lower.fuse(N("branch", op="if",
                       stmt={"op": "if", "cond": {"shape": "count",
                                                  "select": {"kind": "vm"}, "gte": 1}},
                       children=[kid]))
    assert iff[0]["then"] == [CALL]
    seq = lower.fuse(N("both", op="sequence", children=[
        _leaf("a", "new", NEW), _leaf("b", "call", CALL)]))
    assert seq == [NEW, CALL], "a sequence concatenates in order"


def test_a_decomposing_node_that_named_no_operator_is_REFUSED():
    """The failure the note warns about, made loud. Silently concatenating a `foreach`'s
    children would produce a flat sequence that runs ONCE — it validates, it executes, and
    it does the wrong thing. That is the silent-loss class this codebase refuses."""
    bad = N("do it to all of them", op=None, children=[_leaf("act", "call", CALL)])
    with pytest.raises(lower.FusionError, match="named no operator"):
        lower.fuse(bad)


def test_a_container_with_no_statement_of_its_own_is_REFUSED():
    """A `foreach` node with children but no emitted statement has no frame to put them in.
    Fusing anyway would drop the loop and leave the body running once."""
    with pytest.raises(lower.FusionError, match="no statement of its own"):
        lower.fuse(N("loop", op="foreach", children=[_leaf("act", "call", CALL)]))


def test_an_unemitted_leaf_is_REFUSED():
    """A leaf whose emission failed must not vanish into a shorter program. This is where
    per-leaf retry and the `derive()` fallback attach — until they exist, the honest
    behaviour is to refuse rather than to assemble something incomplete."""
    with pytest.raises(lower.FusionError, match="no statement"):
        lower.fuse(N("create 5 vms", op="new"))


def test_a_foreach_frame_cannot_keep_call_and_do_at_once():
    """`call` is foreach's one-statement shorthand and `do` is the block form; the manifest
    declares them one_of. A frame that arrived carrying `call` would silently drop every
    fused child."""
    frame = dict(FOREACH); frame["call"] = {"tool": "launch_vm", "args": {}}
    out = lower.fuse(N("loop", op="foreach", stmt=frame,
                       children=[_leaf("act", "call", CALL)]))
    assert "call" not in out[0] and out[0]["do"] == [CALL]


def test_leaf_schema_offers_exactly_ONE_operator():
    """THE POINT OF STEP 01. Measured 2026-07-29: every constraint shape held 5/5 at one or
    two branches, while the real ELEVEN-branch schema let the model emit `{"op": "else"}` —
    an op no branch permits. One branch is the regime where enforcement was observed to
    hold."""
    s = lower.leaf_schema("call", "achieve")
    assert "oneOf" not in s and "anyOf" not in s
    assert s["properties"]["op"]["const"] == "call"
    assert "tool" in s["required"] and "args" in s["required"]
    for other in ("foreach", "new", "if"):
        assert f'"const": "{other}"' not in str(s), f"{other} leaked into a `call` schema"


def test_every_op_can_be_lowered_to_its_own_schema():
    """Built from the manifest, so a new op is offered here with no edit — the extensibility
    claim the whole package makes, applied to the leaf schema."""
    for op in config.OPS:
        s = lower.leaf_schema(op)
        assert s["properties"]["op"]["const"] == op
        for req in (config.OPS[op].get("required") or ()):
            assert req in s["required"]


def test_leaf_schema_refuses_an_op_the_intent_forbids():
    """A decoder handed nothing legal produces garbage that reads as a model failure. Under
    `fetch` intent, `new` is not offered — say so loudly rather than returning a schema
    nothing can satisfy."""
    with pytest.raises(ValueError, match="not offered under intent"):
        lower.leaf_schema("new", "fetch")


def test_depth_and_leaves_are_measurable():
    """The note requires a depth bound and a no-progress guard; a bound needs something to
    measure, and emission needs the leaves in order."""
    root = N("root", op="sequence", children=[
        _leaf("a", "new", NEW),
        N("mid", op="foreach", stmt=dict(FOREACH), children=[_leaf("b", "call", CALL)]),
    ])
    assert lower.depth(root) == 3
    assert [l["goal"] for l in lower.leaves(root)] == ["a", "b"]


def test_assembly_does_not_mutate_the_tree():
    """The tree is re-graded and possibly re-emitted after review, so assembling it must
    leave it exactly as it was — otherwise the second pass grades a different object."""
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    import copy
    before = copy.deepcopy(root)
    lower.assemble(root)
    assert root == before


# ── step 03: emission, retry, fallback ──────────────────────────────────────────────────
def _emitter(script):
    """A fake emitter driven by a script keyed on goal — no model, fully deterministic.
    `script[goal]` is a list of what successive attempts return; an Exception instance is
    raised (a decode failure), None means the call came back empty."""
    calls = {"n": 0}
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        calls["n"] += 1
        seq = script.get(leaf["goal"])
        if not seq:
            raise AssertionError(f"unscripted leaf {leaf['goal']!r}")
        item = seq.pop(0) if len(seq) > 1 else seq[0]
        if isinstance(item, Exception):
            raise item
        return item
    return emit, calls


def test_a_leaf_that_fails_once_is_RETRIED_not_lost():
    """The design note's one condition. At a measured ~8% decode failure rate, five draws
    without retry is 0.92^5 ~ 66% against 92% for one — the design would be a regression."""
    emit, calls = _emitter({"create 5 vms": [ValueError("decode failed"), NEW]})
    out = lower.emit_leaf(N("create 5 vms", op="new"), emit)
    assert out["stmt"] == NEW
    assert calls["n"] == 2, "it retried exactly once"


def test_retry_stops_when_the_model_returns_the_SAME_statement():
    """No-progress guard. `REPAIR_UNDELIVERED` already taught this: rung 9's repair
    'returned the SAME program — nothing further to try at this temperature'. Spending the
    remaining budget on an identical draw buys nothing."""
    bad = {"op": "new"}                      # missing required `var`/`kind`
    emit, calls = _emitter({"x": [bad]})
    with pytest.raises(lower.LoweringError):
        lower.emit_leaf(N("x", op="new"), emit)
    assert calls["n"] == 2, "stopped after the repeat instead of using the full budget"


def test_a_leaf_that_never_arrives_RAISES_rather_than_assembling_a_hole():
    """A tree with a missing statement is a program that validates, runs, and silently does
    less than the goal asked."""
    emit, _ = _emitter({"x": [ValueError("nope")]})
    with pytest.raises(lower.LoweringError, match="no valid statement"):
        lower.emit_leaf(N("x", op="call"), emit)


def test_derive_fills_a_predicate_leaf_the_model_could_not_emit():
    """The fallback that makes retry cheap — but only where `derive()` can answer at all.
    It computes statements that would make a PREDICATE hold, so it has nothing to say about
    a `call` whose arguments nobody supplied, and pretending otherwise would be a fallback
    that looks general while covering one case."""
    made = {"op": "new", "var": "d", "kind": "vm", "args": {"os_type": "linux"}}
    emit, _ = _emitter({"three vms": [ValueError("x")]})
    leaf = N("three vms", op="achieve")
    leaf["predicate"] = {"shape": "count", "select": {"kind": "vm"}, "eq": 3}
    out = lower.emit_leaf(leaf, emit, derive_fn=lambda p: [made])
    assert out["stmt"] == made


def test_derive_is_NOT_offered_for_ops_it_cannot_answer_for():
    called = {"n": 0}
    def derive_fn(p):
        called["n"] += 1
        return [NEW]
    emit, _ = _emitter({"x": [ValueError("x")]})
    with pytest.raises(lower.LoweringError):
        lower.emit_leaf(N("x", op="call"), emit, derive_fn=derive_fn)
    assert called["n"] == 0, "derive was asked about a `call`, which it cannot answer"


def test_lower_tree_emits_every_leaf_and_the_container_frame():
    """A `foreach` needs its own statement to be a frame for its children, so a container
    branch is emitted too — as a leaf would be, against its own operator's schema."""
    emit, calls = _emitter({"create 5 vms": [NEW],
                            "add them": [dict(FOREACH)],
                            "attach": [CALL]})
    root = N("root", op="sequence", children=[
        N("create 5 vms", op="new"),
        N("add them", op="foreach", children=[N("attach", op="call")]),
    ])
    done = lower.lower_tree(root, emit)
    prog = lower.assemble(done)
    assert prog["body"][0] == NEW
    assert prog["body"][1]["op"] == "foreach" and prog["body"][1]["do"] == [CALL]
    assert calls["n"] == 3, "two leaves plus the foreach frame"


def test_lower_tree_does_not_mutate_the_input_tree():
    emit, _ = _emitter({"a": [NEW]})
    root = N("root", op="sequence", children=[N("a", op="new")])
    import copy
    before = copy.deepcopy(root)
    lower.lower_tree(root, emit)
    assert root == before


def test_a_tree_deeper_than_the_bound_is_REFUSED():
    """The note: 'a goal that keeps decomposing into itself never bottoms out'."""
    deep = N("leaf", op="call", stmt=CALL)
    for i in range(lower.MAX_DEPTH + 1):
        deep = N(f"n{i}", op="sequence", children=[deep])
    emit, _ = _emitter({})
    with pytest.raises(lower.LoweringError, match="never bottoms out"):
        lower.lower_tree(deep, emit)


# ── steps 04 + 05: fusion gates and whole-artifact review ───────────────────────────────
from orchestrator.ai.planner import clause_ledger as _cl


def _reconcile(led, body):
    return _cl.unaccounted(_cl.reconcile(led, body))


def test_review_catches_a_clause_that_appears_NOWHERE():
    """THE THIRD ROW of the note's whole-granularity table, and the only one no local check
    can see: every leaf valid, every fusion well-formed, and a demand of the goal missing.
    This is a wrong DECOMPOSITION, so no amount of re-emitting leaves fixes it."""
    goal = "put every vm on core, except db — db goes on dmz"
    led = _cl.open_ledger(goal, [
        {"text": "put every vm on core", "anchors": ["core"]},
        {"text": "db goes on dmz", "anchors": ["db", "dmz"]}])
    root = N("root", op="sequence", children=[
        _leaf("all on core", "foreach",
              {"op": "foreach", "select": {"kind": "vm"},
               "call": {"tool": "add_vm_to_network", "args": {"net_name": "core"}}}),
        _leaf("verdict", "ensure",
              {"op": "ensure", "predicate": {"shape": "count",
                                             "select": {"kind": "vm"}, "gte": 1}}),
    ])
    rep = lower.review(root, led, _reconcile)
    assert len(rep["unaccounted"]) == 1
    assert lower.revise_target(root, rep) == "decomposition", \
        "a missing clause is a decomposition fault — re-emitting a leaf cannot invent a branch"


def test_review_is_silent_on_a_tree_that_covers_the_goal():
    goal = "put every vm on core, except db — db goes on dmz"
    led = _cl.open_ledger(goal, [
        {"text": "put every vm on core", "anchors": ["core"]},
        {"text": "db goes on dmz", "anchors": ["db", "dmz"]}])
    root = N("root", op="sequence", children=[
        _leaf("all but db on core", "foreach",
              {"op": "foreach", "select": {"kind": "vm", "not": {"name": "db"}},
               "call": {"tool": "add_vm_to_network", "args": {"net_name": "core"}}}),
        _leaf("db on dmz", "call",
              {"op": "call", "tool": "add_vm_to_network",
               "args": {"net_name": "dmz", "vm_name": "db"}}),
        _leaf("verdict", "ensure",
              {"op": "ensure", "predicate": {"shape": "count",
                                             "select": {"kind": "vm"}, "gte": 1}}),
    ])
    rep = lower.review(root, led, _reconcile)
    assert rep["unaccounted"] == [] and rep["grounded"]
    assert lower.revise_target(root, rep) is None


def test_an_ungrounded_program_is_sent_back():
    """Medusa's one soundness rule at the whole-artifact level: a program that acts and
    asserts nothing has established nothing."""
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    rep = lower.review(root)
    assert rep["grounded"] is False
    assert lower.revise_target(root, rep) == "root"


def test_repetition_is_GRADED_and_never_sent_back():
    """*"Redundancy is wasteful, not wrong."* Treating it as a defect would push the design
    toward fewer, larger decisions — the direction that RAISES p_self risk. It is reported
    and must not gate."""
    root = N("root", op="sequence", children=[
        _leaf("a", "call", CALL), _leaf("b", "call", dict(CALL)),
        _leaf("v", "ensure", {"op": "ensure",
                              "predicate": {"shape": "count",
                                            "select": {"kind": "vm"}, "gte": 1}}),
    ])
    rep = lower.review(root)
    assert len(rep["repeated"]) == 1, "the duplicate is reported"
    assert lower.revise_target(root, rep) is None, "and it does NOT send the tree back"


def test_repeated_VERDICTS_are_not_counted_as_repetition():
    """Asserting the same thing twice is cheap and often correct — a barrier before work and
    a check after it are the same predicate on purpose."""
    e = {"op": "ensure", "predicate": {"shape": "count", "select": {"kind": "vm"}, "gte": 1}}
    root = N("root", op="sequence", children=[
        _leaf("a", "ensure", e), _leaf("b", "ensure", dict(e))])
    assert lower.review(root)["repeated"] == []


def test_the_review_loop_is_BOUNDED():
    """The note: a program that cannot satisfy its reviewer would be re-authored forever.

    The rebuild here keeps CHANGING the findings (each round adds a statement) so the
    no-progress guard never fires and only the ROUND BOUND can stop it. That separation
    matters: a bound that is only ever reached because progress stalled is not a bound.
    """
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])   # never grounded
    tries = {"n": 0}
    def rebuild(tree, target):
        tries["n"] += 1
        kids = [_leaf(f"a{i}", "new", dict(NEW)) for i in range(tries["n"] + 1)]
        return N("root", op="sequence", children=kids)
    out, rep = lower.review_loop(root, rebuild, rounds=2)
    assert tries["n"] == 2, "stopped at the bound rather than looping forever"
    assert rep["grounded"] is False


def test_no_progress_fires_even_when_the_TREE_changed():
    """Progress is measured by FINDINGS, not by the tree looking different. A rebuild that
    reshuffles without fixing anything is the same wasted round as one that returns the
    identical object — and the weaker guard would miss it."""
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    tries = {"n": 0}
    def rebuild(tree, target):
        tries["n"] += 1
        return N("root", op="sequence", children=[_leaf(f"renamed{tries['n']}", "new", dict(NEW))])
    lower.review_loop(root, rebuild, rounds=5)
    assert tries["n"] == 1, "different tree, identical findings — stopped after one"


def test_the_review_loop_stops_on_NO_PROGRESS():
    """A rebuild that returns the same tree, or the same findings, buys nothing — the
    lesson `REPAIR_UNDELIVERED` already taught one layer down."""
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    tries = {"n": 0}
    def rebuild(tree, target):
        tries["n"] += 1
        return tree                      # identical
    lower.review_loop(root, rebuild, rounds=5)
    assert tries["n"] == 1, "one attempt, then stopped"


def test_a_tree_the_reviewer_rejected_is_STILL_RETURNED():
    """*"The reviewer must never be the only thing standing between a program and the world,
    or a graded verdict quietly becomes a gate."* It returns the tree AND its findings; what
    to do about them is the caller's decision."""
    root = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    out, rep = lower.review_loop(root, lambda t, w: None, rounds=2)
    assert out is not None and rep["grounded"] is False


# ── the decomposer ──────────────────────────────────────────────────────────────────────
def _router(table):
    def route(goal):
        if goal not in table:
            raise AssertionError(f"unrouted goal {goal!r}")
        return table[goal]
    return route


def test_decompose_builds_the_notes_worked_example():
    route = _router({
        "create 5 vms and add them to a network":
            {"atomic": False, "op": "sequence",
             "steps": ["create 5 vms", "add them to a network"]},
        "create 5 vms": {"atomic": True, "op": "new"},
        "add them to a network":
            {"atomic": False, "op": "foreach", "steps": ["add to the network"]},
        "add to the network": {"atomic": True, "op": "call"},
    })
    root = lower.decompose("create 5 vms and add them to a network", route)
    assert [l["goal"] for l in lower.leaves(root)] == ["create 5 vms", "add to the network"]
    assert root["children"][1]["op"] == "foreach", "the branch names its own operator"
    assert lower.depth(root) == 3


def test_a_branch_that_names_no_operator_is_REFUSED_at_decomposition():
    """The note's open question #3, caught where it happened. Letting it through would
    surface later as a FusionError with no idea which routing call produced it."""
    route = _router({"g": {"atomic": False, "op": None, "steps": ["a"]}})
    with pytest.raises(lower.DecompositionError, match="without naming its own operator"):
        lower.decompose("g", route)


def test_a_sub_goal_that_REPEATS_its_parent_is_absorbed_not_nested():
    """The commonest non-termination in practice: the router restates the goal instead of
    splitting it.

    THIS TEST USED TO ASSERT THE BUG. It required the restatement to become a CHILD keeping
    the parent's operator — which put a `foreach` inside a `foreach`, forbidden because the
    language has one loop variable, and killed rungs 5, 11 and 12 end to end. The correct
    reading is that a node decomposing into exactly itself IS atomic, so it collapses to a
    single leaf and the parent never exists to nest anything in."""
    route = _router({"do the thing": {"atomic": False, "op": "call",
                                      "steps": ["do the thing"]}})
    root = lower.decompose("do the thing", route)
    assert lower.is_leaf(root) and root["op"] == "call" and lower.depth(root) == 1


def test_runaway_decomposition_is_REFUSED():
    route = _router({f"g{i}": {"atomic": False, "op": "sequence", "steps": [f"g{i+1}"]}
                     for i in range(12)})
    with pytest.raises(lower.DecompositionError, match="never bottoms out"):
        lower.decompose("g0", route, max_depth=3)


def test_an_atomic_answer_with_no_operator_is_REFUSED():
    route = _router({"g": {"atomic": True}})
    with pytest.raises(lower.DecompositionError, match="named no operator"):
        lower.decompose("g", route)


def test_a_node_that_decomposes_into_ITSELF_collapses_to_one_leaf():
    """MEASURED 2026-07-29: the first version of this guard made a CHILD carrying the
    parent's operator, so a `foreach` parent got a `foreach` child — which the language
    forbids, one loop variable — and rungs 5, 11 and 12 died on a bug the guard introduced.
    A parent and its only child cannot both be the same container."""
    route = _router({"launch every stopped vm":
                     {"atomic": False, "op": "foreach",
                      "steps": ["launch every stopped vm"]}})
    root = lower.decompose("launch every stopped vm", route)
    assert lower.is_leaf(root) and root["op"] == "foreach"
    assert lower.depth(root) == 1, "one node, not a foreach nested in a foreach"


def test_a_LONE_sub_goal_may_not_LOWER_the_intent():
    """RUNG 7, MEASURED 2026-07-29, and it cost the rung every run.

    The router read "make sure exactly 3 vms carry the 'prod' label" correctly as an
    `achieve`, then handed back ONE sub-goal with the intent word swapped — "ENSURE
    exactly 3 vms carry the 'prod' label" — which routed `ensure` on its own merits. The
    program that came out was `ENSURE COUNT(SELECT vm WHERE label = 'prod') = 3;`: valid,
    grounded, nothing unaccounted, and it CHECKS where the operator asked it to ACT.

    Three things had to line up and all three are the point. Fusion treats an intent
    parent with children as a plain SEQUENCE, so the `achieve` contributed nothing. The
    child's ENSURE then satisfied the groundedness check, so `ground()` declined to add
    the verdict that would have made it act. And the existing self-restatement guard is
    byte-exact, so one reworded word walked past it.

    INTENT IS SUPPLIED, NOT INFERRED — that is intent.py's whole argument, and it names
    this very sentence as the example nothing in the words can settle. A restatement is
    not new information about what the operator wanted.
    """
    route = _router({
        "make sure exactly 3 vms carry the 'prod' label":
            {"atomic": False, "op": "achieve",
             "steps": ["ensure exactly 3 vms carry the 'prod' label"]},
        "ensure exactly 3 vms carry the 'prod' label": {"atomic": True, "op": "ensure"},
    })
    root = lower.decompose("make sure exactly 3 vms carry the 'prod' label", route)
    assert root["children"][0]["op"] == "achieve", "a restatement cannot demote the intent"


def test_a_LONE_sub_goal_MAY_still_correct_a_STRUCTURAL_operator():
    """THE COUNTER-EXAMPLE, and it is why the rule above is about intent and not arity.

    Rung 10, same run: 'launch the last new vm' routed `new` — wrong, launching is a
    call — and its lone restatement 'launch the last vm' routed `call`, which is RIGHT.
    Collapsing every one-step answer to the parent's operator would have thrown that
    correction away and kept the `new`.

    So a restatement may fix HOW, never lower WHAT FOR.
    """
    route = _router({
        "launch the last new vm":
            {"atomic": False, "op": "new", "steps": ["launch the last vm"]},
        "launch the last vm": {"atomic": True, "op": "call"},
    })
    root = lower.decompose("launch the last new vm", route)
    assert root["children"][0]["op"] == "call", "structure may still be corrected"


def test_a_LONE_sub_goal_may_RAISE_the_intent():
    """Only lowering is refused. If the router looks at one sub-goal and decides it needs
    MORE authority than the parent named, that is information rather than drift — and
    `intent.violations()` is the thing that refuses reaching above the operator's rung,
    which is a decision with an owner. Silently capping it here would duplicate that
    judgement in a place with no consent behind it."""
    route = _router({
        "check the fleet is right":
            {"atomic": False, "op": "ensure", "steps": ["make the fleet right"]},
        "make the fleet right": {"atomic": True, "op": "achieve"},
    })
    root = lower.decompose("check the fleet is right", route)
    assert root["children"][0]["op"] == "achieve", "raising is left to intent.violations()"


def test_a_leaf_is_shown_what_its_SIBLINGS_already_emitted():
    """The note's open question #4 at the SEMANTIC level. Measured 2026-07-29: "put the red
    ones together" and "launch the last vm" mean nothing alone, because their referent is a
    sibling's decision. Scope threading fixed the BINDING half; this is the other half."""
    # a TOP-LEVEL call, so neither leaf retries and the indices are the emissions
    TOP = {"op": "call", "tool": "launch_vm", "args": {"name": "made"}}
    seen = []
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        seen.append((leaf["goal"], list(context or [])))
        return NEW if leaf["op"] == "new" else TOP
    root = N("root", op="sequence", children=[N("first", op="new"), N("second", op="call")])
    lower.lower_tree(root, emit)
    assert len(seen) == 2, "no retries — one emission per leaf"
    assert seen[0][1] == [], "the first leaf has no siblings yet"
    assert seen[1][1] == [NEW], "the second is shown what the first decided"


def test_ground_adds_a_verdict_only_when_one_is_missing():
    """Medusa's one soundness rule at the root. A leaf cannot supply it — rung 1 really is
    one `new`, and there is no room inside one statement for a judgement about it."""
    V = {"op": "achieve", "predicate": {"shape": "count",
                                        "select": {"kind": "vm"}, "gte": 1}}
    emit = lambda leaf, schema, objection=None, context=None, ancestry=None: V
    bare = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    out = lower.ground(bare, emit, "make a vm")
    assert lower.review(out)["grounded"], "an ungrounded tree gains a verdict"
    already = N("root", op="sequence", children=[_leaf("v", "achieve", V)])
    assert lower.ground(already, emit, "g") is already, "a grounded tree is untouched"


def test_a_verdict_that_cannot_be_authored_leaves_the_tree_ALONE():
    """Inventing one would be the harness vouching for work it did not check. `run()`
    refusing an ungrounded program is the honest outcome."""
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        raise ValueError("no")
    bare = N("root", op="sequence", children=[_leaf("a", "new", NEW)])
    assert lower.ground(bare, emit, "g") is bare


def test_a_leaf_sees_the_goals_it_sits_UNDER():
    """Measured 2026-07-29: "put the red ones together" and "new vm1 with fleet label" are
    unauthorable alone — the colour, the count and the label all live in the PARENT's
    wording. Sibling context gives a leaf what is already DONE; ancestry gives it what it is
    PART OF, and neither substitutes for the other."""
    seen = []
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        seen.append(list(ancestry or []))
        return NEW
    root = N("make 3 red and 2 blue", op="sequence",
             children=[N("the red ones", op="new")])
    lower.lower_tree(root, emit)
    assert seen[0] == ["make 3 red and 2 blue"]


def test_a_leaf_that_will_not_emit_is_RE_ROUTED_as_a_decomposition():
    """A leaf that cannot be emitted is EVIDENCE THE ROUTER WAS WRONG ABOUT ATOMICITY.
    Measured: rungs 8 and 11 handed the WHOLE goal to one leaf — "put every vm on core,
    except db, db goes on dmz" is plainly two statements and no retry makes it one.
    Re-routing uses the channel that answers this at 10/10 instead of asking the decoder to
    do the impossible again."""
    TOP = {"op": "call", "tool": "launch_vm", "args": {"name": "made"}}
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        if leaf["goal"] == "do A and B":
            return {"op": "call"}            # invalid, never emits
        return NEW if leaf["op"] == "new" else TOP
    route = _router({"do A and B": {"atomic": False, "op": "sequence",
                                    "steps": ["do A", "do B"]},
                     "do A": {"atomic": True, "op": "new"},
                     "do B": {"atomic": True, "op": "call"}})
    root = N("do A and B", op="call")
    out = lower.lower_tree(root, emit, route=route)
    assert [l["goal"] for l in lower.leaves(out)] == ["do A", "do B"]


def test_re_routing_stops_when_the_router_INSISTS_it_is_atomic():
    """No infinite recovery: if the router still says atomic, the original failure stands."""
    def emit(leaf, schema, objection=None, context=None, ancestry=None):
        return {"op": "call"}                # always invalid
    route = _router({"g": {"atomic": True, "op": "call"}})
    with pytest.raises(lower.LoweringError):
        lower.lower_tree(N("g", op="call"), emit, route=route)
