"""Does running this program need the operator's word first?

ENSURE is Medusa's safety net, and the language leans on it: it is the only thing that
says what the program was FOR, the only witness the closure audit will accept, and the
only reason a re-run can tell "already done" from "did nothing". A program that changes
the world and never checks it has vouched for nothing — the executor cannot report it
honestly, and nobody can re-run it safely.

The operator's ruling: that is not a warning. A warning nobody can silence is noise
people learn to scroll past, and this one would appear on exactly the programs that most
need reading. It is a question, asked before anything runs — *this code has no grounding,
are you sure?* — and the answer is a yes or a no.

Kept separate from validate.py on purpose. An ungrounded program is not malformed; it is
a policy question, and the two must not be answered by the same function. Merging them
would mean either that a legitimate one-shot cannot be written at all, or that a real
structural error and a request for consent arrive as the same kind of complaint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config, master

# Ops that CHANGE the world. `ensure` and `if` are excluded because neither acts on its
# own: an `if` is only as consequential as the block it runs, and that block's own
# statements are counted when the walk reaches them.
#
# FROM THE MANIFEST since 2026-07-30. This set and `validate._ACTS` were the same three
# words written twice in modules that cannot see each other, and the fact is load-bearing
# in both — Medusa's soundness rule and the consent prompt.
_ACTING = master.acting_ops()

# Where a statement can carry more statements. Read from the field catalogue rather than
# listed here, so a construct added to the manifest is walked without an edit — the same
# claim the rest of the language makes.
_BLOCK_FIELDS = ("do", "then", "else", "ifails")


def _walk(body: Any) -> List[Dict[str, Any]]:
    """Every statement in the program, nested blocks included."""
    out: List[Dict[str, Any]] = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        out.append(st)
        for field in _BLOCK_FIELDS:
            kids = st.get(field)
            if isinstance(kids, list):
                out += _walk(kids)
    return out


def composition(program: Any) -> Dict[str, Any]:
    """Which of the three a program uses, and whether that combination can stand.

    ENSURE is the load-bearing one, and ACHIEVE is a permutation of it — the same check
    with a convergence loop behind it: act until the condition is met, then confirm it
    is. So ACHIEVE self-grounds; it does not need an ENSURE beside it.

      only ENSURE    fine. Read, judge, report. A complete program.
      only ACHIEVE   fine. Check, and close the difference if there is one.
      only FETCH     NOT fine. It retrieves and never checks what it got, so nothing in
                     it can be believed — retrieval with no verdict is data nobody
                     vouched for.
      only actions   NOT fine, for the same reason: work nothing vouched for.

    Which is one rule, not three: a program needs at least one VERDICT. FETCH answers
    with data and actions answer with nothing, and neither is a judgement about the
    world. ENSURE and ACHIEVE are the only two statements that produce one.
    """
    from .validate import coerce_body
    stmts = _walk(coerce_body(program) or [])
    ops = [st.get("op") for st in stmts]
    return {"fetch": ops.count("fetch"), "ensure": ops.count("ensure"),
            "achieve": ops.count("achieve"),
            "acts": sum(1 for o in ops if o in _ACTING)}


def unsound(program: Any) -> Optional[str]:
    """Why this combination cannot stand, or None if it can."""
    c = composition(program)
    if c["ensure"] or c["achieve"]:
        return None
    if c["fetch"] and not c["acts"]:
        return ("this program only FETCHES. It reads the world and never says what must "
                "be true of what it found, so nothing in it is verified — add an ENSURE, "
                "or an ACHIEVE if you want the gap closed rather than reported.")
    return ("nothing in this program produces a VERDICT. It fetches and acts, and neither "
            "is a judgement about the world — add an ENSURE for what must be true, or an "
            "ACHIEVE for what must end up true.")


def _walk_marked(body: Any, in_loop: bool = False) -> List[Any]:
    """Every statement, paired with whether it sits inside a `foreach`.

    Separate from `_walk` because only one rule needs the flag and the plain walk is used
    everywhere else; folding the flag into `_walk` would change four call sites to answer
    one question.
    """
    out: List[Any] = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        out.append((st, in_loop))
        deeper = in_loop or st.get("op") == "foreach"
        for field in _BLOCK_FIELDS:
            kids = st.get(field)
            if isinstance(kids, list):
                out += _walk_marked(kids, deeper)
    return out


# The loop member's name, `$item` — a FIXED word, not a name the author chooses, which is
# what makes the rule below exact rather than a guess about intent.
_LOOP_REF = config.SIGIL + config.LOOP_VAR


def _asserts_the_member_exists(pred: Any) -> bool:
    """`COUNT(SELECT vm WHERE name = '$item') = 1` — true by construction inside a loop.

    Iterating a member is what established that it exists, so asserting it again
    discriminates nothing: the predicate holds however the program behaves.
    """
    if not isinstance(pred, dict) or pred.get("shape") != "count" or pred.get("eq") != 1:
        return False
    sel = pred.get("select")
    if not isinstance(sel, dict):
        return False
    filters = {k: v for k, v in sel.items() if k != "kind"}
    return (list(filters) == ["name"]
            and isinstance(filters["name"], str) and _LOOP_REF in filters["name"])


def vacuous(program: Any) -> List[str]:
    """Assertions that cannot fail — a witness that witnesses nothing.

    MEASURED 2026-07-31 and this is why it exists. rung 11's program inverted its own
    condition (stopping the machines that DID answer) and carried

        ENSURE COUNT(SELECT vm WHERE name = '$item') = 1;

    inside the loop. The rung's checker correctly said FAIL, the program's own ENSURE said
    PASS, and the ladder recorded a CHECKER_DISPUTE — a category meaning "one of these two
    is wrong and we cannot tell from here". But there was nothing to weigh: the ENSURE was
    satisfied no matter what the program did, so a genuine MODEL reasoning error was filed
    under `harness` and read as the bench possibly being at fault.

    NARROW ON PURPOSE, and this is the [[gorgon-deterministic-rules]] pattern: compute,
    and DECLINE WHEN UNSURE. Only a `count` shape can be vacuous here; `reach` and
    `disjoint` are always treated as real assertions even though some instances of them
    surely are not. A relevance test — "does the predicate mention any attribute an acting
    statement writes" — was considered and REFUSED for now: it would also flag a program
    that creates five vms and ensures a count of five when the write is the creation
    itself, and a false accusation of vacuity is worse than a missed one. It fails a
    correct program and teaches nobody anything.
    """
    out: List[str] = []
    for st, in_loop in _walk_marked(_body_of(program)):
        if st.get("op") not in ("ensure", "achieve"):
            continue
        if in_loop and _asserts_the_member_exists(st.get("predicate")):
            out.append("asserts that the member being iterated exists, which iterating it "
                       "already established — it holds however the program behaves")
        floor = _floor_every_count_clears(st.get("predicate"))
        if floor is not None:
            out.append(f"asserts a count is at least {floor}, and a count never is not — "
                       f"there is no world where this fails")
    return out


def _floor_every_count_clears(pred: Any) -> Optional[int]:
    """The floor of a `COUNT(...) >= n` that no world can miss, or None.

    A COUNT IS A CARDINALITY, so it is never negative and `>= 0` is true in every world.
    That is decorative grounding in its purest form, and it PASSED until 2026-08-06:
    `survey` says in as many words that counting an assertion which cannot fail "would make
    'add any ENSURE' a way to satisfy the grounding rule without satisfying the property",
    and then `COUNT(SELECT vm) >= 0` did exactly that — one act, one assertion, grounded.

    FOUND BY ASKING WHETHER EACH CHECK CAN FAIL rather than whether it passes. The docstring
    above says "assertions that cannot fail" and detected exactly ONE shape; a check nobody
    has watched go red is a claim, not a guarantee.

    NARROW AND CERTAIN, which is the [[gorgon-deterministic-rules]] pattern. Only the FLOOR
    is decidable without knowing the world: no `lte` can be judged here, because whether a
    ceiling is unreachable depends on how many resources could exist, and `eq: 0` is a real
    assertion — "there are none" is a claim a world can break. Nothing else is guessed.
    """
    if not isinstance(pred, dict) or pred.get("shape") != "count":
        return None
    try:
        floor = int(pred["gte"])
    except (KeyError, TypeError, ValueError):
        return None
    return floor if floor <= 0 else None


def _body_of(program: Any) -> List[Any]:
    from .validate import coerce_body
    return coerce_body(program) or []


def survey(program: Any) -> Dict[str, Any]:
    """What this program does and whether anything checks it.

    Returns {acts, asserts, vacuous, grounded}. `acts` counts world-changing statements
    ANYWHERE, including inside a loop body or a recovery block — a program whose only
    effect is in an IFAILS is still a program with effects.

    GROUNDING COUNTS ONLY ASSERTIONS THAT COULD FAIL. An ENSURE that holds however the
    program behaves is not a weaker witness than a real one, it is not a witness — and
    counting it would make "add any ENSURE" a way to satisfy the grounding rule without
    satisfying the property. That matters most on the day the rule starts being scored,
    because the cheapest way to answer a demand for grounding is decorative grounding.
    """
    stmts = _walk(_body_of(program))
    acts = sum(1 for st in stmts if st.get("op") in _ACTING)
    # Both words ground a program. `achieve` is the stronger of the two — it states what
    # the whole thing was for — so a program carrying one is grounded by definition.
    asserts = sum(1 for st in stmts if st.get("op") in ("ensure", "achieve"))
    # A `new` VOUCHES FOR ITS OWN CREATION, AND FOR NOTHING ELSE. The visitor re-reads the
    # world after every creation and files a failure if what was asked for is not there — a
    # verdict about that statement, produced by that statement. So a program whose every act
    # is a creation is already checked act by act, and a closing ENSURE over it asserts a
    # second time what the body just proved: that is the two-line program the operator asked
    # for, *"ensure is unneeded here"*.
    #
    # ONLY WHEN EVERY ACT IS ONE, which is the whole precision of it. A program that creates
    # a machine and then LABELS it has an unvouched-for act — `new` said nothing about the
    # label — and the question still stands. Counting a `new` unconditionally would let a
    # single creation ground a program of sixteen unchecked changes.
    acting = [st for st in stmts if st.get("op") in _ACTING]
    if acting and all(st.get("op") == "new" for st in acting):
        asserts += len(acting)
    empty = vacuous(program)
    return {"acts": acts, "asserts": asserts, "vacuous": len(empty),
            "why_vacuous": empty,
            "grounded": acts == 0 or (asserts - len(empty)) > 0}


def question(program: Any) -> Optional[str]:
    """The operator's question, or None if the program grounds itself.

    Names the number of acting statements rather than saying "this program makes
    changes", because the count is the part that decides the answer: consenting to one
    unverified label is not consenting to sixteen.
    """
    s = survey(program)
    if s["grounded"]:
        return None
    why = unsound(program)
    n = s["acts"]
    # ONE gate, not two. `unsound` says precisely which of the three is missing, and that
    # is a better sentence than the generic one it replaces — but it stays a QUESTION.
    # The operator's ruling was ask, not refuse, and a hard block here would quietly
    # overturn it: there are legitimate one-shots, and the person running them is the one
    # who gets to say so.
    return ((why or f"{n} statement{'s' if n != 1 else ''} change the world and nothing "
             f"checks the result") + " Run it anyway?")


def tools_named(program: Any, seen: Optional[set] = None) -> List[str]:
    """Every tool this program would call, stored procedures expanded, in program order.

    TRANSITIVE, BECAUSE A PROCEDURE IS A TOOL YOU WROTE. `CALL setup_temp_vm(...)` runs the
    stored body through the same visitor, so a red line hidden two procedures deep is still
    a red line this program crosses. `seen` breaks a cycle — a library that calls itself is
    a bug for the validator to name, not a reason for this to hang.

    A SET OF TOOLS, NOT A TALLY OF CALLS: a procedure called twice is expanded once, and a
    caller counting cost rather than asking "which tools" wants a different function. What
    this answers is the membership question, which is the one a red line asks.

    A `NEW`'s TOOL IS RESOLVED, NOT GUESSED. `effects.creator_for` is the visitor's own
    rule, so what is listed here is what will actually be called.
    """
    from . import effects as _effects
    from .validate import coerce_body

    seen = set() if seen is None else seen
    out: List[str] = []
    for st in _walk(coerce_body(program) or []):
        op = st.get("op")
        if op == "new" and st.get("kind"):
            tool = _effects.creator_for(st["kind"], st.get("tool"),
                                        bool(st.get("from"))).get("tool")
            if tool:
                out.append(tool)
        elif op == "call" and st.get("tool"):
            name = str(st["tool"])
            if name in seen:
                continue
            seen.add(name)
            inner = None
            try:
                from .. import procedures as _procs
                inner = _procs.LIBRARY.get(name)
            except Exception:
                # A LIBRARY THAT CANNOT ANSWER IS NOT AN EMPTY ONE. The name stays on the
                # list as itself, so a call nobody could expand is still something the
                # red-line check gets to see rather than something it skips.
                inner = None
            if inner is None:
                out.append(name)
            else:
                out += tools_named(inner, seen)
    return out


def forbidden(program: Any, legal: Optional[Any]) -> List[str]:
    """The red-lined tools this program would call — empty when it may run.

    THE OPERATOR'S RULING, 2026-08-02: *"a tool that is allowed but guarded should still run
    normally because running procedures require operator password already, but banned tools
    should still be banned"* — and *"not be ran at all, not just the tools but also the
    entire program."*

    SO THIS IS A PRE-FLIGHT, NOT A PER-CALL REFUSAL, and the difference is the whole point.
    Refusing the banned call where it sits would run every statement before it and leave the
    lab half-built by a program that was never allowed to start. A red line is a fact about
    the PROGRAM, knowable before the first call, so it is answered before the first call.

    IT IS THE LEGAL FILTER, THE SAME ONE — `is_forbidden`, gauntlet A, injected exactly as
    the tree path injects it (`engine_core._guard`). The program regime had no counterpart:
    the ban was enforced by leaving a tool out of the model's toolkit, which is a filter on
    what a MODEL can ask for and no filter at all on a program that names the tool itself.
    Measured 2026-08-02 — with every tool forbidden, a stored procedure's calls ran.

    `legal` NONE MEANS NOBODY IS ANSWERING, and then nothing is forbidden. That is the
    degraded arm of `_deps` (a sparse checkout with no contract), not a default policy —
    a caller with red lines to enforce passes them.
    """
    if not callable(legal):
        return []
    out: List[str] = []
    for tool in tools_named(program):
        if tool not in out and legal(tool):
            out.append(tool)
    return out


def permitted(banned: List[str], permit: Any) -> bool:
    """Has the operator lifted these red lines? `permit` is shaped exactly like `consent`.

    THE OPERATOR'S RULING, 2026-08-02: *"procedures dont require operator password. ONLY
    WHEN IT CONTAINS BANNED TOOLS, then you require an operator password."* An ordinary
    procedure runs on the consent and destruction questions it already meets; a banned tool
    is the one thing that escalates to RE-AUTHENTICATION, which is the invariant's own words
    for a high-impact act.

    ABSENT AN OPERATOR THE ANSWER IS NO, and here `True` is deliberately NOT accepted as a
    standing grant the way `consent` accepts it. A caller passing `consent=True` is saying
    *"a person already said yes to this program"*; nothing should be able to say that in
    advance about a red line, because the whole point is that a person is asked AT THE
    MOMENT and proves who they are. Only a callable can answer.

    NOTE WHAT THIS CHANGES, so nobody discovers it by reading the contract later:
    `Contract.is_forbidden` calls a w:0 forbid *inviolable*. It is now liftable — by one
    party, in person, with a password, and by nothing else.
    """
    return bool(permit(banned)) if callable(permit) else False


def granted(program: Any, consent: Any) -> bool:
    """Has running this been authorised?

    `consent` is True (granted outright), a callable asked with the question, or anything
    else — including the default None, meaning no operator is present.

    Absent an operator the answer is NO. Fail-closed is the standing rule for every other
    high-impact act here and there is no reason for programs to be the exception: the
    alternative is that an unattended run quietly grants itself the permission a person
    was supposed to give.
    """
    if question(program) is None:
        return True
    if consent is True:
        return True
    if callable(consent):
        return bool(consent(question(program)))
    return False
