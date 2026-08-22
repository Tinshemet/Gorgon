"""TESTIMONY — the structural malfunction reader (D1's front door), now with D1 proper.

Anchors first (the 08-18 rules, previously controlled only by the eval), then the two
shapes the operator ordered built on 08-19 ("for the diagnosis, add that ability"):

  R1 ELABORATION SPREAD — once a request carries a malfunction statement, the following
     plain declarative clause is the symptom's elaboration: *"vm2 is not working, IT
     BOOTS TO A BLUE SCREEN"*. Position + shape (not imperative, not question, not
     condition), never vocabulary.
  R2 THE INDEFINITE FRAME — {something, anything, nothing} + copula IS the malfunction
     marker: *"SOMETHING IS WRONG with the dmz network"*. The predicate is the head;
     the with-phrase stays the patient's.
"""
from orchestrator.languages.english.seam import testimony as T


# ── anchors: the 08-18 rules still hold ──────────────────────────────────────────────

def test_a_negated_modal_is_testimony():
    got = T._of_clause("the web vm won't start")
    assert got and got.predicate == "won't start"


def test_a_negated_copula_with_gerund_is_testimony():
    assert T.is_testimony("vm2 is not working")


def test_a_relative_filter_is_not_testimony():
    assert not T.is_testimony("the vms which stopped")


def test_an_imperative_is_not_testimony():
    assert not T.is_testimony("stop the web vm")


# ── R2: the indefinite frame ─────────────────────────────────────────────────────────

def test_something_is_wrong_is_testimony():
    got = T._of_clause("something is wrong with the dmz network")
    assert got and got.predicate == "something is wrong"
    assert "dmz network" in got.subject


def test_nothing_plus_copula_is_testimony():
    assert T.is_testimony("nothing is responding")


def test_something_without_copula_is_not():
    assert not T.is_testimony("something like the db vm")


# ── R1: elaboration spread ───────────────────────────────────────────────────────────

def test_the_clause_after_testimony_elaborates():
    got = T.read("vm2 is not working, it boots to a blue screen")
    assert len(got) == 2
    assert got[1].clause == "it boots to a blue screen"


def test_the_bare_event_clause_elaborates_too():
    got = T.read("something is wrong with the dmz network, pings time out")
    assert len(got) == 2
    assert got[1].clause == "pings time out"


def test_an_imperative_after_testimony_does_not_elaborate():
    got = T.read("the web vm is not working, restart it")
    assert len(got) == 1


def test_a_question_after_testimony_does_not_elaborate():
    got = T.read("the web vm is not working, is the db vm up")
    assert len(got) == 1


def test_no_testimony_means_no_spread():
    assert T.read("stop the web vm, launch the db vm") == []


# ── predicate_end: the structural end, for the cut rules ─────────────────────────────

def test_predicate_end_negated_copula():
    c = "vm2 is not working it boots to a blue screen"
    assert c[:T.predicate_end(c)] == "vm2 is not working"


def test_predicate_end_indefinite_frame_keeps_its_patient():
    # the with-PP is the patient's and stays with its testimony (measured: cutting
    # before `with` billed the clean row)
    c = "something is wrong with the dmz network pings time out"
    assert c[:T.predicate_end(c)] == "something is wrong with the dmz network"


def test_predicate_end_iteratives_never_cut():
    # "keeps dropping OFF THE NETWORK" — the phrasal tail is inside the predicate
    assert T.predicate_end("the web vm keeps dropping off the network") is None


def test_predicate_end_none_without_testimony():
    assert T.predicate_end("stop the web vm") is None
