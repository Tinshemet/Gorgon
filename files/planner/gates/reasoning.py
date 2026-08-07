"""reasoning.py — GATE 3. Does this reading MAKE SENSE, and is it POSSIBLE?

    inspect(goals, world, settled=False) -> Report(vacuous, inert, unrelated,
                                                   contradictory, unplannable)

## THE QUESTION, AND WHY IT IS DIFFERENT FROM THE FIRST TWO

Gate 1 asks whether the reading is faithful to the SENTENCE. Gate 2 asks whether it is true of
the WORLD. Both pass a reading that is perfectly faithful, perfectly grounded, and **says
nothing** — which is the defect this gate exists for, and the clarification it raises is
**"why?"**: *"create a procedure that checks the network"* refers to real things, invents
nothing, and still means nothing until someone says what checking is.

## ⇒ IT ASKS AND NEVER SUPPLIES

The operator, 2026-08-07: *"we can't truly know what the user wants — it's on them to
clarify."* Gate 2 MAY supply what it finds missing, because a probe only asks the WORLD and
the worst case is a question nobody needed answered. **Everything gate 3 could supply is a
guess about a PERSON**, so it asks. See `Report.questions()` for the case that was refused.

## ⇒ IT NEEDS A PLAN, AND THAT SHAPES EVERYTHING

Vacuity, inertness and relation are statements about what a reading WOULD DO. Gates 1 and 2
are pure functions of (request, goals, world); this one has to ask the writer.

**AND A READING THE WRITER REFUSES NEVER ARRIVES.** `cover` raises `Unsolvable` and the engine
promotes to tree before any gate runs, so gate 3 only ever sees readings that PLAN. That
sounded like a fatal narrowing until it was counted — **18 of the 25 failing readings in the
corpus reach a plan**, and the 5 that do not are all `EXTRACT_WRONG`. The ceiling is 72%, not
the sliver it looked like.

## MEASURED BEFORE IT WAS WRITTEN — the whole file is four rules and each one was counted first

    candidate                    on PASS   on failing
    vacuous reading                 0          6
    made and never related          0          3
    inert (plans nothing)           0          2
    contradiction (single-valued)   —          —      never fired
    ────────────────────────────────────────────────
    unioned                       0/58       11/18

**ZERO OVERLAP** — each catches a distinct set, which is why all three are worth having rather
than one being a weaker spelling of another.

⇒ THE ORDER OF WORK WAS THE POINT. Earlier the same day, the arity rule was validated against
the 14 hand-written correct readings — 0 occurrences, so a shape no correct reading uses could
be refused — and it had to be demoted when 83 REAL readings showed it on ones that PASS.
Fourteen hand-written readings are ONE IDIOM. Nothing here was written before it was counted.

## WHAT IT DOES NOT OWN

**A CLAUSE THAT IS SIMPLY ABSENT.** Rung 13's dropped clique plans fine, asserts something
real, contradicts nothing and relates what it makes. A missing goal is not illogical — it is
missing, and no amount of reasoning about what IS there can see what is NOT. That is the
whole-versus-parts question, which is gate 4's.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import claims as _claims

# STRUCTURAL SELECTOR KEYS — set operations, not attributes of a member.
_STRUCTURAL = ("kind", "not", "any", "all", "except")


class Report:
    """What gate 3 found. Five lists, because they mean five different things."""

    def __init__(self, vacuous=None, inert=None, unrelated=None,
                 contradictory=None, unplannable=None, uncountable=None):
        # ASSERTS NOTHING — true by construction, so it cannot fail and cannot inform.
        self.vacuous: List[Dict[str, Any]] = list(vacuous or ())
        # PLANS NOTHING — see `legal` for why this is conditional on gate 2.
        self.inert: List[Dict[str, Any]] = list(inert or ())
        # COUNTS A SET WHOSE SIZE NOBODY CAN KNOW UNTIL SOMETHING ASKS.
        self.uncountable: List[Dict[str, Any]] = list(uncountable or ())
        # MAKES TWO THINGS THE MANIFEST SAYS CAN RELATE, AND NEVER RELATES THEM.
        self.unrelated: List[Dict[str, Any]] = list(unrelated or ())
        # TWO GOALS FORCING ONE SINGLE-VALUED ATTRIBUTE TO DIFFERENT VALUES.
        self.contradictory: List[Dict[str, Any]] = list(contradictory or ())
        # THE WRITER REFUSED IT. A REPORT, NEVER A FAULT — the engine already answers this by
        # promoting to tree, and a gate that ALSO refused would turn an escalation into a wall.
        self.unplannable: List[Dict[str, Any]] = list(unplannable or ())

    @property
    def legal(self) -> bool:
        return not (self.vacuous or self.inert or self.unrelated or self.contradictory
                    or self.uncountable)

    def findings(self) -> List[str]:
        out = []
        for v in self.vacuous:
            out.append(f"this asserts nothing that could fail: {v['why']}")
        for i in self.inert:
            out.append("nothing in this would do anything")
        for u in self.uncountable:
            out.append(f"it asks for exactly {u['eq']} {u['kind']}s where {u['attr']} holds, "
                       f"and nothing knows how many that is until something asks — "
                       f"`every` says it without counting")
        for u in self.unrelated:
            out.append(f"it makes a {u['kind']} and a {u['other']} and never connects them")
        for c in self.contradictory:
            out.append(f"{c['name']!r} must have {c['attr']}={c['first']!r} "
                       f"and {c['attr']}={c['second']!r}")
        return out

    def reports(self) -> List[str]:
        return [f"the writer cannot close this: {u['why']}" for u in self.unplannable]

    def questions(self) -> List[str]:
        """THE RESOLVE ARM, AND IT IS ALL QUESTIONS. Gate 3 asks **WHY** — for what reason,
        to what end — which is the clarification its findings can actually earn.

        ## ⇒ IT MAY NOT SUPPLY, AND THAT IS A RULING RATHER THAN A LIMITATION

        The operator, 2026-08-07: *"we can't truly know what the user wants — it's on them to
        clarify."*

        The temptation was concrete and it was refused. `unrelated` knows exactly what the
        missing goal WOULD be: `lab` and `web` are both minted and the manifest declares
        `vm.setters.add_vm_to_network refs network`, so `count(vm WHERE name=web AND
        network=lab) = 1` is derivable with no vocabulary and no model call. It would close
        rung 3 outright.

        **AND IT WOULD BE INVENTING INTENT.** Two relatable things a request MEANS to leave
        apart would be joined, silently, by a gate that decided it knew better — and that is
        the one false alarm this gate has which is UNOBSERVED rather than disproven, so
        supplying would be acting confidently on the thing least measured about it.

        ⇒ THE LINE BETWEEN THE GATES IS NOW STATED: **gate 2 MAY supply because a probe only
        asks the WORLD — the worst case is a question nobody needed answered. Gate 3 may not,
        because everything it could supply is a guess about a PERSON.** Same machinery,
        different subject, opposite defaults.

        ONE MESSAGE PER FINDING AND EACH NAMES WHAT TO SAY BACK. A question the operator has
        to decode is a question they will answer wrongly.
        """
        asks = []
        for v in self.vacuous:
            asks.append("this reading asks about things and never changes any of them. "
                        "What should be TRUE when it is finished?")
        for u in self.unrelated:
            asks.append(f"it makes a {u['kind']} and a {u['other']} and never connects them. "
                        f"Did you mean them to be connected, or to stay apart?")
        for i in self.inert:
            asks.append("nothing in this would do anything, and nothing says it is already "
                        "done. What did you want changed?")
        for u in self.uncountable:
            asks.append(f"how many {u['kind']}s have {u['attr']} set is not knowable until "
                        f"something asks. Did you mean ALL of the ones that do?")
        for c in self.contradictory:
            asks.append(f"{c['name']!r} is asked to have {c['attr']}={c['first']!r} and "
                        f"{c['attr']}={c['second']!r}, and it can only have one. Which?")
        return asks

    def __repr__(self) -> str:
        return (f"<Reasoning {'legal' if self.legal else 'ILLEGAL'} "
                f"vacuous={len(self.vacuous)} inert={len(self.inert)} "
                f"unrelated={len(self.unrelated)} uncountable={len(self.uncountable)} "
                f"contradictory={len(self.contradictory)} "
                f"unplannable={len(self.unplannable)}>")


def _single_valued(kind: str, attr: str, table=None) -> bool:
    """Can a member hold ONE value of this attribute, or several?

    ASKED OF THE EXISTING AUTHORITY. `model_world._single` reads it off `attr_values` — an
    attribute with an enumeration takes one of them, one without is a collection. A second
    hand-rolled answer beside it would be a second thing to drift, and this codebase has
    already found two such disagreements today.
    """
    from planner.ir import config as _config
    from planner.model_world import _single
    spec = ((table if table is not None else (_config.KINDS or {})).get(kind) or {})
    for setter in (spec.get("setters") or {}).values():
        if isinstance(setter, dict) and setter.get("attr") == attr:
            return _single(spec, setter)
    return True


def contradictions(goals: List[dict], table=None) -> List[Dict[str, Any]]:
    """Two goals forcing the SAME attribute to DIFFERENT values on a member they SHARE.

    ⇒ SOUND ONLY WHERE THE ATTRIBUTE HOLDS ONE VALUE AT A TIME, and that restriction is the
    entire rule. `vm.network` and `vm.label` are SETS — the manifest gives them unsetters keyed
    by value, and a machine added to `core` and then to `dmz` sits on BOTH. So "every vm on
    core" and "db on dmz" DO NOT CONTRADICT, and a first draft of this check said they did:
    it caught rung 8 by accident, for a reason that does not hold.

    ⇒ AND IT HAS NEVER FIRED. Restricted correctly, only `vm.status` qualifies today and no
    reading in the corpus asserts two statuses on one machine. It is kept because it is free
    and sound, and recorded as untriggered so nobody later reads its silence as coverage.
    """
    forced: Dict[Any, Any] = {}
    out = []
    for claim in _claims.over(goals, table):
        if claim.stance != _claims.ASSERTS or claim.identity is None or not claim.attr:
            continue
        if not _single_valued(claim.kind, claim.attr, table):
            continue
        key = (claim.kind, claim.identity, claim.attr)
        if key in forced and forced[key] != claim.value:
            out.append({"kind": claim.kind, "name": claim.identity, "attr": claim.attr,
                        "first": forced[key], "second": claim.value})
        forced[key] = claim.value
    return out


def uncountable(goals: List[dict], table=None) -> List[Dict[str, Any]]:
    """A `count` whose selector filters on an OBSERVED fact. Its cardinality is unknowable.

    ## ⇒ THE OPERATOR'S DIAGNOSIS, 2026-08-07, AND IT IS THE CLEANEST STATEMENT OF RUNG 11

    *"'stop the unresponsive ones' is a SET, but of an UNKNOWABLE NUMBER. `count` needs a
    knowable number, meaning it either has to count them first and plug them in, or have a way
    to express the count of an unknowable finite set."*

    `count` REQUIRES `amount` — an integer, at authoring time. `alive` is not stored, it is
    ASKED (`observed.alive.by`), so how many machines have it is unknown until something pings.
    A count over that set demands a number nobody can supply.

    ⇒ **AND `every` IS THE ANSWER, WHICH IS WHY THE FINDING SAYS SO.** *"`every` covers an
    unknowable number of a finite set."* `every vm WHERE alive=false must status=stopped`
    quantifies over exactly that set and never counts it — and it round-trips to the
    hand-written correct reading of rung 11 byte for byte. The shape is not missing; it is
    declined.

    ## IT HAS NEVER FIRED, AND THAT IS RECORDED RATHER THAN HIDDEN

    0 false alarms and 0 catches across the corpus, because the model does not attempt the
    honest version and fail — it AVOIDS the filter entirely and names the set instead
    (`count(vm WHERE name='unresponsive') = 0`). The failure is one step earlier than this
    rule can see.

    IT IS KEPT BECAUSE IT IS FREE AND SOUND, and it fires the moment a model does reach for
    the shape this describes. A rule that costs nothing and states a real impossibility is
    worth having before the case arrives, not after.
    """
    from planner.ir import config as _config
    from planner.ir import effects as _effects
    table = table if table is not None else (_config.KINDS or {})
    out = []
    for goal in goals or ():
        if str(goal.get("shape") or "") != "count":
            continue
        sel = goal.get("select") or {}
        kind = sel.get("kind")
        for attr in sel:
            if attr in _STRUCTURAL or attr == "kind":
                continue
            if _effects.probe_for(kind, attr, table):
                out.append({"kind": kind, "attr": attr, "eq": goal.get("eq")})
    return out


def unrelated(goals: List[dict], table=None) -> List[Dict[str, Any]]:
    """Two members brought into being whose kinds the MANIFEST says can be related, and no
    goal relating them.

    RUNG 3'S SHAPE — *"create a network called lab and a vm named web, then put web on lab"* —
    where the third clause is dropped. `vm.setters.add_vm_to_network` declares
    `refs: "network"`, so the fact that a vm CAN be joined to a network is read rather than
    guessed, and a kind added to the manifest later is covered without an edit here.

    ⇒ THE FALSE ALARM THIS COULD HAVE, STATED PLAINLY: *"create a network called lab"* beside
    an unrelated *"create a vm"* is a legal request that makes two relatable things and means
    to leave them apart. **That case does not occur in the corpus**, so 0 false alarms here is
    UNOBSERVED RATHER THAN DISPROVEN. It is the first thing to check if this ever starts
    accusing real work.
    """
    from planner.ir import config as _config
    table = table if table is not None else (_config.KINDS or {})
    made = _claims.minted(goals, table)
    if len(made) < 2:
        return []
    # WHICH KINDS THIS READING ALREADY POINTS AT. A `must` that assigns `network=lab` IS the
    # relation, so a reading carrying one is not missing it.
    related = set()
    for claim in _claims.over(goals, table):
        if claim.stance == _claims.ASSERTS and claim.attr:
            ref = _claims.refers_to(claim.attr, table)
            if ref:
                related.add(ref)
    out = []
    for kind in made:
        for other in made:
            if kind == other or other in related:
                continue
            for setter in ((table.get(kind) or {}).get("setters") or {}).values():
                if isinstance(setter, dict) and setter.get("refs") == other:
                    out.append({"kind": kind, "other": other})
                    break
    return out


def inspect(goals: List[dict], world, intent: str = "achieve",
            settled: bool = False, plan=None, table=None) -> Report:
    """Gate 3 over one reading. Deterministic, no model call.

    `settled` IS GATE 2'S GUARANTEE, AND IT IS WHY THE OLD `inert` RULE COLLIDED. An empty
    program has two causes — the goals ALREADY HOLD, or the reading does nothing — and one is
    a correct answer while the other is a defect. The single gate could not tell them apart
    and `inert` had to be demoted to a report on 2026-08-06. Gate 2 owns `settled` now, so
    passing its answer forward is what lets this one be a real check: **each gate guarantees
    something to the next.**
    """
    from planner import ghost_writer as _gw
    from planner.ir import intent as _intent

    report = Report()
    if not goals:
        return report

    # ── DOES IT ASSERT ANYTHING? The one check that needs neither a plan nor a world. ─────
    why = None
    try:
        why = _intent.vacuous(goals, intent)
    except Exception:
        why = None
    if why:
        report.vacuous.append({"why": str(why)})

    report.contradictory = contradictions(goals, table)
    report.uncountable = uncountable(goals, table)
    report.unrelated = unrelated(goals, table)

    # ── AND WHAT WOULD IT DO? Everything below here needs the writer. ─────────────────────
    if plan is None:
        try:
            plan = _gw.cover(goals, world)
        except _gw.Unsolvable as exc:
            # A REPORT AND NOT A FAULT. The engine answers this by PROMOTING to the tree —
            # a gate that refused here would turn an escalation into a wall, and the tree is
            # the regime that is good at exactly this kind of open-ended problem.
            report.unplannable.append({"why": str(exc)})
            return report
        except Exception:
            return report
    calls = plan if isinstance(plan, list) else (plan or {}).get("plan") or []
    if not calls and not settled:
        report.inert.append({"why": "the plan is empty and nothing says it already holds"})
    return report
