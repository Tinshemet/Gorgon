"""The --rank door of review.py: a second person ranks difficulty, BLIND.

Pins the 08-22 split — the operator certifies and does not rank; the rater ranks and never
sees a verdict. Three things a regression would quietly undo: the rank loop opening the
verdict file, the rank hash binding to the gold, the queue arriving in stratum order.
"""
import builtins
import json
import re
import sys

import pytest

from tests.bench.read_eval import review


def _case(cid, sentence, stratum="clean-single", **extra):
    n = len(sentence.split()[0])
    c = {"id": cid, "stratum": stratum, "noise": "clean", "pair_id": None, "source": "seed",
         "sentence": sentence,
         "gold": {"spans": [], "actions": [{"text": sentence.split()[0], "start": 0, "end": n}],
                  "attachments": []}}
    c.update(extra)
    return c


@pytest.fixture
def cases_file(tmp_path):
    cases = [_case("aa-0001", "stop alpha"), _case("aa-0002", "stop beta", store=[{"word": "beta"}]),
             _case("bb-0001", "restart gamma", stratum="other", context={"mood": "calm"})]
    path = tmp_path / "draft.jsonl"
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    # a verdict file with a note the rater must never be shown
    (tmp_path / "draft.review.json").write_text(json.dumps(
        {"aa-0001": {"verdict": "rejected", "hash": "x", "note": "SECRET-NOTE"}}), encoding="utf-8")
    return cases, str(path)


def _drive(monkeypatch, keys, capsys):
    keys = iter(keys)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(keys))


def test_rank_hash_binds_what_was_shown_not_the_gold():
    a = _case("aa-0001", "stop alpha")
    b = _case("aa-0001", "stop alpha")
    b["gold"]["actions"][0]["text"] = "changed"
    assert review._rank_hash(a) == review._rank_hash(b), "a re-emitted gold must not stale a rank"
    c = _case("aa-0001", "stop alpha", store=[{"word": "alpha"}])
    assert review._rank_hash(a) != review._rank_hash(c), "the store is shown, so it binds"
    d = _case("aa-0001", "stop  alpha")
    assert review._rank_hash(a) != review._rank_hash(d)


def test_rank_loop_records_undoes_and_resumes(cases_file, monkeypatch, capsys):
    cases, path = cases_file
    _drive(monkeypatch, ["7", "u", "3", "s", "q"], capsys)
    assert review.rank(cases, path) == 0
    ranks = review.load_ranks(path)
    assert len(ranks) == 1 and next(iter(ranks.values()))["rank"] == 3
    # resume: the ranked case is out of the queue; the skipped and the quit-on one remain
    _drive(monkeypatch, ["10", "1"], capsys)
    review.rank(cases, path)
    ranks = review.load_ranks(path)
    assert sorted(r["rank"] for r in ranks.values()) == [1, 3, 10]
    assert all(review.rank_state_of(c, ranks) == "ranked" for c in cases)


def test_rank_is_blind(cases_file, monkeypatch, capsys):
    cases, path = cases_file
    verdict_path = path.replace(".jsonl", ".review.json")
    before = open(verdict_path, encoding="utf-8").read()
    opened = []
    real_open = builtins.open

    def spy(file, *a, **k):
        opened.append(str(file))
        return real_open(file, *a, **k)
    monkeypatch.setattr(builtins, "open", spy)
    _drive(monkeypatch, ["5", "5", "5"], capsys)
    review.rank(cases, path)
    out = capsys.readouterr().out
    assert not any(p.endswith(".review.json") for p in opened), "rank opened the verdict file"
    assert open(verdict_path, encoding="utf-8").read() == before
    assert "SECRET-NOTE" not in out and "rejected" not in out and "STALE" not in out
    for leak in ("aa-0001", "clean-single", "other", "seed", "->",
                 review.CYAN + "[", review.UL, review.MAGENTA):   # the gold's paint
        assert leak not in out, f"rank display leaks {leak!r}"
    plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
    assert "stop alpha" in plain and "context: mood=calm" in plain and "store: word=beta" in plain


def test_rank_order_is_fixed_and_not_the_file_order():
    cases = [_case(f"{pfx}-{i:04d}", f"stop vm{i}", stratum=pfx)
             for pfx in ("aa", "bb", "cc") for i in range(1, 7)]
    once = [c["id"] for c in review.rank_order(cases)]
    assert once == [c["id"] for c in review.rank_order(list(reversed(cases)))]
    assert once != [c["id"] for c in cases]
    runs = sum(1 for x, y in zip(once, once[1:]) if x[:2] == y[:2])
    assert runs < len(once) - 3, "a stratum still arrives as a run"


def test_status_does_not_load_verdicts(cases_file, monkeypatch, capsys):
    cases, path = cases_file
    review.save_ranks(path, {"aa-0001": {"rank": 9, "hash": review._rank_hash(cases[0])},
                             "aa-0002": {"rank": 2, "hash": "stale"}})
    monkeypatch.setattr(review, "load_verdicts", lambda *_: pytest.fail("rank_status read verdicts"))
    assert review.rank_status(cases, path) == 0
    out = capsys.readouterr().out
    assert "1 STALE" in out and "1 ranked" in out and "1 unranked" in out
    assert "difficulty: 9:1" in out


def test_certify_shows_the_stale_note(cases_file, capsys):
    """The banner was dead code behind `_channels`'s return (f125461 → 08-23)."""
    cases, path = cases_file
    verdicts = review.load_verdicts(path)            # aa-0001: rejected, hash "x" → STALE
    assert review.state_of(cases[0], verdicts) == "STALE"
    review.show(cases[0], verdicts, {c["id"]: c for c in cases})
    out = capsys.readouterr().out
    assert "STALE" in out and "SECRET-NOTE" in out
