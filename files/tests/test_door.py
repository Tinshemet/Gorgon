"""test_door.py — the regime ladder, pinned against a key committed before it existed.

`orchestrator/door.py` decides which regime a request wants — a tool, a stored procedure, an
assembled program, a question to the operator, or none of those because the request is not
about the lab at all. Its bar is not *"how many does it get right"*; `door_key`'s own scoring
rules say a figure over these rows would average a question against a destruction.

The pins, in order of what matters:

    1  NO CRITICAL CELL FIRES on a row the key did not mark hard — a lab request reaching the
       model ungated, a set request served by one call, a single call routed to the program
       regime (which reaches an unfiltered `count(vm) = 1`), or a rule enacted rather than
       proposed
    2  the ladder READS FACTS AND MAKES NO LOOKUPS, so a wrong destination names its own half
    3  every owner in `GORGON_NOUNS` is classified into a tier — no silent default
    4  the door costs NO MODEL CALL, which is the constraint the whole design rests on
    5  the key still describes the world it was written against

⚠ AND THE CEILING, unchanged and stated in the key itself: every row is one I wrote. This pins
  the RULES against regression; it is not evidence about English or about real traffic.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator import door
from tests.bench import door_key as K
from tests.bench import door_probe

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_the_key_still_describes_the_world():
    """A key whose premises have drifted grades nothing. `check()` asserts them both ways —
    that the words it treats as lab nouns still are, and that the words it treats as NOT lab
    nouns still are not. Two of the latter were wrong when the brief was written."""
    faults = K.check()
    for f in faults:
        print(f"       {f}")
    check(f"the key's premises hold against the manifest — {len(faults)} faults", not faults)


def test_no_critical_cell_fires():
    """⇒⇒ **THE ONE PIN THAT IS A GATE.** The key names four cells that are not merely wrong,
    and one of them is measured rather than feared: `create a vm` routed to the program regime
    lowers to an unfiltered `count(vm) = 1`, satisfied against a nine-machine lab by deleting
    eight — including the machines Gorgon itself runs on.

    ⇒ A row the key marked HARD is exempt and still reported. That is not a loophole: `hard`
      was written into the key before the ladder existed, so it cannot be used to excuse a
      regression after the fact.
    """
    results, world_says, library_says = door_probe.run()
    bad = [(t, keyed, got.goes) for t, keyed, got, hard, _ in results
           if not hard and K.direction(keyed, got.goes) == "CRITICAL"]
    for text, keyed, goes in bad:
        print(f"       {keyed} -> {goes}   {text}")
    check(f"no critical cell fires on a row the key did not mark hard "
          f"({world_says}, {library_says})", not bad)


def test_the_ladder_makes_no_lookups():
    """⇒⇒ **THE RULE AND THE READING ARE SEPARATE, AND THIS IS WHAT KEEPS THEM THAT WAY.**
    `route()` reads fields of `Facts` and nothing else — no manifest, no world, no registry.
    That is the whole reason a wrong destination can name which half was wrong.

    ⇒ Asserted by handing it a Facts built from nothing, with every field at its empty value:
      if the ladder reached for a lookup it would raise rather than answer.
    """
    empty = door.Facts(
        request="", clauses=(), acts=(), says="neither", mood="do",
        kinds=(), members=(), acting=(), asking=(), lab_predicate=False,
        universal=False, numeral=None, comparator="", counted=False, filtered=False,
        ordered=False, postcondition=False, addressed=False, governs=(), shortcut="",
        gorgon=(), procedure="", unknown=(),
    )
    got = door.route(empty)
    check("a Facts holding nothing routes without touching the world",
          got.goes == door.CHAT and got.rung)


def test_every_gorgon_owner_has_a_tier():
    """⇒ **NO SILENT DEFAULT.** `_tier` falls to SELF for any owner not named in
    `GOVERNANCE_OWNERS`, which is the right default and the wrong thing to leave unwatched: a
    new surface — say a second contract store — would quietly become a settings screen.
    Every owner the facts declare is classified here, so adding one is a decision.
    """
    owners = set(door.GORGON_NOUNS.values())
    known = door.GOVERNANCE_OWNERS | {"the chat session", "the model", "operator credentials",
                                      "the display", "the harness", "the host"}
    check(f"every owner is classified — {sorted(owners - known) or 'none unclassified'}",
          not (owners - known))
    # ⇒ AND THE TIER CANNOT NAME AN OWNER THAT DOES NOT EXIST. A typo in `GOVERNANCE_OWNERS`
    #   is silent in exactly the dangerous direction: the entry matches nothing, so a contract
    #   op quietly falls to SELF. The first version of this check was `… or True` and could
    #   not fail — the suite-not-asserting defect, in the suite written to prevent one.
    stray = door.GOVERNANCE_OWNERS - owners
    check(f"every governance owner is a declared owner — {sorted(stray) or 'none stray'}",
          not stray)


def test_governance_is_asked_before_the_lab():
    """⇒⇒ **A RULE NAMING `delete` AND `vm` IS STILL A RULE.** The critical cell is a standing
    rule ENACTED instead of proposed, and the only thing that stops it is the order of the
    rungs — governance is asked before anything lab-shaped is considered.

    ⇒ *"treat prod as read-only"* is the harder half: it carries no closed-class marker at all,
      and `governing.py` owns the frame that reads it.
    """
    world = door_probe.FixtureWorld(K.FIXTURE_MEMBERS)
    for text in ("never delete a vm without asking me first",
                 "prod vms must always keep a snapshot",
                 "treat prod as read-only",
                 "a jumpbox is a vm"):
        got = door.route(door.facts(text, world=world))
        check(f"governance wins — {text!r} -> {got.goes}", got.goes == door.GOVERNANCE)


def test_an_enumerator_absorbs_the_universal():
    """⇒⇒ THE OPERATOR'S OWN EXAMPLE, AND THE ONE PLACE A UNIVERSAL IS NOT A PROGRAM.
    *"list all vms"* is a universal over a kind and `list_vms` takes the whole population
    natively; `stop all the vms` must enumerate and then act on each, which is a program. The
    manifest states the difference — an enumerator against a setter — and nothing is listed.
    """
    world = door_probe.FixtureWorld(K.FIXTURE_MEMBERS)
    absorbed = door.route(door.facts("list all vms", world=world))
    acted = door.route(door.facts("stop all the vms", world=world))
    check("`list all vms` is one call", absorbed.goes == door.TOOL)
    check("`stop all the vms` is a program", acted.goes == door.PROGRAM)


def test_the_door_costs_no_model_call():
    """⇒⇒ **THE CONSTRAINT THE WHOLE DESIGN RESTS ON.** The door runs before the model does, on
    every request that arrives, including a greeting — so `pipeline.run`, which is two model
    calls' worth of questions in pass 1 and one in pass 2, cannot be its source.

    ⇒ Asserted by BREAKING the caller: `_call_ollama` is replaced with something that raises,
      and the whole key is routed through it. A door that reached for the model would fail
      every row instead of none.
    """
    import orchestrator.ai.chat.ollama_client as OC
    original = OC._call_ollama

    def _refuse(*a, **k):
        raise AssertionError("the door reached for the model")

    OC._call_ollama = _refuse
    try:
        world = door_probe.FixtureWorld(K.FIXTURE_MEMBERS)
        for k in K.CONTROLS:
            door.route(door.facts(k.text, world=world))
        check(f"all {len(K.CONTROLS)} controls route with the model unreachable", True)
    except AssertionError as e:
        check(f"all {len(K.CONTROLS)} controls route with the model unreachable — {e}", False)
    finally:
        OC._call_ollama = original


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "door")


if __name__ == "__main__":
    raise SystemExit(main())
