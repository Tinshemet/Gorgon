"""FOR / FROM — A STRUCTURED SELECTOR (operator ruling 2026-09-14).

`for` and `from` mark a selector whose ROLE FOLLOWS ITS COMPLEMENT — the world decides. A world
object (a kind noun, or a declared standing object) is SELECTED; a purpose or a beneficiary is not
a world object, so the same structure stays an adjunct. This recovers the tail the model never
points at past a quoted command (`run "<cmd>" for the vms`).

Model-free: annotate_roles reads the role deterministically from the sentence + the manifest, so
these run without the model (the copula-clitic/TIME selectors work the same way).
"""
from tests.bench.read_eval import runner as R


def _selectors(sent):
    r = R.annotate_roles({"sentence": sent, "rows": [], "operations": []})
    return [s["span"] for s in r["rows"] if s.get("role") == "selector"]


def test_for_a_world_object_recovers_the_tail():
    assert "the vms" in _selectors('run "mysqlshow --status db" for the vms')


def test_from_a_standing_object_is_selected():
    assert "lab" in _selectors("restore db from lab")


def test_for_a_named_vm_is_selected():
    assert "beta" in _selectors("stop the vms for beta")


def test_a_purpose_complement_is_not_a_selector():
    assert _selectors("snapshot alpha for backup") == []


def test_a_beneficiary_complement_is_not_a_selector():
    assert _selectors("make a vm for me") == []


def test_a_numeric_complement_is_not_a_selector():
    assert _selectors("wait for 5 minutes") == []


def test_a_for_inside_a_quoted_command_does_not_leak():
    # `for db` inside the quote must not survive as a selector; only the trailing `the vms` does
    sels = _selectors('run "restore for db" for the vms')
    assert "the vms" in sels
    assert "db" not in sels
