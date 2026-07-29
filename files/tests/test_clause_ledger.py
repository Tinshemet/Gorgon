"""
test_clause_ledger.py — the clause ledger, against the three failures that caused it.

Deterministic, no model, answers in milliseconds. Written the way the Medusa suites are:
the module under test is pure functions over dicts, so it is tested directly rather than
through the ladder. See [ladder-is-not-a-feedback-loop] — a rung is not how you find a
logic bug.

THE THREE REGRESSION CASES ARE REAL MEASUREMENTS, not invented examples. Each is a goal
the atomicity router answered by dropping a clause, 3/3, on 2026-07-29.
"""
import pytest

from orchestrator.ai.planner import clause_ledger as cl

# ── The three measured failures ─────────────────────────────────────────────────────────
# goal · demands (as an enumerator would record them) · what the router actually returned.
MEASURED = [
    (
        "rung 8",
        "put every vm on a network called core, except db — db goes on a network called dmz",
        [{"text": "put every vm on a network called core", "anchors": ["core"]},
         {"text": "db goes on a network called dmz", "anchors": ["db", "dmz"]}],
        [{"op": "foreach", "select": {"kind": "vm"},
          "call": {"tool": "add_vm_to_network", "args": {"net_name": "core"}}}],
        "dmz",
    ),
    (
        "rung 10",
        "clone golden into 3 new vms and launch all of them",
        [{"text": "clone golden into 3 new vms", "anchors": ["golden"]},
         {"text": "launch all of them", "anchors": ["launch"]}],
        [{"op": "new", "var": "clones", "kind": "vm", "amount": 3,
          "args": {"source": "golden"}}],
        "launch",
    ),
    (
        "rung 11",
        "ping every vm and stop the ones that do not answer",
        [{"text": "ping every vm", "anchors": ["ping"]},
         {"text": "stop the ones that do not answer", "anchors": ["stop"]}],
        [{"op": "foreach", "select": {"kind": "vm"},
          "call": {"tool": "guest_ping", "args": {"name": "$item"}}}],
        "stop",
    ),
]


@pytest.mark.parametrize("name,goal,demands,answer,missing_token",
                         MEASURED, ids=[m[0] for m in MEASURED])
def test_it_catches_the_clause_the_router_dropped(name, goal, demands, answer,
                                                  missing_token):
    led = cl.reconcile(cl.open_ledger(goal, demands), answer)
    miss = cl.unaccounted(led)
    assert len(miss) == 1, f"{name}: expected exactly the dropped clause, got {miss}"
    assert miss[0]["text"] == demands[1]["text"]
    assert cl.verdict(led) == cl.UNACCOUNTED
    assert missing_token in cl.report(led).lower()


def test_rung_demands_are_honest():
    """THE BENCHMARK MUST NOT GRADE ITSELF. Every anchor a rung declares has to be a word
    the GOAL actually contains, in whichever column is being asked — otherwise the ledger
    is a second description of the goal held by the harness, and it could point the author
    at something the operator never said.

    `open_ledger` enforces this by dropping unmatched anchors, so this test is about the
    DECLARATIONS: an anchor that survives in neither column is one nobody thought about,
    and it would sit in the file looking load-bearing while doing nothing.
    """
    from tests.bench.rungs import RUNGS
    declared = [r for r in RUNGS if r.demands]
    assert declared, "no rung declares demands — this guard would pass vacuously"
    for rung in declared:
        for d in rung.demands:
            for anchor in d.get("anchors") or []:
                in_lit = anchor.lower() in rung.goal.lower()
                in_para = anchor.lower() in (rung.paraphrase or "").lower()
                assert in_lit or in_para, (
                    f"rung {rung.n}: anchor {anchor!r} appears in NEITHER column's goal — "
                    f"the ledger would be pointing at a word the operator never used")


def test_the_ledger_stays_silent_on_a_correct_rung_8_program():
    """THE FALSE-OBJECTION GUARD, and it is the one that matters for shipping this into
    the repair loop. A correct program must draw no ledger complaint, or the mechanism
    breaks a rung it was supposed to help."""
    from tests.bench.rungs import RUNGS
    r8 = [r for r in RUNGS if r.n == 8][0]
    correct = [
        {"op": "new", "var": "core", "kind": "network", "args": {"net_name": "core"}},
        {"op": "new", "var": "dmz", "kind": "network", "args": {"net_name": "dmz"}},
        {"op": "foreach", "select": {"kind": "vm", "not": {"name": "db"}},
         "call": {"tool": "add_vm_to_network", "args": {"net_name": "core"}}},
        {"op": "call", "tool": "add_vm_to_network",
         "args": {"name": "db", "net_name": "dmz"}},
    ]
    for goal in (r8.goal, r8.paraphrase):
        led = cl.reconcile(cl.open_ledger(goal, r8.demands), correct)
        assert cl.unaccounted(led) == [], f"false objection on a correct program: {goal!r}"


def test_it_catches_the_real_para_8_program():
    """The measured failure, verbatim: every vm on core, then app1/app2/app3 on dmz. `db`
    appears nowhere, which is the defect the validator's `select must name a kind` never
    mentioned across both repair rounds."""
    from tests.bench.rungs import RUNGS
    r8 = [r for r in RUNGS if r.n == 8][0]
    measured = [
        {"op": "new", "var": "core", "kind": "network", "args": {"net_name": "core"}},
        {"op": "foreach", "select": {"kind": "vm"},
         "call": {"tool": "add_vm_to_network", "args": {"net_name": "core"}}},
        {"op": "new", "var": "dmz", "kind": "network", "args": {"net_name": "dmz"}},
        {"op": "foreach", "select": {"name": "['app1', 'app2', 'app3']"},
         "call": {"tool": "add_vm_to_network", "args": {"net_name": "dmz"}}},
    ]
    led = cl.reconcile(cl.open_ledger(r8.paraphrase, r8.demands), measured)
    miss = cl.unaccounted(led)
    assert len(miss) == 1
    assert "db" in miss[0]["text"] and miss[0]["by"] == cl.BY_ANCHOR


def test_a_plan_that_covers_every_demand_is_not_reported_missing():
    """The other direction. A checker that fires on a correct plan is worse than none —
    it teaches the reader to ignore it."""
    demands = [{"text": "ping every vm", "anchors": ["ping"]},
               {"text": "stop the ones that do not answer", "anchors": ["stop"]}]
    answer = [
        {"op": "foreach", "select": {"kind": "vm"},
         "call": {"tool": "guest_ping", "args": {"name": "$item"}}},
        {"op": "foreach", "select": {"kind": "vm", "alive": "false"},
         "call": {"tool": "stop_vm", "args": {"name": "$item"}}},
    ]
    led = cl.reconcile(cl.open_ledger("ping every vm and stop the ones that do not answer",
                                      demands), answer)
    assert cl.unaccounted(led) == []


def test_nothing_proven_missing_is_NOT_reported_as_complete():
    """THE FAILURE MODE OF A COVERAGE CHECKER IS FALSE CONFIDENCE. `unaccounted() == []`
    must never read as "the plan is complete" — the demands were simply never established
    either way, and the report has to say so in words."""
    demands = ["do the first thing", "do the second thing"]      # no anchors declared
    answer = [{"op": "call", "tool": "a"}, {"op": "call", "tool": "b"}]
    led = cl.reconcile(cl.open_ledger("g", demands), answer)
    assert cl.unaccounted(led) == []
    assert len(cl.unverified(led)) == 2
    assert cl.verdict(led) == cl.UNVERIFIED, "must not claim `clear` on unverified rows"
    assert "not the same as complete" in cl.report(led)


def test_pigeonhole_fires_with_no_anchors_at_all():
    """The arithmetic detector standing alone. It cannot say WHICH demand is missing, and
    it does not need anchors to prove that one is — which is what makes it the floor under
    an enumerator that supplies nothing but text."""
    led = cl.reconcile(cl.open_ledger("g", ["first", "second", "third"]),
                       [{"op": "call", "tool": "only_one"}])
    miss = cl.unaccounted(led)
    assert len(miss) == 2, "3 demands and 1 statement proves 2 unaccounted for"
    assert all(m["by"] == cl.BY_PIGEONHOLE for m in miss)
    assert "3 demands, 1 statement" in miss[0]["why"]


def test_the_anchor_verdict_wins_over_pigeonhole():
    """Both detectors can fire on one row. The anchor names WHICH demand is missing where
    pigeonhole only proves that one is, so the more informative attribution must survive —
    otherwise the report degrades to arithmetic whenever both apply."""
    demands = [{"text": "put them on core", "anchors": ["core"]},
               {"text": "and db on dmz", "anchors": ["dmz"]}]
    led = cl.reconcile(cl.open_ledger("put them on core and db on dmz", demands),
                       [{"op": "foreach", "call": {"args": {"net_name": "core"}}}])
    miss = cl.unaccounted(led)
    assert len(miss) == 1 and miss[0]["by"] == cl.BY_ANCHOR


def test_an_anchor_not_in_the_goal_is_dropped():
    """THE HONESTY GUARANTEE. The ledger may only point at words the operator actually
    used — otherwise it becomes a second description of the goal held by the harness, and
    the line between "what is missing" and "what to write" is gone."""
    led = cl.open_ledger("put every vm on core, except db",
                         [{"text": "db goes on dmz", "anchors": ["db", "dmz"]}])
    row = led["demands"][0]
    assert row["anchors"] == ["db"], "only the anchor the goal actually contains survives"
    assert row["dropped"] == ["dmz"]


def test_a_demand_whose_anchors_are_all_dropped_is_still_counted():
    """Dropping anchors must not drop the DEMAND — otherwise a paraphrase that reworded
    one clause would silently shrink what the goal is held to. Rung 10 is `launch all of
    them` literally and `boot every copy` in paraphrase; the demand survives either way
    and the pigeonhole detector still proves it missing."""
    led = cl.reconcile(
        cl.open_ledger("take a copy of golden three times over and boot every copy",
                       [{"text": "copy golden three times", "anchors": ["golden"]},
                        {"text": "launch all of them", "anchors": ["launch"]}]),
        [{"op": "new", "kind": "vm", "amount": 3, "args": {"source": "golden"}}])
    miss = cl.unaccounted(led)
    assert len(miss) == 1 and miss[0]["by"] == cl.BY_PIGEONHOLE
    assert led["demands"][1]["anchors"] == [] and led["demands"][1]["dropped"] == ["launch"]


def test_it_reads_a_routers_plain_english_steps_as_well_as_ir():
    """The router returns `steps` as strings; a program returns IR dicts. The ledger is
    given whichever the planner produced and must not care which."""
    demands = [{"text": "create the vms", "anchors": ["create"]},
               {"text": "launch them", "anchors": ["launch"]}]
    led = cl.reconcile(cl.open_ledger("g", demands), ["create 5 vms", "launch all of them"])
    assert cl.unaccounted(led) == []


def test_it_changes_nothing():
    """Constitutional: it reads and reports. A ledger that edited the plan would be doing
    high-impact work with nobody asking — the book keeper's rule, and the reason neither
    has a writer."""
    demands = [{"text": "a", "anchors": ["a"]}, {"text": "b", "anchors": ["zzz"]}]
    led = cl.open_ledger("g", demands)
    before = [dict(r) for r in led["demands"]]
    plan = [{"op": "call", "tool": "a"}]
    out = cl.reconcile(led, plan)
    assert led["demands"] == before, "reconcile mutated the ledger it was given"
    assert plan == [{"op": "call", "tool": "a"}], "reconcile mutated the plan"
    assert out is not led


def test_a_goal_with_one_demand_and_one_statement_is_never_flagged():
    """The atomic case. Rungs 1, 5, 7, 9 and 12 are single-statement goals and the ledger
    must stay silent on them, or every correct one-operator answer carries a warning."""
    led = cl.reconcile(cl.open_ledger("launch every vm that is currently stopped",
                                      [{"text": "launch every stopped vm",
                                        "anchors": ["launch"]}]),
                       [{"op": "foreach", "select": {"kind": "vm", "status": "stopped"},
                         "call": {"tool": "launch_vm", "args": {"name": "$item"}}}])
    assert cl.unaccounted(led) == []
    assert cl.verdict(led) == "clear"
