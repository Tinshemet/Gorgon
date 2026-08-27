"""test_verb_alias.py — the verb-side mask store, and the one property that makes it safe.

A mask lets a learned word stand in for a lab operation (`relab` -> `reset_lab`). It is the
verb-side sibling of the noun archive, and it inherits the archive's non-negotiable pin:

    1  NOTHING ROUTES UNTIL A PERSON RATIFIES IT. A proposed alias describes and never permits
       — otherwise a sentence teaches a mask AND fires it in one breath, which is the courtesy
       defect one layer up.
    2  supersession keeps the old mask; the store audits backwards (a misspoken alias must be
       recoverable, never silently permanent).
    3  retract (UNALIAS) withdraws routing without deleting the row.

The second safety property — a mask carries no authority of its own, because it expands to a
real Operation the gate checks — lives at the CONSULT site (pipeline), not in the store, and is
pinned there when that step is built.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.languages.english.seam import verb_alias as V

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_nothing_routes_until_a_person_says_so():
    s = V.AliasStore()
    e = s.propose("relab", "reset_lab", description="reset the lab")
    check("a proposed alias is PENDING", e.status == V.PENDING)
    check("a proposed alias does NOT route", not e.routes)
    check("known() returns None before ratification", s.known("relab") is None)
    r = s.ratify("relab", who="operator")
    check("ratify promotes the pending alias", r is not None and r.status == V.RATIFIED)
    check("a ratified+told alias routes", r.routes)
    check("known() now returns the alias", s.known("relab") is not None)
    check("known() carries the operation", s.known("relab").operation == "reset_lab")


def test_patient_binding_is_recorded():
    s = V.AliasStore()
    s.propose("contain", "container_mode", binds_patient=True, description="container-mode a file")
    s.ratify("contain")
    a = s.known("contain")
    check("an alias remembers it binds a patient", a is not None and a.binds_patient is True)


def test_imported_never_routes():
    s = V.AliasStore()
    s.propose("nuke", "destroy_all", source=V.IMPORTED)
    s.ratify("nuke")
    check("an IMPORTED alias never routes even once ratified", s.known("nuke") is None)


def test_supersession_keeps_the_old_row():
    s = V.AliasStore()
    s.propose("relab", "reset_lab"); s.ratify("relab")
    s.propose("relab", "rebuild_lab"); s.ratify("relab")
    check("the newest ratified mask wins", s.known("relab").operation == "rebuild_lab")
    superseded = [e for e in s._rows if e.status == V.SUPERSEDED and e.operation == "reset_lab"]
    check("the old mask is superseded, not deleted", len(superseded) == 1)


def test_retract_withdraws_routing():
    s = V.AliasStore()
    s.propose("relab", "reset_lab"); s.ratify("relab")
    check("routes before retract", s.known("relab") is not None)
    gone = s.retract("relab")
    check("retract returns the withdrawn alias", gone is not None and gone.operation == "reset_lab")
    check("nothing routes after retract", s.known("relab") is None)
    check("the retracted row survives for audit", any(e.status == V.SUPERSEDED for e in s._rows))


def test_declaration_reader_extracts_the_mask():
    got = V.aliases_from("define relab as reset the lab")
    check("reads one mask from a define-as clause", len(got) == 1)
    check("the mask word is the token after define", got and got[0]["word"] == "relab")
    check("the expansion is the phrase after as", got and got[0]["operation"] == "reset the lab")


def test_as_complement_is_required():
    check("define WITHOUT as is not a mask", V.aliases_from("define the problem before you start") == [])
    check("an ordinary order declares no mask", V.aliases_from("restart the web vm") == [])


def test_cannot_mask_a_lab_verb():
    # `stop` is a manifest verb; you may not repaint it, even with the define frame.
    check("the mask word may not be a lab verb", V.aliases_from("define stop as reset the lab") == [])


def test_file_all_proposes_pending_then_ratify_routes():
    s = V.AliasStore()
    got = V.aliases_from("define relab as reset the lab")
    # file into a fresh store (mirror file_all against a local store)
    for a in got:
        s.propose(a["word"], a["operation"], said=a.get("said", ""))
    check("filing yields a PENDING mask that does not route", s.known("relab") is None)
    s.ratify("relab", who="operator")
    check("after the operator signs it, the mask routes", s.known("relab") is not None)
    check("and carries its expansion", s.known("relab").operation == "reset the lab")


def test_expand_is_inert_until_ratified():
    V.ALIASES.propose("zorp", "list the vms")            # pending, never signed
    check("an unratified mask does not expand", V.expand_aliases("zorp")[0] == "zorp")


def test_mask_expands_in_verb_position_only():
    V.ALIASES.propose("relab", "reset the lab"); V.ALIASES.ratify("relab")
    try:
        check("a ratified mask expands at a clause start",
              V.expand_aliases("relab now")[0] == "reset the lab now")
        check("... and after a connective",
              "reset the lab" in V.expand_aliases("stop alpha then relab")[0])
        check("but NOT in object position — there it is a name",
              V.expand_aliases("snapshot the relab vm")[0] == "snapshot the relab vm")
    finally:
        V.ALIASES.retract("relab")


def test_running_a_mask_is_byte_identical_to_the_plain_operation():
    # ⇒ THE SECURITY PROPERTY: a mask read is INDISTINGUISHABLE from the operation it stands
    #   for, so the authority gate checks the real operation and the mask smuggles nothing.
    from orchestrator.languages.english.seam import pipeline
    V.ALIASES.propose("relab", "list the vms"); V.ALIASES.ratify("relab")
    try:
        masked = pipeline.run("relab")
        plain = pipeline.run("list the vms")
        check("running a mask == running the plain operation (authority-transparent)",
              masked == plain)
    finally:
        V.ALIASES.retract("relab")


def test_persistence_round_trips():
    import os, tempfile
    fd, path = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(path)
    try:
        s = V.AliasStore(path)
        s.propose("relab", "reset the lab"); s.ratify("relab"); s.save()
        reloaded = V.AliasStore(path)
        check("a ratified mask survives save + reload", reloaded.known("relab") is not None)
        check("... and keeps its operation", reloaded.known("relab").operation == "reset the lab")
        reloaded.propose("zap", "stop everything"); reloaded.save()
        again = V.AliasStore(path)
        check("a pending mask reloads but still does not route",
              again.known("zap") is None and any(e.word == "zap" for e in again.pending()))
    finally:
        if os.path.exists(path): os.remove(path)


if __name__ == "__main__":
    for fn in [test_nothing_routes_until_a_person_says_so, test_patient_binding_is_recorded,
               test_imported_never_routes, test_supersession_keeps_the_old_row,
               test_retract_withdraws_routing,
               test_declaration_reader_extracts_the_mask, test_as_complement_is_required,
               test_cannot_mask_a_lab_verb, test_file_all_proposes_pending_then_ratify_routes,
               test_expand_is_inert_until_ratified, test_mask_expands_in_verb_position_only,
               test_running_a_mask_is_byte_identical_to_the_plain_operation,
               test_persistence_round_trips]:
        print(fn.__name__)
        fn()
    print(f"\n{_PASS} passed · {_FAIL} failed")
    sys.exit(1 if _FAIL else 0)
