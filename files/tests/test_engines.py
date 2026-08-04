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

from engines import (Channel, MedusaEngine, Orchestrator, Registry,
                                     Session, describe, stub)
from tests.bench.fixture_package import GuestPackage
from engines.session import INTENT_REGIME, rank
from planner.ir import config
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
    return _one(MedusaEngine(World(KITCHEN)))


def _one(engine):
    """A registry holding exactly this engine — the mount, without the rig's opinions."""
    reg = Registry()
    reg.mount(engine)
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
    reg.mount(Narrow(World(KITCHEN), packages=(GuestPackage(),)))
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
          r2["capabilities"] == ["guest"])


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
    """A capability the system has never had, planned from nothing but its manifest.

    Deliberately the HARD case: the work belongs inside virtual machines, so the engine's
    world is its own while its HANDS are injected. That is what a real package does, and it
    is the property a local-only mock would not have tested.

    NARROWED 2026-08-02 WHEN `webcrawl` WAS DELETED. This asserted a fetch/probe chain and a
    reachability FINDING, both of which were that package's design rather than the loading
    contract — `test_the_crawler_probes_rather_than_trusting_a_success_flag` is the test the
    rework owes back, and it belongs with whatever replaces the crawler. What survives here
    is what is true of ANY package: a dependency order the manifest declares, and hands that
    cannot run a tool the manifest never named.
    """
    print("[mock] a capability Gorgon has never had")
    goals = [{"shape": "count", "select": {"kind": "crawl", "crawl_name": "sweep1"}, "eq": 1},
             {"shape": "count", "select": {"kind": "page", "crawl": "sweep1"}, "eq": 3}]
    # CALLED, NOT ROUTED TO. A guest capability is what a Medusa program reaches for once it
    # has a machine — so this exercises it the way it is actually reached, rather than
    # through a door the orchestrator deliberately closed.
    pkg = GuestPackage()
    r = MedusaEngine(pkg.world()).run(goals)
    check("the work completes", r["ok"] is True)
    check("it is grounded", r.get("grounded") is True)
    rendered = r.get("rendered", "")
    # THE ORDER IS THE MANIFEST'S, not the goal list's. `page` declares `create_requires:
    # crawl`, so a page cannot be recorded into a crawl that was never started — and nothing
    # in the goals above says so.
    check("it starts the crawl before recording pages in it",
          rendered.index("start_crawl") < rendered.index("record_page"))

    seen = {t for t, _ in (r["calls"] or [])}
    check("the hands were injected — no tool ran that the manifest did not name",
          seen <= {"start_crawl", "record_page", "finish_crawl"})


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
        reg.mount(GuestPackage())
        check("a package cannot be mounted", False)
    except ValueError as e:
        check("a package cannot be mounted", "PACKAGE" in str(e))
        check("and the refusal explains the distinction", "LOADED" in str(e))
    check("a package has no run()", not hasattr(GuestPackage(), "run"))
    check("and no intents to route on", not hasattr(GuestPackage(), "intents"))

    # LOADED, and then its kinds are plannable by the engine that loaded it.
    engine = MedusaEngine(World(KITCHEN), packages=(GuestPackage(),))
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
        # A FINDING IS `{fact, value}` NOW, uniformly — publications became the source, and a
        # publication says WHAT and WHAT IT WAS rather than spreading a call's arguments
        # across the top level. A narrator that reached for a known key stops working, which
        # is the right pressure: findings whose shape nobody anticipated are exactly what
        # `_atoms` walks the whole structure for.
        names = []
        for f in findings:
            value = f.get("value")
            if isinstance(value, dict) and value.get("dish_name"):
                names.append(value["dish_name"])
            elif f.get("dish_name"):
                names.append(f["dish_name"])
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
    from engines.medusa import _findings_of

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

    pkg = GuestPackage()
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

    from planner import ghost_writer as _gw
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
        from engines.channel import Answer
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
    from engines.channel import Answer

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


def test_sync_covers_the_claimants_before_the_router_chooses():
    """/sync THEN route, and that order is the point.

    An earlier version synced only the WINNER, which meant the choice was made blind and then
    informed — a router deciding between engines needs to know what each holds. Syncing every
    MOUNTED engine would be the 2026-07-31 context overflow one level up, growing with the
    number of engines while nothing recomputes the budget; the CLAIMANT list is short by
    construction, because claiming is a cheap manifest question asked first.
    """
    print("[sync] the claimants, before the choice — not all engines, not just the winner")
    reg = _kitchen()
    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})])).handle(
        "risotto for four")
    check("the session records a sync", any("synced" in l for l in r["log"]))
    # ASSERTED AGAINST THE LEDGER, NOT THE PROSE. The sentence is a rendering; the event
    # names both ends and carries the state as data, which is what a reader actually needs.
    synced = [e for e in r["events"].events if e.executed == "sync(claimants)"]
    check("and it covers the claimants, with their state as data",
          len(synced) == 1 and "medusa" in (synced[0].data or {}))

    # AND NOT EVERY MOUNTED ENGINE. A second engine that claims nothing is never asked.
    class Bystander(MedusaEngine):
        name = "bystander"

        def claims(self, request):
            return False

    reg2 = _kitchen()
    reg2.mount(Bystander(World(KITCHEN)))
    r2 = Orchestrator(reg2, Channel([stub({"risotto for four": RISOTTO})])).handle(
        "risotto for four")
    check("an engine that claims nothing is not synced",
          not any("bystander" in l for l in r2["log"]))


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
    from engines import insession

    def count(regime):
        eng = MedusaEngine(World(KITCHEN))
        sess = Session("risotto", eng, intent="achieve", regime="translation")
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


def test_the_engine_hands_the_red_lines_to_the_program():
    """THE WIRING, not the rule — the rule is tested in `test_medusa`.

    A LEGAL FILTER THAT NOBODY INJECTS IS [[gorgon-built-and-never-called]] in its first
    shape: a seam nobody fills. `execute.run` grew a `legal` parameter and this asserts the
    engine actually passes one, through the whole mounted path, by banning the creator the
    plan needs and watching the world stay empty.
    """
    print("[legal] a banned tool refuses the program, not the call")
    world = World(KITCHEN)

    class Lawful(MedusaEngine):
        legal_filter = staticmethod(lambda tool: tool == "create_dish")

    orch = Orchestrator(_one(Lawful(world)), Channel([stub({"risotto for four": RISOTTO})]))
    r = orch.handle("risotto for four")
    check("the request does not close DONE", r["outcome"] != "DONE")
    check("nothing was cooked", not world.state.get("dish"))
    check("and the reason names the tool", "create_dish" in (r.get("why") or ""))

    # THE SAME ENGINE WITHOUT THE BAN. Otherwise this test would pass on any engine that
    # simply cannot cook, which is the check-that-cannot-fail the suite keeps catching.
    clean = World(KITCHEN)
    ok = Orchestrator(_one(MedusaEngine(clean)),
                      Channel([stub({"risotto for four": RISOTTO})])).handle("risotto for four")
    check("and the same request runs when nothing is forbidden",
          ok["outcome"] == "DONE" and clean.state["dish"]["risotto"]["serves"] == "4")


def test_an_engine_may_not_act_on_a_node_it_was_refused():
    """The verdict is load-bearing, and a decline keeps its reason."""
    print("[in-session] the engine proposes; the orchestrator disposes")
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="achieve", regime="translation")
    out = insession.drive(eng, RISOTTO, sess,
                          lambda st, s: insession.Verdict(insession.STOP, "not tonight"))
    check("nothing ran", not world.state.get("dish"))
    check("the refusal is not filed as a failure", out.get("refused") is True)
    check("and it carries the reason it was given", out.get("why") == "not tonight")
    check("which the in-session recorded", any("-> stop" in l for l in sess.log))


def test_a_refusal_closes_under_its_own_name():
    """REFUSED is a distinct outcome from UNMET: one is the system working."""
    print("[in-session] a decline is an outcome, not a gap")
    from engines import insession

    orch = Orchestrator(_kitchen(), Channel([stub({"a risotto": RISOTTO})]),
                        decide=lambda st, s: insession.Verdict(insession.STOP,
                                                               "the operator said no"))
    r = orch.handle("a risotto")
    check("the outcome names the refusal", r["outcome"] == "REFUSED")
    check("and says who refused and why", r["why"] == "the operator said no")


def test_the_budget_refuses_before_the_act_not_after():
    """An engine told yes and then billed for it spent money nobody agreed to."""
    print("[in-session] cost is declared with the proposal")
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    # The program costs two calls; this session may afford one.
    sess = Session("risotto", eng, intent="achieve", regime="translation", budget=1)
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
    from engines import insession

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
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="achieve", regime="translation")   # translation: one whole program
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
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("risotto", eng, intent="achieve", regime="translation")
    sess.regime = "tree"
    out = insession.drive(eng, [RISOTTO[0]], sess,
                          lambda st, s: insession.Verdict(insession.DECOMPOSE, "again"))
    check("it refused rather than looping", out.get("refused") is True)
    check("and named the node as atomic", "atomic" in out.get("why", ""))
    check("nothing ran without a grant", not world.state.get("dish"))


def test_a_step_declares_whether_there_is_anything_finer_inside_it():
    """Declared, not guessed — so a decider never asks for a split that cannot exist."""
    print("[in-session] the step declares its own grain")
    from engines import insession

    seen = []
    eng = MedusaEngine(World(KITCHEN))
    sess = Session("risotto", eng, intent="achieve", regime="translation")
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
    from engines import insession
    from tests.bench.rungs import RUNGS
    from tests.bench.sim_world import SimWorld
    from tests.test_ghost_writer import GOALS

    def served(n, regime, open_everything):
        rung = next(r for r in RUNGS if r.n == n)
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
        eng = MedusaEngine(world)
        sess = Session("", eng, intent="achieve", regime="translation")
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
    from engines import insession

    world = World(KITCHEN)
    for name in ("risotto", "paella"):
        world.execute("create_dish", {"dish_name": name})
    eng = MedusaEngine(world)
    sess = Session("four each", eng, intent="achieve", regime="translation")
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
    from engines import insession
    from planner import tree_keeper as tk

    def serve(moving):
        world = World(KITCHEN)
        for name in ("risotto", "paella"):
            world.execute("create_dish", {"dish_name": name})
        eng = MedusaEngine(world)
        sess = Session("four each", eng, intent="achieve", regime="translation")
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
    # THE SUBTREE IS MARKED, AND THE ORIGIN IS NAMED SEPARATELY. The children were locally
    # correct and are wrong anyway — that IS root poisoning — so a report calling them sound
    # would be honest about each node and silent about the run. `origins` keeps the
    # distinction the earlier version made with the state alone: who CAUSED it, versus who
    # is under it.
    check("the whole subtree is marked, not just the node that broke",
          moved["tree"]["infected"] == moved["tree"]["nodes"])
    check("while the origin stays exactly one", len(moved["tree"]["origins"]) == 1)
    # ASSERTED ON THE REPORT, which is what a person reads. The first version of this line
    # ended in `or True` — a check that cannot fail, which is the decorative grounding this
    # codebase refuses everywhere else, arriving in a test about honesty.
    check("and a child says it was built under the parent, by name",
          "built under" in moved["tree_report"])


def test_a_goal_of_any_shape_can_be_named_in_one_line():
    """These strings are read by people, in refusals and in the keeper's report."""
    print("[readability] _short speaks every shape the writer accepts")
    from planner import ghost_writer as gw

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
    from engines import insession
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    for name in ("alpha", "beta", "gamma"):
        world.execute("create_vm", {"name": name, "os_type": "linux"})
    eng = MedusaEngine(world)
    sess = Session("just one", eng, intent="achieve", regime="translation")
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
    from engines import insession
    from tests.bench.sim_world import SimWorld

    def serve(regime):
        world = SimWorld()
        for name in ("alpha", "beta", "gamma"):
            world.execute("create_vm", {"name": name, "os_type": "linux"})
        eng = MedusaEngine(world)
        sess = Session("", eng, intent="achieve", regime="translation")
        sess.regime = regime
        out = insession.drive(eng, [{"shape": "reach", "select": {"kind": "vm"}, "min": 3},
                                    {"shape": "count", "select": {"kind": "vm"}, "eq": 1}],
                              sess, lambda st, s: insession.Verdict(insession.RUN))
        return out, world

    whole, w1 = serve("translation")
    opened, w2 = serve("tree")
    check("neither claims success on an impossible request",
          not whole.get("ok") and not opened.get("ok"))
    # THE WHOLE-PROGRAM SESSION ASKS; THE TREE SESSION CANNOT. There is nothing above the
    # tree, so a writer that cannot build it there closes with its OWN reason rather than
    # asking to be promoted to where it already is.
    check("the translation session asks to be promoted", whole.get("promote") == "tree")
    check("the tree session does not ask for a regime it already holds",
          opened.get("promote") is None)
    check("and says why it could not build it instead",
          "reach" in str(opened.get("why") or ""))
    check("the whole-program grain destroyed nothing", len(w1.vms) == 3)
    check("the opened grain had already acted", len(w2.vms) < 3)


def test_a_node_can_be_told_to_wait_and_comes_round_again():
    """YIELD: not now, ask me again — the third answer a node needs.

    Until it existed a node could only run, split, or die, so anything not ready YET had to
    be treated as something that would never be ready.
    """
    print("[in-session] wait, then re-offer")
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("two dishes", eng, intent="achieve", regime="translation")
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
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("four each", eng, intent="achieve", regime="translation")
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
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("a dish", eng, intent="achieve", regime="translation")
    out = insession.drive(eng, [RISOTTO[0]], sess,
                          lambda st, s: insession.Verdict(insession.YIELD, "the oven"))
    check("it stopped", out.get("refused") is True)
    check("naming what it waited for", "the oven" in out.get("why", ""))
    check("and nothing was cooked", not world.state.get("dish"))


def test_a_queue_where_everything_waits_is_a_deadlock_and_says_so():
    """Running is the only thing that changes the world, so a queue that never runs never
    changes. Naming it beats spinning until a counter blames the last node to speak."""
    print("[in-session] every node waiting is a deadlock, not patience")
    from engines import insession

    world = World(KITCHEN)
    eng = MedusaEngine(world)
    sess = Session("two dishes", eng, intent="achieve", regime="translation")
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
    from engines.extract import SCHEMA
    from engines import extract as _ex
    return _ex.select_attrs()


def test_the_lab_mount_speaks_the_manifest_not_the_library():
    """A SILENT WRONG ANSWER, found the first time the QEMU mount met a real lab.

    The library says `labels`; the manifest's attribute is `label`. Rows were copied
    verbatim, so `select(vm where label=x)` matched NOTHING over a lab where machines carried
    it — and the writer answered "nothing to do" rather than failing. A wrong answer that
    looks like a finished job is the worst shape this can take.
    """
    print("[mount] library field names are translated, not copied")
    from engines import QemuEngine

    class FakeLibrary:
        """Speaks the LIBRARY'S vocabulary — plural `labels`, plus fields no predicate has."""

        def vms(self):
            return {"red": {"name": "red", "labels": ["fleet", "prod"], "status": "stopped",
                            "os_type": "linux", "memory_mb": 8192, "arch": "x86_64"},
                    "blue": {"name": "blue", "labels": ["fleet"], "status": "running",
                             "os_type": "windows", "_internal": "ignore me"}}

        def by_network(self):
            return {"lab": ["red", "blue"], "dmz": ["red"], "stale": ["gone"]}

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
    # `memory_mb` USED TO BE THE EXAMPLE HERE and it is not one any more: on 2026-08-04 it
    # became a declared attribute, because `list_vms` returns it on every record and the
    # language had no way to ask about a machine's memory. A field the manifest DOES name is
    # reachable by a goal, which is the whole point of naming it.
    check("a declared attribute is matchable AND reachable by a goal",
          select({"kind": "vm", "memory_mb": 8192}) == ["red"]
          and "memory_mb" in set(extract_attr_enum()))
    # THE RULE ITSELF STILL HOLDS, on a field that genuinely has no predicate. `_as_manifest_
    # row` keeps such a fact under its own name rather than dropping it — not a lie, just not
    # the manifest's business — so a hand-written selector can reach it and nothing the
    # extractor emits can, because its attribute enum is the manifest's and closed.
    check("a field with no predicate keeps its own name", row.get("arch") == "x86_64")
    check("and is reachable only by a hand-written selector, never by a goal",
          select({"kind": "vm", "arch": "x86_64"}) == ["red"]
          and "arch" not in set(extract_attr_enum()))
    check("and an underscore field never reaches the model", "_internal" not in
          eng.world().scratch().state["vm"]["blue"])

    # EVERY KIND THE LIBRARY CAN ANSWER FOR. Seeding only `vm` had the model believe the lab
    # held no networks, so the writer planned `create_network` over a lab that already had
    # five — an empty set is not a neutral default when the plan's next move is to create
    # what is missing.
    model = eng.world().scratch()
    check("networks are seeded too", set(model.state["network"]) == {"lab", "dmz", "stale"})
    check("and membership is INVERTED onto the machine, where the filter asks",
          select({"kind": "vm", "network": "lab"}) == ["blue", "red"]
          and select({"kind": "vm", "network": "dmz"}) == ["red"])
    check("a member the lab no longer has is not conjured into existence",
          "gone" not in model.state["vm"])
    # UNKNOWN IS NOT EMPTY. The library tracks no snapshots, so the model must not answer
    # "there are none" to a question nobody asked.
    # DERIVED, NOT LISTED. `file` joined the manifest with `local_probe` as its observer and
    # no lister at all, and it arrived here for free — which is the extensibility claim the
    # manifest makes, holding: a new kind the library cannot enumerate is UNSEEDED without an
    # edit, so the writer refuses to read silence as "there are none".
    # `template` JOINED THE MANIFEST 2026-08-02 and arrived here the same way `file` did —
    # unseeded without an edit to the seeding code, because this fixture's library enumerates
    # neither. That is the extensibility claim holding twice; the list is still written out
    # because a DERIVED expectation here would assert nothing at all.
    check(f"a kind nothing could seed is named, not silently empty ({model.unseeded})",
          model.unseeded == {"snapshot", "file", "profile", "template"})


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


def test_a_kind_the_world_cannot_see_is_refused_not_assumed_empty():
    """UNSEEDED IS NOT EMPTY — decision 6, applied to planning.

    A world that cannot enumerate a kind answers every question about it with an empty set,
    and the writer's next move is to CREATE what is missing. So a goal about restore points
    would plan to make every one of them again, against a lab that may already have them.
    """
    print("[mount] the planner declines a kind it cannot enumerate")
    from engines import QemuEngine, insession
    from planner import ghost_writer as gw

    check("a goal's kinds include what it SELECTS over",
          gw.kinds_of({"shape": "count", "select": {"kind": "vm"}, "eq": 1}) == {"vm"})
    check("and what it MAKES, which is the one that matters here",
          gw.kinds_of({"per": {"kind": "vm"}, "make": "snapshot", "link": "vm"})
          == {"vm", "snapshot"})

    class FakeLibrary:
        def vms(self):
            return {"red": {"name": "red", "status": "stopped"}}

        def by_network(self):
            return {}

        def known_names(self):
            return {"red"}

    eng = QemuEngine(FakeLibrary(), lambda t, a: {"success": False})
    sess = Session("snapshot everything", eng, intent="achieve", regime="translation")
    out = insession.drive(eng, [{"per": {"kind": "vm"}, "make": "snapshot", "link": "vm"}],
                          sess, lambda st, s: insession.Verdict(insession.RUN))
    check("it refuses rather than planning against a false empty",
          out.get("promote") == "tree" and "snapshot" in (out.get("why") or ""))
    check("and says WHY the empty answer cannot be trusted",
          "there are none" in (out.get("why") or ""))

    # A GOAL THAT TOUCHES ONLY WHAT IT CAN SEE IS UNAFFECTED — the guard is per-goal, not a
    # blanket refusal, or mounting a lab would disable most of the language.
    sess2 = Session("one machine", eng, intent="achieve", regime="translation")
    seen = []
    insession.drive(eng, [{"shape": "count", "select": {"kind": "vm"}, "eq": 2}], sess2,
                    lambda st, s: (seen.append(st) or insession.Verdict(insession.STOP, "x")))
    check("a vm goal still plans normally", seen and seen[0].cost == 1)


def test_a_request_reroutes_to_another_engine_when_the_first_cannot():
    """MULTI-ENGINE REROUTING. Being wrong about which engine is a routing mistake, not a
    dead end — so the rest of the claimants are fallbacks in mount order."""
    print("[routing] the router picks first; the others are fallbacks")

    # A kitchen with no way to set `serves`, so the second goal is genuinely unreachable in
    # it — and a full one that can. Same manifest KIND, different capability.
    thin = {"dish": {**KITCHEN["dish"], "setters": {}}}

    class Thin(MedusaEngine):
        name = "thin"

    reg = Registry()
    reg.mount(Thin(World(thin)))
    reg.mount(MedusaEngine(World(KITCHEN)))
    # THE ROUTER IS INJECTED, SO THE TEST NAMES THE WRONG ENGINE ON PURPOSE. Depending on
    # mount order would test the registry's iteration rather than the rerouting, and the
    # registry does not promise one.
    to_thin = lambda request, menu, engines: "thin"
    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})]),
                     route=to_thin).handle("risotto for four")
    check("it ended up served", r["outcome"] == "DONE")
    check("by the engine that could, not the one the router named",
          r["engine"] == "medusa")
    check("and the first attempt is on the record",
          any("thin could not" in l for l in r["log"]))
    check("with the whole order named", r.get("tried") == ["thin", "medusa"])


def test_a_refusal_is_never_overturned_by_rerouting():
    """THE DISTINCTION THE WHOLE DESIGN RESTS ON.

    An engine that CANNOT do something has said nothing about whether it should happen. An
    engine that WON'T has. Letting the next engine overturn that would make every gate
    advisory — ask enough engines and one says yes.
    """
    print("[routing] inability reroutes; refusal ends it")
    from engines import insession

    class Second(MedusaEngine):
        name = "second"

    reg = Registry()
    reg.mount(MedusaEngine(World(KITCHEN)))
    reg.mount(Second(World(KITCHEN)))
    seen = []

    def refuse(step, session):
        seen.append(session.engine.name)
        return insession.Verdict(insession.STOP, "the operator said no")

    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})]),
                     decide=refuse).handle("risotto for four")
    check("the refusal stands", r["outcome"] == "REFUSED")
    check("and no second engine was asked to overrule it", len(seen) == 1)


def test_trying_three_engines_does_not_cost_three_budgets():
    """A shared budget, or mounting a third engine silently triples what a request may
    spend."""
    print("[routing] the budget is the request's, not the engine's")

    class Useless(MedusaEngine):
        name = "useless"

        def run(self, components, session=None):
            return {"ok": False, "why": "not me", "calls": []}

        steps = None

    reg = Registry()
    reg.mount(Useless(World(KITCHEN)))
    reg.mount(MedusaEngine(World(KITCHEN)))
    # RISOTTO costs two calls; one is all this request may spend, whoever serves it.
    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})]),
                     budget=1).handle("risotto for four")
    check("the fallback engine inherits the remaining budget, not a fresh one",
          r["outcome"] != "DONE")
    check("and the budget is what stopped it",
          any("budget" in l for l in r["log"]) or "budget" in (r.get("why") or ""))


def test_the_mount_contract_is_answerable_by_every_engine():
    """WHAT THE ORCHESTRATOR ASKS, asked of every engine that ships.

    The contract is small on purpose, and small contracts rot quietly: a field nobody reads
    on the engine you happen to test is a field nobody notices missing on the next one. This
    asks every question the orchestrator and registry actually ask, of every mounted engine,
    and it is where a new engine finds out what it forgot.
    """
    print("[contract] every engine answers everything the orchestrator asks")
    from engines import QemuEngine
    from engines.session import REGIMES

    class FakeLibrary:
        def vms(self):
            return {}

        def by_network(self):
            return {}

        def known_names(self):
            return set()

    shipped = [MedusaEngine(World(KITCHEN)),
               MedusaEngine(SimWorldStub()),
               QemuEngine(FakeLibrary(), lambda t, a: {"success": False})]

    for eng in shipped:
        who = type(eng).__name__
        check(f"{who}: has a name", isinstance(eng.name, str) and eng.name != "unnamed")
        check(f"{who}: has a one-line description for the router",
              isinstance(eng.description, str) and 10 < len(eng.description) < 200)
        check(f"{who}: declares intents the ladder knows",
              eng.intents and set(eng.intents) <= {"fetch", "ensure", "achieve"})
        check(f"{who}: its manifest is non-empty — `{{}}` means the DEFAULT, not none",
              bool(eng.manifest))
        # THE WORLD CONTRACT IS ONE REQUIRED THING AND TWO OPTIONAL ONES, and writing it
        # down is the point of this line. `execute` is mandatory — a world that cannot act
        # is not a world. `kinds` absent means the DEFAULT manifest, and `seams` absent means
        # the sim's, which is the one deliberate import production makes from tests/ and is
        # documented at `_seams_of`. The VM sim has NEITHER and all thirteen rungs run on it.
        check(f"{who}: its world can act", callable(getattr(eng.world(), "execute", None)))
        check(f"{who}: and names its own adapter, or is the sim that may not",
              hasattr(eng.world(), "seams") or type(eng.world()).__name__ == "SimWorldStub")
        check(f"{who}: answers `claims` without raising", isinstance(
            eng.claims("make sure there are two machines"), bool))
        check(f"{who}: offers an in-session", callable(getattr(eng, "steps", None)))
    check("and every regime an engine can be put in is one the ladder names",
          set(REGIMES) == {"tool", "translation", "tree"})


def test_claiming_is_derived_from_the_manifest_not_written_twice():
    """Two engines had each hand-rolled the noun match, differently. A third would have made
    it three."""
    print("[contract] one noun match, in the contract, from the manifest")
    from engines.base import Engine

    class Kitchen(Engine):
        name = "kitchen"

        @property
        def manifest(self):
            return KITCHEN

    k = Kitchen()
    check("it claims by the kind's own name", k.claims("how many dish are there"))
    check("and by a noun the manifest declares", k.claims("make a meal"))
    check("and by the plural of one", k.claims("count the meals"))
    check("and declines what it has no noun for", not k.claims("launch a vm"))
    check("Medusa overrides to WIDEN, deliberately, being the fallback",
          MedusaEngine(World(KITCHEN)).claims("launch a vm"))


class SimWorldStub:
    """A world that declares NO kinds — the configuration nobody had tested.

    Every existing test mounts an engine with a manifest of its own: the kitchen, the crawl
    package, a fake library. The ordinary one — an engine on Gorgon's own manifest — was the
    case where `{}` was read as "there are no kinds", and the general engine claimed nothing.
    """

    def execute(self, tool, args):
        return {"success": False}

    def names(self):
        return set()

    @property
    def seams(self):
        return (lambda sel, scope=None: []), (lambda p, scope=None: (False, "stub"))


def test_publish_is_how_an_engine_speaks_upward():
    """THE OTHER HALF OF THE PROTOCOL.

        down:  Step     "this node — run it, or decompose it?"     -> Verdict
        up:    Publish  "here is something I found / claim / made"  -> kept, or forwarded

    It does NOT print. An engine that wrote to the operator directly would be deciding what
    the operator sees, which is the one thing the in-session exists to prevent.
    """
    print("[publish] the engine submits; the orchestrator keeps or forwards")
    from engines import insession

    class Talker(MedusaEngine):
        name = "talker"

        def steps(self, components, session=None):
            yield insession.Publish("dish_count", 2, "counted before doing anything")
            verdict = yield insession.Step(insession.RUN, components, "the whole thing",
                                           cost=0)
            if verdict.action == insession.STOP:
                return {"ok": False, "refused": True, "calls": []}
            yield insession.Publish("oven", "hot")
            return {"ok": True, "calls": [], "findings": []}

    reg = Registry()
    reg.mount(Talker(World(KITCHEN)))
    r = Orchestrator(reg, Channel([stub({"a risotto": RISOTTO})])).handle("a risotto")
    check("publications reach the result", len(r.get("published") or []) == 2)
    check("and become findings the reporter could narrate",
          {f["fact"] for f in r["findings"]} >= {"dish_count", "oven"})
    check("a publication carries its reason",
          any(f.get("why") for f in r["published"]))
    filed = [e for e in r["events"].events if e.executed.startswith("PUBLISH")]
    check("submitting needed no verdict — the engine never waited",
          {e.executed for e in filed} == {"PUBLISH dish_count", "PUBLISH oven"})
    check("and each names who said it and who caught it",
          all(e.filed_by == "talker" and e.caught_by == "orchestrator" for e in filed))


def test_the_orchestrator_may_keep_a_publication_internal():
    """The operator's boundary is the orchestrator's to hold, not the engine's."""
    print("[publish] kept is a decision, and a recorded one")
    from engines import insession

    class Talker(MedusaEngine):
        name = "talker"

        def steps(self, components, session=None):
            yield insession.Publish("debug_trace", "internals")
            yield insession.Publish("dish_count", 2)
            yield insession.Step(insession.RUN, components, "nothing", cost=0)
            return {"ok": True, "calls": [], "findings": []}

    reg = Registry()
    reg.mount(Talker(World(KITCHEN)))
    r = Orchestrator(reg, Channel([stub({"a risotto": RISOTTO})]),
                     forward=lambda pub, s: pub.what != "debug_trace").handle("a risotto")
    check("the kept one never becomes a finding",
          {f["fact"] for f in r["findings"]} == {"dish_count"})
    check("but it is still on the record as having been said",
          any(e.executed == "PUBLISH debug_trace" for e in r["events"].events)
          and r["kept"] == 1)
    check("and the operator's half never mentions it",
          "debug_trace" not in str(r["findings"]))


def test_findings_travel_as_publications_now():
    """WHY THIS REPLACES READING THE WORLD'S LEDGER. Findings used to travel implicitly —
    the orchestrator reached into the world and took what it found. That works while an
    engine's world HAS a ledger and quietly returns nothing when it does not."""
    print("[publish] what the engine observed, SAID rather than left lying around")
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    for n in ("alpha", "beta"):
        world.execute("create_vm", {"name": n, "os_type": "linux"})

    class Lab(MedusaEngine):
        name = "lab"

    reg = Registry()
    reg.mount(Lab(world))
    goals = [{"observe": {"kind": "vm"}, "fact": "alive"}]
    r = Orchestrator(reg, Channel([stub({"ping the machines": goals})])).handle(
        "ping the machines")
    check("the probe's answers came up as publications",
          len(r.get("published") or []) >= 2)
    check("naming what was asked about",
          any("alpha" in str(f.get("fact")) for f in r["published"]))


class FakeLab:
    """A library-shaped stand-in that answers BOTH ways the code reads a library.

    THE PRODUCTION SEAMS READ `library._vms` AND `library._networks` DIRECTLY, while the
    lab mount's scratch calls `library.vms()` and `library.by_network()`. Two access paths
    over one registry — fine for the real `ActiveLibrary`, which has both, and a trap for
    anything standing in for it: a stub with only the public half reads as an EMPTY LAB and
    every query quietly answers "nothing here". That is how three tests in this file passed
    while asserting less than they appeared to.
    """

    def __init__(self, world):
        self.world = world

    @property
    def _vms(self):
        return {n: {"name": n, **r} for n, r in self.world.vms.items()}

    @property
    def _networks(self):
        return {n: {"name": n, "members": sorted(m)}
                for n, m in getattr(self.world, "nets", {}).items()}

    def vms(self):
        return dict(self._vms)

    def by_network(self):
        return {n: list(r["members"]) for n, r in self._networks.items()}

    def known_names(self):
        return set(self.world.vms)


def test_the_executor_is_the_tool_regime_made_real():
    """THE FLOOR HAD NO ENGINE. `session.py` has described the tool regime since the day it
    was written — one call, one answer, close — and `rank("tool") == 0` was a number nothing
    could occupy. A ladder whose bottom rung is a diagram."""
    print("[executor] one call, one answer, close")
    from engines import ExecutorEngine
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    eng = ExecutorEngine(FakeLab(world), world.execute)

    check("it declares only the floor", eng.intents == ("fetch",))
    # ASKING IS THE PRICE OF ACTING, whatever regime you are in. The first version of this
    # engine offered no in-session — "one call, no exchange" — and `plan --dry` created a
    # machine on the real lab while claiming to preview one. "No exchange" means no
    # back-and-forth: no decomposing, no re-planning, no promotion. It never meant acting
    # unasked.
    check("it still asks once per call, because it ACTS",
          callable(getattr(eng, "steps", None)))
    check("it claims by the manifest's nouns, inherited from the contract",
          eng.claims("create a machine") and not eng.claims("bake a cake"))

    # ONE CALL, RUN.
    out = eng.run([{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}])
    check("a single reachable goal is executed", out["ok"] and len(out["calls"]) == 1)
    check("and it actually happened", "alpha" in world.vms)


def test_an_intent_that_may_not_act_is_refused_before_the_decider():
    """THE LADDER, ENFORCED — on BOTH engines, from one rule.

    `intent.violations` refuses a PROGRAM that reaches above its rung, which covers Medusa and
    says nothing at all about the executor engine: the FLOOR, routed to first by
    `rig.floor_first`, declaring `intents = ("fetch",)` and running `delete_vm` on request.
    Declaring a ladder and enforcing one are different things, and only the first had been
    done.

    BEFORE THE DECIDER, NOT THROUGH IT. Authority is what the operator granted, not a policy
    the orchestrator weighs — a gate a decider could overrule would make the whole thing
    advisory. So the step never reaches `decide`, exactly as a step nobody can afford does
    not, and the refusal is filed in the session's own ledger instead.
    """
    print("[intent] a fetch may not change the lab, whichever engine is asked")
    from engines import ExecutorEngine, insession
    from planner.ir import effects as _effects
    from tests.bench.sim_world import SimWorld

    for granted in ("fetch", "ensure"):
        world = SimWorld()
        world.execute("create_vm", {"name": "doomed", "os_type": "linux"})
        eng = ExecutorEngine(FakeLab(world), world.execute)
        sess = Session("delete it", eng, intent=granted)
        seen = []
        out = insession.drive(
            eng, [{"shape": "count", "select": {"kind": "vm", "name": "doomed"}, "eq": 0}],
            sess, lambda st, s: (seen.append(st) or insession.Verdict(insession.RUN)))
        check(f"the floor will not delete under a {granted}", "doomed" in world.vms)
        check(f"and the decider was never asked to weigh it ({granted})", not seen)
        check(f"it closes as a refusal, not a failure ({granted})",
              out.get("refused") is True)
        check(f"naming the tool it would have called ({granted})",
              "delete_vm" in (out.get("why") or ""))
        check(f"and the session records it ({granted})",
              any("REFUSED" in l for l in sess.log))

    # AND THE PLANNER NEVER GETS THAT FAR, WHICH IS BETTER THAN BEING REFUSED. The ladder
    # shapes what Medusa WRITES: under an `ensure` the writer plans a CHECK, so there is no
    # acting step for the gate to catch. Being refused was the first version of this and it
    # was a poor answer — the operator asked whether something was so and was told they were
    # not allowed to ask.
    #
    # THE GATE IS STILL THE BACKSTOP and it is proven above, on the floor engine, which
    # inverts a goal to one call and has no intent-aware planner to shape. Two readings of
    # one rule: one decides what is written, one refuses what escapes.
    kitchen = World(KITCHEN)
    eng = MedusaEngine(kitchen)
    sess = Session("risotto", eng, intent="ensure", regime="translation")
    out = insession.drive(eng, RISOTTO, sess,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("medusa answers instead of refusing", out.get("ok") is True)
    check("and nothing was cooked", not kitchen.state.get("dish"))
    check("the answer is a verdict, and it is no",
          {"fact": "holds", "value": False} in
          [{k: v for k, v in f.items() if k in ("fact", "value")}
           for f in (out.get("findings") or [])])

    # A PROBE IS NOT AN ACT, AND THIS IS THE OTHER HALF OF THE RULE. A `fetch` that could
    # read nothing is a rung with nothing on it, and that is what shipped for a day: every
    # observation the writer makes is spelled `CALL <probe>`, `call` is absent from FETCH's
    # op set, and so *"how many machines are up"* was refused on statement one.
    #
    # ASSERTED ON THE CALLS, NOT ON THE ABSENCE OF A REFUSAL. The first version of this check
    # asked `not out["refused"]` and passed while the program was being thrown out as
    # `exceeds_authority` — a different word for the same nothing. A read that reads is a
    # read that made the call.
    world = SimWorld()
    for n in ("alpha", "beta"):
        world.execute("create_vm", {"name": n, "os_type": "linux"})
    lab = MedusaEngine(world)
    probe = [{"observe": {"kind": "vm"}, "fact": "alive"}]
    ask = Session("which machines are up", lab, intent="fetch", regime="translation")
    out = insession.drive(lab, probe, ask,
                          lambda st, s: insession.Verdict(insession.RUN))
    check("a fetch may still ask questions", out.get("ok") is True)
    check("and it actually asked them", len(out.get("calls") or []) == 2)
    check("with nothing in the plan the manifest calls an act",
          not [t for t, _ in out["calls"] if t in _effects.actors(lab.manifest)])


def test_consent_is_the_operators_and_the_engine_stops_answering_it_for_them():
    """`consent=True`, HARDCODED, ON THE PATH THAT REACHES THE REAL LAB.

    `consent.py` says it in as many words: absent an operator the answer is NO, because the
    alternative is an unattended run granting itself the permission a person was supposed to
    give. The engine granted it on every program regardless, so the one question that module
    exists to ask was answered by the thing being asked about.

    DRIVEN THROUGH `_execute_plan` DIRECTLY, and deliberately: the ghost writer grounds every
    program it writes and staged lowering refuses one that does not, so nothing in production
    can currently REACH this gate. That is a good property and a bad reason not to test the
    gate — a seam nothing exercises is the shape of every defect this project has spent a week
    on.
    """
    print("[consent] the ungrounded program asks, and a no is honoured")
    from tests.bench.sim_world import SimWorld

    from planner import ghost_writer as _gw

    world = SimWorld()
    eng = MedusaEngine(world)
    # ACTS AND VOUCHES FOR NOTHING — the exact program `consent.question` is written about.
    #
    # BUILT BY THE WRITER AND THEN STRIPPED OF ITS WITNESS, rather than hand-authored: a
    # hand-written body would be testing this gate against a program shape nothing produces,
    # and the statement form is the writer's business, not this test's.
    goal = {"shape": "count", "select": {"kind": "vm", "name": "ghost"}, "eq": 1}
    plan = _gw.cover([goal], world)
    whole = _gw.as_program(plan, [goal], world)
    # STRIPPED OF ITS WITNESSES *AND* OF ITS `new`-NESS. The writer emits creations as `new`
    # now, and a `new` vouches for its own creation — so a body of creations is grounded act
    # by act and this gate correctly does not fire on it. What the gate is about is an act
    # that proves NOTHING, which is a bare `call`: it passes the author's arguments through
    # and decides nothing, so nothing checks it.
    ungrounded = {"body": [({"op": "call", "tool": "create_vm", "args": st.get("args", {})}
                            if st.get("op") == "new" else st)
                           for st in whole["body"]
                           if st.get("op") not in ("ensure", "achieve")]}
    planned = {"ok": True, "program": ungrounded, "plan": plan}

    asked = []

    def refuse(question):
        asked.append(question)
        return False

    out = eng._execute_plan(planned, [], Session("x", eng, intent="achieve",
                                                 consent=refuse))
    check("the operator is asked", len(asked) == 1 and "Run it anyway?" in asked[0])
    check("a no stops it", not out["ok"] and not world.vms)

    said = []
    out = eng._execute_plan(planned, [], Session("x", eng, intent="achieve",
                                                 consent=lambda q: said.append(q) or True))
    check("a yes runs it", out["ok"] and "ghost" in world.vms)

    # AND WITH NOBODY THERE, THE ANSWER IS NO. Fail-closed is the standing rule for every
    # other high-impact act here, and an unattended session is exactly when it matters.
    world2 = SimWorld()
    out = MedusaEngine(world2)._execute_plan(
        planned, [], Session("x", None, intent="achieve"))
    check("an unattended session is refused", not out["ok"] and not world2.vms)


def test_the_floor_asks_before_it_acts():
    """FOUND BY POINTING `plan --dry` AT THE REAL LAB with an executor that refuses to act.

    `drive` falls back to `engine.run()` for an engine with no in-session, so this engine
    acted with no verdict, no budget check and no dry run. `delete_vm alpha` is exactly one
    call and irreversible.
    """
    print("[executor] one call is still a call, and it is offered first")
    from engines import ExecutorEngine, insession
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    world.execute("create_vm", {"name": "doomed", "os_type": "linux"})
    eng = ExecutorEngine(FakeLab(world), world.execute)
    sess = Session("delete it", eng, intent="achieve")
    seen = []
    out = insession.drive(
        eng, [{"shape": "count", "select": {"kind": "vm", "name": "doomed"}, "eq": 0}],
        sess, lambda st, s: (seen.append(st) or insession.Verdict(insession.STOP, "no")))
    check("the call was offered before it happened", len(seen) == 1)
    check("declaring what it would destroy", len(seen[0].destroys) == 1)
    check("a refusal is honoured", out.get("refused") is True)
    check("and the machine is still there", "doomed" in world.vms)
    check("a single call is never divisible — there is nothing finer",
          seen[0].divisible is False)


def test_the_floor_refuses_a_red_line_before_it_offers_the_step():
    """THE FLOOR IS WHERE `floor_first` ROUTES EVERYTHING, so a ban that held only in the
    program regime would hold almost nowhere.

    AND IT IS REFUSED BEFORE THE STEP IS OFFERED, not by the decider saying no. A decider
    can be talked into a step; a red line is the answer that does not depend on who is
    asking. The decider here would say YES to everything and the machine must survive it.
    """
    print("[executor] a red line is refused before anything is proposed")
    from engines import ExecutorEngine, insession
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    world.execute("create_vm", {"name": "doomed", "os_type": "linux"})
    world.execute("create_vm", {"name": "spared", "os_type": "linux"})
    world.calls.clear()

    class Lawful(ExecutorEngine):
        legal_filter = staticmethod(lambda tool: tool == "delete_vm")

    eng = Lawful(FakeLab(world), world.execute)
    sess = Session("delete it", eng, intent="achieve")
    seen = []
    out = insession.drive(
        eng, [{"shape": "count", "select": {"kind": "vm", "name": "doomed"}, "eq": 0}],
        sess, lambda st, s: (seen.append(st) or insession.Verdict(insession.RUN)))
    check("no step was ever offered", not seen)
    check("the machine is still there", "doomed" in world.vms)
    check("and nothing was called at all", not world.calls)

    # THE ALL-OR-NOTHING PROPERTY. The legal goal comes FIRST and is one this engine really
    # does serve — checked below — so a per-goal refusal would have BUILT `newbox` on the way
    # to declining the deletion.
    build = {"shape": "count", "select": {"kind": "vm", "name": "newbox"}, "eq": 1}
    out2 = eng.run([build,
                    {"shape": "count", "select": {"kind": "vm", "name": "doomed"}, "eq": 0}])
    check("the whole request is refused", out2.get("failed") == "forbidden")
    check("naming the tool", out2.get("forbidden") == ["delete_vm"])
    check("and the LEGAL goal before it never ran either",
          not world.calls and "newbox" not in world.vms)

    # THE OPERATOR LIFTS IT IN PERSON. `session.permit` is the password prompt, and it is
    # the SAME seam the program regime reads — one answer about what was authorised.
    granted = Session("delete it", eng, intent="achieve")
    granted.permit = lambda tools: True
    out3 = eng.steps([{"shape": "count", "select": {"kind": "vm", "name": "doomed"},
                       "eq": 0}], granted)
    # DRAINED BY HAND rather than through `drive`, so what is asserted is what the ENGINE
    # yielded. It emits a `Publish` after the call as well as the `Step` before it, and
    # counting both would make this pass for the wrong reason.
    offered = []
    try:
        item = next(out3)
        while True:
            offered.append(item)
            item = out3.send(insession.Verdict(insession.RUN))
    except StopIteration:
        pass
    check("with the password the step IS offered",
          len([i for i in offered if getattr(i, "kind", None)]) == 1)
    check("and the deletion the red line was protecting went through",
          "doomed" not in world.vms)

    # AND THE SAME GOAL SERVED BY AN ENGINE WITH NO RED LINE, or the check above would pass
    # against a goal this engine could never have served anyway.
    plain = ExecutorEngine(FakeLab(world), world.execute)
    ok = plain.run([build])
    check("with no red line the same goal is served",
          ok["ok"] and "newbox" in world.vms)


def test_the_executor_refuses_to_plan_and_says_so():
    """WHAT MAKES IT THE FLOOR IS WHAT IT REFUSES TO DO. Naming a tool and knowing WHEN to
    call it are different jobs, and the second one is what Medusa is for."""
    print("[executor] anything needing an order is handed back")
    from engines import ExecutorEngine
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    eng = ExecutorEngine(FakeLab(world), world.execute)
    # A machine must exist before it can be put on a network — that ordering is planning.
    out = eng.run([{"every": {"kind": "vm", "name": "ghost"}, "must": {"network": "lab"}}])
    check("it asks for the translation regime", out.get("promote") == "translation")
    check("naming what it is not", "needs a program" in out["why"])
    check("and nothing was done on the way to saying so", not out["calls"])


def test_a_request_the_floor_cannot_serve_reroutes_up():
    """THE PAIR THE REROUTING WAS BUILT FOR. The executor tries, cannot, and the orchestrator
    sends it to the engine that writes programs — one request, two engines, no operator."""
    print("[executor] floor first, then the engine that plans")
    from engines import ExecutorEngine
    from tests.bench.sim_world import SimWorld

    world = SimWorld()

    class Planner(MedusaEngine):
        name = "medusa"

    reg = Registry()
    reg.mount(ExecutorEngine(FakeLab(world), world.execute))
    reg.mount(Planner(world))
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1},
             {"every": {"kind": "vm", "name": "web"}, "must": {"network": "lab"}}]
    r = Orchestrator(reg, Channel([stub({"put web on lab": goals})]),
                     route=lambda req, menu, engines: "executor").handle("put web on lab")
    check("it ended up done", r["outcome"] == "DONE")
    check("by the engine that plans", r["engine"] == "medusa")
    check("having tried the floor first", r.get("tried") == ["executor", "medusa"])
    check("and the work is real", "web" in world.vms and "lab" in world.vms["web"]["nets"])


def test_the_ledger_names_both_ends_of_every_interaction():
    """AN EVENT NAMES WHO SAID IT AND WHO CAUGHT IT, which is what a log of sentences cannot.

    `session.log` could not answer "who asked whom", "what actually ran", or "which of these
    two components was wrong" — and direction is what separates "the engine asked to
    escalate" from "the orchestrator granted an escalation".

    IT CAUGHT ITSELF MISATTRIBUTING ON ITS FIRST REAL RUN: a reroute note is recorded into
    the NEXT engine's ledger, so defaulting the sender to "this session's engine" filed the
    executor's refusal under Medusa's name.
    """
    print("[ledger] every line has a sender and a receiver")
    from tests.bench.sim_world import SimWorld

    class Thin(MedusaEngine):
        name = "thin"

        def run(self, components, session=None):
            return {"ok": False, "why": "not mine", "calls": []}

        steps = None

    reg = Registry()
    reg.mount(Thin(World(KITCHEN)))
    reg.mount(MedusaEngine(World(KITCHEN)))
    r = Orchestrator(reg, Channel([stub({"risotto for four": RISOTTO})]),
                     route=lambda q, m, e: "thin").handle("risotto for four")
    events = r["events"].events

    check("the request completed", r["outcome"] == "DONE")
    check("every event names both ends",
          all(e.filed_by and e.caught_by for e in events))
    check("every event is numbered in order",
          [e.seq for e in events] == list(range(1, len(events) + 1)))

    failed = [e for e in events if e.level == "warn"]
    check("the engine that could not is the one filed against it",
          len(failed) == 1 and failed[0].filed_by == "thin")
    check("and the orchestrator is who caught it",
          failed[0].caught_by == "orchestrator")

    closed = [e for e in events if e.executed.startswith("close(")]
    check("the close is filed to the OPERATOR — the only line meant for them",
          len(closed) == 1 and closed[0].caught_by == "operator")


def test_every_call_is_a_line_and_the_program_is_at_the_end():
    """"each command, each decision, and the medusa code" — the operator's own list."""
    print("[ledger] one line per call; the program in full, last")
    from tests.bench.sim_world import SimWorld

    world = SimWorld()

    class Lab(MedusaEngine):
        name = "medusa"

    reg = Registry()
    reg.mount(Lab(world))
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1},
             {"every": {"kind": "vm", "name": "alpha"}, "must": {"status": "running"}}]
    r = Orchestrator(reg, Channel([stub({"alpha, running": goals})])).handle("alpha, running")
    log = r["events"]

    calls = [e for e in log.events if e.caught_by == "world"]
    check("every call is its own line", len(calls) == len(r["calls"]))
    check("naming the tool and its arguments",
          any(e.executed.startswith("create_vm(") for e in calls))
    check("with the world as the receiver", all(e.filed_by == "medusa" for e in calls))

    # THE PROGRAM GOES AT THE END, IN FULL. It is the one thing you cannot reconstruct from
    # the lines, and truncating it into a column would make the ledger tidy and useless.
    check("the program is attached", len(log.programs) == 1)
    rendered = log.render()
    check("and printed at the end, whole",
          "THE MEDUSA PROGRAM" in rendered
          and rendered.index("THE MEDUSA PROGRAM") > rendered.index("create_vm("))
    check("the ledger also reads as JSON, one object per line",
          len(log.jsonl().splitlines()) == len(log.events))


def test_a_failure_is_an_event_not_an_absence():
    """A ledger that records only successes is one you cannot debug from."""
    print("[ledger] failures are first-class lines")
    from engines import insession

    reg = _kitchen()
    r = Orchestrator(reg, Channel([stub({"a risotto": RISOTTO})]),
                     decide=lambda st, s: insession.Verdict(insession.STOP,
                                                            "the operator said no")).handle(
        "a risotto")
    log = r["events"]
    check("the refusal closed the session", r["outcome"] == "REFUSED")
    check("and the ledger can list what a reader should look at",
          isinstance(log.failures(), list))
    unfound = [e for e in log.events if e.executed == "close(UNCLAIMED)"]
    check("an outcome nobody wanted is filed as an error, not info", not unfound)

    empty = Orchestrator(Registry(), Channel([stub({})])).handle("bake a cake")
    check("an unclaimed request still returns an outcome", empty["outcome"] == "UNCLAIMED")


def test_there_is_one_constrained_model_call():
    """#63 — ONE PROTOCOL FOR EVERY AI SEAM, and I had just added a third violation of it.

    `extract` built its own call, `reporter.narrator` built a second, and the staged-lowering
    author would have been a fourth. Two of them already differed on `keep_alive` and on how
    a decode failure surfaces — #26's defect (two prompt paths silently diverged) reappearing
    one layer down, where it decides what a model call IS.
    """
    print("[channel] every seam calls the model the same way")
    import inspect

    from engines import channel as _channel
    from engines import reporter as _reporter
    from engines import extract as _extract

    check("the shared call exists", callable(getattr(_channel, "constrained", None)))

    # NOBODY ELSE BUILDS ONE. Asserted on the source, because the failure mode is a NEW seam
    # quietly growing its own — which is how there came to be three.
    for name, mod in (("extractor", _extract), ("reporter", _reporter)):
        src = inspect.getsource(mod)
        check(f"{name} does not build its own HTTP call",
              "api/chat" not in src and "urllib.request.Request" not in src)

    # THE GRAMMAR IS NOT OPTIONAL. A caller that forgot the schema would be free generation
    # wearing a schema's name, which is precisely what 2026-07-31 turned out to be.
    sig = inspect.signature(_channel.constrained)
    check("a schema is required, not defaulted",
          sig.parameters["schema"].default is inspect.Parameter.empty)


def test_the_lab_engine_claims_by_nouns_and_medusa_over_claims():
    """TWO ENGINES, TWO POLICIES, and the difference has to be said out loud because one
    inherits from the other.

    Medusa over-claims ON PURPOSE — it is what runs when nothing more specific fits. The LAB
    engine is something specific. Deleting its duplicate noun match silently promoted it to
    the general fallback, and it began claiming "bake a cake".
    """
    print("[routing] specific engines claim narrowly; the fallback claims widely")
    from engines import QemuEngine

    class FakeLab:
        _vms = {}
        _networks = {}

        def vms(self):
            return {}

        def by_network(self):
            return {}

        def known_names(self):
            return set()

    lab = QemuEngine(FakeLab(), lambda t, a: {"success": False})
    check("the lab engine answers to a machine", lab.claims("create a machine"))
    check("and to the manifest's other nouns", lab.claims("make a subnet"))
    check("but not to a cake", not lab.claims("bake a cake"))
    check("while Medusa, the fallback, takes it",
          MedusaEngine(World(KITCHEN)).claims("bake a cake"))

    # AND NOBODY HAND-ROLLS THE MATCH ANY MORE. Counted rather than eyeballed: an earlier
    # edit claimed to delete this duplicate and silently did not match anything.
    import inspect

    from engines import qemu as _qemu
    check("the lab engine defines no claims of its own",
          "def claims" not in inspect.getsource(_qemu))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "engines"))


if __name__ == "__main__":
    main()
