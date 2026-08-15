"""ITEM 3 — RUN PASS ONE AGAINST THE MODEL. The first real number for the new design.

    PYTHONPATH=. python3 -m orchestrator.seam.pass1            # all 14 rungs
    PYTHONPATH=. python3 -m orchestrator.seam.pass1 --only 11
    PYTHONPATH=. python3 -m orchestrator.seam.pass1 --runs 3

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
import re
from collections import Counter
from typing import Dict, List, NamedTuple, Optional

from planner.formula.legal import Board
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
    from planner.formula.slots import reduce as _reduce
    # ⇒⇒ **THE CORPUS IS THE BENCH'S AND THIS MODULE IS PRODUCTION'S — so the import is GUARDED,
    #   exactly as `rig.staged_seams` guards its own reach into the bench.** Moving this package
    #   out of `tests/` on 2026-08-13 made the coupling visible for the first time: `EXPECTED` is
    #   the RUNG CORPUS, and it had been living inside a production module because production and
    #   bench shared a directory. A sparse checkout, a shipped install, or anyone running without
    #   the test tree gets an EMPTY expectation table rather than an ImportError — the corpus is
    #   what GRADES pass 1, never what pass 1 needs to run.
    try:
        from tests.test_ghost_writer import GOALS
    except Exception:
        return []
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
    from .scan import conditions_from, existence_from_determiner, scan_all

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
            # ⇒⇒ THE DETERMINER IS READ FIRST, AND THE MODEL IS ONLY ASKED WHAT IT DOES NOT
            #   SETTLE. `existence` is the weakest field pass 1 has (85%, every error toward
            #   NEW) and rung 6's verdict was flipping on it — BOUNCE, BOUNCE, ASK across three
            #   runs with byte-identical operations. A determiner is not a guess.
            #   ⇒ AND THE CALL IS SKIPPED ENTIRELY WHEN THE SPAN SETTLES ITSELF, so this is
            #     cheaper as well as steadier — the doctrine is THE MODEL POINTS, THE CODE
            #     READS, and here the code can read it outright.
            existence = existence_from_determiner(first.span)
            if existence is None:
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
        #
        # ⇒⇒ **AND THE ORDER MUST BE TOTAL, WHICH IT WAS NOT UNTIL 2026-08-13.** This read
        #   `sorted({w for w in words if w}, key=len, reverse=True)` — a SET, ordered by
        #   length ALONE. Two candidates of equal length therefore kept the set's iteration
        #   order, which python varies with `PYTHONHASHSEED`, and the first one the lab
        #   recognises WINS THE ROW'S IDENTITY. Measured on *"give n1 the n2 label"* against
        #   a lab holding both:
        #
        #       seed 0, 6   where={'name': 'n1'}  ->  handle n1  ->  BOUNCE
        #       seed 2, 3   where={'name': 'n2'}  ->  handle n2  ->  REFUSE  (no-such-handle)
        #
        #   Same request, same operations, opposite verdict, decided by nothing. It is not a
        #   tie-break detail: a row's IDENTITY is what pass 2 addresses by handle, so an
        #   unstable identity makes a correct operation unaddressable.
        #
        # ⇒ THE TIE-BREAK IS FIRST MENTION, and it is not arbitrary either. Among equally
        #   specific candidates the span's own order is the evidence available — in *"give n1
        #   the n2 label"* the thing acted upon is named first and the modifier follows, which
        #   is the ordinary English shape. Length still leads, because a longer match is a
        #   more specific one.
        words = [w.strip(".,'\"—–") for w in str(row.span or row.name).lower().split()]
        first_at = {}
        for i, w in enumerate(words):
            if w and w not in first_at:
                first_at[w] = i
        for word in sorted(first_at, key=lambda w: (-len(w), first_at[w])):
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


EXCLUDERS = ("except", "excluding", "besides", "apart from", "other than", "but not")


def _affording_kinds(board: Board) -> dict:
    """{verb: {kinds that can be asked to do it}} — READ off the manifest, never listed.

    A probe's own fact and the tool that gathers it both count: `observed.alive.by =
    guest_ping` makes both `alive` and `ping` verbs a vm affords.
    """
    from planner.ir import config as _config
    out: dict = {}
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        verbs = set()
        for group in ("setters", "unsetters", "acts", "creators"):
            for name in (spec.get(group) or {}):
                verbs.add(str(name).split("_")[0].lower())
        for fact, meta in (spec.get("observed") or {}).items():
            verbs.add(str(fact).lower())
            by = (meta or {}).get("by")
            if by:
                verbs.add(str(by).split("_")[-1].lower())
        for v in verbs:
            out.setdefault(v, set()).add(kind)
    return out


def settle_by_affordance(rows: List[S.Declared], request: str,
                         board: Optional[Board] = None) -> List[S.Declared]:
    """A thing asked to do something only one kind can do IS that kind.

    ⇒⇒ **THE OPERATOR, 2026-08-11: *"rung 9 is wrong to be an ASK, since the only thing that can
      ping is a vm."*** Right, and the manifest says so — `alive` is observed on `vm` and on
      nothing else, gathered by `guest_ping`. *"make sure n1, n2 and n3 can all ping each other"*
      therefore SAYS what n1 is, and asking *"what is n1?"* is asking a question the request
      already answered.

    ⇒ **THIS IS THE AFFORDANCE IDEA DONE AS A LOOKUP RATHER THAN A QUESTION.** Asked of the
      MODEL it was vacuous — every word came back yes for every kind ([[gorgon-unfamiliar-nouns]]).
      Asked of the MANIFEST it is arithmetic: which kinds declare this verb, and is there exactly
      one? **The harness is an actioneer — a kind IS what can be done to it** — and that table
      was in the manifest the whole time.

    ⇒ **ZERO OR SEVERAL AFFORDING KINDS SETTLES NOTHING.** `create` belongs to five kinds and
      says nothing; only a verb unique to one kind carries a reading. Same zero/one/several
      honesty as everywhere else, and it is why this cannot quietly type a row as `vm` because
      the request happened to mention a common verb.

    ⇒ ⚠ AND IT ONLY EVER FILLS A KINDLESS ROW. A row the nouns, the lab or the routing settled
      already is left exactly as it was — this adds a reading, it never overrides one.
    """
    board = board or Board()
    afford = _affording_kinds(board)
    from planner.gates import claims as _claims
    from .scan import GRAMMAR, _operation_words

    # ⇒⇒ **A VERB SETTLES THE SPANS IN ITS OWN CLAUSE, NOT EVERY SPAN IN THE REQUEST.**
    #   Added 2026-08-14. This read the affordance off `str(request).split()`, so ONE verb
    #   unique to one kind typed EVERY kindless row in the sentence as that kind — and a
    #   request whose lab-facing clause says `stop` typed its greeting as a machine, which is
    #   how gate 2 came to ask whether to create one. The rule is right and its SCOPE was the
    #   whole sentence.
    #
    #   ⇒ **THE CLAUSE IS THE SCOPE BECAUSE THE SPAN IS TOO NARROW.** Rung 9's spans are
    #     *"make sure n1"*, *"n2"* and *"n3 can all ping each other"* — only the last contains
    #     `ping`, so a span-scoped rule would settle one row of three and leave the rung
    #     exactly as broken as it was before this function existed. The clause holds all three.
    #
    #   ⇒ **AND A SPAN NO CLAUSE CONTAINS SETTLES NOTHING**, rather than falling back to the
    #     request — a fallback is the old behaviour wearing a guard.
    from .pass2 import clauses_of
    _clauses = clauses_of(request) or [str(request)]

    def _kind_for(row) -> Optional[str]:
        """The kind afforded by the clause this row's span sits in, or None."""
        span = str(row.span or row.name).lower().strip()
        holder = next((c for c in _clauses if span and span in c.lower()), None)
        if holder is None:
            return None
        here = {w.strip(".,'\"—–?!").lower() for w in holder.split()}
        found = {next(iter(afford[w])) for w in here
                 if afford.get(w) and len(afford[w]) == 1}
        return found.pop() if len(found) == 1 else None

    # ⇒⇒ **AND THE KIND MUST ARRIVE WITH THE NAME, OR SETTLING IT DESTROYS THE ROW.**
    #   Measured 2026-08-11: typing `n1`/`n2`/`n3` as `vm` and stopping there renamed their
    #   handles to `vm`, `vm_2`, `vm_3` — because `handle_for` gives a KINDLESS row its own word
    #   and a typed row its kind. Rung 9 went from 3 clean declarations to three
    #   indistinguishable enum members, 9 operations and 21 findings.
    #   ⇒ `_stem_for`'s own comment warned about precisely this shape one layer down: *"three
    #     indistinguishable enum members for three distinct objects, the surest way to make the
    #     model pick the wrong one."* **A reading that removes information is not a settlement.**
    #   ⇒ SO THE ROW'S OWN WORD BECOMES ITS KEY VALUE — `n1` is not merely a vm, it is the vm
    #     NAMED `n1`, which is what the request says and what keeps the handle stable.
    verbs = _operation_words(board)
    out = []
    for row in rows:
        if row.object_type != UNKNOWN_KIND:
            out.append(row)
            continue
        kind = _kind_for(row)
        if not kind:
            out.append(row)
            continue
        key = _claims.key_of(kind, board.kinds)
        where = dict(row.where or {})
        if key and not where.get(key):
            span = [w.strip(".,'\"—–") for w in str(row.span or row.name).lower().split()]
            free = [w for w in span if w and w not in GRAMMAR and w not in verbs]
            if free:
                where[key] = free[-1]
        out.append(row._replace(object_type=kind, where=where))
    return out


def _sourcing_verbs(board: Board) -> set:
    """Creator verbs that take a SOURCE they do not make — read off the manifest's `from`."""
    from planner.ir import config as _config
    out = set()
    for spec in (_config.KINDS or {}).values():
        if not isinstance(spec, dict):
            continue
        for name, creator in (spec.get("creators") or {}).items():
            if isinstance(creator, dict) and creator.get("from"):
                out.add(str(name).lower())
    return out


def settle_sources(rows: List[S.Declared], board: Optional[Board] = None) -> List[S.Declared]:
    """What a CLONE is cloned FROM already exists. It is never the thing being created.

    ⇒⇒ **RUNG 10, MEASURED 2026-08-11.** *"clone golden into 3 new vms"* declared `golden` with
      `existence=NEW`, so gate 2 asked *"you asked to create 'golden' and there is already one"*
      — **a question resting on a premise the request never contained.** Nothing asked to create
      `golden`; it is what the copy is taken FROM.

    ⇒ **AND THE RIGHT VERDICT WAS HIDING A REAL HOLE.** That ASK only appears because the lab
      happens to hold a `golden`. With an empty lab nothing objects at all: gate 3 exempts a
      creator's own target from needing an establisher, so `clone_vm(golden)` reads as *golden is
      what I am making* and a clone from a nonexistent source serves clean.

    ⇒ **THE MANIFEST HAS SAID SO ALL ALONG** — `creators.clone = {key: new_name, from:
      source_name}`. The source role is DECLARED and nothing read it, which is the same shape as
      `makeable`, `create_args`, `_creator_args` and the IR's `not`.

    ⇒ AND IT IS A MANIFEST LOOKUP, NOT A VERB LIST: `_sourcing_verbs` reads which creators
      declare a `from`, so a lab that gains one gains this for free (rule W5). The span carries
      the verb — `golden`'s span IS *"clone golden into"* — so nothing has to be inferred.
    """
    board = board or Board()
    verbs = _sourcing_verbs(board)
    if not verbs:
        return rows
    out = []
    for row in rows:
        span = str(row.span or row.name).lower()
        words = {w.strip(".,'\"—–") for w in span.split()}
        # ⇒ THE PRODUCT IS EXEMPT, AND IT SAYS SO ITSELF. *"3 NEW vms"* carries the novelty
        #   marker; the source never does. Without this the whole clause would settle EXISTING
        #   and the thing being made would stop being made.
        from .scan import NOVEL
        if row.existence == S.NEW and (words & verbs) and not (words & NOVEL):
            out.append(row._replace(existence=S.EXISTING))
            continue
        out.append(row)
    return out


def agent_name() -> str:
    """The active agent's own name, without its bundle extension. `doorman` by default.

    ⇒ **THE SYSTEM HAS ALWAYS KNOWN THIS AND THE SEAM COULD NOT SEE IT.** `shared.agent_select`
      resolves it from the env var, then the persisted selection, then the shipped default —
      and every consumer so far has been a CLI command. Read here rather than passed in,
      because the reading is about the request and the agent is not a parameter of it.
    """
    try:
        from shared import agent_select as _sel
        return str(_sel.resolve()).rsplit(".", 1)[0].strip().lower()
    except Exception:
        return ""


def consume_self_address(rows: List[S.Declared], board: Optional[Board] = None,
                         world=None) -> List[S.Declared]:
    """A span that names the AGENT is being ADDRESSED, not declared.

    ⇒⇒ **THE OPERATOR, 2026-08-14: *"gate 2 is a world check, and we have nothing to check for
      the agent's name."*** *"good morning doorman, …"* came back as a declared row, was typed
      `vm` by the affordance rule, and gate 2 asked the only question it could — *"'doorman' is
      referred to as if it exists and the lab has none — should it be created?"* Correct for
      what it was shown, and the wrong question: the lab has no `doorman` because `doorman` is
      **who was being spoken to**.

    ⇒ **THE WORLD MODEL HAS NO CATEGORY FOR THE CONVERSATION** — it knows machines, networks
      and snapshots, not the agent, the operator or the request. This closes the tractable
      part of that: the agent's own name. What is left — *"don't start any changes"*, *"how do
      i stop"* — names nothing in any world and needs the structural answer, not a lookup.

    ⇒ **AND IT IS THE ALLOWED KIND OF FACT** ([[gorgon-encyclopedia]]'s rule): *never write down
      what the model already knows better than you; always write down what it CANNOT know.* Its
      own name is the second — unknowable to the model, already declared by the system, and
      fixable by teaching. That is exactly the test that permits the Encyclopedia and forbids a
      stop-word list.

    ⇒ ⚠ **THE LAB STILL WINS.** A machine really called `doorman` is a machine — the row is kept
      whenever the world holds one by that name. So this can only ever remove a row nothing in
      the lab accounts for, which is the same world-first discipline `lab_has` already uses.
      With NO world it changes nothing, deliberately: absence of a lab is not evidence.

    ⇒ **AND ONLY A KINDLESS ROW**, the same guard `consume_reciprocal` keeps. A row the nouns
      or the lab already settled is a reading somebody made; this only ever drops one nobody
      could.
    """
    name = agent_name()
    if not name or world is None:
        return rows
    out = []
    for row in rows:
        span = str(row.span or row.name).lower()
        names_me = row.object_type == S.UNKNOWN_KIND and re.search(rf"\b{re.escape(name)}\b", span)
        if names_me and not _lab_holds(name, world, board):
            continue
        out.append(row)
    return out


def settle_from_archive(rows: List[S.Declared], board: Optional[Board] = None,
                        archive=None) -> List[S.Declared]:
    """A row nothing live could settle, settled by what the lab was TAUGHT.

    ⇒⇒ **STEP 2 OF THE SETTLING LADDER, AND IT IS THE ONLY ONE THAT GROWS WITHOUT CORPUS.**

        1  the manifest's `nouns`   the built-in vocabulary       lookup
        2  THE ARCHIVE              what is known / was told      lookup   <- this
        3  the lab                  what exists right now         lookup
        4  the ASK                  the operator settles it       -> written back into 2

    ⇒ **IT RUNS AFTER THE WORLD, NOT BEFORE, AND THAT IS THE SAFETY RULE RATHER THAN THE
      LISTING ORDER.** [[gorgon-encyclopedia]]: *"a remembered fact can only fill a row nothing
      live settled. A stale memory must never beat the world."* So this touches KINDLESS rows
      only — it can add a reading and can never replace one.

    ⇒ **AND IT IS INERT UNTIL A PERSON RATIFIES SOMETHING.** `known()` returns ratified-and-told
      entries only, so an empty archive — which is every archive until an operator signs an
      entry — makes this a no-op. That is why it can be wired without moving any measurement:
      the ladder is unchanged because there is nothing in the store, by construction rather
      than by luck.
    """
    from .archive import ARCHIVE
    store = ARCHIVE if archive is None else archive
    out = []
    for row in rows:
        if row.object_type != S.UNKNOWN_KIND:
            out.append(row)                    # the manifest or the lab already answered
            continue
        # ⇒⇒ **THE WORD, NOT THE PHRASE — AND IT IS `issues.word_of` THAT KNOWS WHICH.** The
        #   first cut of this looked the row's NAME up in the archive, and a row is named by
        #   the phrase that produced it: the real reading of *"create a jumpbox named alpha"*
        #   declares `a jumpbox named alpha`. So a ratified entry for `jumpbox` matched
        #   nothing, and the whole teach-then-settle loop would have silently never closed.
        #
        #   ⇒ **THAT IS THE EXACT DEFECT THE LEDGER ALREADY PAID FOR** — its own docstring:
        #     *"an issue was filed under `'a jumpbox named bastion'`, so answering 'a jumpbox
        #     is a vm' matched nothing and the next request learned nothing."* One rule for
        #     phrase-to-word, asked rather than re-derived, or the two stores drift apart on
        #     the one key they must agree on.
        from .issues import word_of
        word = word_of(str(row.span or row.name or ""), board)
        kind = store.kind_of(word) if word else None
        if kind and kind in (board or Board()).kinds:
            out.append(row._replace(object_type=kind,
                                    settled=S.settled_of(kind, row.where or {}, board)))
            continue
        out.append(row)
    return out


def consume_meta_control(rows: List[S.Declared], request: str,
                         board: Optional[Board] = None, world=None) -> List[S.Declared]:
    """A clause about the CONVERSATION declares nothing. Its spans are not things.

    ⇒⇒ **`consume_self_address` NAMED THIS CASE AS THE ONE IT COULD NOT CLOSE:** *"What is left
      — 'don't start any changes', 'how do i stop' — names nothing in any world and needs THE
      STRUCTURAL ANSWER, not a lookup."* The structural answer is `speech_act`, and this is it.

    ⇒ **FOUND BY POINTING THE NEW `--seam` DOOR AT THE OPERATOR'S OWN N3 EXAMPLE**, which is
      what an opt-in door is for. *"don't start any changes, but create a vm named alpha"*
      declared `alpha`, `changes` AND `changes_2`, and asked four questions about them:

          the request does not say what "don't start any changes" is
          the request does not say what 'any changes' is
          "don't start any changes" is referred to as if it exists …
          'any changes' is referred to as if it exists …

      Every one correct for what it was shown, and every one about a clause that was already
      read as an instruction NOT TO ACT. The real finding — that the program was held — sat
      underneath four spurious ones, which is the misdirection the residue accounting was
      fixed for on rung 6.

    ⇒ **THE LAB STILL WINS, exactly as it does for the agent's name.** A machine really called
      `changes` is a machine, and its row is kept. So this can only remove a row nothing in the
      world accounts for — and with no world it removes nothing, because absence of a lab is
      not evidence.

    ⇒ **AND ONLY A KINDLESS ROW**, the guard `consume_reciprocal` and `consume_self_address`
      both keep. A row the nouns or the lab already settled is a reading somebody made; this
      drops only ones nobody could.
    """
    from . import speech_act
    held = [c.strip().lower() for c, act in speech_act.read(request, board, world)
            if act == speech_act.META_CONTROL]
    if not held:
        return rows
    out = []
    for row in rows:
        span = str(row.span or row.name).strip().lower()
        inside = span and any(span in clause for clause in held)
        if (inside and row.object_type == S.UNKNOWN_KIND
                and not _lab_holds(str(row.name), world, board)):
            continue
        out.append(row)
    return out


def _lab_holds(word: str, world, board: Optional[Board] = None) -> bool:
    """Does the lab hold anything keyed by this word? The same question `residue.lab_has` asks."""
    from .residue import lab_has
    return bool(lab_has(word, world, board=board or Board()))


def consume_reciprocal(rows: List[S.Declared], board: Optional[Board] = None
                       ) -> List[S.Declared]:
    """A reciprocal clause is a PREDICATE, not an object. It must not be declared as a thing.

    ⇒⇒ **RUNG 13, MEASURED 2026-08-11.** *"...and make sure they all ping each other"* came back
      as a declared row — `thing`, span *"all ping each other"* — and gate 2 asked, correctly
      for what it was shown, *"the request does not say what 'all ping each other' is."* The
      clause states a RELATION that must hold; there is no object in it to declare.

    ⇒ **IT IS THE SAME DEFECT AS `except db` ARRIVING AS A FLOATING ROW** — a clause that is not
      an object being declared as one, and then nothing able to make sense of it. There the fix
      was to attach it to the set it narrows; here it is consumed by the GOAL
      (`gate4.goals_of` reads the reciprocal directly off the request).

    ⇒ **AND THE GUARD IS THAT IT NAMES NO KIND.** Anchor-and-scan's rule stands — a bare item is
      still a thing, and a kindless row is normally declared so gate 2 can ask. What is dropped
      here is narrower: a row with NO settled kind whose span carries a reciprocal pronoun,
      which is a predicate however you read it. Rung 9's `n1`, `n2`, `n3` have their own spans
      and are untouched, so it keeps asking *what is n1?* — the answer that rung needs.
    """
    from .gate4 import RECIPROCAL
    from .scan import GRAMMAR, _operation_words
    board = board or Board()
    verbs = _operation_words(board)
    out = []
    for row in rows:
        span = str(row.span or row.name).lower()
        if row.object_type != UNKNOWN_KIND or not any(r in span for r in RECIPROCAL):
            out.append(row)
            continue
        # ⇒⇒ **THE SPAN MUST BE *NOTHING BUT* THE PREDICATE — "CONTAINS ONE" IS TOO BROAD, AND
        #   IT COST RUNG 9.** First attempt dropped any kindless row whose span held a
        #   reciprocal; rung 9's third machine has the span *"n3 can all ping each other"*, so
        #   `n3` was eaten, the rung lost a declaration and a CORRECT ASK became a WRONG BOUNCE.
        #   Second time today a guard written one notch too wide swallowed a real finding.
        #
        #   ⇒ SO WHAT IS LEFT AFTER REMOVING THE RECIPROCAL, THE GRAMMAR AND THE VERBS DECIDES.
        #     Nothing left -> the span is a predicate and nothing else. Anything left — `n3` —
        #     is an object the operator named, and it stays.
        rest = span
        for r in RECIPROCAL:
            rest = rest.replace(r, " ")
        words = [w.strip(".,'\"—–") for w in rest.split()]
        if any(w and w not in GRAMMAR and w not in verbs for w in words):
            out.append(row)                # an object hides in here; not ours to drop
    return out


def attach_exclusions(rows: List[S.Declared], board: Optional[Board] = None
                      ) -> List[S.Declared]:
    """An `except X` clause becomes a CONDITION ON THE SET, not a row standing on its own.

    ⇒⇒ **RUNG 8's REAL DEFECT, AND THE ASK WAS THE ONLY THING STANDING IN FRONT OF IT.**
      *"put every vm on a network called core, except db — db goes on a network called dmz"*
      declared `every vm {network: core}` and, separately, `except db`. Nothing joined them, so
      the set still meant EVERY vm and `add_vm_to_network(core_vms, core)` would have put `db`
      on **both** networks. `linguistics.unexpressed-exclusion` detected it and could not fix
      it — a detector in front of a hole.

    ⇒ **THE OPERATOR'S SHAPE, 2026-08-11:** *"it needs to produce a set, `all_vms_but_db`, which
      is a legal set, and then put db in its own set… and then do the other part, the new
      network."* So the excluded thing keeps its own row — later clauses refer to it, and rung
      8's second half operates on it — and the SET it was taken out of records the subtraction.

    ⇒ **THE EXCLUDED ROW IS NOT CONSUMED.** Deleting it would break `db goes on dmz`, which is
      the whole second clause. One thing, two roles: absent from one set, the subject of the
      next step.
    """
    board = board or Board()
    out = list(rows)
    for i, row in enumerate(out):
        span = str(row.span or row.name).strip().lower()
        if not any(span.startswith(w) for w in EXCLUDERS):
            continue
        # THE SET IT COMES OUT OF IS THE NEAREST PRECEDING ONE OF ITS OWN KIND. An exclusion is
        # written directly after what it narrows, which is why proximity is the rule and not a
        # guess — `except` binds to the phrase it follows.
        for j in range(i - 1, -1, -1):
            host = out[j]
            if not host.is_set or (row.kind not in (host.kind, S.UNKNOWN_KIND)):
                continue
            # ⇒⇒ THE EXCLUDED ROW'S OWN CONDITIONS **ARE** THE FILTER. `except db` settles to
            #   `vm {name: db}`, so the carve-out is `{name: db}` with nothing constructed;
            #   *"except the running ones"* would settle to `{status: running}` and work the
            #   same way. **Storing a NAME would have handled only the first of those** — an
            #   exclusion is by predicate, and the predicate is already sitting on the row.
            carve = dict(row.where or {})
            if not carve:
                key = _key_of(row.kind, board)
                named = row.identity or row.name
                carve = {key: str(named)} if key and named else {}
            if carve and carve not in [dict(f) for f in host.excludes]:
                out[j] = host._replace(excludes=tuple(host.excludes) + (carve,))
            break
    return out


def _key_of(kind: str, board: Board):
    from planner.gates import claims as _claims
    return _claims.key_of(kind, board.kinds) if kind in board.kinds else None


def settle_with_answers(rows: List[S.Declared], answers, board: Optional[Board] = None,
                        world=None):
    """Apply what the OPERATOR said a word is. The fourth settler, and the only one with a
    person behind it.

    ⇒⇒ **THE LADDER ALREADY HAD THREE AND THIS IS THE ONE IT WAS MISSING.** `run_scanned` settles
      from the manifest's nouns, `settle_with_world` from the lab, `settle_by_affordance` from
      what the request asks the thing to DO — and when all three fail, gate 2 asks. Until now the
      answer had nowhere to go: an ask was prose and `run()` took no answers, so the same
      question could be asked every time forever.

    ⇒ **IT RUNS LAST, AND THAT ORDERING IS THE SAFETY PROPERTY.** A word the manifest, the lab or
      the request already settled is NOT overridden — this only ever fills a row that reached the
      end unsettled. An operator answer that could overwrite a lookup would make a stale
      Encyclopedia entry stronger than the live world.

    ⇒ **`answers` IS KEYED BY THE ROW, NOT BY THE WORD.** `asking.answered` resolves which
      question an operator's word was about and hands this keys that already name rows. Two
      contracts on purpose: one decides WHICH question is being answered, this one applies it.

    ⇒ **AN ANSWER THAT NAMES NO KIND IS DECLINED, NOT GUESSED AT.** *"a grubnash is a computer"*
      settles nothing unless `computer` is a kind this lab has — and saying so is the honest
      answer, the same three-valued honesty a kindless row already has. Better to ask again than
      to type a row from a word nobody can act on ([[gorgon-unfamiliar-nouns]]).
    """
    board = board or Board()
    conflicts: List[str] = []
    if not answers:
        return rows, conflicts
    from planner.gates import claims as _claims

    from . import reading_answers as _reading

    def _kind_named(said):
        # ⇒ READ BY PASS 1, NOT SCANNED FOR. A substring scan over kind names stood here and was
        #   wrong three times in seven on ordinary English — it read *"not a vm"* as `vm`, a
        #   simile as an identity, and *"a vm or a network"* as `vm`. See `reading_answers`.
        kind, _why = _reading.settle(said, board, world)
        return kind

    KIND_RULES = {"kind-not-settled", "no-such-kind", "unknown-kind", ""}
    EXISTS_RULES = {"not-there", "already-there"}
    out: List[S.Declared] = []
    for row in rows:
        got = answers.get(str(row.name).strip().lower())
        if not got:
            out.append(row)
            continue
        rule, said = got if isinstance(got, tuple) else ("", got)

        # ⇒⇒ **AN EXISTENCE ANSWER, WHICH IS THE ONE THE OPERATOR ACTUALLY MEETS.** Added
        #   2026-08-13 after an end-to-end demo: asked to *"launch every jumpbox"*, the chain
        #   never needed a KIND answer — affordance typed `jumpbox` as a vm from the verb — and
        #   the question that survived was *"should it be created?"*, which had no settler at
        #   all. **The write-back was wired to the rules that rarely fire.**
        #
        #   ⇒ SAYING YES SETS `NEW`, AND NOTHING ELSE. It does not add a step: `derive_creators`
        #     already supplies the maker for a NEW row that something depends on, and duplicating
        #     that here would be a second answer to a question arithmetic already answers.
        #   ⇒ SAYING NO LEAVES THE ROW EXACTLY AS IT WAS, so gate 3 still reports that nothing
        #     establishes it. A refusal to create is not a licence to proceed.
        if rule in EXISTS_RULES:
            wants = _reading.yes_no(said)
            if wants is None:
                conflicts.append(
                    f"you were asked whether {row.name!r} should be created and said {said!r}, "
                    f"which reads as neither yes nor no — nothing was changed")
            elif wants:
                # ⇒ SANCTIONED, not merely NEW. `derive_creators` refuses to mint anything NAMED
                #   because the MODEL's `existence` errors toward NEW and a wrong one would build
                #   a second `core`. That guard is about WHO SAID NEW — and the operator just did.
                out.append(S.declare_from(row.name, row.object_type, dict(row.where), S.NEW,
                                          board, references=list(row.references),
                                          count=row.count, comparator=row.comparator,
                                          span=row.span, identity=row.name, sanctioned=True))
                continue
            out.append(row)
            continue
        if rule not in KIND_RULES:
            out.append(row)               # a rule this settler does not own — untouched
            continue
        # ⇒⇒ **WE CANNOT GROUND AN ANSWER. WE CAN SEE WHEN IT CONFLICTS.** The operator,
        #   2026-08-13: *"we can't really ground what the user response is … but generally yes
        #   we can see if the answers conflict."* Exactly — an answer is free text and nothing
        #   here can check whether it is TRUE. Consistency is a different question and it is
        #   answerable, so the two conflicts below are DETECTED AND SAID rather than swallowed.
        #   Silently declining an answer is the same defect as silently dropping a step: the
        #   operator did something and nothing told them what became of it.
        if row.object_type != UNKNOWN_KIND:
            claimed = _kind_named(said)
            if claimed and claimed != row.object_type:
                conflicts.append(
                    f"you said {row.name!r} is a {claimed}, and it is already settled as a "
                    f"{row.object_type} by the lab or the request — the world's answer stands, "
                    f"so nothing was changed")
            out.append(row)
            continue
        kind = _kind_named(said)
        if not kind:
            conflicts.append(
                f"you said {row.name!r} is {str(said)!r}, and that names no kind this lab has "
                f"({', '.join(sorted(board.kinds))}) — it is still unsettled")
            out.append(row)               # named no kind we have — still unsettled, ask again
            continue
        key = _claims.key_of(kind, board.kinds)
        where = dict(row.where)
        if key:
            where.setdefault(key, row.name)
        out.append(S.declare_from(row.name, kind, where, row.existence, board,
                                  references=list(row.references), count=row.count,
                                  comparator=row.comparator, span=row.span,
                                  identity=row.name))
    return out, conflicts


def settle_by_routing(rows: List[S.Declared], board: Optional[Board] = None,
                      model=None, timeout: int = 120) -> List[S.Declared]:
    """THE RESIDUAL — a row the manifest's nouns and the lab both missed, routed by the model.

    ⇒⇒ **THIS IS THE ONE RUNG OF THE LADDER THE OPERATOR'S SSOT CRITIQUE DEMANDS.** `nouns`
      indexes 48 words; `computers`, `workstations`, `vlans`, `segments`, `blueprints` are not
      among them and are ordinary English for things this lab holds. A word list cannot be
      completed — that is the operator's whole point — so what the list misses is routed by the
      one component that is good at routing.

    ⇒ **AND IT RUNS LAST, ON WHAT IS LEFT.** `settle_with_world` is a LOOKUP and costs nothing;
      this is a MODEL CALL. Anything the manifest or the lab can answer never reaches here, so
      the cost is paid only for words nothing else could settle
      ([[gorgon-vague-request-ladder]] — the ladder is ordered by who verified the artifact).

    ⇒ **`none of these` IS RECORDED, NOT DISCARDED.** The row stays kindless either way, but
      `unroutable` distinguishes *"the request does not say what this is"* from *"this is not
      one of the things this lab keeps"*. Those are different sentences and different questions
      to the operator, and gate 2 asks the right one because of this flag.

    ⇒ **IT DOES NOT ASK WHETHER THE ROW IS A SET.** Number is structural and pass 1 already
      decided it from the enumerator, the plural noun and the pronoun. Asking again would be a
      second question in one call, which is the form-size rule this project measured twice.

    ⚠⚠ **OFF BY DEFAULT, AND IT HAS NOT EARNED BEING ON.** Set `GORGON_ROUTE_NOUNS=1` to run it.
       Measured 2026-08-11 on 20 held-out words (10 unlisted synonyms, 7 kinds this lab does not
       have, 3 nonsense), n=3:

           correct 13/20 · synonyms 4/10 · null arm 9/10 · FALSE MATCH 3

       **THREE FALSE MATCHES IS A FAIL, and the null arm is what fails.** `routers -> network`,
       `blueprints -> profile`, `backups -> file` — each a confident wrong kind, which is a
       FALSE SERVE, which is the one error this whole stage exists to prevent. An earlier arm
       scored FALSE MATCH 0 and that was a LUCKY ENUM ORDER, not a property: it did not survive
       re-ordering, and the reversal guard that was supposed to defend it made things worse.

    ⇒ **WHAT IS ALREADY WORTH KEEPING, AND IT IS THE HALF THAT DOES NOT NEED THE MODEL:** the
      `no-such-kind` FINDING. Gate 2 used to tell the operator *"the request does not say what
      'routers' is"* — which is false, the request says it perfectly clearly and this lab has no
      such thing. Those are two different questions and they wore one sentence.

    ⇒ **THE NEXT MOVE IS NOT A BETTER PROMPT.** `file` and `network` behave as SINK KINDS — an
      unforced choice drains into them, the same shape as `name` sinking every clause it cannot
      hold. A closed enum over kinds always has a sink. Ask instead one yes/no PER KIND — *is
      this another name for a vm?* — and a word with zero yeses or several is refused by
      arithmetic rather than by the model's restraint.
    """
    import os

    from engines.channel import constrained
    board = board or Board()
    if model is False:                     # an explicit opt-out for a no-model bench
        return rows
    if os.environ.get("GORGON_ROUTE_NOUNS") != "1":
        return rows
    out: List[S.Declared] = []
    for row in rows:
        if row.object_type != UNKNOWN_KIND:
            out.append(row)
            continue
        span = str(row.span or row.name)
        question = S.ROUTE_Q.format(name=span, nouns=S.nouns_offered(board), none=S.NO_KIND)

        def once(reverse: bool):
            try:
                got = constrained(question, span, S.route_schema(board, reverse),
                                  model=model, temp=0.0, timeout=timeout) or {}
                return got.get("answer")
            except Exception:
                # ⇒ A FAILED CALL LEAVES THE ROW EXACTLY AS IT WAS. It must not read as
                #   `NO_KIND`: that would turn a broken channel into the confident claim that
                #   the operator asked for something this lab does not keep.
                return None

        # ⇒⇒ THE REVERSAL GUARD WAS TRIED HERE AND WITHDRAWN. MEASURED, 2026-08-11, n=3:
        #
        #       single call, manifest order    stable 18/20   FALSE MATCH 1
        #       ask both orders, keep agreement stable 20/20   FALSE MATCH 3
        #
        #   **IT CONVERTED UNSTABLE-WRONG INTO STABLE-WRONG.** `routers -> network` and
        #   `blueprints -> profile` AGREE in both orders — the variance was run-to-run jitter
        #   at temp 0, not the enum's ordering, so requiring agreement only made the wrong
        #   answer consistent. It cost two calls per row and bought nothing.
        #
        #   ⇒ THE LESSON IS ABOUT THE PROBE, NOT ABOUT THIS STAGE: the reversal probe finds
        #     answers an ORDER decided. It cannot find an answer the MODEL simply has wrong,
        #     and a stage whose defence is "ask it twice" inherits that blind spot.
        answer = once(False)
        if not answer or answer == S.NO_KIND:
            out.append(row._replace(unroutable=answer == S.NO_KIND))
            continue
        if answer not in board.kinds:
            out.append(row)                # the grammar should forbid this; belt and braces
            continue
        object_type = f"{answer}{S.SET_SUFFIX}" if row.is_set else answer
        out.append(S.declare_from(row.name, object_type, row.where, row.existence, board,
                                  references=list(row.references), count=row.count,
                                  comparator=row.comparator, span=row.span,
                                  identity=row.identity))
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
