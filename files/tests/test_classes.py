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

from planner.ir import classes as C
from planner.ir import config, effects

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
          {"create", "delete", "launch", "stop", "label", "alive"} <= set(surface["vm"]))
    # A NETWORK IS A CLASS WITH SOMETHING TO DO, which it was not until 2026-08-04: it had
    # `create` and nothing else, so it was the one kind Medusa could make and never unmake
    # or join. `delete_network` was a real tool the whole time and the manifest row simply
    # never named it.
    check("a network can be made, joined, left and unmade",
          set(surface["network"]) == {"create", "delete", "add_vm", "remove_vm"})
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
    # THE RECEIVER ARGUMENT IS THE MANIFEST'S, NOT A GUESS. `add_vm_to_network` names the
    # machine `vm_name` where `add_label` names it `name`, and a class assuming one spelling
    # would be a second authority for something already stated per setter.
    net = C.methods("network")
    check("and the receiver argument is whatever that row calls it",
          net["add_vm"].call("lab", "web") == ("add_vm_to_network",
                                               {"net_name": "lab", "vm_name": "web"}))
    check("an observation is a call too",
          vm["alive"].call("web") == ("guest_ping", {"name": "web"}))


def test_a_relation_has_one_receiver_and_it_is_the_thing_joined():
    """THE OPERATOR'S RULING, 2026-08-04: membership belongs to the network.

    IT IS NOT A PREFERENCE, IT IS FORCED. One tool call has ONE rendering, so if both ends
    offered a method the renderer would have to choose — and the end it did not choose would
    be a spelling you could type and never save, which is the defect the whole ruling exists
    to remove. `refs` is what says a row describes a relation, so which end owns it is READ
    rather than decided, and the inversion is the same row with its two arguments swapped.
    """
    print("[classes] a relation belongs to the thing being joined")
    surface = C.surface()
    check("the network owns joining and leaving",
          {"add_vm", "remove_vm"} <= set(surface["network"]))
    check("and the machine does not offer the same call under another name",
          "network" not in surface["vm"] and "unnetwork" not in surface["vm"])
    net = C.methods("network")
    check("joining and leaving are the manifest's own two tools",
          net["add_vm"].tool == "add_vm_to_network"
          and net["remove_vm"].tool == "remove_vm_from_network")
    check("a network can be unmade now, and the tool was always there",
          net["delete"].call("lab") == ("delete_network", {"net_name": "lab"}))


def test_an_act_is_reachable_and_promises_nothing():
    """THE OPERATOR'S REQUEST, 2026-08-04: *"to vm add: modify, getters about os_types,
    etc… kill, etc… everything"*, and *"its to replace the straight forward tool calls"*.

    THIRTY-FOUR OF FIFTY-THREE TOOLS WERE UNREACHABLE FROM MEDUSA, and almost every one takes
    `name` — a receiver — so almost every one was a method with nowhere to be declared. The
    manifest could say a tool CREATES, DELETES, WRITES AN ATTRIBUTE or ANSWERS A QUESTION,
    and `open_shell`, `resize_disk` and `update_config` are none of those.

    AND AN ACT MUST PROMISE NOTHING, which is the whole of why it is safe to add so many at
    once. `postcondition` returns None for one — "this tool proves nothing" — so no goal is
    ever closed by having acted. That is the rule the system is built on, applied to the
    surface that would otherwise break it.
    """
    print("[classes] you can do it, and it proves nothing")
    from planner.ir import effects
    vm = C.methods("vm")
    check("a machine can be killed, and it is `stop_vm` with the hammer set",
          vm["kill"].call("web") == ("stop_vm", {"name": "web", "force": True}))
    check("and `stop` is the same tool WITHOUT it — one row each, told apart by the argument",
          vm["stop"].call("web") == ("stop_vm", {"name": "web"}))
    check("a method may take several values, in the order the row lists them",
          vm["limit"].call("web", 80, 4096)
          == ("set_resource_limits", {"name": "web", "cpu_percent": 80,
                                      "memory_mb": 4096}))
    # A VALUE THE TOOL WANTS INSIDE AN OBJECT. Medusa has no object literal, so a raw
    # `modify(updates)` could only ever hand `update_config` a string — a method that always
    # fails. `into` puts the value where the tool wants it and the caller writes what they mean.
    check("a value the tool wants nested is nested",
          vm["memory"].call("web", 8192)
          == ("update_config", {"name": "web", "updates": {"memory_mb": 8192}}))
    check("a trailing value nobody passed is not sent as null",
          vm["logs"].call("web") == ("get_vm_logs", {"name": "web"}))

    # THE PROMISE, OR RATHER ITS ABSENCE — for every act whose tool is not ALSO something the
    # manifest already understands. `kill` is the exception and it is a real one: `stop_vm`
    # is a declared setter, so what it makes true is already known and `kill` inherits it
    # rightly. Everything else proves nothing, which is what makes adding sixteen of them at
    # once safe.
    setters = set((config.KINDS.get("vm") or {}).get("setters") or {})
    claims = [m.name for m in vm.values()
              if m.verb == C.ACT and m.tool not in setters
              and effects.postcondition(*m.call("web")) is not None]
    check(f"no act invents a postcondition ({claims or 'none'})", not claims)
    check("and the one that HAS one has it from a setter row, not from being an act",
          effects.postcondition(*vm["kill"].call("web"))
          == effects.postcondition(*vm["stop"].call("web")))
    # BUT THE RECEIVER STILL HAS TO EXIST, which is the half that IS derivable: you cannot
    # open a shell on a machine that is not there.
    needs = effects.precondition(*vm["shell"].call("web"))
    check("and an act still requires the member it acts on",
          any(p.get("select", {}).get("name") == "web" for p in needs))


def test_one_authority_decides_the_form_and_both_sides_read_it():
    """`receiver` is asked by the PARSER, to refuse the long form, and by the RENDERER, to
    print the short one. The day they disagree a saved program stops reading back as itself
    and the failure surfaces three layers away — so they ask the same function.
    """
    print("[classes] the form is decided in one place")
    check("a call on something the program holds is a method on it",
          C.receiver("launch_vm", {"name": "$b"}, {"b": "vm"}) == ("b", "launch", []))
    check("a relation resolves to the end that owns it",
          C.receiver("add_vm_to_network", {"net_name": "$lab", "vm_name": "$web"},
                     {"lab": "network"}) == ("lab", "add_vm", ["$web"]))
    check("a name the program does not hold has no receiver",
          C.receiver("launch_vm", {"name": "web"}, {}) is None)
    check("nor does one bound to something else",
          C.receiver("launch_vm", {"name": "$b"}, {"b": "network"}) is None)
    # AN ARGUMENT THE METHOD CANNOT CARRY KEEPS THE LONG FORM. `launch_vm(display: none)` is
    # what the writer emits for a machine it minted for its own use, and a method form would
    # silently drop it — so the method is asked to REBUILD the call and compared.
    check("and a call carrying more than the method can say stays a call",
          C.receiver("launch_vm", {"name": "$b", "display": "none"}, {"b": "vm"}) is None)
    # A CONSTRUCTOR IS NOT A METHOD ON AN INSTANCE — the operator's instruction, unchanged:
    # *"the way you create it stays the same with NEW CALL create_vm"*.
    check("a constructor is never a method on the thing it would make",
          C.receiver("create_vm", {"name": "$b"}, {"b": "vm"}) is None)


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
    # NO OTHER CLASS LEAKS IN — asked of the HEADERS, because a vm method may legitimately
    # mention another kind in its own description (`$vm.snapshots()` lists restore points).
    # What must not appear is a second class's surface.
    check("and nothing else — no other kind's surface leaks in",
          not any(f"{other}:" in text for other in C.surface() if other != "vm"))

    # THE HOT PATH IS UNTOUCHED, proved by asking the two builders that feed a model.
    from engines import extract as _extract
    import json as _json
    check("the extractor's schema does not carry a class surface",
          ".launch()" not in _json.dumps(_extract.schema()))
    from tests.bench.author_probe import _system
    from planner.ir import intent as _intent
    check("and neither does the author prompt",
          ".launch()" not in _system(_intent.ACHIEVE))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "classes"))


if __name__ == "__main__":
    main()
