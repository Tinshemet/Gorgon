#!/usr/bin/env python3
"""
test_classes.py — every kind is a class, its methods are DERIVED, and `reach` splits.

THE ARGUMENT IS ERROR-AVOIDANCE. A method on an object cannot be asked about the wrong
scope, because the scope is the receiver — and scope is most of what goes wrong here.

THE TEST THAT MATTERS is not that the names are pretty. It is that NOTHING IS DECLARED
TWICE: every method traces back to a manifest row, so a method that drifted from the
manifest is not expressible. The design note names that as the specific care — *"methods
must not become a second vocabulary"* — and deriving them is what meets it by construction
rather than by discipline.

Run:  PYTHONPATH=. python3 -m tests.test_classes
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.ir import classes as C
from orchestrator.ai.planner.ir import config, effects

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_every_kind_is_a_class():
    print("[classes] the manifest was already one, in everything but name")
    surface = C.surface()
    check(f"every declared kind has a surface ({sorted(surface)})",
          set(surface) == set(config.KINDS or {}))
    check("a vm can be made, changed, asked and unmade",
          {"create", "delete", "launch", "stop", "label", "network", "alive"}
          <= set(surface["vm"]))
    # A KIND WITH NO CREATOR STILL HAS A CLASS. `file` is made by an arbitrary command, and
    # what it CAN do — be asked whether it is there — is exactly its surface.
    check("a kind with no creator still has what it does have",
          set(surface["file"]) == {"exists"})


def test_no_method_is_a_second_vocabulary():
    """THE SPECIFIC CARE THE DESIGN NOTE NAMES, asserted rather than promised."""
    print("[classes] every method IS a manifest row")
    tools = effects.tools_of(None)
    stray = [f"{k}.{m.name} -> {m.tool}"
             for k, ms in C.surface().items() for m in ms.values()
             if m.tool not in tools]
    check(f"no method invents a tool ({stray or 'none'})", not stray)

    # AND EVERY ACTING TOOL IS REACHABLE. A class that offered only some of what a kind can
    # do would be a narrower surface wearing a complete-looking name.
    # PRIMITIVES ARE EXEMPT AND THAT IS THE DEFINITION. `run_command` belongs to no kind —
    # it is the general host command — so it has no receiver and cannot be a method. A class
    # surface that claimed it would be claiming an owner it does not have.
    reachable = {m.tool for ms in C.surface().values() for m in ms.values()}
    missing = sorted(t for t in tools
                     if t not in reachable and t not in set(config.PRIMITIVES or ()))
    check(f"and every tool BELONGING TO A KIND is reachable ({missing or 'all'})",
          not missing)
    # `local_probe` IS THE EXCEPTION AND IT IS A REAL ONE: it is a primitive AND the `file`
    # kind names it as its observer, so it has a receiver after all. `run_command` does not.
    unowned = set(config.PRIMITIVES or ()) - reachable
    check(f"a primitive with no receiver belongs to no class ({sorted(unowned)})",
          "run_command" in unowned)


def test_a_method_is_the_call_the_writer_already_plans():
    """A method that produced something else would need a second runtime, and the whole
    argument for deriving these is that there is nothing new underneath."""
    print("[classes] a method IS a tool call, with a receiver")
    vm = C.methods("vm")
    check("a fixed-value setter takes no value",
          vm["launch"].call("web") == ("launch_vm", {"name": "web"}))
    check("a valued setter takes one",
          vm["label"].call("web", "prod") == ("add_label", {"name": "web",
                                                            "label": "prod"}))
    # THE RECEIVER ARGUMENT IS THE MANIFEST'S, NOT A GUESS. `add_vm_to_network` names it
    # `vm_name` where `add_label` names it `name`, and a class assuming one spelling would
    # be a second authority for something already stated per setter.
    check("and the receiver argument is whatever that setter calls it",
          vm["network"].call("web", "lab") == ("add_vm_to_network",
                                               {"vm_name": "web", "net_name": "lab"}))
    check("an observation is a call too",
          vm["alive"].call("web") == ("guest_ping", {"name": "web"}))


def test_reach_splits_by_receiver_and_that_is_the_whole_of_38():
    """#38 asked whether `reach` should also require a shared network. Production checked
    liveness, the bench checked both, and the two seams each looked correct while
    disagreeing. NEITHER WAS WRONG — one predicate was doing two jobs under one name.

    Split by receiver the ambiguity does not get decided, IT STOPS EXISTING. That is the
    sign of a good reformulation, and the first concrete evidence for the error-avoidance
    argument: the scope error was in the LANGUAGE, not in the model.
    """
    print("[classes] reach is two methods, of two receivers")
    check("a vm's reach is its LIVENESS — can this machine be pinged",
          C.reaches("vm") == "liveness")
    check("a network's reach is MEMBERSHIP — are its members connected",
          C.reaches("network") == "membership")
    check("and a kind that is neither asked nor referred to has no reach",
          C.reaches("profile") is None)
    # DERIVED FROM ROWS THAT ALREADY EXIST. A kind that can be ASKED has liveness; a kind
    # other members REFER TO has topology. Neither is a decision this module makes.
    check("liveness comes from the kind's own `observed`",
          bool((config.KINDS or {}).get("vm", {}).get("observed")))
    check("membership comes from another kind's setter REFERRING to it",
          any(s.get("refs") == "network"
              for s in (config.KINDS or {}).get("vm", {}).get("setters", {}).values()))


def test_the_public_surface_is_small_and_is_not_in_the_big_prompt():
    """THE FIRST ATTEMPT AT CLASSES WAS MEASURED AND WITHDRAWN — 64/78 -> 48/78, model-layer
    failures 1 -> 12, rungs unrelated to reach collapsing — because the interface went into
    the schema every author sees on every call.

    So the surface exists as a STRING FOR A NARROWED CALL, and this asserts the two things
    that keep the old cost away: it names one class, and nothing builds it into the
    whole-program prompt.
    """
    print("[classes] the black box stays shut on the hot path")
    text = C.public("vm")
    check("it names the class and its methods", text.startswith("vm:") and ".launch()" in text)
    check("and nothing else — no other kind leaks in",
          "network:" not in text and "snapshot" not in text)

    # THE HOT PATH IS UNTOUCHED, proved by asking the two builders that feed a model.
    from orchestrator.ai.engines import extract as _extract
    import json as _json
    check("the extractor's schema does not carry a class surface",
          ".launch()" not in _json.dumps(_extract.schema()))
    from tests.bench.author_probe import _system
    from orchestrator.ai.planner.ir import intent as _intent
    check("and neither does the author prompt",
          ".launch()" not in _system(_intent.ACHIEVE))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "classes"))


if __name__ == "__main__":
    main()
