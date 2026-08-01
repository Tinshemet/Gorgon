"""ghost_writer.py — turn a goal into a program. NO MODEL, anywhere in this file.

The operator's design (#60, #61): the AI translates a request into predicates, and this
writes the code. It was `tile_solver.py` until the operator named it, and the name is better
— it does not decide anything, it writes what the goal already implies.

THREE RULES, AND STAGED LOWERING IS THE THIRD:

    1. a goal that already HOLDS contributes nothing        (`already_satisfied`)
    2. a goal a tile INVERTS becomes that tile, preconditions first
    3. a goal no tile inverts is LOWERED into sub-goals, and each is covered the same way

Rule 3 is staged lowering, arriving where it belongs. As a MODEL technique it measured
30/78, because it asked a model to assign operators to prose fragments — the one thing a
model cannot do (#55). The design was never the problem; the consumer was. Lowering a
PREDICATE into sub-predicates is arithmetic, and nothing here can misread a sentence,
because nothing here reads one.

THE VIRTUAL WORLD. Planning runs against a deep copy, and every placed tile is executed on
it. That is not an optimisation: it is what makes lowering correct. "Every stopped machine"
must be resolved against the world AS IT WILL BE when the tile runs, not as it was when
planning began — otherwise a program that creates machines and then labels them would label
only the ones that existed at the start. It also removes the re-derivation wart the first
version had: a precondition met by an earlier tile is simply true by the time it is checked.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from .ir import effects
from .ir import observe as _observe
from .ir import refs


def _kinds(world):
    """The manifest this world is described by, or the default target's."""
    return getattr(world, "kinds", None)


def _seams_of(world):
    """The world's own adapter — `(select, holds)`, part of the mount contract.

    IT USED TO FALL BACK TO `tests.bench.seams` for a world that named none, because the VM
    sim was the one world exempt from the contract, for no reason but history. So a
    production module carried an import of the TEST TREE on a live code path, and a checkout
    shipped without `tests/` would have reported a missing test package where the real fault
    is "this world forgot to say".

    The sim declares its own now, in three lines, exactly like every other world. There is no
    fallback because there is nothing left to fall back for.
    """
    got = getattr(world, "seams", None)
    if got is None:
        raise TypeError(
            f"{type(world).__name__} declares no `seams` — a world names `kinds`, `seams` "
            f"and `execute`, and that is the whole mount contract")
    return got

Call = Tuple[str, Dict[str, Any]]


class Unsolvable(Exception):
    """No tile and no lowering rule reaches a goal — the writer's honest failure.

    DELIBERATELY WITHOUT A FALLBACK. A writer that improvises when it cannot find a tile can
    produce a program nothing vouches for, and the entire reason to move generation out of
    the model is that this component does not guess. `Unsolvable` is also the signal the
    operator's design wants: when the writer cannot build it, the request goes back for
    decomposition rather than forward as something plausible.
    """


def _sel(sel: Dict[str, Any]) -> str:
    return " ".join(f"{k}={v}" for k, v in (sel or {}).items() if k != "kind")


def _short(p: Dict[str, Any]) -> str:
    """One line for a goal of ANY shape, because these strings are read by people.

    IT USED TO SPEAK ONLY `count` AND `reach`, so an `every` — the most common component the
    extractor produces — rendered as `None:?[] >= ?` in refusal messages and in the book
    keeper's report. A diagnostic that cannot name the thing it is diagnosing sends the
    reader back to a debugger.
    """
    if "_call" in p:
        tool, args = p["_call"]
        return f"call {tool}({_sel(args)})"
    for shape in ("every", "observe", "per"):
        if shape in p:
            sel = p[shape]
            head = f"{shape} {sel.get('kind', '?')}"
            if _sel(sel):
                head += f"[{_sel(sel)}]"
            if shape == "every":
                return f"{head} must {_sel(p.get('must') or {})}"
            if shape == "per":
                return f"{head} -> one {p.get('make', '?')} ({p.get('link', '?')})"
            return f"{head} · {p.get('fact', 'alive')}"
    sel = p.get("select") or {}
    tail = f"== {p['eq']}" if "eq" in p else f">= {p.get('min', '?')}"
    return f"{p.get('shape')}:{sel.get('kind', '?')}[{_sel(sel)}] {tail}"


# WHAT A BOUND NAME MAY LOOK LIKE — the schema's own rule, where the WRITER can meet it. The
# writer builds IR directly and is otherwise never held to the constraints the model is held
# to, which is how `STORE http://x = …` once shipped with every suite green.
_PRONOUNCEABLE = __import__("re").compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _fresh_names(kind: str, n: int, taken: set) -> List[str]:
    """Names for members the request never named.

    A REAL GAP, filled deterministically rather than left to a model. "create 5 vms" says
    nothing about what they are called, so somebody must decide; a fixed, world-aware scheme
    means the same request against the same world always yields the same program, which is
    the property that makes the whole pipeline debuggable.
    """
    out, i = [], 1
    while len(out) < n:
        name = f"{kind}{i}"
        if name not in taken:
            out.append(name)
            taken.add(name)
        i += 1
    return out


def _lower(goal: Dict[str, Any], select, world) -> List[Dict[str, Any]]:
    """Decompose a goal no tile inverts, into goals that tiles do. [] means no rule applies.

    Every rule here turns a statement about a SET into statements about NAMED MEMBERS, which
    is the only shape `effects.invert` speaks. That is the whole of the translation from
    collective language to a program.
    """
    # `every` — A COMPONENT, NOT A PREDICATE, and the distinction is deliberate. Medusa's
    # `all` is a COMPOSITE ("every one of these checks holds"), not a universal over a set,
    # so reusing the name would collide with a shape the language already evaluates.
    #
    # This is the operator's design arriving literally: the writer's INPUT is what the AI
    # extracted — a quantifier, a selector, a target state — not something the predicate
    # language has to be able to express. What the language must express is the WITNESS,
    # and `_ground` turns this back into an ordinary count whose number the writer knows
    # because it resolved the set.
    if "every" in goal:
        sel = dict(goal["every"])
        kind = sel.get("kind")
        spec = effects._K(_kinds(world)).get(kind) or {}
        key = spec.get("key")
        if not key:
            return []
        return [{"shape": "count", "select": {"kind": kind, key: m, **goal["must"]},
                 "eq": 1} for m in select(sel)]

    # `observe` — ASK, without requiring anything of the answer. Rung 11 needs every
    # machine pinged before anything can act on WHICH ones answered, and that is not a
    # reach goal: reach also demands a shared network, which the request never asked for.
    # The manifest names the asker (`observed.<fact>.by`), so the rule reads it.
    if "observe" in goal:
        sel = dict(goal["observe"])
        kind = sel.get("kind")
        spec = effects._K(_kinds(world)).get(kind) or {}
        key, probe = spec.get("key"), effects.probe_for(kind, goal.get("fact", "alive"))
        if not key or not probe:
            return []
        return [{"_call": (probe, {key: m})} for m in select(sel)]

    # `per` — one NEW member of another kind for each member of a set. Rung 12's snapshots
    # are the case, and they are the real question it asks: is a third kind one manifest row
    # or does it need language code? Here it is a row — `snapshot` declares its creator and
    # its key like anything else, and this rule never mentions snapshots.
    if "per" in goal:
        src = dict(goal["per"])
        skind = src.get("kind")
        made = goal["make"]
        mspec = effects._K(_kinds(world)).get(made) or {}
        mkey = mspec.get("key")
        if not mkey:
            return []
        taken = set(select({"kind": made}))
        out = []
        for m in select(src):
            name = _fresh_names(made, 1, taken)[0]
            out.append({"shape": "count",
                        "select": {"kind": made, mkey: name, goal["link"]: m}, "eq": 1})
        return out

    shape = goal.get("shape")
    sel = dict(goal.get("select") or {})
    kind = sel.get("kind")
    spec = effects._K(_kinds(world)).get(kind) or {}
    key = spec.get("key")
    if not key:
        return []

    # REACH — a finding AND a topology, so it lowers into both halves. A5 tightened the
    # bench's `reach` to demand that every member has ANSWERED and that they share a
    # network, precisely because production and the bench had drifted on this. So the
    # lowering has to satisfy both: put them together, then ask.
    if shape == "reach":
        probe = effects.probe_for(kind, "alive", _kinds(world))
        if not probe:
            return []
        members = select(sel)
        subs: List[Dict[str, Any]] = []
        # WHAT CONNECTS MEMBERS IS A MANIFEST FACT, not the word "network". The setter whose
        # value `refs` another kind is the connective one, whatever it happens to be called.
        link = next((s_ for s_ in (spec.get("setters") or {}).values()
                     if s_.get("refs")), None)
        connector = link["attr"] if link else None
        ref_kind = link["refs"] if link else None
        # HOW MANY MEMBERS SIT ON EACH CANDIDATE, computed once and used for both questions:
        # do they ALREADY share one, and if not, which is the cheapest to move them onto.
        #
        # IT USED TO ASK `world.common_networks(members)` FOR THE FIRST — a bespoke method the
        # SIM happened to have and the real lab's scratch did not, so the first `reach` goal
        # ever planned against the QEMU mount died with AttributeError. A world seam that only
        # one world implements is not a seam, it is a dependency on one implementation. The
        # tally below answers it from `select` alone, which every world already provides.
        tally: Dict[str, int] = {}
        if connector:
            for cand in select({"kind": ref_kind}):
                n_on = len([m for m in members
                            if m in select({"kind": kind, connector: cand})])
                if n_on:
                    tally[cand] = n_on
        shared = members and any(n == len(members) for n in tally.values())
        if connector and not shared:
            # PREFER A NETWORK THEY MOSTLY ALREADY SHARE. Rung 9 is the case: two of three
            # sit on `mesh0` and one does not, and the work is finding WHICH is wrong. A
            # writer that created a fresh network and moved all three would pass the
            # checker while doing three times the work and discarding what was already
            # right. Ties break on the name so the same world yields the same program.
            net = (max(sorted(tally), key=lambda n: tally[n]) if tally
                   else _fresh_names(ref_kind, 1, set(select({"kind": ref_kind})))[0])
            subs.append({"every": dict(sel), "must": {connector: net}})
        subs += [{"_call": (probe, {key: m})} for m in select(sel)]
        return subs

    if shape != "count" or key in sel:
        return []

    members = select(sel)
    want = goal.get("eq")
    filters = {k: v for k, v in sel.items() if k != "kind"}

    # "NO MEMBER MAY MATCH" — flip each one that does. The value to flip TO is the
    # attribute's other legal value, and `complement` returns None when there are three or
    # more, because the goal genuinely did not say which. Declining beats picking.
    if want == 0 and len(filters) == 1:
        attr, bad = next(iter(filters.items()))
        good = effects.complement(kind, attr, bad, _kinds(world))
        if good is None:
            return []
        return [{"shape": "count", "select": {"kind": kind, key: m, attr: good}, "eq": 1}
                for m in members]

    if want is None:
        return []

    if want < len(members):
        # TOO MANY MATCH. Which members go is a DETERMINISTIC SLICE off the end of a sorted
        # list, so the same request against the same world always removes the same ones —
        # the property that makes a destructive program reviewable before it runs.
        #
        # REMOVING A VALUE AND DELETING A MEMBER ARE NOT THE SAME ACT. Taking `prod` off a
        # machine is reversible and cheap; deleting the machine is neither. Where the goal
        # names an attribute, the attribute is what is surrendered — the writer never
        # destroys a member to satisfy a claim that was only ever about a label.
        surplus = members[want:]
        if len(filters) == 1 and "not" not in filters:
            attr, value = next(iter(filters.items()))
            return [{"shape": "count", "select": {"kind": kind, key: m, attr: value},
                     "eq": 0} for m in surplus]
        if not filters:
            return [{"shape": "count", "select": {"kind": kind, key: m}, "eq": 0}
                    for m in surplus]
        return []

    if want == len(members):
        return []

    # NOT ENOUGH MEMBERS MATCH. Two ways to close the gap, and the order matters: convert
    # members that already exist before creating new ones, because creating a machine to
    # satisfy "five carry the fleet label" when five machines already exist is the wrong
    # program — it satisfies the count and misreads the request.
    deficit = want - len(members)
    subs: List[Dict[str, Any]] = []
    if filters:
        matched = set(members)
        # CANDIDATES MUST RESPECT THE GOAL'S OWN CARVE-OUT. "two blue ones that are not
        # red" may not be satisfied by relabelling a red one, and rung 6 is exactly that
        # partition: without this, `count(vm label=blue)=2` cheerfully paints two of the
        # three machines the previous goal made red. The exclusion is asked of `select`,
        # which already evaluates carve-outs, rather than reimplemented here.
        pool = {"kind": kind}
        if sel.get("not"):
            pool["not"] = sel["not"]
        for m in [x for x in select(pool) if x not in matched][:deficit]:
            subs.append({"shape": "count",
                         "select": {"kind": kind, key: m,
                                    **{k: v for k, v in filters.items() if k != "not"}},
                         "eq": 1})
        deficit -= len(subs)
    plain = {k: v for k, v in filters.items() if k != "not"}
    for name in _fresh_names(kind, deficit, set(select({"kind": kind}))):
        # ONE SUB-GOAL, NOT TWO — carrying the filters the goal asked for, minus the
        # carve-out, which scoped the SET and says nothing once a member is named.
        #
        # It used to emit a bare creation and THEN the attributes, which works only while
        # every attribute has a setter. VMs do: labels and networks are added after the
        # fact. A KITCHEN does not — an ingredient's dish is what the ingredient IS, fixed
        # when it is added — so the second sub-goal arrived at a member that already existed
        # and no tool could change. Asking for the whole thing at once lets `invert` decide:
        # a setter where one exists (and its precondition creates the member first), the
        # creator with arguments where none does.
        subs.append({"shape": "count",
                     "select": {"kind": kind, key: name, **plain}, "eq": 1})
    return subs


def _self_vouched(goal, body, kinds, select) -> bool:
    """Is every member this goal is about one that a `new` in this body already checked?

    NARROW, AND IT DECLINES WHEN UNSURE. Only a plain identity or count over a kind counts:
    a goal carrying `reach`, an observation, or a filter the creation does not establish is
    NOT vouched for by the creation, because `new` proves the member exists and says nothing
    about what else became true of it.
    """
    if goal.get("shape") != "count" or "eq" not in goal:
        return False
    sel = goal.get("select") or {}
    kind = sel.get("kind")
    spec = effects._K(kinds).get(kind) or {}
    key = spec.get("key")
    if not key:
        return False
    news = [st for st in body if st.get("op") == "new" and st.get("kind") == kind]
    if not news:
        return False
    # THE GOAL'S FILTERS MUST BE ONES THE CREATION ITSELF SUPPLIES. `name` and anything the
    # creator was passed are established by the call; a label or a network is not.
    extra = {k: v for k, v in sel.items() if k not in ("kind", key)}
    for st in news:
        args = st.get("args") or {}
        if any(str(args.get(a)) != str(v) for a, v in extra.items()):
            return False
    named = sel.get(key)
    if named is not None:
        return any((st.get("args") or {}).get(key) == named for st in news)
    # AN UNNAMED COUNT is vouched for when the creations ARE the whole of it.
    return len(news) == goal["eq"] and len(select({"kind": kind})) == goal["eq"]


def _ground(goal, select):
    """The predicate that WITNESSES a goal — what the program's closing ENSURE will say.

    A count goal is already its own witness. An `every` component is not a predicate at all,
    so it becomes one here: every member of S carries the target, which is a count over
    S-and-target equal to the size of S. The writer knows that number because it resolved
    the set — the language never has to learn a universal quantifier to check the work.
    """
    if "per" in goal:
        src = dict(goal["per"])
        made, link = goal["make"], goal["link"]
        return [{"shape": "count", "select": {"kind": made, link: m}, "eq": 1}
                for m in select(src)]
    if "every" not in goal:
        return goal
    sel = dict(goal["every"])
    return {"shape": "count", "select": {**sel, **goal["must"]},
            "eq": len(select(sel))}


def _holds(goal, holds, select):
    """True when the goal is met — routed through `_ground` so both input forms answer."""
    g = _ground(goal, select)
    if isinstance(g, list):
        for one in g:
            ok, why = holds(one, {})
            if not ok:
                return False, why
        return True, f"all {len(g)} witness(es) hold"
    return holds(g, {})


def _named_in(goals, kinds) -> set:
    """Every `(kind, name)` the REQUEST itself mentions.

    A member the operator named is theirs whatever the writer had to do to bring it about;
    one they never mentioned, created only so their request could happen, is the program's.
    That is the whole of the temp/fetched distinction and it needs no guess about intent.
    """
    out = set()
    for goal in goals or ():
        for holder in ("select", "every", "observe", "per"):
            sel = goal.get(holder)
            if not isinstance(sel, dict):
                continue
            kind = sel.get("kind")
            key = (effects._K(kinds).get(kind) or {}).get("key")
            if kind and key and sel.get(key):
                out.add((kind, sel[key]))
            # A NAME MENTIONED AS AN ATTRIBUTE IS STILL A NAME. "a snapshot of web" names
            # `web` as plainly as "the machine web" does — the operator said it, so the
            # machine is theirs and the program does not take it down afterwards. Missing
            # this had the writer create `web`, snapshot it, and then DELETE THE MACHINE THE
            # OPERATOR HAD NAMED. Same convention `precondition` uses: an attribute whose
            # name is a declared kind refers to a member of it.
            for attr, value in sel.items():
                if attr in ("kind", "not") or not isinstance(value, str):
                    continue
                if attr in effects._K(kinds):
                    out.add((attr, value))
        for extra in ("make",):
            made = goal.get(extra)
            if isinstance(made, str) and made in effects._K(kinds):
                out.add((made, None))
    return out


def _asked_kinds(goals) -> set:
    """Every KIND the request is about — the third clause of the provenance rule.

    THE TWO CLAUSES ABOVE ARE ABOUT NAMES, AND A REQUEST NEED NOT USE ANY. *"create 3 vms
    labelled red and 2 labelled blue"* names no machine at all, so every one of the five the
    writer mints was scaffolding by the name test, and rung 6's program CREATED THE FIVE
    MACHINES IT WAS ASKED FOR AND THEN DELETED THEM — ten calls of teardown on top of a
    22-call plan, closing DONE against a world it had just emptied. The third instance of
    this same bug, and each earlier one was fixed at the level it was found: first every
    precondition-creation was temp, then a name in the selector's key was honoured, then a
    name in an attribute. All three were sharpenings of "did they SAY it".

    THE QUESTION IS NOT WHETHER THEY NAMED IT — IT IS WHETHER THE GOAL IS ABOUT IT. Asked of
    the KIND, which every goal declares whether or not it names a member:

        create 3 vms labelled red   the goals range over `vm`, so a vm is the DELIVERABLE
        search the web for X        the goals range over `search`, and the `vm` created to
                                    host a browser is a MEANS — nobody asked for a machine

    That is what the motivating case actually turned on, and unlike a name it survives a
    request that mentions none. It only ever WIDENS what belongs to the operator, which is
    the safe direction: scaffolding left standing is litter, and a deliverable torn down is
    the request undone.
    """
    out = set()
    for goal in goals or ():
        out |= kinds_of(goal)
    return out



def _scratch_of(world):
    """A world safe to PLAN against — a model of it, never the thing itself.

    THE BUG THIS EXISTS FOR, found 2026-08-01 the first time the QEMU mount met a real
    library: `cover` advances its virtual world by EXECUTING each placed tile on a deep copy.
    That is safe for a sim, whose `execute` mutates its own dict. It is catastrophic for a
    world whose `execute` reaches OUTSIDE ITSELF — deep-copying a lab copies a reference to
    the real executor, so PLANNING PERFORMED THE ACTIONS. A single goal produced a plan and
    created a machine on the way to producing it, which the program would then have created
    again.

    So a world may offer `scratch()`: a stand-in with the same state and a simulated
    executor. A world that does not offer one is assumed to be pure state, which is what a
    sim is, and is copied. THE DISTINCTION IS THE WORLD'S TO DECLARE, because only it knows
    whether its hands reach outside.
    """
    maker = getattr(world, "scratch", None)
    return maker() if callable(maker) else copy.deepcopy(world)


def cover(goals: List[Dict[str, Any]], world, trace: List[str] = None,
          temps: List = None, acting: bool = True,
          without: Optional[str] = None) -> List[Call]:
    """The calls that make every goal hold, in an order that runs.

    `temps` collects `(kind, name)` for every member this plan CREATES as a precondition —
    something nobody asked for, made so the request could happen. `as_program` takes them
    down at the end.

    `acting=False` PLANS A CHECK RATHER THAN A CORRECTION, and it is the writer's side of the
    intent ladder. This function is the ACHIEVE engine: it closes whatever gap it finds. Under
    a `fetch` or an `ensure` there is no gap to close — the operator asked what is so — and
    planning the correction anyway meant an ENSURE request was translated into a program that
    creates machines and then REFUSED for exceeding its authority. The operator asked a
    question and was told they were not allowed to ask it.

    PROBES STILL RUN, because you cannot report on what you never asked: `reach` and every
    observed attribute are read out of the findings ledger, and a check that skipped the
    probe would answer `unknown` and call it a verdict. What is withheld is every tile that
    CHANGES something — and an unmet goal is then not a failure, it is the answer.
    """
    scratch = _scratch_of(world)
    asked = _named_in(goals, _kinds(scratch))
    # AND THE KINDS THE REQUEST IS ABOUT, computed once beside the names for the same reason
    # the names are: a member is the operator's if they NAMED it or if the goals RANGE OVER
    # its kind, and a request need not contain a single name.
    asked_kinds = _asked_kinds(goals)
    plan: List[Call] = []
    for _round in range(4):
        before = len(plan)
        for goal in goals:
            _achieve(goal, scratch, plan, trace, 0, temps=temps, asked=asked,
                     asked_kinds=asked_kinds, acting=acting, without=without)
        if len(plan) == before:
            return plan
        if trace is not None:
            trace.append(f"— goals interacted; re-covering (round {_round + 2})")
    # Four passes without settling means a goal is undoing another's work, which no amount
    # of further looping fixes and which the writer must not paper over by stopping quietly.
    raise Unsolvable("goals do not settle — they may be pulling against each other")


def _achieve(goal, scratch, plan, trace, depth, internal=False, temps=None, asked=None,
             asked_kinds=None, acting=True, without=None):
    if depth > 12:
        raise Unsolvable("lowering too deep — a goal probably depends on itself")
    say = (lambda m: trace.append("  " * depth + m)) if trace is not None else lambda m: None
    sel, holds = _seams_of(scratch)

    # A LOWERING RULE MAY EMIT A BARE CALL. `reach` needs each member probed, and a probe
    # asserts nothing about the registry — it writes a FINDING. There is no predicate for
    # "has been asked", so the rule names the call directly and says so here rather than
    # inventing a predicate shape to make the code uniform.
    if "_call" in goal:
        tool, args = goal["_call"]
        if (tool, args) not in plan:
            plan.append((tool, args))
            scratch.execute(tool, args)
            say(f"probe {tool}({args})")
        return

    # AN OBSERVATION IS NOT A STATE, so it has no witness and no post-check. "Ask every
    # machine" is a thing DONE, not a thing that becomes true — the findings it writes are
    # what later goals read. Verifying it would need a predicate for "has been asked",
    # which the language does not have and should not grow just to make this uniform.
    if "observe" in goal:
        subs = _lower(goal, sel, scratch)
        say(f"observe {goal['observe']} — {len(subs)} probe(s)")
        for s_ in subs:
            _achieve(s_, scratch, plan, trace, depth + 1, internal=internal, temps=temps, asked=asked,
                     asked_kinds=asked_kinds, acting=acting, without=without)
        return

    ok, why = _holds(goal, holds, sel)
    if ok:
        say(f"{_short(goal)} — ALREADY HOLDS ({why})")
        return

    if not acting:
        # A CHECK PLACES NO WORK, AND AN UNMET GOAL IS THE ANSWER. Under `fetch` or `ensure`
        # the operator asked what is so; closing the gap is exactly the authority they did
        # not grant, and `Unsolvable` would be wrong too — nothing here failed to find a
        # plan, there was no plan to find.
        #
        # STILL LOWERED, ONLY FOR THE PROBES. A goal about an OBSERVED attribute cannot be
        # judged until somebody asks, so the sub-goals are walked and every `_call` among
        # them is placed; the acting tiles inside are refused by this same branch one level
        # down. That is what lets "are they all reachable?" ping four machines and then
        # answer, instead of answering `unknown` and calling it a verdict.
        try:
            subs = _lower(goal, sel, scratch)
        except Exception:
            subs = []
        for s_ in subs:
            _achieve(s_, scratch, plan, trace, depth + 1, internal=internal, temps=temps,
                     asked=asked, asked_kinds=asked_kinds, acting=False)
        say(f"{_short(goal)} — does not hold ({why}), and a {'check'} does not close it")
        return

    # THE OPERATOR'S OWN LIBRARY IS TRIED FIRST, and this is the whole of "can it call what
    # it wrote". A stored procedure declares what it ACHIEVES, so covering a goal with one is
    # the same question as covering it with a primitive — does this make the goal true? — and
    # the answer is a structural match rather than a judgement about a sentence.
    #
    # BEFORE THE PRIMITIVE, DELIBERATELY. A snippet exists because somebody decided the
    # primitive sequence was worth naming: it carries the template, the credentials and the
    # ordering they settled on. Reaching for `create_vm` when `vm_disk_builder` is sitting
    # there would be the writer ignoring the operator's own decision and re-deriving a worse
    # version of it.
    #
    # NOTHING IS BLESSED BY BEING STORED. The body runs through the same visitor and the same
    # guarded executor; what is saved here is a plan, never a permission.
    from . import procedures as _procs
    # A PROCEDURE MAY NOT REACH FOR ITSELF. Authoring `vm_disk_builder` a second time found
    # the FIRST one sitting in the library, covered the goal with it, and produced a body of
    # `CALL vm_disk_builder()` — a procedure whose whole content is a call to itself. It was
    # caught by the validator refusing a call with no args, which is luck rather than a
    # guard: a self-call with arguments would have been kept and would recurse at run time.
    found = _procs.LIBRARY.covering(goal)
    if found and found.get("name") == without:
        found = None
    if found:
        tool, args = found["name"], dict(found["params"] or {})
        say(f"{_short(goal)} — not yet -> PROCEDURE {tool}")
        if (tool, args) not in plan:
            plan.append((tool, args))
            # THE SCRATCH IS ADVANCED BY THE PROCEDURE'S OWN BODY, so the world the rest of
            # the plan is written against reflects what the call will actually do. Skipping
            # this would leave later goals resolved against a world where the procedure never
            # ran — the same reason every placed tile is executed on the scratch.
            for st in (found["procedure"].get("body") or []):
                if st.get("op") == "call" and st.get("tool"):
                    scratch.execute(st["tool"], refs.resolve(st.get("args") or {}, args))
        return

    tile = effects.invert(goal, _kinds(scratch), internal=internal)
    if tile:
        tool, args = tile
        say(f"{_short(goal)} — not yet -> {tool}")
        # A CONDITION ON THE WORLD, NOT A GOAL TO PURSUE. `forbids` says what must not
        # already be true, and the writer's only legal responses are to proceed or to give
        # up — never to act. Treating it as a goal would let "x must not exist" be satisfied
        # by deleting x, destroying a machine to make room for one it was asked to create.
        for no in effects.forbids(tool, args, _kinds(scratch)):
            held, why = holds(no, {})
            if not held:
                raise Unsolvable(
                    f"{tool} cannot be placed here ({why}) — and nothing may act to "
                    f"change that: {goal}")
        # A PRECONDITION IS THE PROGRAM'S OWN BUSINESS. Nobody asked for it; it exists so
        # the thing that WAS asked for can happen. That provenance decides two things the
        # writer would otherwise have to guess: whether a machine gets a display, and
        # whether it is the program's to clean up afterwards.
        for need in effects.precondition(tool, args, _kinds(scratch)):
            _achieve(need, scratch, plan, trace, depth + 1, internal=True, temps=temps, asked=asked,
                     asked_kinds=asked_kinds, acting=acting, without=without)
        if (tool, args) not in plan:
            plan.append((tool, args))
            scratch.execute(tool, args)
            say(f"  place {tool}({', '.join(f'{k}={v}' for k, v in args.items())})")
            if internal and temps is not None:
                # CREATED BY THIS PROGRAM AND NAMED BY NOBODY — that is what makes a member
                # temporary, and the second half is the part I got wrong first.
                #
                # A precondition that creates the very member the goal is ABOUT is not
                # scaffolding, it IS the goal: "alpha is running" needs alpha to exist, and
                # the first version recorded alpha as temp and had the program DELETE THE
                # MACHINE THE OPERATOR ASKED FOR. Scaffolding is a member nobody mentioned,
                # brought into being only so the request could happen.
                #
                # AND A REQUEST NEED NOT NAME ANYTHING AT ALL, which is the third and last
                # form of the same mistake. "create 3 vms labelled red" names no machine, so
                # by the name test alone every one of them was scaffolding and rung 6's
                # program built its five machines and then deleted them. The goals RANGE OVER
                # `vm`, so a vm is what was asked for — see `_asked_kinds`.
                kind = effects._kind_of(tool, _kinds(scratch))
                spec = effects._K(_kinds(scratch)).get(kind) or {}
                name = args.get(spec.get("key"))
                if kind and name and tool == spec.get("create") \
                        and (kind, name) not in (asked or set()) \
                        and kind not in (asked_kinds or set()):
                    temps.append((kind, name))
        return

    subs = _lower(goal, sel, scratch)
    if not subs:
        say(f"{_short(goal)} — NO TILE, NO RULE")
        raise Unsolvable(f"nothing reaches: {goal}")
    say(f"{_short(goal)} — lowered into {len(subs)} sub-goal(s)")
    for s in subs:
        # LOWERING IS NOT A PRECONDITION. A sub-goal is part of what the operator asked for,
        # said more precisely — "every machine running" becomes one goal per machine, and
        # each is still theirs. Only `precondition` marks work nobody requested.
        _achieve(s, scratch, plan, trace, depth + 1, internal=internal, temps=temps, asked=asked,
                     asked_kinds=asked_kinds, acting=acting, without=without)

    ok, why = _holds(goal, holds, sel)
    if not ok:
        # THE LOWERING RAN AND THE GOAL STILL DOES NOT HOLD, which means the rule was wrong,
        # not the world. Checking is cheap and the alternative is a writer that reports
        # success because it did some work — the exact failure the ladder spent a day
        # measuring in the model.
        raise Unsolvable(f"lowering did not achieve it ({why}): {goal}")
    say(f"{_short(goal)} — now holds ({why})")


def kinds_of(goal: Dict[str, Any]) -> set:
    """Every kind a goal touches — the ones it SELECTS over and the one it MAKES.

    Both matter and for different reasons: selecting over a kind the planner cannot see
    resolves to an empty set, and MAKING one it cannot see means it never notices the thing
    already exists. `per vm make snapshot` is the case that needs both.
    """
    out = set()
    for shape in ("every", "observe", "per"):
        if shape in goal:
            out.add((goal[shape] or {}).get("kind"))
    if goal.get("select"):
        out.add(goal["select"].get("kind"))
    if goal.get("make"):
        out.add(goal["make"])
    return {k for k in out if k}


# ── FOUR BACKLOG ITEMS THIS MODULE ANSWERED BY EXISTING ────────────────────────────────
#
# Recorded here rather than left open, because a backlog item that a design has DELETED is
# worse than one nobody started: somebody eventually builds it.
#
# #56  "does one prompt sentence recover the 60 UNGROUNDED cells?"  ASKING A MODEL TO GROUND
#      ITS PROGRAM IS NOT A QUESTION ANY MORE. `as_program` writes the witness for every
#      goal it plans, as a list comprehension. The measurement that motivated the item —
#      60 of 78 programs vouching for nothing — was of a model authoring; nothing on the
#      main line authors.
#
# #29  "the router emits DANGLING sub-goals"  THE ROUTER IS THE FALLBACK NOW. It runs only
#      after `Unsolvable`, inside a granted tree session. The main line lowers STRUCTURE
#      (`_lower`), and a lowering rule cannot emit a fragment: every sub-goal it produces is
#      a predicate over named members, checked by `_holds` before the parent is called done.
#
# #50  "p_self authoring — declare the line's shape before emitting it, then compare"  THE
#      WRITER DOES NOT EMIT LINES, it places tiles, and a tile's shape is the manifest's.
#      The idea survives for STAGED LOWERING, where a model does emit — and `emit_leaf`
#      already validates each statement in the scope it will occupy, which is the same
#      declare-then-check at the only place it applies.
#
# #52  "capability ledger — predict prerequisites from the prompt, reveal them per line"
#      PREREQUISITES ARE NOT PREDICTED, THEY ARE DERIVED. `effects.precondition` computes
#      exactly what must be true before a tool runs, from the manifest, with no prompt and
#      no model. The blinders half dissolved when context became O(1) in engines.

def groundable(goal: Dict[str, Any]) -> bool:
    """Can this goal have a closing witness at all?

    NO, FOR EXACTLY TWO SHAPES, and the reason is the language rather than the writer: a
    `_call` and an `observe` are things DONE, not things that become true, and Medusa has no
    predicate for "has been asked". So they are not ungrounded — they are UNGROUNDABLE, and
    a verdict that counts them as failures is measuring the absence of a predicate nobody
    should add.

    SSOT with `as_program`'s skip, which is what this was extracted from — the two had to
    agree, and agreeing by coincidence is how twins start.
    """
    return not ("_call" in goal or "observe" in goal)


def _as_statement(tool: str, args: Dict[str, Any], kinds) -> Dict[str, Any]:
    """One placed tile as a Medusa statement — `new` for a creation, `call` for the rest.

    THE LANGUAGE HAS A CREATION OPERATOR AND THE WRITER WAS NOT USING IT. Every tile came
    out as a bare tool call, so a program that made a machine read `create_vm(name: vm1)`
    where Medusa says `STORE vm1 = NEW vm(...)`. That is not a formatting preference: `new`
    is the operator the runtime mints names through, the one the book keeper's registry
    injection hangs off, and the one that BINDS what it made so later statements can refer
    to it rather than repeating a string literal.

    Everything else stays a `call`, which is what it is: a tool being invoked.
    """
    spec = None
    kind = effects._kind_of(tool, kinds)
    if kind:
        spec = effects._K(kinds).get(kind) or {}
    # WITHDRAWN, AND THE REASON IS WORTH MORE THAN THE CHANGE WAS.
    #
    # This emitted `new` for creations, which is right in principle — the language HAS a
    # creation operator, `new` is what the runtime mints names through, and a program of raw
    # tool calls is not really written in its own language. It produced:
    #
    #     STORE http://x = NEW page(url: http://x);
    #
    # `http://x` IS NOT A LEGAL VARIABLE NAME. Fed back in, or written by hand, that program
    # fails. The var was the member's KEY VALUE, which is a name for a thing in the world and
    # not an identifier in a program, and those are different alphabets.
    #
    # EVERY SUITE STAYED GREEN, and that is the finding: the writer builds IR DIRECTLY, so it
    # is never held to the constraints the MODEL is held to. The schema constrains `var` to
    # something pronounceable and the writer never meets the schema, so it can emit programs
    # a user could not have written and the system cannot re-read. `test_writer_output_is_
    # writable` now closes that, and doing `new` properly means binding real identifiers AND
    # referring to them with the sigil — a whole change, not half of one.
    # A CREATION IS A `new`. `CALL create_vm(…)` GETS NO CHECK AT ALL — `new` is the one op
    # where the harness itself invents something (it mints the name, chooses the creator,
    # supplies the key), so the visitor re-reads the world after it and files a failure if
    # what was asked for is not there. Emitting a raw call throws that check away and then
    # needs an ENSURE bolted on to replace it, which is exactly the third line the operator
    # struck: *"it should be like 2 lines"*, *"ensure is unneeded here"*.
    #
    # THE WITHDRAWAL THIS REVERSES was about the VARIABLE NAME and nothing else: `var` was
    # set to the member's key value, so it emitted `STORE http://x = NEW page(url: http://x)`.
    # A name for a thing in the world is not an identifier in a program. The key still
    # travels in `args`, where the visitor's "THE AUTHOR'S OWN NAME WINS" rule reads it.
    kind = effects._kind_of(tool, kinds)
    spec = effects._K(kinds).get(kind) or {}
    key = spec.get("key")
    if kind and key and tool == spec.get("create"):
        member = args.get(key)
        var = str(member) if _PRONOUNCEABLE.match(str(member or "")) else f"{kind}1"
        return {"op": "new", "var": var, "kind": kind, "args": dict(args)}
    return {"op": "call", "tool": tool, "args": args}


def as_program(plan: List[Call], goals: List[Dict[str, Any]], world=None,
               temps: List = None, witness: bool = True) -> Dict[str, Any]:
    """The plan as a grounded Medusa program.

    Grounding is not requested from anyone: each goal becomes the program's own closing
    witness. Measured 2026-07-31 — ASKING a model for it left 60 of 78 programs vouching for
    nothing, and DEMANDING it in the prompt made the ladder worse while breaking the decoder.
    Here it is a list comprehension.

    `witness=False` IS THE BOTTOM RUNG OF THE LADDER, and only that. A FETCH answers with
    DATA — "how many are there, list them" — and `intent._PERMITS` does not license it an
    `ensure`, because a verdict is the rung above. So a fetch program asks, publishes what
    it found, and passes judgement on nothing. Every other intent grounds, and the flag is
    named for what it withholds rather than for the intent, because this module has no
    business knowing the ladder's words.
    """
    # THE SAME SCRATCH `cover` USES, AND FOR THE SAME REASON. This deep-copied instead, which
    # is the exact bug `_scratch_of` was written for — a deep copy of a world whose hands
    # reach OUTSIDE ITSELF copies a reference to the real executor, so WRITING THE PROGRAM
    # PERFORMS IT. Fixed in `cover` on 2026-08-01 and missed here; found the first time a
    # QEMU mount met a real library, by an executor that refused to act.
    scratch = _scratch_of(world) if world is not None else None
    if scratch is not None:
        for tool, args in plan:
            scratch.execute(tool, args)
    select = _seams_of(scratch)[0] if scratch is not None else (lambda s, scope=None: [])
    kinds_now = _kinds(scratch)
    body = [_as_statement(t, a, kinds_now) for t, a in plan]

    # THE DELIVERABLE — ask the thing the member was CREATED IN ORDER TO ANSWER.
    #
    # "Search the web for the diameter of the earth" produced a program that started a
    # machine, started a browser, ran a search, asserted that a search EXISTED, and tore it
    # all down. Every call could have succeeded and the operator would still have had no
    # answer, because nothing ever asked what came back. The manifest named the observer —
    # `search.observed.answer.by = camoufox_read` — and no code path ever called it, so
    # there was no finding, so there was nothing to PUBLISH, so the reporter had nothing to
    # say. Four silent layers downstream of one missing question.
    #
    # A KIND DECLARES WHICH FACT IS ITS POINT, because only the kind knows. A machine exists
    # to run things and its reachability is incidental; a SEARCH exists for its answer and is
    # worthless without one. That is not something the writer can infer from the shape of a
    # manifest row.
    #
    # AND THE WITNESS IS `unknown = 0`, which is the clause `observe.py` already argues for:
    # an observed attribute is three-valued, and asserting `answer != 'no'` would be
    # satisfied by a search nobody asked. `unknown = 0` says every member was actually
    # ASKED — the one form that a program which probed nothing cannot pass.
    deliverables: List[str] = []
    for g in goals:
        for holder in ("select", "count", "every"):
            sel = g.get(holder) if isinstance(g.get(holder), dict) else None
            if sel is None and holder == "count":
                sel = g.get("select") if isinstance(g.get("select"), dict) else None
            if not sel:
                continue
            kind = sel.get("kind")
            spec = effects._K(kinds_now).get(kind) or {}
            fact = spec.get("deliverable")
            probe = effects.probe_for(kind, fact) if fact else None
            key = spec.get("key")
            if not (fact and probe and key):
                continue
            # UNLESS THE CREATOR ALREADY BRINGS IT BACK. `camoufox search --json` prints the
            # result — the answer arrives with the act, and a separate read would be a second
            # question to a browser that has already spoken. A kind says so with
            # `create_yields`; anything not listed there still has to be asked.
            if fact not in (spec.get("create_yields") or ()):
                for member in select(sel) or ():
                    body.append({"op": "call", "tool": probe, "args": {key: member}})
            # SCOPED TO THE MEMBERS THIS GOAL IS ABOUT, not to every member of the kind.
            # An unscoped `COUNT(SELECT search WHERE answer='unknown') = 0` asks the world to
            # enumerate a kind it does not track, and production's select answered with the
            # nine machines — so the witness failed at `count is 9, wanted == 0` over a set it
            # was never about. Carrying the goal's own filters keeps the question the same
            # size as the goal.
            body.append({"op": "ensure", "predicate": {
                "shape": "count", "eq": 0,
                "select": {**{k: v for k, v in sel.items() if k != "kind"},
                           "kind": kind, fact: _observe.unknown()}}})
            spec_obs = (spec.get("observed") or {}).get(fact) or {}
            template = spec_obs.get("fact") or (fact + "({member})")
            for member in select(sel) or ():
                deliverables.append(template.replace("{" + key + "}", str(member))
                                            .replace("{member}", str(member)))
            break

    # GROUNDED THROUGH `_ground`, because a goal and a WITNESS are not the same object. An
    # `every` component is not a predicate the language can evaluate; its witness is a count
    # over the same set, and the number is resolved against the world AS THE PROGRAM LEAVES
    # IT — not as it was before, or the witness would assert the wrong total.
    # WHICH MEMBERS THIS PROGRAM CREATED WITH `new`. A `new` VOUCHES FOR ITSELF — the visitor
    # re-reads the world after it and files a failure if what was asked for is not there — so
    # a goal whose whole content is creations is already checked, statement by statement, and
    # a closing ENSURE over it asserts a second time what the body just proved.
    #
    # THE OPERATOR STRUCK IT ON SIGHT: *"it should be like 2 lines"*, *"ensure is unneeded
    # here"*. The third line only ever existed because the first was a raw `CALL`, which has
    # no check to give.
    minted = {st.get("var") for st in body if st.get("op") == "new"}
    made = {(st.get("kind"), (st.get("args") or {}).get(
        (effects._K(kinds_now).get(st.get("kind")) or {}).get("key")))
        for st in body if st.get("op") == "new"}
    for g in goals:
        if not witness or not groundable(g):
            continue
        if _self_vouched(g, body, kinds_now, select):
            continue
        w = _ground(g, select)
        body += [{"op": "ensure", "predicate": p} for p in (w if isinstance(w, list) else [w])]

    # EVERY PROGRAM SAYS SOMETHING WHEN IT IS DONE — the results if it has any, `done` if it
    # does not. A program that finishes silently leaves the operator reading a ledger to work
    # out whether they got what they asked for, and PUBLISH is the channel built so they do
    # not have to: the engine submits, the orchestrator keeps it or carries it up.
    #
    # THE FACT, NEVER THE VALUE. `PUBLISH answer(the diameter of the earth)` names what to
    # submit; the engine attaches what it actually observed. A program that could state its
    # own answer could state one it never obtained.
    #
    # BEFORE TEARDOWN, AFTER THE WITNESS — the same place and the same reason as the closing
    # ENSUREs. Publishing after the scaffolding is gone would report on a world the program
    # had already dismantled.
    # PUBLISH THE THING, NOT THE WORD. A program that made something has an answer to give —
    # the binding it just created — and `done` is what a program says when it has nothing.
    # The operator's form: `PUBLISH(vm)`.
    said = [{"op": "publish", "fact": f} for f in dict.fromkeys(deliverables)]
    if not said and minted:
        said = [{"op": "publish", "fact": v} for v in dict.fromkeys(
            st.get("var") for st in body if st.get("op") == "new")]
    body += said or [{"op": "publish", "fact": "done"}]

    # TEARDOWN LAST, AFTER THE WITNESS. A machine this program made so something else could
    # happen is the program's to take down — the operator never asked for it and will never
    # look for it. A member that already existed is left alone, always: the difference is
    # PROVENANCE, and it is the only line that can be drawn here without guessing intent.
    #
    # AFTER the closing ENSUREs, never before. The witness asserts that what was asked for
    # actually happened, and tearing the scaffolding down first would leave it asserting
    # against a world the program had just dismantled.
    #
    # IN REVERSE ORDER OF CREATION, because a later temp may sit on an earlier one — a
    # browser on a machine — and removing the host first orphans the guest.
    kinds = _kinds(scratch)
    for kind, name in reversed(list(temps or ())):
        spec = effects._K(kinds).get(kind) or {}
        deleter, key = spec.get("delete"), spec.get("key")
        if deleter and key and name:
            # WHAT MUST BE TRUE BEFORE IT CAN GO. `delete_vm` refuses a running machine, so a
            # teardown that emitted the bare deleter emitted a call that could never succeed —
            # and the machine the program minted for its own use survived every run, exactly
            # as if there had been no teardown at all. `Stop the VM before deleting.`, on the
            # lab, on a machine three statements after the program had launched it.
            #
            # DERIVED THROUGH `invert`, not written out here, which is the same route any
            # other attribute change takes. The manifest says a removal needs the member
            # stopped; the writer works out which tool makes that true. A kind that declares
            # nothing emits nothing, so this costs the other kinds exactly zero.
            for attr, value in (spec.get("delete_requires") or {}).items():
                got = effects.invert({"shape": "count", "eq": 1,
                                      "select": {"kind": kind, key: name, attr: value}},
                                     kinds, internal=True)
                if got:
                    tool, args = got
                    body.append({"op": "call", "tool": tool, "args": args, "cleanup": True})
            # MARKED AS CLEANUP, which is what lets it run when the program does not finish.
            # A program that fails at statement three abandons its tail, and the tail is where
            # the teardown lives — so every failed run leaked the machine it had minted, and
            # the operator who never asked for that machine is the one left with it. The
            # runtime treats these as a `finally`: whatever else happened, what the program
            # made for its own use goes away.
            #
            # THE MARK IS IN THE PROGRAM, not a rule in the runtime, because "is this
            # statement scaffolding?" is a fact only the writer knows — it is the thing that
            # decided the member was the program's own rather than the operator's.
            body.append({"op": "call", "tool": deleter, "args": {key: name},
                         "cleanup": True})
    return {"body": body}
