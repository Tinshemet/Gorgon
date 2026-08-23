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
