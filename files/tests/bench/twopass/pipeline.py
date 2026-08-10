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
from . import gate3, gate4, gates12, linguistics, pass1, pass2, schema as S
from .effects import Operation, conditions_after, flatten

SERVE, BOUNCE, ASK, REFUSE = "SERVE", "BOUNCE", "ASK", "REFUSE"

# ⇒ THE ONE RULE OF GATE 3 THE OPERATOR CAN ANSWER. Everything else is a statement about the
#   operation itself and no answer changes it.
ANSWERABLE = frozenset({"unknown-kind"})


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
    outcome: str = ""

    @property
    def handles(self) -> List[str]:
        return [s.handle for s in self.table]


def run(request: str, board: Optional[Board] = None, world=None, model=None,
        timeout: int = 300, retries: int = 1) -> Run:
    """The whole chain. Two model calls' worth of questions in pass 1, one in pass 2."""
    board = board or Board()

    rows = pass1.run_scanned(request, board=board, model=model, timeout=timeout)
    rows = pass1.settle_with_world(rows, world, board)

    early = gates12.report(rows, request, board, world)
    asks: List[str] = list(early["asks"])
    early_bounces = list(early["bounces"])

    declared = pass2.symbol_table(rows, board)

    # ⇒⇒ THE LINGUISTICS GATE RUNS BETWEEN PASS 2 AND GATE 3, AND EVERY EVALUATION GOES THROUGH
    #   IT — including each retry, from the PRISTINE table. Settling drops rows, so re-settling
    #   an already-settled table could never bring one back if a later answer needed it.
    def evaluate(ops):
        settled_rows, settled_table, notes = linguistics.report(
            request, rows, ops, declared, board)
        return settled_rows, settled_table, notes, gate3.check(ops, settled_table, board, world)

    operations = pass2.operations_for(request, rows, board, model=model, timeout=timeout)
    rows, table, ling, illegal = evaluate(operations)

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

    rejected: List[str] = []
    for _round in range(max(0, retries)):
        # ⇒ NOT WHILE SOMETHING THE OPERATOR MUST ANSWER IS STILL OPEN. Rung 9's `add_label` is
        #   genuinely unwarranted and genuinely retryable — but what BLOCKS that rung is *what
        #   is n1?*, and no answer the model gives can settle it. Retrying here spends a call
        #   to invite the guess the kindless row exists to prevent.
        # ⇒ GATE 2 OWNS THE UNSETTLED KIND NOW, so the guard reads gate 2's findings
        #   rather than a duplicate gate 3 was emitting. Same rule, one owner.
        if any(f.kind == 'kind-not-settled' for f in early['findings']):
            break
        retryable = _faults(illegal, ling)
        if not retryable or not operations:
            break
        rejected = sorted(set(retryable) | set(rejected))
        again = pass2.operations_for(request, rows, board, model=model, timeout=timeout,
                                     rejected=rejected)
        if not again:
            break
        fresh_rows, fresh_table, fresh_ling, fresh = evaluate(again)
        # ⇒ KEEP THE BETTER ANSWER, NEVER THE LATER ONE. A retry that produces MORE illegal
        #   steps is a regression, and taking it because it came second would be the repair
        #   loop making things worse while looking busy.
        if len(_faults(fresh, fresh_ling)) >= len(_faults(illegal, ling)):
            break
        operations, rows, table, ling, illegal = again, fresh_rows, fresh_table, fresh_ling, fresh
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
    # ⇒ GATE 1's OTHER HALF, which needs both artifacts: nothing declared may go unused.
    bounces += [f.says for f in gates12.completeness(rows, operations, table, board)]

    declared = {row.name: dict(row.where) for row in rows}
    conditions = flatten(conditions_after(declared, _aimed(operations, table), board))

    return Run(request, rows, table, operations, conditions,
               asks, bounces, illegal, suggested, ling,
               _verdict(operations, illegal, asks, bounces))


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
             asks: List[str], bounces: List[str]) -> str:
    """REFUSE > BOUNCE > ASK > SERVE — and see the module note for why that order."""
    if operations and len(illegal) == len(operations):
        # ⇒ EVERY step illegal. If ANY of them is a question the operator could answer, this
        #   is not a refusal yet — it is a request for the missing fact. Rung 9 is exactly
        #   this case, and it changes verdict when a lab is attached.
        if not any(bad.rule in ANSWERABLE for bad in illegal):
            return REFUSE
    if not operations:
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
