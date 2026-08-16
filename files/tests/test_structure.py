"""test_structure.py — HOW THE SENTENCE IS BUILT, pinned one structural feature at a time.

`tests/bench/structure_map.py` is the map: 39 ways an English sentence is built, what reads
each one today, and 23 holes of which 12 change WHAT RUNS. This suite is where a hole gets
closed — one feature, one test, written BEFORE the fix and kept as the regression.

⇒ **SCOPED TO READ, ON THE OPERATOR'S INSTRUCTION, 2026-08-16:** *"we need to able to cover
  everything in the english language, meaning we complete at least our READ… we aren trying to
  resolve at 100% but READ should be really good"* — and *"a good read and a good route means
  resolve and everything downstream gets better."*

⇒ **AND READ IS SEPARABLE FROM EMIT, WHICH IS WHAT MAKES THIS WORTH DOING NOW.** ISO 24617-2
  treats CONDITIONALITY as a QUALIFIER on a dialogue act rather than as clause structure, so a
  conditional can be READ and carried as a flag while E5 — the writer cannot emit `if` — stays
  open. A conditional that is read and cannot be emitted is strictly better than one nobody
  read, because the first can decline and the second acts on half the sentence.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.seam import pass1, speech_act as SA
from planner.formula.legal import Board

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def test_a_subordinate_clause_is_not_a_predication():
    """⇒⇒ **AN `if` CLAUSE WAS READING AS TEACHING, AND THE LOOP BOUND IS WHY.**

    `_main_clause_copula` walks `words[1:]` looking for a copula that belongs to THIS clause,
    stopping at a relativizer because everything after one belongs to a subordinate clause.
    **It never looks at index 0**, so a clause that OPENS on a subordinator was never
    recognised as subordinate: *"if alpha is stopped"* found `is` and came back ASSERTIVE.

    ⇒ **AND THE VOCABULARY WAS ALREADY DECLARED.** `CONJUNCTIONS` holds `if`, `unless`,
      `while`, `because`, `although`, `though`, `whether`; the coordinating members of the same
      class — `and`, `or`, `but`, `nor`, `yet` — must NOT count, because a clause joined by one
      of those IS a main clause. A subset of a declared class, which is the move `DEONTIC`
      already makes on `AUXILIARIES`.

    ⇒⇒ ⚠ **AND IT WENT FROM WRONG TO SILENT ON 2026-08-16.** The per-chunk producer rule drops
      the rows of any clause that cannot BUILD, and ASSERTIVE is one of those — so a condition
      stopped being mis-declared and started being discarded without a word. `None` is the
      honest answer here: an unread clause is not dropped, so the seam still reports it.
    """
    board = Board()
    for clause in ("if alpha is stopped",
                   "unless alpha is running",
                   "because the vms are stuck",
                   "although alpha is busy",
                   "while the snapshot is running"):
        got = SA.act_of(clause, board)
        check(f"a subordinate clause is not teaching — {clause!r} -> {got}",
              got != SA.ASSERTIVE)

    # ⇒ AND THE COORDINATING HALF MUST BE UNTOUCHED. `and`/`but` join main clauses, so the
    #   copula behind one is this clause's own predication — that is the archive's input.
    for clause in ("and alpha is the jumpbox", "but n1 is a vm"):
        check(f"a coordinated clause still predicates — {clause!r}",
              SA.act_of(clause, board) == SA.ASSERTIVE)

    # ⇒ THE STANDING CONTROL: teaching still reads as teaching.
    check("`a jumpbox is a vm` is still teaching",
          SA.act_of("a jumpbox is a vm", board) == SA.ASSERTIVE)


def test_a_condition_is_not_dropped_in_silence():
    """⇒ **THE WHOLE SENTENCE, NOT THE CLAUSE** — and the reason this test exists beside the
    one above. `pass1.BUILDS` decides whose rows survive; a clause read ASSERTIVE loses its
    rows, and a clause read `None` keeps them because UNREAD is not UNPRODUCTIVE.

    ⇒ So the pin is not *"the condition is understood"* — it is not, and E5 is why. It is that
      **the condition is still VISIBLE to everything downstream**, which is the difference
      between declining and acting on half a request.
    """
    board = Board()
    request = "if alpha is stopped, launch it"
    read = SA.read(request, board)
    dropped = [c for c, a in read if a is not None and a not in pass1.BUILDS]
    check(f"the `if` clause is not dropped as unproductive — read={[a for _, a in read]}",
          not any("if alpha" in c for c in dropped))


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "structure")


if __name__ == "__main__":
    raise SystemExit(main())
