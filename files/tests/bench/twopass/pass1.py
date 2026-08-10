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
    conditions: List[Dict[str, object]]   # DERIVED from the known-correct reading
    sets: int                             # how many declared things are GROUPS
    residual: bool                        # is any row settled at run time
    rows: int                             # how many things there really are — REPORTED only


def _conditions_from_goals(rung: int) -> List[Dict[str, object]]:
    """THE EXPECTED CONDITIONS, DERIVED FROM THE PROJECT'S OWN CORRECT READINGS.

    ⇒ **THE HAND-WRITTEN KEY WAS WRONG AND I ONLY SAW IT BY SCORING AGAINST IT.** I had ruled
      that a name is carried by the name field and is never a condition — so `{name: alpha}`
      counted as an INVENTED condition. But `tests.test_ghost_writer.GOALS`, the readings this
      project已 calls correct, says otherwise:

          rung 1   select {kind: vm, name: alpha}      <- the name IS in the select
          rung 9   select {kind: vm}                   <- and here it is NOT

      My key contradicted them in some places and agreed in others, which is exactly the state
      a hand-written key drifts into. Deriving it removes the judgement: whatever the correct
      reading filters on is what pass 1 must find.
    """
    from tests.bench.formula.slots import reduce as _reduce
    from tests.test_ghost_writer import GOALS
    out: List[Dict[str, object]] = []
    for goal in GOALS.get(rung, []):
        where = _reduce(goal).filled.get("filter") or {}
        for attr, value in where.items():
            row = {attr: value}
            if row not in out:
                out.append(row)
    return out


# ── THE ANSWER KEY. Conditions are DERIVED (above); the rest is hand-written. ──────────
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

# ⇒ THE CONDITIONS ARE NOW DERIVED, NOT DECLARED. Whatever the known-correct reading filters
#   on is what pass 1 must find — no hand-written judgement in between.
for _rung, _entry in list(EXPECTED.items()):
    EXPECTED[_rung] = _entry._replace(conditions=_conditions_from_goals(_rung))


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


def run_scanned(request: str, board: Optional[Board] = None, model=None, temp=0.0,
                timeout=180, trace: Optional[List] = None) -> List[S.Declared]:
    """PASS ONE, ANCHOR-AND-SCAN. The model points; the code reads; the world decides.

    Two model calls' worth of questions instead of four. The TYPE and the CONDITIONS are no
    longer asked at all — the noun gives the kind and the modifiers give the conditions, both
    from the manifest. What the model still supplies is the ANCHOR (14/14) and the EXISTENCE
    intent (85%, errors all in the safe direction).
    """
    from engines.channel import constrained
    from .scan import scan_all, conditions_from

    board = board or Board()

    def ask(question: str, built: dict):
        try:
            got = constrained(question, request, built,
                              model=model, temp=temp, timeout=timeout) or {}
            return got.get("answer")
        except Exception:
            return None

    from .scan import anchors_in, kinds_named
    # THE MANIFEST'S NOUNS ARE ANCHORS AND NEED NO ASKING. The model's answers are ADDED to
    # them, for the things the manifest cannot list — a pronoun-headed set, a bare name.
    from .scan import uncovered, scan
    said = ask(S.NAMES_Q, S.names_schema()) or []
    anchors = anchors_in(request, board) + [a for a in said if a.lower() in request.lower()]
    # ⇒ AND ANYTHING STILL UNCLAIMED IS A CANDIDATE OBJECT — TO A FIXPOINT.
    #
    #   `n1`, `golden`, `db` are not declared nouns, so nothing above reaches them, and rung 9
    #   — which contains no declared noun at all — produced an EMPTY reading until this
    #   existed. But one round is not enough: a word claimed in round 1 widens the covered
    #   text, which can reveal or absorb neighbours, and a word that only becomes claimable
    #   once its neighbour is claimed was never reached.
    #
    #   THE OPERATOR'S POINT, AND IT IS WHAT MAKES THE RESIDUE MEAN ANYTHING: an unclaimed word
    #   is ambiguous between "an object nobody named" and "a clause nobody read" ONLY UNTIL WE
    #   TRY TO CLAIM IT. Run it to a fixpoint and the ambiguity is gone — whatever is still
    #   unclaimed has been offered the chance and failed it, so it is a lost clause and gate 1
    #   may bounce it without guessing.
    for _round in range(4):
        claimed = [(g.start, g.end) for g in (scan(a, request, board) for a in anchors) if g]
        fresh = [w for w in uncovered(request, claimed, board) if w not in anchors]
        if not fresh:
            break
        anchors += fresh
    if trace is not None:
        trace.append(("rounds", _round + 1))
    present = kinds_named(request, board)
    if trace is not None:
        trace.append(("anchors", list(anchors)))

    rows: List[S.Declared] = []
    for anchor in anchors:
        seen = scan_all(anchor, request, board)
        if not seen:
            continue
        # ⇒⇒ A LATER MENTION MARKED **DISTINCT** IS A SECOND THING, NOT A REFERENCE.
        #
        #   The rule was *the first occurrence DECLARES and the rest are REFERENCES to it*,
        #   which is right for `web … web` and wrong for rung 6:
        #
        #       put the red ones together on their OWN network,
        #       and put the blue ones on a DIFFERENT network
        #
        #   `scan_all` finds both — [55,101) and [128,147) — and the second folded into the
        #   first as a mention of it. ONE network was declared where the request names TWO, and
        #   both groups went onto it: red and blue ended up TOGETHER, the exact opposite of what
        #   was asked, with only a residue complaint to show for it.
        #
        #   ⇒ **ENGLISH MARKS IT OVERTLY**, which is what makes this a lookup and not a
        #     judgement: `different`, `own`, `another`, `separate`, `other`, `second` all say
        #     *not the one just mentioned*. A closed class, the same standing as `COMPARATORS`.
        #   ⇒ AND ONLY WHERE THE ANCHOR NAMES A KIND. `ones` appears twice in rung 6, both
        #     times inside a span carrying a marker — *the red ones … their OWN network* and
        #     *the blue ones … a DIFFERENT network* — and declaring the second produced two
        #     junk `?` rows. A marker says the NETWORK is a different network; it says
        #     nothing about the pronoun that happens to share the clause.
        extra = [s for s in seen[1:] if s.kind is not None and _marks_distinct(s.span)]
        for first in [seen[0]] + extra:
            # ⇒ A KINDLESS SPAN THAT CONTAINS A PRONOUN IS A REFERENCE, NOT A THING.
            #   "create a vm named beta and then launch it" scans `it` outward to `launch it` —
            #   no noun, so no kind — and that became a row of its own instead of pointing at
            #   beta. The fold tested the row's NAME, which is the whole span, so a bare pronoun
            #   sitting inside it was never seen.
            if first.kind is None and rows:
                pronoun = next((w for w in str(first.span).lower().split()
                                if S._is_bare_pronoun(w.strip(".,'\""), request)), None)
                if pronoun:
                    at = len(rows) - 1          # the most recent declaration it could be about
                    kept = rows[at]
                    rows[at] = S.declare_from(kept.name, kept.object_type, kept.where,
                                              kept.existence, board,
                                              references=list(kept.references) + [first.span],
                                              count=kept.count, comparator=kept.comparator,
                                              span=kept.span, identity=kept.identity)
                    continue

            # ⇒ THE CONTEXTUAL KIND IS FOR PRONOUN-HEADED SETS AND FOR NOTHING ELSE.
            #
            #   It exists so *"the ones that do not answer"* takes the only kind the request talks
            #   about — a pro-form REFERS, so the kind is in the request even though the span has
            #   no noun. Applied to any kindless span it LAUNDERS JUNK INTO AN OBJECT: measured
            #   2026-08-08, *"create a vm named alpha and launch it, grubnash"* declared `grubnash`
            #   a vm and BOTH GATES RETURNED NOTHING. Gate 1 could not object — the OPERATOR said
            #   the word, and gate 1 catches what the MODEL invented. Gate 2 could not object —
            #   `vm` is a real kind. And `bounces()` never sees it, because the fixpoint claims the
            #   word and a claimed word is never left over.
            #
            #   So the rule now demands the EVIDENCE it was written for. Without a pro-form the
            #   kind stays `?` and gate 2 asks — which is the honest answer anyway, since only the
            #   lab can say whether `grubnash` is a machine name or noise.
            if first.kind is None and len(present) == 1 and _has_pronoun(first.span):
                first = first._replace(kind=present[0])

            # ⇒ A KINDLESS THING IS STILL A THING. Dropping it lost every bare proper name —
            #   db, core, dmz, n1, n2, n3, golden — and rung 9, which contains no declared noun at
            #   all, produced nothing whatever. The operator's rule: a bare item and a full one are
            #   the same until the WORLD says otherwise, so declare it and let gate 2 ask.
            # SPAN COLLISION IS THE FOLD, and only between DECLARATIONS.
            # ⇒ A ROW ON THE SAME PHRASE WINS OVER A ROW THAT MERELY OVERLAPS. Taking the FIRST
            #   overlapping row made the `core` anchor collide with the `every vm` row rather than
            #   with the `a network called core` row it belongs to — and rung 8 declared that
            #   network TWICE, once per anchor.
            clash = next((i for i, r in enumerate(rows)
                          if str(r.span).strip() == str(first.span).strip()), None)
            if clash is None:
                clash = next((i for i, r in enumerate(rows)
                              if r.span and first.collides(_span_of(r, request, board))), None)

            # ⇒⇒ A COLLISION IS NOT ALWAYS A FOLD, AND ASSUMING IT WAS ATE WHOLE OBJECTS.
            #
            #   *"clone golden into 3 new vms"* — `golden` has no noun after it, so its span runs
            #   to the clause boundary and SWALLOWS `3 new vms`. The two overlap, the fold merged
            #   them, and **the clone source vanished from the reading entirely**: rung 10 declares
            #   one row where the correct reading has two. Rung 8 lost its `core` network the same
            #   way. Both were invisible — a merged row looks like a read row.
            #
            #   ⇒ **THE TEST IS THE SPAN, NOT THE OVERLAP.** Two anchors on the SAME phrase are the
            #     same thing: *"create a network called lab"* anchored on `lab` and on `network`
            #     yields identical spans, which is the case the fold was built for. One span
            #     CONTAINING another is the opposite situation — the outer one over-reached, and
            #     the inner one has its own noun.
            if clash is not None:
                kept_span = _span_of(rows[clash], request, board)
                # ⇒ IDENTITY IS THE RECORDED SPAN TEXT, NEVER A RE-DERIVED ONE. `_span_of` re-scans
                #   using the row's whole phrase as an anchor, which can land on different offsets
                #   than the scan that declared it — so comparing offsets said "different" for two
                #   anchors on the same phrase and rung 8 declared `a network called core` TWICE.
                kept_kind = (rows[clash].kind
                             if rows[clash].object_type != UNKNOWN_KIND else None)
                identical = str(first.span).strip() == str(rows[clash].span).strip()
                same_kind = first.kind is not None and first.kind == kept_kind
                if not identical and not same_kind:
                    # ⇒ TRIM AGAINST THE KEPT ROW'S OWN RECORDED WORDS, found in the request. The
                    #   re-derived span scans outward again and comes back covering the SAME ground
                    #   as the over-reaching one, so nothing ever trimmed.
                    at = request.lower().find(str(rows[clash].span).strip().lower())
                    kept_start = at if at >= 0 else (kept_span.start if kept_span else -1)
                    kept_end = (at + len(str(rows[clash].span).strip())) if at >= 0 else (
                        kept_span.end if kept_span else -1)
                    if kept_start >= 0 and first.start < kept_start < first.end:
                        first = first._replace(end=kept_start,
                                               span=request[first.start:kept_start].strip())
                    elif kept_start >= 0 and first.start < kept_end < first.end:
                        first = first._replace(start=kept_end,
                                               span=request[kept_end:first.end].strip())
                    # ⇒ AND WHAT IS LEFT MUST STILL BE A THING. Trimming *"launch every vm that is
                    #   currently stopped"* leaves the bare verb `launch`, and declaring that as an
                    #   object cost rung 5 its SERVE — a verb belongs to pass 2 and may not stand
                    #   alone, which is the same rule gate 1 applies to leftovers.
                    from .scan import GRAMMAR, _operation_words
                    verbs = _operation_words(board)
                    left = [w.strip(".,'\"—–") for w in str(first.span).lower().split()]
                    if not any(w and w not in GRAMMAR and w not in verbs for w in left):
                        continue
                    clash = None

            if clash is not None:
                # ⇒ A COLLISION TAKES THE BETTER INFORMATION, NOT THE EARLIER. Both anchors cover
                #   the same phrase, but the kind is read at-or-before the anchor — so anchored on
                #   `2`, "2 vms labelled 'blue'" has NO noun in its head and comes back kindless,
                #   while anchored on `blue` the same span reads `vm`. Keeping whichever arrived
                #   first threw the kind away.
                kept = rows[clash]
                better_kind = (first.kind and kept.object_type == UNKNOWN_KIND)
                object_type = ((f"{first.kind}{S.SET_SUFFIX}" if _is_group(first) else first.kind)
                               if better_kind else kept.object_type)
                where = dict(kept.where)
                if better_kind:
                    where.update(conditions_from(first.modifiers, first.kind, board, first.span))
                rows[clash] = S.declare_from(kept.name, object_type, where,
                                             kept.existence, board,
                                             references=list(kept.references) + [anchor],
                                             count=kept.count if kept.count is not None
                                             else first.count,
                                             comparator=kept.comparator or first.comparator,
                                             span=kept.span)
                continue
            # ⇒⇒ A VALUE PHRASE IS NOT AN OBJECT. *"give them all the 'fleet' label"* was declared
            #   as a thing of unknown kind, so pass 2 was handed a HANDLE called `fleet` — and then
            #   `add_label(vms, fleet)` reads as *label these machines with that machine*, which
            #   gate 3 rejects. Rungs 4 and 13 both fail this way and neither is a pass 2 error.
            #
            #   ⇒ THE SIGNAL IS THE REQUEST'S OWN PUNCTUATION, not a judgement about what `fleet`
            #     might be. An ATTRIBUTE NAME beside a QUOTED word is the operator writing a value:
            #     `the 'fleet' label`, `labelled 'red'`. A bare word beside an attribute name is
            #     left alone, because only the lab can say whether it names something.
            if first.kind is None and _is_value_phrase(first.span, board):
                continue

            where = (conditions_from(first.modifiers, first.kind, board, first.span)
                     if first.kind else {})
            object_type = (f"{first.kind}{S.SET_SUFFIX}" if _is_group(first) else first.kind) \
                if first.kind else UNKNOWN_KIND
            existence = ask(S.EXISTENCE_Q.format(name=first.span, new=S.NEW,
                                                 existing=S.EXISTING),
                            S.existence_schema()) or S.EXISTING
            rows.append(S.declare_from(first.span, object_type, where, existence, board,
                                       references=[a.anchor for a in seen[1:]],
                                       count=first.count, comparator=first.comparator,
                                       span=first.span))
    return rows



# ⇒ THE DISTINCTNESS MARKERS — a CLOSED class of English, the same standing as `COMPARATORS`
#   and `ENUMERATORS`. Each one says *not the one just mentioned*, which is the only thing
#   that separates a second object from a second mention of the first.
DISTINCT = ("different", "another", "separate", "second", "other", "own", "its own",
            "their own", "a new", "fresh")


def _marks_distinct(span: str) -> bool:
    """Does this span say it is NOT the thing already declared?"""
    words = [w.strip(".,'\"—–").lower() for w in str(span).split()]
    return any(w in DISTINCT for w in words)


UNKNOWN_KIND = S.UNKNOWN_KIND       # DEFINED IN `schema`, beside the row it appears in


def settle_with_world(rows: List[S.Declared], world, board: Optional[Board] = None
                      ) -> List[S.Declared]:
    """THE WORLD DECIDES — apply the answer to the question gate 2 asks about a kindless row.

    ⇒ **THIS IS NOT A GATE REPAIRING SOMETHING, AND THE DISTINCTION IS THE WHOLE DESIGN.**
      Gate 2 asks *"the request does not say what 'db' is"*. It does not answer itself, and it
      must not ([[gorgon-gates-check-legality]]). This is the step AFTER the answer arrives —
      and when a lab is attached, the lab IS the answer, so nobody has to be interrupted.

    ⇒ **AND IT IS A LOOKUP, NOT AN INFERENCE.** `db` is a bare proper name; nothing in the
      words says it is a machine. The lab either holds a vm called `db` or it does not. Both
      the KIND and the KEY VALUE come back from that one query, which is why the row can go
      from `? {}` straight to `vm {name: db}` with nothing guessed in between.

    Rung 8 is the corpse: `put every vm on a network called core, except db — db goes on a
    network called dmz instead` wants `{name: db}` and `{network: dmz}`. The first is a
    DECLARATION and could never come from pass 2 (rule D1 — pass 2 may reference only what
    pass 1 declared); the second is an operation's effect and needs a declared target to
    attach to. So both waited on this.
    """
    from planner.gates import claims as _claims
    board = board or Board()
    if world is None:
        return rows
    out: List[S.Declared] = []
    for row in rows:
        if row.object_type != UNKNOWN_KIND:
            out.append(row)
            continue
        found = None
        # THE ROW'S OWN WORDS, LONGEST FIRST — a bare name is somewhere inside its span, and
        # the span may have picked up a verb or a connective on the way.
        words = [w.strip(".,'\"—–") for w in str(row.span or row.name).lower().split()]
        for word in sorted({w for w in words if w}, key=len, reverse=True):
            for kind in board.kinds:
                key = _claims.key_of(kind, board.kinds)
                if not key:
                    continue
                try:
                    if world.select({"kind": kind, key: word}):
                        found = (kind, key, word)
                        break
                except Exception:
                    continue
            if found:
                break
        if not found:
            out.append(row)
            continue
        kind, key, word = found
        where = dict(row.where)
        where.setdefault(key, word)
        out.append(S.declare_from(row.name, kind, where, row.existence, board,
                                  references=list(row.references), count=row.count,
                                  comparator=row.comparator, span=row.span, identity=word))
    return out

PLURAL_PRONOUNS = {"ones", "them", "they", "those", "these", "all", "both", "rest", "others"}


def _is_group(scanned) -> bool:
    """A thing is a GROUP when the request says so — by count, by plural, or by pronoun.

    Count alone was not enough: *"stop the ones that do not answer"* carries no enumerator and
    is plainly a set. The plural noun and the plural pronoun say it just as clearly.
    """
    if scanned.count == "all" or (isinstance(scanned.count, int) and scanned.count > 1):
        return True
    words = scanned.span.lower().split()

    # ⇒⇒ THE NOUN THAT NAMES THE KIND DECIDES ITS NUMBER — not any plural word in the span.
    #
    #   *"put the red ONES together on their own NETWORK"* was typed a `network_set`, because
    #   the pronoun `ones` sits in the span. But `ones` is the MACHINES; the network is one
    #   network. Rung 6 then offered pass 2 two handles called `networks` and `network` — a
    #   set that is not a set, beside a singular almost identical to it — and unsurprisingly
    #   both groups went onto the first.
    #
    #   ⇒ A PRONOUN DECIDES ONLY WHEN THERE IS NO NOUN TO ASK. Rung 11's *"the ones that do not
    #     answer"* has no noun at all — its kind comes from context — so there the pronoun IS
    #     the evidence, and that path is unchanged.
    # NOTE: read defensively — `test_a_possessive_is_not_a_plural` passes a lightweight
    # stub with only a `span`, and a bare attribute access broke it.
    if getattr(scanned, "kind", None):
        from .scan import _index
        nouns = _index(board_of(scanned))
        head = next((w.strip(".,'\"") for w in words
                     if nouns.get(w.strip(".,'\"")) == scanned.kind), None)
        if head:
            return _plural(head)

    if any(w.strip(".,'") in PLURAL_PRONOUNS and not _possessive(w) for w in words):
        return True
    return any(_plural(w) for w in words)


def board_of(_scanned):
    """The scan carries no board, and `_index` needs one. A default Board is the manifest."""
    return Board()


def _is_value_phrase(span: str, board: Board) -> bool:
    """Is this span the operator WRITING A VALUE rather than naming a thing?

    Two marks, and both must be present, because either alone is far too broad:

      * an ATTRIBUTE NAME the manifest declares — `label`, `status`, `os` — appears in it
      * and a QUOTED word sits beside it, which is how the request itself marks a literal

    `the 'fleet' label` and `labelled 'red'` qualify. `except db` does not — no attribute word.
    `a network called core` does not — it has a kind, so it never reaches here. And a BARE word
    beside an attribute name is deliberately left alone: nothing but the lab can say whether it
    names something, which is the whole of item 0.
    """
    from planner.ir import config as _config
    words = str(span).lower().split()
    attrs = set()
    for spec in (_config.KINDS or {}).values():
        if isinstance(spec, dict):
            attrs |= set(spec.get("attrs") or []) | set((spec.get("aliases") or {}).keys())
    # ⇒ MATCH AN ATTRIBUTE THE SAME WAY `conditions_from` DOES, in both directions. `labelled`
    #   stems to `labell`, which no attribute equals — and a one-way test missed the commonest
    #   descriptor in the whole corpus. The length guards are that function's, for the same
    #   reason: a two-letter cue must match exactly or `ones` starts matching `on`.
    def _is_attr(word: str) -> bool:
        stem = _stem_of(word)
        return any(word == cue or stem == cue
                   or (len(cue) >= 4 and len(stem) >= 3
                       and (cue.startswith(stem) or stem.startswith(cue)))
                   for cue in attrs)

    has_attr = any(_is_attr(w.strip(".,'\"")) for w in words)
    has_quote = any(w.strip(".,").startswith(("'", '"')) and len(w.strip(".,'\"")) > 1
                    for w in words)
    return has_attr and has_quote


def _stem_of(word: str) -> str:
    from .scan import _stem
    return _stem(word)


def _has_pronoun(span: str) -> bool:
    """Does this span contain a pro-form at all — restricted or bare?

    ⇒ **NOT `S._is_bare_pronoun`, AND THE DIFFERENCE IS RUNG 11.** That helper asks whether a
      pro-form stands ALONE, and answers False for *"the ones that do not answer"* precisely
      because `that` restricts it. Here the question is the opposite one: does this span REFER
      at all? A restricted pro-form refers just as hard as a bare one — it is the whole reason
      the contextual kind exists.

    Both lists are consulted because they were built for different jobs: `PRONOUNS` for the
    singular reference that folds into an earlier row, `PLURAL_PRONOUNS` for the group that
    heads a set.
    """
    words = [w.strip(".,'\"") for w in str(span).lower().split()]
    return any((w in PLURAL_PRONOUNS or w in S.PRONOUNS) and not _possessive(raw)
               for raw, w in zip(str(span).lower().split(), words))


def _possessive(word: str) -> bool:
    """`one's` is not `ones`. The apostrophe is the whole difference and it decides SET-NESS.

    The operator, 2026-08-08: *"'ones' (a set) versus 'one's' (one that is) — it needs the
    ability to know the difference."* Right, and without this a possessive reads as a plural:
    *"the machine's network"* was being declared a GROUP of machines.
    """
    stripped = word.strip(".,")
    return "'" in stripped and stripped.endswith("s") and stripped.rfind("'") == len(stripped) - 2


def _plural(word: str) -> bool:
    w = word.strip(".,'\"")
    if _possessive(word) or len(w) <= 3:
        return False
    return w.endswith("s") and not w.endswith("ss") and w not in {"its", "this", "has", "was"}


def _span_of(row: S.Declared, request: str, board: Board):
    from .scan import scan
    return scan(row.span, request, board) or scan(row.name, request, board)


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
    ap.add_argument("--scanned", action="store_true",
                    help="ANCHOR-AND-SCAN: the model points, the code reads, the world decides")
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
          f"{'ANCHOR-AND-SCAN' if args.scanned else ('PAIRED name+type' if args.paired else 'separate questions')}"
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
            rows = (run_scanned(want.request, board=board, model=args.model, trace=trace)
                    if args.scanned else
                    run_pass1(want.request, board=board, model=args.model, trace=trace,
                              paired=args.paired, fold=not args.no_fold,
                              expand_names=not args.no_expand,
                              forced=args.forced_conditions))
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
