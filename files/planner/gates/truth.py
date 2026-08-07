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
                 fetch=None, settled=None, arity=None):
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
        # A GROUP OPERATION AIMED AT A SINGULAR — see `inspect` for the measurement.
        self.arity: List[Dict[str, Any]] = list(arity or ())

    @property
    def legal(self) -> bool:
        """`fetch` and `settled` are NOT faults. A gate whose resolve arm counted against the
        reading would refuse exactly the requests it knows how to help with."""
        return not (self.unreferable or self.illegal_values or self.unsatisfiable
                    or self.arity)

    def findings(self) -> List[str]:
        out = []
        for u in self.unreferable:
            out.append(f"it constrains {u['kind']} {u['name']!r}, and the lab holds no such "
                       f"{u['kind']}")
        for v in self.illegal_values:
            out.append(f"{v['kind']}.{v['attr']} cannot be {v['value']!r} "
                       f"— it is one of {sorted(v['allowed'])}")
        for s in self.unsatisfiable:
            out.append(f"a {s['kind']} can never satisfy {s['shape']}: {s['why']}")
        for a in self.arity:
            out.append(f"it says {a['shape']} over {a['kind']} {a['name']!r} — a group "
                       f"operation aimed at ONE member")
        return out

    def questions(self) -> List[str]:
        """WHAT TO ASK THE WORLD BEFORE JUDGING — the resolve arm, and it acts rather than
        refusing. Each entry is a kind nobody has looked at yet."""
        return [f"nothing has looked at {f['kind']} yet — probe it before judging "
                f"{f['name']!r}" for f in self.fetch]

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


def inspect(goals: List[dict], world, table=None) -> Report:
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
