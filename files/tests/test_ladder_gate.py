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

from tests.bench.ladder_gate import (LAYER, SUCCESS, diff, flaky, goal_asked,
                                     layer_of, over_budget_of, passes_of, table)

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


def cell(n=3, goal="a goal", **outcomes):
    """A measured cell. `goal` carries the question the cell was asked, because a real one
    does now — a fixture without it would exercise the pre-goal path forever and the tests
    below would stop testing the comparison they are named for."""
    return {"n": n, "goal": goal, "outcomes": dict(outcomes),
            "passes": outcomes.get("PASS", 0),
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
                           ("REPAIR_UNDELIVERED:trailing_prose", "harness"),
                           ("REPAIR_UNDELIVERED:malformed", "channel"),
                           ("CRASHED", "harness"),
                           ("CHECKER_DISPUTE", "harness")):
        check(f"{code} -> {expected}", layer_of(code) == expected)

    # THE THREE THE HARNESS OWNS ARE THE POINT. Two of them exist because a real failure
    # was invisible without them, and the third lets the harness accuse itself.
    check("the harness can be blamed by its own gate",
          {"REPAIR_UNDELIVERED:trailing_prose", "CRASHED", "CHECKER_DISPUTE"}
          <= {c for c, l in LAYER.items() if l == "harness"})
    # THE UNSPLIT CODE MUST BE GONE. Leaving it defined would let an un-migrated writer
    # keep emitting a verdict that names the wrong owner half the time.
    check("the ambiguous code no longer exists", "REPAIR_UNDELIVERED" not in LAYER)
    check("an unknown code is UNATTRIBUTED, never filed under the model",
          layer_of("SOMETHING_NEW") == "UNATTRIBUTED")


def test_a_cell_that_never_ran_is_not_a_cell_with_no_failures():
    """CAUGHT BY THIS GATE, IN ITS OWN INSTRUMENTATION, on the first real baseline.

    The probe `continue`s past the rest of the loop on a non-result, which skipped the
    sink append — so a cell whose every reply was malformed JSON recorded as `{}` rather
    than as BAD_JSON×3. Three channel failures, the exact class the taxonomy was built to
    surface, reported as an empty cell. Silence reading as no-data instead of as a failure
    is the shape this codebase keeps rediscovering, and here it was inside the instrument
    meant to prevent it.

    So an empty cell is a HARNESS FAULT, never a clean cell, and n=0 can never read as a
    pass rate.
    """
    empty = {"lit:11": cell(n=0)}
    check("an empty cell records no passes", empty["lit:11"]["passes"] == 0)
    check("and is not flaky — flakiness needs runs", not flaky(empty["lit:11"]))
    # A cell that recorded nothing must not silently match a baseline that recorded
    # failures, or a channel collapse looks like the status quo.
    base = {"lit:11": cell(PASS=1, GOAL_UNMET=2)}
    moves = diff(base, empty)
    check("an empty cell is named a HARNESS fault, not a score change",
          kinds_of(moves).get("lit:11") == "NO RECORD (harness)")
    check("and it does not crash the gate on a divide by zero", bool(moves))
    out = table(empty, "T")
    check("the table shows n=0 rather than an empty line", "0/0" in out)


def test_a_REWORDED_rung_is_void_not_regressed():
    """A2. Without this, rewording a rung reads as PASS RATE DOWN forever — and C4, E5 and
    F1 all imply rewording, so the gate would have started lying the first time any of them
    landed. A cell measured on a different question has not been shown to have regressed;
    reporting a move with a number attached would be a false accusation, which is worse
    than silence.
    """
    base = {"lit:8": cell(goal="put every vm on core, except db", PASS=3)}
    now = {"lit:8": cell(goal="every vm goes on core; db goes on dmz", GOAL_UNMET=3)}
    moves = diff(base, now)
    check("a 3/3 -> 0/3 drop under a NEW question is not a regression",
          kinds_of(moves)["lit:8"] == "GOAL CHANGED — baseline void")
    check("and the reader is shown which words moved",
          any("except db" in str(w) for _k, _t, w, _n in moves))
    same = diff(base, {"lit:8": cell(goal="put every vm on core, except db", GOAL_UNMET=3)})
    check("the SAME question dropping 3/3 -> 0/3 is still a real move",
          kinds_of(same)["lit:8"] == "PASS RATE DOWN")


def test_a_baseline_with_no_goal_says_so_rather_than_matching():
    """The twenty-six cells recorded before today carry no goal. Treating absence as
    agreement is the unstated premise passing for a met one — the same trap `env_stamp`
    closes for conditions, one level in."""
    base = {"lit:1": {"n": 3, "outcomes": {"PASS": 3}, "passes": 3,
                      "calls_min": None, "artifacts": 0, "details": {}}}
    moves = diff(base, {"lit:1": cell(goal="anything at all", PASS=3)})
    check("an unrecorded goal is named, not assumed equal",
          kinds_of(moves)["lit:1"] == "GOAL UNRECORDED")


def test_the_goal_recorded_is_the_goal_ASKED():
    """`author_probe` takes `rung.paraphrase or rung.goal` under -p. If the gate recorded
    the raw `paraphrase` instead, every rung without one would look like a different
    question in the para column than in the lit column — when it is the same sentence."""
    from tests.bench.rungs import RUNGS
    bare = [r for r in RUNGS if not r.paraphrase]
    for r in bare:
        check(f"rung {r.n} has no paraphrase, so both columns ask its literal goal",
              goal_asked(r, "para") == goal_asked(r, "lit") == r.goal)
    worded = [r for r in RUNGS if r.paraphrase][0]
    check("a rung WITH a paraphrase asks it in the para column",
          goal_asked(worded, "para") == worded.paraphrase)
    check("and its literal column is untouched",
          goal_asked(worded, "lit") == worded.goal)


def test_over_budget_is_a_solved_rung_not_a_failure():
    """A DISTORTION I INTRODUCED AND THE FIRST BASELINE EXPOSED. `para:4` printed 0/3 while
    the rung's own checker had PASSED all three runs — the program achieved the goal and
    merely cost 21 calls against a recorded best of 17. Scoring that as a miss reports a
    solved rung as broken, which is the over-reporting this file exists to prevent, coming
    from the instrument itself.

    Cost is a SEPARATE AXIS and is reported rather than counted, for a reason that is not
    squeamishness: `rung.best` is stale in the loose direction (rung 6 declares 30 where
    the model achieves 17) and absent on 8 of 13 rungs. Failing a cell against a number
    nobody has re-earned would be a gate enforcing a guess.
    """
    check("OVER_BUDGET counts as achieving the goal", "OVER_BUDGET" in SUCCESS)
    c = cell(**{"OVER_BUDGET": 3})
    check("a cell that always ran over budget still achieved it 3/3", passes_of(c) == 3)
    check("and is not flaky — it never failed", not flaky(c))
    check("the cost is carried separately", over_budget_of(c) == 3)

    out = table({"para:4": c}, "T")
    check("the table says GOAL ACHIEVED, not PASSES", "GOAL ACHIEVED 3/3" in out)
    check("cost gets its own line", "over budget" in out)
    check("and the line says the baselines are not trustworthy yet", "stale" in out)
    check("an over-budget cell contributes no layer blame",
          "failures by layer: none" in out)

    # AND IT IS NOT A REGRESSION EITHER WAY. Going from PASS to OVER_BUDGET is a cost
    # story, not a correctness one, and a gate that fails on it would be switched off.
    check("PASS -> OVER_BUDGET is not a pass-rate regression",
          not [m for m in diff({"para:4": cell(PASS=3)}, {"para:4": c})
               if m[1] == "PASS RATE DOWN"])

    # ONE DEFINITION OF A PASS. The stored `passes` field went stale the moment the
    # definition changed, which is why every reader now derives it.
    stale = {"n": 3, "outcomes": {"OVER_BUDGET": 3}, "passes": 0,
             "calls_min": None, "artifacts": 0, "details": {}}
    check("a stale stored `passes` is ignored in favour of the derived one",
          passes_of(stale) == 3)


def test_one_event_with_two_owners_gets_two_codes():
    """`lit:7` and `lit:13` both recorded REPAIR_UNDELIVERED and are different bugs.

    lit:13 is `Extra data` — the model produced a CORRECT program and explained itself in
    a trailing sentence, and a strict json.loads threw the answer away. Ours, one line.
    lit:7 is malformed JSON from the decoder. Not ours, and probably not fixable.

    Under one code, fixing the reader would have moved both cells and taken credit for a
    channel defect it never touched. The split is what makes the two separately
    measurable — which is the entire premise of attributing failures to a layer.
    """
    check("a repair lost to OUR reader is the harness",
          layer_of("REPAIR_UNDELIVERED:trailing_prose") == "harness")
    check("a repair lost to broken JSON is the channel",
          layer_of("REPAIR_UNDELIVERED:malformed") == "channel")
    check("and an empty repair reply is the channel too",
          layer_of("REPAIR_UNDELIVERED:empty") == "channel")

    # The two cells must now be able to move independently.
    base = {"lit:7": cell(**{"REPAIR_UNDELIVERED:malformed": 3}),
            "lit:13": cell(**{"REPAIR_UNDELIVERED:trailing_prose": 3})}
    fixed_reader = {"lit:7": cell(**{"REPAIR_UNDELIVERED:malformed": 3}),
                    "lit:13": cell(PASS=3)}
    moves = kinds_of(diff(base, fixed_reader))
    check("fixing the reader moves the cell it fixed", moves.get("lit:13") == "pass rate up")
    check("and leaves the channel cell alone", "lit:7" not in moves)

    from tests.bench.author_probe import _decode_failure
    check("the classifier is shared, so both channels agree",
          _decode_failure("JSONDecodeError: Extra data: line 3") == "trailing_prose"
          and _decode_failure("Expecting value: line 1 column 1") == "empty"
          and _decode_failure("Expecting ':' delimiter") == "malformed")


def test_a_partial_check_does_not_accuse_the_cells_it_skipped():
    """`check -r 7 -r 13 -c lit` reported 26 regressions — the two it measured plus every
    cell it never ran. The same fault as `record` overwriting the whole baseline, arriving
    in the reader instead of the writer: a narrow command treating everything outside its
    own scope as news.

    Scope is what the invocation SET OUT to measure, taken from its arguments and never
    from what came back — so a cell that was asked for and produced nothing is still
    reported NOT MEASURED. Scoping by results instead would let a vanishing cell hide
    behind a narrow run, and silence is the one thing a regression gate may not treat as
    good news.
    """
    base = {"lit:7": cell(GOAL_UNMET=3), "lit:13": cell(GOAL_UNMET=3),
            "lit:1": cell(PASS=3), "para:9": cell(PASS=3)}
    now = {"lit:7": cell(PASS=3), "lit:13": cell(GOAL_UNMET=3)}
    scope = {"lit:7", "lit:13"}

    unscoped = kinds_of(diff(base, now))
    check("without scope, the untouched cells are wrongly accused",
          unscoped.get("lit:1") == "NOT MEASURED")

    scoped = kinds_of(diff(base, now, scope))
    check("with scope, cells outside it are silent", "lit:1" not in scoped
          and "para:9" not in scoped)
    check("and the cells inside it are still judged", scoped.get("lit:7") == "pass rate up")
    check("a cell in scope that stayed put is silent", "lit:13" not in scoped)

    # THE CASE SCOPING MUST NOT BREAK: asked for, and nothing came back.
    vanished = kinds_of(diff(base, {"lit:7": cell(PASS=3)}, scope))
    check("a cell that was asked for and vanished is STILL reported",
          vanished.get("lit:13") == "NOT MEASURED")


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
    """Every `test_*` in this module, in definition order — DISCOVERED, not listed.

    THE LIST WAS THE BUG, and it bit here on 2026-07-30 exactly as it had bitten
    `test_medusa_invariants` the day before: three checks were added for the goal
    comparison and none of them ran, because the hand-maintained tuple below did not
    mention them. The file reported 55/55 and looked green.

    That is this suite's OWN rule turned on itself — *a cell that stopped being measured
    must never read as a cell that stopped failing* — and it is the codebase's oldest
    failure mode, the one `run_all.py` exists for. Discovery removes the step a human has
    to remember.
    """
    import inspect as _inspect  # noqa: F401
    _mod = sys.modules[__name__]
    _found = [v for k, v in vars(_mod).items()
              if k.startswith("test_") and callable(v)]
    _found.sort(key=lambda f: f.__code__.co_firstlineno)
    for fn in _found:
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed  ({len(_found)} tests)")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
