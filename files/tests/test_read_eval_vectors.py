"""Schema v3.0 — FULL VECTOR DECONSTRUCTION PER WORD (operator 08-24, [[gorgon-vector-read]]).

The cells are computed by the seam's real readers, the fold is a function of the words, the
seal binds the vector, and RANKING NEVER SEES IT — grading and ranking are two different
issues, kept apart by construction."""
import json

from planner.formula.legal import Board
from tests.bench.read_eval import capture as CAP
from tests.bench.read_eval.review import _hash, _rank_hash
from tests.bench.read_eval.schema import load, validate
from tests.bench.read_eval.vectors import FOLD_DIMENSIONS, WORD_DIMENSIONS, vector_of

B = Board()
CASES = load("tests/bench/read_eval/cases/v3-draft.jsonl")
BY_ID = {c["id"]: c for c in CASES}


def test_every_case_carries_a_valid_vector():
    assert validate(CASES) == []
    assert all("vector" in c for c in CASES)


def test_the_cells_come_from_the_real_readers_not_word_lists():
    # the naive tagger read `let's` as a genitive; the codex contraction wins
    cells = {w["w"]: w["cells"] for w in BY_ID["io-0004"]["vector"]["words"]}
    assert "clitic" not in (cells["let's"].get("class") or ())
    assert "hort" in cells["let's"]["class"]
    # and the true genitive keeps the clitic
    cells = {w["w"]: w["cells"] for w in BY_ID["po-0001"]["vector"]["words"]}
    assert "clitic" in cells["alpha's"]["class"]


def test_po_0001_word_cells_carry_the_certified_selection_layer():
    cells = {w["w"]: w["cells"] for w in BY_ID["po-0001"]["vector"]["words"]}
    assert cells["alpha's"]["span"] == "s0:patient"
    assert cells["snapshots"]["span"] == "s1:value"
    assert cells["snapshots"]["kind"] == "snapshot"
    assert cells["delete"]["verb"]              # the manifest names the operation


def test_the_wh_cell_is_the_operators_taxonomy():
    cells = {w["w"]: w["cells"] for w in BY_ID["po-0004"]["vector"]["words"]}
    assert cells["how"]["wh"] == "count"        # how many -> count
    nq = {w["w"]: w["cells"] for w in BY_ID["nq-0001"]["vector"]["words"]}
    assert nq["which"]["wh"] == "pick-member"
    assert "neg" in nq["not"]["class"]


def test_the_fold_is_computed_and_stable():
    v = BY_ID["po-0004"]["vector"]["fold"]
    assert v["shape"] == "count" and v["act"] == "directive-inform"
    again = vector_of(BY_ID["po-0004"], B)
    assert again == BY_ID["po-0004"]["vector"]  # deterministic, model stubbed


def test_the_seal_binds_the_vector_but_the_rank_never_sees_it():
    c = dict(BY_ID["po-0001"])
    with_vec, rank_with = _hash(c), _rank_hash(c)
    c2 = {k: v for k, v in c.items() if k != "vector"}
    assert _hash(c2) != with_vec                # grading: a vector change stales a verdict
    assert _rank_hash(c2) == rank_with          # ranking: the rater never saw it — no stale


def test_capture_names_the_dimension_that_moved():
    a = {"x": {"asked": [], "reading": "r", "vector": {"kind": "1", "fold.act": "2"}}}
    b = {"x": {"asked": [], "reading": "r", "vector": {"kind": "9", "fold.act": "2"}}}
    assert CAP.diff(a, b) == ["x              vector[kind]"]


def test_the_rank_door_opens_nothing_but_ranking():
    # the ranker's command can only rank: the module's public surface carries no verdict
    # access, so forgetting a flag cannot land anyone in the grading version
    import tests.bench.read_eval.rank as RK
    assert sorted(n for n in dir(RK) if not n.startswith("_")) == [
        "List", "Optional", "load", "main", "rank", "rank_status", "validate"]


def test_sup_0002_leaf_bare_and_the_superlative_is_an_ordinal():
    # ledger #23 + 08-25 (cluster H): 'oldest' is now its OWN span, role ORDINAL (ranks the
    # set, picks one); alpha patient, snapshot the bare value leaf. adj:sup carries the key.
    c = BY_ID["sup-0002"]
    spans = {s["text"]: next((o["role"] for a in c["gold"]["attachments"]
             for o in a["objects"] if isinstance(o, dict) and o["span"] == i), None)
             for i, s in enumerate(c["gold"]["spans"])}
    assert spans == {"alpha": "patient", "snapshot": "value", "oldest": "ordinal"}
    cells = {w["w"]: w["cells"] for w in c["vector"]["words"]}
    assert "adj:sup" in cells["oldest"]["class"] and "attr" not in cells["oldest"]


def test_a_superlative_is_an_ordinal_that_produces_a_singular():
    # 08-25 (cluster H, operator): superlatives UNIFIED under `ordinal` — 'biggest' its own
    # span, ranking a set to one; NOT the whole-NP reading, NOT a selector.
    c = BY_ID["sup-0001"]
    spans = {s["text"]: next((o["role"] for a in c["gold"]["attachments"]
             for o in a["objects"] if isinstance(o, dict) and o["span"] == i), None)
             for i, s in enumerate(c["gold"]["spans"])}
    assert spans == {"vm": "patient", "biggest": "ordinal"}
    cells = {w["w"]: w["cells"] for w in c["vector"]["words"]}
    assert "adj:sup" in cells["biggest"]["class"]


def test_est_morphology_never_claims_english():
    # `the test vms` (cap-0002) — a 3+ stem is required, so test/rest/west never fire
    cells = {w["w"]: w["cells"] for w in BY_ID["cap-0002"]["vector"]["words"]}
    assert "class" not in cells["test"] or "adj:sup" not in cells["test"]["class"]
