"""test_extract_corpus.py — the repairs, replayed against REAL model answers, with no model.

A 78-CELL GPU MEASUREMENT BECOMES A MILLISECOND TEST. The A/B that proved this session's
extractor changes took forty minutes and a warm GPU; the raw answers it drew are recorded in
`corpus/extract_raw.jsonl`, so every repair can be replayed against exactly what a real model
really said, on every commit, forever.

WHAT IT GUARDS AND WHAT IT CANNOT. It guards `to_goals` — the deterministic half, where every
repair lives and where a regression is otherwise invisible until someone spends a GPU hour. It
says NOTHING about whether the model gets better or worse at answering, because the answers
are frozen. That is the point: it separates a change in the CODE from a change in the MODEL,
which is the confusion `ladder-is-not-a-feedback-loop` was written about.

THE CORPUS IS COMMITTED, AND IT IS HELD OUT BY CONSTRUCTION. It was captured from a run of the
CURRENT code, so the numbers below are a snapshot rather than a target — a later change that
moves them has to be read, not tuned against. That is the
[[gorgon-deterministic-rules]] pattern: commit the corpus, then change the code.
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines.extract import to_goals

_PASS = _FAIL = 0
_CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "bench", "corpus", "extract_raw.jsonl")


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _rows():
    if not os.path.exists(_CORPUS):
        return []
    out = []
    with open(_CORPUS) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def test_the_corpus_is_there_and_is_real_model_output():
    print("[corpus] recorded answers from a real run")
    rows = _rows()
    check(f"the corpus exists and is not thin ({len(rows)} answers)", len(rows) >= 20)
    check("every row carries the request it answered",
          all(r.get("request") for r in rows))
    check("and the raw answer as the model gave it",
          all(isinstance(r.get("raw"), dict) for r in rows))


def test_no_recorded_answer_crashes_the_repairs():
    """A repair that raises loses the whole request. These are the shapes a model really
    produces, including the malformed ones."""
    print("[corpus] every real answer converts without raising")
    bad = []
    for r in _rows():
        try:
            to_goals(r["raw"], r["request"])
        except Exception as exc:
            bad.append(f"rung {r['rung']}/{r['column']}: {type(exc).__name__}: {exc}")
    check(f"nothing raised ({bad[:2] or 'all clean'})", not bad)


def test_conversion_is_deterministic():
    """The model is not deterministic; `to_goals` must be. Otherwise a measurement cannot
    attribute anything to the code."""
    print("[corpus] the same answer converts the same way, twice")
    drift = []
    for r in _rows():
        first = json.dumps(to_goals(r["raw"], r["request"]), sort_keys=True)
        again = json.dumps(to_goals(r["raw"], r["request"]), sort_keys=True)
        if first != again:
            drift.append(r["rung"])
    check(f"every conversion is stable ({drift or 'all stable'})", not drift)


def test_no_goal_survives_that_the_writer_could_not_read():
    """A goal that reaches the writer must be one it can speak about: a declared kind, and a
    shape the vocabulary has. Anything else should have been dropped here."""
    print("[corpus] what survives is sayable to the writer")
    from planner.ir import config
    shapes = {"count", "reach"}
    holders = ("every", "observe", "per")
    strays = []
    for r in _rows():
        for g in to_goals(r["raw"], r["request"]):
            kind = None
            for holder in holders + ("select",):
                sel = g.get(holder)
                if isinstance(sel, dict):
                    kind = sel.get("kind")
                    break
            if kind not in (config.KINDS or {}):
                strays.append(f"rung {r['rung']}: kind={kind!r}")
            elif g.get("shape") and g["shape"] not in shapes:
                strays.append(f"rung {r['rung']}: shape={g['shape']!r}")
    check(f"every surviving goal names a declared kind and a known shape "
          f"({strays[:2] or 'all clean'})", not strays)


def test_the_outcome_mix_is_recorded_not_targeted():
    """A SNAPSHOT, NOT A TARGET. Printed so a change that moves it is READ rather than tuned
    against — the distinction this project has drawn every time a number became a goal."""
    print("[corpus] where the recorded run landed")
    mix = Counter(r.get("outcome") for r in _rows())
    total = sum(mix.values()) or 1
    for outcome, n in mix.most_common():
        print(f"       {n:4} ({100 * n // total:3}%)  {outcome}")
    check("the mix is reported", bool(mix))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "extract corpus"))


if __name__ == "__main__":
    main()
