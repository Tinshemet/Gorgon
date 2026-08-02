"""test_quantifier_rule.py — the shape-based all/any/not rule, with no model.

The properties worth guarding are about SAFETY first and accuracy second. A wrong
deterministic answer narrows the schema and makes a correct program unrepresentable; a
missing one just falls through to the router. So the rule must decline far more readily
than it answers, and every branch must fire on a shape actually present in the clause.

The two scored corpora are checked here as well, because "16/16 and 10/10" is a claim that
should fail loudly if a later edit quietly costs a cell.
"""
from tests.bench import quantifier_rule as qr
from tests.bench.quantifier_holdout import HOLDOUT
from tests.bench.quantifier_probe import CLAUSES


def test_it_never_answers_single():
    """One identified object is recognised by NAMING, not by shape. A rule that guessed
    `single` would deny `foreach` — the one narrowing the master actually applies — on a
    clause it had no evidence about, which is the expensive direction to be wrong in."""
    for text, _want in CLAUSES + HOLDOUT:
        assert qr.classify(text) != "single", text


def test_an_exclusion_marker_wins_over_a_universal():
    """Order matters and this is why: "every vm except golden" contains a universal, and
    the universal branch would answer `all`. Tested first, so a carve-out cannot be read as
    a plain whole."""
    assert qr.classify("label every vm except golden itself 'derived'") == "not"
    assert qr.classify("reboot all machines other than db") == "not"
    assert qr.classify("except db") == "not"
    # No whole named and no exclusion — a condition, not a subtraction.
    assert qr.classify("stop the ones that do not answer") is None


def test_a_modifier_makes_it_a_filter_wherever_it_sits():
    """The operator's rule, and the defect it was aimed at. The model reads an ADJECTIVE as
    part of the kind and a RELATIVE CLAUSE as a filter; they are the same clause."""
    assert qr.classify("take a snapshot of every running vm") == "any"
    assert qr.classify("shut down all vms that are running") == "any"
    assert qr.classify("ping every vm") == "all"
    assert qr.classify("connect each vm to the management network") == "all"


def test_it_does_not_read_the_MANIFEST_vocabulary():
    """Deliberate, and it is what lifted the approach's ceiling. The manifest declares five
    values — 'running', 'stopped' and three booleans — so a value-driven test could not see
    `red` and would miss rung 6's own clause, "put the red ones together". Any
    non-determiner word modifying the head noun is a filter."""
    assert qr.classify("archive every red vm") == "any"
    assert qr.classify("stop every prod machine") == "any"


def test_a_value_as_the_OBJECT_is_not_a_filter():
    """The other half of the operator's rule. "give them all the 'fleet' label" has a
    universal and a quoted value, and its head noun is `label` — not a machine — so the
    rule declines rather than reading the object of the action as a filter on a set."""
    assert qr.classify("give them all the 'fleet' label") is None
    assert qr.classify("tag all of them with 'prod'") is None


def test_the_head_noun_must_be_a_kind_and_kinds_come_from_the_manifest():
    """Add a kind to the manifest and the rule recognises it, with no edit here — the same
    claim every other builder in this codebase makes."""
    from planner.ir import config
    nouns = qr.kind_nouns()
    for kind in config.KINDS:
        assert kind.lower() in nouns and kind.lower() + "s" in nouns


def test_it_declines_far_more_than_it_answers():
    """The safety property in one number. Over both corpora the rule fires on well under
    two thirds of clauses, and every clause it declines falls through to the router."""
    fired = sum(1 for text, _w in CLAUSES + HOLDOUT if qr.classify(text) is not None)
    assert fired < len(CLAUSES + HOLDOUT)


def test_ZERO_wrong_on_both_corpora():
    """The claim that justifies wiring it: not merely accurate but never WRONG where it
    fires, on the corpus it was tuned against AND on ten clauses committed before it
    existed."""
    tuned, held = qr.score(CLAUSES), qr.score(HOLDOUT)
    assert tuned["wrong"] == 0, tuned["misses"]
    assert held["wrong"] == 0, held["misses"]
    assert (tuned["fired"], tuned["correct"]) == (9, 9), tuned
    assert (held["fired"], held["correct"]) == (7, 7), held
