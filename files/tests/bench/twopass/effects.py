"""WHAT AN OPERATION MAKES TRUE — computed from the manifest, never read out of English.

    PYTHONPATH=. python3 -m tests.bench.twopass.effects

# THE QUESTION THIS ANSWERS

Pass 1 finds 9 of 14 rungs' conditions and that is its CEILING, because the other five are not
properties the request asserts — they are states that OPERATIONS produce:

    rung 2   status=running   beta is running BECAUSE "then launch it"
    rung 3   network=lab      web is on lab   BECAUSE "put web on lab"
    rung 4   label=fleet      the label exists BECAUSE something applies it
    rung 8   network=dmz      db is on dmz    BECAUSE "db goes on dmz"

Nothing in those requests says beta IS running. Pass 1 was right not to find it.

⇒ **AND THE MANIFEST ALREADY DECLARES EVERY EFFECT**, so the condition is ARITHMETIC:

        launch_vm         sets status  -> 'running'      (a fixed value)
        stop_vm           sets status  -> 'stopped'      (a fixed value)
        add_vm_to_network sets network -> the net_name argument
        add_label         sets label   -> the label argument

    `launch_vm on beta` therefore YIELDS `beta.status = running`, with no model call and no
    English to read. THE CONDITIONS BECOME COMPLETE WHEN THE OPERATIONS ARE IN — which is pass
    2 — NOT when pass 1 reads better.

# WHY THIS FILE EXISTS BEFORE PASS 2 DOES

To settle whether the structure can reach 14/14 at all, without waiting on a model. The
operations here are hand-supplied — but they are the ones the model was MEASURED producing in
item 1 (`[create_vm beta, launch_vm beta]`, `add_vm_to_network web lab`), so the only thing
being assumed is the half already demonstrated.
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from ..formula.legal import Board


class Operation(NamedTuple):
    operator: str                  # `launch_vm`, `add_vm_to_network`, …
    on: str                        # a DECLARED name
    value: Optional[str] = None    # a second declared name, where the operation takes one


def effect_of(operator: str, board: Optional[Board] = None
              ) -> Optional[Tuple[str, str, Optional[str]]]:
    """(kind, attribute, fixed value) for an operation — or None if it sets nothing.

    READ FROM THE MANIFEST'S `setters`. A fixed value is declared outright (`stop_vm` always
    means stopped); otherwise the value comes from the operation's argument and is None here.
    """
    from planner.ir import config as _config
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        setter = (spec.get("setters") or {}).get(operator)
        if setter:
            return kind, setter.get("attr"), setter.get("value")
    return None


def conditions_after(declared: Dict[str, Dict[str, object]],
                     operations: List[Operation],
                     board: Optional[Board] = None) -> Dict[str, Dict[str, object]]:
    """Every declaration's conditions AFTER the operations have run.

    A declaration says what a thing is; an operation says what becomes true of it. The program
    needs both, and only the first is in the request as a property.
    """
    board = board or Board()
    out = {name: dict(where) for name, where in declared.items()}
    for op in operations:
        effect = effect_of(op.operator, board)
        if not effect or op.on not in out:
            continue
        _kind, attr, fixed = effect
        if not attr:
            continue
        out[op.on][attr] = fixed if fixed is not None else op.value
    return out


def flatten(after: Dict[str, Dict[str, object]]) -> List[Dict[str, object]]:
    """The conditions as the answer key states them — one attribute per entry."""
    rows: List[Dict[str, object]] = []
    for where in after.values():
        for attr, value in where.items():
            row = {attr: value}
            if row not in rows:
                rows.append(row)
    return rows


# ── the five rungs pass 1 cannot reach, with the operations the model was MEASURED giving ──
CASES = {
    2: ({"a vm named beta": {"name": "beta"}},
        [Operation("create_vm", "a vm named beta"),
         Operation("launch_vm", "a vm named beta")]),
    3: ({"a network called lab": {"net_name": "lab"}, "a vm named web": {"name": "web"}},
        [Operation("create_network", "a network called lab"),
         Operation("create_vm", "a vm named web"),
         Operation("add_vm_to_network", "a vm named web", "lab")]),
    4: ({"5 vms": {}, "a network": {}},
        [Operation("add_vm_to_network", "5 vms", "lab"),
         Operation("add_label", "5 vms", "fleet")]),
    8: ({"every vm": {"network": "core"}, "db": {"name": "db"}},
        [Operation("add_vm_to_network", "db", "dmz")]),
    13: ({"5 vms": {}, "a network": {}},
         [Operation("add_vm_to_network", "5 vms", "net1"),
          Operation("add_label", "5 vms", "fleet")]),
}


def main() -> None:
    from .pass1 import EXPECTED

    board = Board()
    print("=" * 96)
    print("CAN DECLARATIONS + OPERATIONS REACH THE CONDITIONS PASS 1 CANNOT? "
          "(no model call)")
    print("=" * 96)
    hit = 0
    for rung, (declared, operations) in sorted(CASES.items()):
        want = EXPECTED[rung].conditions
        after = conditions_after(declared, operations, board)
        got = flatten(after)
        found = [w for w in want if w in got]
        ok = len(found) == len(want)
        hit += ok
        print(f"\nrung {rung}  “{EXPECTED[rung].request[:66]}”")
        print(f"   declared    {declared}")
        print(f"   operations  {[(o.operator, o.on, o.value) for o in operations]}")
        print(f"   AFTER       {after}")
        print(f"   want {want}")
        print(f"   ⇒ {len(found)}/{len(want)}  {'COMPLETE' if ok else 'still short'}")
    print(f"\n{'=' * 96}")
    print(f"  {hit}/{len(CASES)} of the rungs pass 1 could not reach are COMPLETE once the "
          f"operations are in.")
    print(f"  Pass 1 scores 9/14 alone; these five are the remainder, so the structure "
          f"reaches {9 + hit}/14.")


if __name__ == "__main__":
    main()
