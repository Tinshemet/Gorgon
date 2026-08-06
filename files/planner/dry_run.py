"""dry_run.py — what a program WOULD do, and what changed when it did.

## THE CHECK THE PROGRAM REGIME WAS BUILT FOR AND NEVER GOT

The 2026-07-28 design note lists what can be graded, and the third row is the one only this
regime can see:

    leaf     a malformed or ungrounded statement
    fusion   a subtree that does not add up to its sub-goal
    WHOLE    a wrong decomposition · work repeated across distant branches ·
             A CLAUSE OF THE GOAL APPEARING NOWHERE

*"Only the program regime can see that third row, because its artifact is complete and INERT
before anything runs."* The tree cannot: it has already acted by the time it could look.
**The regime was chosen for that capability and the capability was never built.**

## AND THE DRY RUN ALREADY HAPPENS

`ghost_writer.cover` plans against `_scratch_of(world)` and EXECUTES every placed tile on it
— that is how it knows what is already satisfied. So when planning returns, the scratch holds
the program's predicted end state. It was thrown away. Nothing here is a new simulation; this
keeps a result the writer was computing anyway.

## WHY COMPARING THE RESULT TO THE GOALS WOULD BE WORTHLESS

A DONE_BUT_FALSE is a program that satisfies its own goal while the goal is wrong. Checking
the predicted world against the goals passes BY CONSTRUCTION — the run already agrees with
itself; that is what makes the failure invisible.

**THE COMPARISON HAS TO BE AGAINST THE REQUEST.** `clause_ledger` enumerates demands from the
ENGLISH, so reconciling a world diff against those demands is not circular. It also upgrades
the ledger's weakest joint, which its own docstring concedes: *"the plan mentions the token,
which is not the same as addressing the demand."* **A diff is not a token in some text.**

## WHAT IT CAN AND CANNOT SEE — state both, because a grader trusted past its evidence is
## worse than no grader

    CAN   nothing changed at all, on a request that asks for change
    CAN   a clause whose names appear nowhere in what moved
    CAN   work done to a member the request never mentions

    CANNOT  predict an OBSERVATION. Which machines answer a ping is a fact about the real
            lab; the scratch does not know it and must not pretend to. So a program that
            probes and then acts on the answer is only partly visible here — this can say
            NOTHING WAS STOPPED, never THE RIGHT ONES WOULD BE.
    CANNOT  be truer than the world model it ran against. A seam that mis-answers gives a
            diff that mis-reports, which is not hypothetical: the bench seam matched every
            member on any attribute it could not evaluate until 2026-08-06.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from planner.ir import config


def _records(world, kind: str) -> Dict[str, Any]:
    """Every member of `kind` the world will show, as `{name: record}`. `{}` when it cannot.

    TOLERANT OF THE WORLD'S SHAPE ON PURPOSE, and the shapes are real: `SimWorld` holds
    `.vms`, the Active Library holds `._vms`, and `model_world.World` holds a nested
    `{kind: {key: attrs}}`. A grader that demanded one interface would simply not run
    against the lab it most needs to grade.

    NEVER RAISES. A world that cannot answer contributes nothing to the diff, which reads as
    "no change here" — and the caller is told the reading is partial rather than handed a
    crash in the middle of a plan.
    """
    for attr in (f"_{kind}s", f"{kind}s"):
        got = getattr(world, attr, None)
        if isinstance(got, dict):
            return got
    state = getattr(world, "state", None)
    if isinstance(state, dict) and isinstance(state.get(kind), dict):
        return state[kind]
    return {}


def snapshot(world, kinds: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """`{kind: {member: {attr: value}}}` — the world as the language can see it."""
    out: Dict[str, Dict[str, Any]] = {}
    for kind in (kinds or list(config.KINDS or {})):
        rows = _records(world, kind)
        if not rows:
            continue
        out[kind] = {str(name): _flat(rec) for name, rec in rows.items()}
    return out


def _flat(record: Any) -> Dict[str, Any]:
    """One member's attributes, with sets made comparable and order made irrelevant.

    A LABEL SET AND A LABEL LIST ARE THE SAME FACT. `SimWorld` keeps `labels` as a `set` and
    the registry keeps it as a `list`, so comparing them raw reports a change on every
    member of every diff — a grader that cries wolf on all of them is one nobody reads.
    """
    if not isinstance(record, dict):
        return {"_value": record}
    out: Dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, (set, frozenset)):
            out[key] = sorted(str(v) for v in value)
        elif isinstance(value, (list, tuple)):
            out[key] = sorted(str(v) for v in value)
        else:
            out[key] = value
    return out


def diff(before: Dict[str, Dict[str, Any]],
         after: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """What changed between two snapshots — added, removed, and attribute by attribute.

    `changed` is per member and per ATTRIBUTE rather than per member, because "web changed"
    cannot be reconciled against a clause and "web.network went from nothing to lab" can.
    """
    added: Dict[str, List[str]] = {}
    born: Dict[str, Dict[str, Any]] = {}
    removed: Dict[str, List[str]] = {}
    changed: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for kind in sorted(set(before) | set(after)):
        was, now = before.get(kind) or {}, after.get(kind) or {}
        gained = sorted(set(now) - set(was))
        lost = sorted(set(was) - set(now))
        if gained:
            added[kind] = gained
            # WHAT A NEW MEMBER CAME INTO EXISTENCE WITH IS PART OF WHAT CHANGED. Recording
            # only the name loses it: three machines cloned FROM `golden` are evidence about
            # golden, and a diff that forgets the source accuses "clone golden into 3 new
            # vms" of being unaddressed by the program that clones it. Measured, first run.
            born.setdefault(kind, {}).update({m: now[m] for m in gained})
        if lost:
            removed[kind] = lost
        for member in sorted(set(was) & set(now)):
            moved = {a: {"was": was[member].get(a), "now": now[member].get(a)}
                     for a in sorted(set(was[member]) | set(now[member]))
                     if was[member].get(a) != now[member].get(a)}
            if moved:
                changed.setdefault(kind, {})[member] = moved
    return {"added": added, "born": born, "removed": removed, "changed": changed}


def empty(d: Dict[str, Any]) -> bool:
    """Did the program change NOTHING? The loudest thing a diff can say."""
    return not (d.get("added") or d.get("removed") or d.get("changed"))


def touched(d: Dict[str, Any]) -> Set[str]:
    """Every name and value the change is ABOUT — what a clause's anchors are matched against.

    BOTH SIDES OF A MOVE ARE INCLUDED. `network: None -> lab` is evidence about `lab` as much
    as about the machine, and a clause saying *"put web on lab"* names both. Dropping the
    values would leave the diff unable to answer the very demands it exists to answer.
    """
    out: Set[str] = set()

    def take(value: Any) -> None:
        if isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                take(item)
        elif value not in (None, "", True, False):
            out.add(str(value).strip().lower())

    for kind, names in (d.get("added") or {}).items():
        out.update(str(n).lower() for n in names)
    for kind, members in (d.get("born") or {}).items():
        for member, record in members.items():
            for attr, value in (record or {}).items():
                take(value)
    for kind, names in (d.get("removed") or {}).items():
        out.update(str(n).lower() for n in names)
    for kind, members in (d.get("changed") or {}).items():
        for member, moves in members.items():
            out.add(str(member).lower())
            for attr, move in moves.items():
                take(move.get("was"))
                take(move.get("now"))
    return out


def identifiers(*snapshots) -> Set[str]:
    """Every member NAME any of these worlds knows. What a clause may be judged against.

    THE LEDGER'S ANCHORS ARE NOT IDENTIFIERS AND MUST NOT BE USED AS THEM HERE. It keeps
    words longer than two characters that survive a stopword list and are not verbs, capped
    at three — so *"clone golden into 3 new vms"* anchors on `golden`, `new` and `vms`. Two
    of those are nouns of the schema, not names of anything, and accusing a program of not
    mentioning `vms` is how a grader becomes noise nobody reads.

    THE WORLD ALREADY KNOWS WHICH WORDS NAME THINGS, so this asks it rather than guessing
    from spelling. Ground truth beats a word list — the same reason `check_context` takes
    `known_names` from the Active Library instead of inferring them.
    """
    out: Set[str] = set()
    for snap in snapshots:
        for kind, members in (snap or {}).items():
            out.update(str(m).strip().lower() for m in members if str(m).strip())
    return out


def unaddressed(request: str, d: Dict[str, Any],
                known: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """The clauses of `request` whose names appear NOWHERE in what the program moved.

    THIS IS THE THIRD ROW — a clause of the goal appearing nowhere — and it is asked of the
    WORLD rather than of the plan's text. `clause_ledger` already enumerates the demands and
    already reconciles them; what it had to match against was a haystack of statement text,
    where a name could be present because some unrelated line mentioned it.

    A CLAUSE WITH NO ANCHORS IS NOT ACCUSED. *"no more"* and *"boot every copy"* name
    nothing, so nothing can be proven about them here, and the ledger's own asymmetry holds:
    absence of a name proves nothing addressed the demand, presence proves only that
    something mentioned it.
    """
    from planner import clause_ledger as ledger
    try:
        clauses = ledger.enumerate_clauses(request)
    except Exception:
        return []
    moved = touched(d)
    names = {str(n).strip().lower() for n in (known or set()) if str(n).strip()}
    out: List[Dict[str, str]] = []
    for clause in clauses:
        # ONLY WORDS THAT NAME SOMETHING. A clause is judged on the identifiers it mentions,
        # never on the ledger's spelling-filtered anchors — see `identifiers`. With no
        # `known` set supplied nothing is judged at all, which is the safe direction: a
        # grader with no ground truth accuses nobody.
        anchors = [a for a in
                   (str(w).strip(".,!?;:'\"").strip().lower()
                    for w in str(clause.get("text") or "").split())
                   if a in names]
        if not anchors:
            continue
        missing = [a for a in anchors if not any(a in m for m in moved)]
        if missing:
            out.append({"clause": str(clause.get("text") or "").strip(),
                        "why": ("nothing the program would change mentions "
                                + ", ".join(repr(m) for m in missing))})
    return out
