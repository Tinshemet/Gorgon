"""THE CLAUSE MERGE — the last big noise cell (v2 degradation runs, 2026-08-19).

Without punctuation the splitter cannot cut, so `"if alpha is stopped launch it"` stays
ONE clause — `is_condition` then withholds the whole thing from pass 2, the imperative
channel fails (the clause opens on `if`), and the second span's attachment goes with it.
No-punct owned 7 lost spans, 4 lost acts, 10 lost attachments, plus both voice residuals.

The cuts are grammar from closed classes that already exist — courtesy/wrapper literals,
the condition-head set, determiner-shape imperatives — never meaning, never a model call.
Two certified no-punct failures are DELIBERATELY out of scope here: coord-0003-nt (a
bare-name member list without commas — scan's NP reading, not a clause cut) and
sc-0004-nt (a value respeak without commas — self_repair's).
"""
from orchestrator.seam.pass2 import clauses_of


# ── the certified failures this fix must heal ────────────────────────────────────────

def test_courtesy_literal_is_cut_after():
    assert clauses_of("when you get a chance stop the test vms") == \
        ["when you get a chance", "stop the test vms"]


def test_condition_with_copula_cuts_at_the_consequent():
    assert clauses_of("if alpha is stopped launch it") == \
        ["if alpha is stopped", "launch it"]


def test_event_condition_without_copula_cuts_at_the_imperative():
    assert clauses_of("when the backup finishes snapshot the db vm") == \
        ["when the backup finishes", "snapshot the db vm"]


def test_a_wrapper_starts_its_own_clause():
    assert clauses_of("if the backup failed tell me which vms it skipped") == \
        ["if the backup failed", "tell me which vms it skipped"]


def test_mid_clause_if_cuts_both_sides():
    assert clauses_of("check the db vm's disk if it is full delete the oldest snapshot") \
        == ["check the db vm's disk", "if it is full", "delete the oldest snapshot"]


def test_mid_clause_after_cuts_and_its_consequent_follows():
    assert clauses_of("the web vm after you have checked the others restart it") == \
        ["the web vm", "after you have checked the others", "restart it"]


def test_a_second_imperative_is_its_own_clause():
    assert clauses_of("don't stop the web vm stop the db vm") == \
        ["don't stop the web vm", "stop the db vm"]


def test_anyway_releases_the_question_behind_it():
    got = clauses_of("list the vms anyway is alpha running")
    assert "is alpha running" in got
    assert got[0].startswith("list the vms")


# ── the shapes that must NOT cut ─────────────────────────────────────────────────────

def test_a_complement_clause_is_not_an_imperative():
    # `carries` is 3rd-person -s — an imperative is the base form, never -s
    assert clauses_of("make sure the db vm carries the prod label") == \
        ["make sure the db vm carries the prod label"]


def test_a_double_object_is_not_a_cut():
    assert clauses_of("give the web vm the test label") == \
        ["give the web vm the test label"]


def test_a_deontic_rule_is_not_cut_at_its_verb():
    # `must carry a label` — the modal before the verb is the guard
    assert clauses_of("every vm must carry a label") == ["every vm must carry a label"]


def test_a_prepositional_phrase_is_not_a_clause():
    assert clauses_of("put the ready label on the red vms") == \
        ["put the ready label on the red vms"]


def test_a_long_subject_does_not_fake_the_cut():
    # no cut before the subordinate's predicate has been seen
    assert clauses_of("if the web vm the operator built is stopped launch it") == \
        ["if the web vm the operator built is stopped", "launch it"]


def test_the_comma_path_is_unchanged():
    assert clauses_of("if alpha is stopped, launch it") == \
        ["if alpha is stopped", "launch it"]


def test_quotes_are_opaque_to_the_cut():
    assert clauses_of("label the vms 'stop the db'") == ["label the vms 'stop the db'"]


def test_whether_if_is_not_a_condition_cut():
    assert clauses_of("tell me if the db vm restarted") == \
        ["tell me if the db vm restarted"]


def test_the_member_list_rejoin_still_holds():
    got = clauses_of("make sure n1, n2 and n3 can all ping each other")
    assert not any(p.startswith(("ping", "all", "can")) for p in got)


# ── rule 7: the testimony predicate releases its elaboration (D1-exposed cell, 08-20) ─

def test_testimony_releases_its_elaboration():
    assert clauses_of("vm2 is not working it boots to a blue screen") == \
        ["vm2 is not working", "it boots to a blue screen"]


def test_the_indefinite_frame_releases_its_tail():
    assert clauses_of("something is wrong with the dmz network pings time out") == \
        ["something is wrong with the dmz network", "pings time out"]


def test_an_iterative_is_never_cut():
    assert clauses_of("the web vm keeps dropping off the network") == \
        ["the web vm keeps dropping off the network"]


def test_a_short_tail_is_not_an_elaboration():
    # fewer than three words after the predicate — no vote, no cut
    assert clauses_of("the web vm won't start right now") == \
        ["the web vm won't start right now"]
