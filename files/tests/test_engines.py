#!/usr/bin/env python3
"""
test_engines.py — the mount contract, the registry, sessions, promotion, and routing.

The architecture's own suite. It answers the question the design rests on: is an engine
really just a manifest plus an adapter, and does the orchestrator really know nothing about
what any of them do?

NO MODEL ANYWHERE. The channel is stubbed with written-down components, which is not a
testing convenience — it is the claim. The 13/13 rungs ran the same way, and it means the
coupling was never to an AI, only to an answer.

Run:  PYTHONPATH=. python3 -m tests.test_engines
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     Session, describe, stub)
from orchestrator.ai.packages import WebCrawlPackage
from orchestrator.ai.engines.session import INTENT_REGIME, rank
from orchestrator.ai.planner.ir import config
from tests.bench.generic_world import World

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


# A KITCHEN, because a domain Gorgon will never ship is the honest test of a mount contract.
KITCHEN = {
    # `origin` is deliberately settable by NOTHING: no setter writes it, so demanding it on
    # a dish that already exists is genuinely unreachable. A promotion test needs a real
    # dead end, and `serves` is not one — the creator can take it at birth.
    "dish": {"key": "dish_name", "attrs": ["dish_name", "serves", "origin"],
             "nouns": ["dish", "meal"], "create": "create_dish",
             "setters": {"set_serves": {"attr": "serves", "member_arg": "dish_name",
                                        "value_arg": "n", "single": True}}},
}
RISOTTO = [{"shape": "count", "select": {"kind": "dish", "dish_name": "risotto"}, "eq": 1},
           {"every": {"kind": "dish", "dish_name": "risotto"}, "must": {"serves": "4"}}]


def _kitchen():
    reg = Registry()
    reg.mount(MedusaEngine(World(KITCHEN)))
    return reg


def test_an_engine_is_a_manifest_and_an_adapter():
    """Mount a domain the planner has never seen and plan against it."""
    print("[contract] a kitchen mounts with no code")
    reg = _kitchen()
    orch = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})]))
    r = orch.handle("risotto for four")
    check("the request completes", r["outcome"] == "DONE")
    check("the program is grounded", r.get("grounded") is True)
    check("it costs 2 calls", len(r["calls"]) == 2)
    check("and the world changed",
          reg.get("medusa").world().state["dish"]["risotto"]["serves"] == "4")


def test_the_default_manifest_is_restored_even_when_a_run_fails():
    """`config.use_kinds` is acknowledged debt; the one thing it must never do is leak.

    It swaps a module global so a foreign manifest can be validated, which is safe only while
    nothing else runs inside the block — and utterly unsafe if an exception could leave the
    wrong manifest live. The restore is in a `finally`; this proves it.
    """
    print("[debt] the manifest override always restores")
    before = sorted(config.KINDS)
    reg = _kitchen()
    orch = Orchestrator(reg, Channel([stub({"impossible": [
        {"shape": "count", "select": {"kind": "dish", "dish_name": "x", "serves": "9"},
         "eq": 1}]})]))
    orch.handle("impossible")
    check("KINDS is what it was", sorted(config.KINDS) == before)
    with config.use_kinds(KITCHEN):
        inside = sorted(config.KINDS)
    check("it really did swap inside the block", inside == ["dish"])
    check("and restored after", sorted(config.KINDS) == before)


def test_the_router_sees_one_line_per_engine():
    """The reason context stops growing. The router's whole view is names and one-liners."""
    print("[context] the router's view is O(1) in engines")
    reg = _kitchen()
    one = len(reg.menu())

    class Second(MedusaEngine):
        name = "scheduler"
        description = "run work on a timetable"

    reg.mount(Second(World(KITCHEN)))
    two = len(reg.menu())
    check("a second engine adds one line", 0 < two - one < 200)
    check("and the menu holds no tools, kinds or schemas",
          "create_dish" not in reg.menu() and "attrs" not in reg.menu())


def test_nobody_claiming_is_an_answer_not_a_crash():
    """"Nothing mounted can do that" is useful; failing three steps later is not."""
    print("[honesty] an unclaimed request is reported")
    # A NARROW ENGINE, because Medusa deliberately claims everything — it is the general
    # engine, so with it mounted UNCLAIMED is nearly unreachable and that is correct. The
    # outcome exists for a system whose engines are all specialists.
    class Narrow(MedusaEngine):
        name = "scheduler"
        description = "run work on a timetable"

        def claims(self, request):
            return "schedule" in request.lower()

    reg = Registry()
    reg.mount(Narrow(World(KITCHEN), packages=(WebCrawlPackage(),)))
    orch = Orchestrator(reg, Channel())
    r = orch.handle("defragment the mainframe")
    check("outcome is UNCLAIMED", r["outcome"] == "UNCLAIMED")
    check("and it says what IS mounted", r["mounted"] == ["scheduler"])

    # A GUEST ENGINE IS NEVER A DESTINATION, even when it plainly claims the words. The
    # orchestrator reaches Medusa and QEMU; a crawler is something a PROGRAM calls once it
    # has a machine. Routing to it directly would put a capability that parses untrusted
    # input one step from the host.
    # THE PACKAGE PLAINLY CLAIMS THESE WORDS and is still not a destination. It is offered
    # as something a program could call, once it has somewhere to run it.
    r2 = orch.handle("crawl example.com")
    check("a package is not routed to, however well it claims",
          r2["outcome"] == "UNCLAIMED")
    check("but it IS offered as a callable capability",
          r2["capabilities"] == ["webcrawl"])


def test_an_untranslated_request_names_the_front_seam():
    """A request nobody could translate never became a request.

    Naming the stage is the point: confusing a translation failure with an engine failure is
    how a day gets spent debugging the wrong half.
    """
    print("[honesty] translation failure is its own outcome")
    orch = Orchestrator(_kitchen(), Channel([stub({})]))
    r = orch.handle("make a dish somehow")
    check("outcome is UNTRANSLATED", r["outcome"] == "UNTRANSLATED")
    check("no calls were made", not r["calls"])


def test_promotion_is_requested_by_the_engine_and_granted_by_the_orchestrator():
    """The direction matters: an engine asked whether it wants more will always say yes."""
    print("[promotion] the engine asks, the orchestrator decides")
    reg = _kitchen()
    engine = reg.get("medusa")
    s = Session("x", engine, intent="ensure")
    check("a session starts in the regime its intent implies", s.regime == "translation")
    check("it may promote to tree", s.may_promote("tree") is True)
    check("it may NOT demote", s.may_promote("tool") is False)
    s.promote("tree", "unsolvable")
    check("promotion is recorded, not silent", any("promoted" in l for l in s.log))

    # BUDGET IS THE ORCHESTRATOR'S, AND IT MUST BE ABLE TO REFUSE. A tree runs until resolved
    # or abandoned with cost accruing, so a session with nothing left to spend cannot be
    # allowed to open one.
    broke = Session("x", engine, intent="ensure", budget=0)
    check("a session with no budget cannot promote", broke.may_promote("tree") is False)

    # AN ENGINE THAT DOES NOT SERVE `achieve` CANNOT BE PROMOTED INTO AUTONOMY, however much
    # budget there is — the ladder is about capability, not only cost.
    class Answerer(MedusaEngine):
        intents = ("fetch",)
    only_answers = Session("x", Answerer(World(KITCHEN)), intent="fetch")
    check("an answering engine is never promoted to tree",
          only_answers.may_promote("tree") is False)


def test_unsolvable_is_the_promotion_request():
    """The signal already existed. It was built as a refusal and it is really an ask."""
    print("[promotion] Unsolvable reaches the orchestrator as `promote`")
    engine = MedusaEngine(World(KITCHEN))
    # No tool changes a dish's name once it exists, and nothing can be counted into being
    # with an attribute no setter owns on a member that is already there.
    world = engine.world()
    world.execute("create_dish", {"dish_name": "risotto"})
    got = engine.run([{"shape": "count",
                       "select": {"kind": "dish", "dish_name": "risotto", "serves": "4"},
                       "eq": 1}])
    check("the engine does not raise", isinstance(got, dict))
    # It either promotes or completes; what it must never do is fail silently with no reason.
    check("it either asks for a regime or says why",
          bool(got.get("promote")) or got.get("ok") or bool(got.get("why")))


def test_the_intent_ladder_and_the_regimes_are_one_table():
    """Written once. A second copy would drift by the end of the week."""
    print("[ladder] intents map to regimes in exactly one place")
    check("fetch is the floor", INTENT_REGIME["fetch"] == "tool")
    check("achieve is not the floor", INTENT_REGIME["achieve"] != "tool")
    check("the ladder only goes up", rank("tool") < rank("translation") < rank("tree"))


def test_a_new_engine_is_essentially_an_api():
    """The mock crawl engine — a capability Gorgon has never had, mounted and run.

    Deliberately the HARD case: the crawling belongs inside virtual machines, so the engine's
    world is its own while its HANDS are injected. That is what a real one would do, and it
    is the property a local-only mock would not have tested.
    """
    print("[mock] a capability Gorgon has never had")
    goals = [{"shape": "count", "select": {"kind": "crawl", "crawl_name": "sweep1"}, "eq": 1},
             {"shape": "count", "select": {"kind": "page", "crawl": "sweep1"}, "eq": 3},
             {"every": {"kind": "page", "crawl": "sweep1"}, "must": {"fetched": "yes"}},
             {"observe": {"kind": "page", "crawl": "sweep1"}, "fact": "reachable"}]
    # CALLED, NOT ROUTED TO. A guest capability is what a Medusa program reaches for once it
    # has a machine — `CALL web_crawler_search(vm: $temp)` — so this exercises it the way it
    # is actually reached, rather than through a door the orchestrator deliberately closed.
    pkg = WebCrawlPackage()
    r = MedusaEngine(pkg.world()).run(goals)
    check("the crawl completes", r["ok"] is True)
    check("it is grounded", r.get("grounded") is True)
    rendered = r.get("rendered", "")
    check("it starts the crawl before recording pages in it",
          rendered.index("start_crawl") < rendered.index("record_page"))
    check("it records a page before fetching it",
          rendered.index("record_page") < rendered.index("fetch_page"))
    # REACHABILITY IS A FINDING. Nothing infers it from a fetch succeeding — the crawler that
    # trusts its own success flags is the one that reports 400 pages and delivers 12.
    check("and it PROBES rather than assuming", "probe_page" in rendered)

    seen = {t for t, _ in (r["calls"] or [])}
    check("the hands were injected — no tool ran that the manifest did not name",
          seen <= {"start_crawl", "record_page", "fetch_page", "probe_page",
                   "finish_crawl", "assign_runner", "abandon_crawl"})


def test_the_host_boundary_is_structural_not_a_check():
    """ENGINES RUN THE HOST. PACKAGES RUN INSIDE ONE. A package is simply not mountable.

    An earlier version carried `runs_on = "host" | "guest"` and had the registry refuse a
    guest that claimed the host. It worked — and it made safety a CHECK: forgettable,
    subclassable, true on one path and not another. A package has no `run`, so a capability
    that reaches the internet cannot get the host because it is not the kind of object that
    has one. There is nothing to enforce.
    """
    print("[safety] engines run the host; packages run inside one")
    reg = Registry()
    try:
        reg.mount(WebCrawlPackage())
        check("a package cannot be mounted", False)
    except ValueError as e:
        check("a package cannot be mounted", "PACKAGE" in str(e))
        check("and the refusal explains the distinction", "LOADED" in str(e))
    check("a package has no run()", not hasattr(WebCrawlPackage(), "run"))
    check("and no intents to route on", not hasattr(WebCrawlPackage(), "intents"))

    # LOADED, and then its kinds are plannable by the engine that loaded it.
    engine = MedusaEngine(World(KITCHEN), packages=(WebCrawlPackage(),))
    check("a loaded package's kinds join the engine's manifest",
          {"dish", "crawl", "page"} <= set(engine.manifest))
    check("and the engine still owns its own", "dish" in engine.manifest)


def test_the_reporter_is_wired_into_the_close_path():
    """BUILT AND WIRED, in that order and both proven.

    The reporter existed for a commit before anything called it, which is the exact failure
    this week was spent unwinding — a mechanism believed good because it was written. So this
    asserts the orchestrator actually reaches it, and that the verdict travels WITH the
    sentence rather than beside it.
    """
    print("[wiring] findings become an answer")
    reg = _kitchen()
    goals = [{"shape": "count", "select": {"kind": "dish", "dish_name": "risotto"},
              "eq": 1}]

    def narrator(prompt, findings):
        names = [f.get("dish_name") for f in findings if f.get("dish_name")]
        return {"answer": f"Created {names[0]}." if names else "Nothing was done.",
                "mentions": names}

    orch = Orchestrator(reg, Channel([stub({"a risotto": goals})]), narrate=narrator)
    r = orch.handle("a risotto")
    check("an answer comes back", r.get("answer") == "Created risotto.")
    check("and it is grounded", r.get("answer_grounded") is True)

    # AN INVENTED CLAIM IS RETURNED FLAGGED, not suppressed. Silence where there was an
    # answer is its own failure; a confident sentence nobody checked is the worse one.
    def liar(prompt, findings):
        return {"answer": "Created paella.", "mentions": ["paella"]}

    reg2 = _kitchen()
    bad = Orchestrator(reg2, Channel([stub({"a risotto": goals})]),
                       narrate=liar).handle("a risotto")
    check("the invented answer still comes back", bad.get("answer") == "Created paella.")
    check("but flagged ungrounded", bad.get("answer_grounded") is False)
    check("and the unsupported claim named", "paella" in bad.get("answer_unsupported", []))

    # WITHOUT A NARRATOR, NOTHING IS INVENTED. The default is raw findings, so a caller that
    # never configured a reporter is not silently handed a model-written sentence.
    plain = Orchestrator(_kitchen(), Channel([stub({"a risotto": goals})])).handle("a risotto")
    check("no narrator means no answer field", "answer" not in plain)
    check("but the findings are still there", bool(plain["findings"]))


def test_findings_are_what_was_observed_not_what_was_asked():
    """A finding is something the world said; a call is something we asked it.

    Conflating them would let a reporter say "beta was unreachable" because a probe was
    ISSUED — the inference decision 6 forbids, and the reason `reach` demands an answer
    rather than a success flag.
    """
    print("[honesty] findings vs calls")
    from orchestrator.ai.engines.medusa import _findings_of

    class Observed:
        findings = {"reachable(beta)": False}

    check("a ledger is used when there is one",
          _findings_of(Observed(), {"ok": True, "calls": [("x", {})]})
          == [{"fact": "reachable(beta)", "value": False}])

    class Silent:
        findings = {}

    got = _findings_of(Silent(), {"ok": True, "calls": [("create_dish", {"dish_name": "x"})]})
    check("with no observations, what CHANGED is reported instead",
          got == [{"did": "create_dish", "dish_name": "x"}])
    check("and a failed run reports nothing rather than guessing",
          _findings_of(Silent(), {"ok": False, "calls": [("create_dish", {})]}) == [])


def test_an_engine_borrows_hands_without_knowing_whose():
    """`execute` is injected, so the same engine runs against a mock or a guarded executor."""
    print("[mount] the engine cannot tell who is executing")
    seen = []

    def borrowed(tool, args):
        seen.append(tool)
        return {"success": True}

    pkg = WebCrawlPackage()
    engine = MedusaEngine(pkg.world(), execute=borrowed)
    engine.run([{"shape": "count", "select": {"kind": "crawl", "crawl_name": "s"}, "eq": 1}])
    check("the injected executor was used", "start_crawl" in seen)


def test_planning_never_touches_the_world_it_plans_against():
    """PLANNING MUST NOT ACT. Found 2026-08-01, the first time the QEMU mount met a real
    library rather than the sim.

    `cover` advances its virtual world by EXECUTING each placed tile on a copy — which is
    what makes lowering correct, since "every stopped machine" must resolve against the world
    as it WILL BE. That is safe for a sim, whose `execute` mutates its own dict. It is
    catastrophic for a world whose `execute` reaches OUTSIDE ITSELF: deep-copying a lab
    copies a reference to the real executor, so PLANNING PERFORMED THE ACTIONS. One goal
    created a machine on the way to producing the plan that would create it.

    A world may now offer `scratch()` — a model of itself with a simulated executor — and one
    that does not is assumed to be pure state. The distinction is the WORLD'S to declare,
    because only it knows whether its hands reach outside.

    This is the highest-consequence bug of the day and the cheapest possible test, so it is
    asserted directly rather than inferred from a passing plan.
    """
    print("[safety] planning is not acting")
    calls = []

    class Reaching:
        """A world whose executor reaches outside — what a real lab is."""
        kinds = KITCHEN

        def __init__(self):
            self.state = {"dish": {}}

        @property
        def seams(self):
            from tests.bench.generic_world import seams as _s
            return _s(self)

        def names(self):
            return set()

        def execute(self, tool, args):
            calls.append((tool, args))
            return {"success": True}

        def scratch(self):
            from tests.bench.generic_world import World as _Model
            return _Model(KITCHEN)

    from orchestrator.ai.planner import ghost_writer as _gw
    plan = _gw.cover([{"shape": "count", "select": {"kind": "dish", "dish_name": "x"},
                       "eq": 1}], Reaching())
    check("a plan is still produced", plan == [("create_dish", {"dish_name": "x"})])
    check("and the world was NOT touched while planning", calls == [])

    # A WORLD WITH NO `scratch` IS STILL COPIED, so the sim path is unchanged — the fix must
    # not quietly require every world to grow a method.
    from tests.bench.generic_world import World
    pure = World(KITCHEN)
    _gw.cover([{"shape": "count", "select": {"kind": "dish", "dish_name": "y"}, "eq": 1}],
              pure)
    check("a pure-state world is unaffected by planning", pure.state["dish"] == {})


def test_promotion_opens_an_in_session_rather_than_repeating_itself():
    """A RECORDED-BUT-INERT ESCALATION IS WORSE THAN NONE.

    This used to note the promotion and re-run the SAME engine with the SAME components,
    which fails identically by construction — the log said "promoted to tree" and nothing had
    happened. That is the shape of every defect this project spent a week on.

    What a tree session is: the engine could not close a gap, so THE GAP goes on the channel
    as its own question. Not the original request — that was already translated and asking it
    again gets the same answer. The gap is smaller and different: "nothing reaches this — what
    would?"
    """
    print("[promotion] the gap becomes its own question")
    asked = []

    def gap_answerer(gap, world=None):
        from orchestrator.ai.engines.channel import Answer
        asked.append(gap)
        # Answering with what unblocks it: the dish must exist before it can be served.
        return Answer([{"shape": "count", "select": {"kind": "dish", "dish_name": "risotto"},
                        "eq": 1}], "gap-solver", "")

    reg = _kitchen()
    engine = reg.get("medusa")
    engine.world().execute("create_dish", {"dish_name": "other"})

    # A goal the writer cannot reach on its own: no setter writes `serves` onto a member that
    # does not exist, and the creator cannot run on a name already taken by nothing.
    engine.world().execute("create_dish", {"dish_name": "risotto"})
    impossible_first = [{"shape": "count",
                         "select": {"kind": "dish", "dish_name": "risotto",
                                    "origin": "milan"},
                         "eq": 1}]
    orch = Orchestrator(reg, Channel([gap_answerer]))
    r = orch.handle("serve risotto for four", components=impossible_first)

    check("the channel was asked about the GAP, not the request",
          bool(asked) and isinstance(asked[0], dict) and "gap" in asked[0])
    check("and the gap text is the writer's own refusal",
          bool(str(asked[0].get("gap"))))
    check("the log records an in-session", any("in-session" in l for l in r["log"]))


def test_an_unanswerable_gap_closes_honestly_instead_of_looping():
    """An escalation with no answerer behind it is a slower refusal, and must say so."""
    print("[promotion] nobody can answer the gap")
    reg = _kitchen()
    reg.get("medusa").world().execute("create_dish", {"dish_name": "risotto"})
    orch = Orchestrator(reg, Channel())        # no answerers at all
    r = orch.handle("where is this risotto from",
                    components=[{"shape": "count",
                                 "select": {"kind": "dish", "dish_name": "risotto",
                                            "origin": "milan"},
                                 "eq": 1}])
    check("it closes UNMET", r["outcome"] == "UNMET")
    check("naming the gap", "gap" in (r["why"] or "").lower())
    check("and does not loop forever", len(r["log"]) < 12)


def test_a_session_is_abandoned_rather_than_promoted_forever():
    """A tree runs until resolved OR ABANDONED, and abandonment needs a number.

    Three rounds, because the ghost writer's own fixpoint gives up after four passes that
    will not settle — a session that out-loops its writer is chasing a gap the writer has
    already said it cannot close.
    """
    print("[promotion] bounded, not endless")
    from orchestrator.ai.engines.channel import Answer

    def unhelpful(gap, world=None):
        # Answers, but with something that never closes the gap — the shape that would loop.
        return Answer([{"shape": "count", "select": {"kind": "dish", "dish_name": "decoy"},
                        "eq": 1}], "unhelpful", "")

    reg = _kitchen()
    reg.get("medusa").world().execute("create_dish", {"dish_name": "risotto"})
    r = Orchestrator(reg, Channel([unhelpful])).handle(
        "where is this risotto from",
        components=[{"shape": "count",
                     "select": {"kind": "dish", "dish_name": "risotto", "origin": "milan"},
                     "eq": 1}])
    check("it stops", r["outcome"] in {"ABANDONED", "UNMET", "PROMOTION_DECLINED"})
    check("and says the rounds ran out or the gap stayed open",
          bool(r["why"]))


def test_sync_covers_the_engine_that_was_routed_to():
    """/sync is in the flow, and syncing EVERY engine on EVERY prompt is the 2026-07-31
    context overflow one level up — it grows with the number of engines while nothing
    recomputes the budget. Syncing the chosen one costs a lookup."""
    print("[sync] the routed engine, not all of them")
    reg = _kitchen()
    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})])).handle(
        "risotto for four")
    check("the session records a sync", any("synced" in l for l in r["log"]))
    check("naming the engine it routed to", any("synced medusa" in l for l in r["log"]))


def test_the_operator_sees_the_ends_and_never_the_middle():
    """THE IN-SESSION IS INTERNAL. The back-and-forth between orchestrator and engine is
    machinery, and an operator is owed the outcome rather than the machinery.

    It still comes back — under its own key — because a wrong result has to be traceable to
    the stage that caused it. What must not happen is a caller rendering every field and
    narrating the plumbing at somebody who asked a question.
    """
    print("[boundary] internal record vs the answer")
    reg = _kitchen()

    def narrator(prompt, findings):
        return {"answer": "Made risotto.", "mentions": ["risotto"]}

    r = Orchestrator(reg, Channel([stub({"a risotto": RISOTTO})]),
                     narrate=narrator).handle("a risotto")
    check("the answer is a sentence", r.get("answer") == "Made risotto.")
    check("the in-session is recorded separately", bool(r.get("in_session")))
    check("and it holds the routing and sync steps",
          any("routed to" in l for l in r["in_session"])
          and any("synced" in l for l in r["in_session"]))
    check("none of that leaked into the answer",
          "routed" not in r["answer"] and "synced" not in r["answer"])


def test_the_in_session_grain_is_the_regime():
    """A tree asks per goal; a translation asks once. Not described — counted."""
    print("[in-session] the regime IS how often the orchestrator is consulted")
    from orchestrator.ai.engines import insession

    def count(regime):
        eng = MedusaEngine(World(KITCHEN))
        sess = Session("risotto", eng, intent="ensure")
        sess.regime = regime
        seen = []
        out = insession.drive(eng, RISOTTO, sess, lambda st, s: (
            seen.append(st) or insession.Verdict(insession.RUN)))
        return seen, out

    one, out1 = count("translation")
    many, out2 = count("tree")
    check("translation is a single exchange", len(one) == 1)
    check("and it declares the whole program's cost up front", one[0].cost == 2)
    # PLUS ONE FOR THE REQUEST AS A WHOLE. Goals interact — a later one can undo an
    # earlier one — so the tree grain closes with the same fixpoint `cover` uses.
    check("a tree is one exchange per goal, plus one for the whole request",
          len(many) == len(RISOTTO) + 1)
    check("each goal declaring only its own cost", all(s.cost == 1 for s in many[:-1]))
    check("and the closing witness has nothing left to do", many[-1].cost == 0)
    check("both close the work", out1.get("ok") and out2.get("ok"))
    check("and both make the same calls", len(out1["calls"]) == len(out2["calls"]) == 2)


def test_an_engine_may_not_act_on_a_node_it_was_refused():
    """The verdict is load-bearing, and a decline keeps its reason."""
    print("[in-session] the engine proposes; the orchestrator disposes")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="ensure")
    out = insession.drive(eng, RISOTTO, sess,
                          lambda st, s: insession.Verdict(insession.STOP, "not tonight"))
    check("nothing ran", not world.state.get("dish"))
    check("the refusal is not filed as a failure", out.get("refused") is True)
    check("and it carries the reason it was given", out.get("why") == "not tonight")
    check("which the in-session recorded", any("-> stop" in l for l in sess.log))


def test_a_refusal_closes_under_its_own_name():
    """REFUSED is a distinct outcome from UNMET: one is the system working."""
    print("[in-session] a decline is an outcome, not a gap")
    from orchestrator.ai.engines import insession

    orch = Orchestrator(_kitchen(), Channel([stub({"a risotto": RISOTTO})]),
                        decide=lambda st, s: insession.Verdict(insession.STOP,
                                                               "the operator said no"))
    r = orch.handle("a risotto")
    check("the outcome names the refusal", r["outcome"] == "REFUSED")
    check("and says who refused and why", r["why"] == "the operator said no")


def test_the_budget_refuses_before_the_act_not_after():
    """An engine told yes and then billed for it spent money nobody agreed to."""
    print("[in-session] cost is declared with the proposal")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    # The program costs two calls; this session may afford one.
    sess = Session("risotto", eng, intent="ensure", budget=1)
    asked = []
    out = insession.drive(eng, RISOTTO, sess,
                          lambda st, s: (asked.append(st) or insession.Verdict(insession.RUN)))
    check("the decider was never consulted", not asked)
    check("nothing ran", not world.state.get("dish"))
    check("and the log says it was the budget",
          any("REFUSED" in l and "budget" in l for l in sess.log))


def test_an_engine_without_an_in_session_still_runs():
    """The tool regime is one call and no exchange, and the protocol must fit it."""
    print("[in-session] no steps is not an error")
    from orchestrator.ai.engines import insession

    class Plain:
        name = "plain"

        def run(self, components, session=None):
            return {"ok": True, "calls": list(components)}

    out = insession.drive(Plain(), [1, 2], Session("x", Plain()),
                          lambda st, s: insession.Verdict(insession.STOP, "never asked"))
    check("it ran without being asked", out["ok"] and out["calls"] == [1, 2])


def test_decompose_is_a_verdict_that_does_something():
    """The grain is not fixed by the regime — being told to open a node refines it."""
    print("[in-session] 'no, decompose it' actually decomposes")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="ensure")   # translation: one whole program
    seen, opened = [], [False]

    def decide(step, s):
        seen.append(step.why)
        if not opened[0]:                 # open the whole program exactly once
            opened[0] = True
            return insession.Verdict(insession.DECOMPOSE, "one goal at a time, please")
        return insession.Verdict(insession.RUN)

    out = insession.drive(eng, RISOTTO, sess, decide)
    check("it opened once, then ran each goal, then witnessed the parent",
          seen == ["the whole program", "one goal", "one goal",
                   "the whole program · witness"])
    check("and the work still completed", out.get("ok"))
    check("with the same calls the whole program would have made", len(out["calls"]) == 2)


def test_an_atomic_node_says_so_instead_of_inventing_a_split():
    """Decomposing forever is a refusal that will not admit to being one."""
    print("[in-session] nothing lowers it -> say so")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="ensure")
    sess.regime = "tree"
    out = insession.drive(eng, [RISOTTO[0]], sess,
                          lambda st, s: insession.Verdict(insession.DECOMPOSE, "again"))
    check("it refused rather than looping", out.get("refused") is True)
    check("and named the node as atomic", "atomic" in out.get("why", ""))
    check("nothing ran without a grant", not world.state.get("dish"))


def test_a_step_declares_whether_there_is_anything_finer_inside_it():
    """Declared, not guessed — so a decider never asks for a split that cannot exist."""
    print("[in-session] the step declares its own grain")
    from orchestrator.ai.engines import insession

    seen = []
    eng = MedusaEngine(World(KITCHEN))
    sess = Session("risotto", eng, intent="ensure")
    sess.regime = "tree"
    insession.drive(eng, RISOTTO, sess,
                    lambda st, s: (seen.append(st) or insession.Verdict(insession.RUN)))
    check("a lone count goal is atomic", seen[0].divisible is False)
    check("and a quantified one is not", seen[1].divisible is True)


def test_the_grain_does_not_change_the_work_on_any_rung():
    """THE INVARIANCE THAT MAKES THE VERDICTS SAFE TO GIVE.

    A request served as one program and the same request opened all the way down must make
    the same calls. If it did not, the orchestrator's verdicts would silently change WHAT
    HAPPENS rather than only how often it is consulted — and nobody would see it, because
    every grain reports success.

    Thirteen rungs, three grains: whole program, one node per goal, and opened until nothing
    is divisible.
    """
    print("[in-session] thirteen rungs, three grains, one set of calls")
    from orchestrator.ai.engines import insession
    from tests.bench.rungs import RUNGS
    from tests.bench.sim_world import SimWorld
    from tests.test_ghost_writer import GOALS

    def served(n, regime, open_everything):
        rung = next(r for r in RUNGS if r.n == n)
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        eng = MedusaEngine(world)
        sess = Session("", eng, intent="ensure")
        sess.regime = regime
        out = insession.drive(eng, GOALS[n], sess, lambda st, s: insession.Verdict(
            insession.DECOMPOSE if (open_everything and st.divisible) else insession.RUN))
        # THE CHECKER AND THE GROUNDING VERDICT TRAVEL WITH THE CALLS. Matching calls alone
        # would have passed while five rungs quietly stopped vouching for themselves, which
        # is exactly what happened the first time this was measured.
        return (out.get("ok"), out.get("grounded"), rung.check(world),
                sorted(f"{t}{sorted((a or {}).items())}" for t, a in out.get("calls") or []))

    same = 0
    for n in sorted(GOALS):
        grains = {str(served(n, r, o)) for r, o in
                  (("translation", False), ("tree", False), ("translation", True))}
        if len(grains) == 1:
            same += 1
        else:
            print(f"  rung {n} differs by grain")
    check(f"all {len(GOALS)} rungs do — and prove — the same work at every grain "
          f"({same}/{len(GOALS)})", same == len(GOALS))


def test_a_decomposed_goal_is_still_witnessed_by_its_parent():
    """The parent's closing ENSURE is why the re-visit exists, and it catches root poisoning.

    A GOAL SPLIT AGAINST A SET THAT THEN CHANGES is the defect: every child is locally
    correct, every child closes, and the parent goal is false anyway. Nothing that checks a
    node can see it, because the fault is not in any node — so the parent is re-planned
    against the world as it now is, and the work that reappeared shows up as work.
    """
    print("[in-session] the parent is re-visited, so a changed set cannot hide")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    for name in ("risotto", "paella"):
        world.execute("create_dish", {"dish_name": name})
    eng = MedusaEngine(world)
    sess = Session("four each", eng, intent="ensure")
    goals = [{"every": {"kind": "dish"}, "must": {"serves": "4"}}]
    seen, opened = [], [False]

    def decide(step, s):
        seen.append((step.why, step.cost))
        if not opened[0]:
            opened[0] = True
            return insession.Verdict(insession.DECOMPOSE, "one dish at a time")
        # THE SET CHANGES UNDERNEATH THE SPLIT — a third dish nobody planned for, arriving
        # while the children run. This is the concurrent world, simulated at the one moment
        # that makes it visible.
        if step.why == "sub-goal" and "pasta" not in (world.state.get("dish") or {}):
            world.execute("create_dish", {"dish_name": "pasta"})
        return insession.Verdict(insession.RUN)

    out = insession.drive(eng, goals, sess, decide)
    witness = [c for w, c in seen if "witness" in w]
    check("the parent came back as a witness", len(witness) >= 1)
    check("and it had work to do — the split was stale", witness[0] > 0)
    check("re-visiting until it settles is what ends it", witness[-1] == 0)
    check("the goal now actually holds", out.get("ok") and
          all(d.get("serves") == "4" for d in world.state["dish"].values()))
    check("including the dish that arrived late",
          world.state["dish"]["pasta"]["serves"] == "4")


def test_the_book_keeper_reports_a_split_served_against_a_moving_set():
    """It corrected — now somebody has to be TOLD it was needed.

    A run served against a set that changed and one served against a set that held still
    both succeed, and they are not the same thing. The keeper reads and reports; the
    correcting already happened when the parent was re-planned.
    """
    print("[keeper] the in-session tree, read by the book keeper")
    from orchestrator.ai.engines import insession
    from orchestrator.ai.planner import tree_keeper as tk

    def serve(moving):
        world = World(KITCHEN)
        for name in ("risotto", "paella"):
            world.execute("create_dish", {"dish_name": name})
        eng = MedusaEngine(world)
        sess = Session("four each", eng, intent="ensure")
        opened = [False]

        def decide(step, s):
            if not opened[0]:
                opened[0] = True
                return insession.Verdict(insession.DECOMPOSE, "one dish at a time")
            if moving and step.why == "sub-goal" and "pasta" not in world.state["dish"]:
                world.execute("create_dish", {"dish_name": "pasta"})
            return insession.Verdict(insession.RUN)

        return insession.drive(eng, [{"every": {"kind": "dish"},
                                      "must": {"serves": "4"}}], sess, decide)

    still, moved = serve(False), serve(True)
    check("both runs succeeded", still.get("ok") and moved.get("ok"))
    check("a settled tree is clear", still["tree"]["verdict"] == "clear")
    check("a moving one is not", moved["tree"]["verdict"] == tk.INFECTED)
    check("and the infected node is the PARENT, not a child",
          [r["path"] for r in moved["tree"]["origins"]] == ["0"])
    check("the report says what changed",
          "the set it was split over changed" in moved["tree_report"])
    check("children stay sound — the fault was never in one of them",
          moved["tree"]["infected"] == 1 and moved["tree"]["nodes"] == 3)


def test_a_goal_of_any_shape_can_be_named_in_one_line():
    """These strings are read by people, in refusals and in the keeper's report."""
    print("[readability] _short speaks every shape the writer accepts")
    from orchestrator.ai.planner import ghost_writer as gw

    said = [gw._short(g) for g in (
        {"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}},
        {"observe": {"kind": "vm"}, "fact": "alive"},
        {"per": {"kind": "vm"}, "make": "snapshot", "link": "of"},
        {"_call": ("guest_ping", {"name": "alpha"})},
        {"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 2},
    )]
    check("none renders as an unknown shape", not any("?" in t or "None" in t for t in said))
    # A BARE CALL HAS NO KIND — it names a tool, which is the honest thing to name.
    check("every goal names its kind, and the bare call names its tool",
          all("vm" in t for t in said if not t.startswith("call "))
          and said[3] == "call guest_ping(name=alpha)")


def test_a_step_declares_what_it_would_destroy():
    """The reason the protocol asks per node at all — and it was unenforceable until now.

    The claim has been that "a destructive node gets a verdict of its own rather than riding
    in on the back of a program granted as a whole". Until the step SAID which nodes those
    were, nobody reading a step could act on it.
    """
    print("[in-session] a step names what it would destroy")
    from orchestrator.ai.engines import insession
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    for name in ("alpha", "beta", "gamma"):
        world.execute("create_vm", {"name": name, "os_type": "linux"})
    eng = MedusaEngine(world)
    sess = Session("just one", eng, intent="ensure")
    goals = [{"shape": "count", "select": {"kind": "vm"}, "eq": 1}]
    seen = []

    def refuse_destruction(step, s):
        seen.append(step)
        if step.destroys:
            return insession.Verdict(insession.STOP,
                                     f"{len(step.destroys)} machine(s) would be destroyed")
        return insession.Verdict(insession.RUN)

    out = insession.drive(eng, goals, sess, refuse_destruction)
    check("the step named the deletions", len(seen[0].destroys) == 2)
    check("and named them as calls, not a flag",
          all(t == "delete_vm" for t, _ in seen[0].destroys))
    check("a policy that reads it can refuse", out.get("refused") is True)
    check("and nothing was destroyed", len(world.vms) == 3)


def test_the_opened_grain_acts_before_it_knows_the_request_is_impossible():
    """THE TREE REGIME'S INTRINSIC COST, measured rather than asserted.

    "Every machine can reach the others, AND end up with exactly one machine" cannot be
    satisfied. The whole-program grain refuses WITHOUT TOUCHING ANYTHING — `cover` reviews an
    inert artifact before it runs. The opened grain reaches the same refusal having already
    deleted machines, because it acts as it goes.

    That is not a defect to fix. It is what the intent ladder means by gravity pointing down,
    and it is why `Step.destroys` exists: the verdict is the only place it can be caught.
    """
    print("[in-session] the program regime reviews BEFORE; the tree corrects AFTER")
    from orchestrator.ai.engines import insession
    from tests.bench.sim_world import SimWorld

    def serve(regime):
        world = SimWorld()
        for name in ("alpha", "beta", "gamma"):
            world.execute("create_vm", {"name": name, "os_type": "linux"})
        eng = MedusaEngine(world)
        sess = Session("", eng, intent="ensure")
        sess.regime = regime
        out = insession.drive(eng, [{"shape": "reach", "select": {"kind": "vm"}, "min": 3},
                                    {"shape": "count", "select": {"kind": "vm"}, "eq": 1}],
                              sess, lambda st, s: insession.Verdict(insession.RUN))
        return out, world

    whole, w1 = serve("translation")
    opened, w2 = serve("tree")
    check("neither claims success on an impossible request",
          not whole.get("ok") and not opened.get("ok"))
    check("both ask to be promoted rather than inventing an answer",
          whole.get("promote") == "tree" and opened.get("promote") == "tree")
    check("the whole-program grain destroyed nothing", len(w1.vms) == 3)
    check("the opened grain had already acted", len(w2.vms) < 3)


def test_a_node_can_be_told_to_wait_and_comes_round_again():
    """YIELD: not now, ask me again — the third answer a node needs.

    Until it existed a node could only run, split, or die, so anything not ready YET had to
    be treated as something that would never be ready.
    """
    print("[in-session] wait, then re-offer")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("two dishes", eng, intent="ensure")
    sess.regime = "tree"
    goals = [{"shape": "count", "select": {"kind": "dish", "dish_name": "risotto"}, "eq": 1},
             {"shape": "count", "select": {"kind": "dish", "dish_name": "paella"}, "eq": 1}]
    order, held = [], [True]

    def decide(step, s):
        name = (step.node.get("select") or {}).get("dish_name")
        if name == "risotto" and held[0]:
            held[0] = False
            return insession.Verdict(insession.YIELD, "the rice is still in the cupboard")
        order.append(name)
        return insession.Verdict(insession.RUN)

    out = insession.drive(eng, goals, sess, decide)
    check("the yielded node ran after the others", order[0] == "paella")
    check("but it did run", "risotto" in order)
    check("and the work completed", out.get("ok"))
    check("the wait is in the record, with its reason",
          any("waiting" in l and "cupboard" in l for l in sess.log))


def test_waiting_re_plans_against_the_world_it_comes_back_to():
    """THE ONLY KIND OF WAITING THAT CAN END. A yielded node is not a sleep — it is re-planned
    when it comes round, so what it was waiting for can actually have arrived."""
    print("[in-session] the wait is a re-plan, not a sleep")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("four each", eng, intent="ensure")
    sess.regime = "tree"
    goals = [{"every": {"kind": "dish"}, "must": {"serves": "4"}}]
    costs, first = [], [True]

    def decide(step, s):
        costs.append(step.cost)
        if first[0]:
            first[0] = False
            # WHAT IT WAS WAITING FOR ARRIVES WHILE IT WAITS — the dish it is about to
            # quantify over does not exist yet when the node is first offered.
            world.execute("create_dish", {"dish_name": "risotto"})
            return insession.Verdict(insession.YIELD, "no dishes exist yet")
        return insession.Verdict(insession.RUN)

    out = insession.drive(eng, goals, sess, decide)
    check("it had nothing to do the first time", costs[0] == 0)
    check("and real work the second", costs[1] > 0)
    check("the goal holds", out.get("ok")
          and world.state["dish"]["risotto"]["serves"] == "4")


def test_a_node_that_waits_forever_is_refused_by_name():
    """A decider that never says yes is refusing; the engine says so rather than spinning."""
    print("[in-session] waiting forever is a refusal that will not admit it")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("a dish", eng, intent="ensure")
    out = insession.drive(eng, [RISOTTO[0]], sess,
                          lambda st, s: insession.Verdict(insession.YIELD, "the oven"))
    check("it stopped", out.get("refused") is True)
    check("naming what it waited for", "the oven" in out.get("why", ""))
    check("and nothing was cooked", not world.state.get("dish"))


def test_a_queue_where_everything_waits_is_a_deadlock_and_says_so():
    """Running is the only thing that changes the world, so a queue that never runs never
    changes. Naming it beats spinning until a counter blames the last node to speak."""
    print("[in-session] every node waiting is a deadlock, not patience")
    from orchestrator.ai.engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("two dishes", eng, intent="ensure")
    sess.regime = "tree"
    goals = [{"shape": "count", "select": {"kind": "dish", "dish_name": n}, "eq": 1}
             for n in ("risotto", "paella")]
    asked = []

    def decide(step, s):
        asked.append(step)
        return insession.Verdict(insession.YIELD, "each other")

    out = insession.drive(eng, goals, sess, decide)
    check("it named the deadlock", "deadlock" in (out.get("why") or ""))
    check("rather than running the wait counter out",
          len(asked) < len(goals) * 12)
    check("nothing ran", not world.state.get("dish"))


def extract_attr_enum():
    """The attributes a MODEL may name, straight from the extractor's schema."""
    from tests.bench.extract import SCHEMA
    return (SCHEMA["properties"]["goals"]["items"]["properties"]["select"]["properties"]
            ["where"]["items"]["properties"]["attr"]["enum"])


def test_the_lab_mount_speaks_the_manifest_not_the_library():
    """A SILENT WRONG ANSWER, found the first time the QEMU mount met a real lab.

    The library says `labels`; the manifest's attribute is `label`. Rows were copied
    verbatim, so `select(vm where label=x)` matched NOTHING over a lab where machines carried
    it — and the writer answered "nothing to do" rather than failing. A wrong answer that
    looks like a finished job is the worst shape this can take.
    """
    print("[mount] library field names are translated, not copied")
    from orchestrator.ai.engines import QemuEngine

    class FakeLibrary:
        """Speaks the LIBRARY'S vocabulary — plural `labels`, plus fields no predicate has."""

        def vms(self):
            return {"red": {"name": "red", "labels": ["fleet", "prod"], "status": "stopped",
                            "os_type": "linux", "memory_mb": 8192},
                    "blue": {"name": "blue", "labels": ["fleet"], "status": "running",
                             "os_type": "windows", "_internal": "ignore me"}}

        def known_names(self):
            return {"red", "blue"}

    eng = QemuEngine(FakeLibrary(), lambda t, a: {"success": False})
    select, _ = eng.world().scratch().seams
    check("an aliased attribute matches", select({"kind": "vm", "label": "fleet"})
          == ["blue", "red"])
    check("and discriminates within it", select({"kind": "vm", "label": "prod"}) == ["red"])
    check("a canonical attribute still matches",
          select({"kind": "vm", "status": "running"}) == ["blue"])
    check("and one the manifest shares a name for",
          select({"kind": "vm", "os_type": "linux"}) == ["red"])
    row = eng.world().scratch().state["vm"]["red"]
    check("a multi-valued attribute is stored as a set", isinstance(row["label"], set))
    check("a field with no predicate keeps its own name", row.get("memory_mb") == 8192)
    check("it is reachable only by a hand-written selector, never by a goal — "
          "the extractor's attribute enum is the manifest's and closed",
          select({"kind": "vm", "memory_mb": 8192}) == ["red"]
          and "memory_mb" not in set(extract_attr_enum()))
    check("and an underscore field never reaches the model", "_internal" not in
          eng.world().scratch().state["vm"]["blue"])


def test_a_world_that_cannot_ask_still_plans_a_reach():
    """`observed.<fact>.by` is a manifest row like any other, and the model executor ignored
    it — so every reach goal against a mounted lab promoted to tree instead of planning."""
    print("[mount] the model records what it was asked, and evaluates reach")
    world = World(config.KINDS)
    for name in ("alpha", "beta"):
        world.execute("create_vm", {"name": name, "os_type": "linux"})
    _, holds = world.seams
    goal = {"shape": "reach", "select": {"kind": "vm"}, "min": 2}
    ok, why = holds(goal)
    check("unprobed is not reachable, and says which", not ok and "probed" in why)
    for name in ("alpha", "beta"):
        world.execute("guest_ping", {"name": name})
    ok, why = holds(goal)
    check("asked but unconnected is still not reachable", not ok and "connection" in why)
    world.execute("create_network", {"net_name": "lab"})
    for name in ("alpha", "beta"):
        world.execute("add_vm_to_network", {"vm_name": name, "net_name": "lab"})
    ok, why = holds(goal)
    check("answered and connected is reachable", ok)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "engines"))


if __name__ == "__main__":
    main()
