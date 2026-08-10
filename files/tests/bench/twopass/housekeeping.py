"""HOUSEKEEPING — the steps the model proposes that nobody asked for, sorted into four tiers.

    PYTHONPATH=. python3 -m tests.bench.twopass.housekeeping          # the sealed test
    PYTHONPATH=. python3 -m tests.bench.twopass.housekeeping --model qwen2.5:14b --compare

# ⇒⇒ WHY THESE ARE KEPT AT ALL

Asked to justify its own unasked steps, the model quoted no words of the request — and gave a
sound reason every time: *"to check if any of the stopped VMs are now running"*, *"to ensure I
have a snapshot before making changes"*. Six of nine were **check it worked**, one **snapshot
before changing**, one **label it so it can be found**.

    The operator, 2026-08-10: *"its basically being PROACTIVE which is amazing... a better
    model might propose better as well as more housekeeping, making the medusa engine guess
    less."*

⇒ **SO PROPOSAL COUNT IS A CAPABILITY SIGNAL, NOT A DEFECT RATE.** Under the old framing a
  stronger model produced more noise. Under this one it produces a richer advisory tier, and
  every proposal is one thing the engine does not have to guess.

# ⇒ THE FOUR TIERS, AND EVERY TEST IS STRUCTURAL

    1 BENIGN     read-only, and it observes nothing the program changes. Harmless, no value.
    2 GOOD       the brilliant-move tier: it VERIFIES an attribute the program sets, or takes
                 a restore point of something the program is about to mutate.
    3 RISKY      it changes the world, legally and non-destructively, in a way nobody asked
                 for. NEVER compiled into the program — offered afterwards, y/n.
    4 CANCEROUS  destructive, contradicts a step of the program, or writes a meaningless
                 value. Purged.

⇒ **AND THE ORDER OF THE TESTS MATTERS**, because a step can satisfy several: destruction is
  checked before prudence, so *"delete the machines so exactly three carry the label"* cannot
  be excused as tidying up.
"""
import argparse
from typing import Dict, List, NamedTuple, Optional, Tuple

from ..formula.legal import Board
from .effects import Operation, effect_of

BENIGN, GOOD, RISKY, CANCEROUS = "benign", "good", "risky", "cancerous"

#: tiers that may be offered to the operator afterwards; RISKY is the y/n one
OFFERABLE = (GOOD, RISKY)


class Verdict(NamedTuple):
    op: Operation
    tier: str
    why: str

    def __repr__(self):
        return f"[{self.tier}] {self.op.operator}({self.op.on}): {self.why}"


def _read_only(operator: str) -> bool:
    """A probe changes nothing. That is the whole of its safety."""
    from planner.ir import config as _config
    if operator.startswith("probe_"):
        return True
    for spec in (_config.KINDS or {}).values():
        if isinstance(spec, dict) and operator == spec.get("list"):
            return True
    return False


def _destroys(operator: str) -> bool:
    from planner.ir import config as _config
    return any(isinstance(spec, dict) and operator == spec.get("delete")
               for spec in (_config.KINDS or {}).values())


def _creates_restore_point(operator: str) -> Optional[str]:
    """Does this operation produce a thing whose PURPOSE is going back? Read from the manifest.

    `snapshot`'s own doc calls a restore its telic role — *"put the machine back to this
    point"* — so a creator of that kind is a rollback, not merely another object.
    """
    from planner.ir import config as _config
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        acts = spec.get("acts") or {}
        restores = any("back" in str(meta.get("doc", "")).lower() for meta in acts.values())
        for name in (spec.get("creators") or {}):
            made = f"create_{kind}" if name == "create" else f"{name}_{kind}"
            if operator == made and restores:
                return kind
    return None


def _placeholder(op: Operation, board: Board) -> bool:
    """A value that says nothing. `add_label(vms, 'label')` writes the WORD `label`.

    ⇒ Rung 10 produced exactly that, and it is worse than useless: it puts meaningless metadata
      into the lab that somebody later has to interpret. The tell is a value equal to the
      attribute it fills, or one lifted out of the symbol table we handed over — `known at plan
      time` came back as a label once.
    """
    if not op.value:
        return False
    value = str(op.value).strip().lower()
    effect = effect_of(op.operator, board)
    attr = effect[1] if effect else None
    if attr and value == str(attr).lower():
        return True
    return any(token in value for token in ("at plan time", "at run time", "known ", "_set"))


def classify(op: Operation, program: List[Operation], table,
             board: Optional[Board] = None) -> Verdict:
    """One proposed step against the program it accompanies. No model call."""
    board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}

    # 4 · CANCEROUS — checked FIRST, so prudence cannot excuse destruction.
    if _destroys(op.operator):
        return Verdict(op, CANCEROUS,
                       "it destroys something, and nobody asked for anything to be removed")
    if _placeholder(op, board):
        return Verdict(op, CANCEROUS,
                       f"{op.value!r} says nothing — it writes meaningless metadata into the lab")

    effect = effect_of(op.operator, board)
    mine = (effect[1], effect[2]) if effect else (None, None)
    for other in program:
        got = effect_of(other.operator, board)
        if not got or str(other.on) != str(op.on):
            continue
        # the same attribute driven to a DIFFERENT fixed value is an undo
        if got[1] and got[1] == mine[0] and got[2] and mine[1] and got[2] != mine[1]:
            return Verdict(op, CANCEROUS,
                           f"it sets {mine[0]} to {mine[1]!r} on {op.on!r} while the program "
                           f"sets it to {got[2]!r} — one undoes the other")

    touched = {str(o.on) for o in program}

    # 2 · GOOD — it verifies what the program does, or protects what the program changes.
    if _read_only(op.operator):
        fact = op.operator[len("probe_"):] if op.operator.startswith("probe_") else None
        for other in program:
            got = effect_of(other.operator, board)
            if got and str(other.on) == str(op.on):
                if fact and got[1] and (fact == got[1] or fact in str(got[1])):
                    return Verdict(op, GOOD,
                                   f"it checks the very thing the program changes — "
                                   f"{other.operator} sets {got[1]} on {op.on!r}")
                return Verdict(op, GOOD,
                               f"it confirms the state of {op.on!r}, which the program alters")
        # 1 · BENIGN — reads something nothing else touches.
        return Verdict(op, BENIGN,
                       f"it only looks at {op.on!r}, which the program does not change")

    kind = _creates_restore_point(op.operator)
    if kind and str(op.on) in touched:
        return Verdict(op, GOOD,
                       f"it takes a {kind} of {op.on!r} before the program changes it — "
                       f"a way back")

    # 3 · RISKY — it changes the world, legally, and nobody asked.
    where = "something the program also touches" if str(op.on) in touched else \
            f"{op.on!r}, which the program does not otherwise touch"
    return Verdict(op, RISKY,
                   f"it changes {where} and no part of the request asks for it")


def sort_out(suggested: List[Operation], program: List[Operation], table,
             board: Optional[Board] = None) -> Dict[str, List[Verdict]]:
    """The four tiers, and what each is for.

    GOOD may be folded into the proposal. RISKY is held back and offered afterwards —
    *"the model proposed these, add them?"*. BENIGN is noted. CANCEROUS is purged.
    """
    out: Dict[str, List[Verdict]] = {BENIGN: [], GOOD: [], RISKY: [], CANCEROUS: []}
    for op in suggested:
        v = classify(op, program, table, board)
        out[v.tier].append(v)
    return out


# ── THE SEALED TEST · every step below was really produced, on the rung named ──────────
CASES: List[Tuple[str, int, Operation, List[Operation], str]] = [
    ("verifies the very attribute the program sets", 5,
     Operation("probe_alive", "stopped_vms", None),
     [Operation("launch_vm", "stopped_vms", None)], GOOD),
    ("a restore point before the program mutates it", 13,
     Operation("create_snapshot", "vms", None),
     [Operation("add_label", "vms", "fleet")], GOOD),
    ("a meaningless label value", 10,
     Operation("add_label", "vms", "label"),
     [Operation("create_vm", "vms", None)], CANCEROUS),
    ("launching machines nobody asked to launch", 4,
     Operation("launch_vm", "vms", None),
     [Operation("create_vm", "vms", None), Operation("add_label", "vms", "fleet")], RISKY),
    ("deleting to satisfy a label count", 7,
     Operation("delete_vm", "prod_vms", None),
     [Operation("add_label", "prod_vms", "prod")], CANCEROUS),
    ("undoing the program's own step", 5,
     Operation("stop_vm", "stopped_vms", None),
     [Operation("launch_vm", "stopped_vms", None)], CANCEROUS),
    ("a probe of something untouched", 4,
     Operation("probe_exists", "network", None),
     [Operation("create_vm", "vms", None)], BENIGN),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="run the SAME rungs on a second model and compare what each proposes")
    ap.add_argument("--model", default=None, help="the second model, for --compare")
    args = ap.parse_args()

    from . import pass1, pass2
    board = Board()

    if not args.compare:
        print("=" * 96)
        print("HOUSEKEEPING, SORTED — every step below was really produced by the model")
        print("=" * 96)
        ok = 0
        for note, rung, op, program, want in CASES:
            rows = [S for S in ()]
            table = pass2.symbol_table(
                pass1.run_scanned(pass1.EXPECTED[rung].request, board=board), board)
            got = classify(op, program, table, board)
            hit = got.tier == want
            ok += hit
            print(f"  {'ok  ' if hit else 'FAIL'} rung {rung:<3} {note}")
            print(f"       want {want:<10} got {got.tier:<10} {got.why[:64]}")
        print(f"\n  {ok}/{len(CASES)} sorted as sealed")
        return

    # ⇒ THE OPERATOR'S THEORY: a better model proposes MORE and BETTER housekeeping.
    from .metrics import Lab
    from . import pipeline
    world = Lab()
    print("=" * 96)
    print(f"DOES A BETTER MODEL PROPOSE BETTER HOUSEKEEPING?   second model: {args.model}")
    print("=" * 96)
    for n in (2, 4, 5, 11, 13):
        request = pass1.EXPECTED[n].request
        print(f"\nrung {n} · {request[:70]}")
        for label, model in (("baseline", None), (args.model or "second", args.model)):
            got = pipeline.run(request, board=board, world=world, model=model, retries=0)
            tiers = sort_out(list(got.suggested), list(got.operations), got.table, board)
            counts = " ".join(f"{k}={len(v)}" for k, v in tiers.items() if v) or "none"
            print(f"    {label:<12} program {len(got.operations)}  proposed "
                  f"{len(got.suggested)}   {counts}")
            for tier in (GOOD, RISKY, CANCEROUS):
                for v in tiers[tier]:
                    print(f"                 {v!r}"[:100])


if __name__ == "__main__":
    main()
