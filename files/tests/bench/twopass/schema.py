"""PASS ONE — the declaration schema. THE MOCK-UP, and it makes no model call.

Item 2 of the plan. Item 1 (`condition_probe` and its four follow-ons) existed to protect
this file, and everything it settled arrives here as a DECISION rather than a guess:

    settled     COMPUTED from the manifest's `observed`, never asked          (item 1, W8)
    existence   ASKED, and GLOSSED — 85%, and glossing is what makes it       (item 1, gloss)
                robust to wording rather than dependent on one lucky pair
    order       PINNED, never `sorted()` — moving ONE entry doubled exact     (item 1, hazard)
                matches, so order is a hidden parameter and must be visible
    no condition field                                                        (item 1, framing A)
    one question per call, every field required, refusal explicit             (form-size rule)

# WHAT PASS ONE ASKS, AND WHAT IT NEVER ASKS

    1  what things does this sentence talk about?     -> names, in the requester's own words
    2  what sort of thing is each?                    -> a kind, or a kind's SET   [closed]
    3  which ones? (conditions)                       -> declared attributes       [closed]
    4  is it new, or already there?                   -> glossed two-option        [85%]

    settled     NOT ASKED. A definition that mentions an OBSERVED attribute cannot be resolved
                before the run, so binding time follows from the manifest. This is the field
                the writer has never been given ([[gorgon-the-writer-fails-rung-11]]).

⇒ **A SET IS A FIRST-CLASS OBJECT AND THAT IS THE POINT.** The model has repeatedly taken a
  set it could not name — *"the ones that do not answer"* — and sunk it into a `name` field as
  a literal string. Here `unresponsive : vm_set` IS THE CORRECT ANSWER, so the behaviour that
  was the defect becomes the behaviour that is wanted.

⇒ **AND `existence` IS BEST-EFFORT BY DESIGN.** It reads at 85% and every error is toward
  `new` — asking to create something that already exists. That is the disagreement gate 2 is
  built to catch, so a wrong answer here becomes a QUESTION rather than a bad program. The
  `golden` case is NOT reachable from the request at all and belongs to the book keeper
  ([[gorgon-twopass-item-1]]).
"""
from typing import Dict, List, NamedTuple, Optional

from ..formula.legal import Board

PLAN_TIME = "at plan time"
RUN_TIME = "at run time"

NEW, EXISTING = "new", "existing"
SET_SUFFIX = "_set"


class Declared(NamedTuple):
    """One row of the symbol table. Pass 2 may reference nothing else."""
    name: str
    object_type: str                     # `vm` or `vm_set`
    where: Dict[str, object]             # {} for a bare named individual
    existence: str                       # NEW | EXISTING — asked, 85%, errors toward NEW
    settled: str                         # COMPUTED, never supplied

    @property
    def kind(self) -> str:
        return self.object_type[:-len(SET_SUFFIX)] if self.is_set else self.object_type

    @property
    def is_set(self) -> bool:
        return self.object_type.endswith(SET_SUFFIX)

    @property
    def residual(self) -> bool:
        """Cannot be resolved before the run — the writer must leave it in the program."""
        return self.settled == RUN_TIME


# ── the closed lists, PINNED ──────────────────────────────────────────────────────────
def types_offered(board: Optional[Board] = None) -> List[str]:
    """Every kind and every kind's set, IN THE MANIFEST'S OWN DECLARATION ORDER.

    ⇒ **NOT `sorted()`, AND THAT IS LOAD-BEARING.** Item 1 measured that moving a single entry
      from the front of an enum to the back doubled exact matches and removed every spurious
      step — no change to prompt, schema or model. Order is semantically meaningless in a
      closed set, which makes it a HIDDEN PARAMETER: alphabetical order reshuffles whenever a
      kind is added, and behaviour would move with it for no visible reason.

      The manifest's own order is the operator's, it is deliberate, and `test_schema` pins it
      so that any change shows up as a failing test rather than as drifting behaviour.
    """
    board = board or Board()
    out: List[str] = []
    for kind in board.kinds:                       # declaration order, not sorted
        out.append(kind)
        out.append(f"{kind}{SET_SUFFIX}")
    return out


def settled_of(kind: str, where: Dict[str, object],
               board: Optional[Board] = None) -> str:
    """COMPUTED. A set defined by something the world must be ASKED cannot be known early."""
    board = board or Board()
    return RUN_TIME if (set(where) & set(board.observable(kind))) else PLAN_TIME


def attributes_for(object_type: str, board: Optional[Board] = None) -> List[str]:
    """What `where` may narrow on — declared attributes PLUS observed ones.

    Observed attributes belong here and NOT in anything settable: you may select the machines
    that did not answer, and you may not order a machine to answer.
    """
    board = board or Board()
    kind = object_type[:-len(SET_SUFFIX)] if object_type.endswith(SET_SUFFIX) else object_type
    return board.filterable(kind) if kind in board.kinds else []


# ── the four questions. ONE PER CALL. ─────────────────────────────────────────────────
# ⇒⇒ NO PROMPT HERE MAY QUOTE A PHRASE FROM A REQUEST. MEASURED, 2026-08-08.
#
# This question used to illustrate itself with *"the ones that do not answer"* — which is
# rung 11's own wording. The model COPIED THE EXAMPLE INSTEAD OF READING THE SENTENCE:
#
#   with the example      "clone golden into 3 new vms"  ->  ['ones that do not answer', ...]
#   without the example   "clone golden into 3 new vms"  ->  ['a group of clones', 'golden', ...]
#
# So the illustration became the answer, and rung 11 was being handed its own solution — the
# whole first pass-1 measurement was void. `test_twopass_schema` now fails if any question
# string contains a rung's wording, because this is invisible in the output and looks like a
# model failure.
NAMES_Q = (
    "List every distinct thing this sentence talks about, using the sentence's OWN words for "
    "each. A GROUP of things counts as one thing and should be named too. "
    "Do not say what happens to them."
)

TYPE_Q = (
    "What sort of thing is {name!r} in this sentence? Choose ONE option. Choose a plain kind "
    "if it is a single individual thing, and the '{suffix}' form if it is a GROUP of them."
)

WHERE_Q = (
    "Which conditions pick out the members of {name!r}? Use only conditions the sentence "
    "actually states. If {name!r} means all of them with no condition, or is one named thing, "
    "answer with an empty list."
)

# GLOSSED, and the gloss is the measured part — it lifts a weak wording from 54% to 77% and
# collapses the spread between synonym pairs from 31 points to 8.
EXISTENCE_Q = (
    "For {name!r} in this sentence:\n"
    "  answer '{new}' — meaning it must be brought into existence: created, built, "
    "provisioned, made new\n"
    "  answer '{existing}' — meaning it is already there: existing, previously created, only "
    "being selected, reused or acted upon\n"
    "Judge only what the request asks for about THIS thing."
)


# ── THE PAIRED FORM: name and type answered TOGETHER ──────────────────────────────────
#
# Measured 2026-08-08: asked separately, *"create a vm named alpha"* came back as the names
# ['vm', 'alpha'] — correct extraction of both MENTIONS, and no way to say they are ONE thing
# with a type and a name. The flat list of names has no slot for that, so the model cannot
# express it however well it reads.
#
# ⇒ THE RULE THIS IS THE THIRD INSTANCE OF: ask one question at a time, UNLESS the two answers
#   are mutually defining — then splitting them removes the information each one needed.
#   `which_ones` + `must_become` was the first, single-versus-multi action the second.
PAIRED_Q = (
    "List every distinct thing this sentence talks about. For each one give TWO things:\n"
    "  name — the sentence's own words for it\n"
    "  sort — what kind of thing it is\n\n"
    "When the sentence describes something by its KIND and also gives it a NAME, that is ONE "
    "thing and not two: the kind is its sort, and the name is its name.\n"
    "A GROUP of things is also ONE thing, with its own name and sort.\n"
    "Do not say what happens to them."
)


def paired_schema(board: Optional[Board] = None) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {
                "type": "array", "minItems": 1, "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["name", "sort"],
                    "properties": {"name": {"type": "string", "minLength": 2},
                                   "sort": {"type": "string", "enum": types_offered(board)}}}}}}


def names_schema() -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "array", "minItems": 1,
                                      "items": {"type": "string", "minLength": 2}}}}


def type_schema(board: Optional[Board] = None) -> dict:
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": types_offered(board)}}}


def where_schema(object_type: str, board: Optional[Board] = None) -> dict:
    attrs = attributes_for(object_type, board)
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {
                "type": "array",
                "items": {"type": "object", "additionalProperties": False,
                          "required": ["attribute", "value"],
                          "properties": {
                              "attribute": {"type": "string", "enum": attrs} if attrs
                              else {"type": "string"},
                              "value": {"type": ["string", "boolean", "integer"]}}}}}}


def existence_schema() -> dict:
    # EXISTING first: every measured error was toward NEW, so the safe answer leads and a
    # relapse into first-member picking shows up as over-refusal rather than over-creation.
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": [EXISTING, NEW]}}}


def declare_from(name: str, object_type: str, where: Dict[str, object], existence: str,
                 board: Optional[Board] = None) -> Declared:
    """Assemble one row. `settled` is derived here and nowhere else."""
    board = board or Board()
    kind = object_type[:-len(SET_SUFFIX)] if object_type.endswith(SET_SUFFIX) else object_type
    return Declared(name=name, object_type=object_type, where=dict(where or {}),
                    existence=existence if existence in (NEW, EXISTING) else EXISTING,
                    settled=settled_of(kind, where or {}, board))


def render(rows: List[Declared]) -> str:
    """The symbol table as pass 2 will be shown it."""
    if not rows:
        return "(nothing declared)"
    out = ["these things have already been identified and confirmed:"]
    for r in rows:
        where = ", ".join(f"{k} = {v}" for k, v in r.where.items()) or "no condition"
        out.append(f"  {r.name}  —  a {r.object_type}  —  {where}  —  "
                   f"{r.existence}, known {r.settled}")
    return "\n".join(out)
