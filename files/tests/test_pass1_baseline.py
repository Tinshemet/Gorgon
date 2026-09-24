"""test_pass1_baseline.py — pins pass-1's headline metrics on the frozen 3239-atom baseline.

The 2000-turn / 3239-atom marathon dataset is the agreed baseline; `pass1_baseline.jsonl` is a
committed freeze of it so this runs with NO model call, in well under a second — the fast
regression net for "did pass 1's numbers move" without re-running the 3k through the GPU.

⇒ FLOORS, NOT EXACT PINS. Pass 1 is meant to IMPROVE, so an exact pin would go red on every win.
  These are regression FLOORS: green while the metric holds or rises, red only when it drops. As
  we raise a metric, raise its floor. The GOALS below are the targets we are driving toward.

    baseline 2026-09-24 (post negation-fix):  preservation 98.58% · accuracy 74.55% · perfect 73.35%
    GOALS:                                     preservation → 99%   · accuracy → 95% (aiming 99%)

    PYTHONPATH=. python3 -m pytest tests/test_pass1_baseline.py -q
    PYTHONPATH=. python3 tests/test_pass1_baseline.py           # print the numbers
"""
import os

from tests.bench.read_eval import pass1_eval, pass1_score

BASELINE = os.path.join(os.path.dirname(__file__), "bench", "read_eval", "pass1_baseline.jsonl")
M = pass1_score.score(pass1_eval.load(BASELINE))

# regression floors — RAISE these as pass 1 improves (see GOALS in the docstring)
PRESERVATION_FLOOR = 98.5     # data-keeping is a hard guardrail; goal 99
ACCURACY_FLOOR = 74.0         # structural accuracy; goal 95
PERFECT_FLOOR = 73.0
BASELINE_ATOMS = 3239         # the dataset must not silently change size


def test_preservation_holds():
    assert M["preservation"] >= PRESERVATION_FLOOR, \
        f"PRESERVATION regressed to {M['preservation']:.2f}% (floor {PRESERVATION_FLOOR}%) — data is being lost"


def test_accuracy_holds():
    assert M["accuracy"] >= ACCURACY_FLOOR, \
        f"ACCURACY regressed to {M['accuracy']:.2f}% (floor {ACCURACY_FLOOR}%) — structure got worse"


def test_perfect_holds():
    assert M["perfect"] >= PERFECT_FLOOR, \
        f"PERFECT regressed to {M['perfect']:.2f}% (floor {PERFECT_FLOOR}%)"


def test_baseline_dataset_intact():
    assert M["ok"] + M["gorgon_drop"] == BASELINE_ATOMS, \
        f"baseline atom count changed: {M['ok']+M['gorgon_drop']} != {BASELINE_ATOMS} — the fixture moved"


if __name__ == "__main__":
    print(f"pass-1 baseline ({M['turns']} turns):")
    pass1_score.report(M)
    print(f"\nfloors: preservation>={PRESERVATION_FLOOR} accuracy>={ACCURACY_FLOOR} perfect>={PERFECT_FLOOR}")
