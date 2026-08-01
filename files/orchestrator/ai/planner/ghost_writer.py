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
from typing import Any, Dict, List, Tuple

from .ir import effects


def _kinds(world):
    """The manifest this world is described by, or the default target's."""
    return getattr(world, "kinds", None)


def _seams_of(world):
    """The world's own adapter. A world that does not name one is the VM sim, whose
    adapter lives in the bench — production worlds always name theirs, which is what
    stops this module importing a test fixture."""
    got = getattr(world, "seams", None)
    if got is not None:
        return got
    from tests.bench.seams import seams as _bench
    return _bench(world)

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
          temps: List = None) -> List[Call]:
    """The calls that make every goal hold, in an order that runs.

    `temps` collects `(kind, name)` for every member this plan CREATES as a precondition —
    something nobody asked for, made so the request could happen. `as_program` takes them
    down at the end.
    """
    scratch = _scratch_of(world)
    asked = _named_in(goals, _kinds(scratch))
    plan: List[Call] = []
    for _round in range(4):
        before = len(plan)
        for goal in goals:
            _achieve(goal, scratch, plan, trace, 0, temps=temps, asked=asked)
        if len(plan) == before:
            return plan
        if trace is not None:
            trace.append(f"— goals interacted; re-covering (round {_round + 2})")
    # Four passes without settling means a goal is undoing another's work, which no amount
    # of further looping fixes and which the writer must not paper over by stopping quietly.
    raise Unsolvable("goals do not settle — they may be pulling against each other")


def _achieve(goal, scratch, plan, trace, depth, internal=False, temps=None, asked=None):
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
            _achieve(s_, scratch, plan, trace, depth + 1, internal=internal, temps=temps, asked=asked)
        return

    ok, why = _holds(goal, holds, sel)
    if ok:
        say(f"{_short(goal)} — ALREADY HOLDS ({why})")
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
            _achieve(need, scratch, plan, trace, depth + 1, internal=True, temps=temps, asked=asked)
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
                kind = effects._kind_of(tool, _kinds(scratch))
                spec = effects._K(_kinds(scratch)).get(kind) or {}
                name = args.get(spec.get("key"))
                if kind and name and tool == spec.get("create") \
                        and (kind, name) not in (asked or set()):
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
        _achieve(s, scratch, plan, trace, depth + 1, internal=internal, temps=temps, asked=asked)

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
    return {"op": "call", "tool": tool, "args": args}


def as_program(plan: List[Call], goals: List[Dict[str, Any]], world=None,
               temps: List = None) -> Dict[str, Any]:
    """The plan as a grounded Medusa program.

    Grounding is not requested from anyone: each goal becomes the program's own closing
    witness. Measured 2026-07-31 — ASKING a model for it left 60 of 78 programs vouching for
    nothing, and DEMANDING it in the prompt made the ladder worse while breaking the decoder.
    Here it is a list comprehension.
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
    # GROUNDED THROUGH `_ground`, because a goal and a WITNESS are not the same object. An
    # `every` component is not a predicate the language can evaluate; its witness is a count
    # over the same set, and the number is resolved against the world AS THE PROGRAM LEAVES
    # IT — not as it was before, or the witness would assert the wrong total.
    for g in goals:
        if not groundable(g):
            continue
        w = _ground(g, select)
        body += [{"op": "ensure", "predicate": p} for p in (w if isinstance(w, list) else [w])]

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
            body.append({"op": "call", "tool": deleter, "args": {key: name}})
    return {"body": body}
