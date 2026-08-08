"""ITEM 3 — RUN PASS ONE AGAINST THE MODEL. The first real number for the new design.

    PYTHONPATH=. python3 -m tests.bench.twopass.pass1            # all 14 rungs
    PYTHONPATH=. python3 -m tests.bench.twopass.pass1 --only 11
    PYTHONPATH=. python3 -m tests.bench.twopass.pass1 --runs 3

Item 2 built the schema and the suite owns it. This is the first time those four questions
meet a model.

# HOW IT IS GRADED, AND WHY NOT ON NAMES

The names are the requester's own words, so they are free text and cannot be graded by
equality — *"the ones that do not answer"*, *"unresponsive"* and *"dead machines"* are all
correct. So grading is on the three things that are STRUCTURAL and do decide the program:

    CONDITIONS   the union of every row's `where`, against what the request states. This is
                 the LOST-CLAUSE measure — the defect class that has cost most in this project.
    SETS         does a group come back as `<kind>_set` rather than as a single thing. A
                 group declared as an individual is rung 4 and rung 6 broken at the root.
    RESIDUAL     does the run-time set get declared at all. RUNG 11 IS THE ONLY ROW THAT CAN
                 SCORE HERE and it is the one the whole design was built for.

# ⇒ PREDICTIONS, SEALED BEFORE THE RUN (rule V5)

    P1  NAMES COME BACK USABLE. Splitting a request into its own-words parts was measured
        excellent months ago (`extract.in_words`), and this asks for less than that did.
    P2  THE SET DISTINCTION IS THE RISK. "every vm" must come back `vm_set`, not `vm`. I
        expect this to be the weakest of the three axes.
    P3  RUNG 11's RESIDUAL IS ~50/50. Declaring *"the ones that do not answer"* with
        `alive = false` means reaching for an OBSERVED attribute among ten offered. If it
        lands, the design's central claim survives contact; if it does not, pass 1 needs the
        same treatment pass 2 got.
    P4  CONDITIONS UNDER-FILL RATHER THAN OVER-FILL. Lost clauses have always outnumbered
        invented ones here.
    P5  **WATCH FOR OVER-REFUSAL, AND IT WOULD BE MY FAULT.** I put `EXISTING` first in the
        enum deliberately, because every measured error was toward NEW and I wanted the safe
        answer to lead. If first-member bias now dominates, everything comes back EXISTING
        and rungs 1-4 declare nothing as new. That is a decision of mine backfiring, not a
        model failure, and it is the thing to look at first.
"""
import argparse
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
from . import schema as S


class Expect(NamedTuple):
    request: str
    conditions: List[Dict[str, object]]   # every `where` the request states, in any row
    sets: int                             # how many declared things are GROUPS
    residual: bool                        # is any row settled at run time


# THE ANSWER KEY, written before the runner was pointed at a model.
EXPECTED: Dict[int, Expect] = {
    1: Expect("create a vm named alpha", [{"name": "alpha"}], 0, False),
    2: Expect("create a vm named beta and then launch it",
              [{"name": "beta"}], 0, False),
    3: Expect("create a network called lab and a vm named web, then put web on lab",
              [{"net_name": "lab"}, {"name": "web"}], 0, False),
    4: Expect("create 5 vms, put them all in a network, give them all the 'fleet' label, "
              "and make sure they all ping each other", [{"label": "fleet"}], 1, False),
    5: Expect("launch every vm that is currently stopped",
              [{"status": "stopped"}], 1, False),
    6: Expect("create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones "
              "together on their own network, and put the blue ones on a different network",
              [{"label": "red"}, {"label": "blue"}], 2, False),
    7: Expect("make sure exactly 3 vms carry the 'prod' label", [{"label": "prod"}], 1, False),
    8: Expect("put every vm on a network called core, except db — db goes on a network "
              "called dmz instead",
              [{"name": "db"}, {"net_name": "core"}, {"net_name": "dmz"}], 1, False),
    9: Expect("make sure n1, n2 and n3 can all ping each other",
              [{"name": "n1"}, {"name": "n2"}, {"name": "n3"}], 0, False),
    10: Expect("clone golden into 3 new vms and launch all of them", [], 1, False),
    11: Expect("ping every vm and stop the ones that do not answer",
               [{"alive": False}], 2, True),          # ⇐ THE ONE THAT MATTERS
    12: Expect("take a snapshot of every running vm", [{"status": "running"}], 1, False),
    13: Expect("take 5 vms, put them all in a network, give them all the 'fleet' label, "
               "and make sure they all ping each other", [{"label": "fleet"}], 1, False),
    14: Expect("make sure there are exactly two machines left", [], 1, False),
}


def run_pass1(request: str, board: Optional[Board] = None, model=None, temp=0.0,
              timeout=180, trace: Optional[List] = None) -> List[S.Declared]:
    """The four questions, one per call, exactly as `schema.py` declares them."""
    from engines.channel import constrained

    board = board or Board()

    def ask(question: str, built: dict):
        try:
            got = constrained(question, f"the sentence: {request}", built,
                              model=model, temp=temp, timeout=timeout) or {}
            return got.get("answer")
        except Exception as exc:
            if trace is not None:
                trace.append(("<failed>", f"{type(exc).__name__}"))
            return None

    names = ask(S.NAMES_Q, S.names_schema()) or []
    if trace is not None:
        trace.append(("names", list(names)))

    rows: List[S.Declared] = []
    for name in names:
        object_type = ask(S.TYPE_Q.format(name=name, suffix=S.SET_SUFFIX), S.type_schema(board))
        if not object_type:
            continue
        pairs = ask(S.WHERE_Q.format(name=name), S.where_schema(object_type, board)) or []
        where = {p["attribute"]: p["value"] for p in pairs
                 if isinstance(p, dict) and "attribute" in p}
        existence = ask(S.EXISTENCE_Q.format(name=name, new=S.NEW, existing=S.EXISTING),
                        S.existence_schema()) or S.EXISTING
        rows.append(S.declare_from(name, object_type, where, existence, board))
    return rows


def grade(rows: List[S.Declared], want: Expect) -> Dict[str, object]:
    """Structural only. Names are the requester's words and are never compared."""
    got_conditions = [dict(r.where) for r in rows if r.where]
    found = 0
    for wanted in want.conditions:
        if any(all(g.get(k) == v for k, v in wanted.items()) for g in got_conditions):
            found += 1
    invented = sum(1 for g in got_conditions
                   if not any(all(g.get(k) == v for k, v in w.items())
                              for w in want.conditions))
    return {
        "rows": len(rows),
        "conditions": f"{found}/{len(want.conditions)}" if want.conditions else "—",
        "conditions_ok": found == len(want.conditions),
        "invented": invented,
        "sets": sum(1 for r in rows if r.is_set),
        "sets_ok": sum(1 for r in rows if r.is_set) >= want.sets,
        "residual": any(r.residual for r in rows),
        "residual_ok": any(r.residual for r in rows) == want.residual,
        "new": sum(1 for r in rows if r.existence == S.NEW),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    board = Board()
    tally: Counter = Counter()
    print("=" * 104)
    print("ITEM 3 · PASS ONE AGAINST THE MODEL — graded on structure, never on names")
    print("=" * 104)

    for n, want in sorted(EXPECTED.items()):
        if args.only and n != args.only:
            continue
        print(f"\n{'─' * 104}\nrung {n} · “{want.request[:88]}”")
        print(f"    want   conditions {want.conditions}   sets>={want.sets}   "
              f"residual={want.residual}")
        for i in range(args.runs):
            trace: List = []
            rows = run_pass1(want.request, board=board, model=args.model, trace=trace)
            g = grade(rows, want)
            for row in rows:
                mark = "  ⇐ RESIDUAL" if row.residual else ""
                where = ", ".join(f"{k}={v}" for k, v in row.where.items()) or "—"
                print(f"      {row.name[:28]:<30} {row.object_type:<14} {where:<26} "
                      f"{row.existence}{mark}")
            print(f"    run {i + 1}  conditions {g['conditions']}  invented {g['invented']}  "
                  f"sets {g['sets']}  residual {g['residual']}  new {g['new']}")
            tally["conditions_ok"] += g["conditions_ok"]
            tally["sets_ok"] += g["sets_ok"]
            tally["residual_ok"] += g["residual_ok"]
            tally["invented"] += g["invented"]
            tally["new"] += g["new"]
            tally["cells"] += 1

    c = max(tally["cells"], 1)
    print(f"\n{'=' * 104}")
    print(f"  cells                    {tally['cells']}")
    print(f"  every condition found    {tally['conditions_ok']}/{c}")
    print(f"  groups declared as sets  {tally['sets_ok']}/{c}")
    print(f"  residual correct         {tally['residual_ok']}/{c}   "
          f"⇐ rung 11 is the only one that can score TRUE here")
    print(f"  conditions invented      {tally['invented']}    (P4 said under- beats over-fill)")
    print(f"  rows called NEW          {tally['new']}    (P5: near-zero means MY enum "
          f"ordering backfired)")


if __name__ == "__main__":
    main()
