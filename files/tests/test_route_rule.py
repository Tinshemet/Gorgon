"""test_route_rule.py — new-vs-call decided by shape and the manifest, with no model.

D9's defect is one shape: the atomicity router answers `new` for a goal acting on something
ALREADY THERE, and rung 3's "put web on lab" became `NEW vm FROM $web` — a spurious clone
from a program that validated. Teaching the router harder was measured and it TRADES
(f3ccfd8), so this computes the answer instead.

The properties worth guarding are the two that make it different from the rule anyone
writes first.
"""
from tests.bench import route_rule as rr
from tests.bench.route_holdout import HOLDOUT
from tests.bench.route_menu_probe import CELLS


def test_the_ADJECTIVE_new_is_not_evidence_of_creation():
    """THE BUG MY FIRST VERSION HAD, and it is the same mistake the router makes. Listing
    `new` among the creation words answered `new` for "launch the new vm" and "move resource
    to new network" — three of seven cells wrong, because in both the word describes a
    machine that already exists. A word that can modify a noun cannot be evidence."""
    assert rr.classify("launch the new vm", ["clone golden into a new vm"]) == "call"
    assert rr.classify("move resource to new network",
                       ["create a new network for the red resources"]) == "call"
    assert rr.classify("launch the last new vm", ["clone golden into a new vm"]) == "call"


def test_the_discriminator_is_KIND_HOOD_not_the_verb():
    """`NEW` brings a declared KIND into existence. So a creation verb over something the
    world does not declare is a tool call wearing a creation verb, and a creation verb over
    a declared kind is a `new` however the sentence is phrased."""
    assert rr.classify("add a second disk to web", ["create a vm named web"]) == "call"
    assert rr.classify("set up a network called dmz") == "new"
    assert rr.classify("build the lab network") == "new"
    # `snapshot` IS declared, which is what corrected the held-out key.
    from orchestrator.ai.planner.ir import config
    assert "snapshot" in config.KINDS
    assert rr.classify("create a snapshot of web", ["create a vm named web"]) == "new"


def test_copying_answers_new_without_a_kind_noun():
    """"take a copy of golden" names no kind and copies an existing vm into a new one.
    `NEW ... FROM $source` is exactly that statement."""
    assert rr.classify("take a copy of golden") == "new"
    assert rr.classify("clone golden once more", ["clone golden into a new vm"]) == "new"


def test_a_goal_naming_an_earlier_sibling_s_work_is_acting_on_it():
    """D9's own sentence: a goal whose referents already exist cannot be a `new`."""
    assert rr.classify("put web on lab",
                       ["create a network called lab", "create a vm named web"]) == "call"
    assert rr.classify("start it", ["create a vm named beta"]) == "call"


def test_kinds_come_from_the_manifest():
    from orchestrator.ai.planner.ir import config
    words = rr.kind_words()
    for kind in config.KINDS:
        assert kind.lower() in words and kind.lower() + "s" in words


def test_ZERO_wrong_on_both_corpora():
    """The claim that would justify wiring it. The held-out fourteen were committed before
    the rule existed; one key was corrected after scoring and the correction is documented
    in the corpus itself."""
    tuned, held = rr.score(CELLS), rr.score(HOLDOUT)
    assert tuned["wrong"] == 0, tuned["misses"]
    assert held["wrong"] == 0, held["misses"]
    assert (tuned["fired"], tuned["correct"]) == (7, 7), tuned
    assert (held["fired"], held["correct"]) == (14, 14), held
