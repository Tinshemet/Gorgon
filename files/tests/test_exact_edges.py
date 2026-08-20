"""EXACT — the span's edges (the certified boundary families, 2026-08-20).

E1: A KIND WORD IN VERB POSITION IS THE VERB when what follows cannot join it in one
noun phrase — `snapshot the db VM` carries two different kinds, and one NP cannot;
`snapshot the ONES` opens a referential pro-form. Five of the 26 exact misses, one rule.
The guard: `vms the operator built` has no second kind and stays a noun.
"""
from planner.formula.legal import Board

from orchestrator.seam.scan import scan

B = Board()


def test_the_ambiguous_verb_leaves_the_span():
    assert scan("vm", "snapshot the db vm", B).span == "the db vm"
    assert scan("vm", "snapshot the web vm", B).span == "the web vm"


def test_the_pro_form_object_frees_the_verb():
    got = scan("ones", "snapshot the ones that are still running", B)
    assert not got.span.startswith("snapshot")


def test_a_bare_np_keeps_its_noun():
    assert scan("vm", "the web vm", B).span == "the web vm"


def test_a_reduced_relative_is_not_an_imperative():
    # no second kind after the determiner — the noun reading survives
    got = scan("vms", "vms the operator built", B)
    assert got.span.startswith("vms")


def test_the_freed_verb_is_owned_by_its_reading():
    # the ghost rule: E1 frees `snapshot` from the span, so the gate must consume it
    from orchestrator.seam.scan import verb_position_words
    assert verb_position_words("snapshot the db vm, scratch that, snapshot the web vm",
                               B) == {"snapshot"}
    # a noun occurrence anywhere keeps the word a thing
    assert verb_position_words("create a snapshot of every running vm", B) == set()


# ── E5: the partitive — quantifier + of + NP is ONE thing ────────────────────────────

def test_the_partitive_keeps_its_quantifier():
    assert scan("vms", "stop most of the vms", B).span == "most of the vms"
    assert scan("vms", "stop most of vms", B).span == "most of vms"


def test_of_still_cuts_between_two_things():
    # "a snapshot OF every running vm" is two things — the boundary survives
    assert scan("snapshot", "create a snapshot of every running vm", B).span == "a snapshot"
    got = scan("vm", "create a snapshot of every running vm", B)
    assert not got.span.startswith("a snapshot")


# ── E2/E3/E4: the remaining edge families (certified misses, 2026-08-20) ─────────────

def test_a_following_predicate_stays_out():
    assert scan("network", "if the lab network exists, stop it", B).span == "the lab network"
    assert scan("vm", "tell me if the db vm restarted", B).span == "the db vm"
    assert scan("job", "spin down the render vms after the job finishes", B).span == "the job"
    assert scan("alpha", "stop the test vms even though alpha is busy", B).span == "alpha"


def test_a_transfer_verbs_final_pp_is_the_verbs_argument():
    assert scan("notes", "put the notes from the meeting in the shared folder", B).span \
        == "the notes from the meeting"
    assert scan("image", "clone the golden image into three vms", B).span == "the golden image"
    # a plain act's PP restricts the noun and STAYS
    assert scan("vm", "stop the vms on the lab network", B).span == "the vms on the lab network"


def test_a_value_after_the_object_belongs_to_the_verb():
    assert scan("vm", "label the red vms 'ready'", B).span == "the red vms"
    assert scan("vm", "label the vms test", B).span == "the vms"


def test_a_purpose_infinitive_stays_out():
    assert scan("vm", "stop the vms to free up memory", B).span == "the vms"


def test_a_manner_literal_stays_out():
    assert scan("vm", "restart the vms one at a time", B).span == "the vms"


def test_a_clock_adjunct_stays_out():
    assert scan("vm", "snapshot every vm at 21:30", B).span == "every vm"


def test_a_leading_object_pronoun_stays_out():
    assert scan("network", "create two vms and put them on the dmz network", B).span \
        == "the dmz network"
    assert scan("vms", "tell me which vms it skipped", B).span == "which vms"


def test_an_aux_participle_boundary_stops_the_walk():
    got = scan("others", "the web vm, after you have checked the others, restart it", B)
    assert got.span == "the others"


def test_a_new_np_after_the_head_stops_the_walk():
    got = scan("network", "put on the lab network every vm carrying the prod label", B)
    assert got.span == "the lab network"


def test_the_testimony_frame_stays_out_of_the_patient():
    got = scan("network", "something is wrong with the dmz network", B)
    assert got.span == "the dmz network"


def test_a_restrictive_with_still_holds():
    got = scan("vm", "stop every vm with over 6gb of ram", B)
    assert got.span.startswith("every vm")
