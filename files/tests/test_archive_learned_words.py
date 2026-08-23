"""ATTRIBUTES ARE LEAVES (operator ruling 08-23) — step 1: the lookup.

Every learned word is an entry {entry · type · owners}; the manifest's vocabulary is served as
entries of that shape beside the told rows, through ONE lookup that returns the LIST (one word,
several owners, by design — the reader ranks, a tie is an ASK). `known` is untouched.
"""
import pytest

from planner.formula.legal import Board
from orchestrator.languages.english.seam import archive as A

B = Board()


def _types(word):
    return sorted({(e.type, e.owners, e.attribute) for e in A.Archive().learned(word, B)})


def test_the_test_case_cpu_and_ram_resolve_with_owner_and_attribute():
    assert _types("ram") == [("attribute", ("vm",), "memory_mb")]
    assert _types("memory") == [("attribute", ("vm",), "memory_mb")]
    assert _types("gb") == [("unit", ("vm",), "memory_mb")]
    assert _types("mb") == [("unit", ("vm",), "memory_mb")]
    assert ("unit", ("vm",), "cpu_cores") in _types("cores")
    assert _types("cpu") == [("attribute", ("vm",), "cpu_cores")]


def test_the_rest_of_the_attributes_come_for_free():
    assert _types("ip") == [("attribute", ("vm",), "ip")]          # attr + alias, ONCE
    assert _types("address") == [("attribute", ("vm",), "ip")]
    assert _types("mac") == [("attribute", ("vm",), "mac")]
    assert _types("label") == [("attribute", ("vm",), "label")]


def test_a_kind_and_its_nouns_are_class_words():
    vm = [e for e in A.Archive().learned("vm", B) if e.type == "class"]
    assert vm and vm[0].kind == "vm" and vm[0].owners == ()
    assert [e.kind for e in A.Archive().learned("machine", B) if e.type == "class"] == ["vm"]


def test_one_word_several_owners_is_returned_not_picked():
    owners = {e.owners for e in A.Archive().learned("name", B)}
    assert {("vm",), ("network",)} <= owners, "name belongs to more than one class — rule 4"


def test_a_value_is_not_vocabulary():
    assert A.Archive().learned("running", B) == [], "attr_values are the owner's scrutiny"
    assert A.Archive().learned("grabnash", B) == []


def test_a_told_word_joins_the_lookup_only_once_ratified(tmp_path):
    arc = A.Archive(str(tmp_path / "a.json"))
    arc.propose("grabnash", "an operating system", type="value", owners=("vm",),
                attribute="os_type", said="grabnash is an os")
    assert arc.learned("grabnash", B) == []                       # a proposal describes
    arc.ratify("grabnash", who="operator")
    got = arc.learned("grabnash", B)
    assert [(e.type, e.owners, e.attribute) for e in got] == [("value", ("vm",), "os_type")]
    arc.save()
    again = A.Archive(str(tmp_path / "a.json"))                   # survives the disk
    assert again.known("grabnash").owners == ("vm",) and again.known("grabnash").type == "value"


def test_a_type_outside_the_closed_list_is_refused():
    with pytest.raises(ValueError):
        A.Archive().propose("x", type="flavour")


def test_children_inherit_their_owners(tmp_path):
    # "entry: RAM, type unit, owners: computer (and its children)" — vm is a computer
    arc = A.Archive(str(tmp_path / "a.json"))
    arc.propose("vram", "video memory", type="attribute", owners=("computer",))
    arc.ratify("vram")
    arc.propose("vm", "a machine", classes=("computer",))
    arc.ratify("vm")
    entry = arc.known("vram")
    assert arc.owns(entry, "vm") and arc.owns(entry, "computer") and not arc.owns(entry, "network")
    assert arc.ancestors("vm") == ("computer",)


def test_known_is_untouched_by_the_manifest():
    assert A.Archive().known("ram") is None, "the manifest is served beside the told rows, never merged"
