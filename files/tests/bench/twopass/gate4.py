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

from ..formula.legal import Board
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
                  "duplicate-creation", "destructive-goal", "goal-unreachable"})
