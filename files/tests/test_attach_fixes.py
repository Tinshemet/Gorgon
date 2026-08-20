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


# ── round 3: the last deterministic attach mechanisms (0a72cf4 misses) ───────────────

def test_a_leaked_probe_is_dropped_and_the_derived_one_survives():
    # G — the observe arm's cross-clause leak shadowed the rightful copy (mc-0002)
    req = "list the vms. anyway, is alpha running?"
    rows = P1.run_scanned(req, board=B)
    channel, was = _canned([("probe_alive", "alpha", None)])
    try:
        got = P2.operations_by_clause(req, rows, board=B)
        probe = [(c, o) for c, o in got if o.operator == "probe_alive" and o.on == "alpha"]
        assert probe and "running" in probe[0][0]      # attributed to the QUESTION clause
    finally:
        channel.constrained = was


def test_a_coordinated_creator_is_derived():
    # J — "create a network called lab AND A VM NAMED WEB": the verb governs both
    req = "create a network called lab and a vm named web"
    rows = P1.run_scanned(req, board=B)
    channel, was = _canned([("create_network", "lab", None)])
    try:
        got = [(o.operator, o.on) for _, o in P2.operations_by_clause(req, rows, board=B)]
        assert ("create_vm", "web") in got
    finally:
        channel.constrained = was


def test_the_mended_clause_is_asked():
    # K — the marker clause was skipped wholesale; the REPAIRED text is askable
    req = "restart the web vm, no wait, the db one"
    rows = P1.run_scanned(req, board=B)
    table = P2.symbol_table(rows, B)
    h = table[0].handle
    channel, was = _canned([("stop_vm", h, None), ("launch_vm", h, None)])
    try:
        got = [o.operator for _, o in P2.operations_by_clause(req, rows, board=B)]
        assert "stop_vm" in got and "launch_vm" in got
    finally:
        channel.constrained = was


def test_a_licensed_verb_with_no_op_derives_its_own():
    # Q — "launch the blue ones" answered with nothing: verb licence + the one
    #     visible row produce the op
    req = "label the red vms 'ready' and launch the blue ones"
    rows = P1.run_scanned(req, board=B)
    channel, was = _canned([("add_label", "red_vms", "ready")])
    try:
        got = [(o.operator, o.on) for _, o in P2.operations_by_clause(req, rows, board=B)]
        assert any(op == "launch_vm" for op, _ in got)
    finally:
        channel.constrained = was


def test_the_clone_from_role_is_repaired():
    # R — clone_vm(template): the manifest's `from` role says the SOURCE sits in the
    #     value; the created thing takes `on`
    req = "clone the golden image into three vms and label them test"
    rows = P1.run_scanned(req, board=B)
    table = P2.symbol_table(rows, B)
    tmpl = next((x.handle for x in table if x.row.kind == "template"), None)
    vms = next((x.handle for x in table if str(x.row.kind or "").startswith("vm")), None)
    assert tmpl and vms
    channel, was = _canned([("clone_vm", tmpl, None)])
    try:
        got = [(o.operator, o.on, o.value) for _, o in
               P2.operations_by_clause(req, rows, board=B) if o.operator == "clone_vm"]
        assert got == [("clone_vm", vms, tmpl)]
    finally:
        channel.constrained = was


def test_a_probe_on_the_spared_thing_is_refused_too():
    rows = P1.run_scanned("stop every vm except the db vm", board=B)
    table = P2.symbol_table(rows, B)
    spared = next((x.handle for x in table if "db" in str(x.row.span)
                   and not x.row.excludes), None)
    kept = next((x.handle for x in table if x.row.excludes), None)
    channel, was = _canned([("stop_vm", kept, None), ("probe_exists", spared, None)])
    try:
        got = [(o.operator, o.on) for _, o in P2.operations_by_clause(
            "stop every vm except the db vm", rows, board=B)]
        assert ("probe_exists", spared) not in got
        assert ("stop_vm", kept) in got
    finally:
        channel.constrained = was
