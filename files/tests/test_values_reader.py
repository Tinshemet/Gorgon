"""ATTRIBUTES ARE LEAVES — step 2: the reader (operator ruling 08-23).

An assigned value is ITS OWN SPAN; READ never interprets it; owners are ranked by context +
fit and a tie is a conflict carried to ROUTE with its hint. Model-free throughout: pass 1 is
code, and the four units cases are the test case the operator named.
"""
from planner.formula.legal import Board
from orchestrator.languages.english.seam import archive as A, front_door as FD, pass1 as P1
from orchestrator.languages.english.seam import pass2 as P2, schema as S, values as V

B = Board()


def _rows(s):
    return P1.run_scanned(FD.read(s).text, board=B)


def _shape(rows):
    return [(r.span, r.kind, (r.value or {}).get("attribute")) for r in rows]


def test_un_0001_give_the_db_vm_16gb_of_memory():
    assert _shape(_rows("give the db vm 16gb of memory")) == [
        ("the db vm", "vm", None), ("16gb", "value", "memory_mb")]


def test_un_0002_create_a_vm_with_4_cores_and_8gb_of_ram():
    assert _shape(_rows("create a vm with 4 cores and 8gb of ram")) == [
        ("a vm", "vm", None), ("4 cores", "value", "cpu_cores"), ("8gb", "value", "memory_mb")]


def test_un_0003_set_the_cpu_of_the_web_vm_to_4_cores():
    assert _shape(_rows("set the cpu of the web vm to 4 cores")) == [
        ("the web vm", "vm", None), ("4 cores", "value", "cpu_cores")]


def test_the_handover_sentence_give_alpha_4_cores_and_8gb():
    got = _shape(_rows("give alpha 4 cores and 8gb"))
    assert got[1:] == [("4 cores", "value", "cpu_cores"), ("8gb", "value", "memory_mb")]
    assert got[0][0] == "alpha"


def test_read_never_interprets_the_value():
    row = next(r for r in _rows("give the db vm 16gb of memory") if r.kind == "value")
    assert row.span == "16gb" and row.value["owner"] == "vm"
    assert "16384" not in str(row) and "mb" not in row.span


def test_a_selector_value_stays_in_its_phrase():
    # inside an EXISTING phrase behind a selector preposition — where's and magnitudes_in's
    rows = _rows("stop every vm with over 6gb of ram")
    assert not any(r.kind == "value" for r in rows)
    assert rows[0].span.startswith("every vm with over 6gb")


def test_a_value_is_never_a_handle():
    rows = _rows("create a vm with 4 cores and 8gb of ram")
    handles = [sym.handle for sym in P2.symbol_table(rows, B)]
    assert len(handles) == 1 and "cores" not in " ".join(handles) and "gb" not in " ".join(handles)


def test_idempotent_and_inert_without_a_learned_word():
    rows = _rows("stop the web vm and launch the db vm")
    assert not any(r.kind == "value" for r in rows)
    again = V.read_values(_rows("give the db vm 16gb of memory"), "give the db vm 16gb of memory", B)
    assert sum(1 for r in again if r.kind == "value") == 1


def _two_owner_archive(tmp_path):
    arc = A.Archive(str(tmp_path / "a.json"))
    arc.propose("gb", "a gigabyte", type="unit", owners=("network",), attribute="bandwidth")
    arc.ratify("gb")
    return arc


def test_a_tie_is_a_conflict_carried_with_its_hint(tmp_path):
    # `gb` owned by vm (manifest) AND network (told) — and nothing in context picks one
    base = [r for r in _rows("give alpha 8gb") if r.kind != "value"]
    rows = V.read_values(base, "give alpha 8gb", B, archive=_two_owner_archive(tmp_path))
    val = next(r for r in rows if r.kind == "value")
    assert val.value["attribute"] is None and val.value["conflict"] == ("network", "vm")
    assert val.value["hint"] == "'gb' creates a conflict between Network and Vm"


def test_context_breaks_the_tie(tmp_path):
    base = [r for r in _rows("give the db vm 8gb") if r.kind != "value"]
    rows = V.read_values(base, "give the db vm 8gb", B, archive=_two_owner_archive(tmp_path))
    val = next(r for r in rows if r.kind == "value")
    assert val.value["owner"] == "vm" and val.value["attribute"] == "memory_mb"


def test_fit_breaks_the_tie_when_the_attribute_word_says(tmp_path):
    base = [r for r in _rows("give alpha 8gb of ram") if r.kind != "value"]
    rows = V.read_values(base, "give alpha 8gb of ram", B, archive=_two_owner_archive(tmp_path))
    val = next(r for r in rows if r.kind == "value")
    assert val.value["owner"] == "vm" and val.value["attribute"] == "memory_mb"


def test_a_child_inherits_its_parents_ownership(tmp_path):
    # "entry: RAM, type unit, owners: computer (and its children)" — vm is a computer
    arc = A.Archive(str(tmp_path / "a.json"))
    arc.propose("gigs", "gigabytes", type="unit", owners=("computer",), attribute="memory_mb")
    arc.ratify("gigs")
    arc.propose("vm", "a machine", classes=("computer",))
    arc.ratify("vm")
    base = [r for r in _rows("give the db vm 8 gigs") if r.kind != "value"]
    rows = V.read_values(base, "give the db vm 8 gigs", B, archive=arc)
    scores = V.rank_owners(V._candidates("give the db vm 8 gigs", B, arc)[0], base,
                           "give the db vm 8 gigs", arc)
    assert scores["computer"] == 2, "context through inheritance + fit"


def test_pw_0004_a_value_lifted_out_of_a_phrase_leaves_the_thing_behind():
    # `db 8gb` was one kindless row; the value leaves, `db` stays (it was consumed, 08-23)
    got = _shape(_rows("give web 4 cores and db 8gb"))
    assert [g[0] for g in got] == ["web", "db", "4 cores", "8gb"]


def test_mg_0002_a_magnitude_selector_is_not_lifted():
    # the phrase swallowed the NUMBER and not the unit; the value starts inside it behind
    # `with` — a selector, magnitudes_in's to read, not ours to lift
    rows = _rows("list the vms with more than 2 cores")
    assert not any(r.kind == "value" for r in rows)


# ── step 3: the owner scrutinises, the target takes or refuses, the gate tells ──────────
def test_the_owner_scrutinises_from_the_declaration_alone():
    assert B.accept("vm", "memory_mb", "16gb") == (16384, None)
    assert B.accept("vm", "memory_mb", "8 gigs") == (8192, None)
    assert B.accept("vm", "memory_mb", "512mb") == (512, None)
    assert B.accept("vm", "cpu_cores", "4 cores") == (4, None)
    assert B.accept("vm", "ip", "10.0.0.5") == ("10.0.0.5", None)
    assert B.accept("vm", "label", "prod") == ("prod", None)          # no class: open text
    v, why = B.accept("vm", "memory_mb", "2 potatoes")
    assert v is None and "potatoes" in why and "mb" in why
    v, why = B.accept("vm", "ip", "10.0.0")
    assert v is None and "well-formed" in why


def test_a_new_target_takes_the_accepted_values_for_its_creator():
    rows = _rows("create a vm with 4 cores and 8gb of ram")
    vm = rows[0]
    assert vm.where == {"cpu_cores": 4, "memory_mb": 8192} and set(vm.assigned) == {"cpu_cores", "memory_mb"}
    vals = {r.span: r.value for r in rows if r.kind == "value"}
    assert vals["4 cores"]["target"] == "a vm" and vals["4 cores"]["accepted"] == 4
    assert vals["8gb"]["target"] == "a vm" and vals["8gb"]["accepted"] == 8192, "after `and`, its own clause"


def test_a_reference_finds_its_target():
    # `it` is read as a vm row of its own (the 08-16 clause rule); the value targets THAT
    # row and the owner's typed 4 lands in its `where` — no longer the raw string '4'
    rows = _rows("create a vm named alpha. give it 4 cores.")
    val = next(r for r in rows if r.kind == "value")
    target = next(r for r in rows if r.span == val.value["target"])
    assert target.kind == "vm" and target.where.get("cpu_cores") == 4 and "cpu_cores" in target.assigned


def test_an_existing_target_without_a_setter_refuses_with_the_owners_reason():
    for s, attr in [("give the db vm 16gb of memory", "memory_mb"),
                    ("set the cpu of the web vm to 4 cores", "cpu_cores")]:
        val = next(r for r in _rows(s) if r.kind == "value")
        assert attr in val.value["refused"] and "existing vm" in val.value["refused"]
        assert "accepted" not in val.value


def test_the_value_span_is_never_replaced_by_the_number():
    val = next(r for r in _rows("create a vm with 8gb of ram") if r.kind == "value")
    assert val.span == "8gb" and val.value["accepted"] == 8192


def test_an_assigned_key_names_no_handle():
    rows = _rows("create a vm with 4 cores and 8gb of ram")
    assert [s.handle for s in P2.symbol_table(rows, B)] == ["vm"], "not `4_vms`"


def _piped(s):
    import engines.channel as channel
    from orchestrator.languages.english.seam import pipeline as PL
    was = channel.constrained
    channel.constrained = lambda *a, **k: {}
    try:
        return PL.run(s, board=B)
    finally:
        channel.constrained = was


def test_the_refusal_reaches_the_operator_and_not_the_model():
    r = _piped("give the db vm 16gb of memory")
    assert any("cannot set memory_mb on an existing vm" in a for a in r.asks)
    assert r.outcome == "ASK" and r.bounces == [], r.bounces
    assert not any("'value'" in a for a in r.asks), "a value is not a kind the lab lacks"
    assert not any("16gb" in a and "name" in a for a in r.asks), "16gb is read, not residue"


def test_the_owners_number_is_not_an_invented_value():
    r = _piped("create a vm with 4 cores and 8gb of ram")
    assert not any("8192" in a or "never says" in a for a in r.asks + r.bounces)
