"""test_harvest_and_repair.py — THE TWO PIECES THAT REWRITE AN AUTHOR'S PROGRAM.

Both were written 2026-08-13 and both change what the harness runs on the operator's behalf, so
both need pinning directly rather than through the chain. `harvest` in particular had **three
bugs in one afternoon**, every one of them invisible without a model, because it lived as an
inline block inside `pipeline.run`.

    harvest   merge two rounds of a model answer   UPGRADE a step · REFUSE a new one · never DROP
    repair    fix what the manifest determines     UNIQUE answer only, or decline

⇒ EACH CASE BELOW IS A DEFECT THAT REACHED THE SUITE, not an invented scenario. The names say
  which, so a future failure points at the day's finding rather than at an abstraction.
"""
from planner.formula.legal import Board
from orchestrator.seam import gate3, pass1, pass2, repair as R
from orchestrator.seam.effects import Operation
from tests.bench.twopass.metrics import Lab
from orchestrator.seam.pipeline import harvest

_FAIL = 0


def check(label, ok):
    global _FAIL
    if not ok:
        _FAIL += 1
    print(f"    {'ok  ' if ok else 'FAIL'}  {label}")


def _op(operator, on, value=None):
    return Operation(operator=operator, on=on, value=value)


def _bad(step, rule="wrong-kind-operator"):
    return gate3.Illegal(step, rule, "…")


def _sig(ops):
    return [(o.operator, o.on, o.value) for o in ops]


# ── harvest ───────────────────────────────────────────────────────────────────────────────

def test_a_clean_retry_step_supersedes_its_faulty_counterpart():
    """Rung 12. The retry repaired the step we objected to; keep the repair."""
    print("\n[harvest] the retry's fix survives the junk that arrived with it")
    first = [_op("create_snapshot", "snapshot")]
    again = [_op("create_snapshot", "running_vms"), _op("add_label", "snapshot", "prose")]
    got = harvest(first, [_bad(first[0])], again, [_bad(again[1])])
    check("the repaired step replaces the faulty one",
          ("create_snapshot", "running_vms", None) in _sig(got))
    check("and the invented step is refused",
          ("add_label", "snapshot", "prose") not in _sig(got))


def test_two_steps_sharing_an_operator_are_two_steps():
    """Rung 8. `create_network(core)` and `create_network(dmz)` are not one step.

    Keying slots by OPERATOR ALONE collapsed these into one, dropped an establisher, and the
    rung refused for want of a network the retry had actually supplied.
    """
    print("\n[harvest] a second step of the same operator is not a duplicate")
    first = [_op("add_vm_to_network", "vms", "core"), _op("add_vm_to_network", "db", "dmz")]
    again = first + [_op("create_network", "core"), _op("create_network", "dmz")]
    got = harvest(first, [_bad(o) for o in first], again, [])
    check("both establishers survive",
          ("create_network", "core", None) in _sig(got)
          and ("create_network", "dmz", None) in _sig(got))
    check("and nothing is lost from the first round", len(got) == 4)


def test_harvest_never_empties_the_program():
    """The trap: an empty program has ZERO faults, so dropping everything always 'improves'.

    Caught by the destruction guard — `delete_network` was dropped as faulty and took its own
    confirmation with it, because a finding is computed from the operations. **A dropped step
    takes its report with it**, which is why dropping is never a repair.
    """
    print("\n[harvest] a faulty step stands rather than vanishing")
    first = [_op("delete_network", "dmz")]
    got = harvest(first, [_bad(first[0], "unestablished-referent")], [], [])
    check("the destructive step is still there to be confirmed",
          _sig(got) == [("delete_network", "dmz", None)])
    # and with a retry that offers nothing better.
    # ⇒ THE FINDING MUST REFERENCE THE SAME OBJECT AS THE STEP — `harvest` pairs them by
    #   identity, exactly as `gate3.check` returns them. Building the operation twice here made
    #   the junk look CLEAN and it was taken; that was this test's own bug, caught on its first
    #   run, and it is worth keeping visible because any caller reconstructing findings would
    #   hit the same thing silently.
    junk = _op("launch_vm", "x")
    got2 = harvest(first, [_bad(first[0])], [junk], [_bad(junk)])
    check("a retry of pure junk changes nothing",
          _sig(got2) == [("delete_network", "dmz", None)])


def test_a_new_clean_step_joins_and_a_new_faulty_one_does_not():
    print("\n[harvest] what the retry adds is judged before it is taken")
    first = [_op("create_vm", "alpha")]
    again = [_op("create_vm", "alpha"), _op("launch_vm", "alpha"), _op("delete_vm", "beta")]
    got = harvest(first, [], again, [_bad(again[2])])
    check("the clean addition joins", ("launch_vm", "alpha", None) in _sig(got))
    check("the faulty addition does not", ("delete_vm", "beta", None) not in _sig(got))


# ── repair ────────────────────────────────────────────────────────────────────────────────

def _table(rung):
    board = Board()
    rows = pass1.settle_with_world(pass1.run_scanned(pass1.EXPECTED[rung].request, board=board),
                                   Lab(), board)
    return board, pass2.symbol_table(rows, board)


def test_repair_aims_a_creator_from_the_manifest_and_says_so():
    """Rung 12, with NO model call. The manifest names exactly one legal source."""
    print("\n[repair] the fix is a manifest lookup, not a question")
    board, table = _table(12)
    ops = [_op("create_snapshot", "snapshot")]
    findings = gate3.check(ops, table, board, Lab())
    fixed, notes = R.repair(ops, findings, table, board)
    check("the creator is re-aimed", fixed[0].on != "snapshot")
    check("and the change is reported, never silent", len(notes) == 1)
    check("the reason names the manifest", "manifest" in notes[0].why)


def test_repair_declines_rather_than_guessing():
    """Two candidates is not a fix. It is a guess with better odds."""
    print("\n[repair] ambiguity is declined, and the finding survives for the model")
    board, table = _table(12)
    ops = [_op("create_snapshot", "snapshot")]
    findings = gate3.check(ops, table, board, Lab())
    # a second declaration of the source kind makes the target ambiguous
    source_kind = gate3._creation_sources(gate3._made_kind("create_snapshot", board), board)
    twin = [s for s in table if s.row.kind in source_kind]
    check("the fixture is only meaningful if the manifest constrains this creator",
          bool(source_kind) and bool(twin))
    fixed, notes = R.repair(ops, findings, list(table) + list(twin), board)
    check("nothing is changed when the answer is not unique", _sig(fixed) == _sig(ops))
    check("and nothing is claimed", notes == [])


def test_repair_only_touches_rules_it_declares():
    """`OWNS` is the contract: a rule not listed reaches the model untouched."""
    print("\n[repair] a repair nobody declared cannot exist")
    board, table = _table(12)
    ops = [_op("create_snapshot", "snapshot")]
    outside = [gate3.Illegal(ops[0], "value-missing", "…")]
    fixed, notes = R.repair(ops, outside, table, board)
    check("an undeclared rule is left alone", _sig(fixed) == _sig(ops) and notes == [])
    check("and OWNS is a subset of what gate 3 actually raises",
          R.OWNS <= gate3.OWNS)




# ── the red line ──────────────────────────────────────────────────────────────────────────

def test_a_banned_tool_refuses_the_whole_program():
    """THE BARRIER THE TREE HAS AND THE FRONT SEAM DID NOT, until 2026-08-13.

    Found by the operator: *"I do remember the tree having a legal barrier, we don't have it
    here."* The red line was enforced in `engine_core` (per leaf), `consent.forbidden` (whole
    program) and `executor._red_line` (the boundary) — and NOT in the seam that issues the
    verdict. So a banned request came back SERVE and was stopped later, at execution.

    ⇒ **BANNED REFUSES, GUARDED RUNS** — the operator's ruling, restating 2026-08-02. A guarded
      tool is a confirmation and confirmations already live in gate 4; this answers the ban.
    """
    print("\n[redline] a program that names a banned tool may not run at all")
    from orchestrator.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    from orchestrator.seam.gate4 import forbidden_tools

    ops = [_op("create_vm", "alpha"), _op("delete_vm", "alpha")]
    check("with no contract, nothing is forbidden — the degraded arm",
          forbidden_tools(ops, None) == [])
    check("a banned tool is named", forbidden_tools(ops, lambda t: t == "delete_vm")
          == ["delete_vm"])
    check("and a tool nobody banned is not",
          forbidden_tools(ops, lambda t: t == "format_disk") == [])


def test_the_red_line_check_cannot_fail_silently():
    """A SAFETY CHECK THAT QUIETLY RETURNS [] IS WORSE THAN NO CHECK.

    `forbidden_tools` delegates to `consent.forbidden`, which walks an IR PROGRAM — and this
    seam holds `Operation` tuples, not IR. The translation is the one place this can rot: get
    the shape wrong and `tools_named` finds no tools, the ban finds nothing, and every request
    passes. **That failure is invisible from the outside**, which is exactly why it is asserted
    here rather than trusted.
    """
    print("\n[redline] the Operation -> IR translation actually reaches tools_named")
    from planner.ir import consent as _consent
    ops = [_op("create_vm", "alpha"), _op("add_vm_to_network", "alpha", "core")]
    body = [{"op": "call", "tool": o.operator, "args": {}} for o in ops]
    seen = _consent.tools_named({"body": body})
    check(f"every operator is visible to tools_named ({seen})",
          set(seen) == {"create_vm", "add_vm_to_network"})


def test_a_banned_program_refuses_end_to_end():
    print("\n[redline] and the chain returns REFUSE rather than SERVE")
    from orchestrator.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    import tests.test_twopass_schema as T
    channel, was = T._canned([("create_vm", "alpha", None)])
    try:
        served = PL.run("create a vm named alpha", board=Board(), world=Lab())
        banned = PL.run("create a vm named alpha", board=Board(), world=Lab(),
                        legal=lambda t: t == "create_vm")
        check(f"unbanned it serves ({served.outcome})", served.outcome == PL.SERVE)
        check(f"banned it REFUSES ({banned.outcome})", banned.outcome == PL.REFUSE)
        check("and says which tool, so the operator knows why",
              any("create_vm" in a and "forbids" in a for a in banned.asks))
    finally:
        channel.constrained = was


def test_the_seam_consults_the_contract_without_being_asked():
    """THE GUARD AGAINST THE DEFECT THIS BARRIER WAS BORN WITH.

    Built 2026-08-13 as an injected parameter defaulting to `None` — which is exactly the shape
    filed as I9 that same morning: **plumbed end to end and never fed.** A red line nobody
    supplies is not a red line, and the live contract currently forbids none of the seventeen
    operators this seam can name, so THE RUNGS CANNOT TELL THE DIFFERENCE between wired and
    unwired. Nothing else would notice if the default resolution were dropped.

    ⇒ SO THIS FORBIDS SOMETHING AT THE CONTRACT and calls `run()` WITHOUT a `legal` argument.
      It fails the moment the seam stops asking the contract on its own.
    """
    print("\n[redline] the barrier is fed by default, not only when a caller remembers")
    from orchestrator.seam import pipeline as PL
    from tests.bench.twopass.metrics import Lab
    import tests.test_twopass_schema as T

    real = PL._the_red_line
    channel, was = T._canned([("create_vm", "alpha", None)])
    try:
        # stand in for a contract that bans create_vm, resolved the way `None` resolves
        PL._the_red_line = lambda legal: legal if callable(legal) else (lambda t: t == "create_vm")
        got = PL.run("create a vm named alpha", board=Board(), world=Lab())   # no `legal=`
        check(f"a banned tool refuses even with no legal argument ({got.outcome})",
              got.outcome == PL.REFUSE)
    finally:
        PL._the_red_line = real
        channel.constrained = was

    check("and the real resolution reaches the contract's own is_forbidden",
          getattr(PL._the_red_line(None), "__name__", "") == "is_forbidden")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{_FAIL} failed")
