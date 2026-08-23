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
from typing import Dict, List, NamedTuple, Optional, Tuple

from planner.formula.legal import Board

PLAN_TIME = "at plan time"
RUN_TIME = "at run time"

NEW, EXISTING = "new", "existing"
SET_SUFFIX = "_set"

# A THING WHOSE KIND THE REQUEST DOES NOT SETTLE. Declared anyway — a bare item and a full one
# are the same until the world says otherwise — and gate 2 asks. It lives HERE, beside the row
# it appears in, so a gate can name it without importing the runner that produces it.
UNKNOWN_KIND = "?"
# ⇒ A ROW THAT IS A VALUE, NOT A THING (08-23, [[gorgon-attributes-are-leaves]]): its own span,
#   never a handle — `symbol_table` skips it, so pass 2 can never act ON a value.
VALUE_KIND = "value"


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
    identity: Optional[str] = None       # a CANDIDATE name — only the lab confirms it
    # ⇒ THE ROUTING STAGE WAS RUN AND SAID NO. Not "we do not know what this is" but "this is
    #   not one of the things this lab keeps" — a different sentence, and a different question
    #   to the operator. Only ever set by `settle_by_routing`; kindless rows nobody asked about
    #   stay False, so absence of the mark means UNASKED rather than ROUTABLE.
    unroutable: bool = False
    # ⇒⇒ ATTRIBUTES ARE LEAVES (08-23). Set ONLY on a VALUE_KIND row — what READ found and
    #   nothing more: the learned word, the attribute it names, the owner class ranked in
    #   (or the conflict, when two owners tie — then `hint` says so for ROUTE). READ never
    #   interprets the value; the owner package does, on this span.
    value: Optional[dict] = None
    # ⇒ WHICH `where` KEYS WERE ASSIGNED by a value row rather than READ as a descriptor (08-23).
    #   `a vm with 4 cores` is not "the vms where cpu_cores = 4" — an assignment names nothing
    #   (no `4_vms` handle) and the request never "says" the owner's converted number (gate 1).
    assigned: Tuple[str, ...] = ()
    # ⇒⇒ THE LATER MENTIONS OF THIS THING, WITH OFFSETS (08-23, ledger #18): `those vms`
    #   after `3 vms`, `it` after `a network`. Bound by NUMBER AGREEMENT — the operator:
    #   *"'those' is plural, and the only plural here is '3 vms' — it should be paired based
    #   on the plurality"* — with a matching noun or modifier as the tie-breaker; a tie
    #   binds nothing and is carried as a conflict for ROUTE. Each: {text, start, end,
    #   number, bare}. `references` keeps the words (the older carrier); this keeps the
    #   evidence. A full-phrase mention is reported as a span; a bare pronoun is not (the
    #   gold points at the thing, never at the pointer).
    mentions: Tuple[dict, ...] = ()
    # ⇒⇒ **THE OPERATOR SAID SO — provenance on `existence`, not a second copy of it.**
    #   `existence` is the model's weakest field (85%, every error toward NEW), which is why
    #   `derive_creators` refuses to mint anything NAMED: a wrong NEW would quietly build a
    #   second `core`. That guard is about WHO SAID NEW, and an operator answering *"yes, create
    #   them"* is the one authority allowed to say it. Set ONLY by `settle_with_answers`, so its
    #   absence means "nobody was asked", never "somebody said no".
    sanctioned: bool = False
    # ⇒⇒ WHAT THIS SET LEAVES OUT — the handles/names an `except` clause removes from it.
    #
    #   The operator, 2026-08-11, on rung 8: *"it needs to produce a set, `all_vms_but_db`,
    #   which is a legal set, and then put db in its own set."* Before this the exclusion was
    #   DETECTED (`linguistics.unexpressed-exclusion`) and never EXPRESSED, so `every vm` still
    #   meant every vm and the program would have put `db` on BOTH networks.
    #
    #   ⇒ IT LIVES ON THE SET, NOT AS A ROW OF ITS OWN. `except db` arriving as a floating
    #     kindless row is what made it invisible — a row nothing connects to is a clause
    #     nobody applied.
    #
    # ⇒⇒ **EACH ENTRY IS A FILTER, NOT A NAME, AND THAT IS THE WHOLE CORRECTNESS OF IT.**
    #   A tuple of strings assumes exclusion-BY-NAME, which is the special case: *"every vm
    #   except THE RUNNING ONES"* has no name to store. Exclusion is by PREDICATE, so an entry
    #   is `{'name': 'db'}` or `{'status': 'running'}` — **exactly the shape the IR's `not`
    #   block takes**, so nothing has to translate it on the way to the engine.
    excludes: tuple = ()

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


# ── THE RESIDUAL ROUTING QUESTION ─────────────────────────────────────────────────────
#
# ⇒⇒ `nouns` IS A WORD LIST, AND THE OPERATOR'S CRITIQUE OF WORD LISTS IS THE REASON THIS
#   EXISTS. 2026-08-11: *"SSOT of nouns and verbs worked in the tool regime because each tool
#   only has finite slots and words related to it, while in the program regime one noun is
#   still legal due to how the sentence is structured."*
#
#   The manifest indexes 48 words. `computers`, `workstations`, `vlans`, `segments`,
#   `backups`, `documents`, `blueprints` are not among them and are ordinary English for
#   things this lab holds. Every one of them becomes an ASK today.
#
# ⇒ SO THE LADDER IS: the manifest's `nouns` (deterministic) -> the lab (deterministic) ->
#   THIS (one model call, on the residual only) -> the ASK. Cheapest and most-verified first,
#   which is [[gorgon-vague-request-ladder]]'s ordering by WHO VERIFIED THE ARTIFACT.
NO_KIND = "none of these"

# ⇒⇒ THE STEER IS LOAD-BEARING AND THE CONTROL PROVES IT — both arms in ONE process, so no
#   model reload could void the comparison ([[gorgon-handover-2026-08-11]] item 2):
#
#       arm              correct  synonyms  null arm  order-stable  FALSE MATCH
#       steered            13/20      3/10     10/10         20/20            0
#       offered only       13/20      4/10      9/10         18/20            2
#
#   OFFERING THE NULL ARM IS NOT ENOUGH. Arm B has it and still forced two confident wrong
#   kinds — `backups -> file`, `users -> file`. **`file` is the SINK KIND**, the same shape as
#   `name` being a sink for every clause it cannot hold. The option must EXIST and the model
#   must be TOLD TO PREFER IT; one without the other buys a false match.
#
#   ⇒ AND THE COST IS ONE SYNONYM. That is the trade [[gorgon-vague-request-ladder]] already
#     priced: a FALSE AVOID costs far more than an unnecessary question.
ROUTE_Q = (
    "What sort of thing is {name!r} in this request? Choose ONE option.\n\n{nouns}\n"
    "  {none} — it is not any of the above, or the word names nothing this lab keeps\n\n"
    "Choose {none!r} rather than the closest fit. A wrong match is worse than no match."
)


def route_schema(board: Optional[Board] = None, reverse: bool = False) -> dict:
    """The kinds plus a way to decline them. NOTE THE DIFFERENCE FROM `type_schema`.

    ⇒ **`type_schema` HAS NO NULL ARM** — six kinds and `required: ["answer"]`, so a word that
      is none of them cannot be answered honestly and comes back as a confident wrong kind.
      That is why the routing question could not simply be re-enabled: the schema had no way
      to say no. Left untouched here because `kindfirst` still uses it and is not measured by
      this change.

    ⇒⇒ **AND IT IS OFFERED IN TWO ORDERS ON PURPOSE, BECAUSE ONE ORDER MEASURED NOTHING.**
      Verified 2026-08-11 at n=3: the manifest order routed `routers` to `network` twice in
      three, and `blueprints` to `profile` twice in three; the reversed order refused both.
      Neither ordering is the right one — **an answer that moves with the order was decided by
      the order**, which is the reversal probe's own rule. So `settle_by_routing` asks BOTH and
      keeps only what agrees, and the enum ordering stops being a hidden parameter rather than
      being pinned to whichever value happened to score well.
    """
    board = board or Board()
    kinds = list(board.kinds)
    options = ([*reversed(kinds), NO_KIND] if reverse else [NO_KIND, *kinds])
    return {"type": "object", "additionalProperties": False, "required": ["answer"],
            "properties": {"answer": {"type": "string", "enum": options}}}

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


def select_of(row: Declared, board: Optional[Board] = None) -> Optional[dict]:
    """The IR select this declaration denotes — AND THE ONLY PLACE THAT SHAPE IS BUILT.

    ⇒⇒ **ONE BUILDER, BECAUSE TWO WOULD DIVERGE.** Gate 4 checks whether an exclusion is
      honourable and the engine eventually has to honour it. If each constructed its own
      select, gate 4 would be validating a select nobody runs — which is the defect this
      session found seven times in other clothes. Same function, same shape, one owner.

    ⇒⇒ **AND THE MULTI-EXCLUSION FORM IS `all` OF `not`s, NOT ONE MERGED `not`.** Measured
      against the IR's validator 2026-08-11: `{"not": {"name": "db", "status": "running"}}`
      VALIDATES — and means *exclude things that are BOTH named db AND running*, which is an
      AND where the operator said two separate exclusions. **A semantically wrong select that
      passes validation is worse than one that fails**, so the shape is chosen here rather
      than discovered by whether the checker complains:

          one exclusion       not: {name: db}
          several             all: [{not: f1}, {not: f2}]     ⇐ AND of nots = exclude both

    Returns None when the kind is not one the manifest holds — there is no select to build.
    """
    board = board or Board()
    if row.kind not in board.kinds:
        return None
    sel: dict = {"kind": row.kind, **(row.where or {})}
    carved = [dict(f) for f in (row.excludes or ()) if f]
    if not carved:
        return sel
    if len(carved) == 1:
        sel["not"] = carved[0]
    else:
        sel["all"] = [{"not": f} for f in carved]
    return sel


def governs(goal: dict, row: Declared) -> bool:
    """Does this GOAL speak about this ROW? The one place that question is answered.

    ⇒⇒ **IT WAS THE SAME DICT COMPARISON IN THREE FILES** — `linguistics.count-ignored`,
      `gates12.completeness` and the pipeline's `_governed` each wrote out *kind matches and
      the wheres are equal*. Three copies of one question is how they drift, and it broke the
      moment a goal stopped being a simple equality: rung 9's reach goal selects THREE named
      machines with `{name: {in: [...]}}`, which no equality test can match.

    ⇒ MEMBERSHIP COUNTS AS GOVERNING. A goal over `{name: {in: [n1, n2, n3]}}` speaks about the
      row named `n1` just as surely as a goal over `{name: n1}` does.
    """
    sel = goal.get("select") or {}
    if sel.get("kind") != row.kind:
        return False
    where = {k: v for k, v in sel.items() if k != "kind"}
    if where == dict(row.where or {}):
        return True
    for attr, want in where.items():
        if isinstance(want, dict) and "in" in want:
            mine = str((row.where or {}).get(attr, ""))
            if mine and mine in [str(x) for x in want["in"]]:
                return True
    return False


def predicate_of(row: Declared, board: Optional[Board] = None) -> Optional[dict]:
    """The STATE this row asserts, as an IR predicate — or None if it asserts none.

    ⇒⇒ **RUNG 7 NEEDS NO MODEL CALL AND NEVER DID.** *"make sure exactly 3 vms carry the 'prod'
      label"* — pass 1 already reads the enumerator (`count=3`, `comparator='eq'`) and the
      modifiers (`where={'label': 'prod'}`), so the predicate is arithmetic over a row that
      already exists:

          {'shape': 'count', 'select': {'kind': 'vm', 'label': 'prod'}, 'eq': 3}

    ⇒ **AND `planner.ir.derive` HAS BEEN ABLE TO CLOSE IT ALL ALONG.** Its own docstring names
      this rung: llama oscillated 6 -> 4 -> 7 -> 5 and never computed *six exist, three wanted,
      remove three* — *"the harness computes it in one line. So it should."* It was never
      reachable from the front seam. The eighth built-and-never-called of the day.

    ⇒ THE SELECT COMES FROM `select_of`, SO A GOAL OVER A CARVED SET HONOURS THE CARVE-OUT.
      *"make sure exactly 3 vms except db carry prod"* must not count `db`, and it will not,
      because the goal and the set are the same select.
    """
    board = board or Board()
    if row.count is None or not row.comparator or not isinstance(row.count, int):
        return None
    sel = select_of(row, board)
    if sel is None:
        return None
    return {"shape": "count", "select": sel, row.comparator: int(row.count)}


def declare_from(name: str, object_type: str, where: Dict[str, object], existence: str,
                 board: Optional[Board] = None,
                 references: Optional[List[str]] = None,
                 count: object = None, comparator: Optional[str] = None,
                 span: str = "", identity: Optional[str] = None,
                 sanctioned: bool = False) -> Declared:
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
                    count=count, comparator=comparator, span=span, identity=identity,
                    sanctioned=bool(sanctioned))


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


from ..codex import REFERRING_PRONOUNS as PRONOUNS

from ..codex import RESTRICTORS


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


from ..codex import DETERMINERS
from ..codex import BOUNDARY_SEPARATORS as BOUNDARIES


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
