"""THE DEEP LINGUISTICS GATE — the request's GRAMMAR against the program's STRUCTURE.

    after pass 2, before gate 3

# ⇒⇒ WHY IT SITS HERE AND NOWHERE ELSE

Every check in this file needs BOTH artifacts. Pass 1 alone cannot tell whether `snapshot` is a
thing or an action, and pass 2 alone has no declarations to judge. The verb is what settles it,
and the verb only exists once pass 2 has built the actions.

**AND IT RUNS BEFORE GATE 3 BECAUSE GATE 3 IS ALREADY RIGHT AND ADDRESSED TO THE WRONG PERSON.**
Given `all the 'fleet' label` declared as an object, gate 3 correctly says *"add_label takes a
label, not a thing"* — and bounces it to the MODEL, which did nothing wrong. Pass 1 handed it a
bogus object. Settle the role first and gate 3 sees a corrected table, so what it reports is
genuinely the operation's fault.

# ⇒ RULE D8 — THE VERB DECIDES WHAT THE NOUN IS

    give X the 'fleet' LABEL      light verb + attribute-noun   ->  an ATTRIBUTE
    TAKE a snapshot               light verb + kind-noun        ->  an ACTION
    RESTORE a snapshot            contentful verb               ->  the OBJECT itself
    MAKE SURE there are two left  light verb + adjective        ->  a MOOD — achieve, not do

The names are established and this file uses them. `snapshot` is a **dot object**
(`event•object`) and the verb performs **type coercion** to select a facet; `take a snapshot`
is a **light verb construction**, where the verb empties itself and the noun carries the
predicate; whether the noun pre-exists is the **effected vs affected object** distinction,
which is this project's create/use fork under its proper name.

⇒ **AND THE MANIFEST ALREADY HOLDS THE QUALIA STRUCTURE**, so every test below is a lookup:
  `creators` is the AGENTIVE role, `acts` is the TELIC role, `setters` give the attribute slots.

# ⇒ THE TWO HALVES ARE NAMED SEPARATELY ON PURPOSE

`settle_*` CHANGES the table — it applies an answer the verb supplies, exactly as
`settle_with_world` applies one the lab supplies. `findings` only REPORTS. Keeping them apart
is what preserves *gates do not repair* as a property of the reporting half, now that the
stage as a whole is allowed to settle.
"""
from typing import Dict, List, NamedTuple, Optional, Tuple

from planner.formula.legal import Board
from . import schema as S
from .effects import Operation

# ⇒ A CLOSED CLASS OF ENGLISH, the same status `COMPARATORS` and `ENUMERATORS` hold. A light
#   verb contributes almost no meaning, so the NOUN beside it carries the predicate.
#
#   ⇒ **AND IT IS A POSITIVE ASSERTION ONLY — ABSENCE FROM THE MANIFEST DOES NOT MEAN LIGHT.**
#     The tempting move is to delete this list and derive it: a contentful verb is one the
#     manifest declares, so anything else is light. That is wrong in the exact place it matters.
#     *"find me a snapshot"* — `find` is not a declared operation, so absence would call it
#     light and read the snapshot as an ACTION, when it is plainly an object being selected.
#     Absence means *"either light, or an operation this lab does not have"*, and those two
#     need opposite treatment.
LIGHT_VERBS = frozenset({"take", "takes", "give", "gives", "make", "makes", "do", "does",
                         "get", "gets", "have", "has", "carry", "carries",
                         "perform", "performs", "conduct", "conducts"})

CONTENTFUL, LIGHT, UNKNOWN_VERB = "contentful", "light", "unknown"

# ⇒ THE MOOD MARKERS. A request in the ACHIEVE mood states a state that must HOLD; pass 2 only
#   knows how to DO. Every rung filed as a "reasoning error" — 7, 9, 14 — is one of these.
ACHIEVE_MARKERS = ("make sure", "makes sure", "ensure", "ensures", "there should be",
                   "should be", "must be", "make certain", "verify that", "confirm that")

DO, ACHIEVE = "do", "achieve"


class Finding(NamedTuple):
    rule: str            # mood-achieve · unexpressed-exclusion · count-ignored · role-unsettled
    about: str
    says: str
    audience: str        # "operator" | "model"

    def __repr__(self):
        return f"[linguistics/{self.rule}] {self.about}: {self.says}"


# ⇒ WHAT THE LINGUISTICS GATE OWNS: the request's GRAMMAR against the program's STRUCTURE.
#   `role-unsettled` used to be here and is not grammar — it is completeness, and it moved to
#   gate 1 where the leftover rule already lives.
OWNS = frozenset({"mood-achieve", "unexpressed-exclusion", "count-ignored",
                  "unasked-step", "light-verb-object", "unexpressed-choice",
                  "quoted-evidence", "unexpressed-magnitude"})


def mood_of(request: str) -> str:
    """DO or ACHIEVE. A light verb over an adjective marks a state to hold, not an act.

    ⇒ **THIS RENAMES THREE DEFECTS INTO ONE GAP.** *"make sure there are exactly two machines
      left"* is not a badly-parsed instruction — it is a GOAL, and the only thing pass 2 can
      say is `delete_vm(vms)`. No rephrasing fixed it because nothing was mis-read: asked to
      ENSURE two remain, the vocabulary offers only *remove them*.
    """
    low = f" {request.lower()} "
    return ACHIEVE if any(m in low for m in ACHIEVE_MARKERS) else DO


def manifest_verbs(board: Optional[Board] = None) -> set:
    """Every verb the lab actually declares. The head word of each operation it can perform.

    `add_label` -> add · `stop_vm` -> stop · `create_snapshot` -> create · and an act's own key
    is already a verb: `restore`, `kill`, `run`, `check`. READ, never listed (rule W5), so a
    lab that gains an operation gains its verb for free.
    """
    from planner.ir import config as _config
    out: set = set()
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        for group in ("setters", "unsetters", "acts", "creators"):
            for name in (spec.get(group) or {}):
                out.add(str(name).split("_")[0].lower())
        for key in ("delete", "create", "list"):
            if spec.get(key):
                out.add(str(spec[key]).split("_")[0].lower())
                out.add(key)
    return out


def verb_kind(word: str, board: Optional[Board] = None) -> str:
    """CONTENTFUL, LIGHT, or UNKNOWN — and the third is a real answer, not a default.

    ⇒ **THE MANIFEST PROVES CONTENTFUL; THE LIST PROVES LIGHT; NEITHER PROVES NOTHING.** A verb
      the lab declares carries the action itself, so the noun beside it is free to be an object.
      A verb on the closed list empties itself into the noun. A verb that is neither — `find`,
      `locate`, `show` — is UNSETTLED, and settling it by default is how the create/use fork
      gets broken. It is the same three-valued honesty as a kindless row: say you do not know.
    """
    word = str(word).strip(".,'\"").lower()
    if word in manifest_verbs(board):
        return CONTENTFUL
    if word in LIGHT_VERBS:
        return LIGHT
    return UNKNOWN_VERB


def evidence_for(operator: str, board: Optional[Board] = None) -> set:
    """The words in a request that would WARRANT this operation. Read from the manifest.

    ⇒ **AND WHAT COUNTS AS EVIDENCE DIFFERS BY WHAT THE OPERATION IS**, which is the whole
      difficulty. A naive rule — the operation's own name-words must appear — gets it backwards
      in both directions:

        `launch_vm` contains `vm`, so ANY request mentioning a machine would warrant launching
        it, and rung 4's unasked `launch_vm` stays invisible.

        `create_snapshot` split of its kind noun leaves only `create`, so rung 12's *"TAKE a
        snapshot"* — which is correct — would be called spurious.

      So a CREATOR is warranted by its KIND being named (*take a snapshot* -> a snapshot is
      wanted); a SETTER by its ATTRIBUTE or its own verb (*put them in a NETWORK*, *STOP it*);
      a PROBE by its attribute or the doc that defines it, which is how *"do not ANSWER"*
      reaches `probe_alive` without anyone listing `ping`.
    """
    from planner.ir import config as _config
    from .scan import _stem
    board = board or Board()
    out: set = set()
    from .scan import _index
    index = _index(board)
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        # ⇒ **PLURALS COME FROM THE MANIFEST'S OWN INDEX, WHICH ALREADY HAS THEM.** Building the
        #   noun set by hand gave the SINGULARS only, and the stemmer cannot rescue it —
        #   `_stem("vms")` is `"vms"`, because it refuses to strip an `s` from a word of three
        #   letters. So `create_vm` was reported as unasked on every request that says `vms`,
        #   and that false alarm is a large share of the bounces this check introduced.
        nouns = {w for w, k in index.items() if k == kind}
        nouns |= {kind} | {str(n).lower() for n in (spec.get("nouns") or [])}

        for name in (spec.get("creators") or {}):
            if operator == (f"create_{kind}" if name == "create" else f"{name}_{kind}"):
                out |= nouns | {str(name).lower()}          # the KIND is the evidence

        for group in ("setters", "unsetters"):
            meta = (spec.get(group) or {}).get(operator)
            if meta:
                # ⇒⇒ **A GRAMMAR WORD IS NEVER EVIDENCE, AND `to` COST RUNG 10 A WHOLE STEP.**
                #   Splitting `add_vm_to_network` on underscores yields `add`, `to`, `network` —
                #   and `to` is a preposition. *"clone golden INTO 3 new vms"* contains `into`,
                #   which matched, so a phantom `add_vm_to_network(vms, '3')` counted as WARRANTED
                #   BY THE REQUEST, anchored to a clause, and entered the program. There is no
                #   network in that sentence at all.
                #   ⇒ **THE HOUSEKEEPING TIERING IS WHAT SHOULD HAVE DROPPED IT** — an unwarranted
                #     step gets no clause anchor and becomes a SUGGESTION, shown and never run.
                #     A two-letter preposition was enough to defeat that, so the operator saw a
                #     bounce about a network they never mentioned.
                from .scan import GRAMMAR
                out |= {w for w in str(operator).lower().split("_")
                        if w not in nouns and w not in GRAMMAR}
                if meta.get("attr"):
                    out.add(str(meta["attr"]).lower())
                for alias, real in (spec.get("aliases") or {}).items():
                    # ⇒ AND AN ALIAS THAT IS A GRAMMAR WORD IS NOT EVIDENCE EITHER. `on` is
                    #   declared as an alias for `network`, and `clone` CONTAINS it — so rung
                    #   10's phantom `add_vm_to_network` stayed warranted even after `to` was
                    #   excluded. Same rule, the other source.
                    if real == meta.get("attr") and str(alias).lower() not in GRAMMAR:
                        out.add(str(alias).lower())
                # ⇒ **AN ATTRIBUTE'S VALUES ARE NOT EVIDENCE, AND ADDING THEM SERVED A
                #   SELF-CONTRADICTING PROGRAM.** `stopped` is a value of `status`, so it
                #   warranted `stop_vm` on *"launch every vm that is currently stopped"* — and
                #   the chain served `launch_vm` AND `stop_vm` on the same set. A value says
                #   WHICH THINGS ARE SELECTED; it says nothing about what to do to them.

        if operator == spec.get("delete"):
            out |= {"delete", "remove", "destroy", "wipe", "drop", "clear"}

        for fact, meta in (spec.get("observed") or {}).items():
            if operator == f"probe_{fact}":
                out.add(str(fact).lower())
                out |= {_stem(w.strip(".,'")) for w in str(meta.get("doc") or "").lower().split()
                        if len(w) > 5}

        if operator in (spec.get("acts") or {}):
            out.add(str(operator).lower())
    return {w for w in out if w}


def anchor_to_clauses(request: str, operations: List[Operation],
                      board: Optional[Board] = None) -> List[Tuple[str, Operation]]:
    """Which CLAUSE of the request warrants each step. Computed, never asked.

    ⇒⇒ **ASKING PER CLAUSE WAS BUILT, MEASURED AND REFUSED — 2026-08-10.** The model was given
      the whole request, the whole symbol table, and one clause marked as *the part to answer
      for*. It ignored the marking and answered for the whole request every time:

          rung 11  "ping every vm"                -> probe_alive AND stop_vm
                   "stop the ones that do not..." -> probe_alive AND stop_vm
          rung 3   "create a network called lab"  -> add_vm_to_network(lab, web)  <- swapped
          rung 2   "create a vm named beta"       -> add_label(beta, 'known at plan time')
                                                     <- the symbol table's `settled` column,
                                                        read back as a label value

      Duplicated steps, two new failure modes, and no narrowing. **A narrower ASK does not
      produce a narrower ANSWER** — the same law that killed the refusal enum and the `cannot`
      field, met from a third direction.

    ⇒ **SO THE ANCHORING IS ARITHMETIC.** `evidence_for` already says which words warrant an
      operation; running it against each clause instead of the whole request says WHICH PART
      warranted it. No call, no narrowing to ignore.

    An operation warranted by no clause is returned against `""` — which is exactly what
    `unasked-step` reports, now with the clause named when there is one.
    """
    from .pass2 import clauses_of
    from .scan import _stem
    board = board or Board()
    clauses = clauses_of(request)
    spoken = []
    for clause in clauses:
        words = {w.strip(".,'\"—–") for w in clause.lower().split()}
        words |= {_stem(w) for w in words}
        spoken.append((clause, words))

    out: List[Tuple[str, Operation]] = []
    for op in operations:
        warrant = evidence_for(op.operator, board)
        # ⇒ BEST MATCH, NOT FIRST MATCH, AND THE TARGET BREAKS THE TIE. `create_vm` is warranted
        #   by `create` in one clause and by `vm` in another; taking the first put it on the
        #   network's clause. The thing it ACTS ON decides: `create_vm(web)` belongs to the
        #   clause that says `web`.
        best, score = "", 0
        for clause, words in spoken:
            hit = len(warrant & words)
            if hit and str(op.on).lower() in clause.lower():
                hit += 2
            # ⇒⇒ **AND THE VALUE BONUS IS A TIE-BREAKER, NOT EVIDENCE — IT WAS UNGUARDED.**
            #   The target bonus above is gated on `hit`, this one was not, so an operation
            #   warranted by NOTHING could still anchor if its value happened to appear in the
            #   text. Rung 10: `add_vm_to_network(vms, '3')` has zero overlap with its warrant,
            #   and `'3'` appears in *"3 new vms"* — so a step about a network the request never
            #   mentions scored 1, anchored, entered the program and bounced at the operator.
            #   ⇒ **THIS IS WHO SHOULD HAVE DROPPED IT.** An unwarranted step gets no clause and
            #     becomes a SUGGESTION — shown, never run. A tie-breaker able to create a match
            #     from nothing defeated that, which is why the housekeeping tier never saw it.
            if hit and op.value and str(op.value).lower() in clause.lower():
                hit += 1
            if hit > score:
                best, score = clause, hit
        out.append((best, op))
    return out


def _roles(board: Board) -> Tuple[Dict[str, str], Dict[str, str], set]:
    """Every operator, by what it does to its target. READ from the manifest (rule W5).

    Returns (creator_of_kind, actor_on_kind, free_text_value_ops) — the AGENTIVE role, the
    TELIC role, and the setters whose value is a literal rather than a reference.
    """
    from planner.ir import config as _config
    creators: Dict[str, str] = {}
    actors: Dict[str, str] = {}
    literal_value: set = set()
    for kind, spec in (_config.KINDS or {}).items():
        if not isinstance(spec, dict):
            continue
        for name in (spec.get("creators") or {}):
            creators[f"create_{kind}" if name == "create" else f"{name}_{kind}"] = kind
        for group in ("setters", "unsetters"):
            for op, meta in (spec.get(group) or {}).items():
                actors[op] = kind
                if isinstance(meta, dict) and meta.get("value_arg") and not meta.get("refs"):
                    literal_value.add(op)
        for act in (spec.get("acts") or {}):
            actors[act] = kind
        if spec.get("delete"):
            actors[str(spec["delete"])] = kind
    return creators, actors, literal_value


# ── the settling half · IT CHANGES THE TABLE ──────────────────────────────────────────
def settle_with_verb(operations: List[Operation], table,
                     board: Optional[Board] = None) -> Tuple[List, List[Finding]]:
    """THE VERB ANSWERS — the twin of `settle_with_world`, and the same shape.

    A row whose handle is used ONLY as a literal value was never an object: *"give them all the
    'fleet' label"* puts `fleet` in the table as a thing, and `add_label(vms, 'fleet')` proves
    it is a LABEL. Drop it; the literal survives in the operation.

    ⇒ **A ROW IS ONLY EVER DROPPED WHEN IT IS NEVER A TARGET.** Dropping one that some
      operation points at would leave a dangling handle, which is the one thing D1 forbids.

    ⇒ **AND EXISTENCE IS CORRECTED FROM THE VERB, WHICH IS FREE AND BETTER THAN ASKING.** A
      creator's target is an EFFECTED object — it comes into being. An act's or setter's target
      is AFFECTED — it was already there. Pass 1 asks the model this and scores ~85% with every
      error toward `new`; *"what does the request DO to it?"* was measured to kill that bias
      outright, and this is that question answered by arithmetic.
    """
    board = board or Board()
    creators, actors, literal_value = _roles(board)
    targets = {str(op.on) for op in operations}
    literals = {str(op.value) for op in operations
                if op.value and op.operator in literal_value}

    # ⇒ ITERATE THE TABLE, NEVER THE ROWS. The table is the only thing that pairs a handle with
    #   its row, and the existence correction REPLACES the row object — so a filter keyed on
    #   object identity silently discarded `lab` from rung 3, which had merely been corrected
    #   from `existing` to `new`. Losing a declaration inside the step whose purpose is keeping
    #   references sound is exactly the failure this file exists to prevent.
    # ⇒ AND IT RETURNS THE TABLE, NOT THE ROWS. The table is the only thing pairing a handle
    #   with its row; carrying rows separately meant re-deriving that pairing afterwards, and
    #   the only key available was object identity — which the existence correction destroys.
    #   `lab` was corrected from `existing` to `new`, its row object replaced, and it vanished.
    out: List = []
    notes: List[Finding] = []
    for sym in table:
        row, handle = sym.row, sym.handle
        if handle in literals and handle not in targets:
            notes.append(Finding("light-verb-object", handle,
                                 f"{handle!r} is not a thing — the request uses it as a value, "
                                 f"and no operation acts on it", "model"))
            continue                       # a value phrase, never an object. Drop the row.

        # EXISTENCE, from the verb that governs it.
        governing = [op for op in operations if str(op.on) == handle]
        if governing and row.object_type != S.UNKNOWN_KIND:
            effected = any(op.operator in creators for op in governing)
            affected = any(op.operator in actors for op in governing)
            want = S.NEW if effected and not affected else (
                S.EXISTING if affected and not effected else row.existence)
            if want != row.existence:
                row = S.declare_from(row.name, row.object_type, row.where, want, board,
                                     references=list(row.references), count=row.count,
                                     comparator=row.comparator, span=row.span,
                                     identity=row.identity)
        out.append(sym._replace(row=row))
    return out, notes


# ── the reporting half · IT CHANGES NOTHING ───────────────────────────────────────────
def findings(request: str, rows: List[S.Declared], operations: List[Operation], table,
             goals: Optional[List[dict]] = None,
             board: Optional[Board] = None) -> List[Finding]:
    """Where the request's GRAMMAR says something the program does not express."""
    board = board or Board()
    out: List[Finding] = []
    creators, actors, _literal = _roles(board)
    targets = {str(op.on) for op in operations}

    # 1 · THE MOOD. A goal is not a plan.
    #
    # ⇒⇒ **AND IT ONLY COMPLAINS WHEN NOTHING STATES THE GOAL.** The finding says *"the plan
    #   only performs actions — nothing here checks it afterwards or corrects it"*, which was
    #   true while the scaffold carried steps and nothing else. As of 2026-08-11 an ACHIEVE
    #   request also carries the STATE it asks to hold (`schema.predicate_of`), and gate 4
    #   asks `planner.ir.derive` whether that state is reachable. When a goal is captured, the
    #   sentence above stops being true and the ASK stops being honest.
    #
    #   ⇒ THE UNCLOSEABLE CASE IS STILL ASKED — by GATE 4, which has the world and can say
    #     WHY. Rungs whose mood is ACHIEVE and whose goal nothing can state still land here.
    if mood_of(request) == ACHIEVE and operations and not goals:
        out.append(Finding("mood-achieve", request[:40],
                           "this asks for a state to HOLD, and the plan only performs "
                           "actions — nothing here checks it afterwards or corrects it",
                           "operator"))

    # ⇒⇒ 1c · A NUMERIC COMPARISON THE CONDITION CANNOT HOLD.
    #
    #   *"stop every vm with over 6gb of ram"* loses `over` and `6gb` into the span-grain
    #   residue check and declares A MACHINE CALLED `ram` — because `ram` is a declared ALIAS
    #   for `memory_mb` and pass 1 read it as a member name. It BOUNCES rather than serving,
    #   so the cost is service; the reading is still wrong.
    #
    #   ⇒ **`where` HOLDS ONE VALUE PER ATTRIBUTE AND CANNOT HOLD A COMPARISON**, which is a
    #     representation limit rather than a reading one. So this READS the comparison and says
    #     so, exactly as the choice and the quotation do — three findings, one shape: *the
    #     sentence says something the program does not express*.
    #   ⇒ THE COMPARATOR CLASS IS NEW AND THE ATTRIBUTE IS NOT: `scan.MAGNITUDE` is a closed
    #     class of English comparatives, and `ram`/`cores` resolve through the manifest's own
    #     `aliases`. A comparison whose attribute is undeclared is not raised at all.
    from .scan import magnitudes_in as _magnitudes
    for how, amount, unit, attr in _magnitudes(request, board):
        out.append(Finding("unexpressed-magnitude", f"{attr} {how} {amount}{unit}",
                           f"the request compares {attr} against {amount}{unit} — a condition "
                           f"here holds one VALUE, not a comparison, so that filter is not "
                           f"expressed",
                           "operator"))

    # ⇒⇒ 1a · A QUOTED CLAUSE IS EVIDENCE, AND NOTHING HAS EVER READ ONE.
    #
    #   *"alpha won't boot, the error says 'cannot allocate memory'"* — the quoted half
    #   correlates with no kind, no member and no archive entry, which is the exact profile of
    #   something unrelated, and it is the most important part of the sentence. Read as a value
    #   it becomes a machine name; read as nothing it is discarded.
    #
    #   ⇒ **SAID RATHER THAN SWALLOWED.** The alternative was to exempt those words quietly so
    #     they stop being candidate objects, and a word dropped without a word said is how a
    #     request gets half-read and looks whole. Until D1 gives evidence somewhere to GO, the
    #     honest move is to name it.
    #   ⇒ **AND ONE WORD IN QUOTES IS STILL A VALUE** — `scan.quoted_clauses` requires two,
    #     which is the whole of the rule and matches every quoted span in the corpus.
    from .scan import quoted_clauses as _quoted
    for _span in _quoted(request):
        out.append(Finding("quoted-evidence", _span[:40],
                           f"the request quotes {_span!r} — that reads as EVIDENCE rather "
                           f"than as anything to build, and nothing here can use it yet",
                           "operator"))

    # ⇒⇒ 1b · A DISJUNCTION IS A CHOICE, AND THE PROGRAM MADE IT WITHOUT ASKING.
    #
    #   *"stop alpha or beta"* came back `[stop_vm(beta), stop_vm(beta)]` — alpha dropped,
    #   beta doubled. It REFUSED, and only because the lab held neither machine; against a lab
    #   that holds them, **that serves**. Graded on the operations rather than the verdict,
    #   2026-08-16.
    #
    #   ⇒ **THE CLAUSE MUST NOT BE SPLIT.** Splitting a disjunction produces two orders, which
    #     is the acting-on-both this finding exists to stop. It is ONE clause carrying two
    #     candidates and no way to pick, and only the operator can pick.
    #   ⇒ **`or` IS ALREADY IN `CONJUNCTIONS`**, so no vocabulary is added — and `nor` with it,
    #     because a negated disjunction is the same choice with the sign flipped.
    #   ⇒ ⚠ AND IT ASKS ONLY WHEN SOMETHING WAS BUILT. A disjunction in a request that produced
    #     no operations is already being asked about by somebody; adding a second question for
    #     it is the misdirection the residue accounting was fixed for on rung 6.
    from .speech_act import words_of as _words_of
    _said = _words_of(request)
    if operations and ("or" in _said or "nor" in _said):
        out.append(Finding("unexpressed-choice", request[:40],
                           "the request offers a CHOICE — 'or' — and the plan does not make "
                           "one. Which did you mean, or did you mean both?",
                           "operator"))

    # 2 · AN EXCLUSION THE PROGRAM DOES NOT MAKE.
    #
    # ⇒ RUNG 8 IS WRONG TODAY AND NOTHING CATCHES IT. *"put every vm on core, EXCEPT db"*
    #   produces `add_vm_to_network(core_vms, core)` where `core_vms` is EVERY machine — db
    #   included — and then puts db on dmz as well. The exclusion is simply unexpressed, and
    #   the residue check already sees the word and routes it to "pass 2's" with nothing there
    #   to receive it.
    low = request.lower()
    excluders = [w for w in ("except", "excluding", "besides", "instead", "apart from")
                 if w in low]
    # ⇒⇒ **AND IT IS EXPRESSED NOW, WHEN THE SET CARRIES IT.** 2026-08-11: an `except` clause
    #   attaches to the set it narrows (`pass1.attach_exclusions`), so `every vm … except db`
    #   declares `vm_set {network: core} EXCLUDES db` rather than leaving a floating row. The
    #   comment above — *"no operation can express an exclusion"* — was true of the OPERATION
    #   vocabulary and always missed the point: the exclusion belongs to the SET, not the step.
    #
    #   ⇒ SO THE CHECK NOW ASKS WHETHER ANYTHING CARRIES IT, and only complains when nothing
    #     does. A detector standing in front of a hole becomes a detector standing behind a
    #     fix — which is the only honest reason to keep one.
    carried = any(getattr(row, "excludes", ()) for row in (rows or ()))
    if excluders and operations and not carried:
        out.append(Finding("unexpressed-exclusion", excluders[0],
                           f"the request excludes something ({excluders[0]!r}) and no "
                           f"operation can express an exclusion — every step applies to the "
                           f"whole set", "operator"))

    # 3 · A COUNT NOBODY RESPECTS.
    #
    # ⇒ RUNG 14: the declaration carries `eq 2` and the operation is `delete_vm(vms)` over the
    #   whole set. The bound is stated and unused, and there is NO WAY TO SAY a bounded action
    #   — the operation schema has no count field. So this reports rather than bounces: asking
    #   the model again for something unsayable is the trap D5 keeps walking into.
    for sym in table:
        # ⇒ ONLY A NUMERIC BOUND IN THE ACHIEVE MOOD, and both halves of that are load-bearing.
        #   `a vm` carries count 1 from its ARTICLE and `every vm` carries "all" — neither is a
        #   bound, and reporting them accused rungs 3 and 11 of ignoring something nobody said.
        #   And in the DO mood a count is a QUANTITY TO PRODUCE: *"create 5 vms"* is satisfied
        #   by creating five. It is only a bound to maintain when the request asks for a state.
        if not isinstance(sym.row.count, int) or sym.row.count <= 1:
            continue
        if sym.handle not in targets:
            continue
        # ⇒ **IF A CREATOR MAKES THE SET, THE COUNT IS A QUANTITY PRODUCED — NOT A BOUND.**
        #   *"create 5 vms"* is satisfied by creating five, and flagging it accused rung 4 of
        #   ignoring something it was doing. It is only a bound to MAINTAIN when the plan acts
        #   on a set it did not bring into being: rung 14 deletes, rung 7 labels. That is the
        #   effected/affected distinction again, and it settles this better than the mood does
        #   — rung 4 is in the ACHIEVE mood too, because of a different clause entirely.
        if any(op.operator in creators for op in operations if str(op.on) == sym.handle):
            continue
        # ⇒⇒ **AND A COUNT A GOAL STATES IS NOT A COUNT NOBODY EXPRESSED.** This finding says
        #   *"no operation expresses the bound"* — true while steps were the only way to say
        #   anything. As of 2026-08-11 an ACHIEVE request carries the bound AS A PREDICATE, and
        #   the goal is precisely a statement of that count. Complaining here would be accusing
        #   the scaffold of omitting the thing it now leads with.
        #   ⇒ THIRD CHECK TODAY THAT ASSUMED STEPS WERE THE ONLY EXPRESSION — after
        #     `mood-achieve` and gate 1's `unused-declaration`. When a new way to SAY something
        #     is added, every check that tested for the old way is quietly wrong.
        if any(S.governs(g, sym.row) for g in (goals or ())):
            continue
        bound = f"{sym.row.comparator or 'eq'} {sym.row.count}"
        out.append(Finding("count-ignored", sym.handle,
                           f"the request bounds {sym.handle!r} at {bound} and no operation "
                           f"expresses that bound — the plan acts on the whole set",
                           "operator"))

    # 5 · A STEP NOTHING IN THE REQUEST WARRANTS.
    #
    # ⇒ **GATE 3 ASKS WHETHER A STEP IS LEGAL; NOTHING ASKED WHETHER IT WAS WANTED.** Rung 4
    #   came back with `launch_vm` on machines nobody asked to launch, rung 13 with
    #   `create_snapshot` on a request that never mentions a snapshot, rung 14 with `delete_vm`
    #   on a request that never says delete. Every one is perfectly legal, so every one served.
    #   Over-production was the dominant defect the moment the accidental nets came down.
    from .scan import _stem
    said = {_stem(w.strip(".,'\"—–")) for w in request.lower().split()}
    said |= {w.strip(".,'\"—–") for w in request.lower().split()}
    # ⇒⇒ AND NOT AT ALL IN THE ACHIEVE MOOD. Asked to bring a STATE about, the model must
    #   choose actions the request never names — that is what an achieve request IS. Reporting
    #   those as unwarranted told the MODEL to fix rung 14, when the only thing wrong is a mood
    #   this pipeline cannot express, and no answer it gives can settle that. The mood finding
    #   already says so, to the right audience.
    unsettled = {sym.handle for sym in table if sym.row.object_type == S.UNKNOWN_KIND}
    flagged: set = set()
    # ⇒ THE CLAUSE IS COMPUTED, AND A STEP WITH NONE IS THE UNWARRANTED ONE. Same verdict as
    #   before, with the part of the request that warranted it named — which is what a partial
    #   serve will need when the verdict stops being per-request.
    anchored = dict((id(op), clause)
                    for clause, op in anchor_to_clauses(request, list(operations), board))
    for op in (() if mood_of(request) == ACHIEVE else operations):
        # ⇒ NOT WHILE THE TARGET IS UNIDENTIFIED, and not twice for the same operator. Rung 9's
        #   `add_label` is unwarranted whatever `n1` turns out to be — but reporting it to the
        #   MODEL says "fix this", and the model cannot: what blocks that rung is a question
        #   only the operator can answer. Same guard as `role-unsettled`, for the same reason.
        if str(op.on) in unsettled or op.operator in flagged:
            continue
        warrant = evidence_for(op.operator, board)
        if warrant and not anchored.get(id(op)):
            flagged.add(op.operator)
            out.append(Finding("unasked-step", op.operator,
                               f"no clause of the request asks for {op.operator!r} — no part "
                               f"of it warrants this step", "model"))

    return out


def report(request: str, rows: List[S.Declared], operations: List[Operation], table,
           board: Optional[Board] = None, goals: Optional[List[dict]] = None):
    """Settle first, then report on what survived. Returns (rows, table, findings)."""
    board = board or Board()
    # ⇒ THE HANDLES ARE CARRIED THROUGH UNCHANGED, NEVER REGENERATED. `symbol_table` assigns
    #   them in row order with a dedupe counter, so rebuilding after a row is dropped can
    #   RENAME a handle the operations already point at — turning a sound reference into a
    #   dangling one, inside the step whose whole purpose is keeping references sound.
    fresh_table, notes = settle_with_verb(operations, table, board)
    settled = [sym.row for sym in fresh_table]
    return settled, fresh_table, notes + findings(request, settled, operations, fresh_table,
                                                  goals=goals, board=board)
