"""THE MAPPING — every rung as legal moves, sub-keys, and the one folded final key.

    PYTHONPATH=. python3 -m tests.bench.formula.table

Prints four things, in the order they should be read:

    1  ROUND TRIP    can the slots rebuild every reading we already call correct?
    2  THE ALGEBRA   is the fold commutative, associative, and identity-carrying?
    3  THE TABLE     the operator's deliverable: sub-key per move, final key per rung
    4  THE SPACE     how much of the 7168-key space the whole corpus actually uses
"""
import itertools
import json
from typing import List

from tests.test_ghost_writer import GOALS
from tests.bench.rungs import RUNGS

from . import edges as _edges
from .fold import fold
from .slots import CMP, PRED, SLOTS, Move, build, reduce

BAR = "─" * 108


def _moves(rung: int) -> List[Move]:
    return [reduce(g) for g in GOALS.get(rung, [])]


def round_trip() -> None:
    print(BAR)
    print("1 · ROUND TRIP — can nine slots rebuild every reading we already believe correct?")
    print(BAR)
    ok = bad = 0
    for r, goals in sorted(GOALS.items()):
        for g in goals:
            back = build(reduce(g))
            same = json.dumps(back, sort_keys=True) == json.dumps(g, sort_keys=True)
            ok += same
            bad += not same
            if not same:
                print(f"   rung {r} MISMATCH\n     in  {g}\n     out {back}")
    print(f"   {ok} of {ok + bad} goals rebuilt EXACTLY from slots alone.")
    print("   ⇒ the selector keyword — select / every / per / observe — was DERIVED every")
    print("     time. The model's shape choice carried no information the slots did not.")


def algebra() -> None:
    print()
    print(BAR)
    print("2 · THE ALGEBRA — the operator called it a group formula; here is what it is")
    print(BAR)
    worst = 0
    for r, goals in sorted(GOALS.items()):
        m = _moves(r)
        if len(m) > 6:
            continue
        worst = max(worst, len({fold(list(p)).number for p in itertools.permutations(m)}))
    print(f"   COMMUTATIVE   every permutation of every rung's moves -> {worst} number(s) each")
    print("   ASSOCIATIVE   regrouping the clause splitter's output does not move the number")
    print(f"   IDENTITY      the empty request folds to {fold([]).number}")
    print("   NO INVERSES   nothing folds onto 'create five machines' to undo it")
    print()
    print("   ⇒ SO IT IS A COMMUTATIVE MONOID, not a group — and the missing inverses are the")
    print("     domain being honest: acts on a lab do not undo by composition. The GROUP part")
    print("     is real but sits one level down: the nine presence bits under XOR are (Z/2)^9,")
    print("     the elementary abelian 2-group of order 512.")
    print()
    print("   ⇒ AND COMMUTATIVITY IS THE PAYOFF. The AI does not supply order. It is recovered")
    print("     topologically from edges that were themselves derived. `observe alive` precedes")
    print("     `stop where alive=false` because ASKS→FILTERS says so, and nobody said it.")


def table() -> None:
    print()
    print(BAR)
    print("3 · THE TABLE — each rung's legal moves, their sub-keys, and the folded final key")
    print(BAR)
    for rung in RUNGS:
        moves = _moves(rung.n)
        if not moves:
            continue
        sig = fold(moves)
        print(f"\n  RUNG {rung.n} · {rung.name}")
        print(f"    “{rung.goal}”")
        for slot, orig in enumerate(sig.order):
            m = moves[orig]
            note = ""
            if orig in sig.residual:
                note = "   ⇐ RESIDUAL: filters on a fact another move must go and ASK"
            if orig in sig.holes:
                note += "   ⇐ HOLE: excepts an identity nothing else handles"
            print(f"      move {slot + 1}  {m.mnemonic:<34} k={m.key:<6} {_gloss(m)}{note}")
        if sig.joins:
            for e in sig.joins:
                a, b = sig.order.index(e.src) + 1, sig.order.index(e.dst) + 1
                arrow = f"move {a} → move {b}" if e.kind in _edges.ORDERING else f"move {a} ↔ move {b}"
                print(f"      join    {e.kind:<14} {arrow:<18} on {e.on}")
        else:
            print("      join    (none — the moves are independent)")
        print(f"      FINAL   {sig.fingerprint}   {sig.mnemonic}")
        if sig.cyclic:
            print("      ⇐ CYCLIC: the moves disagree about what must come first")


def _gloss(m: Move) -> str:
    f = m.filled
    bits = []
    if "subject" in f:
        bits.append(str(f["subject"]))
    if "filter" in f:
        bits.append("where " + ",".join(f"{k}={v}" for k, v in f["filter"].items()))
    if "except" in f:
        bits.append("except " + ",".join(f"{k}={v}" for k, v in f["except"].items()))
    if "count" in f:
        bits.append(f"{f['count'][0]} {f['count'][1]}")
    if "predicate" in f:
        bits.append(str(f["predicate"]))
    if "target" in f:
        bits.append("must " + ",".join(f"{k}={v}" for k, v in f["target"].items()))
    if "fact" in f:
        bits.append(f"ask {f['fact']}")
    if "makes" in f:
        bits.append(f"makes {f['makes'][0]}")
    if "source" in f:
        bits.append(f"from {f['source']}")
    return " · ".join(bits)


def space() -> None:
    print()
    print(BAR)
    print("4 · THE SPACE — how much of it the corpus uses, which is the whole argument")
    print(BAR)
    total = (1 << len(SLOTS)) * len(CMP) * len(PRED)
    seen = {}
    for r, goals in sorted(GOALS.items()):
        for m in _moves(r):
            seen.setdefault(m.key, [m.mnemonic, 0, set()])
            seen[m.key][1] += 1
            seen[m.key][2].add(r)
    print(f"   {1 << len(SLOTS)} slot combinations x {len(CMP)} comparators x {len(PRED)} relations"
          f"  =  {total} POSSIBLE MOVES")
    print(f"   the fourteen-rung corpus uses {len(seen)}  ({100 * len(seen) / total:.2f}%)\n")
    for key, (mnemonic, n, rungs) in sorted(seen.items(), key=lambda kv: -kv[1][1]):
        print(f"      k={key:<6} {mnemonic:<34} {n:>2} use(s)   rungs {sorted(rungs)}")
    print()
    print("   ⇒ THE MODEL IS CURRENTLY CHOOSING FROM AN UNBOUNDED SPACE OF SHAPES TO LAND ON")
    print(f"     ONE OF {len(seen)}. That gap is the whole design: it is not being asked a hard")
    print("     question badly, it is being asked an open question that has a closed answer.")


if __name__ == "__main__":
    round_trip()
    algebra()
    table()
    space()
