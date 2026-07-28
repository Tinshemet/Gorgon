#!/usr/bin/env python3
"""
test_ladder_gate.py — the regression gate's own logic, with no model and no world.

THE GATE IS ITSELF ONE OF THE FOUR FAILURE POINTS it exists to separate — the language,
the model, the harness, and the report. A gate whose diff logic is wrong reports moves
that did not happen and hides ones that did, which is worse than no gate: it launders a
guess into a measurement. So every rule it applies is exercised here against fixtures,
deterministically, in milliseconds.

The rules under test, each earned from a real mistake made on 2026-07-28:

  A CELL THAT FLICKERS IS NOT A CELL THAT MOVED. Rung 4 fails roughly one run in three on
  an unchanged build. Read at n=1 that is indistinguishable from a regression, and it was
  read that way three times in one day — each diagnosis dissolving at n=3 after the fix
  had already been attempted. So a flaky cell gets one run of slack before it counts.

  A REASON CHANGE IS NEWS AT THE SAME SCORE. A cell going from GOAL_UNMET to BAD_JSON has
  not got better or worse on the scoreboard, and something entirely different is now
  wrong. A pass count cannot say that; the outcome class can.

  AN UNKNOWN CODE IS UNATTRIBUTED, NOT THE MODEL'S FAULT. Filing anything unrecognised
  under the model is how a harness defect becomes a story about a model that cannot
  reason — which is precisely what REPAIR_UNDELIVERED turned out to be.

Run:  PYTHONPATH=. python3 tests/test_ladder_gate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.bench.ladder_gate import LAYER, diff, flaky, layer_of, table

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def cell(n=3, **outcomes):
    return {"n": n, "outcomes": dict(outcomes), "passes": outcomes.get("PASS", 0),
            "calls_min": None, "artifacts": 0, "details": {}}


def kinds_of(moves):
    return {k: what for k, what, _w, _n in moves}


def test_a_flickering_cell_is_not_a_moved_cell():
    """Rung 4's real shape: 2/3 on an unchanged build, measured twice on both arms of an
    ablation and identical each time. A gate without slack calls that a regression on
    roughly a third of all runs and sends someone to fix nothing."""
    base = {"lit:4": cell(PASS=2, UNRECOVERED=1)}
    check("2/3 -> 2/3 is silence", not diff(base, {"lit:4": cell(PASS=2, UNRECOVERED=1)}))
    check("2/3 -> 1/3 is WITHIN the slack a flaky cell earns",
          not diff(base, {"lit:4": cell(PASS=1, UNRECOVERED=2)}))
    check("2/3 -> 0/3 is a real move",
          kinds_of(diff(base, {"lit:4": cell(UNRECOVERED=3)}))["lit:4"] == "PASS RATE DOWN")

    # A UNANIMOUS CELL GETS NO SLACK. Its own history says it does not flicker, so one
    # failure is information rather than noise — the slack is earned by observed variance,
    # never handed out by default.
    solid = {"lit:1": cell(PASS=3)}
    check("3/3 -> 2/3 on a cell that never flickered IS a move",
          kinds_of(diff(solid, {"lit:1": cell(PASS=2, GOAL_UNMET=1)}))["lit:1"]
          == "PASS RATE DOWN")
    check("flaky() means what it says",
          flaky(cell(PASS=2, GOAL_UNMET=1)) and not flaky(cell(PASS=3))
          and not flaky(cell(GOAL_UNMET=3)))


def test_a_new_reason_at_the_same_score_is_reported():
    """The move a scoreboard cannot show. Rung 11 failed all day at the same rate while
    the CAUSE moved from an inverted condition, to malformed JSON, to a correct repair
    discarded over a trailing sentence — three different defects wearing one FAIL."""
    base = {"lit:11": cell(PASS=1, GOAL_UNMET=2)}
    same_rate_new_reason = {"lit:11": cell(PASS=1, **{"BAD_JSON:malformed": 2})}
    moves = diff(base, same_rate_new_reason)
    check("the reason change is surfaced", kinds_of(moves)["lit:11"] == "NEW FAILURE REASON")
    check("and it names the reason that is new",
          "BAD_JSON:malformed" in moves[0][3])
    check("the same reason at the same rate stays quiet",
          not diff(base, {"lit:11": cell(PASS=1, GOAL_UNMET=2)}))


def test_appearing_and_vanishing_cells_are_both_reported():
    """A cell that stopped being measured must never read as a cell that stopped failing.
    Silence is the one thing a regression gate may not treat as good news — this codebase
    has learned it twice, from a suite that stopped being mentioned and stopped being run,
    and from a tool that reported done whenever the call returned."""
    base = {"lit:1": cell(PASS=3), "lit:2": cell(PASS=3)}
    moves = kinds_of(diff(base, {"lit:1": cell(PASS=3)}))
    check("a cell missing from the run is REPORTED, not skipped",
          moves.get("lit:2") == "NOT MEASURED")
    moves = kinds_of(diff({"lit:1": cell(PASS=3)}, base))
    check("a cell with no baseline is flagged as new", moves.get("lit:2") == "NEW CELL")


def test_an_improvement_is_not_a_regression():
    """Both are moves and only one is bad news. Collapsing them would make the gate's exit
    code fire on a fix, which is the fastest way to have a gate switched off."""
    moves = diff({"lit:11": cell(GOAL_UNMET=3)}, {"lit:11": cell(PASS=3)})
    check("a cell that got better is reported", len(moves) == 1)
    check("and is not called a regression", moves[0][1] == "pass rate up")


def test_every_outcome_names_the_layer_that_owns_it():
    """The whole point of the taxonomy. Four failure points collapsed into one FAIL is
    what made a discarded repair look like a model that could not reason."""
    for code, expected in (("GOAL_UNMET", "model"), ("UNRECOVERED", "model"),
                           ("NO_EMISSION", "channel"),
                           ("BAD_JSON:trailing_prose", "channel"),
                           ("GATE_REFUSED", "language"),
                           ("REPAIR_UNDELIVERED", "harness"), ("CRASHED", "harness"),
                           ("CHECKER_DISPUTE", "harness")):
        check(f"{code} -> {expected}", layer_of(code) == expected)

    # THE THREE THE HARNESS OWNS ARE THE POINT. Two of them exist because a real failure
    # was invisible without them, and the third lets the harness accuse itself.
    check("the harness can be blamed by its own gate",
          {"REPAIR_UNDELIVERED", "CRASHED", "CHECKER_DISPUTE"}
          <= {c for c, l in LAYER.items() if l == "harness"})
    check("an unknown code is UNATTRIBUTED, never filed under the model",
          layer_of("SOMETHING_NEW") == "UNATTRIBUTED")


def test_the_report_states_its_own_n():
    """The fourth failure point is the person relaying the numbers. A table that omits how
    many runs produced it invites exactly the over-reading that happened repeatedly on
    2026-07-28 — a single sample quoted as a result."""
    out = table({"lit:4": cell(PASS=2, UNRECOVERED=1)}, "T")
    check("n appears per cell", "  3  " in out or "3  " in out)
    check("the pass figure carries its denominator", "2/3" in out)
    check("a flaky cell says so in the table", "~flaky" in out)
    check("failures are summarised by LAYER, not just counted",
          "failures by layer" in out and "model" in out)
    check("and the table states where its figures came from",
          "from this run" in out)


def main():
    for fn in (test_a_flickering_cell_is_not_a_moved_cell,
               test_a_new_reason_at_the_same_score_is_reported,
               test_appearing_and_vanishing_cells_are_both_reported,
               test_an_improvement_is_not_a_regression,
               test_every_outcome_names_the_layer_that_owns_it,
               test_the_report_states_its_own_n):
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
