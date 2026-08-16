"""iso.py — THE READING, SAID IN SOMEBODY ELSE'S VOCABULARY. ISO 24617-2, emitted.

    annotate("if alpha is stopped, maybe stop most of the vms")
        Task / Instruct   qualifiers: conditionality=conditional · certainty=uncertain
                                      partiality=partial

# ⇒⇒ WHY EMIT AT ALL, WHEN A TRANSLATION TABLE ALREADY EXISTS

`tests/bench/iso_map.py` says where our types SIT in the standard. That is worth having and it
is not enough, for one reason: **without ISO-shaped OUTPUT we cannot be measured against an
ISO-annotated corpus.** Our reading is `directive-act`; theirs is `Task/Instruct` with
`certainty: uncertain`. The map says those correspond; only an emitter makes them comparable.

⇒ **AND THAT IS THE ANSWER TO THE STANDING CEILING.** Every number in this project is measured
  against a corpus one of us wrote — the fourteen rungs, the 48 controls, the door key, all
  mine. An emitter plus a published annotated corpus is **the first measurement that is not
  ours**, and it is available before A1 is spent.

# ⇒⇒ THREE AXES, AND WE HAD COLLAPSED TWO OF THEM

    DIMENSION   what the segment is ABOUT — nine of them, and one utterance may carry several
    FUNCTION    what it DOES in that dimension
    QUALIFIER   HOW it is held — certainty · conditionality · partiality · sentiment

⇒ **THE QUALIFIER AXIS IS THE ONE WE NEVER HAD.** Stance was modelled as a SPECIES beside
  order and question; ISO makes it a MODIFIER on any act. *"maybe stop the vms"* is an Instruct
  held uncertainly — not a different kind of sentence. **And CONDITIONALITY is one of them**,
  which is why a conditional can be READ while E5 stands: a flag on the act, not a clause
  structure the writer must emit.

# ⇒ NOTHING HERE READS ANYTHING NEW

Every field is assembled from a reader that already exists — `speech_act` for the act,
`temporal` for the event and clock, `scan` for the quantifiers, `linguistics` for the mood.
**This is a projection, not a second opinion**, which is what keeps the two vocabularies from
disagreeing: change the reading and this changes with it.

⇒ ⚠ **AND `sentiment` IS DECLINED, DELIBERATELY.** It is the one qualifier that cannot be read
  from a declared class — [[gorgon-unprocessable-taxonomy]] concluded that of the whole
  taxonomy only FLAVOUR needs vocabulary, and sentiment is flavour. A `PLEASANTRIES`-shaped
  constant is what the Encyclopedia's rule forbids, so it stays empty until somebody TEACHES
  it. An empty qualifier is a gap; a guessed one is a wrong annotation that scores as right.
"""
from typing import Dict, List, NamedTuple, Optional

from planner.formula.legal import Board

# ── the nine dimensions ──────────────────────────────────────────────────────────────
TASK = "Task"
AUTO_FB = "Auto-Feedback"
ALLO_FB = "Allo-Feedback"
TURN = "Turn Management"
TIME = "Time Management"
DISCOURSE = "Discourse Structuring"
OWN_COMM = "Own Communication Management"
PARTNER_COMM = "Partner Communication Management"
SOCIAL = "Social Obligations Management"

DIMENSIONS = (TASK, AUTO_FB, ALLO_FB, TURN, TIME, DISCOURSE, OWN_COMM, PARTNER_COMM, SOCIAL)

QUALIFIERS = ("certainty", "conditionality", "partiality", "sentiment")

# ⇒⇒ **OUR TYPES, PLACED — AND THIS TABLE IS THE ONLY PLACE THE TWO VOCABULARIES MEET.**
#   The operator's ruling, 2026-08-16: *"map rather than rename."* `DIRECTIVE_ACT` and the rest
#   are embedded everywhere and are staying; one table, read by production and by the bench, is
#   what stops them drifting apart across a dozen docstrings.
#
#   ⇒ ⚠ **`declaration` DOES NOT FIT, AND SAYING SO IS THE POINT OF MAPPING.** A standing rule
#     changes what is PERMITTED by being said. ISO's Task dimension has no such function,
#     because ISO annotates dialogue ABOUT a task rather than dialogue that LEGISLATES over
#     one. Filed under Inform with the mismatch recorded, not forced.
PLACED: Dict[str, tuple] = {
    "directive-act":    (TASK, "Instruct"),
    "directive-inform": (TASK, "Set Question"),
    "assertive":        (TASK, "Inform"),
    "answer":           (TASK, "Answer"),
    "commissive":       (TASK, "Promise"),
    "meta-control":     (TIME, "Pausing"),
    "expressive":       (SOCIAL, "Greeting"),
    "declaration":      (TASK, "Inform"),
}

# ⇒ THE EPISTEMIC ADVERBS. A closed class, and the same licence `FREQUENCY` claims for
#   `never`/`always`: English has these and gains none.
#   ⇒ ⚠ THE MODALS ARE DELIBERATELY ABSENT. `may` and `might` are epistemic AND deontic, and
#     `DEONTIC` already spends them on permission — a word claimed twice is how a reading
#     starts disagreeing with itself.
HEDGES = frozenset({"maybe", "perhaps", "probably", "possibly", "presumably", "apparently",
                    "likely", "seemingly"})
EMPHATIC = frozenset({"definitely", "certainly", "surely", "obviously", "clearly",
                      "undoubtedly", "absolutely"})


class Annotation(NamedTuple):
    """One functional segment, in ISO's terms.

    ⇒ `function` is empty when `speech_act` could not settle the segment — UNREAD is a real
      answer here exactly as it is there, and an annotation that guesses is worse than one that
      abstains, because it scores as right.
    """
    segment: str
    dimension: str
    function: str
    qualifiers: Dict[str, str]

    def __repr__(self) -> str:
        q = " · ".join(f"{k}={v}" for k, v in sorted(self.qualifiers.items()) if v)
        return f"{self.dimension}/{self.function or '—'}" + (f"  [{q}]" if q else "")


def qualifiers_of(segment: str, board: Optional[Board] = None) -> Dict[str, str]:
    """The four ISO qualifiers, read from classes that are already declared.

    ⇒ **CONDITIONALITY** — a subordinating `if`/`unless`, or an event that starts the act.
      Both are already read: `speech_act.SUBORDINATING` landed with the subordinator head test
      and `temporal.events_in` with the trigger reader.
    ⇒ **PARTIALITY** — `scan.PARTIAL`, the quantifier between one and all. It names an amount
      NOBODY CAN COMPUTE, so it is a qualifier and a question rather than a set.
    ⇒ **CERTAINTY** — the epistemic adverbs, a closed class.
    ⇒ ⚠ **SENTIMENT** — declined. It is the one qualifier that needs vocabulary rather than a
      class, and a constant for it is what the Encyclopedia's rule forbids.
    """
    from .scan import PARTIAL
    from . import speech_act as SA, temporal as T

    said = SA.words_of(segment)
    words = set(said)
    out: Dict[str, str] = {}

    if is_condition(segment):
        out["conditionality"] = "conditional"
    # ⇒ ⚠ **`how many` IS A COUNT QUESTION, NOT A PARTIAL QUANTIFIER**, and the first cut of
    #   this annotated *"how many vms are running"* as `partiality=partial`. `many` is a real
    #   partial determiner — *"many vms are stopped"* — and inside the wh-phrase it is
    #   interrogative. Position settles it, and the pair is one word apart.
    partial = {w for i, w in enumerate(said)
               if w in PARTIAL and not (i and said[i - 1] == "how")}
    if partial:
        out["partiality"] = "partial"
    if words & HEDGES:
        out["certainty"] = "uncertain"
    elif words & EMPHATIC:
        out["certainty"] = "certain"
    return out


def is_condition(segment: str, board: Optional[Board] = None) -> bool:
    """Does this segment state a CONDITION on another act rather than an act of its own?

    ⇒⇒ **A CONDITION IS NOT A SECOND DIALOGUE ACT, AND READING IT AS ONE IS THE DEFECT THIS
      WHOLE AREA KEEPS PRODUCING.** *"whenever a vm stops, take a snapshot"* is ONE Instruct
      held conditionally; the first cut of `annotate` emitted TWO Instructs, because
      `speech_act` reads the condition clause as directive-act — it carries `stops`, which is
      a manifest verb.
    ⇒ **SO THE TEST IS POSITIONAL AND NOT SEMANTIC:** a segment that OPENS on a subordinator
      hangs off another. The same bound that stopped `if alpha is stopped` reading as teaching,
      one layer out — and `SUBORDINATING` and `temporal.EVENTS` are both already declared.
    """
    from . import speech_act as SA, temporal as T
    # ⇒ A STANDING PHRASE SITS IN FRONT OF THE CONDITION AND IS NOT ONE. *"FROM NOW ON after
    #   you are done with a vm"* is the operator's own trigger example, and taking the head
    #   before stripping it read `from` and missed the `after` behind it.
    low = str(segment).lower().strip()
    for phrase in T.STANDING:
        if low.startswith(phrase):
            low = low[len(phrase):].strip(" ,")
    head = SA._after_openers(SA.words_of(low))
    if not head:
        return False
    first = head[0]
    return (first in {"if", "unless"} or first in T.EVENTS
            or first in T.ALWAYS_STANDING
            or any(low.startswith(p) for p in T.ALWAYS_STANDING_PHRASES))


def annotate(request: str, board: Optional[Board] = None, world=None) -> List[Annotation]:
    """Every functional segment of the request, in ISO's vocabulary.

    ⇒ **A PROJECTION OF READINGS THAT ALREADY EXIST**, never a second opinion. The segment is
      `speech_act.clauses` — which is pass 2's splitter, not a third one — and the function is
      whatever `speech_act` settled, translated through `PLACED`.

    ⇒ ⚠ **AND THE CONDITIONALITY QUALIFIER MOVES TO THE ACT IT MODIFIES.** *"if alpha is
      stopped, launch it"* is ONE dialogue act — an Instruct held conditionally — and not two.
      A condition read as its own segment is the mistake that had it filed as teaching for a
      month; here the flag rides on the clause that BUILDS, which is what a qualifier is.
    """
    from . import self_repair as SR, speech_act as SA

    board = board or Board()
    # ⇒⇒ **A REPAIR IS ITS OWN DIALOGUE ACT AND IT IS EMITTED FIRST**, because it is about the
    #   TURN rather than about the task. ISO files both under Own Communication Management, and
    #   the segment that follows is still whatever it is — an Instruct the operator amended is
    #   an Instruct and an amendment, not one or the other.
    mend = SR.read(request)
    # ⇒⇒ ⚠ **AND THE TASK ACT IS READ FROM WHAT WAS ASKED, NOT FROM THE RAW STRING.** With the
    #   repair still in it, *"stop alpha — sorry, i meant beta"* split into three segments and
    #   `i meant beta` came back a GREETING — the producer test reaching EXPRESSIVE because the
    #   fragment names no verb. The repair markers are not part of the request; they are the
    #   operator managing their own turn, and they are already annotated above.
    #   ⇒ **THIS IS NOT THE SUBSTITUTION WE REFUSE TO MAKE.** Reading the act from what was
    #     SAID is not the same as deciding what the correction REPLACES — that alignment is
    #     still asked, by `linguistics/self-correction`, and nothing here guesses it.
    read = SA.read(mend.withdrawn if mend else request, board, world)
    segments = [(c, a) for c, a in read]

    # ⇒ THE CONDITION'S OWN SEGMENT CARRIES NO FUNCTION, so its qualifier is lifted onto the
    #   first segment that has one. Nothing is lost and nothing is duplicated.
    carried: Dict[str, str] = {}
    out: List[Annotation] = []
    for clause, act in segments:
        q = qualifiers_of(clause, board)
        # ⇒ A CONDITION CARRIES ITS QUALIFIER FORWARD AND EMITS NOTHING OF ITS OWN, whatever
        #   `speech_act` made of it — see `is_condition`.
        if act is None or act not in PLACED or is_condition(clause, board):
            carried.update(q)
            continue
        dimension, function = PLACED[act]
        merged = dict(carried)
        merged.update(q)
        carried = {}
        out.append(Annotation(clause.strip(), dimension, function, merged))

    # ⇒ AND A REQUEST WHOSE EVERY SEGMENT WAS UNREAD STILL PRODUCES ONE ROW, because *nothing
    #   was understood* is a reading and an empty list is an absence of one.
    if not out and segments:
        out.append(Annotation(request.strip(), TASK, "", carried))
    if mend:
        out.insert(0, Annotation(
            mend.withdrawn or request.strip(), OWN_COMM,
            "Retraction" if mend.kind == SR.RETRACTED else "Self-Correction", {}))
    return out
