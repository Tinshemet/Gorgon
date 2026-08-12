"""THE WHOLE CHAIN, IN ONE PLACE — request in, declarations · operations · a verdict out.

    PYTHONPATH=. python3 -m tests.bench.twopass.pipeline
    PYTHONPATH=. python3 -m tests.bench.twopass.pipeline --only 11

# ⇒⇒ WHY THIS FILE IS THE ITEM AND NOT A CONVENIENCE

Six pieces were built and measured over two days and every one of them ran in a bench of its
own. `operations_for` had exactly ONE caller — its own `main`. `gate3.check` had none outside
its test. That is [[gorgon-built-and-never-called]], the dominant defect class in this project,
and it had just been fed four new members.

**A stage measured in isolation is a claim about a stage.** Until something runs the chain, no
number here is a claim about the system.

# ⇒ THE ORDER, AND WHAT EACH STEP IS ALLOWED TO DO

    1 pass 1        the model points at anchors; the code reads the phrases   MODEL
    2 settle        a bare name's kind, from the lab                          lookup
    3 gates 1–2     did you say it · can the world hold it · what is left over
    4 pass 2        what has to be DONE, over the confirmed symbol table      MODEL
    5 gate 3        is each operation legal
    6 effects       what the operations MAKE TRUE, from the manifest

**NO STAGE REPAIRS ANOTHER.** Findings accumulate and the verdict is taken at the end. An
early return would hide the rest of the reading, and the gates exist to report rather than to
fix ([[gorgon-gates-check-legality]]).

# ⇒⇒ THE ROUTING, AND IT IS DECIDED BY A MEASUREMENT RATHER THAN A PREFERENCE

Rung 9 — *"make sure n1, n2 and n3 can all ping each other"* — comes back with every operation
illegal under BOTH conditions, but for two different reasons:

    with an empty lab    every step   unknown-kind          THE OPERATOR CAN ANSWER THIS
    with a lab that      every step   value-is-an-object    NOBODY CAN — you cannot label a
    knows n1, n2, n3                                        machine WITH a machine

⇒ **SO A REFUSAL IS ONLY A REFUSAL WHEN IT IS NOT ANSWERABLE.** The same rung is a QUESTION
  while the kinds are unknown and a REFUSAL once they are known and it is still illegal. That
  falls straight out of gate 3's rule names; nothing had to be invented for it.

And the rest of the order follows from what each audience costs:

    REFUSE   nothing legal remains and no answer would change that
    BOUNCE   the request BINDS the words and the reading missed them — cheap, and it is the
             model's own miss, so try it before spending the operator's attention
    ASK      the request genuinely does not settle it — the operator's turn
    SERVE    nothing to report

⚠ MODEL-SPECIFIC TUNING LIVES UPSTREAM OF THIS FILE — see two-pass-rules.md §4b.
  Everything measured here was measured on llama3.1:8b. A different model needs the
  knobs re-measured, or `--order alpha` and its own unfitted ceiling.
"""
import argparse
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
from . import gate3, gate4, gates12, linguistics, pass1, pass2, repair, schema as S
from .effects import Operation, conditions_after, flatten

SERVE, BOUNCE, ASK, REFUSE = "SERVE", "BOUNCE", "ASK", "REFUSE"

# ⇒⇒ **GATE 3 HAS NO OPERATOR-ANSWERABLE RULE, AND HAS NOT SINCE `unknown-kind` MOVED.**
#
#   This held `{"unknown-kind"}` — and gate 3 stopped owning that rule when the unsettled kind
#   became GATE 2's question. So the set matched nothing, and the escape hatch it exists for —
#   *every step is illegal, but the operator could answer one of them, so this is a QUESTION
#   rather than a refusal* — has been dead code. Found 2026-08-11 by the audience test, not by
#   anything failing: a REFUSE that should have been an ASK simply refused.
#
#   ⇒ **IT IS EMPTY RATHER THAN DELETED**, because the rule it encodes is still the right one
#     and gate 3 may own an answerable finding again. `test_every_finding_reaches_an_audience`
#     asserts the set stays a subset of what gate 3 actually owns, so this cannot silently rot
#     a second time.
#   ⇒ AND THE ANSWERABILITY THAT MATTERS NOW LIVES IN GATE 2: `kind-not-settled` and
#     `no-such-kind` both go to the operator, and `UNSETTLED_KIND` stops the retry re-asking.
ANSWERABLE: frozenset = frozenset()


class Run(NamedTuple):
    request: str
    declarations: List[S.Declared]
    table: List["pass2.Symbol"]
    operations: List[Operation]
    conditions: List[Dict[str, object]]     # what will be true once the operations have run
    asks: List[str]                         # to the OPERATOR
    bounces: List[str]                      # to the MODEL
    illegal: List[gate3.Illegal]
    suggested: List[Operation] = ()   # legal, unasked, PRUDENT — shown, never run
    linguistics: List = ()
    # ⇒ THE STATES AN ACHIEVE REQUEST ASKS TO HOLD. A scaffold carrying a goal and no steps is
    #   COMPLETE, not empty — the engine derives what closes it.
    goals: List[dict] = ()
    outcome: str = ""
    # ⇒ WHAT THE HARNESS CHANGED ON THE AUTHOR'S BEHALF. Empty on any run that needed no
    #   repair, which is most of them — and never silently non-empty: `main` prints it, so a
    #   reader always knows the program shown is not the one the author wrote.
    repairs: List = ()

    @property
    def handles(self) -> List[str]:
        return [s.handle for s in self.table]



def harvest(first, first_findings, again, again_findings):
    """Merge two rounds of an answer: UPGRADE a step, REFUSE a new one, never DROP one.

    ⇒⇒ **EXTRACTED 2026-08-13 AFTER THREE BUGS IN ONE AFTERNOON**, all of them from this being
      an inline block nobody could test without a model. It carries more judgement than any
      other piece of the retry, and it was the only piece with no test of its own.

    The three, because each names a rule below:

        1  it kept "every clean step from either round" — and AN EMPTY PROGRAM HAS ZERO FAULTS,
           so the loop could always improve its score by deleting everything. `delete_network`
           vanished with its own confirmation attached. **A dropped step takes its report with
           it**, so dropping is never a repair.
        2  it keyed steps by OPERATOR ALONE, so rung 8's `create_network(core)` and
           `create_network(dmz)` collided and one establisher was lost.
        3  (the first version) took the retry whole or not at all, so a repair arriving beside
           an invented step was binned along with it — which is what made rung 12 a coin flip.

    ⇒ THE RULE, stated once:

        a step of round one is answered by the step in the SAME SLOT of the retry — slot being
        (operator, which occurrence it is). If that answer is clean it supersedes; otherwise the
        original stands, faulty and therefore still reported. A retry step in no slot of round
        one is genuinely new, and joins only if it is clean.

      Coverage never shrinks, so "better" can never mean "emptier".

    ⇒ WHAT IS STILL AN ASSUMPTION, and it is the only one: that the k-th step of an operator in
      one round CORRESPONDS to the k-th of the other. Both rounds answer the same request from
      the same schema, so the order is stable in practice — but this is a heuristic, not a
      lookup, and it is the piece held-out prompts would actually test. Every fault the manifest
      can settle is repaired BEFORE the retry (`repair.py`) precisely so that less rides on it.
    """
    def _slots(ops):
        seen, out = {}, {}
        for op in ops:
            k = seen.get(op.operator, 0)
            seen[op.operator] = k + 1
            out[(op.operator, k)] = op
        return out

    faulty_now = {id(f.step) for f in again_findings}
    first_at, retry_at = _slots(first), _slots(again)
    merged, used = [], set()
    for slot, op in first_at.items():
        better = retry_at.get(slot)
        if better is not None and id(better) not in faulty_now:
            used.add(slot)
            merged.append(better)          # the retry repaired this one
        else:
            merged.append(op)              # stands: faulty, reported, confirmable
    for slot, op in retry_at.items():      # genuinely new, and only when clean
        if slot not in used and slot not in first_at and id(op) not in faulty_now:
            merged.append(op)
    return merged


def run(request: str, board: Optional[Board] = None, world=None, model=None,
        timeout: int = 300, retries: int = 1) -> Run:
    """The whole chain. Two model calls' worth of questions in pass 1, one in pass 2."""
    board = board or Board()

    rows = pass1.run_scanned(request, board=board, model=model, timeout=timeout)
    rows = pass1.settle_with_world(rows, world, board)
    # ⇒⇒ THE LADDER, AND THE ORDER IS THE POINT: the manifest's `nouns` settled what it could
    #   inside `run_scanned`, the LAB settled what it could on the line above, and only what
    #   NEITHER could reach gets a model call. A row nothing settles stays kindless and gate 2
    #   asks — but it now asks the RIGHT question, because the routing stage distinguishes
    #   *"nobody said what this is"* from *"this lab keeps no such thing"*.
    rows = pass1.settle_by_routing(rows, board, model=model, timeout=timeout)
    # ⇒ AND AN `except` CLAUSE JOINS THE SET IT NARROWS. It runs AFTER settling because the
    #   excluded thing is usually a bare name only the lab can identify — rung 8's `db` is a
    #   machine because the lab says so, and nothing in English does.
    rows = pass1.attach_exclusions(rows, board)
    # ⇒ AND A RECIPROCAL CLAUSE IS A PREDICATE, NOT A THING. Rung 13 declared `all ping each
    #   other` as an object; the goal reads it directly, so the row must not also exist.
    rows = pass1.consume_reciprocal(rows, board)
    # ⇒ AND WHAT A CLONE IS TAKEN FROM ALREADY EXISTS. `creators.clone` declares a `from` role;
    #   reading it stops rung 10 asking *"you asked to create golden"* about a thing nobody
    #   asked to create.
    rows = pass1.settle_sources(rows, board)
    # ⇒ AND A THING ASKED TO DO SOMETHING ONLY ONE KIND CAN DO IS THAT KIND. *"n1, n2 and n3 can
    #   all PING each other"* — `alive` is observed on `vm` and nothing else, so the request
    #   already says what n1 is. The affordance table was in the manifest the whole time.
    rows = pass1.settle_by_affordance(rows, request, board)

    early = gates12.report(rows, request, board, world)
    asks: List[str] = list(early["asks"])
    early_bounces = list(early["bounces"])

    declared = pass2.symbol_table(rows, board)

    # ⇒⇒ THE LINGUISTICS GATE RUNS BETWEEN PASS 2 AND GATE 3, AND EVERY EVALUATION GOES THROUGH
    #   IT — including each retry, from the PRISTINE table. Settling drops rows, so re-settling
    #   an already-settled table could never bring one back if a later answer needed it.
    # ⇒⇒ AN ACHIEVE REQUEST CARRIES THE STATE IT ASKS TO HOLD, NOT ONLY THE STEPS.
    #
    #   *"make sure exactly 3 vms carry the 'prod' label"* is a GOAL. Pass 1 already read the
    #   enumerator and the modifiers, so the predicate is arithmetic off an existing row — no
    #   model call. The scaffold gains a goal; MEDUSA writes whatever closes it.
    #
    #   ⇒ THE ORCHESTRATOR NEVER EMITS THE LOOP. It states the goal and gate 4 asks the world
    #     whether the goal is reachable — which is where the line between proposing and writing
    #     sits ([[gorgon-orchestrator-proposes-a-scaffold]]).
    goals = gate4.goals_of(rows, request, board)

    def _governed(ops, tbl):
        """Steps the GOAL replaces — the ones over the row it governs.

        ⇒⇒ **A GOAL DOES NOT SIT BESIDE THE STEPS, IT STANDS IN FOR THEM.** Capturing the goal
          and leaving pass 2's attempt in place gave rung 14 both — and the attempt was
          `delete_vm(vms) · probe_alive(vms) · delete_vm(vms)`, i.e. DELETE EVERY MACHINE for
          *"make sure there are exactly two machines left"*. That is the oscillation
          `planner.ir.derive` was written to replace (*6 -> 4 -> 7 -> 5, it never computed
          six exist, three wanted, remove three*), and serving it alongside the goal would be
          shipping the very thing the goal exists to avoid.

        ⇒ **THE GOAL GOVERNS ONE ROW, SO IT REPLACES ONLY THAT ROW'S STEPS.** Rungs 4 and 13
          capture no goal, so nothing of theirs is dropped; a request that is part DO and part
          ACHIEVE keeps its DO steps.
        """
        # ⇒⇒ **ONLY A `count` GOAL REPLACES STEPS.** A count goal is about a QUANTITY, so any
        #   step changing that quantity is an attempt to close it — which is why rung 14's
        #   `delete_vm(vms)` must go. A `reach` goal is about a RELATION, and rungs 4/13's
        #   steps (`create 5 vms`, `give them the fleet label`, `put them in a network`) are
        #   explicitly ASKED-FOR DO clauses that happen to touch the same row. Dropping them
        #   would delete the request's own instructions and serve an empty scaffold.
        #   ⇒ THE GOAL REPLACES WHAT ATTEMPTS IT, NOT EVERYTHING THAT TOUCHES ITS SUBJECT.
        counted = [g for g in goals if g.get("shape") == "count"]
        if not counted:
            return list(ops), []
        by_handle = {sym.handle: sym.row for sym in tbl}
        owned = {sym.handle for sym in tbl
                 if any(S.governs(goal, sym.row) for goal in counted)}
        kept = [o for o in ops if str(o.on) not in owned]
        return kept, [o for o in ops if str(o.on) in owned]

    def evaluate(ops):
        settled_rows, settled_table, notes = linguistics.report(
            request, rows, ops, declared, board, goals=goals)
        # ⇒⇒ **THE VERB SETTLE REBUILDS ROWS AND DROPS THE SOURCE READING, SO IT IS RE-APPLIED.**
        #   Traced 2026-08-11: the first pass had `golden` EXISTING and the RETRY had it NEW
        #   again — `settle_with_verb` reconstructs rows, and `settle_sources`' correction went
        #   with them. `normalise_creator_args` then silently no-opped, because its swap needs
        #   one NEW row and one EXISTING one.
        #   ⇒ **A CORRECTION APPLIED ON ONE PATH AND LOST ON ANOTHER** — the same defect as
        #     `completeness` after the retry loop and the guard on one of two gate 3 loops.
        #     Applying it where EVERY evaluation passes is what makes it hold.
        #   ⇒ AND THE HANDLES ARE PRESERVED RATHER THAN REBUILT: `symbol_table` renumbers on
        #     collision, so regenerating here could rename a handle the operations point at.
        fixed = pass1.settle_sources(settled_rows, board)
        by_name = {r.name: r for r in fixed}
        settled_table = [s._replace(row=by_name.get(s.row.name, s.row)) for s in settled_table]
        # ⇒⇒ THE DUPLICATE CHECK RUNS HERE, INSIDE EVERY EVALUATION, SO THE RETRY CAN SEE IT.
        #   Computed after the loop it was a report to nobody — the identical defect
        #   `uncreated-declaration` had this morning, and the twelfth instance today of a
        #   finding that is correct and unreachable. The model already knows a clone creates
        #   (probed 3/3); it only needs telling that it counted the creation twice.
        dups = gate4.duplicate_creations(ops, settled_table, board)
        return (fixed, settled_table, notes,
                gate3.check(ops, settled_table, board, world), dups)

    operations = pass2.operations_for(request, rows, board, model=model, timeout=timeout)
    # ⇒⇒ R2 — A THING DEPENDED ON AND NEVER BROUGHT ABOUT IS SUPPLIED BY ARITHMETIC, NOT ASKED
    #   FOR AGAIN. It runs BEFORE `evaluate`, so gate 3 and the linguistics gate judge the
    #   COMPLETED program: a step that only exists because the manifest requires it is still a
    #   step, and hiding it from the gates would be exempting it from the rules.
    #   ⇒ NO MODEL CALL. The determiner said NEW and the manifest says how a network is made.
    operations = pass2.derive_creators(operations, pass2.symbol_table(rows, board), board)
    # ⇒ AND THE ORDER IS ARITHMETIC TOO. An establisher that runs after its dependent has not
    #   run at all; which step precedes which is a fact about the table, not a judgement.
    # ⇒ A CREATION THE MODEL SPLIT IN TWO IS REJOINED FIRST — the clone's product became its
    #   own step because the sentence wraps back on itself. Before the other assembly steps,
    #   so they see one operation rather than two halves.
    operations = pass2.merge_split_creation(
        operations, pass2.symbol_table(rows, board), request, board)
    operations = pass2.normalise_creator_args(operations, pass2.symbol_table(rows, board), board)
    # ⇒ AND A ROW MADE TWICE KEEPS THE MAKER THE REQUEST NAMES. The model was told three ways
    #   and would not drop the spare, and a caught error it will not act on is ours to fix.
    operations = pass2.drop_redundant_creators(
        operations, pass2.symbol_table(rows, board), request, board)
    operations = pass2.order_by_dependency(operations, pass2.symbol_table(rows, board), board)
    rows, table, ling, illegal, dups = evaluate(operations)

    # ⇒⇒ **REPAIR BEFORE ASKING — compute the fix where the manifest determines it.**
    #
    #   Gate 3's objection on rung 12 NAMES ITS OWN REMEDY: *"a snapshot is made from a vm …
    #   aim it at what it is made FROM"*, and `Board.makeable` computes the one legal target
    #   from `create_args`. Until now we spent a model call asking that, and then judged the
    #   reply on a rule that could discard it — so a rung whose fix was already derivable
    #   turned on whether the model felt like inventing an extra step.
    #
    #   ⇒ IT RUNS BEFORE THE RETRY, so a determinable fault never reaches the model at all;
    #     that is the whole point of the ordering (compute first, ask only when you cannot).
    #   ⇒ AND THE RESULT IS RE-EVALUATED, never assumed correct — a repair is a change to the
    #     program and gets judged like any other.
    repaired: List[repair.Repaired] = []
    operations, repaired = repair.repair(operations, illegal, table, board)
    if repaired:
        rows, table, ling, illegal, dups = evaluate(operations)

    # ⇒⇒ THE RETRY. A BOUNCE MEANS THE MODEL'S OWN MISS, SO THE MODEL GETS ANOTHER GO.
    #
    #   It is handed the steps that were rejected and the manifest's reason for each — evidence
    #   it did not have, not instruction about how to behave. The base question is byte-identical
    #   on the first attempt, so **a request that succeeds first time never sees any of this**:
    #   the retry cannot regress what already worked, by construction rather than by measurement.
    #   That matters because the last time prompt text was added to change behaviour, a bisect
    #   proved the text caused the gain AND the damage together.
    #
    #   ⇒ AND `unknown-kind` IS NOT RETRIED. Only the operator or the lab can say what `n1` is,
    #     so re-asking would be inviting the model to guess — which is the whole failure the
    #     kindless row exists to prevent.
    # ⇒ A SPURIOUS STEP IS RETRYABLE TOO, AND IT IS THE MODEL'S TO DROP. `unasked-step` says
    #   nothing in the request warrants the operation — evidence the model can act on, exactly
    #   like an illegal one. Everything the linguistics gate addresses to the OPERATOR stays
    #   out of the retry: re-asking for a mood the vocabulary cannot express is the trap.
    def _faults(bad_steps, notes):
        return ([repr(b) for b in bad_steps if b.rule not in ANSWERABLE]
                + [repr(n) for n in notes if n.audience == "model"])

    # ⇒⇒ A FINDING THAT ASKS FOR A STEP TO BE **ADDED** CANNOT TRAVEL IN THE REJECTION LIST.
    #
    #   Measured on rung 8: `core` and `dmz` are both used and neither supplied. Both were
    #   reported, and the retry added `create_network(core)` and never `dmz` — identical at
    #   `--retries 1`, `2` and `3`. The missing step was being handed over under a heading that
    #   reads *"cannot be used"*, i.e. the opposite instruction.
    #
    #   ⇒ THE SPLIT IS BY WHAT THE FINDING ASKS FOR, not by which gate raised it. `wants_a_step`
    #     goes to the payload's `needed` section; everything else stays a rejection.
    WANTS_A_STEP = frozenset({"unestablished-referent"})

    def _split(bad_steps, notes, dups=()):
        add = [repr(b) for b in bad_steps if b.rule in WANTS_A_STEP]
        drop = ([repr(b) for b in bad_steps
                 if b.rule not in ANSWERABLE and b.rule not in WANTS_A_STEP]
                + [repr(n) for n in notes if n.audience == "model"]
                # a duplicate asks for a step to be REMOVED, so it travels as a rejection
                + list(dups or ()))
        return drop, add

    rejected: List[str] = []
    needed: List[str] = []
    for _round in range(max(0, retries)):
        # ⇒ NOT WHILE SOMETHING THE OPERATOR MUST ANSWER IS STILL OPEN. Rung 9's `add_label` is
        #   genuinely unwarranted and genuinely retryable — but what BLOCKS that rung is *what
        #   is n1?*, and no answer the model gives can settle it. Retrying here spends a call
        #   to invite the guess the kindless row exists to prevent.
        # ⇒ GATE 2 OWNS THE UNSETTLED KIND NOW, so the guard reads gate 2's findings
        #   rather than a duplicate gate 3 was emitting. Same rule, one owner.
        if any(f.kind in gates12.UNSETTLED_KIND for f in early['findings']):
            break
        retryable = _faults(illegal, ling) + list(dups)
        if not retryable or not operations:
            break
        drop_now, add_now = _split(illegal, ling, dups)
        rejected = sorted(set(drop_now) | set(rejected))
        needed = sorted(set(add_now) | set(needed))
        again = pass2.operations_for(request, rows, board, model=model, timeout=timeout,
                                     rejected=rejected, needed=needed)
        if not again:
            break
        # ⇒⇒ THE RETRY GETS THE SAME TREATMENT AS THE FIRST PASS, AND IT DID NOT UNTIL NOW.
        #   `derive_creators` and `order_by_dependency` ran only on the first answer, so a
        #   retry's output was judged against rules its own steps had never been put through —
        #   which is how rung 8 came back with `create_network(dmz)` sitting AFTER the step
        #   that needs it. Two paths to the same gates must be prepared the same way.
        _tbl = pass2.symbol_table(rows, board)
        again = pass2.merge_split_creation(again, _tbl, request, board)
        again = pass2.order_by_dependency(
            pass2.drop_redundant_creators(
                pass2.normalise_creator_args(
                    pass2.derive_creators(again, _tbl, board), _tbl, board),
                _tbl, request, board), _tbl, board)
        fresh_rows, fresh_table, fresh_ling, fresh, fresh_dups = evaluate(again)
        # ⇒⇒ **THE RETRY'S ANSWER IS REPAIRED TOO, AND IT WAS NOT UNTIL THE REVIEW OF 08-13.**
        #
        #   `repair` ran once, on the first answer, before this loop — so a `wrong-creation-source`
        #   in a RETRY reached the model instead of the manifest that could settle it. **A rule
        #   placed on one of two paths**, which is the defect class this project has now recorded
        #   fourteen times, added by me hours after writing that sentence down. The two paths must
        #   be prepared the same way, exactly as the note above `merge_split_creation` says.
        again, more = repair.repair(again, fresh, fresh_table, board)
        if more:
            repaired.extend(more)
            fresh_rows, fresh_table, fresh_ling, fresh, fresh_dups = evaluate(again)
        # ⇒⇒ **HARVEST THE CLEAN STEPS FROM BOTH ROUNDS — DO NOT CHOOSE BETWEEN THE ANSWERS.**
        #
        #   This compared TOTAL fault counts and kept whichever answer scored better, whole.
        #   Measured on rung 12 (2026-08-13), and it is why that rung read SERVE on 08-11 and
        #   REFUSE today with nothing in between changing:
        #
        #       first   wrong-creation-source(create_snapshot) · value-missing(add_vm_to_network)
        #       retry   unestablished-referent(add_label)      · wrong-kind-operator(add_label)
        #
        #   **The retry REPAIRED the thing we objected to** — `create_snapshot(snapshot)` became
        #   `create_snapshot(running_vms)` and drew no finding at all. It also invented a junk
        #   step, which drew two. Two against two, `>=` fired, and the whole answer went in the
        #   bin TAKING THE REPAIR WITH IT — leaving the original wrong step to be refused.
        #
        #   ⇒ SO THE RUNG WAS NEVER SOLIDLY SERVED. It served whenever the model happened not to
        #     bolt an extra step onto its second try, and refused when it did. A coin the model
        #     flips, recorded as a result on a day it landed heads.
        #
        # ⇒ THE RULE: a step gate 3 found NO fault with is kept, whichever round produced it;
        #   everything else is dropped. That is [[gorgon-detector-not-producer-again]]'s harvest
        #   applied to the repair loop — a spurious step becomes unrepresentable rather than
        #   fatal, so whether the model adds one no longer decides the verdict.
        # ⇒⇒ **THE HARVEST MAY UPGRADE A STEP OR REFUSE A NEW ONE. IT MAY NEVER DROP ONE.**
        #
        #   The first version of this kept "every clean step from either round" — and an EMPTY
        #   PROGRAM HAS ZERO FAULTS, so the loop could always improve its score by deleting
        #   everything. Caught by the destruction guard, which is the right test to catch it:
        #   `delete_network(dmz)` was dropped as faulty and came out
        #
        #       ops []   illegal []   asks []   ->  a destructive step SILENTLY GONE
        #
        #   ⇒ **A DROPPED STEP TAKES ITS FINDING WITH IT**, because findings are computed from
        #     the operations. So dropping is not a quiet repair, it is the deletion of a report
        #     — and for a destructive step it is the deletion of a confirmation. The wholesale
        #     rule this replaced was accidentally guarding against exactly that.
        #
        #   ⇒ SO THE RULE IS ONE-WAY: a first-round step is replaced only by a CLEAN retry step
        #     answering the same operator, and otherwise stands — faulty, reported, confirmable.
        #     A retry step that answers nothing already present is added only if it is clean.
        #     Coverage never shrinks, so "better" can never mean "emptier".
        # ⇒ STEPS PAIR BY OPERATOR **AND OCCURRENCE**, never by operator alone. Keying on the
        #   operator collapsed rung 8: it needs `create_network(core)` AND `create_network(dmz)`,
        #   and one key held both, so the second establisher was dropped and the rung refused
        #   for want of a network the retry had actually supplied. The k-th `create_network` of
        #   one round answers the k-th of the other; anything past that is genuinely new.
        merged = harvest(operations, illegal, again, fresh)
        merged = pass2.order_by_dependency(merged, _tbl, board)
        # ⇒ AND THE MERGE IS RE-JUDGED, NEVER ASSUMED. A step clean on its own can be faulty
        #   beside another — an establisher's ordering is a property of the SET. Harvesting
        #   without re-evaluating would be the same trust the wholesale rule at least refused.
        merged_rows, merged_table, merged_ling, merged_ill, merged_dups = evaluate(merged)
        if (len(_faults(merged_ill, merged_ling)) + len(merged_dups)
                >= len(_faults(illegal, ling)) + len(dups)):
            break                              # no progress — keep what we had
        operations, rows, table, ling, illegal, dups = (
            merged, merged_rows, merged_table, merged_ling, merged_ill, merged_dups)
    # ⇒⇒ A WORD MAY BE ACCOUNTED FOR BY AN OPERATION, NOT ONLY BY A DECLARATION.
    #
    #   Gate 1's leftover rule was written when declarations were all there was, so it asks
    #   which words no DECLARATION claimed. *"give them all the 'fleet' label"* is not a thing
    #   — it is something pass 2 DOES — and once `all the 'fleet' label` stopped being declared
    #   as a bogus object, gate 1 started bouncing `'fleet'` as unread. It is read perfectly
    #   well, by `add_label(vms, 'fleet')`.
    #
    #   ⇒ **THIS IS THE FIRST CHECK THAT SPANS BOTH PASSES**, and it is only possible now that
    #     both artifacts exist. Absence becomes a comparison across the pair rather than within
    #     one of them.
    # ⇒⇒ AN UNASKED STEP IS NOT NOISE. IT IS HOUSEKEEPING, AND WE HAD BEEN THROWING IT AWAY.
    #
    #   Asked to justify its own invented steps, the model quoted NO words of the request — and
    #   then gave a reason that was sound every time:
    #
    #       probe_alive     "to check if any of the stopped VMs are now running"
    #       create_snapshot "to ensure I have a snapshot before making changes"
    #       add_label       "to assign a label for identification purposes"
    #
    #   Six of the nine invented steps are *check it worked*, one is *snapshot before changing*,
    #   one is *label it so it can be found*. Those are OPS INSTINCTS applied unasked, not
    #   misreadings — which is exactly why telling the model a step was rejected changed
    #   nothing, byte for byte: from its side the step was never a mistake.
    #
    #   ⇒ **SO THE SPLIT IS THREE-WAY, NOT TWO.** What the request asked for is the PROGRAM.
    #     What it did not ask for, and is legal and harmless, is a SUGGESTION — shown, never
    #     run. What is illegal or destructive stays a finding, because a helpful instinct that
    #     deletes machines is not helpful.
    from .linguistics import anchor_to_clauses
    asked_now, suggested = [], []
    destroyers = gate4._destroyers(board)
    for clause, op in anchor_to_clauses(request, list(operations), board):
        if clause or op.operator in destroyers:
            asked_now.append(op)          # a destructive step is never quietly "suggested"
        else:
            suggested.append(op)
    operations = asked_now

    # ⇒ A BAD SUGGESTION IS DROPPED, NEVER HELD AGAINST THE PROGRAM. Gate 3 had judged the
    #   whole list, so rung 12's illegal `add_vm_to_network(running_vms)` — now merely a
    #   suggestion — made every operation look illegal and turned a servable request into a
    #   REFUSE. An offer we cannot stand behind is simply not offered.
    suggested = [op for op in suggested
                 if not gate3.check([op], table, board, world)]

    # ⇒⇒ A BAD SUGGESTION NEVER COSTS THE PROGRAM ITS VERDICT.
    #
    #   The operator, 2026-08-10: *"a cancerous housekeeping should be dropped but the core
    #   proposal shipped — we don't drop a whole proposal only because of a bad housekeeping
    #   solution."* Right, and it has to be STRUCTURAL rather than hoped for: an illegal
    #   suggestion once made every operation look illegal and turned a servable rung 12 into a
    #   REFUSE. So the tiers are sorted here, the CANCEROUS ones are purged outright, and
    #   `illegal` is recomputed over the PROGRAM ALONE — the verdict cannot see the offers.
    from .housekeeping import CANCEROUS, GOOD, RISKY, sort_out
    tiers = sort_out(suggested, operations, table, board)
    purged = [v.op for v in tiers[CANCEROUS]]
    suggested = [v.op for v in tiers[GOOD] + tiers[RISKY]]
    # ⇒⇒ THE GOAL STANDS IN FOR THE STEPS IT GOVERNS — see `_governed`. This happens AFTER the
    #   housekeeping tiering so a suggestion is judged on the program as pass 2 wrote it, and
    #   BEFORE gate 3 and gate 4 so neither reports on steps that are no longer proposed.
    #   A `delete_vm` that the goal replaced must not raise a destructive confirmation: the
    #   scaffold is not asking to delete anything, it is asking for a count to hold.
    operations, replaced = _governed(operations, table)
    illegal = gate3.check(operations, table, board, world)

    spent = {str(op.value).strip().lower() for op in operations + suggested if op.value}
    spent |= {str(op.on).strip().lower() for op in operations + suggested}
    # ⇒⇒ AND A WORD CARRIED BY A ROW THE PROGRAM OPERATES ON HAS ALSO BEEN USED.
    #
    #   The same accounting, one level down, and leaving it out made rung 6 lie. `red` is
    #   quoted in the request and the residue check found it unread inside the NETWORK's span —
    #   but `red_vms {label: red}` carries it, and the program does `add_vm_to_network(red_vms,
    #   …)`. The word is accounted for by a REFERENCE to that row.
    #
    #   ⇒ AND THE COST OF MISSING IT WAS NOT NOISE, IT WAS MISDIRECTION. Rung 6's genuine
    #     finding — a second network declared and never used — sat underneath two spurious
    #     complaints telling the model to go re-read `'red'` and `'blue'`, which it had read
    #     correctly. The true fault was the one the reader would reach last.
    by_handle = {sym.handle: sym.row for sym in table}
    carried = set()
    for op in operations:
        row = by_handle.get(str(op.on))
        if row is not None:
            carried |= {str(v).strip().lower() for v in (row.where or {}).values()}

    bounces: List[str] = []
    for finding in early_bounces:
        if finding.kind == "left-over":
            unclaimed = [w.strip(" '\"") for w in str(finding.about).split(",")
                         if w.strip(" '\"").lower() not in spent]
            if not unclaimed:
                continue          # every leftover word is an operation's argument
        if finding.kind == "unread-value" and str(finding.about).strip().lower() in carried:
            continue              # a condition of a row the program acts on — already used
        bounces.append(finding.says)

    # ⇒ THE LINGUISTICS FINDINGS CARRY THEIR OWN AUDIENCE. A mood or an exclusion the
    #   vocabulary cannot express is the OPERATOR's — re-asking the model for something
    #   unsayable is the trap three refusal attempts already walked into.
    for note in ling:
        if note.rule == "unasked-step":
            continue      # ⇒ it is a SUGGESTION now, carried on the Run rather than complained about
        (asks if note.audience == "operator" else bounces).append(repr(note))
    for bad in illegal:
        (asks if bad.rule in ANSWERABLE else bounces).append(repr(bad))
    asks += gate4.confirmations(operations, table, request, board)
    # ⇒ AND A SET WHOSE EXCLUSION THE ENGINE COULD NOT EXPRESS IS NOT VIABLE. The declaration
    #   is only worth making if something downstream can honour it; asked of the IR's own
    #   validator so this cannot drift from what the engine actually accepts.
    bounces += gate4.unhonourable_exclusions(table, board)
    # ⇒ AND A ROW MADE TWICE IS THE SCAFFOLD CONTRADICTING ITSELF. The model's miss — the
    #   request names one creator — so it bounces and the retry drops the spare.
    bounces += list(dups)
    # ⇒ AND A GOAL NOTHING COULD CLOSE IS THE OPERATOR'S TO HEAR. `derive` answers in three
    #   values — already true, reachable, or nothing-can — and only the third is a question.
    asks += gate4.unreachable_goals(goals, world, board)
    # ⇒ AND A GOAL THAT CLOSES BY REMOVING THINGS IS CONFIRMED, exactly as a destructive STEP
    #   is. The goal replacing the steps must not also replace the guard over them.
    asks += gate4.destructive_goals(goals, world, board)
    # ⇒ GATE 1's OTHER HALF, which needs both artifacts: nothing declared may go unused.
    bounces += [f.says for f in gates12.completeness(rows, operations, table, board,
                                                    goals=goals)]

    declared = {row.name: dict(row.where) for row in rows}
    conditions = flatten(conditions_after(declared, _aimed(operations, table), board))

    return Run(request, rows, table, operations, conditions,
               asks, bounces, illegal, suggested, ling, list(goals),
               _verdict(operations, illegal, asks, bounces, goals), list(repaired))


def _aimed(operations: List[Operation], table) -> List[Operation]:
    """Point each operation at the ROW its handle addresses.

    `conditions_after` is keyed by the declaration's name and pass 2 speaks in handles, so
    without this the effects land on nothing and the conditions come back short — silently,
    which is the failure mode worth naming. The handle IS the address; this is where it is
    dereferenced.
    """
    by_handle = {sym.handle: sym.row.name for sym in table}
    return [Operation(op.operator, by_handle.get(op.on, op.on), op.value)
            for op in operations]


def _verdict(operations: List[Operation], illegal: List[gate3.Illegal],
             asks: List[str], bounces: List[str], goals: List[dict] = ()) -> str:
    """REFUSE > BOUNCE > ASK > SERVE — and see the module note for why that order."""
    if operations and len(illegal) == len(operations):
        # ⇒ EVERY step illegal. If ANY of them is a question the operator could answer, this
        #   is not a refusal yet — it is a request for the missing fact. Rung 9 is exactly
        #   this case, and it changes verdict when a lab is attached.
        if not any(bad.rule in ANSWERABLE for bad in illegal):
            return REFUSE
    # ⇒⇒ A SCAFFOLD WITH A GOAL AND NO STEPS IS NOT EMPTY. *"make sure there are exactly two
    #   machines left"* proposes a STATE; the steps that close it are the engine's to write, so
    #   an empty operation list is the correct shape rather than a failure to produce one.
    # ⇒⇒ **AND AN EMPTY PROGRAM WITH OPEN QUESTIONS IS AN ASK, NOT A REFUSAL.** REFUSE is
    #   defined at the top of this file as *nothing legal remains AND NO ANSWER WOULD CHANGE
    #   THAT*. The branch above already honours it — *"if ANY of them is a question the operator
    #   could answer, this is not a refusal yet"* — and this branch never did.
    #
    #   Measured 2026-08-11: rung 9 came back with no operations at all (pass 2 emitted none)
    #   and three open questions — *what is `n1`?* — and was REFUSED 3/3. An answer to any one
    #   of them changes the whole reading, which is the definition of not-a-refusal.
    #   ⇒ THE SAME RULE, WRITTEN IN TWO PLACES, AGREEING IN ONE OF THEM. Ninth time today.
    if not operations and not goals and not asks:
        return REFUSE
    if bounces:
        return BOUNCE
    if asks:
        return ASK
    return SERVE


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--retries", type=int, default=1,
                    help="how many times a BOUNCE is handed back to the model")
    ap.add_argument("--no-lab", action="store_true",
                    help="run with no world at all — every bare name stays kindless")
    args = ap.parse_args()

    from .metrics import Lab
    board = Board()
    world = None if args.no_lab else Lab()
    tally: Dict[str, int] = {}

    print("=" * 100)
    print(f"THE WHOLE CHAIN{'  ·  NO LAB' if args.no_lab else '  ·  with a lab'}")
    print("=" * 100)

    for n, want in sorted(pass1.EXPECTED.items()):
        if args.only and n != args.only:
            continue
        got = run(want.request, board=board, world=world, model=args.model,
                  retries=args.retries)
        tally[got.outcome] = tally.get(got.outcome, 0) + 1
        print(f"\n{'─' * 100}\nrung {n} · “{want.request[:74]}”")
        print(f"    declared   {', '.join(got.handles) or '—'}")
        print(f"    operations {[(o.operator, o.on, o.value) for o in got.operations] or '—'}")
        for r in got.repairs:
            print(f"      REPAIRED {r}")
        if got.suggested:
            print(f"    SUGGESTED  {[(o.operator, o.on, o.value) for o in got.suggested]}")
        print(f"    conditions {got.conditions or '—'}")
        for a in got.asks:
            print(f"      ASK     {a[:92]}")
        for b in got.bounces:
            print(f"      BOUNCE  {b[:92]}")
        print(f"    ⇒ {got.outcome}")

    print(f"\n{'=' * 100}")
    for outcome in (SERVE, BOUNCE, ASK, REFUSE):
        if tally.get(outcome):
            print(f"    {outcome:<8} {tally[outcome]}")


if __name__ == "__main__":
    main()
