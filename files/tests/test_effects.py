#!/usr/bin/env python3
"""
test_effects.py — a tool's postcondition must be TRUE, not merely well-formed.

Step 1 of the tiling design (#61): a tile is a tool that can say what it makes true, in the
same language the goals are written in. The claim is worthless unless it holds, so the
central test here RUNS each tool against the sim and evaluates its predicate through the
SAME seams the language uses.

That distinction is the lesson of 2026-07-31 applied one level up. A schema that parses is
not a schema that constrains; a postcondition that parses is not a postcondition that is
true. Both fail silently, and both were believed for weeks.

Run:  PYTHONPATH=. python3 -m tests.test_effects
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from executor.command_catalog import KNOWN_TOOLS
from planner.ir import config, effects
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


def test_every_declared_tool_is_real_and_names_real_attributes():
    """The manifest cannot claim an effect for a tool or attribute that does not exist.

    The drift guard. `kinds.<k>.setters` is hand-written data — the only hand-written part —
    so it is exactly where a typo would sit and never be noticed, because a postcondition
    nobody evaluates looks identical to a correct one.
    """
    print("[drift] declared effects vs the registry and the manifest")
    for tool, kind in sorted(effects.declared().items()):
        check(f"{tool} is a real tool", tool in KNOWN_TOOLS)
        check(f"{tool} names a real kind", kind in (config.KINDS or {}))
    for kind, spec in (config.KINDS or {}).items():
        attrs = set(spec.get("attrs") or ()) | set((spec.get("aliases") or {}).keys())
        for tool, s in (spec.get("setters") or {}).items():
            check(f"{tool} writes a real attribute of {kind}", s["attr"] in attrs)
            # A LITERAL VALUE MUST BE ONE THE ATTRIBUTE CAN TAKE. `stop_vm` claiming
            # status='halted' would produce a predicate that can never hold, and the
            # writer would loop forever trying to satisfy it.
            enum = (spec.get("attr_values") or {}).get(s["attr"])
            if enum and "value" in s:
                check(f"{tool}'s literal is a legal {s['attr']}", s["value"] in enum)


def test_a_postcondition_is_true_after_the_tool_runs():
    """THE ONE THAT MATTERS. Run the tool, then evaluate its own claim about the world."""
    print("[truth] each tool's postcondition holds after it acts")
    plan = [
        ("create_network",    {"net_name": "core"}),
        ("create_vm",         {"name": "alpha", "os_type": "linux"}),
        ("create_vm",         {"name": "beta",  "os_type": "linux"}),
        ("add_vm_to_network", {"vm_name": "alpha", "net_name": "core"}),
        ("add_label",         {"name": "alpha", "label": "fleet"}),
        # LAUNCH BEFORE STOP, and the reason is a finding rather than test hygiene: a
        # freshly created machine is ALREADY stopped, so `stop_vm`'s postcondition holds
        # before it runs. Starting beta first is what makes "false before" mean anything
        # here — and the already-satisfied case gets its own test below, because for a
        # tiling solver it is not an awkward edge, it is the signal to skip the tool.
        ("launch_vm",         {"name": "beta"}),
        ("stop_vm",           {"name": "beta"}),
    ]
    world = SimWorld()
    sel, holds = seams(world)
    for tool, args in plan:
        pred = effects.postcondition(tool, args)
        check(f"{tool} declares a postcondition", pred is not None)
        if pred is None:
            continue
        # FALSE BEFORE, TRUE AFTER — both halves. A predicate that already held is not
        # evidence the tool did anything, and it is precisely the vacuous witness #53 was
        # built to catch, arriving here as a bad TILE instead of a bad program.
        before, _ = holds(pred, {})
        world.execute(tool, args)
        after, why = holds(pred, {})
        check(f"{tool}: false before it ran", before is False)
        check(f"{tool}: TRUE after it ran ({why})", after is True)


def test_a_postcondition_that_already_holds_is_the_signal_to_skip_the_tool():
    """Found by the truth test above failing, and it is a feature of the design.

    A fresh machine is already stopped, so `stop_vm`'s postcondition holds before it runs.
    For a WRITER that is not an edge case — it is the whole basis of doing nothing when
    nothing is needed, the program-regime counterpart of `already_satisfied` that the tree
    regime has and the program regime does not (#21). A tile whose postcondition already
    holds should not be placed.

    It is also the honest reading of cost: the cheapest correct program for "make sure beta
    is stopped" against a stopped beta is the empty one, and only a postcondition can say so.
    """
    print("[idempotence] a tile whose claim already holds need not be placed")
    world = SimWorld()
    sel, holds = seams(world)
    world.execute("create_vm", {"name": "gamma", "os_type": "linux"})
    pred = effects.postcondition("stop_vm", {"name": "gamma"})
    already, _ = holds(pred, {})
    check("a new machine is already stopped, so the claim already holds", already is True)
    world.execute("stop_vm", {"name": "gamma"})
    after, _ = holds(pred, {})
    check("running it anyway does not break the claim", after is True)


def test_an_unknown_tool_says_unknown_rather_than_guessing():
    """None must mean unknown, and must not be filled in with something plausible.

    A solver that treats a guessed postcondition as met would report a goal reached because
    a tool it does not understand returned ok — "unverified is not done" broken from the
    inside, by the component whose job is to enforce it.
    """
    print("[honesty] unknown effects stay unknown")
    check("a tool with no declared effect returns None",
          effects.postcondition("check_system", {}) is None)
    check("a real tool with the wrong args returns None, not a broken predicate",
          effects.postcondition("add_label", {"name": "alpha"}) is None)
    check("an unregistered tool returns None",
          effects.postcondition("no_such_tool_xyz", {"name": "a"}) is None)


def test_the_predicate_is_the_goal_language_not_a_second_one():
    """A tile's claim must be a shape the language already evaluates.

    The point of the whole design is that a postcondition and a goal are comparable. Emitting
    a private shape here would give the writer a vocabulary the rest of Medusa cannot read —
    the third-lexicon defect this codebase keeps deleting.
    """
    print("[one language] postconditions are ordinary Medusa predicates")
    pred = effects.postcondition("add_label", {"name": "alpha", "label": "fleet"})
    check("the shape is a declared predicate",
          pred["shape"] in (config.PREDICATES or {}))
    check("its operand is a select", "select" in pred)
    check("it filters on BOTH the member and the attribute",
          pred["select"].get("name") == "alpha" and pred["select"].get("label") == "fleet")
    gone = effects.postcondition("delete_vm", {"name": "alpha"})
    check("a deleter claims a count of zero, same shape", gone["eq"] == 0)


def test_the_bench_seam_answers_only_for_kinds_it_TRACKS():
    """A HARNESS MUST NEVER BE MORE PERMISSIVE THAN THE SYSTEM IT MEASURES.

    `seams.select` fell through to `world.vms` for every kind it had no branch for, so it
    answered a question about a kind the sim does not track WITH THE MACHINES:

        select(kind=vm)               -> ['app1']
        select(kind=file)             -> ['app1']      <- the machines
        select(kind=__no_such_kind__) -> ['app1']      <- the machines

    THAT IS THE DEFECT `LabWorld.seams` RECORDS HAVING FIXED ON THE PRODUCTION SIDE — *"the
    production select, asked about a kind it did not know, answered with the nine MACHINES"* —
    and the fix never reached the bench, so every measurement was taken against a world more
    forgiving than the lab.

    IT WAS NOT COSMETIC. Every diff-based check read polluted evidence: creating 8 machines
    appeared in `dry_run.diff` as 8 files, 8 profiles and 8 templates as well, so `touched`
    and `unaddressed` reasoned about members that do not exist.
    """
    print("[seam] a kind the sim does not track answers EMPTY, not with the machines")
    from tests.bench.seams import seams
    from tests.bench.sim_world import SimWorld

    world = SimWorld()
    world.vms["app1"] = world.blank_vm()
    world.execute("create_network", {"net_name": "core"})
    select, _holds = seams(world)

    check("it answers for the machines", select({"kind": "vm"}) == ["app1"])
    check("and for the networks", select({"kind": "network"}) == ["core"])
    # THE KINDS THE MANIFEST DECLARES AND THE SIM DOES NOT TRACK. These are the ones that
    # polluted the diff, and they are declared — so a guard that only refused UNKNOWN kinds
    # would have missed every one of them.
    for kind in ("file", "profile", "template"):
        check(f"a declared but untracked kind answers empty ({kind})",
              select({"kind": kind}) == [])
    check("and a kind nothing declares answers empty",
          select({"kind": "__no_such_kind__"}) == [])


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "effects"))


if __name__ == "__main__":
    main()
