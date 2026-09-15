"""EXCEPT — a carved-out world object is EXCLUDED even when the model never rowed it (2026-09-15).

The marathon's one genuine content miss: `launch all the vms except grubnash` rowed the quantified
patient but dropped the name after `except`, silently keeping a prohibited target in the action set
(the safety-bad direction). The except-scan in annotate_roles reads it deterministically, like the
for/from selector — model-free, no model call needed."""
from tests.bench.read_eval import runner as R


def _excluded(sent):
    r = R.annotate_roles({"sentence": sent, "rows": [], "operations": []})
    return [s["span"] for s in r["rows"] if s.get("role") == "excluded"]


def test_except_a_named_vm_is_excluded():
    assert "grubnash" in _excluded("launch all the vms except grubnash")   # the marathon miss


def test_except_the_db_is_excluded():
    assert "db" in _excluded("stop everything except the db")


def test_but_not_a_name_is_excluded():
    assert "web" in _excluded("restart the vms but not web")


def test_except_a_non_object_does_not_fire():
    assert _excluded("restart it except when it is down") == []
    assert _excluded("snapshot all except that one") == []
