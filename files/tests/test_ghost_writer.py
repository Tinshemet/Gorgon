#!/usr/bin/env python3
"""
test_ghost_writer.py — every rung, written by code alone. #60/#61.

All thirteen, each graded by THE RUNG'S OWN CHECKER — the same function that grades the
model. No model is called anywhere in this suite.

WHAT IS UNDER TEST IS THE WRITING HALF ONLY. Goals arrive as predicates and components —
what the operator's design has the AI extract — and whether a model produces them is a
separate measurement. Keeping them apart is the point: today a wrong program could mean the
goal was misread OR the writing fumbled, and nothing distinguished them.

THE GOALS BELOW ARE THE INTERFACE. Two forms appear, and the difference is deliberate:
  * a PREDICATE (`count`, `reach`) — something the language already evaluates
  * a COMPONENT (`every`, `per`, `observe`) — a quantifier, a selector and a target state,
    which the predicate language has no shape for and does not need one for. The writer
    lowers a component into per-member predicates and grounds it as a count it can compute.

Run:  PYTHONPATH=. python3 -m tests.test_ghost_writer
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.ir import consent, render, validate
from planner.ir import run as ir_run
from tests.bench.ghost_writer import Unsolvable, as_program, cover
from tests.bench.rungs import RUNGS
from tests.bench.seams import seams
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


C = lambda k, **f: {"shape": "count", "select": {"kind": k, **f}}
GOALS = {
 1: [{**C("vm", name="alpha"), "eq": 1}],
 2: [{**C("vm", name="beta"), "eq": 1},
     {**C("vm", name="beta", status="running"), "eq": 1}],
 3: [{**C("network", net_name="lab"), "eq": 1},
     {**C("vm", name="web"), "eq": 1},
     {**C("vm", name="web", network="lab"), "eq": 1}],
 4: [{**C("vm"), "eq": 5},
     {"every": {"kind": "vm"}, "must": {"network": "lab"}},
     {"every": {"kind": "vm"}, "must": {"label": "fleet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}],
 5: [{**C("vm", status="stopped"), "eq": 0}],
 6: [{**C("vm", label="red"), "eq": 3},
     {**C("vm", label="blue", **{"not": {"label": "red"}}), "eq": 2},
     {"every": {"kind": "vm", "label": "red"}, "must": {"network": "rednet"}},
     {"every": {"kind": "vm", "label": "blue"}, "must": {"network": "bluenet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "red"}, "min": 3},
     {"shape": "reach", "select": {"kind": "vm", "label": "blue"}, "min": 2}],
 7: [{**C("vm", label="prod"), "eq": 3}],
 8: [{"every": {"kind": "vm", "not": {"name": "db"}}, "must": {"network": "core"}},
     {**C("vm", name="db", network="dmz"), "eq": 1}],
 9: [{"shape": "reach", "select": {"kind": "vm"}, "min": 3}],
10: [{**C("vm"), "eq": 4},
     {"every": {"kind": "vm", "not": {"name": "golden"}}, "must": {"status": "running"}}],
11: [{"observe": {"kind": "vm"}, "fact": "alive"},
     {"every": {"kind": "vm", "alive": False}, "must": {"status": "stopped"}}],
12: [{"per": {"kind": "vm", "status": "running"}, "make": "snapshot", "link": "vm"}],
13: [{**C("vm"), "eq": 5},
     {"every": {"kind": "vm"}, "must": {"network": "net1"}},
     {"every": {"kind": "vm"}, "must": {"label": "fleet"}},
     {"shape": "reach", "select": {"kind": "vm", "label": "fleet"}, "min": 5}],
# THE DELETION RUNG, AND THE GOAL IS A PLAIN COUNT. That is not a simplification — it is
# the only shape that MEANS deletion today, and finding out why was the point of adding it.
#
# `count(vm WHERE label = 'scratch') = 0` does NOT mean "delete those machines". The writer
# reads a filtered zero-count as "no member carries this value" and surrenders the ATTRIBUTE,
# deliberately: taking `prod` off a machine is reversible and cheap, deleting the machine is
# neither, and a writer that destroyed a member to satisfy a claim about a label would be
# choosing the irreversible reading of an ambiguous request. So a filtered count can never
# express a deletion, and an UNFILTERED one — "there should be two" — is what removes members.
#
# THE LANGUAGE CANNOT SAY "these particular members must not exist", and that is a sharper
# statement of the deletion gap than "no rung deletes". It is left named rather than closed
# by inventing a component shape: language work is designed and reviewed before it is typed.
14: [{**C("vm"), "eq": 2}],
}



def _write(n):
    rung = next(r for r in RUNGS if r.n == n)
    world = SimWorld()
    if rung.setup:
        rung.setup(world)
    plan = cover(GOALS[n], world)
    return rung, world, plan, as_program(plan, GOALS[n], world)


def test_every_rung_is_written_by_code_and_passes_its_own_checker():
    """The headline. Thirteen rungs, no model, each graded by the benchmark's own function."""
    print("[all 13] written by code, graded by the rung")
    passed = 0
    for n in sorted(GOALS):
        rung, world, plan, prog = _write(n)
        ok, problems = validate(prog, known_names=world.names())
        sel, holds = seams(world)
        res = ir_run(prog, world.execute, select=sel, holds=holds,
                     known_names=world.names(), consent=True, intent="achieve")
        good = bool(rung.check(world))
        passed += good
        check(f"rung {n:>2}: valid={ok} ran={res['ok']} CHECKER={'PASS' if good else 'FAIL'} "
              f"({len(plan)} calls, best {rung.best})",
              ok and not problems and res["ok"] and good)
    # COUNTED FROM THE TABLE, NOT FROM A NUMBER IN THIS LINE. It read `passed == 13` and the
    # label said THIRTEEN, so adding rung 14 failed a suite in which every rung had passed —
    # the stale twin, in the headline of the writer's own proof.
    check(f"ALL {len(GOALS)}: {passed}/{len(GOALS)}", passed == len(GOALS))


def test_it_never_writes_an_ungrounded_or_self_vouching_program():
    """The property 60 of 78 model-written programs lacked, on all thirteen.

    2026-07-31 measured both alternatives: ASKING left 60 programs vouching for nothing, and
    DEMANDING it in the prompt took the ladder 7/78 -> 6/78 while breaking the decoder. Here
    each goal simply becomes the witness — and `vacuous == 0` matters as much as `grounded`,
    since the cheap way to satisfy a grounding rule is a witness that cannot fail (#53).
    """
    print("[grounding] every program vouches for itself, with claims that could fail")
    for n in sorted(GOALS):
        _, _, _, prog = _write(n)
        s = consent.survey(prog)
        check(f"rung {n:>2}: grounded, {s['vacuous']} vacuous",
              s["grounded"] is True and s["vacuous"] == 0)


def test_a_finished_world_gets_the_empty_program():
    """`already_satisfied` for the program regime (#21), as a consequence rather than a feature.

    RUNG 13 IS THE INTERESTING EXCEPTION AND IT IS CORRECT. Its setup leaves the registry
    already satisfied — five labelled machines on one network — yet the writer still emits
    five calls the FIRST time, because nothing has been PROBED and reach is a finding, never
    an inference (decision 6, A5). "Nothing to do" is true of the registry and false of the
    findings. On the second pass, with the answers in hand, it writes nothing.
    """
    print("[idempotence] nothing to do means nothing written")
    for n in sorted(GOALS):
        rung, world, plan, _ = _write(n)
        for tool, args in plan:
            world.execute(tool, args)
        again = cover(GOALS[n], world)
        if n == 11:
            # RUNG 11 IS DELIBERATELY NOT IDEMPOTENT, and that is the correct behaviour. Its
            # goal begins with an OBSERVATION, and a finding goes stale: whether a machine
            # answers is not a fact the registry stores, so asking again is the whole point
            # of asking. What must NOT repeat is the acting — a second pass may re-probe and
            # must not re-stop anything.
            check("rung 11: a second pass re-probes but CHANGES NOTHING",
                  again and all(t == "guest_ping" for t, _ in again))
            continue
        check(f"rung {n:>2}: a second pass emits no calls", again == [])


def test_it_stops_instead_of_improvising():
    """No tile, no lowering rule, no program — deliberately with no fallback.

    The whole reason to move generation out of the model is that this component does not
    invent steps, so producing something plausible for a goal it cannot reach is the one
    thing it must never do. `Unsolvable` is also the design's own signal: the request goes
    back for decomposition rather than forward as a guess.
    """
    print("[honesty] an unreachable goal raises rather than improvises")
    # `os_type` on a NEW machine is reachable and should be — it is a creation argument, and
    # the writer learning to pass it is an improvement, not a regression. The unreachable
    # case is changing it on a machine that ALREADY EXISTS: no setter writes os_type, and
    # no amount of lowering invents one.
    existing = SimWorld()
    existing.execute("create_vm", {"name": "x", "os_type": "linux"})
    for world, label, goal in (
        (existing, "no tool CHANGES os_type once a machine exists",
         {"shape": "count", "select": {"kind": "vm", "name": "x", "os_type": "windows"}, "eq": 1}),
        (SimWorld(), "a kind with no creator",
         {"shape": "count", "select": {"kind": "nonesuch", "name": "x"}, "eq": 1}),
    ):
        try:
            cover([goal], world)
            check(f"{label}: must not succeed", False)
        except Unsolvable:
            check(f"{label}: raises Unsolvable", True)


def test_the_same_request_against_the_same_world_writes_the_same_program():
    """DETERMINISM, and it is the property everything else rests on.

    #28 recorded rung 6 flipping BUILD FAILED -> BUILD OK on byte-identical code. That was
    the TREE path, which calls a model — and `pinned.py` already states in its own comment
    that "temperature 0 is deterministic" is a false assumption. So it was never a bug to
    chase; it was the documented behaviour of a model-driven path.

    The writer makes it structurally impossible. Same goals, same world, same program, every
    time — which is what lets a failing case be reproduced from a seed, what makes the fuzz
    corpus meaningful, and what allows a destructive plan to be reviewed before it runs. A
    writer that varied would take all three away at once.
    """
    print("[determinism] the same request writes the same program")
    import json as _json
    for n in sorted(GOALS):
        rung = next(r for r in RUNGS if r.n == n)
        seen = set()
        for _ in range(4):
            world = SimWorld()
            if rung.setup:
                rung.setup(world)
            seen.add(_json.dumps(cover(GOALS[n], world), sort_keys=True))
        check(f"rung {n:>2}: one program over four runs", len(seen) == 1)


def test_verified_costs_still_hold():
    """A3/#16 — THE VERIFIED COST BASELINE, all thirteen rungs, no model.

    `rung.best` prices a MODEL'S program and is deliberately loose, because a model may
    spend calls verifying its own work. `rung.verified` is a different number: what
    deterministic code actually does, graded by the rung's own checker. The writer is
    deterministic, so any movement here is a change in what the PLANNER does — which is
    exactly the tripwire that was missing when rung 4 went from 17 calls to 35 overnight
    with nothing comparing the number to anything.

    IT IS A TRIPWIRE, NEVER A TARGET. A number that falls because the system got better is
    progress and this test will say so; a number that falls because a rung was special-cased
    is the benchmark being gamed, and it will say that identically. Reading which is which is
    a person's job, and it cannot be done at all if nobody is told the number moved.
    """
    print("[cost] the writer's own price, per rung")
    moved = []
    for n in sorted(GOALS):
        rung, world, plan, _program = _write(n)
        for tool, args in plan:
            world.execute(tool, args)
        cost = len(plan)
        if rung.verified is None:
            moved.append(f"rung {n}: nothing recorded, writer costs {cost}")
        elif cost != rung.verified:
            moved.append(f"rung {n}: {rung.verified} -> {cost} "
                         f"({'cheaper' if cost < rung.verified else 'MORE EXPENSIVE'})")
        if not rung.check(world):
            moved.append(f"rung {n}: the plan ran and its own checker refused it")
    check(f"all {len(GOALS)} rungs cost what was recorded and pass their checker", not moved)
    for line in moved:
        print(f"       {line}")
    # AND THE LOOSE DIRECTION IS REPORTED, not enforced. Where `best` sits above what the
    # writer achieves, the gap is real information about model pricing — rung 6 is priced at
    # 30 and code does it in 22 — but tightening `best` to match would punish a model for
    # checking its own work, which is the mistake this file warns about one field over.
    loose = [(r.n, r.best, r.verified) for r in RUNGS
             if r.best is not None and r.verified is not None and r.verified < r.best]
    print(f"       `best` is loose on {len(loose)} rung(s): "
          + ", ".join(f"#{n} priced {b}, code does {v}" for n, b, v in loose))
    # THE REAL PROPERTY, rather than a note. Wherever both numbers exist, the writer must
    # come in at or under the price a model is allowed — if deterministic code ever cost MORE
    # than the model's budget, the budget would be pricing something nothing can achieve, and
    # every OVER_BUDGET verdict against a model would be measuring the harness.
    over = [(r.n, r.best, r.verified) for r in RUNGS
            if r.best is not None and r.verified is not None and r.verified > r.best]
    check(f"the writer never costs more than a model is priced at ({len(over)} do)", not over)


def test_a_member_the_program_made_is_referred_to_and_not_repeated():
    """THE OTHER HALF OF `new`, and `_as_statement` had already named it as unfinished:
    *"doing `new` properly means binding real identifiers AND referring to them with the
    sigil — a whole change, not half of one."*

    THE OPERATOR'S REASON, 2026-08-04: *"gorgon does deal with objects, vms are objects,
    networks are objects … all it does is interact with objects."* A program that HOLDS the
    machine it made can say what it is doing to it; one that repeats a literal is naming
    something it hopes is the same thing. It is also what makes the class surface appear at
    all — a method needs a receiver, and a receiver is a bound name.

    THE THREE REFUSALS ARE THE TEST. Each is a way to turn a readable program into a wrong
    one, and none of them is hypothetical.
    """
    print("[writer] what the program made, it refers to")
    from planner.ghost_writer import _by_reference
    from planner.ir import config

    made = [{"op": "new", "var": "lab", "kind": "network", "args": {"net_name": "lab"}},
            {"op": "new", "var": "web", "kind": "vm", "args": {"name": "web"}},
            {"op": "call", "tool": "add_vm_to_network",
             "args": {"net_name": "lab", "vm_name": "web"}},
            {"op": "call", "tool": "add_label", "args": {"name": "web", "label": "web"}}]
    out = _by_reference(made, config.KINDS)
    check("both ends of a relation become references",
          out[2]["args"] == {"net_name": "$lab", "vm_name": "$web"})
    # A VALUE THAT IS NOT A REFERENCE IS UNTOUCHED, even when it is the same word. A label
    # that happens to equal a machine name is still a label.
    check("and a value that merely LOOKS like a member is left alone",
          out[3]["args"] == {"name": "$web", "label": "web"})

    # A MEMBER THE PROGRAM DID NOT MAKE STAYS A LITERAL. The writer plans over a world it
    # READ; a machine that was already there is not this program's to name, and claiming it
    # would be claiming provenance the program does not have.
    found = [{"op": "call", "tool": "launch_vm", "args": {"name": "already-there"}}]
    check("a member the program did not make stays a literal",
          _by_reference(found, config.KINDS) == found)

    # A `NEW` OF SEVERAL BINDS A LIST — `scope[var] = names` when the amount is above one —
    # and a list in a `name:` slot is not a name.
    many = [{"op": "new", "var": "vms", "kind": "vm", "amount": 3, "args": {"name": "vm"}},
            {"op": "call", "tool": "launch_vm", "args": {"name": "vm"}}]
    check("a creation of several is not a receiver",
          _by_reference(many, config.KINDS)[1]["args"] == {"name": "vm"})

    # AND A REUSED VARIABLE IS SKIPPED ENTIRELY. `_as_statement` falls back to `{kind}1` when
    # a member's name is not a legal identifier, so two such creations bind the same word and
    # a reference means whichever ran last. Ambiguous is not better than literal.
    twice = [{"op": "new", "var": "vm1", "kind": "vm", "args": {"name": "a"}},
             {"op": "new", "var": "vm1", "kind": "vm", "args": {"name": "b"}},
             {"op": "call", "tool": "launch_vm", "args": {"name": "a"}}]
    check("an ambiguous binding is not used",
          _by_reference(twice, config.KINDS)[2]["args"] == {"name": "a"})


def test_an_open_attribute_leaves_a_value_by_being_unset():
    """A CAPABILITY THE WRITER HAD THE TOOLS FOR AND COULD NOT REACH, found 2026-08-05.

    `count(vm WHERE label=scratch) = 0` — the canonical teardown — asked `effects.complement`
    for the OTHER legal value of a label. A label is open-valued, so there is none, and the
    lowering returned `[]`. An empty lowering means "nothing to do", so `cover` raised
    `Unsolvable: nothing reaches` and DELETING BY LABEL WAS IMPOSSIBLE — while `remove_label`
    sat in the manifest as a declared unsetter the entire time.

    FLIPPING AND UNSETTING ARE DIFFERENT ANSWERS AND ONLY ONE NEEDS A COMPLEMENT. A closed
    attribute leaves a value by taking the other one; an open attribute leaves it by being
    unset. The complement is an OPPORTUNITY, not a precondition.

    THE HOLE WAS INVISIBLE UNTIL A SEPARATE BUG WAS FIXED. While the extractor was turning
    `amount: -1` into `eq: 1`, the writer was handed a goal it COULD plan, so nothing ever
    asked it for `eq: 0` on a label. Two defects, and the first hid the second.
    """
    print("[lowering] an open attribute is left by being unset, not flipped")

    def lab(n, label=True, stopped=False):
        w = SimWorld()
        for i in range(n):
            w.execute("create_vm", {"name": f"s{i}"})
            if label:
                w.execute("add_label", {"name": f"s{i}", "label": "scratch"})
            if not stopped:
                w.execute("launch_vm", {"name": f"s{i}"})
        return w

    zero = lambda **f: [{"shape": "count", "select": {"kind": "vm", **f}, "eq": 0}]

    calls = cover(zero(label="scratch"), lab(3))
    check("a label-scoped zero is now plannable at all",
          len(calls) == 3 and all(t == "remove_label" for t, _ in calls))
    check("and it names the value being dropped, not just the member",
          all(a.get("label") == "scratch" for _, a in calls))

    # THE CLOSED-ATTRIBUTE PATH MUST NOT HAVE MOVED. `status` HAS a complement, so "no
    # machine may be stopped" still means START them — it must never fall through to an
    # unsetter, and it must never mean delete.
    calls = cover(zero(status="stopped"), lab(3, label=False, stopped=True))
    check("a closed attribute still flips to its complement",
          len(calls) == 3 and all(t == "launch_vm" for t, _ in calls))

    # AND AN UNFILTERED ZERO IS STILL THE ONLY THING THAT DESTROYS MEMBERS.
    calls = cover(zero(), lab(3, label=False))
    check("an unfiltered zero still deletes the members",
          [t for t, _ in calls].count("delete_vm") == 3)
    check("a label-scoped zero destroys NOTHING",
          not any(t == "delete_vm"
                  for t, _ in cover(zero(label="scratch"), lab(3))))

    check("a goal already true still writes nothing", cover(zero(label="scratch"), lab(0)) == [])


def test_the_no_model_path_only_ever_emits_the_core():
    """PHASE 2'S BOUNDARY, MADE A FACT THE SUITE CHECKS.

    The operator, 2026-08-06: *"first make the writer version work and then build the user end
    on top of it through a post translator."* That split rests on a measurement:

        core     new · publish · call · ensure · foreach   count · reach
        surface  achieve · break · fetch · if              all · any · disjoint · is · not

    MORE THAN HALF THE LANGUAGE IS SURFACE, which is the empirical case for freezing it while
    the writer path is what fails. That was an observation somebody made once; the manifest
    now DECLARES it and this asserts it, so `core` cannot quietly grow a dependency on a
    surface form and the surface cannot quietly become load-bearing.

    ## THERE ARE TWO PRODUCERS ON THE NO-MODEL PATH AND THIS ONLY ASKED ONE

    It walked the written programs alone and concluded the core was FOUR ops. But `derive()`
    — ACHIEVE's deterministic engine — emits `foreach` and `call` when it closes a gap, and
    it runs at CORRECTION time (`engines/medusa/_run.py::_correct`), after a program has
    already run. So `foreach` never appears in a written program and is emitted by no-model
    code on every per-member correction.

    **CORE IS WHAT THE NO-MODEL PATH EMITS, not what the writer's first pass emits** — the
    distinction the two-way partition had no room for, and the reason the count was wrong.
    Both producers are asked here, which is what makes "no core op is unused" mean anything.

    AND IT WALKS NESTED BODIES. Reading only the top level is how a surface op becomes
    load-bearing without tripping this: today the writer emits nothing nested, so the two
    readings agree and the recursion costs nothing — which is exactly when to add it.

    IT WILL FAIL THE DAY EITHER PRODUCER LEARNS A NEW OP, and that is the point — the
    boundary should move by a manifest edit somebody meant, not by a code change nobody
    noticed.
    """
    print("[regime] the no-model path emits the core and nothing else")
    import importlib
    from planner.ir import config
    derive = importlib.import_module("planner.ir.derive")

    check("the partition covers every op", config.CORE_OPS | config.SURFACE_OPS == set(config.OPS))
    check("and every predicate",
          config.CORE_PREDICATES | config.SURFACE_PREDICATES == set(config.PREDICATES))
    check("with nothing in both", not (config.CORE_OPS & config.SURFACE_OPS)
          and not (config.CORE_PREDICATES & config.SURFACE_PREDICATES))

    seen_ops, seen_preds = set(), set()

    def walk(stmts):
        """Every op and predicate in a body, INCLUDING nested ones."""
        for st in stmts or ():
            if not isinstance(st, dict):
                continue
            if st.get("op"):
                seen_ops.add(st["op"])
            shape = (st.get("predicate") or {}).get("shape")
            if shape:
                seen_preds.add(shape)
            for value in st.values():
                if isinstance(value, list):
                    walk(value)

    # PRODUCER ONE — the writer, over every rung's known-good goals.
    for n in sorted(GOALS):
        rung, world, plan, _ = _write(n)
        temps = []
        walk(as_program(cover(GOALS[n], world, temps=temps), GOALS[n],
                        world, temps=temps).get("body"))

    written = set(seen_ops)

    # PRODUCER TWO — the correction engine. Three gaps that between them reach every
    # `foreach` branch `derive` has: a membership count short of its target, the same count
    # over its target (which corrects DOWNWARD), and an unreachable set.
    pool = ["a", "b", "c", "d", "e"]
    labelled = lambda f: [] if f.get("label") else pool
    every = lambda f: pool
    gaps = (({"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 3}, labelled),
            ({"shape": "count", "select": {"kind": "vm", "label": "prod"}, "eq": 1}, every),
            ({"shape": "reach", "select": {"kind": "vm"}}, every))
    corrected = set()
    for pred, select in gaps:
        fix = derive.derive(pred, select, {}, intent="achieve")
        check(f"the correction engine closes {pred['shape']}", bool(fix))
        before = set(seen_ops)
        walk(fix)
        corrected |= seen_ops - before

    check(f"the correction engine emits foreach (saw {sorted(corrected)})",
          "foreach" in corrected)
    check("and the writer never does — the two producers really are different",
          "foreach" not in written)

    stray_ops = seen_ops - config.CORE_OPS
    stray_preds = seen_preds - config.CORE_PREDICATES
    check(f"every op the no-model path emits is core (saw {sorted(seen_ops)})", not stray_ops)
    check(f"every predicate it emits is core (saw {sorted(seen_preds)})", not stray_preds)

    # AND THE CORE IS NOT LARGER THAN IT NEEDS TO BE. A core op NEITHER producer emits is
    # surface wearing the wrong label, and the freeze would be protecting the wrong half.
    unused = config.CORE_OPS - seen_ops
    check(f"and no core op goes unemitted ({sorted(unused)})", not unused)


def test_a_plan_can_carry_a_loop_and_the_program_names_nobody():
    """STEP 1 of writing OUTSIDE TIME. The operator, 2026-08-14: *"instead of thinking in
    write time we force it to think 'outside' time, more generic, applicable forever."*

    ⇒ **THE BLOCKER WAS THE PLAN'S TYPE, NOT THE TILES.** `Call` is `(tool, args)`, so a plan
      is a flat list of invocations and a loop cannot be written in one — which is why the
      writer resolves a select while writing and emits one call per name it finds. Measured
      the same day: **7 of 14 rungs carry a name read out of the lab**, and such a program is
      correct only for the lab it was written against.

    NOTHING EMITS A `Loop` YET. This pins the shape before the writer produces one, so the
    step that flips `_lower` over has something to be judged against rather than a claim.
    """
    from planner.ir import config, execute
    from planner.ir.render import render
    from planner.model_world import World, seams
    from tests.bench.ghost_writer import Loop

    def lab(*rows):
        w = World(kinds=config.KINDS)
        for name, status in rows:
            w.execute("create_vm", {"name": name, "os_type": "linux"})
            w.execute("launch_vm", {"name": name})
            if status == "stopped":
                w.execute("stop_vm", {"name": name})
        return w

    goal = [{"shape": "count", "select": {"kind": "vm", "status": "stopped"}, "eq": 0}]
    over = {"kind": "vm", "status": "stopped"}
    plan = [Loop("launch_vm", {"name": config.SIGIL + config.LOOP_VAR}, over)]

    author = lab(("alpha", "stopped"), ("beta", "stopped"))
    prog = as_program(plan, goal, author)
    text = render(prog)

    check("a loop-carrying plan renders a foreach", "FOREACH" in text)
    # ⇒ THE POINT OF THE WHOLE EXERCISE, ASSERTED DIRECTLY: no machine the writer LOOKED UP
    #   may appear. `alpha` and `beta` were in the lab when this was written.
    check("and the program names nobody it looked up",
          "alpha" not in text and "beta" not in text)
    # ⇒ `select`, NOT `in`. A literal list would be the write-time answer written down again.
    loop = next(s for s in prog["body"] if s.get("op") == "foreach")
    check("it carries the QUESTION, not the answer",
          loop.get("select") == over and "in" not in loop)
    check("the closing witness is still computed and still timeless",
          any(s.get("op") == "ensure"
              and (s["predicate"].get("select") or {}).get("status") == "stopped"
              for s in prog["body"]))

    # ⇒ AND IT SURVIVES THE LAB MOVING, which is the entire reason for the shape. Written
    #   against two stopped machines, run against three.
    runtime = lab(("alpha", "stopped"), ("beta", "stopped"), ("gamma", "stopped"))
    sel, holds = seams(runtime)
    res = execute.run(prog, runtime.execute, select=sel, holds=holds)
    check("it runs against a lab that MOVED since it was written", res.get("ok"))
    check("and it acted on the machine that was not there at write time",
          runtime.state["vm"]["gamma"].get("status") == "running")


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "ghost writer"))


if __name__ == "__main__":
    main()
