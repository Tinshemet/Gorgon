"""THE IMPERATIVE SHAPE, WITH OR WITHOUT ITS ARTICLE — noise-floor classes 1+2 (08-19).

Terse noise drops articles, and the imperative test demanded one: `restart db vm`
failed `words[1] in dets` and the act vanished — 4 of the 7 terse act losses on the
certified v2 run. Three more died on object words that ARE determiners' own grammar
family but were not in the set: `stop most of vms` · `launch everything` · `snapshot
ones that are still running`.

One predicate now owns the question (`scan.opens_imperative`), built from closed
classes only: the determiner set + quantifiers + universals + pro-forms, and the
article-less arm requires a MANIFEST NOUN heading the object — read from the board,
never hand-listed.
"""
from planner.formula.legal import Board

from orchestrator.seam.scan import opens_imperative


B = Board()


def _t(clause):
    return opens_imperative(str(clause).lower().split(), B)


# ── the certified terse failures this must heal ─────────────────────────────────────

def test_an_articleless_object_headed_by_a_manifest_noun():
    assert _t("restart db vm because it is stuck")
    assert _t("snapshot db vm")
    assert _t("restart web vm and db vm")
    assert _t("restart web vm")


def test_a_quantifier_object():
    assert _t("stop most of vms")


def test_a_universal_object():
    assert _t("launch everything")


def test_a_pro_form_object():
    assert _t("snapshot ones that are still running")


def test_the_articled_shape_still_passes():
    assert _t("stop the test vms")
    assert _t("launch it")
    assert _t("restart it")


# ── what must NOT read as an imperative ──────────────────────────────────────────────

def test_a_bare_np_is_not_an_imperative():
    assert not _t("the web vm")          # ba-0004's first fragment — a thing, not an act
    assert not _t("the db one")


def test_a_rule_is_not_an_imperative():
    assert not _t("every vm must carry a label")     # opens on its own quantifier


def test_testimony_is_not_an_imperative():
    assert not _t("vm2 is not working")
    assert not _t("pings time out")


def test_a_question_is_not_an_imperative():
    assert not _t("is alpha running")
    assert not _t("which vms are stopped")


def test_a_negated_imperative_is_left_to_its_own_reader():
    assert not _t("don't stop the web vm")
