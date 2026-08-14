"""GATE 4 — IS THIS WORTH SERVING? Not whether it is legal; whether it should be run.

⚠ MODEL-SPECIFIC TUNING LIVES UPSTREAM — see two-pass-rules.md §4b.

# ⇒⇒ WHY THIS EXISTS AS A GATE AND NOT AS A LINE IN THE PIPELINE

The destructive guard was written in `pipeline.py`, and I said at the time that it belonged
here. It stayed there for two days. That is exactly how a check ends up owned by nobody:

    gate 1  did you say this?          faithfulness to the request
    gate 2  can the world hold it?     the manifest, and the lab
    gate 3  is this operation legal?   the program, against what an operation may be
    gate 4  is it worth serving?       ⇐ IMPACT. Nothing above asks this.

**A step can be perfectly faithful, perfectly grounded and perfectly legal, and still be a
thing you would want to be asked about before it runs.** That is the whole of gate 4, and it is
why no other gate can hold it.

# ⇒ THE ONE RULE IT HAS, AND THE CORPSE

    rung 14  'make sure there are exactly two machines left'
      declared    vms                                  every machine, count eq 2
      operations  delete_vm(vms) · probe_exists(vms)
      ⇒ SERVE

`delete_vm` over the unfiltered set of every machine, and every check passed. Gate 3 was RIGHT
to stay quiet — nothing about it is illegal. The declaration says how many should be LEFT, the
operation says what to remove, and no gate compared the two.

⇒ **AND IT ASKS RATHER THAN REFUSING.** A high-impact act takes the operator's word, and only
  the operator can give it ([[gorgon-security-invariants]]).

⇒ **THE EXEMPTION IS THE REQUEST, NOT THE TARGET.** The first version exempted a NAMED
  individual, reasoning that deleting something named is no surprise. Rung 8 disproved it:
  *"db goes on a network called dmz"* produced `delete_network(dmz)` — the operator named `dmz`
  as a CREATE target, not as a delete target. So what matters is whether the REQUEST asks to
  destroy anything at all.
"""
from typing import List, Optional

from planner.formula.legal import Board
from .effects import Operation

# ⇒ THE COMPLETE SET OF ENGLISH RECIPROCAL PRONOUNS. Two of them, and there is no third —
#   closed the way `INDEFINITE`/`DEFINITE` are closed, which is what separates this from a
#   curated content-word list like `ACHIEVE_MARKERS`.
RECIPROCAL = ("each other", "one another")

DESTRUCTIVE_WORDS = ("delete", "remove", "destroy", "tear down", "get rid",
                     "wipe", "drop", "kill off", "clear out")


def _destroyers(board: Board):
    """Each kind's declared destructive operation. READ, never listed (rule W5)."""
    from planner.ir import config as _config
    return {str(spec["delete"]): kind
            for kind, spec in (_config.KINDS or {}).items()
            if isinstance(spec, dict) and spec.get("delete")}


def unhonourable_exclusions(table, board: Optional[Board] = None) -> List[str]:
    """A set that leaves something out, that the ENGINE could not actually express.

    ⇒⇒ **THE HANDOFF THAT WAS ASSUMED, NOW CHECKED.** `attach_exclusions` makes rung 8's set
      `all vms but db` and rung 8 SERVES on the strength of it — but nothing in the orchestrator
      subtracts a member from anything (`Lab.select` is exact-match, and no code here enumerates
      a set at all). **The correctness of a served program therefore rests on the engine
      honouring `excludes`,** and until now nothing verified it could. That is exactly the shape
      this session kept finding: a rule that only half the path knows about.

    ⇒ **SO IT IS ASKED OF THE IR'S OWN VALIDATOR, NEVER RE-DECIDED HERE.** The engine's select
      supports `not` — `{"kind": "vm", "network": "core", "not": {"name": "db"}}`, whose schema
      doc is literally *'every vm except db'* — so the contract IS honourable. Constructing the
      select the engine would need and validating it is the difference between knowing that and
      assuming it. If a future manifest or IR change withdraws `not`, this says so on the next
      run instead of serving a program that quietly includes what the operator excluded.

    ⇒ AND IT IS GATE 4's BY GRAIN: viability of the assembled scaffold, statable only about the
      whole — *can what we are proposing actually be carried out?*
    """
    import importlib

    from . import schema as S

    # ⇒ `planner.ir.__init__` RE-EXPORTS THE FUNCTION `validate`, WHICH SHADOWS THE MODULE OF
    #   THE SAME NAME — the same trap `planner.ir.derive` sets. Imported by path so the module
    #   is what arrives, not its namesake.
    _validate = importlib.import_module("planner.ir.validate")
    board = board or Board()
    out: List[str] = []
    for sym in table:
        row = sym.row
        if not getattr(row, "excludes", ()) or row.kind not in board.kinds:
            continue
        # ⇒ ONE BUILDER — `schema.select_of` — so this validates the select the engine would
        #   actually receive, not a second construction of my own that could differ from it.
        #   It carries EVERY carve-out (`all` of `not`s), so a set leaving out two things has
        #   both checked rather than one.
        sel = S.select_of(row, board)
        problems = _validate._check_select(sel, f"select for {sym.handle}") if sel else []
        if problems:
            carved = "; ".join(str(f) for f in row.excludes)
            out.append(f"[gate4/exclusion-not-expressible] {sym.handle!r} leaves out {carved} and the engine cannot express "
                       f"that: {problems[0]}")
    return out


def duplicate_creations(operations, table, board: Optional[Board] = None) -> List[str]:
    """One thing, two makers. The scaffold brings the same row about twice.

    ⇒⇒ **RUNG 10, THE LAST LAYER.** *"clone golden into 3 new vms"* came back as
      `create_vm(vms)` AND `clone_vm(vms, golden)` — the machines made once fresh and once as
      copies. Neither reading is the request, and an engine handed both has no way to know that
      only one was meant. Every step is legal on its own, which is why gate 3 stayed quiet.

    ⇒ **IT NEEDS TWO STEPS TO STATE, SO IT IS GATE 4's BY GRAIN** — viability of the assembled
      whole, exactly the re-charter's test. And it BOUNCES rather than asks: the request says
      *clone*, the words are there, and choosing between two creators is the model's own miss.

    ⇒ AND THE MAKERS ARE READ OFF THE MANIFEST, so a kind that gains a second creator is covered
      without an edit here.
    """
    from .gate3 import _makers
    board = board or Board()
    by_handle = {sym.handle: sym.row for sym in table}
    made_by: dict = {}
    for op in operations:
        row = by_handle.get(str(op.on))
        if row is not None and op.operator in _makers(row.kind):
            made_by.setdefault(str(op.on), []).append(op.operator)
    out: List[str] = []
    for handle, makers in made_by.items():
        if len(makers) > 1:
            out.append(f"[gate4/duplicate-creation] {handle!r} is brought about twice — by "
                       f"{' and by '.join(sorted(set(makers)))}. Only one of them was asked "
                       f"for; keep the one the request names and drop the other.")
    return out


def destructive_goals(goals: List[dict], world=None,
                      board: Optional[Board] = None) -> List[str]:
    """A GOAL whose closure removes things. The operator confirms that, exactly as for a step.

    ⇒⇒ **A HOLE OPENED ON 2026-08-11 AND A FAILING TEST IS WHAT FOUND IT.** `confirmations`
      watches the OPERATIONS — and once an ACHIEVE goal replaced the steps it governs, rung 14's
      `delete_vm(vms)` stopped being proposed, so the destructive guard stopped seeing anything.
      **The scaffold still means deletion**: *"make sure there are exactly two machines left"*
      against a lab holding six closes by removing four. A confirmation that vanishes because
      the request got a better representation is a guard that fails exactly when the request
      is understood properly.

    ⇒ **SO WHAT THE GOAL WOULD DO IS ASKED OF `derive`, AND THE ANSWER IS READ FOR DESTROYERS.**
      No judgement here: the same deriver the engine will use, the same manifest-declared
      `delete` operators `confirmations` already reads. If the closure happens to need no
      removal — rung 14 against a lab of exactly two — there is nothing to confirm and this
      stays silent, which is why it must ask the world rather than assume.
    """
    import importlib

    if world is None or not goals:
        return []
    _derive = importlib.import_module("planner.ir.derive")
    from planner.ir.intent import ACHIEVE as _INTENT_ACHIEVE

    board = board or Board()
    destroyers = set(_destroyers(board))
    select = _name_select(world, board)
    out: List[str] = []
    for goal in goals:
        try:
            plan = _derive.derive(goal, select, {}, _INTENT_ACHIEVE) or []
        except Exception:
            continue
        removed = [s for s in plan
                   if str((s.get("call") or {}).get("tool") or s.get("tool")) in destroyers]
        if not removed:
            continue
        sel = goal.get("select") or {}
        bound = ", ".join(f"{k} = {v}" for k, v in sel.items() if k != "kind")
        n = sum(len(s.get("in") or ()) for s in removed) or len(removed)
        out.append(f"[gate4/destructive-goal] holding {sel.get('kind')}s{' where ' + bound if bound else ''} at the "
                   f"number you asked for means REMOVING {n} of them, and the request never "
                   f"says to remove anything. Confirm before this runs.")
    return out


def goals_of(rows, request: str, board: Optional[Board] = None) -> List[dict]:
    """The states an ACHIEVE request asks to HOLD. Empty for a request that only asks to DO.

    ⇒ THE MOOD DECIDES WHETHER THERE IS A GOAL AT ALL. *"launch every stopped vm"* is a DO —
      the steps are the whole of it. *"make sure exactly 3 vms carry prod"* is a state, and
      the steps are only whatever closes the gap today.
    """
    from . import schema as S
    from .linguistics import ACHIEVE, ACHIEVE_MARKERS, mood_of
    if mood_of(request) != ACHIEVE:
        return []
    board = board or Board()

    # ⇒⇒ **THE GOAL MUST BE STATED IN THE ACHIEVE CLAUSE, NOT MERELY SOMEWHERE IN THE REQUEST.**
    #
    #   Rung 4 — *"create 5 vms, put them all in a network, give them all the 'fleet' label,
    #   and MAKE SURE THEY ALL PING EACH OTHER"* — is ACHIEVE mood and has a row carrying
    #   `count=5`. Without this, `count(vm) eq 5` would be captured as the goal, `derive` would
    #   call it reachable, and `mood-achieve` would fall silent — **while the thing actually
    #   asked for, mutual reachability, went unaddressed.** A FALSE SERVE, and strictly worse
    #   than the ASK it replaced.
    #
    #   ⇒ SO A ROW ONLY STATES THE GOAL IF ITS SPAN FALLS AFTER THE MARKER. `make sure exactly
    #     3 vms carry prod` puts the count inside the clause; rung 4 puts it three clauses
    #     earlier, describing what to BUILD rather than what must HOLD.
    #   ⇒ AND `reach` — *ping each other* — IS A PREDICATE `derive` CAN CLOSE (`_derive_reach`)
    #     but `predicate_of` cannot yet BUILD. Until it can, rungs 4 and 13 must keep asking.
    low = request.lower()
    at = min((low.index(m) for m in ACHIEVE_MARKERS if m in low), default=None)
    if at is None:
        return []

    out: List[dict] = []
    for row in rows:
        span = str(row.span or row.name).lower()
        where = low.find(span)
        if where < 0 or where < at:
            continue                      # stated before the marker: not what must HOLD
        goal = S.predicate_of(row, board)
        if goal:
            out.append(goal)

    # ⇒⇒ A RECIPROCAL CLAUSE STATES A `reach` GOAL, AND IT HAS NO NOUN OF ITS OWN.
    #
    #   Rungs 4 and 13 end *"...and make sure they all ping EACH OTHER"* — a pronoun and a
    #   reciprocal, so the span test above can never reach it: the set it speaks about was
    #   named three clauses earlier. Six places in this codebase discuss this clause as the
    #   unsolved one; nothing detected it.
    #
    #   ⇒ **`each other` / `one another` IS THE COMPLETE SET OF ENGLISH RECIPROCAL PRONOUNS.**
    #     Two entries, closed the way the determiners are closed — not a curated content list,
    #     which is the distinction the operator drew and the one `ACHIEVE_MARKERS` fails.
    #
    #   ⇒ **AND THE SUBJECT IS FOUND BY ARITHMETIC, NOT BY RESOLVING THE PRONOUN.** A reciprocal
    #     needs a plurality; if the request declares EXACTLY ONE set whose kind the manifest
    #     knows, that is what "they" can only mean. Zero or several and there is no goal — rung
    #     9's `n1, n2, n3` are kindless singles, so it captures nothing and keeps asking *what
    #     is n1?*, which is the correct answer. Same zero/one/several honesty as elsewhere.
    if any(r in low[at:] for r in RECIPROCAL):
        plural = [r for r in rows if r.is_set and r.kind in board.kinds]
        if len(plural) == 1:
            sel = S.select_of(plural[0], board)
            if sel:
                out.append({"shape": "reach", "select": sel})
        elif not plural:
            # ⇒⇒ **A COORDINATION OF SINGULARS IS A PLURALITY TOO** — the operator's *"even
            #   though it's singular we should still treat it as a set"*, and rung 9 is the
            #   case: *"make sure n1, n2 AND n3 can all ping each other"* declares three
            #   separate machines, not one set. A reciprocal needs two or more things; three
            #   named rows of one kind ARE the two or more.
            #
            #   ⇒ AND IT IS EXPRESSED AS MEMBERSHIP, WHICH THE IR ALREADY TAKES:
            #     `{kind: vm, name: {in: [n1, n2, n3]}}` — one select over the three, rather
            #     than three goals that would each be trivially true alone. Reachability is a
            #     relation; a goal about one machine could not state it.
            from planner.gates import claims as _claims
            named: dict = {}
            for row in rows:
                if row.is_set or row.kind not in board.kinds:
                    continue
                key = _claims.key_of(row.kind, board.kinds)
                value = (row.where or {}).get(key) or row.identity
                if key and value:
                    named.setdefault(row.kind, []).append(str(value))
            for kind, values in named.items():
                if len(values) >= 2:
                    key = _claims.key_of(kind, board.kinds)
                    out.append({"shape": "reach",
                                "select": {"kind": kind, key: {"in": sorted(values)}}})
    return out


def _name_select(world, board: Board):
    """`world.select` normalised to the contract `derive` and the book keeper both assume:
    a query in, a list of NAMES out. A mount that already returns names passes through."""
    from planner.gates import claims as _claims

    def select(query):
        rows = world.select(query) or []
        out = []
        for r in rows:
            if isinstance(r, str):
                out.append(r)
                continue
            kind = (query or {}).get("kind") or (r.get("kind") if isinstance(r, dict) else None)
            key = _claims.key_of(kind, board.kinds) if kind in board.kinds else None
            out.append(str(r.get(key) if key and isinstance(r, dict) else
                           (r.get("name") if isinstance(r, dict) else r)))
        return out
    return select


def unreachable_goals(goals: List[dict], world=None,
                      board: Optional[Board] = None) -> List[str]:
    """An ACHIEVE goal nothing could close. ASKED OF `planner.ir.derive`, never re-decided.

    ⇒⇒ **GATE 4's FIRST REAL VIABILITY DUTY** — *can the assembled scaffold actually be carried
      out?* — as distinct from its impact duty. `derive` answers in three values and they map
      straight onto verdicts, so nothing here has to judge:

          []            already true          nothing to do, and that is a SERVE
          statements    reachable             the scaffold is viable; MEDUSA writes the loop
          None          nothing can close it  ASK, and now for a stated reason

    ⇒ **THE ORCHESTRATOR NEVER SEES THE STATEMENTS.** It learns only whether the goal is
      closeable. Emitting the `foreach` here would put the orchestrator back into code
      generation, which is the engine's job and the boundary rule D7 exists to hold
      ([[gorgon-orchestrator-proposes-a-scaffold]]).
    """
    import importlib

    from .linguistics import ACHIEVE as _MOOD_ACHIEVE  # noqa: F401  (documents the caller)
    _derive = importlib.import_module("planner.ir.derive")
    from planner.ir.intent import ACHIEVE as _INTENT_ACHIEVE

    if world is None:
        return []            # ⇒ NO WORLD, NO ANSWER. Absent is not the same as unreachable.

    # ⇒⇒ `derive` EXPECTS `select` TO RETURN **NAMES**; THE BENCH LAB RETURNS ROW DICTS.
    #   Measured 2026-08-11: unadapted, `_derive_count` reached `sorted(pool)` over dicts,
    #   raised, and the `except` below turned the crash into *"not reachable"* — **a false ASK
    #   produced by a contract mismatch, wearing the costume of a real finding.** Two consumers
    #   of one seam disagreeing about its type is the same defect this session found eight
    #   times; adapting HERE, at the boundary, keeps the disagreement from spreading.
    select = _name_select(world, board or Board())

    out: List[str] = []
    for goal in goals:
        try:
            plan = _derive.derive(goal, select, {}, _INTENT_ACHIEVE)
        except Exception:
            # ⇒ CONSERVATIVE, AND DELIBERATELY SO: a goal we could not evaluate is one we
            #   cannot promise, so it is ASKED rather than served. But note what that cost
            #   above — an error and an unreachable goal report identically, which is why the
            #   mismatch hid. If this fires again, suspect the seam before the goal.
            plan = None
        if plan is None:
            # ⇒ THE MESSAGE FOLLOWS THE SHAPE. A count that cannot be reached and a set that
            #   cannot be made mutually reachable are different failures, and one wording for
            #   both told the operator the wrong thing about rung 9.
            sel = goal.get("select") or {}
            kind = sel.get("kind")
            named = sel.get(next((k for k in sel if k != "kind"), ""), None)
            listed = (", ".join(str(x) for x in named["in"])
                      if isinstance(named, dict) and "in" in named else None)
            who = f"{kind}s {listed}" if listed else f"{kind}s"
            if goal.get("shape") == "reach":
                out.append(f"[gate4/goal-unreachable] nothing here can make {who} able to reach each other — they are "
                           f"not in the lab, so there is nothing to connect")
            else:
                bound = ", ".join(f"{k} = {v}" for k, v in sel.items() if k != "kind")
                out.append(f"[gate4/goal-unreachable] nothing available can make {kind}s"
                           f"{' where ' + bound if bound else ''} come out at the number asked "
                           f"for — the goal is stated but not reachable from here")
    return out


def confirmations(operations: List[Operation], table, request: str = "",
                  board: Optional[Board] = None) -> List[str]:
    """What the operator must agree to before this runs. Never a refusal, always a question."""
    board = board or Board()
    destroyers = _destroyers(board)
    by_handle = {sym.handle: sym for sym in table}
    asked_to_destroy = any(word in request.lower() for word in DESTRUCTIVE_WORDS)

    out: List[str] = []
    for op in operations:
        if op.operator not in destroyers:
            continue
        sym = by_handle.get(str(op.on))
        if sym is None:
            continue
        if asked_to_destroy and not sym.row.is_set:
            continue          # they said to remove it, and named the one thing to remove
        bound = ", ".join(f"{k} = {v}" for k, v in (sym.row.where or {}).items())
        narrow = (" — narrowed only by " + bound if bound else
                  " — NOTHING NARROWS IT" if sym.row.is_set else "")
        out.append(f"[gate4/destructive-confirm] {op.operator}({op.on}) removes {sym.definition}{narrow}, and the request "
                   f"never asks to remove anything. Confirm before this runs.")
    return out


# ⇒ DECLARED, NOT FITTED, and it must stay that way until held-out prompts exist. The measured
#   shares are literal 21% · filler 58% · asked 54% · framed 72%, so a half is comfortably above
#   the plain-order band without being tuned to sit between any two arms — and it separates
#   NOTHING on its own, which is why it is the one input that cannot promote by itself. Anything
#   more precise than a round number here would be fitted to fourteen sentences.
_ANSWER_CONFIDENCE = 0.5


def answer_not_act(operations: List[Operation], table=(), request: str = "",
                   board: Optional[Board] = None, world=None, goals=None) -> List[str]:
    """THE REQUEST ASKED TO BE TOLD SOMETHING AND THE PROGRAM WOULD CHANGE THE LAB.

    ⇒⇒ **WHY THIS IS GATE 4's AND NOT THE DOOR'S.** At the door there is only a sentence, and
      *"is this a question?"* is a call the model was measured at near-chance on (2026-08-14:
      asked whether `ping` was a thing or an action, 2/3 on one rung and 0/3 on its twin).
      Here there are four sources of evidence — what was said, what it was read as, **what the
      program would DO**, and what the lab holds. So the question does not have to be the hard
      linguistic one. It is K5's shape instead: *this program acts; did the request authorise
      acting?* Prove authority rather than detect an interrogative.

    ⇒⇒ **IT MAY ASK. IT MAY NEVER GRANT.** The asymmetry is `intent.permits`': FETCH and
      ENSURE cannot change the lab and ACHIEVE can, so only one direction of this decision is
      irreversible. This function can turn a proposed act into a question and can do nothing
      else — it never hands out an authority the operator did not, and it never silently
      re-routes. Same rule, same reason as [[gorgon-courtesy-escalates-intent]].

    ⇒ **ABSENCE IS NOT EVIDENCE, AND THAT IS WHAT KEEPS THE LADDER WHOLE.** It fires only when
      `declared()` POSITIVELY names a rung that cannot change the lab. Measured over all
      fourteen rungs on 2026-08-14: every one returns `None`, so this is silent on the entire
      corpus and cannot cost a SERVE. Firing on absence instead would have turned 13 SERVE
      into 14 ASK — the whole ladder — which is what a guard looks like when it is written
      against the case its author had in mind rather than against the corpus.

    ⇒ ⚠ **IT IS NOT A SECOND `intent.violations`.** That function REFUSES an acting op under a
      granted FETCH, and it is the enforcement. This one exists because the front seam grants
      nothing at all — `pipeline.py` never resolves an intent, so `violations(program, None)`
      refuses nothing and there is no authority step on this path. The two do not overlap:
      one guards a grant that was made, this guards a request that was never granted.

    ONE FINDING, NOT ONE PER OPERATION. The mismatch is a single fact about the request — it
    asked to be told — and reporting it once per acting call would report the same fact four
    times for a four-step program. The calls are named inside it instead.
    """
    board = board or Board()
    from planner.ir import config as _config, effects as _effects
    from .residue import kindless as _kindless

    acting = _effects.actors(_config.KINDS)
    hits = [op for op in operations if op.operator in acting]
    if not hits:
        return []                      # it already answers rather than acts — nothing to ask

    # ⇒⇒ THE TRIGGER IS RESIDUE, AND IT USED TO BE `intent.declared()`. Changed 2026-08-14
    #   after testing the rule end to end rather than assuming it worked.
    #
    #   THE MARKER LIST COULD NOT BE THE TRIGGER. The rule fired only on a POSITIVE
    #   fetch/ensure — and the courtesy fix shipped the same morning makes `declared()` return
    #   None whenever the sentence names an ACT. A request that should trigger this declares a
    #   read AND acts, and the reason it acts is almost always a verb on the achieve list:
    #
    #       "list the vms and stop the ones running"    -> None   (stop is a marker)  silent
    #       "list the vms and remove the fleet label"   -> fetch  (remove is not)     FIRED
    #
    #   **So whether the safety rule engaged depended on whether the acting verb happened to
    #   be on a hand-written English list.** That is a coin toss, not a trigger.
    #
    #   ⇒ RESIDUE IS MEASURED WHERE THAT WAS ARBITRARY: a span the world cannot account for is
    #     conversational wrapper, and wrapper is what a request carries when it is asking
    #     rather than ordering. literal 1/14 · filler 14/14 · asked 11/14 · framed 14/14,
    #     bit-stable over three seeds and reproduced against a real lab.
    #
    #   ⚠ IT TRIGGERS A QUESTION AND NEVER A VERDICT, which is the whole of what it can
    #     honestly do: residue cannot tell a POLITE ORDER from a question — both carry
    #     wrapper — so it fires on courtesy too. A question costs a question; executing one
    #     cannot be taken back.
    # ⚠⚠ **RESIDUE IS THE TRIGGER AND IT IS A STAND-IN. The trigger should be INTENT.**
    #
    #   The operator, 2026-08-14, naming the three jobs: *"intent for information is measurable
    #   in linguistics; a viable query is evidence the question can be answered; the confidence
    #   threshold is a way to make sure the AI didn't make an educated guess."* Read that way
    #   the parts are WANTED / POSSIBLE / RELIABLE — and residue is the third, not the first.
    #
    #   ⇒ **THE COST OF HAVING IT FIRST IS MEASURED, NOT FEARED.** *"list the vms and remove the
    #     fleet label from them"* declares a read AND would act — the case this rule exists for
    #     — and carries no wrapper at all, so a residue trigger is silent on it. A plainly
    #     worded question leaves nothing over to detect.
    #
    #   ⇒ **AND `intent.declared()` IS NOT THE ANSWER EITHER**, which is why it is not wired
    #     back in: it is a hand-written marker list that returns None the moment a sentence
    #     names an act, so it fired or not depending on which verb the request happened to use
    #     ([[gorgon-courtesy-escalates-intent]] is the same list, one harm earlier).
    #
    #   THE REAL TRIGGER IS AN INFORMATION-INTENT READING FROM THE LINGUISTICS, and `mood_of`
    #   has two values today. Until it has three, this fires on what it can see.
    rows = [s.row for s in table] if table else []
    leftover = _kindless(rows, request, board, world)
    if not leftover:
        return []

    calls = ", ".join(dict.fromkeys(f"{op.operator}({op.on})" for op in hits))
    spans = ", ".join(repr(r.span or r.name) for r in leftover[:3])

    # ⇒⇒ **THREE THINGS DECIDE WHAT TO SAY, AND ONLY THE FIRST TWO ARE REQUIRED.** The operator,
    #   2026-08-14: *"a query and intent are needed, confidence is not but it's taken into
    #   consideration; above a certain confidence it's allowed."*
    #
    #   1 · A VIABLE QUERY — could the answer actually be given? An ask that offers a branch
    #       the system cannot honour invites the operator to choose a failure. Where none is
    #       producible the finding still SAYS what it read, and offers nothing.
    #   2 · THE USER'S OWN INTENT, as evidence and never as inference. Absent it, ask.
    #   3 · CONFIDENCE — the share of the reading nothing in the world accounts for. Considered,
    #       never required, and it cannot promote on its own.
    from planner.ghost_writer import queryable as _queryable
    from planner.ir import intent as _intent

    answerable = any(_queryable(g) for g in (goals or ()))
    said = _intent.declared(request)
    evidence = said in (_intent.FETCH, _intent.ENSURE)
    share = len(leftover) / len(rows) if rows else 0.0

    if not answerable:
        # ⇒ SAY WHAT WAS READ, OFFER NOTHING. The choice is withheld because it could not be
        #   honoured — `reach`, `observe` and `per` goals take no query form yet.
        return [f"[gate4/answer-not-act] this program would run {calls}, and the request "
                f"carries words the lab cannot account for — {spans}. Read as an instruction; "
                f"there is no answerable form of it to offer instead."]
    if evidence and share >= _ANSWER_CONFIDENCE:
        return [f"[gate4/answer-not-act] the request names a {said}, {share:.0%} of the "
                f"reading is words the lab cannot account for, and it can be answered rather "
                f"than run — {calls} withheld. Say so if you meant it done."]
    return [f"[gate4/answer-not-act] this program would run {calls}, and the request carries "
            f"words the lab cannot account for — {spans}. Did you mean it done, or asked?"]


def forbidden_tools(operations: List[Operation], legal=None, table=None,
                    board: Optional[Board] = None) -> List[str]:
    """The RED-LINED tools this program would call — empty when it may run.

    ⇒⇒ **THE BARRIER THE TREE HAS AND THIS SEAM DID NOT.** Found by the operator, 2026-08-13:
      *"I do remember the tree having a legal barrier, we don't have it here."* Correct — the
      red line was enforced in three places and the front seam was none of them:

          tree              engine_core.py   `if legal_filter and legal_filter(name, args)`
          program regime    consent.forbidden(program, legal)
          executor engine   executor._red_line
          the front seam    -- nothing --

      So a request the contract BANS came back **SERVE**, and the refusal happened later, at
      execution. A SERVE is a claim that the request is servable, and *"nothing legal remains
      and no answer would change that"* is this file's own definition of REFUSE.

    ⇒ **AND IT IS THE SAME DEFECT `consent.forbidden` WAS WRITTEN TO FIX, ONE LAYER UP.** Its
      docstring records it: *"the ban was enforced by leaving a tool out of the model's
      toolkit, which is a filter on what a MODEL can ask for and NO FILTER AT ALL on a program
      that names the tool itself."* This seam filters what the model may name via
      `operators_offered(board)` — a manifest filter — and never asked whether the result is
      PERMITTED.

    ⇒ **GATE 4 OWNS IT, BY THE OPERATOR'S RULING:** *"only when the program is complete can we
      assess legality."* A red line is a fact about the PROGRAM — `consent.forbidden` says the
      same thing, *"knowable before the first call, so it is answered before the first call"* —
      which is gate 4's question, not gate 3's one-operation one.

    ⇒ **BANNED REFUSES; GUARDED RUNS.** The operator, 2026-08-13, restating the 08-02 ruling.
      A guarded tool is a confirmation, and confirmations already live in this gate. This
      answers only the ban.

    ⇒ `legal` NONE MEANS NOBODY IS ANSWERING and nothing is forbidden — the same degraded arm
      `consent.forbidden` documents, so a bench with no contract behaves exactly as before.
      **It is injected, never imported**, for the reason the tree injects its own: a seam that
      reached for the contract itself could not be handed a different one.

    ⇒⇒ **AND SINCE 2026-08-13 IT CARRIES THE TARGET — WHICH IS THE ONLY THING THAT COULD
      EVER HAVE CAUGHT RUNG 14** (K5). `delete_vm` over the unfiltered set of every machine
      passed every check this seam had, because there was nothing to CATCH: no banned tool,
      no illegal operation, no missing confirmation. A scope inverts the question — the call
      must SHOW itself inside a permitted context — and an unbound set shows nothing.

      The evidence is a `schema.select_of` SELECTOR, not a literal, because this seam reads a
      request before any literal exists. Same law, different evidence: `contract.refusal`
      takes both and `scope.outside` decides which it can read.

    ⇒ **THE OPERATIONS ARE ALREADY THE TOOL LIST**, so this asks per operation rather than
      through `consent.tools_named`. That function answers *"which tools does this program
      call"* over an IR BODY with procedures to expand and creators to resolve; an
      `Operation` is a resolved operator with a declared target attached. Synthesising a body
      to re-derive what `op.operator` already says would throw the target away at exactly the
      seam that has one — which was the previous version's actual defect.

    ⇒ WITHOUT `table` THIS IS THE BAN CHECK ALONE, unchanged. A caller that cannot resolve a
      target defers the scope question by `scope.outside`'s rule rather than guessing at it.
    """
    if not callable(legal):
        return []
    from planner.ir import consent as _consent
    from . import schema as _schema
    board = board or Board()
    by_handle = {sym.handle: sym for sym in (table or ())}
    out: List[str] = []
    for op in operations:
        if op.operator in out:
            continue
        sym = by_handle.get(str(op.on))
        selector = _schema.select_of(sym.row, board) if sym is not None else None
        if _consent.ask(legal, op.operator, selector=selector):
            out.append(op.operator)
    return out


# ⇒ EVERY RULE NAME THIS GATE OWNS. `test_each_gate_owns_its_own_checks` asserts no other gate
#   emits one of these, which is the thing that would have caught the destructive guard sitting
#   in `pipeline.py` and `role-unsettled` sitting in the grammar gate.
# ⇒⇒ **AND EVERY NAME HERE IS NOW ACTUALLY EMITTED. Until 2026-08-13 NONE of them was.**
#   This gate's findings were bare strings, so a name in this set matched nothing — and
#   `test_each_gate_owns_its_own_checks`, which asserts no OTHER gate emits one of these,
#   PASSED VACUOUSLY: trivially true when nobody emits them at all. Third instance of that
#   shape after `ANSWERABLE` and the `_FAIL` counter, and the lesson is the same one —
#   **a test whose subject does not exist is a stopped clock.**
#   ⇒ THE TAG FORMAT IS THE LINGUISTICS GATE'S, deliberately: `[gate4/<rule>] …`, so a reader
#     and a test can attribute a finding to the gate that raised it without a second registry.
#   ⇒ `goal-unreachable` JOINS THE SET — `unreachable_goals` emitted findings this gate owned
#     and could not name, so the roster was short as well as unenforced.
OWNS = frozenset({"destructive-confirm", "exclusion-not-expressible",
                  "duplicate-creation", "destructive-goal", "goal-unreachable",
                  "red-line", "answer-not-act"})
