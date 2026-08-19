"""THE FRONT DOOR — junk out ASAP, one layer down (the operator, 2026-08-19).

The v2 degradation run priced two cells and the operator ruled them ONE defect:
a leading filler killed 9/10 instructed acts (the imperative-shape test never fired),
and a typo'd CLOSED-SET marker un-recognized its construct so the debris became op
targets (`stop_vm(sorry)`). Both are junk surviving past the entrance. The fix is not
per-consumer — it is ONE pass before ANY construct reads, producing a working VIEW
plus an offset map back to the original bytes, so spans still score at the original
offsets and names are never rewritten.
"""
import pytest

from orchestrator.seam import front_door as FD


def test_a_typoed_marker_is_recognized_in_its_phrase():
    # `no wati` sits where `no wait` sits, every other phrase word exact — recognized
    v = FD.read("restrt the web vm, no wati, the db one")
    assert "no wait" in v.text
    assert "wati" not in v.text
    assert any("wati" in n for n in v.notices)
    # the operation verb's own typo is NOT a closed-set word — never touched
    assert "restrt" in v.text


def test_a_name_is_never_rewritten():
    v = FD.read("stop alpah — sorry, i mesnt beta")
    assert "i meant" in v.text          # the marker is recognized
    assert "alpah" in v.text            # the name's typo is the name
    assert "beta" in v.text


def test_courtesy_with_a_typo_is_recognized():
    v = FD.read("wehn you get a chance, stop the test vms")
    assert "when you get a chance" in v.text


def test_a_filled_pause_is_dropped_and_offsets_map_back():
    original = "uh stop the vms on the lab network"
    v = FD.read(original)
    assert v.text == "stop the vms on the lab network"
    # a span found in the VIEW maps back to its ORIGINAL offsets
    s = v.text.index("the vms")
    e = s + len("the vms on the lab network")
    assert original[v.back[s]:v.back[e]] == "the vms on the lab network"


def test_evidence_is_opaque():
    # ruled: evidence is opaque testimony — nothing inside quotes is ever edited
    v = FD.read("the log says 'no wati, retrying'")
    assert "no wati" in v.text


def test_clean_text_is_the_identity():
    req = "stop the web vm and launch the db one"
    v = FD.read(req)
    assert v.text == req
    assert v.notices == []
    assert all(v.back[i] == i for i in range(len(req) + 1))


def test_a_real_word_pair_below_the_length_floor_is_left_alone():
    # `no way` is ed-1 inside... it is not: 3 chars < the floor — never touched
    v = FD.read("there is no way the db vm survives")
    assert "no way" in v.text


def test_mid_sentence_pause_with_commas():
    v = FD.read("stop it, um, right away")
    assert v.text == "stop it, right away"
