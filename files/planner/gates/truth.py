"""truth.py — GATE 2. Does this reading refer to a world that can satisfy it?

    inspect(goals, world) -> Report(unreferable, illegal_values, unsatisfiable, fetch, settled)

## THE ONE QUESTION, AND THE OPERATOR'S OWN RULE FOR ANSWERING IT

The operator, 2026-08-07:

> *"if `web` and `lab` exist in the ledgers or in the world, it's a FETCH REFERENCE; if they
> don't, then we CREATE them as new items."*

So the identities in a reading divide, and the division is the whole gate:

    REFERS    the goal CONSTRAINS a member that must already be there —
              `every vm ...`, `observe vm ...`, `count(... WHERE name=X AND other=Y)`
    CREATES   the goal BRINGS a member into existence, or may mint one —
              `count(vm WHERE name=X) = 1`, and every value in a `must`

A REFERENCE to something the world does not hold is illegal: there is nothing to constrain.
A CREATION of something the world does not hold is the ordinary case and perfectly legal.

⇒ AND A READING IS A CONJUNCTION, so a reference is judged against the END STATE — the world
NOW plus whatever the reading itself mints. "create a vm named beta and then launch it"
constrains a machine its own sibling goal creates.
**The same absent name is a fault in one position and the point of the request in the other**,
which is why a rule that merely asks "does this name exist" produces a false alarm on every
`create` and has to be thrown away.

⇒ THE DISTINCTION IS ALREADY WORKED OUT: *"a SELECTOR refers (the name must be given), a
`must` ASSIGNS (the name may be minted)"* ([[gorgon-reading-names-writing-mints]]).

## ⇒ AND THE MUTATION THIS GATE OWNS IS NOT GATE 1'S

    GATE 1   the TOKEN changed          `fleet` -> `fleetsize`, data added or dropped
                                        ⇒ decidable from the SENTENCE alone
    GATE 2   the token is intact and    `db` -> `database`: well-formed, spelled plausibly,
             the OUTCOME changed        and the world holds no `database`
                                        ⇒ needs the WORLD, which is why it lives here

## ⇒ WHY "ABSENT" IS NOT A VERDICT UNTIL SOMEBODY HAS LOOKED

**A KIND THE WORLD CANNOT SEE IS NOT A KIND WITH NOTHING IN IT.** Decision 6, and the reason
this gate PROMPTS A FETCH instead of refusing: a world that cannot enumerate a kind answers
every question about it with an empty set, and a gate that trusted that would call every
reference to a real machine an invention. The lab mount declares `unseeded` for exactly this.

So an unresolvable name against an UNPROBED kind is not a fault — it is a question for the
world, and asking it is this gate's resolve arm. The operator named that case directly:
*"gate 2 should flag rung 13 for a world check, and REQUIRE IT TO PROMPT A FETCH."*

## WHAT IT DELIBERATELY DOES NOT DO

**IT DOES NOT READ THE REQUEST.** Whether the sentence contained a word is gate 1's, settled
and measured. This gate only ever asks the world. Keeping the request out is what stops gate 2
becoming a worse copy of gate 1 — the collision that forced the original single gate apart.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

REFERS = "refers"
CREATES = "creates"


class Report:
    """What gate 2 found, in five lists, because they resolve five different ways."""

    def __init__(self, unreferable=None, illegal_values=None, unsatisfiable=None,
                 fetch=None, settled=None, arity=None, uncarried=None,
                 shared=None):
        # A REFERENCE TO A MEMBER THE WORLD DOES NOT HOLD. Nothing to constrain.
        self.unreferable: List[Dict[str, Any]] = list(unreferable or ())
        # A VALUE THE MANIFEST DOES NOT ALLOW FOR THAT ATTRIBUTE.
        self.illegal_values: List[Dict[str, Any]] = list(illegal_values or ())
        # A SHAPE THE KIND CAN NEVER SATISFY — asked of the manifest, not of the world.
        self.unsatisfiable: List[Dict[str, Any]] = list(unsatisfiable or ())
        # NOBODY HAS LOOKED YET. Not a fault: a question for the world.
        self.fetch: List[Dict[str, Any]] = list(fetch or ())
        # ALREADY TRUE. Also not a fault — but the caller should know before it plans.
        self.settled: List[Dict[str, Any]] = list(settled or ())
        # ⇒ A GROUP OPERATION AIMED AT A SINGULAR — A REPORT, NOT A FAULT, AND THE
        #   DEMOTION IS MEASURED.
        #
        #   It looked like a clean legality rule: `every`/`per` over a key-pinned selector
        #   occurs 0 times in the 14 hand-written correct readings, so a shape no correct
        #   reading uses can be refused. **That sample was the wrong one.** Against 83 REAL
        #   model readings the shape appears on ones that PASS — `every vm WHERE name=db`
        #   five times — because it is a clumsy way to say something true and the writer
        #   plans it correctly anyway.
        #
        #   SO IT IS STILL WORTH SAYING AND NOT WORTH REFUSING. That is the same conclusion
        #   `clause-untouched` and `inert` reached on 2026-08-06, and the lesson underneath it
        #   is about the SAMPLE: fourteen hand-written readings are one idiom, and a rule
        #   validated only against them is a rule about that idiom.
        # N OF A MEMBER THAT ALREADY EXISTS — a count of copies wearing an identity's clothes.
        self.shared: List[Dict[str, Any]] = list(shared or ())
        # A CARDINALITY THE REQUEST STATED THAT NO GOAL CARRIES — gate 1 finds the numbers,
        # this gate judges them against the world. See `inspect` for the measurement.
        self.uncarried: List[Dict[str, Any]] = list(uncarried or ())
        self.arity: List[Dict[str, Any]] = list(arity or ())

    @property
    def legal(self) -> bool:
        """`fetch` and `settled` are NOT faults. A gate whose resolve arm counted against the
        reading would refuse exactly the requests it knows how to help with."""
        return not (self.unreferable or self.illegal_values or self.unsatisfiable
                    or self.uncarried or self.shared)

    def findings(self) -> List[str]:
        out = []
        for u in self.unreferable:
            out.append(f"it constrains {u['kind']} {u['name']!r}, and the lab holds no such "
                       f"{u['kind']}")
        for v in self.illegal_values:
            out.append(f"{v['kind']}.{v['attr']} cannot be {v['value']!r} "
                       f"— it is one of {sorted(v['allowed'])}")
        for h in self.shared:
            out.append(f"it asks for {h['amount']} {h['kind']}s all called {h['name']!r}, "
                       f"and {h['name']!r} is one that already exists")
        for u in self.uncarried:
            out.append(f"the request says {u['said']} and no goal asks for {u['said']} "
                       f"of anything")
        for s in self.unsatisfiable:
            out.append(f"a {s['kind']} can never satisfy {s['shape']}: {s['why']}")
        return out

    def reports(self) -> List[str]:
        """TRUE, WORTH SAYING, AND NOT A REASON TO DOUBT THE READING.

        Kept OUT of `findings()` so it cannot leak into the caller's fault channel: `rig.py`
        folds findings into `Answer.illegal`, and a report filed among faults is how a
        measurement nobody acted on becomes a refusal nobody intended.
        """
        return [f"it says {a['shape']} over {a['kind']} {a['name']!r} — a group "
                f"operation aimed at ONE member" for a in self.arity]

    def supply(self) -> List[Dict[str, Any]]:
        """THE RESOLVE ARM, AND IT ACTS. The goals that would establish what this reading
        needs — returned to be ADDED to the reading, never executed here.

        ⇒ A GATE THAT ONLY NAMES THE PROBE HAS NOT RESOLVED ANYTHING. The operator's
        instruction was that gate 2 must PROMPT A FETCH, and until now `questions()` was the
        whole of it: a sentence in the ledger and nothing that made the probe happen.

        ⇒ AND IT AMENDS THE READING RATHER THAN REACHING FOR THE WORLD. Gate 2 has no
        executor and should not have one — running a tool from inside a legality check is a
        second door onto the lab. What it CAN do is say the missing claim out loud:
        `observe(vm) alive`. The writer then plans the probe the way it plans anything else,
        the in-session grants it like any other step, and the whole path stays one path.
        MEASURED SUPPORT: rung 11's own known-good reading is exactly
        `observe(vm) alive` + `every vm WHERE alive=false must status=stopped` — so supplying
        the first goal turns a deficient reading INTO the hand-written correct one.

        ⇒ ONLY FOR AN UNESTABLISHED FACT, never for an unprobed KIND. "nobody has enumerated
        `file` yet" is answered by the mount, not by a goal, and inventing an `observe` for it
        would be a claim about a kind this reading never spoke about.
        """
        return [{"observe": {"kind": f["kind"]}, "fact": f["name"]}
                for f in self.fetch if f.get("probe")]

    def questions(self) -> List[str]:
        """WHAT TO ASK THE WORLD BEFORE JUDGING — the resolve arm, and it acts rather than
        refusing. Each entry is a kind nobody has looked at yet."""
        return [f"nothing has looked at {f['kind']} yet — probe it before judging "
                f"{f['name']!r}" for f in self.fetch]

    def asks(self) -> List[str]:
        """WHAT ONLY THE **OPERATOR** CAN SETTLE — as opposed to `questions()`, which the
        SYSTEM answers for itself by probing.

        ⇒ THESE TWO WERE MERGED INTO ONE METHOD AND IT BROKE THE BOUNCE. `questions()` travels
        to `Answer.fetch`, the channel for a question the world can answer; folding an
        operator's question into it sent the shared-identity ask somewhere nothing reads it,
        and rung 10's paraphrase BLOCKED with a perfectly good question sitting in the wrong
        field. Two audiences, two methods — merging them once already cost a shadowed
        definition, and merging them again cost a silent block.

        `to_goals` REFUSES a shared identity and is right to: three members cannot share one
        name. What it cannot do is say what the operator probably meant, which is N COPIES.
        """
        return [f"you asked for {h['amount']} {h['kind']}s called {h['name']!r}, and "
                f"{h['name']!r} already exists — did you mean {h['amount']} copies of it?"
                for h in self.shared]

    def __repr__(self) -> str:
        return (f"<Truth {'legal' if self.legal else 'ILLEGAL'} "
                f"unreferable={len(self.unreferable)} values={len(self.illegal_values)} "
                f"unsatisfiable={len(self.unsatisfiable)} arity={len(self.arity)} "
                f"fetch={len(self.fetch)} settled={len(self.settled)}>")


def _kinds(table=None) -> Dict[str, Any]:
    from planner.ir import config as _config
    return table if table is not None else (_config.KINDS or {})


def positions(goal: Dict[str, Any], table=None):
    """(kind, key, value, stance) for every identity a goal pins — DELEGATED.

    ⇒ THIS USED TO WORK OUT THE STANCES ITSELF, AND THAT WAS THE BUG. `to_goals` folds
    "create beta and launch it" into one `count(vm WHERE name=beta AND status=running) = 1`,
    this read the fold as a constraint, and passing readings were accused of holding a machine
    they were building. The fix was one line here — and gates 3 and 4 would each have hit the
    same fold and each needed their own version of it.

    So shape is read in ONE place now (`planner/gates/claims.py`) and every gate asks. Kept as
    a function rather than inlined because it is this gate's vocabulary for the shared answer,
    and its tests name it.
    """
    from planner.gates import claims as _claims
    out = []
    for claim in _claims.claims(goal, table):
        if claim.identity is None or claim.stance == _claims.ASSERTS:
            continue
        stance = REFERS if claim.stance == _claims.REFERS else (
            REFERS if claim.stance == _claims.REMOVES else CREATES)
        out.append((claim.kind, claim.key, claim.name, stance))
    return out


def _refers_to(attr: str, table=None) -> Optional[str]:
    """The kind an attribute POINTS AT, from the manifest's own `refs`, or None.

    DECLARED, NOT INFERRED. `vm.setters.add_vm_to_network` carries `refs: "network"`, so the
    manifest already says that `network` is a reference rather than a label — no name-matching
    heuristic, and a kind added later is covered without an edit here.
    """
    for spec in _kinds(table).values():
        if not isinstance(spec, dict):
            continue
        for setter in (spec.get("setters") or {}).values():
            if isinstance(setter, dict) and setter.get("attr") == attr:
                return setter.get("refs")
    return None


def _allowed(kind: str, attr: str, table=None) -> Optional[Set[str]]:
    """The declared value set for an attribute, or None if it is not enumerated."""
    values = ((_kinds(table).get(kind) or {}).get("attr_values") or {}).get(attr)
    return {str(v) for v in values} if values else None


def carried(n: int, goals: List[dict], here: int) -> bool:
    """Does some goal assert this number, or a number DERIVABLE from it and the world?

    ⇒ THE DERIVATION IS THE WHOLE RULE, and it is what makes this checkable at all. "clone
    golden into 3 NEW vms" is correctly served by `count(vm) = 4` — three clones plus the
    `golden` already there — because A COUNT IS A TOTAL AND THE REQUEST STATED A DELTA
    ([[gorgon-count-is-a-total]]). A rule demanding the literal 3 accuses that reading, which
    is a hand-written CORRECT answer; a rule that also accepts `3 + here` does not.

    THIS IS WHY THE CHECK CANNOT LIVE IN GATE 1. `here` is the world.
    """
    asserts = set()
    for goal in goals or ():
        for field in ("eq", "gte", "lte", "min", "max"):
            if isinstance(goal.get(field), int):
                asserts.add(goal[field])
    if n in asserts:
        return True
    return any(x == n + here or x == here - n or x == n - here for x in asserts)


def inspect(goals: List[dict], world, table=None,
            said_numbers: Optional[Set[int]] = None,
            copies: Optional[List[Dict[str, Any]]] = None) -> Report:
    """Gate 2 over one reading. Deterministic, no model call, NO REQUEST TEXT.

    The world is asked through the language's own reader, so a production mount answers this
    exactly as a bench world does — the defect that made every earlier gate result bench-only.
    """
    from planner import ghost_writer as _gw
    from planner.ir import effects as _effects

    table = _kinds(table)
    report = Report()
    try:
        select, _holds = _gw._seams_of(world)
    except Exception:
        return report                      # a world nobody can read is not a reading's fault

    blind = set(getattr(world, "unseeded", ()) or ())
    seen: Dict[str, Set[str]] = {}

    # ⇒ WHAT THIS READING WILL BRING INTO EXISTENCE, GATHERED BEFORE ANYTHING IS JUDGED.
    #
    #   A READING IS A CONJUNCTION OF CLAIMS ABOUT THE END STATE, NOT A SEQUENCE OF LOOKUPS.
    #   "create a vm named beta and then launch it" is `count(vm WHERE name=beta) = 1` AND
    #   `every vm WHERE name=beta must status=running` — the second constrains a machine the
    #   FIRST creates. Judging each goal against the world ALONE called that a reference to a
    #   machine that does not exist, and it was 2 of the 5 false alarms this gate opened with.
    #
    #   SO A REFERENCE IS LEGAL IF THE END STATE WILL HOLD IT: the world now, PLUS whatever
    #   the reading itself mints.
    minted: Dict[str, Set[str]] = {}
    # AND WHICH OBSERVED FACTS THIS READING ESTABLISHES FOR ITSELF. Same conjunction argument:
    # a reading that pings BEFORE it filters has supplied its own precondition.
    established: Set[Tuple[str, str]] = set()
    for goal in goals or ():
        for kind, _key, value, stance in positions(goal, table):
            if stance == CREATES:
                minted.setdefault(kind, set()).add(str(value))
        watch = goal.get("observe")
        if isinstance(watch, dict) and goal.get("fact"):
            established.add((watch.get("kind"), str(goal["fact"])))
    # WHAT THE WORLD HAS ALREADY BEEN ASKED, so a second request in the same session does not
    # re-probe what the ledger already holds. `Findings` is not a plain sequence — it exposes
    # `known()` — and a bare `or ()` over it raises rather than degrading, so it is asked by
    # name and every other shape is tolerated.
    book = getattr(world, "findings", None)
    rows = ()
    for accessor in ("known", "persistable"):
        got = getattr(book, accessor, None)
        if callable(got):
            try:
                rows = got() or ()
                break
            except Exception:
                rows = ()
    for finding in rows if not isinstance(rows, dict) else rows.values():
        if isinstance(finding, dict) and finding.get("fact") and finding.get("kind"):
            established.add((finding["kind"], str(finding["fact"])))

    def members(kind: str) -> Set[str]:
        if kind not in seen:
            try:
                seen[kind] = {str(n) for n in (select({"kind": kind}) or [])}
            except Exception:
                seen[kind] = set()
        return seen[kind]

    # ⇒ N OF A MEMBER THAT ALREADY EXISTS. Gate 1 read these off the RAW answer, because
    #   `_refuse_shared_identity` drops the goal before any gate could look.
    #
    #   THE MEMBERSHIP TEST IS WHAT MAKES IT SAFE, and it took three attempts to find. On the
    #   raw alone the check costs 25 false alarms of 58 — the `name` slot is a SINK for
    #   descriptions the model cannot shape (`'every'`, `'vms labelled prod'`) which are
    #   repaired away rather than meant as identities. Narrowing to names the operator SAID
    #   still costs 9, because `'blue'` is said as a LABEL. Narrowing to names that are
    #   EXISTING MEMBERS costs **0 of 58** and catches rung 10's paraphrase.
    for copy in copies or ():
        if str(copy.get("name")) in members(str(copy.get("kind"))):
            report.shared.append(dict(copy))

    # ⇒ A CARDINALITY THE OPERATOR STATED AND NO GOAL CARRIES.
    #
    #   GATE 1 FINDS THE NUMBERS AND THIS GATE JUDGES THEM, because the question needs BOTH
    #   the sentence and the world and neither gate may have the other's subject. What crosses
    #   is a SET OF INTEGERS — a fact, not a sentence — so gate 2 still reads no English.
    #
    #   MEASURED BEFORE IT WAS WRITTEN: 5 catches against ONE distinct false alarm, and the
    #   false alarm is rung 13's paraphrase, which omits `count(vm) = 5` and is labelled PASS
    #   ONLY BECAUSE THE WORLD ALREADY HOLDS FIVE MACHINES. The reading is deficient and works
    #   by luck; flagging it is right and the outcome metric cannot see that.
    if said_numbers:
        kinds = {(g.get("select") or g.get("every") or {}).get("kind") for g in goals or ()}
        here = max([len(members(k)) for k in kinds if k] or [0])
        for n in sorted(said_numbers):
            if not carried(n, goals, here):
                report.uncarried.append({"said": n, "world": here})

    for goal in goals or ():
        for kind, key, value, stance in positions(goal, table):
            name = str(value)
            if kind in blind:
                # NOBODY HAS LOOKED. Decision 6: unseeded is not empty, and judging here would
                # call every real machine an invention.
                report.fetch.append({"kind": kind, "name": name, "why": "unprobed kind"})
                continue
            here = members(kind) | minted.get(kind, set())
            if stance == REFERS and name not in here:
                report.unreferable.append({"kind": kind, "key": key, "name": name,
                                           "holds": sorted(here)[:8]})
            elif stance == CREATES and name in members(kind):
                # NOT A FAULT. "create a vm named alpha" against a lab that has one is
                # ALREADY TRUE, and the program regime's right answer is an empty program —
                # which is a legitimate outcome, not a refusal.
                report.settled.append({"kind": kind, "name": name})

        # ⇒ GROUP / WORLD CONSISTENCY: A QUANTIFIER AIMED AT A SINGLE MEMBER.
        #
        #   The operator, 2026-08-07: gate 2 is *"group/world consistency — it catches if you
        #   use FOREACH ON A SINGULAR."* `every vm WHERE name='alpha'` is a group operation
        #   over a set the manifest guarantees holds at most ONE member, because `name` is the
        #   kind's KEY. The reading is not wrong about the world; it is wrong about ARITY —
        #   the model reached for the quantified shape where a singular claim was meant.
        #
        #   MEASURED BEFORE IT WAS WRITTEN, which is what makes it a rule rather than a hunch:
        #   `every`/`per` over a key-pinned selector occurs **0 times in the 14 hand-written
        #   correct readings**. A shape no correct reading ever uses can be refused; one they
        #   use idiomatically could only ever have been a report.
        for field in ("every", "per"):
            sel = goal.get(field)
            if not isinstance(sel, dict):
                continue
            k = ((table.get(sel.get("kind")) or {}).get("key"))
            if k and isinstance(sel.get(k), (str, int)):
                report.arity.append({"shape": field, "kind": sel.get("kind"),
                                     "key": k, "name": sel[k]})

        # ⇒ A FACT NOBODY HAS ESTABLISHED. The operator, 2026-08-07: gate 2 resolves
        #   *"fetch/create issues as well as STATUS (alive/etc) RESOLUTION."*
        #
        #   `alive` IS NOT STORED, IT IS ASKED. The manifest says who asks — `observed.alive.by`
        #   — so a goal that FILTERS on it has a precondition nothing else can supply: somebody
        #   has to ping first. "stop the ones that do not answer" is `observe(vm) alive` AND
        #   `every vm WHERE alive=false must status=stopped`, and a reading carrying only the
        #   second is filtering on a fact it never established.
        #
        #   AND THE ANSWER IS A FETCH, NOT A REFUSAL, for the reason the ledger exists:
        #   **NOBODY ASKED IS NOT THE SAME AS IT SAID NO.** An unobserved `alive` reads as
        #   `false` to anything that treats absence as denial — which would stop every machine
        #   in the lab on a request to stop the unresponsive ones.
        for sel in (goal.get("every"), goal.get("per"), goal.get("observe"),
                    goal.get("select")):
            if not isinstance(sel, dict):
                continue
            kind = sel.get("kind")
            for attr in sel:
                if attr in ("kind", "not", "any", "all", "except"):
                    continue
                if not _effects.probe_for(kind, attr, table):
                    continue                      # a stored attribute, not an observed fact
                if (kind, attr) in established:
                    continue
                report.fetch.append({"kind": kind, "name": attr,
                                     "why": "an observed fact nothing has asked for",
                                     "probe": _effects.probe_for(kind, attr, table)})

        # ⇒ CAN THIS KIND SATISFY THIS SHAPE AT ALL? Asked of the MANIFEST, so the answer is
        #   the same on an empty lab as on a full one — and it is the question
        #   [[gorgon-can-the-world-satisfy-it]] records as the one that keeps paying: four
        #   shapes were offered to kinds that could never satisfy them.
        #
        #   EVERY ARM READS A DECLARATION AND NONE GUESSES. A kind with no creator cannot be
        #   counted into existence; one with no deleter cannot be counted to zero; a fact no
        #   kind declares `observed` cannot be established; an attribute with no setter cannot
        #   be required. The manifest already says all four.
        shape = str(goal.get("shape") or "")
        sel = goal.get("select") or goal.get("every") or goal.get("per") \
            or goal.get("observe") or {}
        kind = sel.get("kind")
        spec = table.get(kind) or {}
        if kind and spec:
            if shape == "count" and goal.get("eq") == 0 and not spec.get("delete"):
                report.unsatisfiable.append({"kind": kind, "shape": "count = 0",
                                             "why": "nothing can remove one"})
            elif shape == "count" and goal.get("eq") not in (0, None) \
                    and not (spec.get("create") or spec.get("creators")):
                report.unsatisfiable.append({"kind": kind, "shape": f"count = {goal['eq']}",
                                             "why": "nothing can make one"})
            # ⇒ `exists` IS ANSWERED BY ENUMERATION, NOT BY A PROBE, so `probe_for` correctly
            #   returns nothing for it and reading that as "unsatisfiable" accused 3 PASSING
            #   readings. Any kind the world can list can answer whether a member is there;
            #   only a fact that needs a TOOL needs a declaration.
            if "observe" in goal and str(goal.get("fact") or "") not in ("", "exists") \
                    and not _effects.probe_for(kind, str(goal["fact"]), table):
                report.unsatisfiable.append({"kind": kind,
                                             "shape": f"observe {goal['fact']}",
                                             "why": "no probe establishes it"})
            for attr in (goal.get("must") or {}):
                if not _effects.writable(kind, attr, table):
                    report.unsatisfiable.append({"kind": kind, "shape": f"must {attr}",
                                                 "why": "nothing can set it"})

        # VALUES THE MANIFEST FORBIDS. Asked of the declaration, never of the world, so it is
        # the same answer on an empty lab as on a full one.
        must = goal.get("must")
        if isinstance(must, dict):
            sel = goal.get("every") or goal.get("select") or {}
            kind = sel.get("kind")
            for attr, value in must.items():
                allowed = _allowed(kind, attr, table)
                if allowed and str(value) not in allowed:
                    report.illegal_values.append({"kind": kind, "attr": attr,
                                                  "value": value, "allowed": allowed})
    return report
