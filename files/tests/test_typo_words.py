"""SINGLE-WORD TYPO RECOGNITION — N2, the operator's ruling (2026-08-19).

*"on 'sure-hit' — very distinct common words like thrm = them, or even verbs — the
system should try to correct it. but 'eveyr' could mean ever or every... so we run all
possibilities (within common sense, not the whole of the english language) then see
which one produces the most likely sentence."*

The design that honours it: candidates come ONLY from our own closed sets (object
openers · operation words · manifest nouns), Damerau distance 1, word >=4 letters and
not itself known. The SIM CHECK is the slot test: each candidate is tried in place and
kept only if the grammar around it votes — an opener needs a noun after it, a pronoun
needs a verb before it, a verb needs clause-initial position, a noun needs an opener
in front. One fitting candidate -> fixed, with a notice. Ties or no fit -> untouched.
`ever` is protected without being known: in "did you eveyr stop it" the candidate
`every` fails its slot, so nothing fires.
"""
from orchestrator.languages.english.seam import front_door as FD


def test_a_pronoun_sure_hit():
    v = FD.read("create two vms and put thrm on the dmz network")
    assert "put them on" in v.text
    assert any("thrm" in n for n in v.notices)


def test_a_verb_sure_hit():
    v = FD.read("stop alpha. then launhc beta.")
    assert "launch beta" in v.text


def test_an_opener_fixed_when_its_slot_votes():
    v = FD.read("put on the lab network eveyr vm carrying the prod label")
    assert "every vm" in v.text


def test_the_same_word_left_alone_when_the_slot_refuses():
    # `eveyr` here could as well be `ever` — no noun follows, the candidate fails
    v = FD.read("did you eveyr stop it")
    assert "eveyr" in v.text


def test_a_manifest_noun_inside_its_np():
    v = FD.read("create two vms and put them on the dmz netwrk")
    assert "dmz network" in v.text


def test_a_name_is_never_a_candidate():
    # `alpah` is edit-1 from the NAME alpha — names are no closed set; untouched
    v = FD.read("stop alpah please")
    assert "alpah" in v.text


def test_a_content_word_is_never_a_candidate():
    v = FD.read("put on the lab network every vm carryimg the prod label")
    assert "carryimg" in v.text


def test_quotes_stay_opaque():
    v = FD.read("the log says 'launhc beta failed'")
    assert "launhc" in v.text


def test_a_known_word_is_never_touched():
    # `them` is itself a closed-set word — no candidate search ever runs on it
    v = FD.read("stop the vms and label them test")
    assert v.text == "stop the vms and label them test"


def test_offsets_still_map_back():
    original = "put thrm on the dmz netwrk"
    v = FD.read(original)
    s = v.text.index("the dmz")
    assert original[v.back[s]:].startswith("the dmz")
