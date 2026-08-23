"""THE LICENCE HOLE — a verb Gorgon cannot read licenses nothing mutating.

Measured 08-22 (n=3): Hebrew `תעצור the web vm` fired stop_vm. pass2's verb licence read the
first `[a-z]+` word, so a foreign verb was licensed by the first English NOUN — i.e. by
nothing — and translated freely. Gorgon reads English by declaration (ledger #12/#16).
Model-free: the pass-2 answer is canned, so this is the filter's behaviour, not the model's.
"""
from planner.formula.legal import Board
from orchestrator.languages.english.seam import pass1 as P1, pass2 as P2
from tests.test_twopass_schema import _canned

B = Board()


def _ops(req, steps):
    rows = P1.run_scanned(req, board=B)
    channel, was = _canned(steps)
    try:
        return [o.operator for _, o in P2.operations_by_clause(req, rows, board=B)]
    finally:
        channel.constrained = was


def _handle(req):
    rows = P1.run_scanned(req, board=B)
    return P2.symbol_table(rows, B)[0].handle


def test_a_foreign_verb_licenses_no_mutation():
    req = "תעצור the web vm"
    h = _handle(req)
    got = _ops(req, [("stop_vm", h, None), ("launch_vm", h, None), ("probe_exists", h, None)])
    assert "stop_vm" not in got and "launch_vm" not in got, got
    assert "probe_exists" in got, "the observe arm is housekeeping, never a wrong choice"


def test_the_control_an_english_verb_still_translates_freely():
    req = "restart the web vm"
    h = _handle(req)
    got = _ops(req, [("stop_vm", h, None), ("launch_vm", h, None)])
    assert "stop_vm" in got and "launch_vm" in got


def test_english_shaped_nonsense_is_not_the_hole():
    # `florp` is declared OUT of scope here: telling it from `restart` needs a lexicon
    # the codex does not claim to be. This pins the scope, not a virtue.
    req = "florp the web vm"
    h = _handle(req)
    assert "stop_vm" in _ops(req, [("stop_vm", h, None)])


def test_the_derive_arm_is_guarded_too():
    # Q derives an op from the licence when the model answers nothing — with a foreign
    # verb ahead of an op-segment word, `_cw0[0]` would be the segment itself
    req = "תפעיל launch the blue ones"
    assert _ops(req, []) == []


def test_the_predicate_itself():
    f = P2._foreign_verb_position
    assert f("תעצור the web vm") and f("arrête la vm") and f("停止 alpha")
    assert not f("stop alpha") and not f("please stop alpha") and not f("3 vms, stop them")
    assert not f("'prod' vms: stop") and not f("") and f("  תעצור")


# ── rule 8: a cut must not split a noun phrase from the predicate that restricts it ──
def test_a_goal_heads_subject_keeps_its_predicate():
    """Language benchmark rung 7 (08-22): N3's comma restore cut `exactly 3 vms ▸ carry the
    'prod' label`; the row lost label=prod and the goal became count(vm)=3 — the DELETION
    shape. A goal head takes a clause: the NP after it is a subject, the base-form op
    word after that is its predicate."""
    from orchestrator.languages.english.seam import front_door as FD
    s = "make sure exactly 3 vms carry the 'prod' label"
    assert P2.merge_cut_points(s) == []
    view = FD.read(s)
    assert view.text == s and not view.notices
    rows = P1.run_scanned(view.text, board=B)
    assert [(r.kind, r.count, r.where) for r in rows] == [("vm", 3, {"label": "prod"})]


def test_rule_8_does_not_undo_rules_5_and_6():
    cuts = P2.merge_cut_points
    assert cuts("make sure the web vm is stopped launch the db vm") == [32]   # 5, as before
    assert cuts("don't stop the web vm stop the db vm") == [22]              # 6, as before
    assert cuts("if alpha is stopped launch it") == [20]                      # 5, as before
    # the plural subject's base-form predicate is now SEEN, so the imperative after it cuts
    assert cuts("make sure the vms carry the label stop the db vm") == [34]
    assert cuts("if you stop the web vm launch the db vm") == [23]
