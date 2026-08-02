"""test_tree_keeper.py — the tree regime's correct-AFTER pass, tested with no model.

THE ROWS ARE FLAT AND KEYED BY PATH, which is a change from the nested-node shape these
tests were written against. Nothing ever called that shape: the engine's queue is
breadth-first, so it builds path-keyed rows, and a keeper demanding a tree object would
have made the engine build a second structure for the auditor's benefit. Every property
below is the one it always asserted; only the fixture moved.
"""
import copy

from planner import tree_keeper as tk

P_THREE = {"shape": "count", "select": {"kind": "vm"}, "eq": 3}


def _holds(answer):
    return lambda pred, scope: (answer, "stubbed")


def _row(goal, path, premise=None, op="call", **rest):
    return {"goal": goal, "path": path, "op": op, "premise": premise, **rest}


def test_a_node_with_no_premise_is_UNKNOWN_never_sound():
    """Decision 6's rule applied to plans: unprobed is not healthy. A keeper reporting zero
    infected while nothing recorded a premise would be reporting an unasked question."""
    rows = tk.inspect([_row("g", "0", op="new")], _holds(True))
    assert rows[0]["state"] == tk.UNKNOWN
    assert tk.drift(rows)["verdict"] == tk.UNKNOWN
    assert "not the same as sound" in tk.report(rows)


def test_a_premise_that_still_holds_is_sound():
    rows = tk.inspect([_row("g", "0", P_THREE, op="new")], _holds(True))
    assert rows[0]["state"] == tk.SOUND and tk.drift(rows)["verdict"] == "clear"


def test_a_broken_premise_POISONS_THE_WHOLE_SUBTREE():
    """THE DEFECT ITSELF: every child is locally valid and wrong anyway, because the thing
    the parent assumed stopped being true."""
    rows = tk.inspect([_row("set up the fleet", "0", P_THREE, op="foreach"),
                       _row("attach it", "0.0")], _holds(False))
    assert [r["state"] for r in rows] == [tk.INFECTED, tk.INFECTED]
    assert "built under" in rows[1]["why"], "the child says WHY, and names the parent"


def test_the_report_names_the_ORIGIN_not_just_the_casualties():
    """A reader shown the children first chases symptoms. Origins are the nodes whose OWN
    premise broke, distinct from those merely underneath one."""
    d = tk.drift(tk.inspect([_row("root", "0", P_THREE, op="foreach"),
                             _row("child", "0.0", P_THREE)], _holds(False)))
    assert d["infected"] == 2 and len(d["origins"]) == 1
    assert d["origins"][0]["goal"] == "root"


def test_parents_are_reported_BEFORE_children():
    rows = tk.inspect([_row("child", "0.0"), _row("root", "0", P_THREE, op="foreach")],
                      _holds(True))
    assert [r["goal"] for r in rows] == ["root", "child"]


def test_a_seam_that_cannot_answer_is_UNKNOWN_not_sound():
    """A keeper that treated an evaluator error as 'fine' would go quiet exactly when the
    world stopped being readable — which is when it matters most."""
    def boom(pred, scope):
        raise RuntimeError("registry unreachable")
    rows = tk.inspect([_row("g", "0", P_THREE, op="new")], boom)
    assert rows[0]["state"] == tk.UNKNOWN


def test_a_verdict_the_engine_already_reached_is_not_overwritten():
    """EVIDENCE BEATS INFERENCE. The witness re-visit RE-PLANS the goal and asks whether
    work remains, which is strictly stronger than re-checking a count — so this fills in the
    nodes that had no witness and leaves the ones that did."""
    rows = tk.inspect([_row("witnessed", "0", P_THREE, state=tk.SOUND,
                            why="ran with its own closing witness")], _holds(False))
    assert rows[0]["state"] == tk.SOUND
    assert "closing witness" in rows[0]["why"]


def test_it_changes_NOTHING():
    """The book keeper's constitutional rule: it marks, it never re-plans. Re-planning is a
    MAKE and MAKEs belong to something with consent behind them."""
    rows = [_row("root", "0", P_THREE, op="foreach"), _row("k", "0.0")]
    before = copy.deepcopy(rows)
    tk.inspect(rows, _holds(False))
    assert rows == before
