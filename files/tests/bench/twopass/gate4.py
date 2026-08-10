"""GATE 4 — IS THIS WORTH SERVING? Not whether it is legal; whether it should be run.

⚠ MODEL-SPECIFIC TUNING LIVES UPSTREAM — see two-pass-rules.md §4b.

# ⇒⇒ WHY THIS EXISTS AS A GATE AND NOT AS A LINE IN THE PIPELINE

The destructive guard was written in `pipeline.py`, and I said at the time that it belonged
here. It stayed there for two days. That is exactly how a check ends up owned by nobody:

    gate 1  did you say this?          faithfulness to the request
    gate 2  can the world hold it?     the manifest, and the lab
    gate 3  is this operation legal?   the program, against what an operation may be
    gate 4  is it worth serving?       ⇐ IMPACT. Nothing above asks this.

**A step can be perfectly faithful, perfectly grounded and perfectly legal, and still be a
thing you would want to be asked about before it runs.** That is the whole of gate 4, and it is
why no other gate can hold it.

# ⇒ THE ONE RULE IT HAS, AND THE CORPSE

    rung 14  'make sure there are exactly two machines left'
      declared    vms                                  every machine, count eq 2
      operations  delete_vm(vms) · probe_exists(vms)
      ⇒ SERVE

`delete_vm` over the unfiltered set of every machine, and every check passed. Gate 3 was RIGHT
to stay quiet — nothing about it is illegal. The declaration says how many should be LEFT, the
operation says what to remove, and no gate compared the two.

⇒ **AND IT ASKS RATHER THAN REFUSING.** A high-impact act takes the operator's word, and only
  the operator can give it ([[gorgon-security-invariants]]).

⇒ **THE EXEMPTION IS THE REQUEST, NOT THE TARGET.** The first version exempted a NAMED
  individual, reasoning that deleting something named is no surprise. Rung 8 disproved it:
  *"db goes on a network called dmz"* produced `delete_network(dmz)` — the operator named `dmz`
  as a CREATE target, not as a delete target. So what matters is whether the REQUEST asks to
  destroy anything at all.
"""
from typing import List, Optional

from ..formula.legal import Board
from .effects import Operation

DESTRUCTIVE_WORDS = ("delete", "remove", "destroy", "tear down", "get rid",
                     "wipe", "drop", "kill off", "clear out")


def _destroyers(board: Board):
    """Each kind's declared destructive operation. READ, never listed (rule W5)."""
    from planner.ir import config as _config
    return {str(spec["delete"]): kind
            for kind, spec in (_config.KINDS or {}).items()
            if isinstance(spec, dict) and spec.get("delete")}


def confirmations(operations: List[Operation], table, request: str = "",
                  board: Optional[Board] = None) -> List[str]:
    """What the operator must agree to before this runs. Never a refusal, always a question."""
    board = board or Board()
    destroyers = _destroyers(board)
    by_handle = {sym.handle: sym for sym in table}
    asked_to_destroy = any(word in request.lower() for word in DESTRUCTIVE_WORDS)

    out: List[str] = []
    for op in operations:
        if op.operator not in destroyers:
            continue
        sym = by_handle.get(str(op.on))
        if sym is None:
            continue
        if asked_to_destroy and not sym.row.is_set:
            continue          # they said to remove it, and named the one thing to remove
        bound = ", ".join(f"{k} = {v}" for k, v in (sym.row.where or {}).items())
        narrow = (" — narrowed only by " + bound if bound else
                  " — NOTHING NARROWS IT" if sym.row.is_set else "")
        out.append(f"{op.operator}({op.on}) removes {sym.definition}{narrow}, and the request "
                   f"never asks to remove anything. Confirm before this runs.")
    return out


# ⇒ EVERY RULE NAME THIS GATE OWNS. `test_each_gate_owns_its_own_checks` asserts no other gate
#   emits one of these, which is the thing that would have caught the destructive guard sitting
#   in `pipeline.py` and `role-unsettled` sitting in the grammar gate.
OWNS = frozenset({"destructive-confirm"})
