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
