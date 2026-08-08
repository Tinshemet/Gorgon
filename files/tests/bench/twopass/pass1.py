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

# ⇒⇒ THE FIRST FINDING, AND IT IS AN ARCHITECTURAL HOLE WE PUT THERE

Rung 11 fails structurally, not narrowly:

    vm                        vm_set        —           existing
    ones that do not answer   network_set   net_name=   new      ⇐ should be vm_set, alive=false

The type answer is wrong, so `where_schema` then offered NETWORK attributes — `alive` was
never on the menu and the residual could not be found EVEN IN PRINCIPLE. One wrong answer
poisons every question after it.

**AND THE CAUSE IS ONE WORD.** Measured stable, 2 of 2 each:

    'ones that do not answer'        -> network_set   WRONG   ⇐ the model's own name
    'the ones that do not answer'    -> vm_set        right
    'the ones that do not respond'   -> vm_set        right
    'unresponsive machines'          -> vm_set        right

⇒ **THE NAME IS PASS ONE'S ONLY FREE-TEXT FIELD, AND IT IS THE INPUT TO ALL THE OTHERS.** We
  closed conditions, types and existence to enums and left free text in the ONE place that
  feeds all three. Question 1 emits a paraphrase; questions 2-4 consume it; and a type error
  is unrecoverable because it changes which attributes exist to be chosen from.

⇒ TWO CANDIDATE FIXES:
    * ASK NAME AND TYPE TOGETHER — **MEASURED AND REJECTED, see below.**
    * MAKE THE NAME A SPAN of the request rather than a paraphrase. Untested. Span quotation
      was tried once before and withdrawn ([[gorgon-refusal-enum-withdrawn]]).

# ⇒⇒ RESULTS WITH CLEAN PROMPTS — THE PAIRED FIX IS REJECTED, AND PASS 1 DOES NOT WORK

                             baseline    paired
    named things found         14/14      14/14
    GROUPS SEEN AS GROUPS      13/14       4/14   <- pairing DESTROYED the one working axis
    conditions found           12/14      13/14
    surplus things declared       24         31
    conditions INVENTED           36         37

**PAIRING NAME AND TYPE COLLAPSES SET RECOGNITION.** Forced to commit to a sort while it is
still listing, the model picks the plain kind over the `_set` kind, so "every vm" comes back as
one machine. The contrastive-pair precedent did not transfer: `which_ones` and `must_become`
disambiguate each other, but a name does not disambiguate a type — it PRECEDES it, and the
separate question gets to see the finished name before judging it.

**AND PASS 1 DOES NOT WORK IN EITHER ARM.** Rung 11:

    baseline   ping / vm / ones, all vm_set, no conditions   <- "ping" declared as a THING
    paired     answer : network, one row

Neither finds `alive = false`, so the residual — the entire point — is never reachable.

# ⇒ WHAT THE NUMBERS ACTUALLY SAY THE PROBLEM IS

It is NOT extraction. Names come back 14/14 in both arms. The failures are:

  * **OVER-DECLARATION.** 24 surplus rows across 14 requests. It declares verbs (`ping`),
    fragments (`ones`, `answer`, `each other`) and the kind word itself as separate things.
    Question 1 asks for "every distinct thing" and every noun phrase qualifies.
  * **INVENTED CONDITIONS.** 36 of them. Given a `where` question about a thing that should
    have no conditions, it fills one in anyway — the same over-fill P4 got backwards.

⇒ SO THE OPEN QUESTION IS NOT "can it name things" — IT CAN. It is **how to stop it naming
  things that are not things**, which is a different problem from anything item 1 tested.
"""
import argparse
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board
from . import schema as S


class Expect(NamedTuple):
    request: str
    identities: List[str]                 # names the request states — must appear SOMEWHERE
    conditions: List[Dict[str, object]]   # real conditions BEYOND identity
    sets: int                             # how many declared things are GROUPS
    residual: bool                        # is any row settled at run time
    rows: int                             # how many things there really are — REPORTED only


# ── THE ANSWER KEY, CORRECTED. The first version was wrong twice, both my errors: ──────
#
#   1  IT DOUBLE-COUNTED IDENTITY. If a row is NAMED `alpha` and typed `vm`, demanding
#      `where {name: alpha}` as well asks the model to state the same fact twice. A name is
#      carried by the `name` field; it is not a condition. So identities are now checked as
#      NAMES and struck from `conditions`.
#   2  IT COUNTED ACTIONS AS CONDITIONS. Rung 4's *"give them all the 'fleet' label"* is
#      something pass 2 DOES, not something that picks the set out. Asking pass 1 for it was
#      asking the wrong pass.
#
# What remains under `conditions` is only what genuinely narrows a set: a status, a label
# that DISTINGUISHES two groups, an observed fact.
EXPECTED: Dict[int, Expect] = {
    1: Expect("create a vm named alpha", ["alpha"], [], 0, False, 1),
    2: Expect("create a vm named beta and then launch it", ["beta"], [], 0, False, 1),
    3: Expect("create a network called lab and a vm named web, then put web on lab",
              ["lab", "web"], [], 0, False, 2),
    4: Expect("create 5 vms, put them all in a network, give them all the 'fleet' label, "
              "and make sure they all ping each other", [], [], 1, False, 2),
    5: Expect("launch every vm that is currently stopped",
              [], [{"status": "stopped"}], 1, False, 1),
    6: Expect("create 3 vms labelled 'red' and 2 vms labelled 'blue', put the red ones "
              "together on their own network, and put the blue ones on a different network",
              [], [{"label": "red"}, {"label": "blue"}], 2, False, 4),
    7: Expect("make sure exactly 3 vms carry the 'prod' label",
              [], [{"label": "prod"}], 1, False, 1),
    8: Expect("put every vm on a network called core, except db — db goes on a network "
              "called dmz instead", ["db", "core", "dmz"], [], 1, False, 4),
    9: Expect("make sure n1, n2 and n3 can all ping each other",
              ["n1", "n2", "n3"], [], 0, False, 3),
    10: Expect("clone golden into 3 new vms and launch all of them",
               ["golden"], [], 1, False, 2),
    11: Expect("ping every vm and stop the ones that do not answer",
               [], [{"alive": False}], 2, True, 2),   # ⇐ THE ONE THAT MATTERS
    12: Expect("take a snapshot of every running vm",
               [], [{"status": "running"}], 1, False, 2),
    13: Expect("take 5 vms, put them all in a network, give them all the 'fleet' label, "
               "and make sure they all ping each other", [], [], 1, False, 2),
    14: Expect("make sure there are exactly two machines left", [], [], 1, False, 1),
}


def ask_conditions(name: str, object_type: str, ask, board: Board) -> Dict[str, object]:
    """THE FORCED CHOICE — MEASURED WORSE AND NOT THE DEFAULT. Kept for the A/B.

    The idea was sound and the measurement refused it: 32 genuinely invented conditions against
    the array form's 16, with the scope question working correctly at 6/6 in isolation.

    ⇒ **THE ESCAPE HATCH MATTERED MORE THAN THE CLOSURE.** An array can answer `[]` at the END,
      after seeing the attributes. This commits at the START and then REQUIRES an attribute and
      a value, so every "only some" manufactures a condition whether or not one exists. Removing
      the late decline cost more than closing the value bought.
    """
    kind = object_type[:-len(S.SET_SUFFIX)] if object_type.endswith(S.SET_SUFFIX) else object_type
    scope = ask(S.SCOPE_Q.format(name=name, plural=S.plural_for(kind, board)),
                S.scope_schema())
    if scope != S.ONLY_SOME:
        return {}                                   # it declined, and declining is an answer
    attr = ask(S.ATTRIBUTE_Q.format(kind=kind, name=name),
               S.attribute_schema(object_type, board))
    if not attr:
        return {}
    value = ask(S.VALUE_Q.format(name=name, attr=attr),
                S.value_schema(object_type, attr, board))
    return {attr: value} if value is not None else {}


def _old_where(name: str, object_type: str, ask, board: Board) -> Dict[str, object]:
    """The array form, kept only so the A/B can be re-run. MEASURED WORSE."""
    pairs = ask(S.WHERE_Q.format(name=name), S.where_schema(object_type, board)) or []
    return {p["attribute"]: p["value"] for p in pairs
            if isinstance(p, dict) and "attribute" in p}


def run_pass1(request: str, board: Optional[Board] = None, model=None, temp=0.0,
              timeout=180, trace: Optional[List] = None,
              paired: bool = False, fold: bool = True,
              expand_names: bool = True, forced: bool = False) -> List[S.Declared]:
    """The questions, one per call, exactly as `schema.py` declares them.

    `paired=True` asks NAME and TYPE together — the fix for the measured cascade, where the
    model's own free-text name became the input to the type question and one missing word
    ('the') flipped `vm_set` to `network_set`.
    """
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

    if paired:
        got = ask(S.PAIRED_Q, S.paired_schema(board)) or []
        pairs = [(p.get("name"), p.get("sort")) for p in got
                 if isinstance(p, dict) and p.get("name") and p.get("sort")]
    else:
        names = ask(S.NAMES_Q, S.names_schema()) or []
        pairs = [(n, None) for n in names]
    if trace is not None:
        trace.append(("things", list(pairs)))

    rows: List[S.Declared] = []
    for name, sort in pairs:
        # REPAIR A CHUNKED NAME BEFORE ANY QUESTION IS ASKED ABOUT IT. The restriction is
        # still in the request; recovering it is cheaper and more reliable than re-asking.
        name = S.expand(name, request) if expand_names else name
        object_type = sort or ask(S.TYPE_Q.format(name=name, suffix=S.SET_SUFFIX, nouns=S.nouns_offered(board)),
                                  S.type_schema(board))
        if not object_type:
            continue
        where = ask_conditions(name, object_type, ask, board) if forced else _old_where(
            name, object_type, ask, board)
        existence = ask(S.EXISTENCE_Q.format(name=name, new=S.NEW, existing=S.EXISTING),
                        S.existence_schema()) or S.EXISTING
        rows.append(S.declare_from(name, object_type, where, existence, board))
    # FOLD REPEATED MENTIONS. The model mentions things more than once — by name and by
    # pronoun — and that is fine. The first mention declares; the rest become references.
    return S.merge(rows, board, request) if fold else rows


def grade(rows: List[S.Declared], want: Expect) -> Dict[str, object]:
    """Structural only. Names are the requester's words and are never compared."""
    got_conditions = [dict(r.where) for r in rows if r.where]
    found = sum(1 for wanted in want.conditions
                if any(all(g.get(k) == v for k, v in wanted.items()) for g in got_conditions))
    invented = sum(1 for g in got_conditions
                   if not any(all(g.get(k) == v for k, v in w.items())
                              for w in want.conditions))
    # IDENTITY IS CHECKED AS A NAME **OR AS A REFERENCE**, not as a condition. `alpha` must
    # appear as the name of some row; demanding `where {name: alpha}` too would ask for the
    # same fact twice.
    #
    # ⇒ REFERENCES COUNT, AND LEAVING THEM OUT WAS A GRADER BUG. The operator: *"the older run
    #   is now invalid, because yes it can name objects correctly but it doesn't account for
    #   the issue that surfaced, which is references."* A mention that folds CORRECTLY was
    #   scoring as a LOST name — the whole 14/14 -> 12/14 drop was this, not a regression.
    names = " ".join([r.name.lower() for r in rows]
                     + [ref.lower() for r in rows for ref in r.references])
    named = sum(1 for i in want.identities if i.lower() in names)
    return {
        "rows": len(rows),
        "folded": sum(len(r.references) for r in rows),
        "extra_rows": len(rows) - want.rows,
        "identities": f"{named}/{len(want.identities)}" if want.identities else "—",
        "identities_ok": named == len(want.identities),
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
    ap.add_argument("--paired", action="store_true",
                    help="ask NAME and TYPE together — the cascade fix (REJECTED, kept for A/B)")
    ap.add_argument("--forced-conditions", action="store_true",
                    help="ask ALL-or-SOME first — MEASURED WORSE (32 invented against 16) "
                         "because committing to SOME leaves no way to decline afterwards")
    ap.add_argument("--no-expand", action="store_true",
                    help="do NOT repair chunked names from the request")
    ap.add_argument("--no-fold", action="store_true",
                    help="do NOT fold repeated mentions — the pre-fold baseline")
    args = ap.parse_args()

    board = Board()
    tally: Counter = Counter()
    print("=" * 104)
    print(f"ITEM 3 · PASS ONE AGAINST THE MODEL — "
          f"{'PAIRED name+type' if args.paired else 'separate questions'}"
          f"{'' if args.no_expand else ' + EXPAND'}"
          f"{'' if args.no_fold else ' + FOLD'}, "
          f"graded on structure, never on names")
    print("=" * 104)

    for n, want in sorted(EXPECTED.items()):
        if args.only and n != args.only:
            continue
        print(f"\n{'─' * 104}\nrung {n} · “{want.request[:88]}”")
        print(f"    want   names {want.identities}   conditions {want.conditions}   "
              f"sets>={want.sets}   residual={want.residual}   rows {want.rows}")
        for i in range(args.runs):
            trace: List = []
            rows = run_pass1(want.request, board=board, model=args.model, trace=trace,
                             paired=args.paired, fold=not args.no_fold,
                             expand_names=not args.no_expand,
                             forced=args.forced_conditions)
            g = grade(rows, want)
            for row in rows:
                mark = "  ⇐ RESIDUAL" if row.residual else ""
                where = ", ".join(f"{k}={v}" for k, v in row.where.items()) or "—"
                print(f"      {row.name[:28]:<30} {row.object_type:<14} {where:<26} "
                      f"{row.existence}{mark}")
            print(f"    run {i + 1}  names {g['identities']}  conditions {g['conditions']}  "
                  f"invented {g['invented']}  sets {g['sets']}  residual {g['residual']}  "
                  f"rows {g['rows']} (want {want.rows})  folded {g['folded']}")
            tally["identities_ok"] += g["identities_ok"]
            tally["folded"] += g["folded"]
            tally["extra_rows"] += max(0, g["extra_rows"])
            tally["conditions_ok"] += g["conditions_ok"]
            tally["sets_ok"] += g["sets_ok"]
            tally["residual_ok"] += g["residual_ok"]
            tally["invented"] += g["invented"]
            tally["new"] += g["new"]
            tally["cells"] += 1

    c = max(tally["cells"], 1)
    print(f"\n{'=' * 104}")
    print(f"  cells                    {tally['cells']}")
    print(f"  named things found       {tally['identities_ok']}/{c}")
    print(f"  SURPLUS rows declared    {tally['extra_rows']}    (over-declaration)")
    print(f"  mentions FOLDED as refs  {tally['folded']}    (repeat mentions recognised)")
    print(f"  every condition found    {tally['conditions_ok']}/{c}")
    print(f"  groups declared as sets  {tally['sets_ok']}/{c}")
    print(f"  residual correct         {tally['residual_ok']}/{c}   "
          f"⇐ rung 11 is the only one that can score TRUE here")
    print(f"  conditions invented      {tally['invented']}    (P4 said under- beats over-fill)")
    print(f"  rows called NEW          {tally['new']}    (P5: near-zero means MY enum "
          f"ordering backfired)")


if __name__ == "__main__":
    main()
