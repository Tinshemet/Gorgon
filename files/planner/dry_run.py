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
        # A BARE SET OF NAMES IS STILL A POPULATION. `SimWorld.nets` is a `set`, so the whole
        # NETWORK kind was invisible to every snapshot: a program that created `lab` showed a
        # diff mentioning only the machine, and a clause naming the network could never be
        # judged. Found 2026-08-06 while checking why a rule did not fire — a kind absent
        # from the diff reads exactly like a kind nothing happened to.
        if isinstance(got, (set, frozenset)):
            return {str(name): {} for name in got}
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


def observations(world) -> Set[str]:
    """What the world has been ASKED, as a set of finding keys. `set()` when it cannot say.

    A PROBE IS AN EFFECT AND THE REGISTRY CANNOT SEE IT. `alive` is not stored on a machine;
    it is recorded in the findings ledger (decision 6), so a program whose whole job is to
    establish an observation moves nothing a snapshot of `_records` can read and looks
    IDENTICAL to a program that did nothing.

    THAT COST TWO FALSE ALARMS THE FIRST TIME THE GATE WAS WIRED — rung 9 asks whether three
    machines can reach each other and rung 11 pings before it acts, and both were accused of
    changing nothing while doing exactly what was asked.
    """
    found = getattr(world, "findings", None)
    if found is None:
        return set()
    # THREE SHAPES, AND `Findings` IS NEITHER A DICT NOR ITERABLE. `planner.findings.Findings`
    # keeps its entries privately and exposes `known()` (added for this — `persistable()`
    # deliberately drops probe facts, which are precisely the ones that matter here); `model_world.Ledger` IS a dict;
    # a test may pass a plain one. The first version tried `dict(found)` and then iteration,
    # got a TypeError from both, and silently returned the empty set — so EVERY probe looked
    # like no probe and the rule this exists to fix stayed broken while appearing fixed.
    for read in (lambda: found.known(), lambda: dict(found), lambda: set(found)):
        try:
            got = read()
        except Exception:
            continue
        try:
            return {str(k) for k in got}
        except Exception:
            continue
    return set()


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


def reads(plan, kinds=None) -> Set[str]:
    """Every name the plan READS rather than changes — a SOURCE, not a target.

    A CLAUSE NAMING A SOURCE IS ADDRESSED BY A PLAN THAT READS IT. *"Clone golden into 3 new
    vms"* names `golden`, and a correct program never changes golden — it copies FROM it. A
    diff of what MOVED therefore says golden was untouched, which is true and is not a fault,
    and accusing it is how the clause rule earned its withdrawal on first wiring.

    READ FROM THE MANIFEST'S OWN `from` DECLARATIONS — `creators.clone.from = source_name`
    already says which argument names the thing being copied. No second list, no word
    matching: the fact was declared for the writer and this is a second reader of it.
    """
    from planner.ir import config as _config
    sources: Dict[str, Set[str]] = {}
    for spec in (kinds or _config.KINDS or {}).values():
        for maker in (spec.get("creators") or {}).values():
            if maker.get("tool") and maker.get("from"):
                sources.setdefault(str(maker["tool"]), set()).add(str(maker["from"]))
    # A PROBED MEMBER IS ADDRESSED TOO. "make sure n1, n2 and n3 can all ping each other" is
    # answered by ASKING about n1 — the program does exactly what was requested and changes
    # nothing, because the request was a question. Every prober's member argument counts.
    asked = probers(kinds)
    out: Set[str] = set()
    for call in plan or ():
        tool = call[0] if isinstance(call, (list, tuple)) and call else getattr(call, "tool", None)
        args = call[1] if isinstance(call, (list, tuple)) and len(call) > 1 else getattr(call, "args", {})
        wanted = set(sources.get(str(tool), ()))
        if str(tool) in asked:
            wanted |= {k for k in (args or {})}
        for arg in wanted:
            value = (args or {}).get(arg)
            if isinstance(value, str) and value.strip():
                out.add(value.strip().lower())
    return out


def mentions(goals) -> Set[str]:
    """Every literal the GOALS name — what the reading accounted for, whether or not it acts.

    A NAME CAN BE ADDRESSED BY BEING EXCLUDED. Rung 10's known-good reading is `count(vm) = 4`
    beside `every vm EXCEPT golden must be running`: `golden` appears only as a carve-out, so
    no call mentions it and a plan-only reading accuses the clause *"clone golden into 3 new
    vms"* of being ignored. It was not ignored — it was READ, and the reading put golden on
    the other side of an exclusion.

    SO THE RULE'S REAL QUESTION IS NARROWER THAN "DID ANYTHING HAPPEN TO IT": it is whether
    the request names something the translation never accounted for ANYWHERE. That is a much
    smaller claim, and it is the only one this evidence supports.
    """
    out: Set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple, set)):
            for item in node:
                walk(item)
        elif isinstance(node, str) and node.strip():
            out.add(node.strip().lower())

    walk(goals)
    return out


def unaddressed(request: str, d: Dict[str, Any],
                known: Optional[Set[str]] = None,
                plan=None, goals=None) -> List[Dict[str, str]]:
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
    # WHAT MOVED, PLUS WHAT WAS READ. A source is addressed by being read; see `reads`.
    moved = touched(d) | reads(plan) | mentions(goals)
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


def probers(kinds=None) -> Set[str]:
    """Every tool the manifest declares as ESTABLISHING an observed fact.

    READ FROM `observed.<fact>.by`, never a hand-written list — the manifest already names
    the asker for each fact, and a second list here would be the vocabulary defect this
    codebase has now paid for several times.
    """
    from planner.ir import config as _config
    out: Set[str] = set()
    for spec in (kinds or _config.KINDS or {}).values():
        for fact in (spec.get("observed") or {}).values():
            by = (fact or {}).get("by")
            if by:
                out.add(str(by))
    return out


def asks(plan) -> bool:
    """Does this plan ASK the world anything? Read off the PLAN, not off the ledger.

    THE LEDGER CANNOT ANSWER THIS ON A SECOND PASS. A re-run probes exactly as the first run
    did, but the facts are already recorded, so "did new findings appear" is FALSE while the
    program is doing precisely the work it is supposed to do — and the gate then called a
    correct re-verification inert. Measured on `test_medusa_rungs`' second-pass invariant.

    THE PLAN IS THE HONEST PLACE TO ASK, because it says what WILL BE DONE rather than what
    happened to be new about it.
    """
    tools = probers()
    for call in plan or ():
        name = call[0] if isinstance(call, (list, tuple)) and call else getattr(call, "tool", None)
        if str(name) in tools:
            return True
    return False
