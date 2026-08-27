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


def test_a_macro_alias_expands_to_multiple_gated_ops():
    # macros come free from Option B: a multi-step expansion re-reads into >1 gated op, and is
    # still byte-identical to typing the steps out, so each step faces the authority gate.
    from orchestrator.languages.english.seam import pipeline
    V.ALIASES.propose("cleanup", "stop alpha and stop beta"); V.ALIASES.ratify("cleanup")
    try:
        masked = pipeline.run("cleanup")
        plain = pipeline.run("stop alpha and stop beta")
        check("a macro mask == the plain multi-step request", masked == plain)
        check("... and it produced two operations", len(masked.operations) == 2)
    finally:
        V.ALIASES.retract("cleanup")


def test_procedure_alias_declaration_and_skip():
    # `define X as the <name> procedure` binds a PROCEDURE, not an operation phrase.
    got = V.aliases_from("define contain as the quarantine procedure")
    check("reads a procedure-target mask", got and got[0]["target"] == "procedure")
    check("the target is the procedure name", got and got[0]["operation"] == "quarantine")
    check("a plain phrase stays an operation target",
          V.aliases_from("define relab as reset the lab")[0]["target"] == "operation")
    s = V.AliasStore()
    s.propose("contain", "quarantine", target="procedure"); s.ratify("contain")
    check("a procedure mask is NOT surface-substituted (seam leaves it alone)",
          _expand_with(s, "contain it") == "contain it")


def _expand_with(store, text):
    import orchestrator.languages.english.seam.verb_alias as m
    saved = m.ALIASES
    try:
        m.ALIASES = store
        return m.expand_aliases(text)[0]
    finally:
        m.ALIASES = saved


def test_procedure_for_only_returns_procedure_masks():
    s = V.AliasStore()
    s.propose("contain", "quarantine", target="procedure"); s.ratify("contain")
    s.propose("relab", "reset the lab", target="operation"); s.ratify("relab")
    import orchestrator.languages.english.seam.verb_alias as m
    saved = m.ALIASES
    try:
        m.ALIASES = s
        check("procedure_for returns the name for a procedure mask", m.procedure_for("contain") == "quarantine")
        check("procedure_for returns None for an operation mask", m.procedure_for("relab") is None)
        check("procedure_for returns None for an unknown word", m.procedure_for("nope") is None)
    finally:
        m.ALIASES = saved


def test_procedure_mask_runs_through_the_gated_runner():
    # the bridge: a procedure-mask word reaches Procedures._run_one with the resolved name.
    import orchestrator.languages.english.seam.verb_alias as m
    from orchestrator.ai.chat.shortcuts.procedures import Procedures
    from orchestrator.ai.chat.shortcuts.mask_run import MaskRun
    s = V.AliasStore(); s.propose("contain", "quarantine", target="procedure"); s.ratify("contain")
    saved, orig = m.ALIASES, Procedures._run_one
    calls = []
    try:
        m.ALIASES = s
        Procedures._run_one = staticmethod(lambda lib, name, given, verbose: calls.append((name, given)))
        mr = MaskRun()
        check("matches a ratified procedure mask", mr.matches("contain") is True)
        mr.run("contain os=linux", [], 0, False)
        check("run() invokes the runner with the resolved procedure name", calls and calls[0][0] == "quarantine")
        check("... and passes k=v params through", calls and calls[0][1] == ["os=linux"])
    finally:
        m.ALIASES, Procedures._run_one = saved, orig


if __name__ == "__main__":
    for fn in [test_nothing_routes_until_a_person_says_so, test_patient_binding_is_recorded,
               test_imported_never_routes, test_supersession_keeps_the_old_row,
               test_retract_withdraws_routing,
               test_declaration_reader_extracts_the_mask, test_as_complement_is_required,
               test_cannot_mask_a_lab_verb, test_file_all_proposes_pending_then_ratify_routes,
               test_expand_is_inert_until_ratified, test_mask_expands_in_verb_position_only,
               test_running_a_mask_is_byte_identical_to_the_plain_operation,
               test_persistence_round_trips,
               test_a_macro_alias_expands_to_multiple_gated_ops,
               test_procedure_alias_declaration_and_skip, test_procedure_for_only_returns_procedure_masks,
               test_procedure_mask_runs_through_the_gated_runner]:
        print(fn.__name__)
        fn()
    print(f"\n{_PASS} passed · {_FAIL} failed")
    sys.exit(1 if _FAIL else 0)
