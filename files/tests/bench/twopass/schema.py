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
    references: List[str] = ()           # LATER mentions of this same object, in order
    count: object = None                 # 5 · "all" · None — READ from the enumerator
    comparator: Optional[str] = None     # eq · min · max — READ from in front of it
    span: str = ""                       # the noun phrase the request actually wrote

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

# ⇒⇒ THE MANIFEST'S OWN SYNONYMS, AND WITHOUT THEM THE QUESTION IS UNANSWERABLE.
#
# The enum says `vm`. A request says *"machines"*. Nothing told the model those are the same
# thing — and the manifest has always known:  vm.nouns = machine, box, node, server, host...
#
# Measured 2026-08-08, rung 14. WITHOUT the nouns, every wording failed:
#     'two machines' -> snapshot · 'a group of machines' -> network · 'machines' -> snapshot
# WITH them, all correct — and *"a restore point"* maps to `snapshot`, a word that appears
# nowhere but the synonym list, which is what proves it is the nouns and not luck.
def nouns_offered(board: Optional[Board] = None) -> str:
    board = board or Board()
    lines = []
    for kind in board.kinds:                      # declaration order, pinned like the rest
        also = (board.kinds[kind] or {}).get("nouns") or []
        lines.append(f"  {kind} — also called: {', '.join(also)}" if also else f"  {kind}")
    return "\n".join(lines)


TYPE_Q = (
    "What sort of thing is {name!r} in this request? Choose ONE option.\n\n{nouns}\n\n"
    "Choose the plain kind if it is a single individual thing, and the '{suffix}' form if it "
    "is a GROUP of them."
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
                 board: Optional[Board] = None,
                 references: Optional[List[str]] = None,
                 count: object = None, comparator: Optional[str] = None,
                 span: str = "") -> Declared:
    """Assemble one row. `settled` is derived here and nowhere else.

    ⇒ `count` AND `comparator` ARE READ, NOT ASKED. They live in the request's enumerator
      region — *"exactly two machines"*, *"at most three vms"*, *"5 vms"* — and pass 1 never
      asked for either, so half the rungs could not have been expressed however good the
      other answers were.
    """
    board = board or Board()
    kind = object_type[:-len(SET_SUFFIX)] if object_type.endswith(SET_SUFFIX) else object_type
    return Declared(name=name, object_type=object_type, where=dict(where or {}),
                    existence=existence if existence in (NEW, EXISTING) else EXISTING,
                    settled=settled_of(kind, where or {}, board),
                    references=list(references or []),
                    count=count, comparator=comparator, span=span)


def render(rows: List[Declared]) -> str:
    """The symbol table as pass 2 will be shown it."""
    if not rows:
        return "(nothing declared)"
    out = ["these things have already been identified and confirmed:"]
    for r in rows:
        where = ", ".join(f"{k} = {v}" for k, v in r.where.items()) or "no condition"
        also = f"   (also referred to as: {', '.join(r.references)})" if r.references else ""
        howmany = ""
        if r.count is not None:
            howmany = f"  —  {r.comparator or 'eq'} {r.count}" if r.comparator or \
                isinstance(r.count, int) else f"  —  {r.count}"
        out.append(f"  {r.name}  —  a {r.object_type}{howmany}  —  {where}  —  "
                   f"{r.existence}, known {r.settled}{also}")
    return "\n".join(out)


# A BARE PRONOUN REFERS; A RESTRICTED ONE DOES NOT. Closed set, so this is arithmetic.
#
# The operator, 2026-08-08: *"or not even by name, through context — 'create X then put it in
# Y' is actually 2 X references, one is X as create and then 'it' is also a reference to X."*
#
# The model already shows this. Rung 2 came back as `vm` / `beta` / `it`, with `it` declared
# as an object of its own.
#
# ⇒ **BUT ONLY A BARE PRONOUN FOLDS.** *"the ones that do not answer"* is NOT a reference to
#   *"every vm"* — it is a different set, restricted. Folding on the word `ones` alone would
#   silently merge a subset into its superset, which is rung 11's whole distinction destroyed.
#   So the match must be the WHOLE name, with nothing else in it.
# ⇒⇒ MEASURED REGRESSION, 2026-08-08, AND IT WAS TWO OF THESE MECHANISMS COMPOUNDING.
#
# `one`, `ones`, `that`, `those` and `these` USED TO BE IN THIS SET. They are the HEADS OF
# RESTRICTED DESCRIPTIONS, not pro-forms: *"the ones that do not answer"*. The naming question
# chunks that phrase down to the bare token `ones` — and the fold then merged `ones` into
# `vm`, correctly by its own rule, destroying rung 11's subset.
#
#     pre-fold   ping · vm · ones          <- three rows, `ones` badly representing the subset
#     folded     ping · vm                 <- the subset GONE, refs=['ones'] on `vm`
#
# The guard checked the whole name for a restriction, but the chunker had ALREADY stripped it.
# So: only unambiguous pro-forms are listed, AND the request is consulted for a restrictor.
PRONOUNS = frozenset({
    "it", "its", "them", "they", "their", "theirs", "both",
    "all of them", "each of them", "every one of them",
})

# a word that turns a noun phrase into a RESTRICTED description — "the ones THAT do not answer"
RESTRICTORS = ("that", "which", "who", "whose", "with", "without", "not")


def _is_bare_pronoun(name: str, request: str = "") -> bool:
    """A pro-form with nothing attached. The REQUEST is consulted, because the naming question
    chunks restricted phrases down to their head and the restriction is no longer in the name.
    """
    word = name.strip().strip(".,'\"").lower()
    if word not in PRONOUNS:
        return False
    if request:
        low = request.lower()
        if any(f"{word} {r} " in low or low.endswith(f"{word} {r}") for r in RESTRICTORS):
            return False        # it heads a restriction in the request — not a bare reference
    return True


# ── COREFERENCE, COMPUTED RATHER THAN ASKED ───────────────────────────────────────────
def merge(rows: List[Declared], board: Optional[Board] = None,
          request: str = "") -> List[Declared]:
    """Collapse rows that provably denote the SAME object.

    The operator, 2026-08-08, on rung 3: *"when an object got referenced twice, it seems like
    it didn't connect the dots."* Correct — `web` is mentioned in both clauses and came back
    as two separate declarations, alongside a third from the chunking.

    ⇒ **AND THE IDENTITY IS ALREADY IN THE ANSWERS.** Two rows of the same kind whose KEY
      attribute holds the same value are the same object — `key` is declared in the manifest,
      so this is arithmetic, not a judgement. W8: when a value can be computed, do not ask.

    ⇒ **THE FIRST MENTION DECLARES; EVERY LATER ONE IS A REFERENCE.** The operator's design:
      *"if an object with the same name pops up twice, we fold the later onto a reference. In
      'create X, do Y with X', X is an object because of CREATE, and then X shows up again as
      part of Y, which is an operator. So X is saved twice — once as the actual object, and
      later as a reference."*

      That ordering carries two things a symmetric merge throws away:

        * **A LATER MENTION CAN NEVER RE-CREATE.** The declaration's `existence` is decided by
          the mention that declared it. A second appearance inside an operation is a use, so
          it is `existing` by definition and is not judged again.
        * **THE REFERENCES ARE THE DEPENDENCY STRUCTURE.** That X is mentioned again in a later
          clause says that clause depends on X's declaration — the join, stated rather than
          inferred.

    ⇒ AND IT MEANS WE STOP FIGHTING THE OVER-DECLARATION. The model extracts well (names 14/14);
      it simply mentions things more than once. Let it, and fold behind it.

    A row with no key value cannot be proven identical to anything and is left alone; a set is
    never folded into an individual.
    """
    from planner.gates import claims as _claims

    board = board or Board()
    out: List[Declared] = []
    seen: Dict[tuple, int] = {}
    for row in rows:
        # A BARE PRONOUN IS A REFERENCE TO THE MOST RECENT DECLARATION IT COULD BE ABOUT.
        # Its own type answer is not trusted — the model was asked to type a pronoun, which
        # is not a question with an answer.
        if _is_bare_pronoun(row.name, request) and out:
            back = next((i for i in range(len(out) - 1, -1, -1)
                         if out[i].kind == row.kind or not row.where), None)
            if back is not None:
                first = out[back]
                out[back] = declare_from(first.name, first.object_type, first.where,
                                         first.existence, board,
                                         references=list(first.references) + [row.name])
                continue

        key_attr = _claims.key_of(row.kind, board.kinds)
        value = (row.where or {}).get(key_attr) if key_attr else None
        token = (row.kind, row.is_set, value) if value not in (None, "") else None
        if token is not None and token in seen:
            at = seen[token]
            first = out[at]
            where = dict(first.where)
            where.update(row.where)          # a later mention may still ADD a condition
            out[at] = declare_from(first.name, first.object_type, where,
                                   first.existence, board,   # the DECLARATION's answer stands
                                   references=list(first.references) + [row.name])
            continue
        if token is not None:
            seen[token] = len(out)
        out.append(row)
    return out


# ── A TRUNCATED NAME IS REPAIRED FROM THE REQUEST, NOT RE-ASKED ────────────────────────
DETERMINERS = ("the", "a", "an", "every", "all", "each", "both", "any", "some", "no",
               "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
BOUNDARIES = (",", ";", " and ", " then ", " but ", "—", " - ")


def expand(name: str, request: str) -> str:
    """Grow a chunked name back to the phrase it came from, using the REQUEST as the source.

    The naming question chunks — *"the ones that do not answer"* comes back as bare `ones`, and
    every question after it is then asked about a fragment. The restriction is not lost, it is
    still sitting in the request, so it is RECOVERED rather than re-requested.

    ⇒ AND IT IS MEASURED, not hoped for. From the same model, earlier the same day:

          'ones that do not answer'       -> network_set   WRONG
          'the ones that do not answer'   -> vm_set        right, 2 of 2

      So the expansion fixes the TYPE as well as giving the conditions question something to
      read. Both failures downstream of rung 11 have one upstream cause.

    Conservative by construction: it extends left over at most ONE determiner, and extends
    right ONLY when a restrictor immediately follows, stopping at the first clause boundary.
    A name that is not found verbatim is returned untouched.
    """
    if not name or not request:
        return name
    low, target = request.lower(), name.strip().lower()
    at = low.find(target)
    if at < 0:
        return name
    end = at + len(target)

    # left: one determiner, if the word before it is one
    before = low[:at].rstrip()
    if before:
        word = before.split()[-1] if before.split() else ""
        if word in DETERMINERS or word.isdigit():      # "5 vms" as well as "five vms"
            at = len(before) - len(word)

    # right: only through a restrictor, and only to the end of this clause
    rest = low[end:]
    following = rest.strip().split()[0] if rest.strip() else ""
    if following in RESTRICTORS:
        stop = len(rest)
        for mark in BOUNDARIES:
            found = rest.find(mark)
            if 0 <= found < stop:
                stop = found
        end += stop
    return request[at:end].strip()


# ── CONDITIONS, ASKED AS A FORCED CHOICE AND THEN CLOSED AT BOTH ENDS ──────────────────
#
# MEASURED 2026-08-08, over 14 requests: the old array form produced 7 correct conditions, 19
# INVENTED, and 10 empties. Two holes, neither of them the model being poor at reading:
#
#   1 THE VALUE WAS FREE TEXT. The attribute came from a closed list and the value did not, so
#     `status = pingable` and `status = new` were writable — while the manifest says status is
#     running or stopped. We closed one half of the pair and left the other open.
#   2 THE QUESTION WAS ASKED WHERE NO ANSWER WAS WANTED. About 17 of the 19 invented conditions
#     sat on things needing none — `alpha`, `db`, `n1`, and chunks like `called lab`. `[]` was
#     available and it did not take it.
#
# And every one of the 7 correct answers was a request containing the value word LITERALLY —
# "currently stopped", "the 'prod' label", "every running vm". It matches text.
ALL_OF_THEM, ONLY_SOME = "all of them", "only some of them"

# ⇒⇒ THIS IS THE WORDING THAT WAS MEASURED. DO NOT "IMPROVE" IT.
#
# It scored 4/4. I then added two sentences of guidance that began *"Answer 'only some of
# them' just when..."* — and it dropped to 2/4, answering "only some" for everything including
# the verb `ping`. NAMING ONE OF THE OPTIONS INSIDE THE EXPLANATION PRIMES IT. That is the
# third measured question degraded today by being improved after it was measured.
# AND IT SAYS "machines", NOT "vms" — the manifest's own noun. Substituting the KIND name
# dropped it from 4/4 to 2/3: 'the ones that do not answer' answered "all of them" when asked
# about `vms` and "only some" when asked about `machines`. Same finding as the type question.
SCOPE_Q = "Does {name!r} mean ALL of the {plural}, or only SOME of them?"


def plural_for(kind: str, board: Optional[Board] = None) -> str:
    """The operator's word for this kind, pluralised — never the system's word."""
    board = board or Board()
    nouns = (board.kinds.get(kind) or {}).get("nouns") or []
    word = nouns[0] if nouns else kind
    return word if word.endswith("s") else f"{word}s"

ATTRIBUTE_Q = (
    "Which ONE thing about a {kind} decides whether it is part of {name!r}? Choose from the "
    "list. Judge MEMBERSHIP of that group, not what should happen to it."
)

VALUE_Q = (
    "For something to be part of {name!r}, what must its {attr} be?"
)


def scope_schema() -> dict:
    # ALL FIRST, DELIBERATELY. The first enum member is over-picked on this stack, and the
    # errors here run 19 invented against a handful missing — so the safe bias is toward
    # "no condition", which is what leading with `all of them` buys.
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string",
                                      "enum": [ALL_OF_THEM, ONLY_SOME]}}}


def attribute_schema(object_type: str, board: Optional[Board] = None) -> dict:
    attrs = attributes_for(object_type, board)
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": attrs} if attrs
                           else {"type": "string"}}}


def value_schema(object_type: str, attr: str, board: Optional[Board] = None) -> dict:
    """THE VALUE LIST IS BUILT FROM THE ATTRIBUTE, so an illegal value is UNWRITABLE.

    This is the half that was open. `status = pingable` was not a mistake the model made in
    spite of the schema — the schema permitted it. Where the manifest declares a closed set the
    answer is an enum; where the attribute is OBSERVED it is a boolean; only genuinely open
    attributes, like a name, stay free text.
    """
    board = board or Board()
    kind = object_type[:-len(SET_SUFFIX)] if object_type.endswith(SET_SUFFIX) else object_type
    allowed = board.values(kind, attr)
    if allowed:
        return {"type": "object", "additionalProperties": False, "required": ["answer"],
                "properties": {"answer": {"type": "string", "enum": list(allowed)}}}
    if attr in board.observable(kind):
        return {"type": "object", "additionalProperties": False, "required": ["answer"],
                "properties": {"answer": {"type": "boolean"}}}
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "minLength": 1}}}
