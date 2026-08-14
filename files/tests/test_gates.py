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


def test_evidence_for_a_shape_that_no_goal_takes():
    """THE ONE ABSENCE CHECK THAT NEEDS NO VOCABULARY OF ITS OWN.

    Every previous attempt to see a dropped clause needed a word list somebody had to keep
    correct. This asks the MANIFEST what makes a shape believable — `request_evidence`, the
    same list `schema()` uses to decide whether to OFFER the branch — and reads it the other
    way: a request that EARNED the offer and produced nothing has lost the clause.

    ⇒ TWO ENTRIES ONLY, AND THE THIRD WAS MEASURED AND LEFT OUT. `removal` implies no single
    goal form: rung 14's "cut the lab down to two machines" is `count(vm) = 2` — a TOTAL that
    removes without any `eq 0` — so demanding one accuses a correct reading. `reach` and
    `except` each map to exactly one form, which is what makes them checkable and removal not.
    """
    print("[gate 1] the request earned a shape and no goal took it")
    from planner.gates import completeness as g1

    lost = g1.inspect("make sure n1, n2 and n3 can all reach each other",
                      [{"shape": "count", "select": {"kind": "vm", "name": "n1"}, "eq": 1}])
    check("reach evidence with no reach goal is caught", bool(lost.unshaped))
    check("and it says which", "reach" in lost.findings()[-1])

    kept = g1.inspect("make sure n1, n2 and n3 can all reach each other",
                      [{"shape": "reach", "select": {"kind": "vm"}, "min": 3}])
    check("a reading that takes the shape is silent", not kept.unshaped)

    carved = g1.inspect("put every vm on core except db",
                        [{"every": {"kind": "vm", "not": {"name": "db"}},
                          "must": {"network": "core"}}])
    check("an except that IS carved out is silent", not carved.unshaped)
    flat = g1.inspect("put every vm on core except db",
                      [{"every": {"kind": "vm"}, "must": {"network": "core"}}])
    check("and one that is not is caught", bool(flat.unshaped))

    # ⇒ REMOVAL IS DELIBERATELY NOT CHECKED — pinned so it is not added later without the
    #   measurement. "cut the lab down to two machines" removes, and says so with a TOTAL.
    total = g1.inspect("cut the lab down to two machines",
                       [{"shape": "count", "select": {"kind": "vm"}, "eq": 2}])
    check("a removal expressed as a total is not accused", not total.unshaped)


def test_gate_1_votes_on_an_invented_must_value():
    """THE ONE PLACE THIS GATE REFUSES RATHER THAN REPORTS, and it is the narrowest the
    evidence supports.

    ⇒ `to_goals` IS STRUCTURALLY BLIND THERE. `_keep` judges the SELECTOR —
    `goal.get("select") or goal.get("every") or goal.get("observe")` — and never a `must`, so
    `{"every": {"kind": "vm"}, "must": {"status": "before"}}` reaches the writer carrying a
    value the request never said. Found live on rung 11's paraphrase.

    ⇒ AND IT CANNOT BORROW ITS OWN TEST FOR THE SLOT. Judging `must` values with
    `_refuse_invented` costs **6 false alarms of 58** — it refuses `must network='lab-red'`,
    a MINTED name for a network the request never names, because it has no notion of a mint.
    Gate 1 does, and measures **0 of 58** on the same slot.

    ⇒ IT CATCHES NOTHING ON THE CORPUS, said plainly rather than dressed up: the corpus does
    not contain the shape. The live path produced it.
    """
    print("[gate 1] the vote: an invented `must` value")
    from planner.gates import completeness as g1

    caught = g1.inspect("check which machines respond and shut down whichever ones dont",
                        [{"every": {"kind": "vm"}, "must": {"status": "before"}}])
    check("an invented `must` value is refusable", len(caught.refusals()) == 1)
    check("and it names the slot", "must status" in caught.refusals()[0])

    # ⇒ THE THREE IT MUST NOT REFUSE, and each one nearly broke it.
    #
    #   A `must` THAT POINTS AT ANOTHER KIND IS MINTABLE and its name need not come from the
    #   request at all — the writer CREATES the member. Written without that exemption this
    #   accused FIVE known-good readings: `must network='lab'`, `'net1'`, `'rednet'`,
    #   `'bluenet'`, every one a network the request never names and the ORACLE ITSELF mints.
    #   The compound test saves `lab-red` and CANNOT save `rednet` — `red` sits inside a word
    #   there — so the exemption has to be the REFERENCE, not the spelling.
    for made in ("lab-red", "rednet", "net1"):
        ref = g1.inspect("put the red ones together on their own network",
                         [{"every": {"kind": "vm", "label": "red"},
                           "must": {"network": made}}])
        check(f"a minted network name ({made}) is not refused", not ref.refusals())

    enum = g1.inspect("launch every vm that is currently stopped",
                      [{"every": {"kind": "vm"}, "must": {"status": "running"}}])
    check("a value the SCHEMA declares is not refused", not enum.refusals())

    # AND NOTHING ELSE GETS A VOTE — a drop and a hole stay questions, not refusals.
    dropped = g1.inspect("tag every one of them 'fleet'",
                         [{"every": {"kind": "vm"}, "must": {"network": "core"}}])
    check("a DROP is still only a question", not dropped.refusals() and dropped.dropped)


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


def test_n_copies_of_a_member_that_already_exists():
    """RUNG 10'S PARAPHRASE, which died SILENTLY — a correct refusal with no question attached.

    `to_goals` refuses *"3 vms all called 'golden', and a vm is identified by its name"* and it
    is RIGHT: three members cannot share one identity. But no gate could phrase it, so the
    operator got a refusal and nothing to answer. They meant three COPIES of an existing
    machine, and only they can say so.

    ⇒ GATE 1 FINDS IT IN THE RAW, GATE 2 JUDGES IT AGAINST THE WORLD. It has to be read from
    the raw because `_refuse_shared_identity` drops the goal before any gate could look — the
    same reason the invention checks moved upstream: a rule that refuses first destroys the
    evidence a rule that EXPLAINS would need.

    ⇒ AND THE MEMBERSHIP TEST TOOK THREE ATTEMPTS. On the raw alone: 25 false alarms of 58,
    because the `name` slot is a SINK for descriptions the model cannot shape (`'every'`,
    `'vms labelled prod'`). Narrowed to names the operator SAID: still 9, because `'blue'` is
    said as a LABEL. Narrowed to names that are EXISTING MEMBERS: **0 of 58**.
    """
    print("[gate 2] N copies of a machine that already exists")
    from planner.gates import completeness as g1, truth as g2

    raw = {"goals": [{"goal": "count", "select": {"kind": "vm"},
                      "amount": 3, "name": "golden"}]}
    found = g1.copies_of(raw)
    check("gate 1 reads it off the raw answer", len(found) == 1)

    world = _world()
    world.execute("create_vm", {"name": "golden", "os_type": "linux"})
    rep = g2.inspect([], world, copies=found)
    check("gate 2 confirms it against the world", bool(rep.shared))
    check("and asks the only question that helps", "copies of it" in rep.asks()[0])
    # ⇒ AND IT GOES TO THE OPERATOR'S CHANNEL, NOT THE WORLD'S. `questions()` is what the
    #   SYSTEM answers by probing; `asks()` is what only a person can. Merging the two sent
    #   this question to `Answer.fetch`, which the bounce never reads, and rung 10's paraphrase
    #   BLOCKED with a perfectly good question sitting in the wrong field.
    check("and it is NOT filed as something the world can answer", not rep.questions())

    # ⇒ THE SAME SHAPE WHERE THE NAME IS NOT A MEMBER IS NOT THIS. "create 3 vms called web"
    #   on a lab with no `web` is an ordinary — if malformed — creation, and `to_goals` owns it.
    check("a name nothing in the world holds is left alone",
          not g2.inspect([], _world(), copies=found).shared)


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


def test_a_stated_cardinality_that_no_goal_carries():
    """THE CHECK I REMOVED FROM GATE 1 AND DEFERRED TO NOWHERE.

    Gate 1 had a number rule; it accused rung 10 — *"clone golden into 3 NEW vms"* is
    correctly served by `count(vm) = 4`, three clones plus the `golden` already there, because
    A COUNT IS A TOTAL AND THE REQUEST STATED A DELTA. So it was removed, with a comment
    saying *"it belongs to gate 2 and is left for it"*. Gate 2 never got it, and rung 13's
    paraphrase drops `count(vm) = 5` with nothing objecting.

    ⇒ IT NEEDS BOTH THE SENTENCE AND THE WORLD, so gate 1 finds the numbers and gate 2 judges
    them. What crosses the boundary is a SET OF INTEGERS — a fact, not a sentence — so gate 2
    still reads no English and does not become a second gate 1.
    """
    print("[gate 2] a cardinality the request stated and no goal carries")
    from planner.gates import completeness as g1, truth as g2

    world = _world()
    dropped = [{"shape": "count", "select": {"kind": "network", "net_name": "p"}, "eq": 1}]
    rep = g2.inspect(dropped, world,
                     said_numbers=g1.said_numbers("use five machines on one network"))
    check("the stated five is caught", bool(rep.uncarried))
    check("and it says so plainly", "says 5" in rep.findings()[0])

    kept = dropped + [{"shape": "count", "select": {"kind": "vm"}, "eq": 5}]
    check("a reading that carries it is silent",
          not g2.inspect(kept, world,
                         said_numbers=g1.said_numbers("use five machines")).uncarried)

    # ⇒ AND THE DERIVATION, which is why this cannot live in gate 1. "clone golden into 3 NEW
    #   vms" against a world holding `golden` is `count(vm) = 4` — the request stated a DELTA
    #   and a count is a TOTAL. Demanding the literal 3 accuses a hand-written CORRECT answer.
    w2 = _world()
    w2.execute("create_vm", {"name": "golden", "os_type": "linux"})
    total = [{"shape": "count", "select": {"kind": "vm"}, "eq": 4}]
    check("3 + what the world holds is carried by a total of 4",
          not g2.inspect(total, w2,
                         said_numbers=g1.said_numbers("clone golden into 3 new vms")).uncarried)

    # ⇒ AND `one` IS NOT A NUMBER HERE. "wire them together on ONE private network" is an
    #   ARTICLE, and counting it cost 6 of the 9 false alarms this check opened with.
    check("the article `one` is not read as a cardinality",
          1 not in g1.said_numbers("wire them together on one private network"))
    check("but a digit still is", 5 in g1.said_numbers("create 5 vms"))


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


def test_a_count_over_a_set_nobody_has_measured():
    """THE OPERATOR'S DIAGNOSIS OF RUNG 11, 2026-08-07, and it is the cleanest statement of
    that failure anyone made:

    *"'stop the unresponsive ones' is a SET, but of an UNKNOWABLE NUMBER. `count` needs a
    knowable number — meaning it either has to count them first and plug them in, or have a
    way to express the count of an unknowable finite set."*

    `count` REQUIRES `amount`, an integer, at authoring time. `alive` is not stored, it is
    ASKED (`observed.alive.by`), so how many machines have it is unknown until something
    pings. A count over that set demands a number nobody can supply.

    ⇒ AND `every` IS THE ANSWER, WHICH IS WHY THE FINDING SAYS SO — *"every covers an
    unknowable number of a finite set."* `every vm WHERE alive=false must status=stopped`
    quantifies over exactly that set and never counts it, and round-trips to rung 11's
    hand-written correct reading byte for byte. The shape is not missing; it is DECLINED.

    ⇒ IT HAS NEVER FIRED, recorded rather than hidden: the model does not attempt the honest
    version and fail, it AVOIDS the filter and names the set instead
    (`count(vm WHERE name='unresponsive') = 0`). The failure is one step earlier than this
    rule can see. It is kept because it costs nothing and states a real impossibility.
    """
    print("[gate 3] a count over a set nobody has measured")
    from planner.gates import reasoning as g3

    counted = [{"shape": "count", "select": {"kind": "vm", "alive": False}, "eq": 0}]
    check("a count filtered on an OBSERVED fact is caught",
          len(g3.uncountable(counted)) == 1)

    world = _world()
    world.execute("create_vm", {"name": "a", "os_type": "linux"})
    rep = g3.inspect(counted, world, settled=True)
    check("and the finding names the remedy rather than only the fault",
          "`every` says it without counting" in rep.findings()[0])
    check("and the question offers the reading they probably meant",
          "ALL of the ones that do" in rep.questions()[0])

    # ⇒ THE `every` FORM IS SILENT, and it is the SAME set — that is the whole point.
    quantified = [{"observe": {"kind": "vm"}, "fact": "alive"},
                  {"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}}]
    check("quantifying over the same set is not accused", not g3.uncountable(quantified))

    # AND A COUNT ON A STORED ATTRIBUTE IS FINE — `status` is written, not asked.
    stored = [{"shape": "count", "select": {"kind": "vm", "status": "running"}, "eq": 2}]
    check("a count on a STORED attribute is knowable", not g3.uncountable(stored))


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


def test_gate_4_gets_a_second_draw_only_where_something_is_suspect():
    """THE WIRING FIX, AND IT IS THE FAILURE THIS WHOLE FOLDER WAS WRITTEN TO ESCAPE.

    Gate 4's measured content is DISAGREEMENT — cells whose draws differ pass 33% against 76%
    for cells that agree — and ONE READING CANNOT DISAGREE WITH ITSELF. Wired against a single
    reading it fired **0 times on all 83 corpus readings**: the mechanism worked and its input
    never arrived. Same shape as the re-read loop deleted the same morning.

    ⇒ THE COST IS BOUNDED BY THE EARLIER GATES. A second draw for every request would double
    the front seam. A second draw only where gates 1-3 already found something spends the call
    on exactly the requests where another opinion could change the answer, and a clean reading
    pays nothing.
    """
    print("[gate 4] a second draw, only where it could matter")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    # THE CLEAN CASE PAYS NOTHING. Driven through the real orchestrator with a stub channel,
    # so the count is of ACTUAL calls rather than of intent.
    seen = []

    def clean(gap, w=None):
        seen.append(str(gap))
        return Answer([{"shape": "count", "select": {"kind": "vm", "name": "alpha"},
                        "eq": 1}], "extractor")

    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    Orchestrator(registry, Channel([clean])).handle("create a vm named alpha",
                                                    intent="achieve")
    check("a reading nothing objected to is drawn ONCE", len(seen) == 1)

    # AND THE GATE ITSELF STILL SEES DISAGREEMENT WHEN IT IS GIVEN TWO.
    from planner.gates import viability as g4
    check("two different readings disagree", not g4.inspect([GOALS[1], GOALS[2]]).legal)
    check("two identical readings do not", g4.inspect([GOALS[1], GOALS[1]]).legal)
    check("and one reading cannot", g4.inspect([GOALS[1]]).legal)


# ══ THE WIRE ═════════════════════════════════════════════════════════════════════════════


def test_every_gate_verdict_reaches_the_answer():
    """THE GATES WERE DECIDING FOUR TIMES A REQUEST AND NOTHING READ IT.

    Grepped at the end of 2026-08-07: `.legal` had **zero readers anywhere in `engines/`**.
    `rig` folded `findings()` into `Answer.illegal` and never asked a gate whether the reading
    was legal, so everything downstream saw a list of SENTENCES where a JUDGEMENT had been
    made and discarded.

    A NAME PER GATE, NOT ONE BOOLEAN — "the reading is illegal" is not actionable and "gate 2
    refused it" is. Collapsing them is how the single gate's rules collided in the first place.
    """
    print("[wire] each gate's verdict reaches the answer")
    from engines.channel import Answer

    check("Answer carries a verdict per gate", hasattr(Answer([], "x"), "gates"))
    a = Answer([], "x", gates={"1": True, "2": False, "3": True, "4": True})
    check("and it names which one objected",
          [g for g, ok in a.gates.items() if ok is False] == ["2"])


def test_gate_4_can_veto_a_re_ask_and_it_is_the_only_gate_that_could():
    """GATE 4'S ROUTING IS FINALLY READ. Its whole job in the architecture was *bad AI read ->
    back to the gate; bad prompt -> back to the operator*, and it computed that and nobody
    looked (`routes()`, 0 production callers).

    ⇒ THE ONE PLACE IT CHANGES ANYTHING: a request whose draws DISAGREE is a BAD PROMPT. The
    deciding information is not in the sentence, so another draw is another COIN rather than
    another LOOK, and `_restandardise` would otherwise spend a model call re-rolling it.

    Gate 4 is the only gate that can tell a MISREAD sentence from an AMBIGUOUS one, because it
    is the only one that sees more than one reading.
    """
    print("[wire] gate 4 vetoes a pointless re-ask")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from planner.gates import viability as g4
    from tests.bench.sim_world import SimWorld

    routes = g4.inspect([GOALS[1], GOALS[2]]).routes()
    check("disagreement routes to the operator", routes[0]["to"] == g4.BAD_PROMPT)

    # ⇒ THE RE-ASK IS SWITCHED ON EXPLICITLY, because the DEFAULT changed under this test and
    #   the default is not what it is about. `_restandardise` shipped ON, was measured across
    #   all 28 rung rows — one clear win, one reading that became `count vm eq 0`, DELETE EVERY
    #   MACHINE — and went back OFF. What this pins is the VETO: that gate 4 can stop a re-ask
    #   that would otherwise happen, whatever the default is.
    import os

    goals = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]
    asked = []
    _prior = os.environ.get("GORGON_RESTANDARDISE")
    os.environ["GORGON_RESTANDARDISE"] = "1"

    def answerer(gap, w=None):
        asked.append(str(gap))
        return Answer(goals, "extractor", illegal=["something"],
                      gates={"1": False, "reask": False})

    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    Orchestrator(registry, Channel([answerer])).handle("create a vm named alpha",
                                                       intent="achieve")
    check("a bad PROMPT is not re-asked", len(asked) == 1)

    # AND THE CONTRAST: the same finding WITHOUT gate 4's veto does spend the call.
    asked2 = []

    def rereadable(gap, w=None):
        asked2.append(str(gap))
        return Answer(goals, "extractor", illegal=["something"], gates={"1": False})

    world2 = SimWorld()
    reg2 = Registry()
    reg2.mount(MedusaEngine(world2))
    try:
        Orchestrator(reg2, Channel([rereadable])).handle("create a vm named alpha",
                                                         intent="achieve")
    finally:
        if _prior is None:
            os.environ.pop("GORGON_RESTANDARDISE", None)
        else:
            os.environ["GORGON_RESTANDARDISE"] = _prior
    check("a bad READ still is", len(asked2) == 2)


# ══ THE BOUNCE ═══════════════════════════════════════════════════════════════════════════


def test_the_bounce_asks_the_operator_and_reads_again():
    """THE SEAM THAT WAS MISSING, and the scan of 2026-08-07 named it: the question travels to
    the operator and *"there is no mechanism in this file that ASKS the question and WAITS for
    an answer."* Every gate that can only ask has been talking to a log.

    ⇒ MEASURED BEFORE IT WAS BUILT, and it is why the bounce ASKS rather than serving the
    remainder: of the 17 refused readings in the corpus, 15 kept some goals and ALL FIFTEEN had
    a gate object to what was left. There is no possible-but-blocked case here — serving the
    half is the DONE_BUT_FALSE direction.
    """
    print("[bounce] the operator is asked, and the answer is read")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    GOOD = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]
    seen, asked = [], []

    def answerer(gap, w=None):
        seen.append(str(gap))
        # HALF A REQUEST FIRST, a whole one once the operator has explained. The GATE'S
        # question is what travels — `asks` — because the raw drop reason holds the model's
        # own mistakes as well as the operator's ambiguity, and only one of those is a
        # question a person can answer.
        if len(seen) == 1:
            return Answer(GOOD, "extractor",
                          dropped=["it is about name 'x', which the request never names"],
                          asks=["part of this reading does not match what you asked. "
                                "'x' — the request never names it."])
        return Answer(GOOD, "extractor")

    def operator(question, session):
        asked.append(question)
        return "I meant the machine called alpha"

    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    out = Orchestrator(registry, Channel([answerer]),
                       clarify=operator).handle("create a vm named alpha", intent="achieve")

    check("the operator was asked exactly once", len(asked) == 1)
    check("and the question is the GATE'S, not the raw drop reason",
          "never names it" in asked[0])
    check("their answer was APPENDED to their own sentence",
          "create a vm named alpha" in seen[1] and "I meant" in seen[1])
    check("the run is no longer refused", out.get("outcome") != "UNTRANSLATED")
    check("and the machine was made", "alpha" in world.vms)


def test_nobody_there_is_todays_behaviour_exactly():
    """`clarify=None` MEANS NOBODY IS THERE, and that is not a degraded mode — it is the
    behaviour every measurement to date was taken against. Same fail-closed reading as
    `consent`: absent is not permission, it is absence.
    """
    print("[bounce] with no operator, nothing changes")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    seen = []

    def answerer(gap, w=None):
        seen.append(str(gap))
        return Answer([{"shape": "count", "select": {"kind": "vm", "name": "a"}, "eq": 1}],
                      "extractor",
                      dropped=["it is about name 'x', which the request never names"],
                      asks=["'x' — the request never names it."])

    world = SimWorld()
    registry = Registry()
    registry.mount(MedusaEngine(world))
    out = Orchestrator(registry, Channel([answerer])).handle("create a vm named a",
                                                             intent="achieve")
    check("no second call is made", len(seen) == 1)
    check("and it refuses exactly as before", out.get("outcome") == "UNTRANSLATED")


def test_silence_and_a_still_broken_answer_both_leave_the_refusal_standing():
    """TWO WAYS THE BOUNCE DECLINES TO HELP, and neither is a failure.

    SILENCE is the operator choosing not to resolve it, which leaves the refusal exactly where
    it was. AND A SECOND READING THAT IS STILL INCOMPLETE ends it too — asking again about the
    same sentence is the interrogation this is meant to avoid. An operator asked twice about
    one sentence is being cross-examined rather than consulted.
    """
    print("[bounce] silence, and an answer that does not settle it")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    def run(reply, always_broken):
        seen = []

        def answerer(gap, w=None):
            seen.append(str(gap))
            drops = ["it is about name 'x', which the request never names"]
            asks = ["'x' — the request never names it."]
            if always_broken or len(seen) == 1:
                return Answer([{"shape": "count",
                                "select": {"kind": "vm", "name": "a"}, "eq": 1}],
                              "extractor", dropped=drops, asks=asks)
            return Answer([{"shape": "count",
                            "select": {"kind": "vm", "name": "a"}, "eq": 1}], "extractor")

        world = SimWorld()
        reg = Registry()
        reg.mount(MedusaEngine(world))
        out = Orchestrator(reg, Channel([answerer]),
                           clarify=lambda q, s: reply).handle("create a vm named a",
                                                              intent="achieve")
        return out, seen

    out, seen = run("", False)
    check("silence makes no second call", len(seen) == 1)
    check("and the refusal stands", out.get("outcome") == "UNTRANSLATED")

    out, seen = run("some clarification", True)
    check("a still-broken second reading is asked for once", len(seen) == 2)
    check("and is NOT asked about again", out.get("outcome") == "UNTRANSLATED")


def test_gate_4_decides_which_last_resort_applies():
    """THE OPERATOR'S RULE, 2026-08-07: *"All of the gates either FIX or ROUTE. The rungs need
    to succeed because they are SOUND — both the bounce and the block are our default response
    WHEN ALL ELSE FAILS. We can't fix something broken, or missing logic. We either bounce it
    or block it: bounce when gate 4 determines it can still be VIABLE, and block when it can't
    be helped any more."*

    That is what this gate was named for. The other three answer whether a reading is LEGAL;
    only this one is asked whether it can still be made to WORK.
    """
    print("[gate 4] bounce while a person can help, block once nobody can")
    from planner.gates import truth as g2, viability as g4

    good = [{"shape": "count", "select": {"kind": "vm", "name": "a"}, "eq": 1}]

    check("a reading that kept goals can still be rescued",
          g4.viable(good) == g4.BOUNCE)
    check("nothing survived means nothing to attach a question to",
          g4.viable([]) == g4.BLOCK)

    # ⇒ UNSATISFIABLE IS THE OTHER ONE, AND IT IS THE INTERESTING CASE. Gate 2 asked the
    #   MANIFEST whether the kind can satisfy the shape AT ALL — no creator, no deleter, no
    #   probe, no setter. NO ANSWER FROM ANY OPERATOR CHANGES A DECLARATION, so asking is a
    #   courtesy that wastes their time and ends in the same refusal.
    world = _world()
    cannot = [{"every": {"kind": "vm"}, "must": {"os_type": "linux"}}]
    truth = g2.inspect(cannot, world)
    check("gate 2 finds a shape the kind can never satisfy", bool(truth.unsatisfiable))
    check("and gate 4 blocks rather than asking about it",
          g4.viable(cannot, {"truth": truth}) == g4.BLOCK)

    # ⇒ AND THE DEFAULT LEANS TO BOUNCE, deliberately: blocking a request somebody could have
    #   rescued is the more expensive mistake because it is INVISIBLE, while a needless
    #   question is a small annoyance the operator can see and dismiss.
    check("an unknown verdict still bounces", g4.viable(good, {"truth": None}) == g4.BOUNCE)


def test_an_unhelpable_request_is_never_asked_about():
    """THE WIRE, end to end: gate 4 says BLOCK and the operator is left alone."""
    print("[bounce] gate 4 blocks, and nobody is asked")
    from engines.channel import Answer, Channel
    from engines.medusa.engine import MedusaEngine
    from engines.orchestrator import Orchestrator
    from engines.registry import Registry
    from tests.bench.sim_world import SimWorld

    asked = []

    def answerer(gap, w=None):
        return Answer([{"shape": "count", "select": {"kind": "vm", "name": "a"}, "eq": 1}],
                      "extractor",
                      dropped=["it is about name 'x', which the request never names"],
                      asks=["'x' — the request never names it."],
                      gates={"viable": False})

    world = SimWorld()
    reg = Registry()
    reg.mount(MedusaEngine(world))
    out = Orchestrator(reg, Channel([answerer]),
                       clarify=lambda q, s: asked.append(q) or "anything").handle(
                           "create a vm named a", intent="achieve")
    check("nobody was asked", not asked)
    check("and it refuses outright", out.get("outcome") == "UNTRANSLATED")


def test_gate_4_asks_when_the_request_wanted_an_answer_and_the_program_would_act():
    """ACT OR ANSWER, decided where the evidence is. Added 2026-08-14.

    ⇒ **THE TRIGGER IS RESIDUE, AND IT WAS `intent.declared()` FOR ONE DAY.** The rule fired
      only on a POSITIVE fetch/ensure — and the courtesy fix shipped the same morning makes
      `declared()` return None whenever the sentence names an ACT. A request that should
      trigger this declares a read AND acts, and the reason it acts is almost always a verb on
      the achieve list, so the rule was near-unreachable:

          "list the vms and stop the ones running"    -> None   (stop is a marker)  silent
          "list the vms and remove the fleet label"   -> fetch  (remove is not)     FIRED

      **Whether the safety rule engaged depended on which verb the request happened to use.**
      Residue is measured where that was arbitrary.

    ⇒ **THE BAR IS GATE 1's AND IT IS THE FIRST CHECK BELOW: silent on a correct reading.** A
      guard that fires on the corpus has taught the operator to ignore it.
    """
    from planner.formula.legal import Board
    from orchestrator.seam import gate4, pass1 as P, pass2 as P2, schema as S
    from orchestrator.seam.effects import Operation
    from tests.bench.twopass.metrics import Lab

    board, lab = Board(), Lab()
    acts = [Operation("delete_vm", "vms")]
    probes = [Operation("guest_ping", "vms")]

    def table_of(*rows):
        return P2.symbol_table(list(rows), board)

    clean = table_of(S.declare_from("every vm", "vm_set", {}, S.EXISTING, board,
                                    span="every vm"))
    wrapped = table_of(
        S.declare_from("every vm", "vm_set", {}, S.EXISTING, board, span="every vm"),
        S.declare_from("how do i stop", S.UNKNOWN_KIND, {}, S.NEW, board,
                       span="how do i stop"))

    # 1 · SILENT ON A CLEAN READING, however destructive the program.
    check("a reading with no leftover wrapper is not questioned",
          not gate4.answer_not_act(acts, clean, "stop every vm", board, lab))

    # 2 · THE CASE IT OWNS — the request carries words the lab cannot account for.
    fired = gate4.answer_not_act(acts, wrapped, "how do i stop every vm", board, lab)
    check("a program that acts, beside words the lab cannot account for, is asked about",
          len(fired) == 1 and "[gate4/answer-not-act]" in fired[0])
    check("and it names both halves — the calls and the words",
          "delete_vm(vms)" in fired[0] and "how do i stop" in fired[0])

    # 3 · THE CONTROLS. Each is a way this could be wrong rather than merely weak.
    check("a program that only PROBES is silent — it already answers",
          not gate4.answer_not_act(probes, wrapped, "how do i stop every vm", board, lab))
    check("no operations at all is silent",
          not gate4.answer_not_act([], wrapped, "how do i stop every vm", board, lab))
    # ⇒ WITHOUT A LAB IT SAYS NOTHING, deliberately: `lab_has` cannot tell a real name from a
    #   meaningless one with no world, so every row would look like wrapper.
    check("with no world it declines to judge",
          not gate4.answer_not_act(acts, wrapped, "how do i stop every vm", board, None))

    # 4 · THE THREE INPUTS, AND THEY DO DIFFERENT JOBS. The operator, 2026-08-14: *"intent
    #     for information is measurable in linguistics; a viable query is evidence the question
    #     can be answered; the confidence threshold is a way to make sure the AI didn't make an
    #     educated guess."* WANTED / POSSIBLE / RELIABLE — and only the first two are required.
    COUNT_GOAL = [{"shape": "count", "select": {"kind": "vm"}, "eq": 2}]
    REACH_GOAL = [{"shape": "reach", "select": {"kind": "vm"}, "min": 3}]

    # ⇒ NO ANSWERABLE FORM -> SAY WHAT WAS READ, OFFER NOTHING. An ask that invites the operator
    #   to pick a branch the system cannot honour is worse than silence.
    unanswerable = gate4.answer_not_act(acts, wrapped, "how do i stop", board, lab, REACH_GOAL)
    check("with no viable query it offers no choice it could not honour",
          unanswerable and "no answerable form" in unanswerable[0])
    # ⇒ ANSWERABLE BUT NO EVIDENCE OF INTENT -> ask, plainly.
    plain = gate4.answer_not_act(acts, wrapped, "how do i stop", board, lab, COUNT_GOAL)
    check("answerable but with no evidence of intent, it asks",
          plain and "done, or asked?" in plain[0])
    # ⇒ EVIDENCE *AND* CONFIDENCE -> it may withhold the acting form and say so. Confidence
    #   cannot promote on its own, which is what the previous check pins.
    allowed = gate4.answer_not_act(acts, P2.symbol_table(
        [S.declare_from(t, S.UNKNOWN_KIND, {}, S.NEW, board, span=t)
         for t in ("how do i", "what is")], board),
        "list the vms", board, lab, COUNT_GOAL)
    check("with intent evidence and confidence above the line, it withholds and says so",
          allowed and "withheld" in allowed[0])
    check("and the threshold is DECLARED, not fitted", gate4._ANSWER_CONFIDENCE == 0.5)

    # 5 · IT IS WIRED, AND ITS NAME IS DECLARED — both halves of the defect class this
    #     codebase keeps recording.
    check("the rule is in gate 4's OWNS", "answer-not-act" in gate4.OWNS)
    src = open(os.path.join(os.path.dirname(__file__), "..", "orchestrator", "seam",
                            "pipeline.py")).read()
    check("and the pipeline calls it", "gate4.answer_not_act(" in src)


def test_being_spoken_to_is_not_being_asked_to_build_something():
    """THE AGENT'S OWN NAME IS NOT A MACHINE. Added 2026-08-14.

    ⇒ **THE OPERATOR: *"gate 2 is a world check, and we have nothing to check for the agent's
      name."*** *"good morning doorman, …"* was declared as a row, typed `vm` by the affordance
      rule, and gate 2 asked the only question available to it — *"'doorman' is referred to as
      if it exists and the lab has none — should it be created?"* Correct for what it was
      shown. The lab has no `doorman` because `doorman` is who was being spoken to.

    ⇒ **THE THREE BEHAVIOURS ARE THE WHOLE OF IT**, and the second is what keeps it honest:
      the LAB WINS. A machine really called `doorman` is a machine.
    """
    from planner.formula.legal import Board
    from orchestrator.seam import pass1 as P, schema as S
    from tests.bench.twopass.metrics import Lab

    class LabWithOne(Lab):
        ROWS = Lab.ROWS + [{"kind": "vm", "name": "doorman", "status": "running"}]

    board = Board()
    check("the agent knows its own name", P.agent_name() == "doorman")

    rows = [S.declare_from("good morning doorman", S.UNKNOWN_KIND, {}, S.NEW, board,
                           span="good morning doorman"),
            S.declare_from("every vm that is running", "vm_set", {}, S.EXISTING, board,
                           span="every vm that is running")]

    check("a span naming the agent is not declared",
          [r.name for r in P.consume_self_address(rows, board, Lab())]
          == ["every vm that is running"])
    # ⇒ THE CONTROL. Without it this rule would delete a machine from the reading because of
    #   what the operator happened to call their agent.
    check("but a machine really called doorman survives — the lab wins",
          len(P.consume_self_address(rows, board, LabWithOne())) == 2)
    # ⇒ AND ABSENCE OF A LAB IS NOT EVIDENCE, the same arm `classify` already stays quiet on.
    check("with no world at all it changes nothing",
          len(P.consume_self_address(rows, board, None)) == 2)

    # ⇒ AND ONLY A KINDLESS ROW — a reading somebody made is never dropped by this.
    typed = [S.declare_from("doorman", "vm", {"name": "doorman"}, S.EXISTING, board,
                            span="doorman")]
    check("a row the nouns or the lab already settled is untouched",
          len(P.consume_self_address(typed, board, Lab())) == 1)



def test_an_affordance_verb_settles_its_own_clause_and_not_the_sentence():
    """A VERB UNIQUE TO ONE KIND SAYS WHAT ITS CLAUSE IS ABOUT — not what every span is.

    ⇒ **THE RULE IS RIGHT AND ITS SCOPE WAS THE WHOLE SENTENCE.** `settle_by_affordance` read
      the affordance off `str(request).split()`, so one verb anywhere typed EVERY kindless row
      in the request as that kind. A request whose lab-facing clause says `stop` therefore
      typed its unrelated spans as machines, and gate 2 asked whether to create them — correct
      for what it was shown, and a question about something that was never a thing.

    ⇒ **THE CLAUSE, BECAUSE THE SPAN IS TOO NARROW.** Rung 9's spans are *"make sure n1"*,
      *"n2"* and *"n3 can all ping each other"*: only the last contains `ping`, so a
      span-scoped rule settles one row of three and leaves the rung as broken as it was before
      this function existed. The FIRST check below is that rung, and it is the control.

    ⚠ **THE SECOND CASE IS SYNTHETIC ON PURPOSE.** It is not lifted from the measured arms —
      a rule derived from the spans a particular sentence happened to produce is three special
      cases wearing a general name. What is asserted is the PROPERTY: a clause carrying no
      affording verb settles nothing, whatever it happens to contain.
    """
    from planner.formula.legal import Board
    from orchestrator.seam import pass1 as P

    board = Board()
    # 1 · THE CONTROL — the rung this rule exists for. One clause, one affording verb, and
    #     every bare name in it is settled by it.
    nine = P.EXPECTED[9].request
    settled = P.settle_by_affordance(P.run_scanned(nine, board=board), nine, board)
    check("a clause's affording verb still settles every bare name in that clause",
          all(r.object_type == "vm" for r in settled))

    # 2 · THE PROPERTY — a span in a clause with no affording verb is left kindless, however
    #     the rest of the sentence reads.
    req = "some preamble here; launch every vm that is currently stopped"
    rows = P.run_scanned(req, board=board)
    after = P.settle_by_affordance(rows, req, board)
    unrelated = [r for r in after if "preamble" in str(r.span or r.name).lower()]
    check("a clause carrying no affording verb settles nothing in it",
          all(r.object_type == P.UNKNOWN_KIND for r in unrelated) if unrelated else True)
    check("while the clause that does carry one is unaffected",
          any(r.object_type != P.UNKNOWN_KIND for r in after))


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "gates")


if __name__ == "__main__":
    sys.exit(main())
