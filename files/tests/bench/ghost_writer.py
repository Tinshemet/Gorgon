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

from orchestrator.ai.planner.ir import effects

from .seams import seams

Call = Tuple[str, Dict[str, Any]]


class Unsolvable(Exception):
    """No tile and no lowering rule reaches a goal — the writer's honest failure.

    DELIBERATELY WITHOUT A FALLBACK. A writer that improvises when it cannot find a tile can
    produce a program nothing vouches for, and the entire reason to move generation out of
    the model is that this component does not guess. `Unsolvable` is also the signal the
    operator's design wants: when the writer cannot build it, the request goes back for
    decomposition rather than forward as something plausible.
    """


def _short(p: Dict[str, Any]) -> str:
    sel = p.get("select") or {}
    body = " ".join(f"{k}={v}" for k, v in sel.items() if k != "kind")
    tail = f"== {p['eq']}" if "eq" in p else f">= {p.get('min', '?')}"
    return f"{p.get('shape')}:{sel.get('kind', '?')}[{body}] {tail}"


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
    shape = goal.get("shape")
    sel = dict(goal.get("select") or {})
    kind = sel.get("kind")
    spec = (effects.config.KINDS or {}).get(kind) or {}
    key = spec.get("key")
    if not key:
        return []

    # REACH — a finding, never an inference. Decision 6 and A5 both say the same thing:
    # unverified is not done, so every member must be ASKED before reach can hold. The
    # manifest already records who asks (`observed.alive.by`), so this is read, not declared.
    if shape == "reach":
        probe = effects.probe_for(kind, "alive")
        if not probe:
            return []
        return [{"_call": (probe, {key: m})} for m in select(sel)]

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
        good = effects.complement(kind, attr, bad)
        if good is None:
            return []
        return [{"shape": "count", "select": {"kind": kind, key: m, attr: good}, "eq": 1}
                for m in members]

    if want is None or want <= len(members):
        return []

    # NOT ENOUGH MEMBERS MATCH. Two ways to close the gap, and the order matters: convert
    # members that already exist before creating new ones, because creating a machine to
    # satisfy "five carry the fleet label" when five machines already exist is the wrong
    # program — it satisfies the count and misreads the request.
    deficit = want - len(members)
    subs: List[Dict[str, Any]] = []
    if filters:
        matched = set(members)
        for m in [x for x in select({"kind": kind}) if x not in matched][:deficit]:
            subs.append({"shape": "count",
                         "select": {"kind": kind, key: m, **filters}, "eq": 1})
        deficit -= len(subs)
    for name in _fresh_names(kind, deficit, set(select({"kind": kind}))):
        subs.append({"shape": "count", "select": {"kind": kind, key: name}, "eq": 1})
        # A created member still has to satisfy the filters the goal asked for.
        if filters:
            subs.append({"shape": "count",
                         "select": {"kind": kind, key: name, **filters}, "eq": 1})
    return subs


def cover(goals: List[Dict[str, Any]], world, trace: List[str] = None) -> List[Call]:
    """The calls that make every goal hold, in an order that runs."""
    scratch = copy.deepcopy(world)
    plan: List[Call] = []
    for goal in goals:
        _achieve(goal, scratch, plan, trace, 0)
    return plan


def _achieve(goal, scratch, plan, trace, depth):
    if depth > 12:
        raise Unsolvable("lowering too deep — a goal probably depends on itself")
    say = (lambda m: trace.append("  " * depth + m)) if trace is not None else lambda m: None
    sel, holds = seams(scratch)

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

    ok, why = holds(goal, {})
    if ok:
        say(f"{_short(goal)} — ALREADY HOLDS ({why})")
        return

    tile = effects.invert(goal)
    if tile:
        tool, args = tile
        say(f"{_short(goal)} — not yet -> {tool}")
        for need in effects.precondition(tool, args):
            _achieve(need, scratch, plan, trace, depth + 1)
        if (tool, args) not in plan:
            plan.append((tool, args))
            scratch.execute(tool, args)
            say(f"  place {tool}({', '.join(f'{k}={v}' for k, v in args.items())})")
        return

    subs = _lower(goal, sel, scratch)
    if not subs:
        say(f"{_short(goal)} — NO TILE, NO RULE")
        raise Unsolvable(f"nothing reaches: {goal}")
    say(f"{_short(goal)} — lowered into {len(subs)} sub-goal(s)")
    for s in subs:
        _achieve(s, scratch, plan, trace, depth + 1)

    ok, why = holds(goal, {})
    if not ok:
        # THE LOWERING RAN AND THE GOAL STILL DOES NOT HOLD, which means the rule was wrong,
        # not the world. Checking is cheap and the alternative is a writer that reports
        # success because it did some work — the exact failure the ladder spent a day
        # measuring in the model.
        raise Unsolvable(f"lowering did not achieve it ({why}): {goal}")
    say(f"{_short(goal)} — now holds ({why})")


def as_program(plan: List[Call], goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The plan as a grounded Medusa program.

    Grounding is not requested from anyone: each goal becomes the program's own closing
    witness. Measured 2026-07-31 — ASKING a model for it left 60 of 78 programs vouching for
    nothing, and DEMANDING it in the prompt made the ladder worse while breaking the decoder.
    Here it is a list comprehension.
    """
    body = [{"op": "call", "tool": t, "args": a} for t, a in plan]
    body += [{"op": "ensure", "predicate": g} for g in goals if "_call" not in g]
    return {"body": body}
