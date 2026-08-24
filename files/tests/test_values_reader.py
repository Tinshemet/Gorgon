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


def test_a_selector_value_is_a_leaf_too_marked_as_selector():
    # RULED 08-23 (v2.6): a selecting value is its own span; it PICKS, it is not given
    rows = _rows("stop every vm with over 6gb of ram")
    val = next(r for r in rows if r.kind == "value")
    assert val.span == "6gb" and val.value["selector"] and "refused" not in val.value
    assert rows[0].span == "every vm"


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


def test_mg_0002_a_magnitude_selector_is_lifted_whole():
    # the phrase had swallowed the NUMBER and not the unit; the value starts inside it
    # behind `with` — a selector, lifted whole, its comparator named
    rows = _rows("list the vms with more than 2 cores")
    val = next(r for r in rows if r.kind == "value")
    assert val.span == "2 cores" and val.value["comparator"] == "more than"


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
    val = next(r for r in rows if r.kind == "value" and r.span == "4 cores")
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


# ── step 4: A NAME IS A LEAF (ledger #17) ───────────────────────────────────────────────
def _named(s):
    rows = _rows(s)
    return ([(r.span, r.kind, r.where) for r in rows if r.kind != "value"],
            [(r.span, r.value["attribute"], r.value.get("target")) for r in rows if r.kind == "value"])


def test_a_name_at_creation_is_its_own_span():
    things, values = _named("create a vm named alpha")
    assert things == [("a vm", "vm", {"name": "alpha"})]
    assert values == [("alpha", "name", "a vm")]


def test_a_network_name_uses_the_kinds_key_attribute():
    things, values = _named("create a network called lab")
    assert things == [("a network", "network", {"net_name": "lab"})]
    assert values == [("lab", "net_name", "a network")]


def test_nl_0001_a_literal_list_is_one_leaf_per_name():
    things, values = _named("create three vms named a, b and c")
    assert [t[0] for t in things] == ["three vms"]
    assert [v[0] for v in values] == ["a", "b", "c"] and all(v[1] == "name" for v in values)


def test_nl_0002_two_networks_called_front_and_back():
    things, values = _named("create two networks called front and back")
    assert [t[0] for t in things] == ["two networks"]
    assert [v[0] for v in values] == ["front", "back"]


def test_nl_0003_a_generator_spec_is_itself_the_one_leaf():
    things, values = _named("create 5 vms named 1-5")
    assert things == [("5 vms", "vm", {"name": "1-5"})], "the spec, not the old partial '1'"
    assert values == [("1-5", "name", "5 vms")]


def test_nl_0004_a_theme_generator_and_a_named_network():
    things, values = _named("create 3 vms named after musicians and a network called the stadium "
                            "and add those vms to it")
    # `those vms` is folded into `3 vms` as a reference by resolve_proforms (pre-existing)
    assert [t[0] for t in things] == ["3 vms", "a network"], things
    assert [v[0] for v in values] == ["after musicians", "the stadium"]


def test_a_name_that_refers_stays_in_its_phrase():
    things, values = _named("stop the vm named web")
    assert things == [("the vm named web", "vm", {"name": "web"})] and values == []


def test_the_list_ends_where_the_next_clause_begins():
    things, values = _named("create a vm named alpha and launch it")
    assert [v[0] for v in values] == ["alpha"]


def test_the_naming_cue_is_claimed_not_left_over():
    r = _piped("create a vm named alpha")
    assert not any("'named'" in b for b in r.bounces), r.bounces


# ── step 5: SHAPES — ip · mac · serial by the class's declared shape ─────────────────────
def _shaped(s):
    rows = _rows(s)
    return ([(r.span, r.kind, r.where) for r in rows if r.kind != "value"],
            [(r.span, r.value["attribute"], {k for k in ("accepted", "refused", "predicate") if k in r.value})
             for r in rows if r.kind == "value"])


def _sel(s):
    rows = _rows(s)
    return ([(r.span, r.kind, r.where) for r in rows if r.kind != "value"],
            [(r.span, r.value["attribute"], r.value.get("selector"), r.value.get("comparator"))
             for r in rows if r.kind == "value"])


def test_id_0001_a_selecting_ip_is_its_own_span_and_the_phrase_keeps_the_filter():
    # RULED 08-23 (schema v2.6, role selector): "wouldn't this make sense that 10.0.0.5 is
    # a different span since it's an attribute?" — one rule for every value a class owns
    things, values = _sel("stop the vm at 10.0.0.5")
    assert things == [("the vm", "vm", {"ip": "10.0.0.5"})]
    assert values == [("10.0.0.5", "ip", True, None)]


def test_id_0004_a_selecting_serial_takes_its_attribute_word_as_context():
    things, values = _sel("stop the vm with serial 7f3k-2210")
    assert things == [("the vm", "vm", {"serial": "7f3k-2210"})]
    assert values == [("7f3k-2210", "serial", True, None)]


def test_mg_0001_a_compared_selector_names_its_comparator_and_fills_no_where():
    # `where` holds one value per attribute and cannot hold a comparison (magnitudes_in's)
    things, values = _sel("stop every vm with over 6gb of ram")
    assert things == [("every vm", "vm", {})]
    assert values == [("6gb", "memory_mb", True, "over")]
    things, values = _sel("list the vms with more than 2 cores")
    assert things == [("the vms", "vm", {})] and values == [("2 cores", "cpu_cores", True, "more than")]


def test_a_duration_no_class_owns_stays_in_the_phrase():
    things, values = _sel("delete the snapshots older than a month")
    assert things == [("the snapshots older than a month", "snapshot", {})] and values == []


def test_id_0002_a_query_value_is_a_predicate_not_an_assignment():
    things, values = _shaped("which vm has mac aa:bb:cc:dd:ee:ff?")
    assert [t[0] for t in things] == ["which vm"]
    assert values == [("aa:bb:cc:dd:ee:ff", "mac", {"predicate"})]


def test_id_0003_an_assigned_ip_on_an_existing_vm_is_refused_by_the_owner():
    things, values = _shaped("give the web vm the ip 10.0.0.7")
    assert [t[0] for t in things] == ["the web vm"]
    assert values == [("10.0.0.7", "ip", {"refused"})]
    r = _piped("give the web vm the ip 10.0.0.7")
    assert any("cannot set ip on an existing vm" in a for a in r.asks) and r.outcome == "ASK"


def test_id_0005_a_token_in_the_selector_slot_is_a_value_even_unshaped():
    # RULED 08-23 (ledger #20), overturning #17b's stays-in-the-phrase clause: "8g:77q is
    # an attribute the same way an ip is, so it should be treated the same" — the slot is
    # the licence; the owner refuses what nobody declares and gate 4 asks the operator
    things, values = _shaped("stop the vm at 8g:77q")
    assert things == [("the vm", "vm", {})]
    assert values == [("8g:77q", None, {"refused"})]


def test_a_shaped_value_at_creation_is_taken_by_the_creator():
    things, values = _shaped("create a vm named alpha with ip 10.0.0.9")
    assert things == [("a vm", "vm", {"name": "alpha", "ip": "10.0.0.9"})]
    assert ("10.0.0.9", "ip", {"accepted"}) in values


def test_the_attribute_word_before_a_shape_is_claimed():
    r = _piped("which vm has mac aa:bb:cc:dd:ee:ff?")
    assert not any("'mac'" in b for b in r.bounces), r.bounces


def test_an_identifier_is_never_made_of_english():
    # `read-only` fits the serial shape xxxx-xxxx and is two English words (cc-0007)
    things, values = _shaped("treat prod as read-only")
    assert values == []


# ── rule 8 · POSSESS — `X's snapshot`: the leaf is its own span, X its owner (ledger #19) ────

def _genitive(s):
    rows = _rows(s)
    return ([(r.span, r.kind) for r in rows if r.kind != "value"],
            [(r.span, r.value["attribute"], r.value.get("owner"), r.value.get("target"),
              {k for k in ("accepted", "refused") if k in r.value}) for r in rows if r.kind == "value"])


def test_po_0001_delete_alphas_snapshots_is_owner_plus_leaf():
    # the operator, 08-23: "'X's snapshot' — snapshot here should be a value as a span";
    # "patient for the owner". `snapshots` fits vm because `snapshot.attrs` names `vm`.
    things, values = _genitive("delete alpha's snapshots")
    assert things == [("alpha", "?")]
    assert values == [("snapshots", "snapshot", "vm", "alpha", {"accepted"})]


def test_po_0002_the_owner_phrase_keeps_its_own_kind():
    things, values = _genitive("list the web vm's snapshots")
    assert things == [("the web vm", "vm")]
    assert values[0][:2] == ("snapshots", "snapshot") and values[0][3] == "the web vm"


def test_the_clitic_belongs_to_neither_span():
    s = "delete alpha's snapshots"
    rows = _rows(s)
    spans = [str(r.span) for r in rows]
    assert spans == ["alpha", "snapshots"]
    assert s[7:12] == "alpha" and s[15:24] == "snapshots"      # the gold's offsets (v3 po-0001)


def test_a_declared_attribute_behind_the_clitic_resolves_to_its_canonical_name():
    things, values = _genitive("alpha's ram")
    assert things == [("alpha", "?")]
    assert values[0][:3] == ("ram", "memory_mb", "vm")


def test_po_0003_an_undeclared_leaf_is_spanned_and_refused_by_the_owner():
    # `disk` is declared nowhere — the slot still spans it (UNKNOWN is never filtered) and
    # the owner refuses it, which gate 4 tells the operator: teach the word
    things, values = _genitive("check beta's disk")
    assert [t[0] for t in things] == ["beta"]
    assert values[0][0] == "disk" and values[0][1] is None and "refused" in values[0][4]
    refused = [r.value["refused"] for r in _rows("check beta's disk") if r.kind == "value"][0]
    assert "'disk'" in refused and "beta" in refused


def test_a_plural_clitic_makes_the_owner_a_set():
    things, values = _genitive("the vms' labels")
    assert things == [("the vms", "vm")] and values[0][:2] == ("labels", "label")
    assert [r.is_set for r in _rows("the vms' labels") if r.kind != "value"] == [True]


def test_the_copula_contraction_is_not_a_possessive():
    # `running` is a declared VALUE of status — `alpha's running` says alpha IS running
    assert not any(r.kind == "value" for r in _rows("alpha's running"))


def test_the_codex_contractions_are_never_split():
    for s in ("let's stop alpha", "it's down", "that's the db vm"):
        assert not any((r.value or {}).get("genitive") for r in _rows(s)), s


def test_the_verb_governs_the_leaf_not_its_owner():
    # pass 2's one address is the owner; `delete_vm(alpha)` for `delete alpha's snapshots`
    # is a destructive step on the wrong thing and is dropped — the lab's limit is then
    # gate 4's line to the operator, never a silent empty program
    r = _piped("delete alpha's snapshots")
    assert not any(op.operator == "delete_vm" and op.on == "alpha" for op in r.operations)
    assert any("alpha's snapshots" in a for a in r.asks), r.asks


def test_rule_8_is_idempotent():
    rows = _rows("delete alpha's snapshots")
    assert V.read_values(rows, "delete alpha's snapshots", B) == rows


# ── rule 9 · SELECT-UNSHAPED — the slot is the licence, the owner answers (ledger #20) ───────

def test_an_unshaped_selector_is_refused_with_the_ask():
    refused = [r.value["refused"] for r in _rows("stop the vm at 8g:77q") if r.kind == "value"]
    assert refused and "'8g:77q'" in refused[0] and "which is it" in refused[0]


def test_the_ask_reaches_the_operator_not_the_model():
    r = _piped("stop the vm at 8g:77q")
    assert any("8g:77q" in a for a in r.asks), r.asks


def test_a_bare_word_in_the_slot_may_be_a_name_and_stays():
    # ba-0001's convention holds: `lab` behind `on` is a NAME, not an attribute value —
    # only an identifier SHAPE (a digit or separator) claims the slot (rr-0001, adj-0004)
    for s in ("stop the vms running on lab", "stop the vm at zzz"):
        assert not any(r.kind == "value" for r in _rows(s)), s


def test_a_clock_is_never_a_selector():
    # qual-0005 (sealed x3) and dt-0001 share the slot's preposition with a TIME
    for s in ("snapshot every vm at 21:30", "stop every vm at 9pm"):
        assert not any(r.kind == "value" for r in _rows(s)), s


def test_a_thing_and_an_attribute_word_stay_in_the_phrase():
    things, values = _shaped("stop the vms on the lab network")
    assert values == [] and things[0][2] == {"network": "lab"}


def test_rule_9_is_idempotent():
    rows = _rows("stop the vm at 8g:77q")
    assert V.read_values(rows, "stop the vm at 8g:77q", B) == rows


# ── rule 8-of · the genitive's OF spelling + the ordering axis (ledger #23) ──────────────────

def test_sup_0002_the_of_genitive_leaf_is_bare_and_carries_its_ordering():
    rows = _rows("delete the oldest snapshot of alpha")
    assert [(r.span, r.kind) for r in rows] == [("alpha", "?"), ("snapshot", "value")]
    v = next(r.value for r in rows if r.kind == "value")
    assert v["ordering"] == "oldest" and v["owner"] == "vm" and v["target"] == "alpha"


def test_the_attribute_of_form_still_belongs_to_step_one():
    # `the cpu of the web vm` — an ATTRIBUTE head is step 1/4's; rule 8-of must not double-read
    assert _shape(_rows("set the cpu of the web vm to 4 cores")) == [
        ("the web vm", "vm", None), ("4 cores", "value", "cpu_cores")]


def test_a_quantifier_head_is_the_partitive_not_a_leaf():
    for s in ("stop two of the lab vms", "stop half of the vms"):
        assert not any(r.kind == "value" for r in _rows(s)), s


def test_the_ordering_axis_ask_is_licensed_by_the_declared_types():
    from orchestrator.languages.english.seam.gate4 import unordered_superlatives
    # two orderable axes on vm -> WHICH; none on snapshot -> TEACH; ordinals never fire
    asks = unordered_superlatives(_rows("stop the biggest vm"), B)
    assert len(asks) == 1 and "cpu_cores, memory_mb — which?" in asks[0]
    asks = unordered_superlatives(_rows("delete the oldest snapshot of alpha"), B)
    assert len(asks) == 1 and "teach the axis" in asks[0]
    assert unordered_superlatives(_rows("delete the last snapshot"), B) == []
