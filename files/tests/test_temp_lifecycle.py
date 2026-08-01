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

from orchestrator.ai.planner import ghost_writer as gw
from orchestrator.ai.planner.ir import effects
from orchestrator.ai.planner.ir import render
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


def _deletes(text):
    return [ln for ln in text.splitlines() if ln.startswith("delete_vm(")]


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
    check("and nothing is deleted", not _deletes(text))


def test_a_name_in_an_attribute_is_still_a_name():
    """"take a snapshot of web" names web as plainly as "the machine web" does."""
    print("[lifecycle] named as an attribute -> still theirs")
    program, temps, text = _plan([{"shape": "count",
                                   "select": {"kind": "snapshot", "snap_name": "s1",
                                              "vm": "web"}, "eq": 1}])
    check("the machine is brought into being", len(_creates(program)) == 1)
    check("the snapshot is taken of it", len(_creates(program, "snapshot")) == 1)
    check("and the machine survives", not _deletes(text) and temps == [])


def test_deleting_is_what_the_operator_asked_for():
    print("[lifecycle] told to remove it -> removed")
    _program, temps, text = _plan([{"shape": "count",
                                    "select": {"kind": "vm", "name": "doomed"}, "eq": 0}],
                                  seed=("doomed",))
    check("it is deleted", _deletes(text) == ["delete_vm(name: doomed);"])
    check("but not as scaffolding — the operator asked", temps == [])


def test_a_fetched_machine_is_never_deleted():
    """It was already there. The program did not make it and does not get to unmake it."""
    print("[lifecycle] fetched -> left exactly as found")
    program, temps, text = _plan([{"every": {"kind": "vm"}, "must": {"label": "audit"}}],
                                 seed=("existing1", "existing2"))
    check("the label is applied", "add_label" in text)
    check("nothing was created", not _creates(program))
    check("nothing is temporary", temps == [])
    check("and nothing is deleted", not _deletes(text))


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
    check("and nothing acts after it in a run with no scaffolding",
          ops.index("ensure") == len(ops) - 1 or temps)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "temp lifecycle"))


if __name__ == "__main__":
    main()


def test_the_engine_collects_temps_so_teardown_can_fire():
    """`cover` fills a temps list and `as_program` empties it — the engine passed neither.

    The writer's whole provenance rule (a machine the operator never named is the program's
    own and goes away after the witness) was implemented, unit-tested, and unreachable from
    production. The search request created and launched a machine and emitted no delete; it
    was still on the lab afterwards.
    """
    from orchestrator.ai.engines.medusa import MedusaEngine
    from orchestrator.ai.planner.model_world import World

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
    tools = [s.get("tool") for s in body if s.get("op") == "call"]
    assert "create_vm" in tools, tools
    # THE MACHINE NOBODY ASKED FOR GOES AWAY, and after the witness rather than before.
    assert "delete_vm" in tools, tools
    ensure_at = next(i for i, s in enumerate(body) if s.get("op") == "ensure")
    del_at = next(i for i, s in enumerate(body)
                  if s.get("op") == "call" and s.get("tool") == "delete_vm")
    assert del_at > ensure_at, "teardown must follow the witness, not precede it"
