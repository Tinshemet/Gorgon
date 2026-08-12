"""EVERY METRIC IN ONE TABLE — pass 1, the effect table, and junk handling. No model call.

    PYTHONPATH=. python3 -m tests.bench.twopass.metrics

⇒ **THE OPERATIONS ARE SUPPLIED, AND THAT IS STATED IN THE OUTPUT RATHER THAN BURIED HERE.**
  Pass 2 does not exist yet. The operations below are the ones the model was MEASURED
  producing in item 1 (`[create_vm beta, launch_vm beta]` 3/3, `add_vm_to_network web lab`
  3/3), and every EFFECT is computed from the manifest with no model call. So the table says
  what the structure reaches once operations are in — not what a live pipeline scores today.

⇒ **AND THEY ARE APPLIED TO PASS 1's REAL ROWS**, not to an idealised declaration set.
  `effects.py` hand-supplied a `db` row for rung 8 that pass 1 does not produce, which is why
  it read 5/5 there. Against the actual rows rung 8 is short, and the table shows it short.
"""
from typing import Dict, List

from planner.formula.legal import Board
from orchestrator.seam import gates12, pass1
from orchestrator.seam import residue
from orchestrator.seam.effects import Operation, conditions_after, flatten

# THE OPERATIONS, KEYED TO THE ROW NAMES PASS 1 ACTUALLY EMITS. Anything not listed runs with
# no operations at all, which is correct — those rungs assert their conditions outright.
OPERATIONS: Dict[int, List[Operation]] = {
    2: [Operation("launch_vm", "a vm named beta")],
    3: [Operation("add_vm_to_network", "a vm named web", "lab")],
    4: [Operation("add_label", "5 vms", "fleet")],
    8: [Operation("add_vm_to_network", "db", "dmz")],
    13: [Operation("add_label", "5 vms", "fleet")],
}

class Lab:
    """THE SMALLEST LAB THAT ANSWERS `select`, AND EVERY ROW IN IT IS NAMED BY THE CORPUS.

    ⇒ **STATED LOUDLY BECAUSE IT IS THE DIFFERENCE BETWEEN 13/14 AND 14/14.** Rung 8 says
      *"except db"* and nothing in English says `db` is a machine. Only a lab can, and a real
      deployment has one — but a bench does not, so this is it. It holds exactly the objects
      the requests REFER TO as already existing, and nothing else: adding a row the corpus
      does not mention would be flattering the number.
    """
    ROWS = [
        {"kind": "vm", "name": "db", "status": "running"},        # rung 8's `except db`
        {"kind": "vm", "name": "golden", "status": "stopped"},    # rung 10's clone source
    ]

    def select(self, query):
        return [r for r in self.ROWS
                if all(str(r.get(k, "")).lower() == str(v).lower() for k, v in query.items())]


JUNK = [
    ("junk as a descriptor", "create a grubnash vm named alpha", "ASK"),
    ("junk on a second kind", "put every vm on a grubnash network", "ASK"),
    ("junk in two spans", "create a grubnash vm and add it to a grubnash network", "ASK"),
    ("junk as a NAME", "create a vm named grubnash", "silent"),
    ("junk as a LABEL", "give every vm the 'grubnash' label", "silent"),
    ("junk with no kind", "create a vm named alpha and launch it, grubnash", "gate 2"),
    ("junk alone", "grubnash grubnash grubnash", "gate 2"),
]


def _aimed(operations: List[Operation], rows) -> List[Operation]:
    """Point an operation at a row by WHAT IT IDENTIFIES, never by the row's span text.

    ⇒ **THE TABLE USED TO NAME THE SPAN VERBATIM — `'except db — db goes on a network called
      dmz instead'` — AND THAT IS RUNG-SPECIFIC IN THE WORST WAY.** The string is an artefact
      of how the scanner happened to cut that sentence, so any scanner change silently misses
      the row and the effect vanishes with no error. It also encoded a defect: that span WAS
      the bug.

    An operation names an IDENTITY (`db`); this finds whichever row carries it. That is the
    same contract pass 2 will have — rule D1, an operation may only point at a declared name.
    """
    out: List[Operation] = []
    for op in operations:
        target = op.on
        for row in rows:
            values = {str(v).lower() for v in (row.where or {}).values()}
            if (str(row.name).lower() == str(op.on).lower()
                    or str(op.on).lower() in values
                    or str(row.identity or "").lower() == str(op.on).lower()):
                target = row.name
                break
        out.append(Operation(op.operator, target, op.value))
    return out


def _stub_model():
    import engines.channel as channel
    was, channel.constrained = channel.constrained, lambda *a, **k: {}
    return channel, was


def main() -> None:
    channel, was = _stub_model()
    board = Board()
    try:
        print("=" * 100)
        print("PASS 1 — anchor and scan, graded on structure (no model call)")
        print("=" * 100)
        tally = {k: 0 for k in ("identities_ok", "conditions_ok", "conditions_effects_ok",
                                "sets_ok", "residual_ok", "invented", "extra")}
        verdicts: Dict[str, int] = {}
        rung_rows = {}
        lab = Lab()
        for n, want in sorted(pass1.EXPECTED.items()):
            rows = pass1.run_scanned(want.request, board=board)
            # ⇒ GATE 2 ASKS WHAT A KINDLESS ROW IS; THE LAB ANSWERS. The gate still repairs
            #   nothing — this applies an answer that arrived, and with a lab attached the
            #   answer arrives without interrupting anyone.
            rows = pass1.settle_with_world(rows, lab, board)
            rung_rows[n] = rows
            g = pass1.grade(rows, want)

            # ── the SAME rows, after the manifest's declared effects
            declared = {r.name: dict(r.where) for r in rows}
            after = flatten(conditions_after(declared, _aimed(OPERATIONS.get(n, []), rows),
                                             board))
            with_effects = sum(1 for w in want.conditions if w in after)
            ok_effects = with_effects == len(want.conditions)

            for r in residue.report(rows, want.request, board):
                verdicts[r.verdict] = verdicts.get(r.verdict, 0) + 1

            tally["identities_ok"] += g["identities_ok"]
            tally["conditions_ok"] += g["conditions_ok"]
            tally["conditions_effects_ok"] += ok_effects
            tally["sets_ok"] += g["sets_ok"]
            tally["residual_ok"] += g["residual_ok"]
            tally["invented"] += g["invented"]
            tally["extra"] += max(0, g["extra_rows"])
            mark = "" if ok_effects else "   ⇐ still short"
            print(f"  rung {n:>2}  names {g['identities']:<5} conditions {g['conditions']:<5} "
                  f"+effects {with_effects}/{len(want.conditions)}{mark}")

        c = len(pass1.EXPECTED)
        print("\n" + "=" * 100)
        print(f"  {'named things found':<34} {tally['identities_ok']}/{c}")
        print(f"  {'groups declared as sets':<34} {tally['sets_ok']}/{c}")
        print(f"  {'residual correct':<34} {tally['residual_ok']}/{c}")
        print(f"  {'conditions — pass 1 alone':<34} {tally['conditions_ok']}/{c}")
        print(f"  {'conditions — WITH the effect table':<34} "
              f"{tally['conditions_effects_ok']}/{c}   ⇐ operations supplied")
        print(f"  {'conditions invented':<34} {tally['invented']}")
        print(f"  {'surplus rows':<34} {tally['extra']}")
        print(f"  {'span-grain verdicts on 14 rungs':<34} {verdicts}")

        print("\n" + "=" * 100)
        print("JUNK HANDLING — the same meaningless word in every position it can occupy")
        print("=" * 100)
        for label, request, want in JUNK:
            rows = pass1.run_scanned(request, board=board)
            rep = gates12.report(rows, request, board)
            span = [f for f in rep["findings"] if f.kind == "unread-descriptor"]
            kindless = [f for f in rep["findings"] if f.kind == "kind-not-settled"]
            got = ("ASK" if span else "gate 2" if kindless else
                   "silent" if not rep["findings"] else "other")
            laundered = any(r.kind in board.kinds and "grubnash" in r.name.lower()
                            and not r.where for r in rows)
            print(f"  {label:<24} {got:<8} want {want:<8} "
                  f"{'ok ' if got == want else 'FAIL'}  "
                  f"{'LAUNDERED' if laundered and got == 'silent' else ''}")
            for f in (span + kindless)[:1]:
                print(f"      {f.says[:88]}")
    finally:
        channel.constrained = was


if __name__ == "__main__":
    main()
