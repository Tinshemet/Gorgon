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

from planner.formula.legal import Board
from . import schema as S
from .effects import Operation


class Illegal(NamedTuple):
    step: Operation
    rule: str                # unknown-kind · value-is-an-object · value-missing · no-such-slot
    says: str

    def __repr__(self):
        return (f"{self.step.operator}({self.step.on}"
                f"{', ' + str(self.step.value) if self.step.value else ''}): {self.says}")


# ⇒ WHAT GATE 3 OWNS: whether one OPERATION is legal. Not whether the world can hold a thing
#   (gate 2), not whether the request said it (gate 1), not whether it is worth doing (gate 4).
OWNS = frozenset({"no-such-handle", "wrong-kind-operator", "value-missing",
                  "value-is-an-object", "wrong-kind-value", "value-not-declared",
                  "circular-probe", "not-settled-yet", "unestablished-referent",
                  "wrong-creation-source", "incomplete-creation"})


def _makers(kind: str) -> set:
    """Operators that BRING ABOUT one of this kind — off the manifest, nothing hardcoded."""
    from planner.ir import config as _config
    spec = (_config.KINDS or {}).get(kind) or {}
    return {f"create_{kind}" if n == "create" else f"{n}_{kind}"
            for n in (spec.get("creators") or {})}


def _made_kind(operator: str, board: Board) -> Optional[str]:
    """The kind this operator BRINGS ABOUT, or None if it is not a creator."""
    for kind in board.kinds:
        if operator in _makers(kind):
            return kind
    return None


def _creation_sources(kind: str, board: Board) -> list:
    """Kinds a `create_{kind}` must be made FROM — [] when it is made from nothing.

    ⇒⇒ **`Board.makeable` WAS WRITTEN FOR THIS AND HAD NEVER BEEN CALLED.** Its docstring says
      *"kinds that can be created ONE PER MEMBER of this kind — rung 12's snapshot"*, and it
      computes exactly that from `create_args`. Another built-and-never-called, and it cost rung
      12 two weeks parked behind a claim that the manifest could not express the request.

    Only `create_snapshot` is constrained here (to `vm`); every other creator comes back
    unconstrained, so this rule cannot reach any other rung.
    """
    return [m for m in board.kinds if kind in board.makeable(m)]


def _referents(step, by_handle, row_here) -> list:
    """What this step needs to ALREADY BE THERE when it runs.

    ⇒ A CREATOR'S OWN TARGET IS NOT A REFERENT. `create_network(network_2)` does not presuppose
      `network_2` — it is what brings it about, so requiring it beforehand would make every
      creation illegal and every program unservable.
    """
    out = []
    makes_it = row_here is not None and step.operator in _makers(row_here.kind)
    # ⇒⇒ **A SOURCING CREATOR WITH ONE ARGUMENT IS AIMED AT ITS SOURCE, NOT ITS PRODUCT.**
    #   `clone_vm` declares `from: source_name` (manifest `creators.clone`), so it takes a thing
    #   it does NOT make. Rung 10 emits `clone_vm(golden)` with no second argument — and with
    #   only one argument, that argument can only be the source. Exempting it as *the creator's
    #   own target* let a clone from a NONEXISTENT source serve clean, because nothing then
    #   required `golden` to be there at all.
    #   ⇒ READ OFF THE MANIFEST, so a lab whose creators change gets this without an edit.
    if makes_it and step.value is None and _takes_a_source(step.operator):
        makes_it = False
    if not makes_it and row_here is not None:
        out.append(str(step.on))
    if step.value is not None and str(step.value) in by_handle:
        out.append(str(step.value))
    return [r for r in out if r in by_handle]


def _creator_spec(operator: str) -> Optional[Dict]:
    """The manifest's declaration of this creator, or None if the operator is not one."""
    from planner.ir import config as _config
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        for name, creator in (spec.get("creators") or {}).items():
            made = f"create_{kind}" if name == "create" else f"{name}_{kind}"
            if made == operator and isinstance(creator, dict):
                return creator
    return None


def _takes_a_source(operator: str) -> bool:
    """Does this creator declare a `from` — a thing it copies rather than makes?"""
    return bool((_creator_spec(operator) or {}).get("from"))


def _has_something_to_find_by(row, board: Board) -> bool:
    """Is there a value a FETCH could look this up by? A name, or a confirmed identity."""
    from planner.gates import claims as _claims
    if row.kind not in board.kinds:
        return False
    key = _claims.key_of(row.kind, board.kinds)
    return bool(row.identity or (key and (row.where or {}).get(key)))


def _in_the_world(row, world) -> bool:
    """Does the lab already hold this ONE thing? Then a FETCH establishes it.

    ⇒ THIS IS GATE 2's QUESTION ASKED AS A FACT, NOT RE-REPORTED AS A FINDING. Gate 2 says
      whether the world CAN hold a thing and complains when it cannot; this only needs the
      answer in order to decide whether the PROGRAM still owes a maker. Line 170's rule — a
      gate that re-derives another gate's finding is adding noise — is about duplicating the
      COMPLAINT, not about being forbidden to look.
    """
    if world is None:
        return False
    from planner.gates import claims as _claims
    from planner.ir import config as _config
    key = _claims.key_of(row.kind, _config.KINDS or {})
    value = row.identity or (row.where or {}).get(key)
    if not key or not value:
        return False                      # nothing to look it up BY — no fetch can settle it
    try:
        return bool(world.select({"kind": row.kind, key: value}))
    except Exception:
        return False                      # cannot ask -> cannot claim it is there


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

    # ⇒⇒ BINDING TIME IS AN ORDERING, AND NOTHING HAS EVER READ IT.
    #
    #   `settled` has been on every row since the schema was written — *at plan time* or *at
    #   run time* — and the only consumer was gate 2 refusing to CREATE a residual set. It also
    #   states an ORDER, and ignoring that let this serve silently:
    #
    #       probe_alive(not_alive_vms) · stop_vm(vms)      -> SERVE, nothing objects
    #
    #   which stops EVERY machine instead of the unresponsive ones — rung 11 inverted into a
    #   fleet-wide outage. Every existing check passes it: both operations are legal, both
    #   operators are warranted by the request, both handles are used, and `stop_vm` is not a
    #   delete so the destructive guard stays quiet.
    #
    #   ⇒ TWO RULES FALL OUT OF THE ONE FACT, and both are arithmetic over the table:
    #     A RESIDUAL SET IS NOT KNOWN UNTIL SOMETHING ASKS THE MACHINES, so an operation on one
    #     must come AFTER the probe that settles it; and THE PROBE THAT SETTLES IT CANNOT TAKE
    #     IT AS ITS TARGET, which is the circularity above — you cannot ask only the machines
    #     that failed to answer whether they answer.
    from planner.ir import config as _config
    probe_for: Dict[str, str] = {}
    for spec in (_config.KINDS or {}).values():
        if isinstance(spec, dict):
            for fact in (spec.get("observed") or {}):
                probe_for[str(fact)] = f"probe_{fact}"
    settled_now: set = set()
    established: set = set()

    for step in operations:
        row_here = by_handle.get(step.on)
        if row_here is not None and row_here.residual:
            observed = [a for a in (row_here.where or {}) if a in probe_for]
            wanted = {probe_for[a] for a in observed}
            if step.operator in wanted:
                out.append(Illegal(step, "circular-probe",
                                   f"{step.on!r} is the set of machines that answered a "
                                   f"certain way, so {step.operator!r} cannot be asked OF it — "
                                   f"ask the whole set first"))
                continue
            if wanted and not (wanted & settled_now):
                out.append(Illegal(step, "not-settled-yet",
                                   f"{step.on!r} is decided by asking the machines and nothing "
                                   f"has asked yet — {', '.join(sorted(wanted))} must run first"))
                continue

        # ⇒⇒ EVERY REFERENT NEEDS AN ESTABLISHER, AND ONE MUST RUN BEFORE THIS STEP.
        #
        #   The operator, 2026-08-11: *"it just forgot that a prerequisite to use it is to check
        #   if it exists, and if not, create it. If something is referenced but not created, you
        #   need to supply it either through a FETCH or CREATE."*
        #
        #   ⇒ **`not-settled-yet` ABOVE IS ALREADY THIS RULE, FOR ONE ESTABLISHER.** A
        #     probe-defined set is established by a PROBE; a thing the lab holds is established
        #     by a FETCH; anything else must be established by a CREATOR. Same rule, three
        #     establishers, one grain — this step and its own referents.
        #
        #   ⇒ **AND IT IS WHY THIS IS GATE 3's AND NOT GATE 4's.** Phrased as *no step creates
        #     network_2* it reads as an absence, which is the whole program's business. Phrased
        #     as *this step's referent is never established* it is a fact about THIS operation's
        #     own soundness, statable without reference to any other step — the re-charter's own
        #     grain test. It replaces `uncreated-declaration`, which sat in gate 1.
        #
        #   ⇒ **A SET IS EXEMPT, AND RUNG 11 BOUGHT THAT GUARD.** `every vm` is a SELECTION over
        #     the world, not an object anybody makes; demanding a maker for one bounced the rung
        #     this design exists for. Only a single thing can be owed a creator.
        for referent in _referents(step, by_handle, row_here):
            ref_row = by_handle[referent]
            if referent in established or ref_row.is_set or ref_row.residual:
                continue
            # ⇒⇒ AN UNSETTLED KIND IS GATE 2's QUESTION, AND THIS RULE MUST STAY OUT OF IT —
            #   the same rule the SECOND loop already obeys, and I broke it here on the first
            #   attempt. Rung 9's `n1` is unsettled AND absent from the lab, so this fired
            #   `unestablished-referent`, and a BOUNCE outranks an ASK — turning *"nothing says
            #   what n1 is"*, which is the honest and correct answer, into a demand that the
            #   model go and make one. **You cannot owe a creator for a thing nobody has said
            #   the kind of.** Establishment is only a question once the kind is settled.
            if ref_row.object_type == S.UNKNOWN_KIND or ref_row.kind not in board.kinds:
                continue
            if _in_the_world(ref_row, world):
                continue                  # a FETCH establishes it; nothing is owed
            # ⇒⇒ **AND WITH NO WORLD TO ASK, NOTHING IS OWED EITHER — ABSENCE IS NOT A VERDICT
            #   UNTIL SOMEBODY HAS LOOKED.** `planner/gates/truth.py` states this as decision 6
            #   and I broke it on 2026-08-11: `_in_the_world(row, None)` returns False, which
            #   this rule read as *nothing establishes it*, so every named referent was flagged
            #   whenever the caller passed no lab. A thing with a name to look up by is UNKNOWN
            #   without a world, not missing.
            #   ⇒ AN UNNAMED ROW IS DIFFERENT AND STILL FLAGGED: no probe could ever find it,
            #     so it needs a maker whether or not a lab is attached. That is rung 6.
            if world is None and _has_something_to_find_by(ref_row, board):
                continue
            out.append(Illegal(step, "unestablished-referent",
                               f"{referent!r} is used here and nothing establishes it first — "
                               f"the lab does not hold one and no earlier step makes one"))

        if row_here is not None and step.operator in _makers(row_here.kind):
            established.add(step.on)      # THIS step is what brings it about
        settled_now.add(step.operator)

    for step in operations:
        row = by_handle.get(step.on)
        if row is None:
            out.append(Illegal(step, "no-such-handle",
                               f"{step.on!r} was never declared"))
            continue

        # ⇒⇒ A CREATOR MUST BE AIMED AT WHAT IT IS MADE **FROM**.
        #
        #   Rung 12 — *"take a snapshot of every running vm"* — came back as
        #   `create_snapshot(snapshot)`: a snapshot OF the snapshot. The manifest says what one
        #   is made from (`snapshot.create_args = {"vm": "name"}`) and `Board.makeable` already
        #   computes it; nothing read either, so the wrong target was perfectly legal.
        #
        #   ⇒⇒ **THE MODEL WAS ASKED WHY, 2026-08-11, AND IT PAIRED BY SPELLING.** Verbatim and
        #     identical 3/3: *"I aimed the step at 'snapshot' because it is more specific and
        #     directly related to the action being taken, whereas 'running_vms' is a collection
        #     of VMs that happen to be running."* The operator `create_snapshot` and the row
        #     `snapshot` share a name, so it matched them — and then dismissed the set the
        #     request is ABOUT. A rationalisation of a spelling collision, not a reason.
        #
        #   ⇒ **AND IT HAS NO PER-MEMBER SEMANTICS.** Asked how many snapshots
        #     `create_snapshot(running_vms)` makes over four running vms, it answered **5**,
        #     three times out of three — not 4, not 1. There is no FOR in its head, so no
        #     wording can teach it one.
        #
        #   ⇒⇒ **BUT ASKED TO CHOOSE BETWEEN THE TWO STEPS IT PICKS CORRECTLY 3/3.** So the fix
        #     does not need that gap repaired: REMOVE THE ILLEGAL TARGET and the only option
        #     left is the right one. Subtractive — the one move measured to work here.
        made = _made_kind(step.operator, board)
        if made:
            sources = _creation_sources(made, board)
            if sources and row.kind not in sources:
                out.append(Illegal(step, "wrong-creation-source",
                                   f"a {made} is made from a {' or a '.join(sources)}, and "
                                   f"{step.on!r} is a {row.kind} — aim it at what it is made "
                                   f"FROM"))
                continue

        # ⇒ AN UNSETTLED KIND IS **GATE 2's QUESTION** AND THIS GATE STAYS OUT OF IT.
        #   `kind-not-settled` and this rule were the same fact reported twice: on rung 9 the
        #   one fact *nothing says what n1 is* came back FIVE times, three from gate 2 and two
        #   from here. A gate that re-derives another gate's finding is not adding a check, it
        #   is adding noise — and it is how a check ends up owned by nobody.
        if row.object_type == S.UNKNOWN_KIND:
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
            # ⇒⇒ **"A CREATOR HAS NO VALUE CONTRACT" IS TRUE OF `create` AND FALSE OF `clone`.**
            #
            #   `creators.clone` declares BOTH `key: new_name` AND `from: source_name` — two
            #   arguments, a product and a source. Skipping every creator here let rung 10 serve
            #   `clone_vm(golden)` with ONE argument: golden cloned into nothing, while
            #   `create_vm(vms)` separately made three FRESH machines that are copies of nothing.
            #   *"clone golden into 3 new vms"* asks for the new machines to BE copies, and the
            #   served program silently dropped that.
            #
            #   ⇒ **AND IT WAS HIDDEN BEHIND A RIGHT-ANSWER-WRONG-REASON ASK.** Until the source
            #     role was read, rung 10 asked *"you asked to create golden and there is already
            #     one"* — a false premise that happened to stop a human before the bad program
            #     ran. Fixing the premise removed the accidental guard and exposed this, which is
            #     [[gorgon-be-stricter]] exactly: **a correct verdict for a wrong reason survives
            #     every check that only looks at verdicts.**
            #
            #   ⇒ READ OFF THE MANIFEST, so a creator that gains a `from` gains this for free.
            made = _creator_spec(step.operator)
            if made and made.get("key") and made.get("from") and step.value in (None, ""):
                out.append(Illegal(step, "incomplete-creation",
                                   f"{step.operator!r} makes one thing FROM another — it needs "
                                   f"both, and only {step.on!r} was given. What is it "
                                   f"{'copied' if made.get('records') else 'built'} into?"))
            # ⇒⇒ **AND A SOURCING CREATOR'S VALUE IS A REFERENCE, SO IT MUST RESOLVE.**
            #   Rung 10 served `clone_vm(vms, 'from_template_vm')` — an OPERATOR NAME sitting in
            #   the source slot, cloning from a thing that is not a thing. Nothing objected,
            #   because `_setter_for` finds no setter for a creator and the walk `continue`d
            #   before rule 5 ever ran. The same *"a creator has no value contract"* assumption
            #   that hid `incomplete-creation` two hours earlier, in the same branch.
            #   ⇒ D1 IS UNCHANGED BY WHO IS ASKING: a reference resolves or it is an error, and
            #     a clone's source is as much a reference as a network's is.
            if (made and made.get("from") and step.value not in (None, "")
                    and str(step.value) not in by_handle):
                out.append(Illegal(step, "value-not-declared",
                                   f"{step.operator!r} copies from {step.value!r}, and nothing "
                                   f"declares one — a source must be a thing that exists"))
            continue                       # otherwise: a probe or a delete — no value contract

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
    # ⇒⇒ **COUNT THE STEPS THAT HAVE A FINDING, NOT THE FINDINGS.** This read
    #   `len(check(...)) == len(operations)`, which silently assumed ONE finding per step.
    #   `unestablished-referent` can raise TWO for one step — its target and its value — so on
    #   2026-08-11 rung 9's mesh produced 12 findings over 4 steps and a genuine refusal
    #   reported False. Fragile before that rule existed; wrong after it.
    bad = check(operations, table, board, world)
    return len({id(i.step) for i in bad}) == len(operations)
