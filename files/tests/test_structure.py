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


def test_a_negation_selects_the_complement():
    """⇒⇒ **A NEGATED FILTER WAS READING AS ITS OWN OPPOSITE.** *"every vm that is NOT
    running"* came back `{status: running}` — the exact set the operator excluded.

    `conditions_from` computes `negated` and spends it on ONE of its three rules: an OBSERVED
    attribute gets `out[attr] = not negated`. Rule 1 — a declared VALUE naming its own
    attribute — ignored it, and rule 1 is the one every status filter goes through.

    ⇒ **AND THE MANIFEST MAKES THE FIX EXACT RATHER THAN APPROXIMATE.** `attr_values.status`
      is a CLOSED set of exactly two — `running` and `stopped` — so the complement of one is
      the other, by declaration. Nothing is inferred and no new field is needed.
    ⇒ **WITH MORE THAN TWO IT DECLINES**, because the complement is then a SET and `where`
      holds one value. Saying nothing leaves gate 2 to ask; saying `stopped` when there are
      four states would be confidently wrong.
    """
    from orchestrator.seam.scan import conditions_from
    board = Board()
    got = conditions_from("that is not running", "vm", board)
    check(f"`not running` is the complement — {got}", got.get("status") == "stopped")
    got = conditions_from("that is not stopped", "vm", board)
    check(f"`not stopped` is the complement — {got}", got.get("status") == "running")
    # ⇒ THE ALIAS RESOLVES FIRST, so the complement is taken of what the lab stores.
    got = conditions_from("that is not up", "vm", board)
    check(f"`not up` resolves then complements — {got}", got.get("status") == "stopped")

    # ⇒ THE CONTROLS: an unnegated filter is untouched, and a negator belonging to a DIFFERENT
    #   value must not reach this one.
    check("`that is running` is unchanged",
          conditions_from("that is running", "vm", board).get("status") == "running")
    check("`currently stopped` is unchanged",
          conditions_from("that is currently stopped", "vm", board).get("status") == "stopped")
    # ⇒ AND THE OBSERVED ARM, WHICH ALREADY HAD THE NEGATION, STILL HAS IT — rung 11.
    got = conditions_from("that do not answer", "vm", board)
    check(f"the observed arm still negates — {got}", got.get("alive") is False)


def test_a_disjunction_is_a_choice_nobody_made():
    """⇒⇒ **`or` READ AS `and` ACTS ON BOTH, AND THE VERDICT HID IT.** *"stop alpha or beta"*
    came back REFUSE — but only because the lab held neither machine. The OPERATIONS are what
    show the reading:

        stop alpha or beta    ops=[stop_vm(beta), stop_vm(beta)]

    alpha dropped, beta doubled. **Against a lab that holds them, that serves.**

    ⇒ **A DISJUNCTION IS A CHOICE AND ONLY THE OPERATOR CAN MAKE IT.** The clause must NOT be
      split — splitting produces two orders, which is the acting-on-both this exists to stop.
      It is one clause carrying two candidates and no way to pick.

    ⇒ **`or` IS ALREADY IN `CONJUNCTIONS`**, so this adds no vocabulary — it adds a finding,
      which is `unexpressed-exclusion`'s own shape one word over: the sentence says something
      the program does not express.
    """
    from orchestrator.seam import linguistics as L
    from orchestrator.seam.effects import Operation
    board = Board()
    ops = [Operation("stop_vm", "beta", None), Operation("stop_vm", "beta", None)]
    got = L.findings("stop alpha or beta", [], ops, [], board=board)
    kinds = [f.rule for f in got]
    check(f"a disjunction is raised — {kinds}", "unexpressed-choice" in kinds)

    # ⇒ THE CONTROLS. `or` inside a QUOTED value is not a choice, and a request with no `or`
    #   must stay silent — a finding that fires on everything is a finding nobody reads.
    quiet = L.findings("stop the vms", [], [Operation("stop_vm", "vms", None)], [], board=board)
    check("no disjunction, no finding",
          "unexpressed-choice" not in [f.rule for f in quiet])
    check("the rule belongs to linguistics", "unexpressed-choice" in L.OWNS)


def test_a_quoted_clause_is_evidence_not_a_value():
    """⇒⇒ **QUOTES ALREADY MEAN *A VALUE* IN THIS SYSTEM, AND THAT IS RIGHT FOR ONE WORD.**
    `residue.classify` bounces on a quoted word — *"3 vms labelled 'red'"* binds `red` — and
    the whole corpus quotes labels that way.

    ⇒ **A QUOTED CLAUSE IS A DIFFERENT ACT.** *"the error says 'cannot allocate memory'"* is
      the operator handing us DATA: it correlates with no kind, no member and no archive entry
      — the exact profile of something unrelated — and it is the EVIDENCE a diagnosis runs on.

    ⇒ **THE DISCRIMINATOR IS LENGTH AND IT IS STRUCTURAL.** One word inside quotes is a value;
      two or more is a quotation. No vocabulary, and it matches the corpus exactly — every
      quoted span in the fourteen rungs is a single word.
    """
    from orchestrator.seam.scan import quoted_clauses
    check("a multi-word quote is evidence",
          quoted_clauses("the error says 'cannot allocate memory'")
          == ("cannot allocate memory",))
    check("double quotes read the same",
          quoted_clauses('it said "no space left on device"')
          == ("no space left on device",))
    # ⇒⇒ ⚠ THE CONTRACTION, AND IT IS HERE BECAUSE THE UNIT TEST MISSED IT. Every example
    #   above avoids apostrophes, so the first cut matched from the one in `won't` to the one
    #   opening the real quotation and reported "t boot, the error says" as evidence. Found by
    #   running the whole seam, which is why the end-to-end check is not optional.
    check("an apostrophe inside a word is not a quote",
          quoted_clauses("alpha won't boot, the error says 'cannot allocate memory'")
          == ("cannot allocate memory",))
    check("a possessive does not open a quote",
          quoted_clauses("delete alpha's snapshots") == ())
    # ⇒ THE CONTROLS — every quoted span in the rung corpus is a single word, and must stay one.
    for value in ("make sure exactly 3 vms carry the 'prod' label",
                  "create 3 vms labelled 'red' and 2 vms labelled 'blue'",
                  "give them all the 'fleet' label"):
        check(f"a quoted VALUE is not evidence — {value[:34]!r}",
              quoted_clauses(value) == ())


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "structure")


if __name__ == "__main__":
    raise SystemExit(main())
