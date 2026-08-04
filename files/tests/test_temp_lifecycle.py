"""test_temp_lifecycle.py — WHOSE MACHINE IS IT, and therefore what happens to it.

THE OPERATOR'S RULE, in their words: *"if the user asks to create a vm that's a permanent
one you don't delete it; if he asks to delete it you do. But if a task calls for an action,
you create a temp vm, launch it, do the task and then delete it when you are done. If you
fetch one for the task, you don't delete it. You only delete when told, or when you created
temp vms for a task where the task goal was not the vms but the goal."*

IT REDUCES TO PROVENANCE, and that is why it needs no guess about intent:

    NAMED BY THE OPERATOR   theirs. Created if missing, never taken away.
    ASKED TO BE GONE        deleted, because that IS the request.
    FETCHED (already there) not ours. Never created, never deleted.
    MINTED AS A PRECONDITION the program's own scaffolding — headless, and torn down
                            after the witness has been taken.

AND DISPLAY FOLLOWS THE SAME LINE. A machine the operator asked for is one they intend to
LOOK at, so it keeps the shipped display; one the writer needed as a host is a shell and
nothing else, because a VNC session nobody opens is a port, a password and a listener per
machine.

TWO BUGS THIS FILE EXISTS BECAUSE OF, both found by running it rather than reasoning:
  * the first version treated a creation placed as a precondition as temp, full stop — so
    "make sure alpha is running" created alpha and then DELETED IT. The creation of the
    member the goal is ABOUT is not scaffolding; it is the goal.
  * the second still deleted `web` from "take a snapshot of web", because the name sat in an
    ATTRIBUTE rather than in the selector's key. A name the operator said is a name.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner import ghost_writer as gw
from planner.ir import effects
from planner.ir import master
from planner.ir import render
from tests.bench.sim_world import SimWorld

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _plan(goals, seed=()):
    world = SimWorld()
    for name in seed:
        world.execute("create_vm", {"name": name, "os_type": "linux"})
    temps = []
    calls = gw.cover(goals, world, temps=temps)
    program = gw.as_program(calls, goals, world, temps=temps)
    return program, temps, render(program)


def _deletes(program):
    """Deletions, asked of the IR — for the reason `_creates` states two functions below.

    It read the RENDERING and matched a line starting with `delete_vm(`, and the renderer
    now writes `CALL delete_vm(...)`. So it matched nothing whatever the program did: the
    check that a requested deletion happens passed the day it was written and has been
    reporting an empty list ever since. The lesson was already recorded beside it.
    """
    tools = set(effects.deleters(None))
    return [st for st in program["body"]
            if st.get("op") == "call" and st.get("tool") in tools]


def _creates(program, kind="vm"):
    """Creations, asked of the IR rather than the rendering.

    A CREATION IS A `new`, NOT A CALL — the language has an operator for it, and the writer
    now uses it. These assertions read the op so they say what they mean and do not break
    the next time the surface changes.
    """
    creators = {(effects._K(None).get(k) or {}).get("create") for k in (kind,)}
    return [st for st in program["body"]
            if st.get("op") in ("new", "call")
            and (st.get("kind") == kind or st.get("tool") in creators)]


def test_a_machine_the_operator_named_is_never_taken_away():
    print("[lifecycle] named by the operator -> theirs")
    program, temps, text = _plan([{"shape": "count",
                                   "select": {"kind": "vm", "name": "keeper",
                                              "status": "running"}, "eq": 1}])
    check("it is created", len(_creates(program)) == 1)
    check("nothing is marked temporary", temps == [])
    check("and nothing is deleted", not _deletes(program))


def test_a_name_in_an_attribute_is_still_a_name():
    """"take a snapshot of web" names web as plainly as "the machine web" does."""
    print("[lifecycle] named as an attribute -> still theirs")
    program, temps, text = _plan([{"shape": "count",
                                   "select": {"kind": "snapshot", "snap_name": "s1",
                                              "vm": "web"}, "eq": 1}])
    check("the machine is brought into being", len(_creates(program)) == 1)
    check("the snapshot is taken of it", len(_creates(program, "snapshot")) == 1)
    check("and the machine survives", not _deletes(program) and temps == [])


def test_a_name_in_a_must_is_still_a_name():
    """THE OTHER HALF OF THE SAME RULE, and it was missing until 2026-08-04.

    "put every machine on lab" names `lab` in the goal's MUST, not in its selector — and
    `_named_in` read only the selectors. So the writer minted the network, filed it as
    scaffolding, and tore it down at the end: the closing witness passed and then the
    program destroyed the very thing it had just asserted.

    IT WAS HIDDEN BY A MISSING MANIFEST ROW, which is the part worth remembering. `network`
    declared no deleter, so the teardown had nothing to emit and a wrong classification cost
    nothing. The row was added the same day and the bug arrived with it, fully formed and
    four rungs wide. A rule that cannot fire is not a rule that is right.
    """
    print("[lifecycle] named in a MUST -> still theirs")
    program, temps, text = _plan([{"every": {"kind": "vm"}, "must": {"network": "lab"}},
                                  {"shape": "count", "select": {"kind": "vm"}, "eq": 2}])
    check("the network is brought into being",
          len(_creates(program, "network")) == 1)
    check("it is not scaffolding", ("network", "lab") not in temps)
    check("and it is still there when the program ends",
          "delete_network" not in text)


def test_scaffolding_that_the_goal_IS_MADE_OF_is_not_scaffolding():
    """PROVENANCE SAYS WHO MADE IT; IT DOES NOT SAY WHETHER ANYTHING STILL NEEDS IT.

    "make these three machines reach each other" names no network, so the one the writer
    mints to connect them is, by provenance, pure scaffolding — and deleting it after the
    witness falsifies the goal the program has just asserted. The machines are left holding a
    network that is gone, which is also what the executor does to them: `delete_network`
    drops the record and leaves every member's NIC pointing at nothing.

    FOUND BY MEASUREMENT, not by reading. All 84 ladder runs were outcome-for-outcome
    identical before and after the day's changes; ONE line differed, rung 9 literal costing
    one call more, and that one call was this deletion. The rung was already failing for an
    unrelated reason, so the verdict hid it.
    """
    print("[lifecycle] the thing the goal is made of stays")
    program, temps, text = _plan([{"shape": "reach", "select": {"kind": "vm"}, "min": 3}],
                                 seed=("n1", "n2", "n3"))
    check("the network is still marked temporary — nobody named it",
          any(k == "network" for k, _n in temps))
    check("but it is NOT torn down, because the machines still sit on it",
          "delete_network" not in text)


def test_still_needed_answers_all_four_ways():
    """A GUARD THAT ONLY EVER SAYS "KEEP IT" IS NOT A GUARD, it is a disabled teardown. So
    the rule is asserted in both directions, and on the case that would quietly break it:
    a network whose only member is ALSO being removed is not needed by anything that
    survives, or a browser would pin the machine it runs on forever."""
    print("[lifecycle] needed by what survives, and only that")
    from planner.ghost_writer import _still_needed
    from planner.ir import config
    from tests.bench.seams import seams
    world = SimWorld()
    world.execute("create_vm", {"name": "host", "os_type": "linux"})
    world.execute("create_network", {"net_name": "n1"})
    world.execute("create_network", {"net_name": "empty"})
    world.execute("add_vm_to_network", {"net_name": "n1", "vm_name": "host"})
    select = seams(world)[0]
    check("a network something sits on is needed",
          _still_needed("network", "n1", select, config.KINDS, set()))
    check("an empty one is not — it goes",
          not _still_needed("network", "empty", select, config.KINDS, set()))
    check("and a machine nothing points at is not",
          not _still_needed("vm", "host", select, config.KINDS, set()))
    check("a reference from something ALSO being removed does not count",
          not _still_needed("network", "n1", select, config.KINDS, {("vm", "host")}))


def test_deleting_is_what_the_operator_asked_for():
    print("[lifecycle] told to remove it -> removed")
    program, temps, _text = _plan([{"shape": "count",
                                    "select": {"kind": "vm", "name": "doomed"}, "eq": 0}],
                                  seed=("doomed",))
    gone = _deletes(program)
    check("it is deleted",
          len(gone) == 1 and gone[0]["args"] == {"name": "doomed"})
    check("but not as scaffolding — the operator asked", temps == [])


def test_a_fetched_machine_is_never_deleted():
    """It was already there. The program did not make it and does not get to unmake it."""
    print("[lifecycle] fetched -> left exactly as found")
    program, temps, text = _plan([{"every": {"kind": "vm"}, "must": {"label": "audit"}}],
                                 seed=("existing1", "existing2"))
    check("the label is applied", "add_label" in text)
    check("nothing was created", not _creates(program))
    check("nothing is temporary", temps == [])
    check("and nothing is deleted", not _deletes(program))


def test_display_follows_the_same_line():
    """A machine the operator asked for is one they intend to look at."""
    print("[lifecycle] who it is for decides whether it has a screen")
    running = {"shape": "count",
               "select": {"kind": "vm", "name": "alpha", "status": "running"}, "eq": 1}
    check("the operator's machine keeps the shipped display",
          effects.invert(running) == ("launch_vm", {"name": "alpha"}))
    check("the program's own is a shell and nothing else",
          effects.invert(running, internal=True)
          == ("launch_vm", {"display": "none", "name": "alpha"}))


def test_a_creators_arguments_are_requirements():
    """A snapshot is OF a machine; a search runs IN a browser. Those must exist first."""
    print("[lifecycle] a creator's arguments name things that must already be there")
    need = effects.precondition("snapshot_create", {"snap_name": "s1", "name": "web"})
    check("the machine is required", need and need[0]["select"]["name"] == "web")
    check("and an ordinary attribute never becomes one",
          not effects.precondition("create_vm", {"name": "x", "os_type": "linux"}))


def test_the_teardown_comes_after_the_witness():
    """Tearing the scaffolding down first would leave the witness asserting against a world
    the program had just dismantled."""
    print("[lifecycle] prove it happened, then clean up")
    program, temps, text = _plan([{"shape": "count",
                                   "select": {"kind": "snapshot", "snap_name": "s1",
                                              "vm": "scratch"}, "eq": 1}])
    # `scratch` IS named here, so this run has no temps — the ordering rule is asserted on
    # the assembled body instead, where it is a property of `as_program` rather than of one
    # example. A run with nothing to tear down must still put its witness last.
    ops = [st.get("op") for st in program["body"]]
    check("the witness is present", "ensure" in ops)
    # NOTHING THAT ACTS, WHICH IS WHAT THIS ALWAYS MEANT. It asked whether the ENSURE was
    # the LAST statement, and `PUBLISH done` was added after it — a statement whose whole
    # effect is on the conversation. A witness followed by a report is still a witness that
    # nothing dismantled; asked as "is it last" the check fails on a program that is
    # perfectly ordered.
    after = program["body"][ops.index("ensure") + 1:]
    check("and nothing acts after it in a run with no scaffolding",
          temps or not [st for st in after if master.statement_acts(st)])


def test_the_engine_collects_temps_so_teardown_can_fire():
    """`cover` fills a temps list and `as_program` empties it — the engine passed neither.

    The writer's whole provenance rule (a machine the operator never named is the program's
    own and goes away after the witness) was implemented, unit-tested, and unreachable from
    production. The search request created and launched a machine and emitted no delete; it
    was still on the lab afterwards.
    """
    from engines.medusa import MedusaEngine
    from planner.model_world import World

    KINDS = {
        "vm": {"key": "name", "attrs": ["name", "status"], "nouns": ["vm"],
               "create": "create_vm", "delete": "delete_vm",
               "attr_values": {"status": ["running", "stopped"]},
               "create_defaults": {"status": "stopped"},
               "setters": {"launch_vm": {"attr": "status", "member_arg": "name",
                                         "value": "running"}}},
        "browser": {"key": "browser_name", "attrs": ["browser_name", "vm"],
                    "nouns": ["browser"], "create": "start_browser",
                    "delete": "stop_browser",
                    "create_requires": [{"kind": "vm", "must": {"status": "running"}}]},
    }

    class W(World):
        def __init__(self):
            super().__init__(KINDS)

    eng = MedusaEngine(W())
    plan = eng._plan([{"shape": "count", "select": {"kind": "browser"}, "eq": 1}], None)
    body = ((plan.get("program") or {}).get("body")) or []
    # A CREATION IS A `new`, NOT A `call`. This read `op == "call"` and could therefore
    # never see one — written before `NEW` issued the creation itself, and never updated
    # because the test was defined below the `__main__` guard and had never run.
    tools = [s.get("tool") for s in body if s.get("op") == "call"]
    made = [s.get("kind") for s in body if s.get("op") == "new"]
    assert "vm" in made, (made, tools)
    # THE MACHINE NOBODY ASKED FOR GOES AWAY, and after the witness rather than before.
    assert "delete_vm" in tools, tools
    # THE WITNESS IS WHATEVER VOUCHES, and it is not always an `ensure` — a creation
    # re-reads the world and files its own failure, so the writer's closing verdict here is
    # a `publish`. Asserting the OP rather than the ROLE made this test read a program shape
    # that has since changed; it never ran, so it was never corrected.
    witnesses = [i for i, s in enumerate(body) if s.get("op") in ("ensure", "publish")]
    assert witnesses, [s.get("op") for s in body]
    ensure_at = witnesses[0]
    del_at = next(i for i, s in enumerate(body)
                  if s.get("op") == "call" and s.get("tool") == "delete_vm")
    assert del_at > ensure_at, "teardown must follow the witness, not precede it"


def test_cleanup_runs_when_the_program_fails_midway():
    """Teardown is the program's `finally` — a failed run must not leak its own scaffolding.

    Three machines leaked in one afternoon: the search program failed at statement three,
    everything after it was abandoned, and the `delete_vm` for the machine it had minted
    lived in that tail. The operator who never asked for a machine was the one left with it.
    """
    from planner.ir import execute as EX

    done = []

    def world(tool, args):
        done.append(tool)
        # The middle statement fails, exactly as `camoufox_launch` did against a machine
        # with no guest agent.
        if tool == "stop_vm":
            return {"success": False, "error": "no"}
        return {"success": True}

    program = {"body": [
        {"op": "call", "tool": "create_vm", "args": {"name": "vm1", "os_type": "linux"}},
        {"op": "call", "tool": "stop_vm", "args": {"name": "vm1"}},
        {"op": "ensure", "predicate": {"shape": "count", "select": {"kind": "vm"}, "eq": 1}},
        {"op": "call", "tool": "delete_vm", "args": {"name": "vm1"}, "cleanup": True},
    ]}
    out = EX.run(program, world,
                 select=lambda q: [], holds=lambda p, s: (False, "no"),
                 known_tools={"create_vm", "stop_vm", "delete_vm"})

    assert not out["ok"]
    assert "delete_vm" in done, f"the minted machine leaked: {done}"
    # THE ORIGINAL FAILURE STANDS — cleanup is a second fact, not a correction of the first.
    assert out.get("failed") not in (None, "ok"), out
    # And a statement that ran is not reported as still owed.
    assert not [s for s in (out.get("remaining") or []) if s.get("cleanup")], out.get("remaining")


def test_cleanup_only_covers_what_the_writer_marked():
    """A runtime guessing which trailing deletes are safe to force would eventually be wrong."""
    from planner.ir import execute as EX

    done = []
    program = {"body": [
        {"op": "ensure", "predicate": {"shape": "count",
                                       "select": {"kind": "vm"}, "eq": 9}},
        {"op": "call", "tool": "delete_vm", "args": {"name": "theirs"}},
    ]}
    out = EX.run(program, lambda t, a: done.append(t) or {"success": True},
                 select=lambda q: [], holds=lambda p, s: (False, "no"),
                 known_tools={"delete_vm"})
    assert "delete_vm" not in done, "an unmarked delete was forced"
    assert any(s.get("tool") == "delete_vm" for s in (out.get("remaining") or []))

# THE ENTRY POINT BELONGS AT THE BOTTOM, and this is not style: `main()` ends in `sys.exit`,
# so every test defined BELOW this guard was never even defined when the suite was run
# directly — silently absent from the count, and from `run_all.py`. Found 2026-08-04 by a
# sweep after the same trap was hit in `test_extract.py`; three suites carried it and eleven
# tests had never run. `_suite.py` discovers by definition order, so placement is the only
# thing keeping a test alive.
def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "temp lifecycle"))


if __name__ == "__main__":
    main()
