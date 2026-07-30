#!/usr/bin/env python3
"""
test_medusa.py — the first unit suite over MEDUSA, the procedure language.

WHY THIS EXISTS. Until now nothing outside `tests/bench/` imported
`orchestrator.ai.planner.ir` at all: 35 suites were green and not one of them touched the
language. Every defect in it was therefore found by running a probe against a live
llama3.1 at temperature 0 — slow, needing a model to be up, and unable to attribute a
regression to a commit. It also meant the defects that DID land were the silent kind:

  * `asserted = True` had no `nonlocal`, so the rule "with an ENSURE present its verdict
    stands" had never once fired;
  * composite predicates had never been evaluated — `ENSURE AND(...)` returned
    "unevaluated shape all", and an unevaluable check counted as FAILED;
  * the schema withheld constructs the validator already implemented, and the model was
    marked wrong for not guessing them.

Each of those is a pure function over dicts. `run`, `evaluate`, `derive`, `validate` and
`observe` need no model, no network and no qemu, so they are tested here directly, and the
invariants that regressed silently get a guard that fails in under a second.

Run:  PYTHONPATH=. python3 tests/test_medusa.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.findings import (DEFAULT_SCHEMA, Findings, extract_value,
                                              yield_fact)
from orchestrator.ai.planner.ir import (config, consent, derive, evaluate, intent,
                                        observe, refs, render, run, validate)
from tests.bench.author_probe import _seams
from tests.bench.sim_world import SimWorld

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


def _world(names=("a", "b", "c"), label="fleet", dead=()):
    """A lab with `names` created and labelled, `dead` set to not answer a ping."""
    w = SimWorld()
    for n in names:
        w.execute("create_vm", {"name": n, "os_type": "linux"})
        w.execute("launch_vm", {"name": n})
        if label:
            w.execute("add_label", {"name": n, "label": label})
    w.unreachable.update(dead)
    w.calls.clear()
    return w


def _run(prog, w, **kw):
    sel, holds = _seams(w)
    return run(prog, w.execute, select=sel, holds=holds,
               known_names=w.names(), consent=True, **kw)


# ── the findings yield: a verdict, not a call status ──────────────────────────────────
def test_guest_ping_records_the_answer():
    """The real guest_ping returns success:True on every path except a missing config —
    a stopped VM, a disabled agent and a timed-out daemon all answer
    {"success": True, "alive": False}. Reading `success` recorded reachable(x)=True for
    machines that demonstrably did not respond, and three consumers (acceptance,
    anti-rediscovery, cost) then believed it."""
    spec = DEFAULT_SCHEMA["guest_ping"]
    check("guest_ping yields the fact key reachable(<name>)",
          yield_fact("guest_ping", {"name": "web"}, DEFAULT_SCHEMA) == "reachable(web)")
    check("guest_ping records `alive`, NOT `success`", spec["value"] == "alive")
    dead = {"success": True, "name": "web", "alive": False, "reachable": False}
    check("a ping that ran and got NO answer extracts False",
          extract_value(dead, spec) is False)
    live = {"success": True, "name": "web", "alive": True, "reachable": True}
    check("a ping that got an answer extracts True", extract_value(live, spec) is True)
    check("fleet still reads its own verdict key (all_reachable)",
          DEFAULT_SCHEMA["fleet"]["value"] == "all_reachable")


# ── decision 6: observed attributes, and the third value ──────────────────────────────
def test_observed_is_three_valued():
    led = Findings()
    check("an unprobed machine reads `unknown`",
          observe.value(led, "vm", "alive", "a") == observe.unknown())
    check("unknown does not match `true`",
          observe.matches(led, "vm", "alive", "a", "true") is False)
    check("unknown does not match `false` either — unasked is not dead",
          observe.matches(led, "vm", "alive", "a", "false") is False)
    check("unknown matches `unknown`, so 'who has nobody asked about' is a query",
          observe.matches(led, "vm", "alive", "a", "unknown") is True)
    led.record("reachable(a)", False, source="guest_ping")
    check("a recorded negative reads `false`",
          observe.value(led, "vm", "alive", "a") == "false")
    check("a recorded negative matches `false`",
          observe.matches(led, "vm", "alive", "a", "false") is True)
    check("a recorded negative no longer matches `unknown`",
          observe.matches(led, "vm", "alive", "a", "unknown") is False)
    check("a registry attribute is not observed — None routes it to the registry",
          observe.matches(led, "vm", "status", "a", "running") is None)
    check("is_observed distinguishes the two", observe.is_observed("vm", "alive")
          and not observe.is_observed("vm", "status"))


def test_fact_key_uses_the_kinds_key():
    check("vm's observed fact binds the kind's KEY to the member",
          config.fact_key("vm", "alive", "web") == "reachable(web)")
    check("an unobserved attribute has no fact key",
          config.fact_key("vm", "status", "web") is None)
    check("a kind with no observed table has none",
          config.fact_key("network", "alive", "core") is None)


def test_queryable_is_one_authority():
    """The attribute set was read off `attrs` in four places — the validator's legality
    check, its rejection message, the schema offered to the author, and the prompt's
    "queryable on" line. A manifest row visible to one and not the others is the
    schema-withholding failure that accounted for more measured "model errors" than
    anything else."""
    q = config.queryable("vm")
    check("queryable carries the registry attributes", {"name", "status", "label"} <= q)
    check("queryable carries the observed ones too", "alive" in q)
    check("queryable carries the harness's synonyms", "tag" in q)
    check("observed() is empty for a kind that has none", config.observed("network") == {})


def test_validator_accepts_and_polices_observed():
    ok, _ = validate({"body": [{"op": "foreach",
                                "select": {"kind": "vm", "alive": "false"},
                                "call": {"tool": "stop_vm", "args": {"name": "$item"}}}]})
    check("a WHERE on an observed attribute validates", ok)
    ok2, probs = validate({"body": [{"op": "foreach",
                                     "select": {"kind": "vm", "alive": "yes"},
                                     "call": {"tool": "stop_vm",
                                              "args": {"name": "$item"}}}]})
    check("an illegal observed value is refused", not ok2)
    check("and the refusal names all three legal values",
          probs and all(v in probs[0] for v in config.OBSERVED_VALUES))
    check("and it names the tool that learns it", probs and "guest_ping" in probs[0])


def test_the_loop_probes_the_ledger_remembers_the_query_reads():
    """Decision 6 end to end: nothing escapes the iteration. The rollout example."""
    w = _world(dead=("b",))
    sel, _ = _seams(w)
    check("before any probe, every member is unknown",
          sel({"kind": "vm", "label": "fleet", "alive": "unknown"}) == ["a", "b", "c"]
          and sel({"kind": "vm", "label": "fleet", "alive": "false"}) == [])
    prog = {"body": [
        {"op": "foreach", "select": {"kind": "vm", "label": "fleet"},
         "call": {"tool": "guest_ping", "args": {"name": "$item"}}},
        {"op": "foreach", "select": {"kind": "vm", "label": "fleet", "alive": "false"},
         "call": {"tool": "stop_vm", "args": {"name": "$item"}}},
        {"op": "achieve", "predicate": {"shape": "all", "of": [
            {"shape": "count",
             "select": {"kind": "vm", "label": "fleet", "alive": "unknown"}, "eq": 0},
            {"shape": "count",
             "select": {"kind": "vm", "label": "fleet", "alive": "false"}, "lte": 1}]}}]}
    ok, probs = validate(prog, known_names=w.names())
    check("the rollout program validates", ok, )
    res = _run(prog, w)
    check("it achieves its goal", res["ok"] and res.get("failed") is None)
    check("the probe filled the ledger from the call results",
          [(f, w.findings.get(f)) for f in sorted(w.findings.facts())]
          == [("reachable(a)", True), ("reachable(b)", False), ("reachable(c)", True)])
    check("only the machine that actually failed was stopped",
          w.vms["b"]["status"] == "stopped"
          and w.vms["a"]["status"] == "running" and w.vms["c"]["status"] == "running")


def test_a_program_that_never_probes_cannot_close_green():
    """The hazard the third value exists to close. With unknown collapsed into false, a
    program that asks nothing satisfies `COUNT(... alive='false') = 0` trivially and
    reports success over a fleet it never touched."""
    w = _world(dead=("b",))
    prog = {"body": [
        {"op": "achieve", "predicate": {"shape": "all", "of": [
            {"shape": "count",
             "select": {"kind": "vm", "label": "fleet", "alive": "unknown"}, "eq": 0},
            {"shape": "count",
             "select": {"kind": "vm", "label": "fleet", "alive": "false"}, "eq": 0}]}}]}
    res = _run(prog, w)
    check("a goal over observations fails when nothing has been asked",
          not res["ok"] and res.get("failed") == "unachieved")
    naive = {"body": [{"op": "achieve", "predicate": {
        "shape": "count", "select": {"kind": "vm", "label": "fleet", "alive": "false"},
        "eq": 0}}]}
    res2 = _run(naive, w)
    check("WITHOUT the unknown clause the same unprobed world passes — the clause is "
          "what makes the goal honest, and this records why it is not optional",
          res2["ok"])


def test_observed_survives_the_carve_out():
    """The exclude side goes through the same matcher as the include side, so a carve-out
    cannot drift from the selection it carves out of."""
    w = _world(dead=("b", "c"))
    for n in ("a", "b", "c"):
        w.execute("guest_ping", {"name": n})
    sel, _ = _seams(w)
    check("EXCEPT on an observed attribute excludes the right members",
          sel({"kind": "vm", "label": "fleet", "not": {"alive": "false"}}) == ["a"])


# ── invariants that regressed silently, and now have a guard ──────────────────────────
def test_ensure_verdict_stands_over_a_tolerated_failure():
    """`asserted = True` bound a local and died with the call, so the rule three lines
    below it had NEVER fired: a grounded program that tolerated a failed call — the
    ordinary shape of a RE-RUN, where creation fails because the thing already exists —
    was reported as calls_failed anyway."""
    w = _world(names=("a",), label="fleet")
    prog = {"body": [
        {"op": "call", "tool": "create_vm", "args": {"name": "a", "os_type": "linux"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "name": "a"}, "eq": 1}}]}
    res = _run(prog, w)
    check("a failed call the world already satisfied does not sink a grounded program",
          res["ok"])
    check("but the failure is still RECORDED, not concealed", len(res["failures"]) == 1)
    bare = {"body": [{"op": "call", "tool": "create_vm",
                      "args": {"name": "a", "os_type": "linux"}}]}
    res2 = _run(bare, w)
    check("with nothing vouching for the end state, the same failure fails the run",
          not res2["ok"] and res2.get("failed") == "calls_failed")


def test_composites_evaluate():
    """`ENSURE AND(...)` returned "unevaluated shape all" and an unevaluable check counted
    as FAILED. Two causes: the ensure branch called the injected evaluator directly,
    skipping the language's own handling, and that handling lived in a closure."""
    w = _world()
    _, holds = _seams(w)
    three = {"shape": "count", "select": {"kind": "vm", "label": "fleet"}, "eq": 3}
    nine = {"shape": "count", "select": {"kind": "vm", "label": "fleet"}, "eq": 9}
    check("AND of two true checks holds",
          evaluate({"shape": "all", "of": [three, three]}, {}, holds)[0] is True)
    check("AND with one false does not",
          evaluate({"shape": "all", "of": [three, nine]}, {}, holds)[0] is False)
    check("OR with one true holds",
          evaluate({"shape": "any", "of": [nine, three]}, {}, holds)[0] is True)
    check("NOT inverts", evaluate({"shape": "not", "of": [nine]}, {}, holds)[0] is True)
    good, why = evaluate({"shape": "all", "of": [three, nine]}, {}, holds)
    check("a failed composite explains which child failed", "count is 3" in why)
    check("evaluate is reachable at module level, not trapped in run()'s closure",
          callable(evaluate))


def test_graft_binds_per_iteration_and_does_not_outlive_the_loop():
    w = _world(dead=("b",))
    prog = {"body": [
        {"op": "foreach", "select": {"kind": "vm", "label": "fleet"}, "do": [
            {"op": "call", "tool": "guest_ping", "args": {"name": "$item"},
             "graft": "answer"},
            {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
             "then": [{"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}]}]}]}
    ok, _ = validate(prog, known_names=w.names())
    check("a graft read INSIDE its own iteration validates", ok)
    res = _run(prog, w)
    check("and each member's own answer drives its own branch",
          w.vms["b"]["status"] == "stopped" and w.vms["a"]["status"] == "running")
    after = {"body": prog["body"] + [
        {"op": "ensure", "predicate": {"shape": "is", "of": "$answer.alive", "eq": True}}]}
    ok2, probs = validate(after, known_names=w.names())
    check("reading it AFTER the loop is refused", not ok2)
    check("and the refusal names loop scoping as the cause",
          probs and "does not outlive" in probs[0])
    never = {"body": [{"op": "ensure", "predicate": {"shape": "is",
                                                     "of": "$nobody.alive", "eq": True}}]}
    ok3, probs3 = validate(never)
    check("a name nothing ever bound gets the OTHER diagnosis, not the loop one",
          not ok3 and probs3 and "nothing binds it" in probs3[0])


def test_intent_is_enforced_before_anything_runs():
    w = _world()
    acting = {"body": [{"op": "new", "var": "x", "kind": "vm",
                        "args": {"os_type": "linux"}}]}
    res = _run(acting, w, intent=intent.FETCH)
    check("a program that acts under a FETCH is refused",
          not res["ok"] and res.get("failed") == "exceeds_authority")
    check("and nothing ran", res["calls"] == [])
    check("the same program is allowed under an ACHIEVE",
          _run(acting, w, intent=intent.ACHIEVE)["ok"])
    check("several markers take the HIGHEST rung, not a conflict",
          intent.declared("check golden exists, then spin up two") == intent.ACHIEVE)
    check("with nobody to ask the answer is the bottom rung",
          intent.resolve("do something vague") == intent.FETCH)


def test_a_standing_goal_below_its_granted_authority_is_raised():
    """The mirror of the check above. `violations` refuses a program reaching ABOVE its
    rung; `promote` lifts one sitting BELOW it, and only the standing goal.

    MEASURED CAUSE, 2026-07-30: granted ACHIEVE the model writes ENSURE for the goal — a
    CHECK where it was licensed to CORRECT. `execute` reports a failed non-achieve as
    `unsatisfied`, the deriver fires only for `unachieved`, so the convergence path is
    unreachable and the cell fails every run. That is para:7.
    """
    goal_pred = {"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 3}
    checked = {"body": [{"op": "ensure", "predicate": goal_pred}]}

    promoted, note = intent.promote(checked, intent.ACHIEVE)
    check("granted ACHIEVE, a standing ENSURE is raised to ACHIEVE",
          promoted["body"][0]["op"] == intent.ACHIEVE)
    check("and the rewrite is REPORTED, not silent", bool(note))
    check("the authored program is left untouched",
          checked["body"][0]["op"] == intent.ENSURE)

    check("granted only ENSURE, nothing is raised — that would be the trespass",
          intent.promote(checked, intent.ENSURE) == (checked, None))
    check("granted only FETCH either",
          intent.promote(checked, intent.FETCH) == (checked, None))

    # A PRECONDITION IS NOT THE GOAL. Promoting every check would license acting on
    # something the author meant only to verify — inferring intent from wording again.
    with_pre = {"body": [{"op": "ensure", "predicate": {"shape": "count",
                                                        "select": {"kind": "vm"}, "gte": 1}},
                         {"op": "achieve", "predicate": goal_pred}]}
    before = json.dumps(with_pre)
    check("a mid-program ensure beside a real goal is left alone",
          intent.promote(with_pre, intent.ACHIEVE)[1] is None
          and json.dumps(with_pre) == before)

    # The standing goal is the rule's other half, and both halves cost a rung to learn.
    check("an achieve outranks an ensure wherever it sits",
          intent.standing_goal(with_pre)["op"] == intent.ACHIEVE)
    last_wins = {"body": [{"op": "ensure", "predicate": {"shape": "count",
                                                         "select": {"kind": "vm"}, "gte": 1}},
                          {"op": "ensure", "predicate": goal_pred}]}
    check("among ensures the LAST wins — a precondition is not what a program was for",
          intent.standing_goal(last_wins)["predicate"] is goal_pred)
    loop_local = {"body": [{"op": "foreach", "in": "$vms", "then": [
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "name": "$item"}, "eq": 1}}]}]}
    check("a loop-local predicate cannot stand for the program",
          intent.standing_goal(loop_local) is None)
    check("and so it is not promoted either",
          intent.promote(loop_local, intent.ACHIEVE) == (loop_local, None))


def test_a_method_means_what_its_CLASS_says_it_means():
    """MEDUSA CLASSES, groundwork. `reach` was ONE predicate doing TWO jobs, which is how
    two correct implementations came to disagree: production answered per-member liveness,
    the bench answered shared topology, and #38 asked which was right. Neither — they are
    two methods, and the receiver decides.

        $web.reach()    can this machine be pinged
        $lab.reach()    are all this network's members connected AND answering

    Split by receiver, "REACH of what?" cannot be asked wrongly, because the scope IS the
    receiver. That is the argument for classes in one line.
    """
    from orchestrator.ai.planner.ir import methods

    check("both classes declare the method, from the manifest",
          methods.has("vm", "reach") and methods.has("network", "reach"))
    check("a kind that does not answer it says so", not methods.has("snapshot", "reach"))
    # WITHDRAWN FROM THE OFFERING 2026-07-31, deliberately and on measurement: putting `on`
    # in the predicate schema cost 16 runs (64/78 -> 48/78) and offering it PROPERLY
    # recovered nothing — the whole-program prompt has no headroom. The dispatch below is
    # kept because the SEMANTICS are right; only the surface was wrong.
    check("no predicate advertises a receiver while classes are withdrawn",
          methods.receivers("reach") == [] and methods.receivers("count") == [])

    w = SimWorld()
    for n in ("a", "b"):
        w.execute("create_vm", {"name": n, "os_type": "linux"})
    w.execute("create_network", {"net_name": "lab"})
    for n in ("a", "b"):
        w.execute("add_vm_to_network", {"net_name": "lab", "vm_name": n})
    _sel, holds = _seams(w)
    scope = {"lab": "lab", "web": "a"}
    net, vm = {"shape": "reach", "on": "$lab"}, {"shape": "reach", "on": "$web"}

    # UNPROBED IS NOT DEAD AND NOT ALIVE — decision 6, and it holds for both classes.
    check("an unprobed network does not reach", holds(net, scope)[0] is False)
    check("an unprobed machine does not reach", holds(vm, scope)[0] is False)
    for n in ("a", "b"):
        w.execute("guest_ping", {"name": n})
    check("once every member answered, the NETWORK reaches", holds(net, scope)[0] is True)
    check("and the MACHINE reaches on its own answer", holds(vm, scope)[0] is True)

    # The two really are different questions: a machine on no network still answers.
    lone = SimWorld()
    lone.execute("create_vm", {"name": "solo", "os_type": "linux"})
    _s, holds2 = _seams(lone)
    lone.execute("guest_ping", {"name": "solo"})
    check("a machine on NO network still reaches — that is vm.reach()",
          holds2({"shape": "reach", "on": "$x"}, {"x": "solo"})[0] is True)

    check("the renderer still shows the receiver, so a stored program stays legible",
          "$lab.reach()" in render({"body": [{"op": "ensure", "predicate": net}]}))
    ok, problems = validate({"body": [{"op": "ensure", "predicate": net}]},
                            known_names=set())
    check("and the validator refuses a method nothing advertises",
          not ok and "not a method" in problems[0])


def test_a_statement_may_not_name_what_the_program_creates_later():
    """RUNG 3, measured 2026-07-30. The author wrote, in this order:

        STORE lab = NEW network;
        add_vm_to_network(net_name: $lab, vm_name: web);
        STORE web = NEW vm(name: web, os_type: linux);

    Three statements, VALID, no complaint — and then "no VM named web" at run time. The
    `$ref` rules already cover `$lab`; a LITERAL name had nothing checking it, because a
    bare name may perfectly well refer to something the lab already holds.

    What makes it decidable is the PAIR of facts: the name is not in the world AND this
    same program creates it further down. Neither alone is a defect — naming an existing
    machine is ordinary, and creating something late is fine if nothing used it earlier.
    """
    ordered = [{"op": "new", "var": "lab", "kind": "network"},
               {"op": "new", "var": "web", "kind": "vm",
                "args": {"name": "web", "os_type": "linux"}},
               {"op": "call", "tool": "add_vm_to_network",
                "args": {"net_name": "$lab", "vm_name": "web"}}]
    backwards = [ordered[0], ordered[2], ordered[1]]

    ok, problems = validate({"body": backwards}, known_names=set())
    late = [p for p in problems if "until statement" in p]
    check("using a name the program creates later is refused", bool(late))
    check("and the objection says WHERE the creation is, so it can be moved",
          late and "statement 3" in late[0])
    check("the same statements in the right order validate",
          validate({"body": ordered}, known_names=set())[0] is True)

    # A bare name is ordinary language for something that already exists — the check must
    # not fire on it, or every program that touches the lab it was given gets rejected.
    standing = {"body": [{"op": "call", "tool": "add_vm_to_network",
                          "args": {"net_name": "core", "vm_name": "web"}}]}
    check("naming a machine the lab ALREADY holds is left alone",
          validate(standing, known_names={"web", "core"})[0] is True)


def test_a_failed_predicate_does_not_silently_swallow_the_rest_of_the_program():
    """A failed predicate returns from `run`, abandoning every statement after it — and
    nothing said so, while `derive` then closed the predicate's gap and reported the goal
    held. A green verdict over an unfinished program.

    FOUND BY A BENCHMARK, NOT BY A TEST, which is the point of writing this one. para:4:
    the author put `ACHIEVE REACH(...)` at statement 5 and the `add_label(... fleet)` loop
    at statement 6. Tightening `reach` to require probes made statement 5 fail, so the
    tagging never ran, the derived fix probed and declared success, and only the rung's own
    checker noticed the fleet was untagged.

    Costing extra calls to finish the work is the right trade: the calls take seconds and
    the thing they automate takes minutes.
    """
    w = SimWorld()          # a clean lab: nothing labelled, nothing probed
    prog = {"body": [
        {"op": "new", "var": "machines", "kind": "vm", "amount": 3,
         "args": {"os_type": "linux"}},
        {"op": "new", "var": "net", "kind": "network"},
        {"op": "foreach", "in": "$machines",
         "call": {"tool": "add_vm_to_network",
                  "args": {"net_name": "$net", "vm_name": "$item"}}},
        {"op": "achieve",
         "predicate": {"shape": "reach", "select": {"kind": "vm"}, "min": 3}},
        {"op": "foreach", "in": "$machines",
         "call": {"tool": "add_label", "args": {"name": "$item", "label": "fleet"}}},
    ]}
    sel, holds = _seams(w)
    res = run(prog, w.execute, select=sel, holds=holds, known_names=w.names(),
              consent=True, intent=intent.ACHIEVE)
    check("the predicate fails because nobody probed", res.get("failed") == "unachieved")
    check("and the abandoned tail is REPORTED, not dropped in silence",
          len(res.get("remaining") or []) == 1)
    check("the tagging genuinely did not happen", w.members("fleet") == [])

    from orchestrator.ai.planner.ir import execute as _ex
    fixed = derive(prog["body"][3]["predicate"], sel, res.get("scope"), intent.ACHIEVE)
    body = _ex.follow_up(res, fixed or [])
    check("the follow-up carries the correction AND the tail", len(body["body"]) == 3)
    # The tail is resolved against the scope the aborted run held — `params` cannot express
    # a bound set, since every declarable type is a scalar.
    check("the tail's set reference is resolved to its members, not left dangling",
          body["body"][-1]["in"] == ["machines1", "machines2", "machines3"])
    res2 = run(body, w.execute, select=sel, holds=holds, known_names=w.names(),
               consent=True, intent=intent.ACHIEVE)
    check("the follow-up runs clean", res2.get("ok") is True)
    check("the work that was skipped has now happened",
          sorted(w.members("fleet")) == ["machines1", "machines2", "machines3"])
    check("and the goal it failed on now holds",
          holds({"shape": "reach", "select": {"kind": "vm"}, "min": 3}, {})[0] is True)


def test_an_ungrounded_program_asks_first():
    w = _world()
    acting = {"body": [{"op": "new", "var": "x", "kind": "vm",
                        "args": {"os_type": "linux"}}]}
    sel, holds = _seams(w)
    res = run(acting, w.execute, select=sel, holds=holds, known_names=w.names())
    check("a program that acts and vouches for nothing is refused pending consent",
          not res["ok"] and res.get("failed") == "ungrounded")
    check("and it is refused BEFORE the first call — a question asked halfway through "
          "is a notification", res["calls"] == [])
    # The question names the SOUNDNESS RULE rather than the resource: a program needs at
    # least one verdict, and FETCH answers with data while actions answer with nothing.
    # Naming the rule is what makes the question answerable — it says which of the two
    # words is missing, instead of restating what the operator already asked for.
    q = consent.question(acting) or ""
    check("the question names the missing VERDICT", "VERDICT" in q)
    check("and offers both words that could supply one", "ENSURE" in q and "ACHIEVE" in q)
    check("the survey counts the acting statements that prompted it",
          consent.survey(acting) == {"acts": 1, "asserts": 0, "grounded": False})


def test_derivation_closes_a_countable_gap():
    w = _world(names=("a", "b", "c", "d", "e", "f"), label="prod")
    sel, _ = _seams(w)
    pred = {"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 3}
    steps = derive(pred, sel)
    check("six exist and three are wanted, so the harness computes a removal", bool(steps))
    check("it removes exactly the surplus",
          steps and len(steps[0]["in"]) == 3
          and steps[0]["call"]["tool"] == "remove_label")
    check("it acts on a deterministic slice, so a re-derivation is idempotent",
          steps and steps[0]["in"] == sorted(steps[0]["in"]))
    check("a satisfied predicate derives [] — 'nothing needs doing'",
          derive({"shape": "count", "select": {"kind": "vm", "label": "prod"},
                  "gte": 2}, sel) == [])
    check("an unclosable shape derives None, which is NOT the same as []",
          derive({"shape": "disjoint", "sets": ["$a", "$b"]}, sel) is None)


def test_amount_creates_the_shortfall_and_never_a_negative():
    w = _world(names=("a", "b"), label="fleet")
    prog = {"body": [
        {"op": "fetch", "var": "have", "count": {"kind": "vm", "label": "fleet"}},
        {"op": "new", "var": "more", "kind": "vm", "amount": {"minus": [5, "$have"]},
         "args": {"os_type": "linux"}},
        {"op": "achieve", "predicate": {"shape": "count",
                                        "select": {"kind": "vm"}, "gte": 5}}]}
    res = _run(prog, w)
    check("FETCH + AMOUNT creates only the difference", res["ok"] and len(w.vms) == 5)
    w2 = _world(names=tuple("abcdefg"), label="fleet")
    res2 = _run(prog, w2)
    check("the SAME program against an already-satisfied world creates nothing",
          res2["ok"] and len(w2.vms) == 7)
    check("and it made no create call at all",
          not [c for c in w2.calls if c["tool"] == "create_vm"])


def test_a_set_cannot_sit_where_one_value_belongs():
    """Rung 9, 2026-07-27. `STORE vms = FETCH SELECT vm WHERE ...` binds the NAMES; the
    next line wrote `ENSURE REACH(SELECT vm WHERE label = '$vms')`. It validated, and
    `refs.resolve` correctly kept the list type — that is what makes `IN $vms` iterate —
    so a list reached `f["label"] not in {...}`, which cannot hash it. The TypeError took
    down the whole 13-rung run at rung 9, losing rungs 10-13 with it."""
    prog = {"body": [
        {"op": "fetch", "var": "vms", "select": {"kind": "vm", "label": "mesh"}},
        {"op": "ensure", "predicate": {"shape": "reach",
                                       "select": {"kind": "vm", "label": "$vms"},
                                       "min": 3}}]}
    ok, probs = validate(prog)
    check("a name bound by FETCH SELECT is refused in a scalar filter", not ok)
    check("and the refusal says it holds the members, not a shared attribute",
          probs and "holds the members" in probs[0])
    # The remedy changed when membership landed: before, the only construct that took a
    # set was `foreach in`, so that is what the message named. Now a predicate can hold
    # one, and the message should say so — the objection is an interface, and it has to
    # point at what the language can actually do TODAY.
    check("and it names the construct that DOES take a set",
          probs and "INCLUDE" in probs[0])
    counted = {"body": [
        {"op": "fetch", "var": "have", "count": {"kind": "vm", "label": "mesh"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "label": "mesh"},
                                       "eq": "$have"}}]}
    ok2, _ = validate(counted)
    check("FETCH COUNT binds a NUMBER and stays legal — the distinction is the point",
          ok2)
    literal = {"body": [{"op": "foreach",
                         "select": {"kind": "vm", "name": ["n1", "n2"]},
                         "call": {"tool": "stop_vm", "args": {"name": "$item"}}}]}
    ok3, probs3 = validate(literal)
    check("a LITERAL list in a filter is refused too", not ok3)
    check("with the other diagnosis — say membership, not a bare list",
          probs3 and "INCLUDE" in probs3[0] and "in" in probs3[0])
    made = {"body": [
        {"op": "new", "var": "box", "kind": "vm", "amount": 3,
         "args": {"os_type": "linux"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "name": "$box"},
                                       "eq": 3}}]}
    ok4, _ = validate(made)
    check("NEW with an amount above one binds a set, and is caught the same way",
          not ok4)


def test_the_seam_does_not_raise_on_a_non_scalar_filter():
    """The validator refuses it statically, but a value can still arrive non-scalar at run
    time — a parameter supplied at invocation is not knowable in advance. A seam that
    crashes destroys the measurement around it."""
    w = _world()
    sel, _ = _seams(w)
    try:
        got = sel({"kind": "vm", "label": ["fleet", "other"]})
        ok = got == []
    except Exception:
        ok = False
    check("a list-valued filter matches nobody instead of raising", ok)


def test_the_authors_own_name_wins_over_the_minted_one():
    """Rung 8, both columns, 2026-07-27. The model wrote
    `STORE core_net = NEW network(net_name: core)` — correct — and the executor built
    `{**extra, key_arg: minted}`, so the resource was created as `core_net` and every
    later reference to `core` failed against a world that never contained it. Minting
    exists to supply a name when nobody said one, not to overrule someone who did."""
    w = SimWorld()
    sel, holds = _seams(w)
    run({"body": [{"op": "new", "var": "core_net", "kind": "network",
                   "args": {"net_name": "core"}}]},
        w.execute, select=sel, holds=holds, consent=True)
    check("an explicitly supplied key names the resource", sorted(w.nets) == ["core"])
    w2 = SimWorld()
    sel2, holds2 = _seams(w2)
    res = run({"body": [{"op": "new", "var": "lab", "kind": "network"}]},
              w2.execute, select=sel2, holds=holds2, consent=True)
    check("with no name supplied it still mints from the variable",
          sorted(w2.nets) == ["lab"])
    check("and the variable binds the name that was actually used",
          res["scope"]["lab"] == "lab")
    w3 = SimWorld()
    sel3, holds3 = _seams(w3)
    res3 = run({"body": [{"op": "new", "var": "x", "kind": "vm", "amount": 3,
                          "args": {"name": "node", "os_type": "linux"}}]},
               w3.execute, select=sel3, holds=holds3, consent=True)
    check("several resources suffix the SUPPLIED name, not the variable",
          sorted(w3.vms) == ["node1", "node2", "node3"]
          and res3["scope"]["x"] == ["node1", "node2", "node3"])


def test_an_attribute_with_a_closed_vocabulary_is_policed():
    """Rung 5 wrote `status = 'not running'`, matched nobody, ran ZERO calls and reported
    ok — a program that looks right, validates, and does nothing. `status` is running or
    stopped and the schema offered it as a bare string."""
    check("values_for answers for a registry attribute",
          config.values_for("vm", "status") == ["running", "stopped"])
    check("and for an observed one, from the same call",
          config.values_for("vm", "alive") == list(config.OBSERVED_VALUES))
    check("an open attribute answers None rather than an empty set",
          config.values_for("vm", "label") is None)
    check("aliases resolve before the lookup — `os` is `os_type`",
          config.canonical("vm", "os") == "os_type"
          and config.canonical("vm", "tag") == "label")
    ok, probs = validate({"body": [{"op": "foreach",
                                    "select": {"kind": "vm", "status": "not running"},
                                    "call": {"tool": "launch_vm",
                                             "args": {"name": "$item"}}}]})
    check("an invented status is refused", not ok)
    check("and the refusal names the vocabulary",
          probs and "running or stopped" in probs[0])
    ok2, _ = validate({"body": [{"op": "foreach",
                                 "select": {"kind": "vm", "status": "stopped"},
                                 "call": {"tool": "launch_vm",
                                          "args": {"name": "$item"}}}]})
    check("a legal status still validates", ok2)


def test_the_objection_names_the_statement_not_the_tool():
    """Rungs 4 and 13, paraphrase. "create_vm also requires 'os_type'" is a sentence about
    a TOOL, and the model did what it asks — added a separate create_vm call beside the
    NEW, creating everything twice — then the repair loop re-rejected the untouched NEW
    twice more and gave up. The author writes Medusa; the objection must too."""
    ok, probs = validate({"body": [{"op": "new", "var": "machines", "kind": "vm",
                                    "amount": 5}]})
    check("a NEW missing a required creator argument is refused", not ok)
    check("and the objection is phrased as NEW, not as the tool",
          probs and probs[0].startswith("statement 1: NEW vm"))
    check("it shows the shape to write", probs and "NEW vm(os_type: ...)" in probs[0])
    check("and says outright not to add a separate call",
          probs and "do NOT add a separate create_vm call" in probs[0])


def test_a_loop_inside_a_loop_is_refused():
    """The language has ONE loop variable, so an inner foreach shadows the outer member
    and the nesting cannot express anything the inner loop alone does not — while
    multiplying the work by the outer set. Rungs 4 and 13 issued 50 pings for 5 machines
    this way, 66 calls in total, and it validated."""
    prog = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
        {"op": "foreach", "in": "$vms",
         "call": {"tool": "guest_ping", "args": {"name": "$item"}}}]}]}
    ok, probs = validate(prog)
    check("a nested foreach is refused", not ok)
    check("and the reason names the shadowed loop variable",
          probs and "rebinds $item" in probs[0])
    check("and points at the construct that DOES relate a whole set",
          probs and "REACH" in probs[0])
    # AT ANY DEPTH. The first version scanned only the loop's direct children, so rung 13
    # buried a foreach inside an `if` inside the body and ran 23 calls through it.
    buried = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
        {"op": "if", "cond": {"shape": "count", "select": {"kind": "vm"}, "gte": 1},
         "then": [{"op": "foreach", "in": "$vms",
                   "call": {"tool": "guest_ping", "args": {"name": "$item"}}}]}]}]}
    ok_b, probs_b = validate(buried)
    check("a foreach buried inside an if inside the body is refused too", not ok_b)
    check("with the same reason", probs_b and "rebinds $item" in probs_b[0])
    flat = {"body": [
        {"op": "foreach", "select": {"kind": "vm"},
         "call": {"tool": "guest_ping", "args": {"name": "$item"}}},
        {"op": "foreach", "select": {"kind": "vm"},
         "call": {"tool": "stop_vm", "args": {"name": "$item"}}}]}
    ok2, _ = validate(flat)
    check("two loops one after the other are fine", ok2)


def test_not_accepts_the_shape_its_own_schema_asks_for():
    """Three parts disagreed about `NOT`'s operand. The manifest says arity one; the
    SCHEMA offered `of` as an array for every non-value arity, so the decoder wrote
    `[{...}]` as instructed; the executor coerced a list and ran it; the validator refused
    and the renderer printed `<not a predicate: [...]>`. Rung 8 (literal) and rung 5
    (paraphrase) both died on programs the runtime would have executed correctly."""
    inner = {"shape": "count", "select": {"kind": "vm"}, "eq": 0}
    listed = {"body": [{"op": "if", "cond": {"shape": "not", "of": [inner]},
                        "then": [{"op": "call", "tool": "stop_vm",
                                  "args": {"name": "a"}}]}]}
    bare = {"body": [{"op": "if", "cond": {"shape": "not", "of": inner},
                      "then": [{"op": "call", "tool": "stop_vm",
                                "args": {"name": "a"}}]}]}
    check("a one-element list under NOT validates", validate(listed)[0])
    check("a bare object under NOT validates too", validate(bare)[0])
    check("and both render the same readable line",
          render(listed) == render(bare) and "NOT(COUNT(SELECT vm) = 0)" in render(listed))
    w = _world()
    _, holds = _seams(w)
    check("the executor agrees with both",
          evaluate({"shape": "not", "of": [inner]}, {}, holds)[0]
          == evaluate({"shape": "not", "of": inner}, {}, holds)[0])
    check("AND/OR still demand two or more — arity `many` is unchanged",
          not validate({"body": [{"op": "ensure",
                                  "predicate": {"shape": "all", "of": [inner]}}]})[0])


def test_an_empty_then_is_told_it_is_an_unstated_inversion():
    """Rung 11, measured 2026-07-28. The author's first draft is the same in every
    phrasing and its INTENT IS CORRECT — `if alive then {} else {stop}` reads "if it
    answers do nothing, otherwise stop it", which is exactly the goal. It fails on SHAPE,
    twice over: `then` is left empty, and `else` is written as a sibling STATEMENT.

    Both objections used to say only what was malformed. "`then` is a list of statements,
    got []" gave the repair loop nothing to go on, so it guessed — it folded the else body
    up into `then` and left `cond` alone, and a correct intent became a program that
    stopped the machines that DID answer. A repair that silently reverses what a program
    means is worse than one that gives up, and the objection is the only thing standing
    between the two.

    So both messages name the ROUTE. The inversion is phrased as an IDENTITY rather than a
    prohibition on purpose: a rule has to be remembered, an identity can be re-derived, and
    it carries its own reason — an empty THEN means the condition you wrote is not the
    condition you care about.
    """
    stop = {"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}
    cond = {"shape": "is", "of": "$answer.alive", "eq": True}

    empty_then = {"body": [{"op": "if", "cond": cond, "then": [], "else": [stop]}]}
    ok, problems = validate(empty_then)
    check("an empty `then` is refused", not ok)
    check("and the objection names the identity, not just the malformation",
          any("IF NOT(X) THEN" in p for p in problems))
    check("it also offers the shorthand for a boolean IS",
          any("eq to false" in p for p in problems))

    check("and every form is told the PRINCIPLE, not an edit",
          all("ONE decision" in p and "only the side that ACTS" in p
              for p in problems if "`then` is empty" in p))

    # THE THIRD FORM, AND THE ONE THAT MATTERS MOST. Taught to invert, the author kept the
    # habit and changed the spelling: `IF X {}` followed by `IF NOT(X) {work}` — one
    # if/else written as two statements, with the empty positive branch kept as its "other
    # half". Telling it to DELETE the empty one would be the same checklist thinking that
    # produced it. The objection names the statement that IS the whole decision, so what
    # the author learns is that the case never needed writing.
    split = {"body": [
        {"op": "call", "tool": "guest_ping", "args": {"name": "web"}, "graft": "answer"},
        {"op": "if", "cond": cond, "then": []},
        {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
         "then": [{"op": "call", "tool": "stop_vm", "args": {"name": "web"}}]}]}
    ok_s, problems_s = validate(split)
    check("the split form is refused too", not ok_s)
    check("and the objection NAMES the statement that is the real decision",
          any("Statement 3 already checks the opposite" in p for p in problems_s))
    check("and says there was never another half to write",
          any("no other half" in p for p in problems_s))
    check("it does NOT tell the author to delete anything",
          not any("delete" in p.lower() for p in problems_s))

    # A LONE EMPTY IF, with no twin anywhere, is a different sentence — there is no
    # statement to point at, so pointing at one would be a false accusation.
    hollow = {"body": [{"op": "if", "cond": cond, "then": []}]}
    ok_h, problems_h = validate(hollow)
    check("an if with no branches at all is refused too", not ok_h)
    check("and is told no decision is being made, with no twin invented",
          any("no decision being made" in p for p in problems_h)
          and not any("already checks the opposite" in p for p in problems_h))

    # TWO EMPTY IFS ARE NOT A MISPLACED DECISION. The twin only counts when it ACTS —
    # otherwise the objection would name a statement that is just as empty as this one.
    both_empty = {"body": [
        {"op": "if", "cond": cond, "then": []},
        {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
         "then": []}]}
    check("an empty twin is not offered as the real decision",
          not any("already checks the opposite" in p
                  for p in validate(both_empty)[1]))

    # THE WORD IS REAL, THE PLACE IS WRONG. Listing the legal ops is the right answer to an
    # invented word and the wrong one here: it sends the author hunting for a different
    # construct instead of telling it where the one it already wants lives.
    sibling = {"body": [{"op": "if", "cond": cond, "then": [stop]},
                        {"op": "else", "do": [stop]}]}
    ok2, problems2 = validate(sibling)
    check("`else` as a statement of its own is refused", not ok2)
    check("and is told it is a FIELD of the if above, not an op",
          any("FIELD of the `if`" in p for p in problems2))
    check("a genuinely invented op still gets the plain list of legal ones",
          any("expected one of" in p
              for p in validate({"body": [{"op": "elsif", "do": [stop]}]})[1]))

    # BOTH LEGAL SPELLINGS OF THE INVERSION ALREADY WORK — the model is not missing the
    # concept, only the shape. Given a synonym-mutated wording of this same goal it wrote
    # `eq: false` unprompted and passed the rung.
    def _loop(branch):
        """Rung 11's own shape: probe each member, then branch on that member's answer."""
        return {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
            {"op": "call", "tool": "guest_ping", "args": {"name": "$item"},
             "graft": "answer"}, branch]}]}

    check("NOT(...) is a legal cond — it composes over every predicate",
          validate(_loop({"op": "if", "cond": {"shape": "not", "of": cond},
                          "then": [stop]}))[0])
    check("and flipping eq says the same thing",
          validate(_loop({"op": "if",
                          "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
                          "then": [stop]}))[0])

    # THE RUNTIME NEVER HAD THIS RESTRICTION. execute.py picks its branch with
    # `_block(st.get("then" if good else "else") or [])`, so an empty branch simply runs
    # nothing — only the schema and the validator forbid writing it. Same shape as the
    # ACHIEVE ordering rules dropped in 62160da, and worth pinning so the next reader knows
    # this is a TEACHING choice about what a program should SAY, not a capability gap.
    import inspect
    from orchestrator.ai.planner.ir import execute as _execute
    check("the runtime tolerates an absent branch, so this is a language choice",
          'st.get("then" if good else "else") or []' in inspect.getsource(_execute))


def test_the_sanitiser_drops_only_what_could_never_run():
    """Artifacts come off before the program is judged — and only artifacts.

    The measured case is rung 11: `IF IS($answer.alive) = true { }` beside a second `if`
    that does the work. That cond is byte-identical to the ONE `if` among the few-shot
    examples, down to the variable, the field and the polarity, none of which appear in the
    goal. It is the example reproduced with nothing that fits in it — one-example
    generalisation, whose residue a compiler drops without comment.

    Everything here guards the BOUNDARY rather than the feature, because the objection to
    building this at all was that a cleaner could hide a reasoning fault, and the boundary
    is the whole answer to that objection.
    """
    from orchestrator.ai.planner.ir.sanitize import sanitize, kinds, severity

    stop = {"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}
    ping = {"op": "call", "tool": "guest_ping", "args": {"name": "$item"},
            "graft": "answer"}
    alive = {"shape": "is", "of": "$answer.alive", "eq": True}
    dead_if = {"op": "if", "cond": alive, "then": []}
    work_if = {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
               "then": [stop]}

    draft = {"body": [{"op": "foreach", "select": {"kind": "vm"},
                       "do": [ping, dead_if, work_if]}]}
    cleaned, removed = sanitize(draft)
    check("the dead branch is dropped", len(removed) == 1)
    check("and named by kind and severity",
          removed[0]["kind"] == "dead_if" and removed[0]["severity"] == "benign")
    check("the path is spelled the way validate spells it",
          removed[0]["where"] == "statement 1 (foreach body) → statement 2")
    check("what remains is the program that was always meant",
          cleaned["body"][0]["do"] == [ping, work_if])
    check("REJECTED BEFORE, VALID AFTER — the artifact was the only fault",
          not validate(draft)[0] and validate(cleaned)[0])

    # THE AUTHOR'S ORIGINAL IS EVIDENCE. The artifact rate is measured off the raw draft,
    # so a pass that edited in place would destroy the thing it exists to count.
    check("the draft is not mutated",
          draft["body"][0]["do"] == [ping, dead_if, work_if])

    # NEVER REWRITES A CHECK — the line between a compiler pass and a correction. An
    # unstated inversion is a claim about what the program MEANS, so it stays for the
    # validator to object to rather than being quietly edited into meaning it.
    inversion = {"body": [{"op": "if", "cond": alive, "then": [], "else": [stop]}]}
    out, removed2 = sanitize(inversion)
    check("an if/else inversion is left exactly as written",
          out == inversion and not removed2)
    check("so the validator's objection still fires",
          any("ONE decision" in p for p in validate(inversion)[1]))

    # NEVER EMPTIES A BLOCK — otherwise a dead statement is traded for a validation error
    # about a block the author did fill in.
    lone = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [dead_if]}]}
    out3, removed3 = sanitize(lone)
    check("a block that would be emptied is left alone", out3 == lone and not removed3)

    # A HEALTHY PROGRAM IS UNTOUCHED. Measured across a 31-program corpus: 21 valid
    # programs, zero altered, zero outcomes changed.
    healthy = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [ping, work_if]}]}
    check("a valid program comes through byte-identical", sanitize(healthy) == (healthy, []))

    # A KIND IS EARNED. Two candidates were REFUSED on measurement rather than taste:
    # repeated_loop_same_set fired 6 times over 31 programs with 5 PASSING, and its
    # replacement repeated_identical_call never fired at all.
    # KINDS ARE EARNED ONE AT A TIME. `dead_if` came from rung 11; `trailing_prose` from
    # lit:7 and lit:13 at six runs of six. Two candidates were REFUSED on measurement in
    # between — repeated_loop_same_set fired 6 times over 31 programs with 5 PASSING, and
    # its replacement repeated_identical_call never fired at all. The count is asserted so
    # that adding a third has to come here and state its evidence.
    check("exactly the two measured kinds are defined",
          sorted(kinds()) == ["dead_if", "trailing_prose"])
    check("every kind carries its evidence",
          all(k.get("evidence") for k in kinds().values()))
    check("an unknown kind is unclassified, never assumed benign",
          severity("something_new") == "unclassified")


def test_the_sanitiser_reaches_the_reply_not_just_the_program():
    """THE INSTRUMENT'S REACH USED TO STOP ONE LAYER SHORT.

    `sanitize()` takes a parsed program. Trailing prose kills the parse — so the one
    instrument whose job is removing model residue could never see the most common residue
    there is. Measured: lit:7 and lit:13, six runs of six, each a COMPLETE schema-shaped
    object followed by a sentence explaining the fix. `json.loads` demands the whole string
    be one value, so byte 815 discarded bytes 1-814 and the answer was recorded as though
    the model had said nothing. Rung 11's discarded repair was valid and passed in 6 calls.

    THIS KIND IS DIFFERENT FROM dead_if, and the difference is why `symptom_of` exists.
    `dead_if` is legal JSON and legal schema, merely useless. Prose after the closing brace
    is a SCHEMA VIOLATION — `type: object` has no production permitting it — so it is
    entirely safe to REMOVE while its RATE says the constrained decoder is not holding.
    Severity and symptom answer different questions and one field cannot hold both.
    """
    from orchestrator.ai.planner.ir.sanitize import (kinds, sanitize_text, severity,
                                                     symptom_of)

    body = '{"body": [{"op": "call", "tool": "list_vms", "args": {}}]}'
    prose = "\n\nI fixed the NEW statement to include 'os_type' in its arguments."

    prog, removed = sanitize_text(body + prose)
    check("the program survives the prose", prog == json.loads(body))
    check("and the prose is REMOVED, not ignored", len(removed) == 1)
    check("named as its own kind", removed[0]["kind"] == "trailing_prose")
    check("benign — it was never part of the program",
          removed[0]["severity"] == "benign")
    check("but flagged as a symptom of the CHANNEL",
          removed[0]["symptom_of"] == "channel" == symptom_of("trailing_prose"))
    check("and the text is kept as evidence, not discarded",
          "os_type" in removed[0]["text"])

    # A CLEAN REPLY IS UNTOUCHED, and reports nothing — a pass that invented work would
    # make its own rate meaningless.
    check("a clean reply yields no artifact", sanitize_text(body) == (json.loads(body), []))
    check("leading whitespace is not an artifact",
          sanitize_text("  \n" + body)[1] == [])

    # A REPLY THAT IS NOT JSON AT ALL IS A CHANNEL FAILURE, NOT AN ARTIFACT. The caller has
    # to be able to tell "the model answered and chattered" from "the model emitted
    # garbage" — they have different owners, and collapsing them is what hid a correct
    # repair inside a bucket labelled "no result" for a day.
    for bad in ("not json at all", '{"body": [{"op":', ""):
        try:
            sanitize_text(bad)
            check(f"non-JSON {bad[:12]!r} raises rather than being cleaned", False)
        except Exception:
            check(f"non-JSON {bad[:12]!r} raises rather than being cleaned", True)

    # SEVERITY AND SYMPTOM ARE INDEPENDENT AXES.
    check("dead_if is benign and symptom of nothing",
          severity("dead_if") == "benign" and symptom_of("dead_if") is None)
    check("both kinds still carry their evidence",
          all(k.get("evidence") for k in kinds().values()))


def test_achieve_may_change_the_world_and_ensure_may_not():
    """WHAT SEPARATES THE TWO WORDS, and it is the whole of it. The operator: *"ENSURE is
    a sanity check, no world change. ACHIEVE is a world change."*

    `derive()` closed a count gap by adding or removing LABELS and refused to touch
    resources at all — "creating them is a bigger decision than closing a gap, so leave it
    to the model". That was the wrong axis. ACHIEVE means MAKE SURE, and making sure is
    SYMMETRIC: too few is closed by creating, too many by removing. The operator, arriving
    at it in two steps: *"it's allowed to create resources, not delete"*, then *"creation
    and modifications and even deletions are allowed in achieve, given correct intent...
    it CAN CHANGE the world to meet the goal, that's the correction part of it."*

    SO THE GATE IS THE INTENT, NEVER THE SIGN OF THE DIFFERENCE. Under `fetch` or `ensure`
    nothing may act; under `achieve` the world may be corrected either way. An UNSTATED
    intent stays conservative, because a caller that has not said what the operator wants
    has not established that removal was asked for.

    AND THIS IS NOT WHERE DELETION IS MADE SAFE — which is what I had it doing. A derived
    call meets consent, the contract tier and delete_vm's double confirmation on its way to
    the world exactly as an authored one does. Refusing here duplicated a judgement that
    already has an owner, and broke the language's own promise that an ACHIEVE is a legal
    way to state a goal and let the harness plan it.

    It also repairs a promise the prompt makes and the code did not keep: "a program that
    is nothing but an achieve is a legal way to state a goal and let the harness plan it"
    was true for labels and false for existence, so an end-state goal against an empty lab
    came back `unachieved` with nothing derived.

    WHERE THE never-guess LINE FALLS. create_vm REQUIRES os_type, which no predicate
    carries. Inventing one per call would be the schema-withholding defect in reverse —
    the model wrote `status = 'not running'` precisely because nothing declared what
    status could be. A value in `create_defaults` is not that: declared once, identical on
    every derivation, and visible to anyone reading the manifest. The operator: *"or it is
    the intended"*. A kind with a required argument nobody declared cannot be derived into
    existence and the author is asked instead.
    """
    from orchestrator.ai.planner.ir.derive import derive as _derive
    from orchestrator.ai.planner.ir.derive import _creator_args

    def seams(vms=()):
        w = SimWorld()                 # EMPTY — _world() seeds three, which is not the case
        for name in vms:
            w.execute("create_vm", {"name": name, "os_type": "linux"})
        return w, _seams(w)[0]

    # EMPTY LAB, bare existence count -> create the shortfall.
    _w, sel = seams()
    out = _derive({"shape": "count", "select": {"kind": "vm"}, "gte": 5}, sel, {})
    check("an unmet existence count now derives", out is not None and len(out) == 1)
    check("as a counted NEW of the right kind",
          out[0]["op"] == "new" and out[0]["kind"] == "vm" and out[0]["amount"] == 5)
    check("carrying the DECLARED creator argument, not an invented one",
          out[0]["args"] == {"os_type": "linux"})

    # A LABELLED count creates AND labels — creating a machine does not label it.
    out = _derive({"shape": "count", "select": {"kind": "vm", "label": "fleet"},
                          "gte": 5}, sel, {})
    check("a labelled count creates and then labels", len(out) == 2)
    check("and labels what it just made, by reference",
          out[1]["op"] == "foreach" and out[1]["in"] == "$_derived")

    # PARTIAL: three exist unlabelled, five wanted -> label 3, create 2.
    _w, sel3 = seams(["a", "b", "c"])
    out = _derive({"shape": "count", "select": {"kind": "vm", "label": "fleet"},
                          "gte": 5}, sel3, {})
    made = [st for st in out if st["op"] == "new"]
    check("existing resources are used before new ones are made",
          made and made[0]["amount"] == 2)

    # DOWNWARD IS SYMMETRIC, AND THE GATE IS INTENT — not the sign of the difference.
    # The operator: "creation and modifications and even deletions are allowed in achieve,
    # given correct intent... it CAN CHANGE the world to meet the goal, that's the
    # correction part of it." Refusing here treated derive() as the safety mechanism,
    # which it is not: a derived call meets consent, the contract tier and delete_vm's
    # double confirmation exactly as an authored one does.
    from orchestrator.ai.planner.ir import intent as _intent
    _w, sel5 = seams(["a", "b", "c", "d", "e"])
    pred_down = {"shape": "count", "select": {"kind": "vm"}, "eq": 2}
    out = _derive(pred_down, sel5, {}, _intent.ACHIEVE)
    check("under ACHIEVE a surplus is corrected downward", out is not None)
    check("by the kind's DECLARED destroyer, on the surplus only",
          out[0]["call"]["tool"] == "delete_vm" and len(out[0]["in"]) == 3)
    check("choosing deterministically, so a re-derivation is the same program",
          out == _derive(pred_down, sel5, {}, _intent.ACHIEVE))
    check("under ENSURE nothing may act, so it derives nothing",
          _derive(pred_down, sel5, {}, _intent.ENSURE) is None)
    check("and an UNSTATED intent is conservative — silence is not permission",
          _derive(pred_down, sel5, {}) is None)
    # Dropping a LABEL is not deleting a resource, so that path is untouched.
    for n in ("a", "b", "c"):
        _w.execute("add_label", {"name": n, "label": "prod"})
    out = _derive({"shape": "count", "select": {"kind": "vm", "label": "prod"},
                          "eq": 1}, _seams(_w)[0], {})
    check("but dropping a surplus LABEL still derives",
          out and out[0]["call"]["tool"] == "remove_label")

    # THE UNDECLARED CASE STAYS EXPLICIT.
    check("a kind with a declared default can be derived",
          _creator_args("vm") == {"os_type": "linux"})
    check("a kind needing nothing extra derives with no args",
          _creator_args("network") == {})
    check("and an undeclared required argument refuses",
          _creator_args("snapshot") is None)

    # IDEMPOTENT: the same gap derives the same program, so a re-run is a no-op rather
    # than a second creation — which is the promise this module's own docstring makes.
    _w, sel0 = seams()
    a = _derive({"shape": "count", "select": {"kind": "vm"}, "gte": 5}, sel0, {})
    b = _derive({"shape": "count", "select": {"kind": "vm"}, "gte": 5}, sel0, {})
    check("deriving twice from one world gives one answer", a == b)


def test_new_is_for_what_does_not_exist_yet():
    """THE MOST EXPENSIVE DEFECT IN THE LADDER, and it is world blindness.

    Shown a lab holding five labelled machines and asked to USE five, the author writes
    `NEW AMOUNT(5)` and ends with ten. The CURRENT STATE block is read as background
    rather than as input. The prompt has said "read first, then act on the difference"
    under `fetch` since the op existed and it does not land there — so the objection is
    raised at the STATEMENT where the mistake is made, and it names the count.

    The operator's rule, which is an order of operations rather than a prohibition: *"NEW
    means creation of NEW objects. Only use when asked TO CREATE new objects, OR when
    objects don't exist. If the user intent is NOT to create but rather use existing
    resources, USE FETCH. If nothing comes back from said fetch then your fallback is
    creation."*

    NARROW BY CONSTRUCTION, because a rule that fires on honest programs gets ignored:
    only a COUNTED creation, only of a kind the lab already holds, never a copy, and never
    when the program read first. `from` names an existing resource, so copying one is
    precisely the case where creation IS the request.
    """
    blind = {"body": [{"op": "new", "var": "vms", "kind": "vm", "amount": 5,
                       "args": {"os_type": "linux"}}]}

    ok, problems = validate(blind, census={"vm": 5})
    check("a counted creation into a full lab is refused", not ok)
    check("and the objection names what is already there",
          any("already holds 5 vm" in p for p in problems))
    check("it explains AMOUNT means MORE, not a total",
          any("MORE" in p and "in total" in p for p in problems))
    # LENGTH IS PART OF THE CONTRACT HERE, not a style note. At ~370 characters this
    # objection made the repair call return NOTHING — 6 replies of 6, empty — and at 163
    # it came back 2 of 3. The probe's own header records the same effect from the other
    # direction: "a richer prompt -> fewer calls". An objection the author cannot answer
    # is worth less than no objection at all, because it costs the round as well.
    check("and it stays short enough to be answerable",
          all(len(p) < 200 for p in problems if "already holds" in p))
    check("and offers both routes — read the difference, or state the end state",
          any("FETCH" in p and "ACHIEVE COUNT" in p for p in problems))

    check("the same program in an EMPTY lab is fine", validate(blind, census={})[0])
    check("reading first clears it",
          validate({"body": [{"op": "fetch", "var": "have", "count": {"kind": "vm"}}]
                            + blind["body"]}, census={"vm": 5})[0])
    check("a COPY is untouched — `from` is the case where creating IS the request",
          validate({"body": [{"op": "new", "var": "c", "kind": "vm", "amount": 3,
                              "from": "golden"}]},
                   census={"vm": 5}, known_names={"golden"})[0])
    check("a single named creation is left to the duplicate rule",
          validate({"body": [{"op": "new", "var": "b", "kind": "vm",
                              "args": {"os_type": "linux"}}]}, census={"vm": 5})[0])
    check("and with NO census the check cannot fire at all",
          validate(blind)[0])

    # THE CENSUS IS PER KIND. A lab full of networks says nothing about creating vms.
    check("a full lab of another kind does not accuse this one",
          validate(blind, census={"network": 9})[0])

    # THE BENCH AND THE VALIDATOR MUST COUNT THE SAME THINGS, or the rule fires in one
    # place and not the other.
    w = _world()
    check("the world's census is keyed by the manifest's kinds",
          set(w.census()) <= set(config.KINDS) and w.census()["vm"] == 3)


def test_every_few_shot_example_is_a_valid_program():
    """A worked example is the strongest teaching signal there is — the shots beat the
    prompt whenever they disagree, which is how rung 7 was taught the old single-word
    ENSURE semantics while the prompt taught the split. An invalid shot teaches an invalid
    language, silently, to every program authored afterwards."""
    from tests.bench.author_probe import SHOTS
    for goal, prog in SHOTS:
        ok, probs = validate(prog)
        check(f"shot validates: {goal[:46]}", ok or f"{probs[:1]}")
    # No assertion about WHICH constructs appear. A shot for FETCH was added on the
    # reasoning that it is the one construct never demonstrated, measured over both
    # columns, and found to make things worse — rung 13 paraphrase went PASS -> FAIL and
    # rung 7 picked up three junk VMs from copying the shot's shape. The reasoning behind
    # the shot set is in author_probe.SHOTS; pinning the set here would turn a measured
    # judgement into a tripwire against re-measuring it.
    check("the shot set is non-empty and every goal is distinct",
          len(SHOTS) > 0 and len({g for g, _ in SHOTS}) == len(SHOTS))


def test_the_grader_finds_a_verdict_nested_in_a_loop():
    """Rung 9's only verdict was an ENSURE inside a foreach body. The probe searched the
    TOP level for it, found none, and `_goal_holds()` then returned True unconditionally —
    so its corrective program was reported `goal=HOLDS` while the rung checker said FAIL.
    A grader that cannot find the program's verdict is not grading it."""
    prog = {"body": [{"op": "foreach", "in": ["n1", "n2"], "do": [
        {"op": "call", "tool": "guest_ping", "args": {"name": "$item"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm"}, "gte": 3}}]}]}
    flat = consent._walk(prog["body"])
    found = next((st["predicate"] for st in reversed(flat)
                  if st.get("op") == "ensure"), None)
    check("_walk reaches a verdict inside a loop body", found is not None)
    check("and it is the right one", found == {"shape": "count",
                                               "select": {"kind": "vm"}, "gte": 3})
    top_only = next((st["predicate"] for st in prog["body"]
                     if st.get("op") == "ensure"), None)
    check("the old top-level-only search found nothing, hence the vacuous pass",
          top_only is None)
    # AND THE OPPOSITE ERROR, which walking nested blocks introduced: a LOOP-LOCAL
    # predicate cannot stand for the program. Rung 11's in-loop
    # `COUNT(SELECT vm WHERE name = '$item') = 1` matched zero rows outside its loop, so a
    # correct revision was reported `goal=unmet` and no correction could ever pass.
    member = f"{config.SIGIL}{config.LOOP_VAR}"
    loop_local = {"shape": "count",
                  "select": {"kind": "vm", "name": member}, "eq": 1}
    standing = {"shape": "count", "select": {"kind": "vm"}, "gte": 3}
    usable = [p for p in (loop_local, standing) if member not in json.dumps(p)]
    check("a predicate naming the loop variable is excluded from the standing goal",
          usable == [standing])


def test_the_loop_variable_pins_exactly_one_member():
    """`$item` is ONE member of the set being walked — that is what foreach means. The
    satisfiability check refused `REACH(SELECT vm WHERE name = 'n1') >= 2` for a literal
    but declined to look at `name = '$item'`, on the grounds a reference might be a set.
    It never can be here. Rung 9 wrote exactly that inside a loop, asking whether one
    machine can reach two, and aborted on its first iteration after a single call."""
    inside = {"body": [{"op": "foreach", "in": ["n1", "n2", "n3"], "do": [
        {"op": "call", "tool": "add_vm_to_network",
         "args": {"net_name": "mesh0", "vm_name": "$item"}},
        {"op": "ensure", "predicate": {"shape": "reach",
                                       "select": {"kind": "vm", "name": "$item"},
                                       "min": 2}}]}]}
    ok, probs = validate(inside)
    check("REACH >= 2 over a single loop member is refused as unsatisfiable", not ok)
    check("and the reason says a name names ONE resource",
          probs and "names ONE resource" in probs[0])
    over_set = {"body": [{"op": "ensure", "predicate": {
        "shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 2}}]}
    check("the same check over a real SET is untouched", validate(over_set)[0])
    bound = {"body": [
        {"op": "fetch", "var": "picked", "select": {"kind": "vm", "label": "fleet"}},
        {"op": "ensure", "predicate": {"shape": "reach",
                                       "select": {"kind": "vm"}, "min": 2}}]}
    check("and an ordinary $reference is still treated as possibly-many",
          validate(bound)[0])


def test_is_on_the_loop_member_is_refused():
    """Rung 8. `IS` reads what a CALL returned; `$item` is the member's NAME, a plain
    string. `IS($item.name) = 'db'` reaches for a field on a string, resolves to nothing,
    and is false for every member in every world — so `NOT(...)` was true for everything,
    db went onto `core` with the rest, six calls ran and the program reported ok. It
    validated because `item` IS in scope, which is the wrong question about it."""
    prog = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
        {"op": "if", "cond": {"shape": "is", "of": "$item.name", "eq": "db"},
         "then": [{"op": "call", "tool": "add_vm_to_network",
                   "args": {"net_name": "dmz", "vm_name": "$item"}}]}]}]}
    ok, probs = validate(prog)
    check("IS on the loop member is refused", not ok)
    check("and the reason says it is a name, not a result",
          probs and "not a result" in probs[0])
    check("and it names the carve-out as the way to treat one member differently",
          probs and "EXCEPT" in probs[0])
    grafted = {"body": [{"op": "foreach", "select": {"kind": "vm"}, "do": [
        {"op": "call", "tool": "guest_ping", "args": {"name": "$item"},
         "graft": "answer"},
        {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": False},
         "then": [{"op": "call", "tool": "stop_vm", "args": {"name": "$item"}}]}]}]}
    check("IS on a genuinely grafted result is untouched", validate(grafted)[0])


def test_new_args_are_reference_checked_like_a_calls():
    """`NEW network(net_name: $blue_net)` with nothing binding `blue_net` validated, the
    token survived resolution, and the lab ended up holding a network literally named
    `$blue_net` and machines named `$blues1`. The rung checker PASSED it, because it
    inspects shape and not name sanity. Two statements that both take `args` must both
    check them."""
    prog = {"body": [{"op": "new", "var": "net", "kind": "network",
                      "args": {"net_name": "$blue_net"}}]}
    ok, probs = validate(prog)
    check("an unbound reference in NEW's args is refused", not ok)
    check("with the same wording a call gets",
          probs and "never created" in probs[0])
    bound_ok = {"body": [
        {"op": "new", "var": "blue_net", "kind": "network"},
        {"op": "new", "var": "vm1", "kind": "vm",
         "args": {"os_type": "linux", "name": "$blue_net"}}]}
    check("a reference that IS bound still validates", validate(bound_ok)[0])
    # And the executor refuses to mint a name that still carries a sigil, because a
    # parameter supplied at invocation is not knowable statically.
    w = SimWorld()
    sel, holds = _seams(w)
    run({"body": [{"op": "new", "var": "net", "kind": "network",
                   "args": {"net_name": "$never_bound"}}]},
        w.execute, select=sel, holds=holds, consent=True)
    check("and a sigil never reaches the world as a resource name",
          not any("$" in n for n in w.nets))


def test_the_operators_intent_reaches_the_runtime():
    """Decision 5 was built, enforced in run(), and never exercised by the benchmark —
    `grep intent tests/bench/` returned nothing. Rung 9 measured the cost: the literal
    "make SURE they can ping each other" reads as a verification, gets ENSURE, and a
    failed ENSURE routes to the model rather than to derive() — so `_derive_reach`, which
    creates a network and attaches every member, sat unreachable while the paraphrase of
    the same rung ("sort out whatever is stopping that") passed in three calls."""
    from tests.bench.author_probe import _system
    check("the author is told outright when it is a command",
          "THIS IS A COMMAND" in _system(intent.ACHIEVE))
    check("and told not to change anything when it is a verification",
          "Do NOT" in _system(intent.ENSURE))
    check("with no intent supplied the instruction is absent, not guessed",
          "THIS IS A COMMAND" not in _system(None))
    w = _world()
    acting = {"body": [{"op": "new", "var": "x", "kind": "vm",
                        "args": {"os_type": "linux"}}]}
    res = _run(acting, w, intent=intent.ENSURE)
    check("run() refuses an acting program under a verification",
          not res["ok"] and res.get("failed") == "exceeds_authority")
    check("and nothing ran before the refusal", res["calls"] == [])


def test_a_name_you_can_bind_is_a_name_you_can_read():
    """THE INVARIANT: legal binding names == readable names. `-` is deliberately excluded
    from a reference token so `$item-snap` composes a name out of `$item` plus `-snap`
    (rung 12 needs that) — which also means `STORE red-net = NEW network` binds a name no
    reference can pronounce. Rung 6's paraphrase did exactly that in three samples out of
    three, and was told `$red-net` "refers to $red, which is never created" one line after
    creating it."""
    check("a plain name is referenceable", refs.is_referenceable("red_net"))
    check("a hyphenated one is not", not refs.is_referenceable("red-net"))
    check("nor is one starting with a digit", not refs.is_referenceable("2nd"))
    check("nor an empty name", not refs.is_referenceable(""))
    bad = {"body": [{"op": "new", "var": "red-net", "kind": "network"}]}
    ok, probs = validate(bad)
    check("binding an unpronounceable name is refused", not ok)
    check("and the message shows how it misreads",
          probs and "$red followed by text" in probs[0])
    check("and offers the underscore form", probs and "'red_net'" in probs[0])
    grafted = {"body": [{"op": "call", "tool": "guest_ping", "args": {"name": "web"},
                         "graft": "the-answer"}]}
    check("graft names are held to the same rule", not validate(grafted)[0])
    good = {"body": [{"op": "new", "var": "red_net", "kind": "network"}]}
    check("the underscore form validates", validate(good)[0])
    # And the composition that the exclusion exists FOR must keep working.
    compose = {"body": [{"op": "foreach", "in": ["a", "b"],
                         "call": {"tool": "snapshot_create",
                                  "args": {"name": "$item", "snap_name": "$item-snap"}}}]}
    check("$item-snap still composes a name — the reason `-` is excluded",
          validate(compose)[0])


def test_new_vouches_for_what_it_made():
    """Operator decision 2026-07-27: NEW carries its own ENSURE.

    NEW is the ONE op where the harness itself invents something — it mints the name,
    chooses the creator, supplies the key argument. A `call` passes the author's
    arguments through and decides nothing. So NEW is the only statement that can quietly
    produce something OTHER than what was asked for, and it did three separate ways in
    one day: a minted name overrode an explicit `net_name` (`core` came out as
    `core_net`), an unresolved `$reference` became a literal resource name, and a
    supplied base got suffixed. All three reported success, because the creator call
    genuinely succeeded — it just made the wrong thing.
    """
    class _Liar(SimWorld):
        """A creator that reports success and records nothing — the shape of every
        false-success this check exists to refuse."""
        def _t_create_network(self, a):
            return {"success": True, "net_name": a.get("net_name")}

    prog = {"body": [{"op": "new", "var": "core_net", "kind": "network",
                      "args": {"net_name": "core"}}]}
    w = SimWorld()
    sel, holds = _seams(w)
    good = run(prog, w.execute, select=sel, holds=holds, consent=True)
    check("an honest creation passes and records no failure",
          good["ok"] and not good["failures"])
    check("and the resource carries the name the author asked for",
          sorted(w.nets) == ["core"])

    liar = _Liar()
    sel2, holds2 = _seams(liar)
    bad = run(prog, liar.execute, select=sel2, holds=holds2, consent=True)
    check("a creator that reports success but makes nothing is caught",
          not bad["ok"] and bad.get("failed") == "calls_failed")
    check("and the objection names the resource that never appeared",
          bad["failures"] and "no network named 'core' exists" in bad["failures"][0]["error"])

    # POST-check, never a pre-check: decision 2 refuses adopting. A NEW against a world
    # that already holds the resource must still ATTEMPT it and report the world's
    # refusal — not silently skip and call itself satisfied.
    w2 = SimWorld()
    w2.execute("create_network", {"net_name": "core"})
    w2.calls.clear()
    sel3, holds3 = _seams(w2)
    again = run(prog, w2.execute, select=sel3, holds=holds3, consent=True)
    check("a re-run still issues the creator call — NEW means new",
          [c["tool"] for c in w2.calls] == ["create_network"])
    check("and the world's own refusal is what gets recorded, not a skip",
          again["failures"] and "already exists" in again["failures"][0]["error"])

    # It verifies the SET, not just the first member.
    w3 = SimWorld()
    sel4, holds4 = _seams(w3)
    many = run({"body": [{"op": "new", "var": "box", "kind": "vm", "amount": 3,
                          "args": {"os_type": "linux"}}]},
               w3.execute, select=sel4, holds=holds4, consent=True)
    check("a counted NEW verifies every member it minted",
          many["ok"] and sorted(w3.vms) == ["box1", "box2", "box3"])
    check("and it costs ONE query per statement, not per resource",
          len([c for c in w3.calls if c["tool"] == "create_vm"]) == 3)


def test_mutations_preserve_the_goal():
    """The ladder's third column is mechanical, so nobody's intent can leak into it — but
    a mutation that changes what the goal MEANS does not measure robustness, it corrupts
    the benchmark, and it looks exactly like a model failure. Two rules keep that from
    happening (whitelist not blacklist; quoted text untouchable), and this is what holds
    them.

    Both defects this caught were the same shape — a substitution valid in one position
    and not another: `all` -> "every one of" gave "put them every one of in a net", and
    `running` -> "up" gave "each up box". Neither is a rewording; both are awkward English
    that inflates difficulty on its own.
    """
    from tests.bench import mutate
    from tests.bench.rungs import RUNGS

    # IDENTITY NAMES ARE UNREACHABLE. Not because they are excluded — because they are
    # absent from the substitution table, which is what makes the guarantee hold for
    # names nobody has invented yet.
    identities = ("alpha", "beta", "web", "lab", "db", "core", "dmz",
                  "n1", "n2", "n3", "golden", "mesh0")
    for r in RUNGS:
        for name in mutate.MUTATIONS:
            out = mutate.apply(r.goal, name)
            lost = [i for i in identities
                    if re.search(rf"\b{i}\b", r.goal) and not re.search(rf"\b{i}\b", out,
                                                                       re.I)]
            check(f"rung {r.n} {name}: keeps every identity name", not lost)

    # QUOTED VALUES SURVIVE VERBATIM — they are what the checker matches on.
    quoted = [r for r in RUNGS if "'" in r.goal]
    for r in quoted:
        vals = re.findall(r"'([^']*)'", r.goal)
        for name in mutate.MUTATIONS:
            out = mutate.apply(r.goal, name)
            check(f"rung {r.n} {name}: quoted values intact",
                  all(f"'{v}'" in out for v in vals))

    # ONE CONCEPT, ONE WORD, within a single goal.
    for r in RUNGS:
        out = mutate.synonym(r.goal)
        for words in (("network", "networks", "net", "nets", "subnet", "subnets"),
                      ("vm", "vms", "machine", "machines", "box", "boxes",
                       "host", "hosts")):
            used = {w for w in words if re.search(rf"\b{w}\b", out)}
            stems = {w[:-2] if w.endswith("es") else w.rstrip("s") for w in used}
            check(f"rung {r.n}: synonym picks one word per concept", len(stems) <= 1)

    # DETERMINISTIC: same goal + same rule -> same sentence, every run.
    for name in mutate.MUTATIONS:
        g = RUNGS[3].goal
        check(f"{name} is deterministic",
              mutate.apply(g, name) == mutate.apply(g, name))

    # REORDER REFUSES A SEQUENCED GOAL — reordering "create beta and THEN launch it"
    # would change the goal rather than reword it.
    seq = "create a vm named beta; then launch it"
    check("reorder declines a goal carrying an ordering word",
          mutate.reorder(seq) == seq)


def test_creating_the_same_thing_twice_is_refused():
    """`STORE lab = NEW network;` then `create_network(net_name: lab)` — NEW calls the
    creator itself, so the second one is refused by the world and, with no ENSURE, sinks
    the program. Rung 3 died this way under `terse`, and the recovery was worse than the
    fault: revision 2 wrote `delete_vm(web)` then `NEW vm FROM web`, cloning a machine it
    had just deleted, and the rung ended with zero VMs."""
    lit = {"body": [{"op": "new", "var": "lab", "kind": "network"},
                    {"op": "call", "tool": "create_network",
                     "args": {"net_name": "lab"}}]}
    ok, probs = validate(lit)
    check("NEW plus a literal creator call is refused", not ok)
    check("and the message says NEW already calls the creator",
          probs and "already creates" in probs[0])
    # The REFERENCE form is the commoner one — the model refers to the var it just bound.
    ref = {"body": [{"op": "new", "var": "net2", "kind": "network"},
                    {"op": "call", "tool": "create_network",
                     "args": {"net_name": "$net2"}}]}
    check("NEW plus a $reference creator call is refused too", not validate(ref)[0])
    twice = {"body": [{"op": "call", "tool": "create_network", "args": {"net_name": "a"}},
                      {"op": "call", "tool": "create_network", "args": {"net_name": "a"}}]}
    check("two identical creator calls are refused", not validate(twice)[0])
    fine = {"body": [{"op": "new", "var": "lab", "kind": "network"},
                     {"op": "call", "tool": "create_network",
                      "args": {"net_name": "other"}}]}
    check("creating a DIFFERENT resource stays legal", validate(fine)[0])


def test_a_dotted_path_needs_a_grafted_result():
    """`add_vm_to_network(net_name: $item.networks[0], ...)` — the model invented array
    indexing. `item` IS in scope so nothing objected, `resolve` left the token standing as
    written (deliberately, so a ledger row stays debuggable), and the literal text
    `$item.networks[0]` was handed to the tool as a network name. Only a call's RESULT has
    fields; everything else a program binds is a name or a set of them."""
    bad = {"body": [{"op": "foreach", "select": {"kind": "vm"},
                     "call": {"tool": "add_vm_to_network",
                              "args": {"net_name": "$item.networks",
                                       "vm_name": "$item"}}}]}
    ok, probs = validate(bad)
    check("a dotted path on the loop member is refused", not ok)
    check("and the reason says it is a name, not a result",
          probs and "NAME, not a call's result" in probs[0])
    good = {"body": [{"op": "call", "tool": "guest_ping", "args": {"name": "web"},
                      "graft": "answer"},
                     {"op": "if", "cond": {"shape": "is", "of": "$answer.alive",
                                           "eq": True},
                      "then": [{"op": "call", "tool": "stop_vm",
                                "args": {"name": "web"}}]}]}
    check("a dotted path on a GRAFTED result is fine", validate(good)[0])
    compose = {"body": [{"op": "foreach", "in": ["a"],
                         "call": {"tool": "snapshot_create",
                                  "args": {"name": "$item",
                                           "snap_name": "$item-snap"}}}]}
    check("and $item-snap still composes a name", validate(compose)[0])


def test_a_legal_predicate_renders_legibly():
    """`reach` declares comparators_optional, so a bare REACH(...) is legal and means the
    default floor. It printed `REACH(SELECT vm) ? None` — a valid statement reading as
    malformed to the one person who has to approve it. The renderer exists so a human can
    check what the machine understood."""
    bare = {"body": [{"op": "ensure", "predicate": {"shape": "reach",
                                                    "select": {"kind": "vm"}}}]}
    out = render(bare)
    check("a bare REACH renders without a placeholder comparator",
          "?" not in out and "None" not in out)
    check("and reads as the check it is", "ENSURE REACH(SELECT vm);" in out)
    check("a REACH WITH a floor still shows it",
          ">= 3" in render({"body": [{"op": "ensure", "predicate": {
              "shape": "reach", "select": {"kind": "vm"}, "min": 3}}]}))


def test_the_repair_budget_carries_distinct_objections():
    """Six lines reach the model on a retry, and they were being spent on repetition:
    rung 4 under `verbose` came back with the SAME objection four times, one per statement
    that made the same mistake, so every other problem was cut off. It re-emitted an
    identical program twice and the rung was lost."""
    from tests.bench.author_probe import _distinct
    same = "is reads what a CALL returned, and $item is the member's name"
    probs = [f"statement 5 (foreach body) → statement 2: {same}",
             f"statement 6 (foreach body) → statement 2: {same}",
             f"statement 7: {same}",
             "statement 7: is reads $item2, which is not in scope here"]
    out = _distinct(probs)
    check("four objections collapse to two", len(out) == 2)
    check("the repeated one carries its count", "(in 3 statements)" in out[0])
    check("and the DISTINCT one survives — it was being cut off",
          "item2" in out[1])
    check("a single objection is left alone", _distinct([probs[3]]) == [probs[3]])


def test_a_select_can_name_its_members():
    """Operator decision 2026-07-27: add INCLUDE (membership) and nested WHERE (groups).

    A select could already NAME a member — but only to EXCLUDE it, via the carve-out. The
    include side had no form, and `foreach` has an escape hatch a PREDICATE does not:
    predicates take a select and nothing else, so a check could never be about particular
    machines. Rung 9's goal is literally "make sure n1, n2 and n3 can all ping each
    other", and the author invented four syntaxes for it in one day — `label =
    'n1,n2,n3'`, `label = '$vms'`, `$item1`/`$item2`, `$item.networks[0]` — and was marked
    wrong each time.
    """
    w = SimWorld()
    for n in ("n1", "n2", "n3", "db"):
        w.execute("create_vm", {"name": n, "os_type": "linux"})
    w.execute("add_label", {"name": "n1", "label": "red"})
    w.execute("add_label", {"name": "db", "label": "blue"})
    sel, _ = _seams(w)

    members = {"kind": "vm", "name": {"in": ["n1", "n2", "n3"]}}
    check("membership validates", validate({"body": [{"op": "ensure", "predicate": {
        "shape": "count", "select": members, "eq": 3}}]})[0])
    check("and selects exactly those members", sel(members) == ["n1", "n2", "n3"])
    check("it renders as the mirror of EXCEPT",
          "INCLUDE name = [n1, n2, n3]" in render(
              {"body": [{"op": "ensure", "predicate": {"shape": "count",
                                                       "select": members, "eq": 3}}]}))
    check("membership works on ANY attribute, not just the key",
          sel({"kind": "vm", "label": {"in": ["red", "blue"]}}) == ["db", "n1"])
    check("it composes with an ordinary filter",
          sel({"kind": "vm", "label": "red", "name": {"in": ["n1", "n2"]}}) == ["n1"])
    check("and with the carve-out, which still wins",
          sel({"kind": "vm", "name": {"in": ["n1", "n2", "db"]},
               "not": {"name": "db"}}) == ["n1", "n2"])

    # GROUPS — `any` is OR, `all` an explicit AND, in the predicate combinators' own words.
    check("an OR group selects the union",
          sel({"kind": "vm", "any": [{"label": "red"}, {"label": "blue"}]}) == ["db", "n1"])
    check("and renders with parentheses, so precedence never has to be known",
          "(label = 'red' OR label = 'blue')" in render(
              {"body": [{"op": "ensure", "predicate": {
                  "shape": "count",
                  "select": {"kind": "vm", "any": [{"label": "red"},
                                                   {"label": "blue"}]}, "eq": 2}}]}))
    check("a group needs two or more branches",
          not validate({"body": [{"op": "ensure", "predicate": {
              "shape": "count",
              "select": {"kind": "vm", "any": [{"label": "red"}]}, "eq": 1}}]})[0])
    check("a branch is checked by the same rules — a bad attribute is still refused",
          not validate({"body": [{"op": "ensure", "predicate": {
              "shape": "count",
              "select": {"kind": "vm", "any": [{"nonsense": "x"}, {"label": "red"}]},
              "eq": 1}}]})[0])

    # EQUALITY still refuses a set reference: that was rung 9's actual mistake, putting
    # the members where a shared attribute belongs. Membership is how to say it now.
    scalar_set = {"body": [
        {"op": "fetch", "var": "vms", "select": {"kind": "vm", "label": "red"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "label": "$vms"},
                                       "eq": 1}}]}
    ok, probs = validate(scalar_set)
    check("a $set in a scalar slot is still refused", not ok)
    check("and the message now names membership as the fix",
          probs and "INCLUDE" in probs[0])
    bound = {"body": [
        {"op": "fetch", "var": "vms", "select": {"kind": "vm", "label": "red"}},
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm",
                                                  "name": {"in": "$vms"}},
                                       "eq": 1}}]}
    check("but membership against a BOUND set is legal — 'the ones I just found'",
          validate(bound)[0])


def test_the_harness_can_close_a_named_member_goal():
    """The reason this mattered. Rung 9 states its end state in one line, and `derive`
    inverts it into the plan — no model call for the structure at all. That is the design
    note's deferred option 3 ("when a procedure is nothing but ENSURE clauses, the harness
    MAY derive the plan"), reachable only once a predicate could name its members."""
    from tests.bench.rungs import RUNGS
    r9 = next(r for r in RUNGS if r.n == 9)
    w = SimWorld()
    r9.setup(w)
    w.calls.clear()
    sel, holds = _seams(w)
    pred = {"shape": "reach", "select": {"kind": "vm",
                                         "name": {"in": ["n1", "n2", "n3"]}}, "min": 3}
    res = run({"body": [{"op": "achieve", "predicate": pred}]}, w.execute,
              select=sel, holds=holds, known_names=w.names(), consent=True)
    check("the bare goal does not hold in the seeded world",
          not res["ok"] and res.get("failed") == "unachieved")
    steps = derive(pred, sel)
    check("the harness computes the plan", bool(steps))
    run({"body": steps}, w.execute, select=sel, holds=holds, consent=True)
    check("and running it satisfies the rung's own checker", bool(r9.check(w)))
    # One network, three attaches, AND THREE PROBES. Attaching machines makes them
    # addressable, not reachable — reachability is a finding, so a derivation that stopped
    # at the attach would close the bench's reach (which asks only whether a network is
    # shared) and leave production's unestablished. The probe is part of the fix.
    check("one network, three attaches, three probes",
          len(w.calls) == 7
          and [c["tool"] for c in w.calls].count("guest_ping") == 3)


def test_the_goal_cannot_be_its_own_precondition():
    """Rungs 7 and 9, 2026-07-27. Both opened with an ENSURE that WAS the goal:

        ENSURE COUNT(SELECT vm WHERE label = 'prod') = 3;
        FOREACH $item IN [four, one, three] { add_label(...); }
        ENSURE COUNT(SELECT vm WHERE label = 'prod') = 3;
            -> ran 0 calls

    ENSURE is a ground check that STOPS the program when it fails — decision 3, and the
    reason it may open a procedure. Assert the goal there and the work is unreachable. The
    model was arguably obeying instructions: intent.instruction(ACHIEVE) says "open with
    ENSURE if something must already be true" and the prompt says a ground check comes
    FIRST. It put the right shape around the wrong predicate.
    """
    goal = {"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 3}
    work = {"op": "foreach", "in": ["a"],
            "call": {"tool": "add_label", "args": {"name": "$item", "label": "prod"}}}
    ok, probs = validate({"body": [{"op": "ensure", "predicate": goal}, work,
                                   {"op": "ensure", "predicate": goal}]})
    check("the goal asserted before its own work is refused", not ok)
    check("and the message says the work never runs",
          probs and "the work never runs" in probs[0])
    check("and names the statement it duplicates", probs and "statement 3" in probs[0])
    check("an ACHIEVE at the end is the same mistake when pre-asserted",
          not validate({"body": [{"op": "ensure", "predicate": goal}, work,
                                 {"op": "achieve", "predicate": goal}]})[0])
    # WHAT MUST STAY LEGAL — a real precondition is a DIFFERENT check about something the
    # work needs to exist, which is exactly the shape decision 3 blessed.
    real = {"body": [
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm", "name": "golden"},
                                       "eq": 1}},
        {"op": "new", "var": "copy", "kind": "vm", "from": "golden",
         "args": {"os_type": "linux"}},
        {"op": "achieve", "predicate": goal}]}
    check("a genuine precondition still validates",
          validate(real, known_names={"golden"})[0])
    check("work then goal, the ordinary shape, is untouched",
          validate({"body": [work, {"op": "achieve", "predicate": goal}]})[0])
    check("the same check twice with NO work between is not this mistake",
          validate({"body": [{"op": "ensure", "predicate": goal},
                             {"op": "ensure", "predicate": goal}]})[0])


def test_render_never_raises_on_malformed_input():
    """It renders UNVALIDATED model output, so a renderer that crashes hides the very
    thing you opened it to look at."""
    for bad in ({"body": [{"op": "ensure", "predicate": {"shape": "count",
                                                         "select": 3, "eq": 1}}]},
                {"body": [{"op": "nonsense"}]},
                {"body": [{"op": "foreach", "in": None, "call": None}]},
                {"body": ["not a statement"]}):
        try:
            render(bad)
            ok = True
        except Exception:
            ok = False
        check(f"render survives {str(bad)[:44]}…", ok)


def main():
    """Every `test_*` in this module, in definition order — DISCOVERED, not listed.

    THE LIST WAS THE BUG, and it bit here on 2026-07-30 for the third time in three days,
    after being fixed twice by pasting a discovery loop into one file. A test added for the
    intent promotion never ran, and this suite reported the SAME 415/415 it had reported
    before that test existed. An unchanged total is the only symptom there is.

    So the loop lives in `tests/_suite.py` now, once. See its docstring for all three.
    """
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__]))


if __name__ == "__main__":
    main()
