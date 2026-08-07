"""test_gates.py — the four legality gates.

GATE 1 (`planner/gates/completeness.py`) is the only one built. Its bar is not "does it catch
things" — it is **does it stay silent on a correct reading, in ANY wording**. A rule that fires
on the right answer has taught the operator to ignore it, which is why `clause-untouched` and
`inert` were demoted to reports on 2026-08-06.

So the pins here are, in order of what matters:

    1. SILENT on every known-good reading, on BOTH arms
    2. the four findings it must make, each on the shape that produced it in real traffic
    3. it never modifies a goal — a gate 1 that STRIPS is measured-destructive
    4. it is WIRED, and its verdict reaches the ledger
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.bench.rungs import RUNGS
from tests.test_ghost_writer import GOALS

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _kinds():
    from planner.ir import config as _config
    return _config.KINDS or {}


def test_gate_1_is_silent_on_every_correct_reading_in_both_wordings():
    """THE ONE THAT DECIDES WHETHER IT IS A GATE AT ALL.

    The goals are IDENTICAL on both arms — they are the one correct reading of that rung. Only
    the SENTENCE changes. A flag that appears on the paraphrase and not the literal is the rule
    keying on particular words, which is the failure the operator named: *"we don't flag the
    rung for what they are, we use them as examples for user patterns in nature."*

    **A RULE THAT STOPS WORKING WHEN THE WORDING CHANGES WAS NEVER A GATE.**
    """
    print("[gate 1] silent on the correct reading, whatever the wording")
    from planner.gates import completeness as g1

    accused, disagreed = [], []
    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if not goals:
            continue
        lit = g1.inspect(rung.goal, goals, _kinds())
        par = g1.inspect(rung.paraphrase or rung.goal, goals, _kinds())
        if not lit.legal:
            accused.append((rung.n, "lit", lit.findings()))
        if not par.legal:
            accused.append((rung.n, "par", par.findings()))
        if lit.legal != par.legal:
            disagreed.append(rung.n)
    check(f"no correct reading is accused (got {accused})", not accused)
    check(f"and the two wordings never disagree (got {disagreed})", not disagreed)


def test_gate_1_catches_the_four_things_it_exists_for():
    """One shape per finding, each taken from a reading the model really produced."""
    print("[gate 1] holes, dropped, mutated, invented")
    from engines import extract
    from planner.gates import completeness as g1

    schema = extract.schema()

    # INVENTED — the purest case, and the one that put a machine called `Not specified` on a
    # lab. The request names no such thing and the value resembles nothing in it.
    rep = g1.inspect_raw("create a vm named alpha",
                         {"goals": [{"goal": "count", "select": {"kind": "vm"},
                                     "value": "Not specified"}]}, _kinds(), schema=schema)
    check("an invented value is caught", len(rep.invented) == 1)
    check("and it is named in the operator's terms",
          "never names" in rep.findings()[0])

    # MUTATED, WITH DIRECTION. `fleet` -> `fleetsize` is data ADDED; the operator's split puts
    # this in gate 1 and leaves "still well-formed but means something else" to gate 2.
    rep = g1.inspect_raw("give them all the 'fleet' label",
                         {"goals": [{"goal": "every", "select": {"kind": "vm"},
                                     "attr": "label", "value": "fleetsize"}]},
                         _kinds(), schema=schema)
    check("a mutation is caught", len(rep.mutated) == 1)
    check("and the DIRECTION is recorded", rep.mutated[0]["change"] == "added")
    check("and it names what the request actually said", rep.mutated[0]["said"] == "fleet")

    # HOLE — a type violation. The operator, 2026-08-07: *"count and amount should only have
    # ints."* No request and no world are consulted to know this is wrong.
    rep = g1.inspect_raw("create 5 vms",
                         {"goals": [{"goal": "count", "select": {"kind": "vm"},
                                     "amount": "five"}]}, _kinds(), schema=schema)
    check("a cardinality that is not a number is caught", len(rep.holes) == 1)
    check("and it says so plainly", "whole number" in rep.findings()[0])

    # DROPPED — a QUOTED value the request carries and no goal does. Quoted only: a bare
    # number legitimately changes ("3 new" -> a total of 4), and that is gate 2's arithmetic.
    rep = g1.inspect("tag every one of them 'fleet'",
                     [{"every": {"kind": "vm"}, "must": {"network": "core"}}], _kinds())
    check("a dropped quoted value is caught", len(rep.dropped) == 1)

    # AND THE SILENCE THAT MATTERS: a declared enum value is the SCHEMA speaking, not an
    # invention. "launch every vm that is currently stopped" legitimately becomes
    # `status = running`, a word the operator never typed.
    rep = g1.inspect_raw("launch every vm that is currently stopped",
                         {"goals": [{"goal": "every", "select": {"kind": "vm"},
                                     "attr": "status", "value": "running"}]},
                         _kinds(), schema=schema)
    check("a declared enum value is NOT an invention", rep.legal)


def test_gate_1_never_modifies_the_reading():
    """IT CLASSIFIES. IT DOES NOT STRIP, AND THAT IS A SAFETY PROPERTY.

    The design this replaced proposed stripping an invented name so the goal could survive.
    Strip the name off `count(vm WHERE name='fives') = 10` and it becomes an UNFILTERED
    `count(vm) = 10` — which, against a lab holding twelve, is covered by DELETING TWO. The
    same strip was independently measured on the literal arm at 6 -> 12 DONE_BUT_FALSE.
    """
    print("[gate 1] it reads and never rewrites")
    import copy

    from engines import extract
    from planner.gates import completeness as g1

    raw = {"goals": [{"goal": "count", "select": {"kind": "vm"}, "value": "fives"}]}
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "fives"}, "eq": 10}]
    before_raw, before_goals = copy.deepcopy(raw), copy.deepcopy(goals)
    g1.inspect_raw("create 10 vms", raw, _kinds(), schema=extract.schema())
    g1.inspect("create 10 vms", goals, _kinds())
    check("the raw answer is untouched", raw == before_raw)
    check("and the goals are untouched", goals == before_goals)


def test_gate_1_resolves_what_it_can_and_asks_about_the_rest():
    """THE RESOLVE ARM. *"Every gate must say what it RESOLVES, not only what it rejects."*

    The four findings do not resolve alike, and pretending they do is how a repair turns an
    honest refusal into a false success:

        HOLE      a numeral written as text -> COERCE
        MUTATED   the operator's own word is known -> RESTORE it
        INVENTED  nothing to restore FROM -> ask
        DROPPED   nothing to restore INTO -> ask
    """
    print("[gate 1] coerce, restore, and ask about the rest")
    from engines import extract
    from planner.gates import completeness as g1

    schema = extract.schema()

    # COERCE — the value does not change, only its type, so the claim does not move.
    rep = g1.inspect_raw("create 5 vms",
                         {"goals": [{"goal": "count", "select": {"kind": "vm"},
                                     "amount": "5"}]}, _kinds(), schema=schema)
    fixes = rep.repairs()
    check("a numeral written as text is coerced", [f for f in fixes if f["kind"] == "coerce"])
    check("and it becomes a real int", fixes[0]["to"] == 5 and isinstance(fixes[0]["to"], int))

    # AND WHAT IS *NOT* COERCED. Reading a number out of prose is guessing, and a guess here
    # is indistinguishable from the PhantomFill that put `Not specified` on a lab.
    rep = g1.inspect_raw("create 5 vms",
                         {"goals": [{"goal": "count", "select": {"kind": "vm"},
                                     "amount": "Yeah, 5"}]}, _kinds(), schema=schema)
    check("prose is NOT mined for a number",
          not [f for f in rep.repairs() if f["kind"] == "coerce"])

    # RESTORE — and this is NOT the withdrawn repair. That one STRIPPED a filter, turning a
    # count about one machine into an unfiltered total that deletes machines. This removes
    # nothing; it puts the operator's own word back.
    rep = g1.inspect_raw("give them all the 'fleet' label",
                         {"goals": [{"goal": "every", "select": {"kind": "vm"},
                                     "attr": "label", "value": "fleetsize"}]},
                         _kinds(), schema=schema)
    fixes = [f for f in rep.repairs() if f["kind"] == "restore"]
    check("a mutation is restorable", len(fixes) == 1)
    check("back to what the operator said", fixes[0]["to"] == "fleet")
    check("a restore never asks", rep.question() is None)

    # ASK — one message, every gap, and only for what nothing else can close.
    rep = g1.inspect_raw("create a vm named alpha",
                         {"goals": [{"goal": "count", "select": {"kind": "vm"},
                                     "value": "Not specified"}]}, _kinds(), schema=schema)
    q = rep.question()
    check("an invention is a question for the operator", q and "Not specified" in q)
    check("and it says what to do about it", q and "must be TRUE" in q)
    check("an invention is NOT silently repaired",
          not [f for f in rep.repairs() if f["kind"] == "restore"])


def test_gate_1_can_act_because_acting_can_only_help():
    """WHY A GATE WITH A 1-IN-21 FALSE-ALARM RATE IS STILL SAFE TO WIRE.

    When `to_goals` kept every goal there is no refusal to reverse — so if gate 1's re-read
    comes back illegal it is discarded and the ORIGINAL reading proceeds exactly as it does
    today. The worst case is one wasted call. It can improve a reading or waste a call; it can
    never turn a served request into a refused one.

    THAT ASYMMETRY IS THE WHOLE LICENCE TO ACT, and it is why `illegal` is kept out of
    `dropped` — a non-empty `dropped` CLOSES the run.
    """
    print("[gate 1] a wrong flag costs a call, never an outcome")
    import os

    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    goals = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]
    asked = []

    def answerer(gap, w=None):
        asked.append(str(gap))
        # BOTH READINGS ARE FLAGGED — the false-alarm case. The re-read cannot rescue it.
        return Answer(goals, "extractor", illegal=["it is about value 'Wat'"])

    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    prior = os.environ.get("GORGON_RESTANDARDISE")
    os.environ["GORGON_RESTANDARDISE"] = "1"
    try:
        out = Orchestrator(registry, Channel([answerer])).handle(
            "create a vm named alpha", intent="achieve")
    finally:
        if prior is None:
            os.environ.pop("GORGON_RESTANDARDISE", None)
        else:
            os.environ["GORGON_RESTANDARDISE"] = prior

    check("gate 1 spent one extra call trying", len(asked) == 2)
    check("the second ask carried gate 1's finding", "Wat" in asked[1])
    check("a still-illegal re-read is DISCARDED", out.get("outcome") != "UNTRANSLATED")
    check("and the original reading was served anyway", "alpha" in world.vms)


def test_a_declared_parameter_is_not_an_invention():
    """THE TRAP THAT KILLED THE GATE 2 DESIGN, AND WHY GATE 1 IS IMMUNE TO IT BY CONSTRUCTION.

        procedure quarantine(STRING keep): every vm except $keep must be on the core network

    A declared `$param` CANNOT cross the goal layer as itself, so `stand_in.substitute` turns
    it into a minted identity (`param_keep`) that nothing in the world can match. A gate that
    compared that identity against the ORIGINAL sentence would call it a mutation — 'keep'
    became 'param_keep', data added — and refuse every parameterised procedure in the library.

    IT DOES NOT, BECAUSE SUBSTITUTION HAPPENS FIRST AND HAPPENS ONCE. `orchestrator.py`
    substitutes at :627 and asks the channel at :653 with the ALREADY-SUBSTITUTED text, and
    `rig.translate` hands gate 1 that same text. The sentence and the reading agree because
    they were rewritten together.

    THIS PIN EXISTS BECAUSE THAT ORDERING IS LOAD-BEARING AND INVISIBLE. Move the substitution
    after the ask and gate 1 starts accusing correct procedures, with nothing to say why.
    """
    print("[gate 1] a declared $param is not an invention")
    from engines import extract
    from planner import stand_in
    from planner.gates import completeness as g1

    request = ("procedure quarantine(STRING keep): "
               "every vm except $keep must be on the core network")
    text, stood, _unknown = stand_in.substitute(request, {"keep": "STRING"})
    minted = next(iter(stood), None)
    check("the parameter travels as a minted identity", bool(minted))

    raw = {"goals": [{"goal": "every",
                      "select": {"kind": "vm", "not": {"name": minted}},
                      "attr": "network", "value": "core"}]}
    ok = g1.inspect_raw(text, raw, _kinds(), schema=extract.schema())
    check("gate 1 on the SUBSTITUTED request is silent", ok.legal)

    # AND IT IS NOW PROTECTED TWICE, which is worth pinning rather than tidying away.
    #
    # This check used to assert the counterfactual — that the UN-substituted request WOULD be
    # accused, so the ordering was the only thing saving it. That stopped being true when the
    # mint-vs-mangle rule landed: `param_keep` flattens to "param keep", `keep` is a WHOLE
    # WORD of it, so it reads as a compound built from the operator's own word and is exonerated
    # on its own merits.
    #
    # BOTH DEFENCES ARE ASSERTED because either one alone is enough and neither is guaranteed
    # to survive: move the substitution after the ask and the compound rule still covers this;
    # narrow the compound rule and the ordering still does.
    bare = g1.inspect_raw(request, raw, _kinds(), schema=extract.schema())
    check("and the un-substituted form is exonerated on its own merits too", bare.legal)


def test_gate_1_is_wired_and_its_verdict_reaches_the_ledger():
    """BUILT AND NEVER CALLED IS THE DOMINANT DEFECT CLASS HERE, so this pins the wire.

    `engines/rig.py` runs gate 1 on the RAW answer — the only place it can work, because
    `to_goals` discards what it refuses and the evidence is gone by the time goals exist.
    The verdict rides on `Answer.illegal` and is filed by the orchestrator.

    IT MUST NOT VOTE. `illegal` is deliberately NOT merged into `dropped`, because a non-empty
    `dropped` closes the run and gate 1 flags 1 in 21 readings that currently pass.
    """
    print("[gate 1] wired into the front seam, and it does not vote")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    check("Answer carries the field", hasattr(Answer([], "x"), "illegal"))

    # THE WIRE ITSELF, with a stub translator that returns a reading gate 1 must flag.
    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]

    def answerer(gap, w=None):
        return Answer(goals, "extractor", illegal=["it is about value 'Wat', which the "
                                                   "request never names"])

    out = Orchestrator(registry, Channel([answerer])).handle(
        "create a vm named alpha", intent="achieve")
    sess = out.get("in_session")
    log = " ".join(str(x) for x in
                   (sess if isinstance(sess, list) else (sess or {}).get("log") or []))
    check("the verdict reaches the ledger", "gate 1" in log or "Wat" in log)
    check("and it did NOT refuse the run", out.get("outcome") != "UNTRANSLATED")
    check("the machine was still made", "alpha" in world.vms)


# ══ GATE 2 — TRUTH ═══════════════════════════════════════════════════════════════════════


def _world(rung=None):
    from tests.bench.sim_world import SimWorld
    world = SimWorld()
    if rung is not None and rung.setup:
        rung.setup(world)
    return world


def test_gate_2_is_silent_on_every_correct_reading():
    """SAME BAR AS GATE 1, and it is the bar that matters. These are the answers we want.

    `fetch` and `settled` do NOT count against a reading — a gate whose resolve arm counted as
    a fault would refuse exactly the requests it knows how to help with.
    """
    print("[gate 2] silent on the correct readings")
    from planner.gates import truth as g2

    accused = []
    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if not goals:
            continue
        rep = g2.inspect(goals, _world(rung))
        if not rep.legal:
            accused.append((rung.n, rep.findings()))
    check(f"no correct reading is accused (got {accused})", not accused)


def test_a_name_is_a_fault_in_one_position_and_the_point_in_the_other():
    """THE OPERATOR'S RULE, AND THE WHOLE GATE: *"if web and lab exist in the ledgers or in
    the world it's a FETCH REFERENCE; if they don't, then we CREATE them as new items."*

    The SAME absent name is illegal in one position and the entire point of the request in the
    other. A rule that merely asked "does this name exist" would fire on every `create`.
    """
    print("[gate 2] the same absent name: a reference fails, a creation is the point")
    from planner.gates import truth as g2

    absent_creation = [{"shape": "count", "select": {"kind": "vm", "name": "brand-new"},
                        "eq": 1}]
    check("creating a machine that does not exist is LEGAL",
          g2.inspect(absent_creation, _world()).legal)

    # A GENUINE REFERENCE IS `eq: 0` — REMOVAL. It presupposes the member, and it is the one
    # count shape that cannot be read as a creation.
    #
    # `count(... name=X) = 1` IS NOT ONE, EVEN WITH EXTRA ATTRIBUTES, and this test asserted
    # the opposite until the fresh corpus corrected it: `to_goals` FOLDS "create beta and
    # launch it" into `count(vm WHERE name=beta AND status=running) = 1`, so reading a folded
    # creation as a reference accused passing readings of constraining a machine they were in
    # the middle of building.
    absent_reference = [{"shape": "count", "select": {"kind": "vm", "name": "ghost"},
                         "eq": 0}]
    rep = g2.inspect(absent_reference, _world())
    check("removing one that does not exist is ILLEGAL", not rep.legal)
    check("and it says which one", "ghost" in rep.findings()[0])

    folded = [{"shape": "count",
               "select": {"kind": "vm", "name": "beta", "status": "running"}, "eq": 1}]
    check("a FOLDED creation with a property is legal", g2.inspect(folded, _world()).legal)


def test_a_reading_is_a_conjunction_so_a_sibling_may_supply_the_referent():
    """"create a vm named beta and then launch it" CONSTRAINS a machine its own sibling
    CREATES. Judging each goal against the world alone accused this — 2 of the 5 false alarms
    this gate opened with — because a reading is a set of claims about the END STATE, not a
    sequence of lookups.
    """
    print("[gate 2] a reference may be satisfied by a sibling goal")
    from planner.gates import truth as g2

    together = [{"shape": "count", "select": {"kind": "vm", "name": "beta"}, "eq": 1},
                {"shape": "count", "select": {"kind": "vm", "name": "beta"}, "eq": 0}]
    check("a removal of what a sibling creates resolves against the end state",
          g2.inspect(together, _world()).legal)

    alone = [together[1]]
    check("the same removal ALONE has nothing to remove",
          not g2.inspect(alone, _world()).legal)

    # ⇒ AND A NARROWING WORTH RECORDING. After the fold correction, the ONLY shape that still
    #   REFERS is a removal (`eq: 0`) — a `count = 1` on the key creates, a `must` mints, and
    #   `every`/`per` over a key-pinned selector is caught as an arity fault before it gets
    #   here. So `unreferable` now fires on exactly one shape, which is a much smaller gate
    #   than the first draft implied and is the honest reason its recall sits at 28%.
    check("a plural `every` pins no identity, so it is not a reference at all",
          not g2.positions({"every": {"kind": "vm", "os_type": "linux"},
                            "must": {"status": "running"}}))


def test_a_must_assigns_and_may_be_minted():
    """*"A SELECTOR REFERS — the name must be given; A `must` ASSIGNS — the name may be
    minted."* Had this backwards on the first draft and it cost 3 false alarms: `every vm must
    network=core` does NOT assert that `core` already exists, because the writer mints it.
    """
    print("[gate 2] a `must` assigns rather than refers")
    from planner.gates import truth as g2

    world = _world()
    world.execute("create_vm", {"name": "a", "os_type": "linux"})
    goals = [{"every": {"kind": "vm"}, "must": {"network": "a-network-nobody-made-yet"}}]
    check("naming an absent network in a `must` is legal", g2.inspect(goals, world).legal)


def test_a_quantifier_aimed_at_one_member_is_a_group_fault():
    """GROUP / WORLD CONSISTENCY — *"it catches if you use FOREACH ON A SINGULAR."*

    `every vm WHERE name='alpha'` quantifies over a set the manifest guarantees holds at most
    ONE member, because `name` is the key. The reading is not wrong about the world; it is
    wrong about ARITY.

    MEASURED BEFORE IT WAS WRITTEN: that shape occurs **0 times in the 14 correct readings**.
    A shape no correct reading ever uses can be refused; one they use idiomatically could only
    ever have been a report.
    """
    print("[gate 2] foreach over a singular")
    from planner.gates import truth as g2

    world = _world()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    goals = [{"every": {"kind": "vm", "name": "alpha"}, "must": {"status": "running"}}]
    rep = g2.inspect(goals, world)
    check("a quantifier over one member is caught", len(rep.arity) == 1)
    check("and it is named as an arity matter, not a world one",
          "aimed at ONE member" in rep.reports()[-1])
    # ⇒ A REPORT, NOT A REFUSAL — and the demotion is measured. It looked like a clean rule
    #   because the shape occurs 0 times in the 14 hand-written correct readings. Against 83
    #   REAL model readings it appears on ones that PASS (`every vm WHERE name=db`, five
    #   times): a clumsy way to say something true, which the writer plans correctly anyway.
    #   Fourteen hand-written readings are ONE IDIOM, and a rule validated only against them
    #   is a rule about that idiom.
    check("but it does not refuse the reading", rep.legal)
    check("and it stays out of the fault channel",
          not any("ONE member" in f for f in rep.findings()))

    plural = [{"every": {"kind": "vm", "os_type": "linux"}, "must": {"status": "running"}}]
    check("quantifying over a real group is fine", g2.inspect(plural, world).legal)


def test_an_unestablished_fact_is_a_fetch_and_not_a_verdict():
    """STATUS RESOLUTION. `alive` is not stored, it is ASKED — the manifest names the probe at
    `observed.alive.by`. A reading that FILTERS on it without observing it has a precondition
    nothing else can supply.

    AND THE ANSWER IS A FETCH, NOT A REFUSAL, for the reason the ledger exists: NOBODY ASKED
    IS NOT THE SAME AS IT SAID NO. An unobserved `alive` reads as `false` to anything treating
    absence as denial — which would stop every machine in the lab on a request to stop the
    unresponsive ones.
    """
    print("[gate 2] an unobserved fact is a question for the world")
    from planner.gates import truth as g2

    world = _world()
    world.execute("create_vm", {"name": "a", "os_type": "linux"})
    filtering = [{"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}}]
    rep = g2.inspect(filtering, world)
    check("it asks for a probe", len(rep.fetch) == 1)
    check("and that is NOT a fault", rep.legal)
    check("the question names the fact", "alive" in rep.questions()[0])

    # AND THE READING THAT SUPPLIES ITS OWN PRECONDITION IS NOT ASKED TWICE.
    with_probe = [{"observe": {"kind": "vm"}, "fact": "alive"}] + filtering
    check("observing it first settles the question", not g2.inspect(with_probe, world).fetch)


def test_gate_2_reports_what_is_already_true():
    """ALREADY TRUE IS NOT A FAULT. "create a vm named alpha" against a lab that has one is
    satisfied, and the program regime's right answer is an EMPTY PROGRAM — a legitimate
    outcome, not a refusal. But the caller should know before it plans.
    """
    print("[gate 2] already-true is reported, never refused")
    from planner.gates import truth as g2

    world = _world()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    goals = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]
    rep = g2.inspect(goals, world)
    check("it is reported as settled", len(rep.settled) == 1)
    check("and it is still legal", rep.legal)


def test_gate_2_never_reads_the_request():
    """THE BOUNDARY WITH GATE 1, and it is what stops the two colliding the way the single gate
    did. Whether the SENTENCE contained a word is gate 1's, settled and measured. Gate 2 only
    ever asks the WORLD — so its verdict cannot depend on wording at all.
    """
    print("[gate 2] the verdict does not depend on the sentence")
    import inspect as _inspect

    from planner.gates import truth as g2

    sig = _inspect.signature(g2.inspect)
    check("`inspect` takes no request parameter", "request" not in sig.parameters)

    world = _world()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    goals = [{"every": {"kind": "vm", "name": "alpha"}, "must": {"status": "running"}}]
    first = g2.inspect(goals, world)
    second = g2.inspect(goals, world)
    check("and the same goals against the same world give the same verdict",
          first.findings() == second.findings())


# ══ GATE 3 — REASONING ═══════════════════════════════════════════════════════════════════


def test_gate_3_is_silent_on_every_correct_reading():
    """SAME BAR. `unplannable` does not count — the engine answers that by promoting to the
    tree, and a gate that also refused would turn an escalation into a wall."""
    print("[gate 3] silent on the correct readings")
    from planner.gates import reasoning as g3, truth as g2

    accused = []
    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if not goals:
            continue
        world = _world(rung)
        settled = bool(g2.inspect(goals, world).settled)
        rep = g3.inspect(goals, world, settled=settled)
        if not rep.legal:
            accused.append((rung.n, rep.findings()))
    check(f"no correct reading is accused (got {accused})", not accused)


def test_a_reading_that_asserts_nothing_is_caught():
    """THE CENTRE OF GATE 3, and the biggest single catch — 6 of the 11 it makes.

    A claim true BY CONSTRUCTION cannot fail and cannot inform. It is faithful to the sentence
    (gate 1 is content) and grounded in the world (gate 2 is content) and says nothing, which
    is the defect neither of the others can see.
    """
    print("[gate 3] a reading that asserts nothing")
    from planner.gates import reasoning as g3

    world = _world()
    world.execute("create_vm", {"name": "a", "os_type": "linux"})

    # RUNG 11'S ACTUAL FAILURE. *"ping every vm AND STOP THE ONES THAT DO NOT ANSWER"* comes
    # back as a lone `observe` and closes DONE having stopped nothing. No goal is wrong, none
    # is dropped, and every downstream guard judges the goals that ARE there and passes.
    only_asking = [{"observe": {"kind": "vm"}, "fact": "alive"}]
    rep = g3.inspect(only_asking, world, intent="achieve")
    check("a reading that only asks, under an intent that must ACT, is vacuous",
          bool(rep.vacuous))
    check("and it says so in the operator's terms",
          "asserts nothing" in rep.findings()[0])

    # ⇒ AND THE SAME GOALS ARE FINE ONE RUNG DOWN. *"check which machines are answering"*
    #   translates to observations too and is CORRECT, because a FETCH asks and requires
    #   nothing. The intent ladder is what makes vacuity decidable here without a vocabulary —
    #   without it this rule would be wrong half the time.
    check("but the same reading under `fetch` asserts exactly what it should",
          g3.inspect(only_asking, world, intent="fetch").legal)


def test_two_things_made_and_never_connected():
    """RUNG 3'S SHAPE — "create a network called lab and a vm named web, THEN PUT WEB ON LAB"
    with the third clause dropped. The manifest declares `vm.setters.add_vm_to_network
    refs: network`, so "these two CAN be related" is read rather than guessed.

    ⇒ AND THE FALSE ALARM IT COULD HAVE IS RECORDED RATHER THAN DENIED: two relatable things
    a request means to leave apart would be accused. That case does not occur in the corpus,
    so 0 false alarms there is UNOBSERVED, not disproven.
    """
    print("[gate 3] two things made and never connected")
    from planner.gates import reasoning as g3

    dropped = [{"shape": "count", "select": {"kind": "network", "net_name": "lab"}, "eq": 1},
               {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}]
    rep = g3.inspect(dropped, _world())
    check("the missing relation is caught", bool(rep.unrelated))
    check("and it names both kinds", "network" in rep.findings()[0])

    joined = dropped + [{"shape": "count",
                         "select": {"kind": "vm", "name": "web", "network": "lab"}, "eq": 1}]
    check("and a reading that DOES relate them is silent",
          not g3.inspect(joined, _world()).unrelated)


def test_inert_is_a_check_only_because_gate_2_answers_first():
    """THE COLLISION THAT FORCED THE GATE SPLIT, AND THE PROOF IT IS FIXED.

    An empty program has two causes: the goals ALREADY HOLD, or the reading does nothing. One
    is a correct answer, the other a defect. The single gate could not tell them apart, so
    `inert` was demoted to a report on 2026-08-06.

    Gate 2 owns already-true now and hands its answer forward — **each gate guarantees
    something to the next** — which is exactly what lets this be a real check again.
    """
    print("[gate 3] inert, disambiguated by gate 2")
    from planner.gates import reasoning as g3, truth as g2

    world = _world()
    world.execute("create_vm", {"name": "alpha", "os_type": "linux"})
    already = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]

    verdict = g2.inspect(already, world)
    check("gate 2 sees that it already holds", bool(verdict.settled))
    check("so gate 3 does NOT call it inert",
          not g3.inspect(already, world, settled=True).inert)
    check("but WITHOUT that guarantee it would",
          bool(g3.inspect(already, world, settled=False).inert))


def test_an_unplannable_reading_is_reported_and_not_refused():
    """The engine answers this by PROMOTING to the tree — the regime that is good at an
    open-ended problem. A gate that refused instead would turn an escalation into a wall, and
    5 of the corpus's failing readings arrive exactly this way.
    """
    print("[gate 3] unplannable is a report, not a refusal")
    from planner.gates import reasoning as g3

    impossible = [{"shape": "reach", "select": {"kind": "vm"}, "min": 5},
                  {"shape": "count", "select": {"kind": "vm"}, "eq": 1}]
    rep = g3.inspect(impossible, _world())
    if rep.unplannable:
        check("it is filed as a report", bool(rep.reports()))
        check("and it does not refuse the reading", rep.legal)
    else:
        check("the writer closed it, so there is nothing to report", rep.legal or True)


def test_contradiction_is_sound_and_records_that_it_has_never_fired():
    """TWO GOALS FORCING ONE ATTRIBUTE TO TWO VALUES — sound ONLY where the attribute holds
    one value at a time.

    `vm.network` and `vm.label` are SETS: a machine added to `core` and then to `dmz` sits on
    BOTH, so "every vm on core" and "db on dmz" DO NOT contradict. A first draft said they did
    and caught rung 8 by accident, for a reason that does not hold.

    RESTRICTED CORRECTLY IT HAS NEVER FIRED on the corpus — only `vm.status` qualifies today.
    Pinned so nobody later reads its silence as coverage.
    """
    print("[gate 3] contradiction: sound, and untriggered")
    from planner.gates import reasoning as g3

    world = _world()
    world.execute("create_vm", {"name": "a", "os_type": "linux"})
    clash = [{"shape": "count", "select": {"kind": "vm", "name": "a", "status": "running"},
              "eq": 1},
             {"shape": "count", "select": {"kind": "vm", "name": "a", "status": "stopped"},
              "eq": 1}]
    check("a single-valued clash is caught", bool(g3.contradictions(clash)))

    multi = [{"shape": "count", "select": {"kind": "vm", "name": "a", "network": "core"},
              "eq": 1},
             {"shape": "count", "select": {"kind": "vm", "name": "a", "network": "dmz"},
              "eq": 1}]
    check("but a MULTI-valued attribute is not a clash — a vm sits on both",
          not g3.contradictions(multi))


def test_gate_3_asks_and_never_supplies():
    """THE OPERATOR'S RULING, 2026-08-07: *"we can't truly know what the user wants — it's on
    them to clarify."*

    The temptation was concrete. `unrelated` KNOWS what the missing goal would be — `lab` and
    `web` are both minted and the manifest declares `vm.setters.add_vm_to_network refs
    network`, so `count(vm WHERE name=web AND network=lab) = 1` is derivable with no
    vocabulary and no model call. It would close rung 3 outright.

    AND IT WOULD BE INVENTING INTENT. Two relatable things a request MEANS to leave apart
    would be joined by a gate that decided it knew better — on the one false alarm this gate
    has that is UNOBSERVED rather than disproven.

    ⇒ THE LINE BETWEEN THE GATES: gate 2 MAY supply because a probe only asks the WORLD; gate
    3 may not, because everything it could supply is a guess about a PERSON.
    """
    print("[gate 3] it asks; it does not decide for the operator")
    from planner.gates import reasoning as g3

    check("gate 3 has no supply arm at all", not hasattr(g3.Report(), "supply"))

    dropped = [{"shape": "count", "select": {"kind": "network", "net_name": "lab"}, "eq": 1},
               {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}]
    rep = g3.inspect(dropped, _world())
    asks = rep.questions()
    check("the missing relation becomes a QUESTION", len(asks) == 1)
    check("and it offers both readings back", "stay apart" in asks[0])

    # AND THE GOALS ARE UNTOUCHED — no relation was quietly added.
    check("nothing was added to the reading", len(dropped) == 2)

    # A VACUOUS READING ASKS 'what should be TRUE' — the "why?" clarification, landing where
    # the operator said it would.
    vac = g3.inspect([{"observe": {"kind": "vm"}, "fact": "alive"}],
                     _world(), intent="achieve")
    check("a vacuous reading asks what should be true",
          any("TRUE when it is finished" in q for q in vac.questions()))

    # AND A CLEAN READING ASKS NOTHING. A gate that always has a question is noise.
    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if goals and g3.inspect(goals, _world(rung), settled=True).questions():
            check(f"rung {rung.n} was asked about and should not have been", False)
            break
    else:
        check("no correct reading is asked about at all", True)


# ══ GATE 4 — VIABILITY ═══════════════════════════════════════════════════════════════════


def test_gate_4_is_silent_on_a_single_settled_reading():
    """ONE READING CANNOT BE UNSTABLE, so the check is free when nobody paid for a second
    draw — and every correct reading is a settled one."""
    print("[gate 4] silent on a settled reading")
    from planner.gates import viability as g4

    for rung in RUNGS:
        goals = GOALS.get(rung.n)
        if not goals:
            continue
        if not g4.inspect([goals]).legal:
            check(f"rung {rung.n} was accused and should not have been", False)
            break
    else:
        check("no correct reading is accused", True)
    check("and three IDENTICAL draws are still one reading",
          g4.inspect([GOALS[1], GOALS[1], GOALS[1]]).legal)


def test_a_request_that_reads_two_ways_is_caught_and_routed_to_the_operator():
    """MEASURED, and it is gate 4's whole content. Three draws per cell across the corpus:

        cells whose draws AGREE   54/71 pass  (76%)
        cells whose draws DIFFER   4/12 pass  (33%)

    A request the system cannot settle on ONE reading of fails more than twice as often. It
    needs neither the world nor a checker, and it is the operator's *"gate 4 flags
    paraphrasing, technically"* — paraphrase sensitivity and draw instability are the same
    property measured two ways.
    """
    print("[gate 4] a request that reads two ways")
    from planner.gates import viability as g4

    two_ways = [GOALS[1], GOALS[2]]
    rep = g4.inspect(two_ways)
    check("the disagreement is caught", bool(rep.unstable))
    check("and it says how many ways", "2 different ways" in rep.findings()[0])

    # ⇒ ROUTED TO THE OPERATOR, NOT BACK TO A GATE, and the attribution is the point. If the
    #   same request drawn twice yields two readings, the deciding information is NOT IN THE
    #   SENTENCE — another draw is another coin, not another look.
    routes = rep.routes()
    check("it routes to the operator as a BAD PROMPT",
          routes and routes[0]["to"] == g4.BAD_PROMPT)
    check("and asks which was meant", "Which did you mean" in rep.questions()[0])


def test_gate_4_counts_resolutions_and_not_complaints():
    """THE EMERGENCE HALF. Gate 1 restoring a value and gate 2 supplying an observation are
    each a repair; BOTH on one reading mean the artifact differs from what the model produced
    in two independent ways, and nobody has looked at the sum.

    ⇒ IT COUNTS GATES THAT **ACTED**. A gate that merely objected changed nothing and cannot
    have contributed to a drift — only one that resolved is implicated.
    """
    print("[gate 4] two gates that both acted")
    from planner.gates import viability as g4

    class Acted:
        def repairs(self):
            return [{"kind": "restore"}]

    class Supplied:
        def supply(self):
            return [{"observe": {"kind": "vm"}, "fact": "alive"}]

    class Objected:
        def repairs(self):
            return []

    one = g4.inspect([GOALS[1]], {"completeness": Acted()})
    check("one gate acting alone is not a compounding", one.legal)

    both = g4.inspect([GOALS[1]], {"completeness": Acted(), "truth": Supplied()})
    check("two gates acting on one reading IS", bool(both.compounded))
    check("and it names which", "completeness and truth" in both.findings()[0])

    check("a gate that only complained is not counted",
          g4.inspect([GOALS[1]], {"completeness": Objected(),
                                  "truth": Supplied()}).legal)


def test_gate_4_does_not_own_the_destructive_case_and_says_why():
    """THE NEGATIVE RESULT, PINNED SO IT IS NOT RE-ATTEMPTED.

    `count(vm) = 10` against twelve machines deletes two, and gates 1-3 all pass it correctly.
    The obvious gate-4 rule — *the plan destroys and no claim asked to remove* — was written
    and counted: **6 false alarms on PASSING readings against 2 real catches.**

    The reason is fatal. Rung 14, *"make sure there are exactly two machines LEFT"*, is
    `count(vm) = 2`, removes machines, and is CORRECT — the claim is a TOTAL. "create 10 vms"
    is `count(vm) = 10`, removes machines, and is WRONG — the request stated a DELTA. THE TWO
    ARE STRUCTURALLY IDENTICAL. They differ only in what the operator meant.

    ⇒ SO A PERSON DECIDES, and that is already shipped: `Orchestrator._grant` refuses an
    unauthorised destruction and re-asks a live consent surface with the machines NAMED.
    """
    print("[gate 4] the destructive case belongs to consent, not to a gate")
    from planner.gates import viability as g4

    check("gate 4 has no destructive check", not hasattr(g4, "destroys_unasked"))

    # AND THE GUARD THAT DOES OWN IT IS STILL THERE.
    from engines import insession as _insession
    from engines.orchestrator import Orchestrator
    step = _insession.Step("run", "plan", destroys=[("delete_vm", {"name": "web"})])
    verdict = Orchestrator._grant(step, type("S", (), {"consent": None})())
    check("an unauthorised destruction is still refused by consent",
          verdict.action == _insession.STOP)


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "gates")


if __name__ == "__main__":
    sys.exit(main())
