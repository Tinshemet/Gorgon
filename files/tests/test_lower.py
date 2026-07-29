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
    def emit(leaf, schema):
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
