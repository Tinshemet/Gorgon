"""ATTACH — the precision column's deterministic fixes (2026-08-20, measured misses).

A · an object PRONOUN licenses visibility — `launch it` refers by grammar; the
    cross-clause leak filter was eating the reading (ana-0001, ba-0004, coord-0004).
B · AN EXCEPTION IS SPARED, STRUCTURALLY — a mutating op on the carved-out thing
    executes the exact harm the request forbade (neg-0001: the model stopped the
    spared machine). Refused at birth, whatever the model says.
D · TYPED ROLE REPAIR — the manifest declares a setter's owner and referenced kinds;
    a double-reversed answer is mended by the types (ba-0003), never scored as a miss.
"""
from planner.formula.legal import Board

from orchestrator.seam import pass1 as P1, pass2 as P2
from tests.test_twopass_schema import _canned

B = Board()


def test_a_pronoun_clause_keeps_its_operation():
    rows = P1.run_scanned("create a vm named alpha and launch it", board=B)
    channel, was = _canned([("create_vm", "alpha", None), ("launch_vm", "alpha", None)])
    try:
        got = [op.operator for _, op in P2.operations_by_clause(
            "create a vm named alpha and launch it", rows, board=B)]
        assert "launch_vm" in got          # `launch it` — visible through the pronoun
    finally:
        channel.constrained = was


def test_the_spared_target_is_refused():
    rows = P1.run_scanned("stop every vm except the db vm", board=B)
    table = P2.symbol_table(rows, B)
    spared = next((s.handle for s in table if "db" in str(s.row.span)
                   and not s.row.excludes), None)
    kept = next((s.handle for s in table if s.row.excludes), None)
    assert spared and kept
    channel, was = _canned([("stop_vm", spared, None), ("stop_vm", kept, None)])
    try:
        got = [(op.operator, op.on) for _, op in P2.operations_by_clause(
            "stop every vm except the db vm", rows, board=B)]
        assert ("stop_vm", spared) not in got     # the exception is spared
        assert ("stop_vm", kept) in got           # the set is still acted on
    finally:
        channel.constrained = was


def test_the_reversed_setter_is_mended_by_its_types():
    req = "put on the lab network every vm carrying the prod label"
    rows = P1.run_scanned(req, board=B)
    table = P2.symbol_table(rows, B)
    net = next((s.handle for s in table if s.row.kind == "network"), None)
    vms = next((s.handle for s in table if s.row.kind in ("vm", "vm_set")), None)
    assert net and vms
    channel, was = _canned([("add_vm_to_network", net, vms)])   # reversed, as measured
    try:
        got = [(op.on, op.value) for _, op in P2.operations_by_clause(req, rows, board=B)
               if op.operator == "add_vm_to_network"]
        assert got == [(vms, net)]                # mended: owner in on, ref in value
    finally:
        channel.constrained = was


def test_a_question_computes_its_probe():
    # E — no model probe came back; the asked value names its fact, the row is visible
    rows = P1.run_scanned("is alpha running?", board=B)
    channel, was = _canned([])
    try:
        got = [(op.operator, op.on) for _, op in P2.operations_by_clause(
            "is alpha running?", rows, board=B)]
        assert any(o.startswith("probe_") and h == "alpha" for o, h in got)
    finally:
        channel.constrained = was
