"""test_tree_keeper.py — the tree regime's correct-AFTER pass, tested with no model."""
from orchestrator.ai.planner import tree_keeper as tk
from orchestrator.ai.planner.ir import lower

N = lower.node
P_THREE = {"shape": "count", "select": {"kind": "vm"}, "eq": 3}


def _holds(answer):
    return lambda pred, scope: (answer, "stubbed")


def test_a_node_with_no_premise_is_UNKNOWN_never_sound():
    """Decision 6's rule applied to plans: unprobed is not healthy. A keeper reporting zero
    infected while nothing recorded a premise would be reporting an unasked question."""
    rows = tk.inspect(N("g", op="new"), _holds(True))
    assert rows[0]["state"] == tk.UNKNOWN
    assert tk.drift(rows)["verdict"] == tk.UNKNOWN
    assert "not the same as sound" in tk.report(rows)


def test_a_premise_that_still_holds_is_sound():
    root = tk.with_premise(N("g", op="new"), P_THREE)
    rows = tk.inspect(root, _holds(True))
    assert rows[0]["state"] == tk.SOUND and tk.drift(rows)["verdict"] == "clear"


def test_a_broken_premise_POISONS_THE_WHOLE_SUBTREE():
    """THE DEFECT ITSELF: every child is locally valid and wrong anyway, because the thing
    the parent assumed stopped being true."""
    kid = N("attach it", op="call")
    root = tk.with_premise(N("set up the fleet", op="foreach", children=[kid]), P_THREE)
    rows = tk.inspect(root, _holds(False))
    assert [r["state"] for r in rows] == [tk.INFECTED, tk.INFECTED]
    assert "built under" in rows[1]["why"], "the child says WHY, and names the parent"


def test_the_report_names_the_ORIGIN_not_just_the_casualties():
    """A reader shown the children first chases symptoms. Origins are the nodes whose OWN
    premise broke, distinct from those merely underneath one."""
    kid = tk.with_premise(N("child", op="call"), P_THREE)
    root = tk.with_premise(N("root", op="foreach", children=[kid]), P_THREE)
    d = tk.drift(tk.inspect(root, _holds(False)))
    assert d["infected"] == 2 and len(d["origins"]) == 1
    assert d["origins"][0]["goal"] == "root"


def test_parents_are_reported_BEFORE_children():
    kid = N("child", op="call")
    root = tk.with_premise(N("root", op="foreach", children=[kid]), P_THREE)
    assert [r["goal"] for r in tk.inspect(root, _holds(True))] == ["root", "child"]


def test_a_seam_that_cannot_answer_is_UNKNOWN_not_sound():
    """A keeper that treated an evaluator error as 'fine' would go quiet exactly when the
    world stopped being readable — which is when it matters most."""
    def boom(pred, scope):
        raise RuntimeError("registry unreachable")
    rows = tk.inspect(tk.with_premise(N("g", op="new"), P_THREE), boom)
    assert rows[0]["state"] == tk.UNKNOWN


def test_it_changes_NOTHING():
    """The book keeper's constitutional rule: it marks, it never re-plans. Re-planning is a
    MAKE and MAKEs belong to something with consent behind them."""
    import copy
    root = tk.with_premise(N("root", op="foreach", children=[N("k", op="call")]), P_THREE)
    before = copy.deepcopy(root)
    tk.inspect(root, _holds(False))
    assert root == before
