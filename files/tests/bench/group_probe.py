"""group_probe.py — can a SET-ALGEBRA check tell a right reading from a wrong one?

    PYTHONPATH=. python3 tests/bench/group_probe.py

## THE OPERATOR'S OBSERVATION, 2026-08-07

*"most of the failures like rung 3, 8, 11, 13 are group theory classics so we need to add that
into the logic/reasoning."* And they are — each of the four is a set operation:

    rung 3   put web on lab                      a BINARY RELATION (membership)
    rung 8   every vm on core EXCEPT db -> dmz   a PARTITION by set difference
    rung 11  stop the ones that do not answer    a FILTER by a RUNTIME-COMPUTED predicate
    rung 13  5 vms, all labelled, all ping       SUBSET + UNIFORM PROPERTY + CLIQUE

## THIS IS A MOCK-UP, DELIBERATELY, AND IT IS TESTED BEFORE ANYTHING IS IMPLEMENTED

The working protocol is research -> mock up -> TEST THE MOCK-UP -> implement. So this file
implements the check in ONE function, `contradictions()`, against a hand-written right reading
and a hand-written wrong one, and reports only whether the two come out DIFFERENT.

**THAT IS THE WHOLE BAR, and it is the bar the last three attempts failed.** On 2026-08-07 ten
meaning-level checks were run against rung 3's correct and incorrect readings and every one
produced BIT-IDENTICAL output — `lost []`, `vacuous None`, `unaddressed []`, `inert False`,
`judge proceed`. A rule that cannot discriminate is not a weak rule, it is not a rule.

## WHY THIS ASKS THE MODEL NOTHING

`select.except` ALREADY EXISTS in the extraction schema, on all five branches, and rung 8
still fails — so OFFERING the model a group shape is measured-dead before it is written
([[gorgon-offering-is-not-using]]). This computes the set algebra from the GOALS and the
WORLD, which are both already in hand. No vocabulary, no prompt, no schema, no model call.
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Set, Tuple

from planner import ghost_writer as _gw
from tests.bench.rungs import RUNGS
from tests.test_ghost_writer import GOALS

# ── THE WRONG READINGS, each the FAILURE ACTUALLY OBSERVED for that rung ──────────────────
#
# Hand-written on purpose. Drawing them from the live model would make this a measurement of
# the model rather than of the check, and the model is the noisy part
# ([[gorgon-ladder-noise-exceeds-the-effect]]).
WRONG: Dict[int, Tuple[str, List[dict]]] = {
    3: ("the relation clause is dropped — 'connect web to it' never becomes a goal", [
        {"shape": "count", "select": {"kind": "network", "net_name": "lab"}, "eq": 1},
        {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1},
    ]),
    8: ("the EXCEPTION is dropped — 'except db' never reaches the selector", [
        {"every": {"kind": "vm"}, "must": {"network": "core"}},
        {"shape": "count", "select": {"kind": "vm", "name": "db", "network": "dmz"}, "eq": 1},
    ]),
    11: ("the FILTER becomes an invented NAME — the sink for a clause it cannot shape", [
        {"observe": {"kind": "vm"}, "fact": "alive"},
        {"every": {"kind": "vm", "name": "unresponsive"}, "must": {"status": "stopped"}},
    ]),
    13: ("the CLIQUE is dropped — 'they all ping each other' never becomes a goal", [
        {"shape": "count", "select": {"kind": "vm"}, "eq": 5},
        {"every": {"kind": "vm"}, "must": {"network": "net1"}},
        {"every": {"kind": "vm"}, "must": {"label": "fleet"}},
    ]),
}


def _members(sel: Dict[str, Any], select) -> Set[str]:
    """The member set a selector denotes, resolved against the world.

    THE ONLY SET OPERATION THAT NEEDS TO EXIST FOR THIS CHECK. `not` is a set DIFFERENCE and
    the goal language already carries it (`planner/ir/validate.py:809`), so nothing new is
    being invented here — it is being READ, which nothing downstream currently does.
    """
    plain = {k: v for k, v in sel.items() if k not in ("not", "any", "all")}
    inside = {str(n) for n in (select(plain) or [])}
    carve = sel.get("not")
    if carve:
        removed = {str(n) for n in
                   (select({"kind": sel.get("kind"), **carve}) or [])}
        inside -= removed
    return inside


def _assignments(goals: List[dict], select) -> List[Tuple[Set[str], str, Any, str]]:
    """(members, attr, value, what said so) for every attribute a goal FORCES.

    Two goal shapes force an attribute, and reading only the first is what would make this
    miss rung 8 entirely:

        every S must {a: v}                  forces a=v on every member of S
        count {S, a: v} eq 1                 forces a=v on the member S names
    """
    out = []
    for g in goals:
        if "every" in g:
            who = _members(g["every"], select)
            for attr, value in (g.get("must") or {}).items():
                out.append((who, attr, value, f"every {g['every'].get('kind')} must {attr}={value}"))
        elif g.get("shape") == "count" and (g.get("eq") == 1):
            sel = g.get("select") or {}
            key = "name" if "name" in sel else ("net_name" if "net_name" in sel else None)
            if not key:
                continue
            named = {str(sel[key])}
            for attr, value in sel.items():
                if attr in ("kind", key, "not", "any", "all"):
                    continue
                out.append((named, attr, value, f"{sel[key]} must {attr}={value}"))
    return out


def single_valued(kind: str, attr: str) -> bool:
    """Can a member hold ONE value of this attribute, or SEVERAL?

    **THE DISTINCTION THE FIRST DRAFT OF THIS PROBE MISSED, AND IT INVALIDATED ITS ONLY
    POSITIVE RESULT.** The manifest declares it and nothing had to be invented: an attribute
    with an UNSETTER keyed by a value (`remove_vm_from_network(vm_name, net_name)`) is a SET —
    you remove one value and the others remain. An attribute whose setters merely assign
    (`stop_vm` / `launch_vm` -> `status`) holds one value at a time.

        vm.network   MULTI  (add_vm_to_network / remove_vm_from_network)
        vm.label     MULTI  (add_label / remove_label)
        vm.status    single (stop_vm, launch_vm — no unsetter)

    MEASURED against the world to be sure the manifest is not lying: adding `db` to `core` and
    then to `dmz` leaves `nets = {core, dmz}`, and `select(vm, network=core)` and
    `select(vm, network=dmz)` BOTH return `db`.
    """
    from planner.ir import config as _config
    spec = (_config.KINDS.get(kind) or {})
    unset = {v.get("attr") for v in (spec.get("unsetters") or {}).values()
             if isinstance(v, dict)}
    return attr not in unset


def contradictions(goals: List[dict], world, sound: bool = True) -> List[str]:
    """THE CHECK. Two goals that force the SAME attribute to DIFFERENT values on a member they
    SHARE cannot both hold — BUT ONLY IF THE ATTRIBUTE HOLDS ONE VALUE AT A TIME.

    `sound=False` reproduces the first draft, which did not ask. Keep it: the gap between the
    two columns IS the finding, and a probe that quietly fixed itself would have hidden a
    false positive that read exactly like a success.

    ⇒ FOR A MULTI-VALUED ATTRIBUTE THERE IS NO CONTRADICTION TO FIND. "every vm on core" and
    "db on dmz" are BOTH SATISFIABLE — db sits on both. The wrong reading of rung 8 is not
    illogical; it is a reading that LOST the operator's exclusion. That is information, not
    reasoning, and it belongs to gate 1.
    """
    select, _holds = _gw._seams_of(world)
    found = []
    forced = _assignments(goals, select)
    for i, (who_a, attr_a, val_a, why_a) in enumerate(forced):
        for who_b, attr_b, val_b, why_b in forced[i + 1:]:
            if attr_a != attr_b or val_a == val_b:
                continue
            if sound and not single_valued(who_a and "vm" or "vm", attr_a):
                continue
            both = who_a & who_b
            if both:
                found.append(f"{sorted(both)} must have {attr_a}={val_a} ({why_a}) "
                             f"AND {attr_b}={val_b} ({why_b})")
    return found


def main(argv=None) -> int:
    from tests.bench.sim_world import SimWorld
    print(f"\n{'rung':<6}{'naive':<22}{'SOUND (asks the manifest)':<28}what the gap means")
    print("─" * 108)
    score = {"sound": 0, "false-positive": 0, "blind": 0}
    for rung in RUNGS:
        if rung.n not in WRONG:
            continue
        why, wrong_goals = WRONG[rung.n]
        right_goals = GOALS.get(rung.n) or []
        col = {}
        for mode in (False, True):
            seen = {}
            for label, goals in (("RIGHT", right_goals), ("wrong", wrong_goals)):
                world = SimWorld()
                if rung.setup:
                    rung.setup(world)
                try:
                    seen[label] = contradictions(goals, world, sound=mode)
                except Exception as exc:
                    seen[label] = [f"RAISED {type(exc).__name__}: {exc}"]
            col[mode] = seen
        naive_ok = bool(col[False]["wrong"]) and not col[False]["RIGHT"]
        sound_ok = bool(col[True]["wrong"]) and not col[True]["RIGHT"]
        if sound_ok:
            verdict, key = "DISCRIMINATES — real", "sound"
        elif naive_ok:
            verdict, key = "the naive catch was a FALSE POSITIVE", "false-positive"
        else:
            verdict, key = f"blind — {why[:40]}", "blind"
        score[key] += 1
        print(f"{rung.n:<6}{('catches' if naive_ok else 'blind'):<22}"
              f"{('catches' if sound_ok else 'blind'):<28}{verdict}")
        for line in col[False]["wrong"]:
            print(f"{'':<6}naive said: {line[:88]}")
    print("─" * 108)
    print(f"  sound catches {score['sound']} · FALSE POSITIVES {score['false-positive']} · "
          f"blind {score['blind']}")
    print()
    print("  ⇒ THE CONTRADICTION CHECK IS SOUND ONLY WHERE AN ATTRIBUTE HOLDS ONE VALUE.")
    print("    `vm.network` and `vm.label` are SETS (they have unsetters), so 'every vm on")
    print("    core' and 'db on dmz' are BOTH SATISFIABLE — db sits on both. Rung 8's wrong")
    print("    reading is not ILLOGICAL, it LOST the operator's exclusion.")
    print("    ⇒ RUNG 8 IS A GATE 1 FAILURE (information), NOT A GATE 3 FAILURE (reasoning).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
