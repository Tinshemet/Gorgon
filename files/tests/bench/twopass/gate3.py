"""GATE 3 — IS THIS OPERATION LEGAL? The refusal, COMPUTED, because the model will not give it.

# ⇒⇒ WHY THIS IS THE REFUSAL AND A SCHEMA FIELD IS NOT

Three measurements now say the same thing, the third made on 2026-08-09:

    the `cannot` field           legal to fill, NEVER CHOSEN — 0 declines in 8
    a closed enum of reasons     4/8 declines, and it refused the parameterised-procedure
                                 request 3/3 — withdrawn
    a span-anchored quotation    2/8, three ordinary requests broken — withdrawn
    ⇒ `minItems: 1` REMOVED      **BYTE-IDENTICAL. 0/3.** The empty answer was made
                                 representable, with no prompt text and no new vocabulary,
                                 and the model still answered `add_label(n1, n2)` for
                                 *"make sure n1, n2 and n3 can all ping each other"*.

That last one is the cleanest of the three, because it is purely SUBTRACTIVE — it removed the
requirement to answer rather than adding a way to decline — and it still measured zero. The
standing law holds ([[gorgon-offering-is-not-using]]): **a shape the model will not emit is
not a mechanism.**

⇒ **SO THE DECLINE IS NOT ASKED FOR. IT IS DERIVED.** Every check below is a manifest lookup
  with no judgement in it, and each one catches a step the model produced 3 times out of 3.

# ⇒ THE THREE RULES, AND THE CORPSE EACH COMES FROM

    1 · YOU CANNOT OPERATE ON A THING WHOSE KIND IS UNKNOWN
        rung 9 — n1, n2, n3 are bare names no lab settled, so `add_label(n1, …)` asserts they
        are machines. Nothing said so. This is item 0's `?` reaching pass 2 intact.

    2 · A VALUE THAT NAMES AN OBJECT MAY ONLY FILL A SLOT THAT REFERS TO ONE
        rung 9 — `add_label` declares no `refs`, so its value is free text: a LABEL. Passing
        the handle `n2` says "label this machine with that machine". `add_vm_to_network` DOES
        declare `refs: network`, which is why `add_vm_to_network(web, lab)` is legal.

    3 · A SETTER THAT DECLARES A VALUE ARGUMENT REQUIRES ONE
        rung 12 — `add_vm_to_network(running_vms, null)` came back with the network missing.

# ⇒ AND A GATE STILL DOES NOT REPAIR

It says the step is illegal and why. It does not choose a legal operator, invent a network, or
drop the step — because only the operator can say what was meant
([[gorgon-gates-check-legality]]). What it produces is a refusal with a reason attached, which
is the thing three attempts at asking the model could not produce.
"""
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
from . import schema as S
from .effects import Operation


class Illegal(NamedTuple):
    step: Operation
    rule: str                # unknown-kind · value-is-an-object · value-missing · no-such-slot
    says: str

    def __repr__(self):
        return (f"{self.step.operator}({self.step.on}"
                f"{', ' + str(self.step.value) if self.step.value else ''}): {self.says}")


def _setter_for(operator: str) -> Optional[Dict]:
    """The manifest's declaration of this operation, wherever it lives."""
    from planner.ir import config as _config
    for spec in (_config.KINDS or {}).values():
        if not isinstance(spec, dict):
            continue
        for group in ("setters", "unsetters"):
            meta = (spec.get(group) or {}).get(operator)
            if meta:
                return meta
    return None


def kind_of_operator(operator: str) -> Optional[str]:
    """WHICH KIND THIS OPERATION BELONGS TO. Read off the manifest, never listed.

    ⇒ **THE GAP THE FIRST END-TO-END RUN LEFT OPEN.** Rung 7 came back with
      `delete_profile(prod_vms)` — a PROFILE's delete applied to a set of MACHINES — and every
      rule passed it, because `_setter_for` finds nothing for a delete and the check returned
      early. An operator that belongs to another kind is illegal on its face.

    ⇒ **AND IT COVERS DELETES AND SETTERS ONLY — A CREATOR IS DELIBERATELY EXCLUDED.** A
      creator's target is not its own kind: `create_snapshot(running_vms)` takes a snapshot OF
      the machines, and that is rung 12's CORRECT answer. Including creators here would have
      flagged it, which is a false alarm on a right answer — the most expensive kind. A setter
      and a delete act on a member of their own kind, and those are the ones with evidence.
    """
    from planner.ir import config as _config
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        if operator == spec.get("delete"):
            return kind
        if operator in (spec.get("setters") or {}) or operator in (spec.get("unsetters") or {}):
            return kind
    return None


def check(operations: List[Operation], table, board: Optional[Board] = None,
          world=None) -> List[Illegal]:
    """Every step, against the manifest and the symbol table. No model call, no judgement.

    `table` is `pass2.symbol_table`'s output — handle, row, definition. It is the ONLY source
    of what a handle means, which is rule D1 again: pass 2 may reference nothing else, so
    nothing else may be consulted to check it.
    """
    board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}
    out: List[Illegal] = []

    for step in operations:
        row = by_handle.get(step.on)
        if row is None:
            out.append(Illegal(step, "no-such-handle",
                               f"{step.on!r} was never declared"))
            continue

        # 1 · AN UNSETTLED KIND CANNOT BE OPERATED ON.
        if row.object_type == S.UNKNOWN_KIND:
            out.append(Illegal(step, "unknown-kind",
                               f"nothing says what {step.on!r} is, so {step.operator!r} "
                               f"cannot be applied to it — say what it is first"))
            continue

        # 4 · AN OPERATOR BELONGS TO A KIND, AND MAY NOT BE APPLIED TO ANOTHER.
        owner = kind_of_operator(step.operator)
        if owner and owner != row.kind:
            out.append(Illegal(step, "wrong-kind-operator",
                               f"{step.operator!r} is a {owner} operation and {step.on!r} "
                               f"is a {row.kind}"))
            continue

        meta = _setter_for(step.operator)
        if meta is None:
            continue                       # a creator, a probe or a delete — no value contract

        refs = meta.get("refs")
        value_arg = meta.get("value_arg")

        # 3 · A DECLARED VALUE ARGUMENT IS REQUIRED.
        if value_arg and step.value in (None, ""):
            out.append(Illegal(step, "value-missing",
                               f"{step.operator!r} needs a {value_arg} and none was given"))
            continue

        if step.value in (None, ""):
            continue

        names_an_object = str(step.value) in by_handle

        # 2 · AN OBJECT MAY ONLY FILL A SLOT THAT REFERS TO ONE — BOTH WAYS.
        if names_an_object and not refs:
            out.append(Illegal(step, "value-is-an-object",
                               f"{step.operator!r} takes a {value_arg or 'value'}, not a "
                               f"thing — {step.value!r} is a declared {by_handle[str(step.value)].object_type}"))
            continue
        if names_an_object and refs:
            got = by_handle[str(step.value)]
            if got.kind != refs:
                out.append(Illegal(step, "wrong-kind-value",
                                   f"{step.operator!r} needs a {refs} and {step.value!r} "
                                   f"is a {got.kind}"))
            continue

        # 5 · A REFERENCE SLOT NEEDS A THING THAT EXISTS — the symbol table, then the lab.
        #
        # ⇒ **THIS RULE EXISTS BECAUSE THE VALUE ENUM WAS REMOVED.** While `value` was
        #   restricted to declared handles the grammar guaranteed this, at the cost of making
        #   `add_label(prod_vms, "prod")` unsayable — five of seven pass-2 errors. Free text
        #   fixes those and opens this hole, so the guarantee moves from the grammar to here.
        #   D1 is unchanged either way: a reference must resolve or it is an error.
        if refs and not names_an_object:
            there = None
            if world is not None:
                from planner.gates import claims as _claims
                key = _claims.key_of(refs, board.kinds)
                try:
                    there = world.select({"kind": refs, key: str(step.value)}) if key else None
                except Exception:
                    there = None
            if not there:
                out.append(Illegal(step, "value-not-declared",
                                   f"{step.operator!r} needs a {refs} called {step.value!r} "
                                   f"and nothing declares one"))
    return out


def refused(operations: List[Operation], table, board: Optional[Board] = None,
            world=None) -> bool:
    """Is EVERY step illegal? Then the request cannot be served with this vocabulary.

    ⇒ **THIS IS THE DISTINCTION THAT MATTERS.** One bad step among good ones is a correction.
      All steps bad means the model was reaching — there was no legal answer and the grammar
      made it produce one anyway. Rung 9 is the second case, 4 steps out of 4.
    """
    if not operations:
        return True
    return len(check(operations, table, board, world)) == len(operations)
