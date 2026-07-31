"""tile_solver.py — cover a goal with tiles. NO MODEL, anywhere in this file.

Step 2 of the operator's design (#61): if the AI's only job is to translate a request into a
set of components, then everything after that must be a deterministic algorithm. This is
that algorithm, at its smallest — backward chaining over tiles whose postconditions are
declared in `ir/effects.py`.

WHAT IT PROVES, AND WHAT IT DOES NOT. It answers one question: given the goal as predicates,
can code alone produce the program a human would write, in the right order? It says nothing
about whether the model can produce those predicates — that is the translation half, and it
is measured separately. Keeping the two apart is the entire point of the architecture, since
today a wrong program could mean the goal was misread OR the writing was fumbled, and
nothing distinguishes them.

THE ALGORITHM, in three lines:
    a goal that already HOLDS contributes nothing        (this is `already_satisfied`)
    otherwise invert it to the tile that makes it true
    and place that tile's PRECONDITIONS first, recursively

Order is not a rule anyone wrote down. It falls out of the third line: `add_vm_to_network`
needs `lab` to exist, so the tile creating `lab` is placed before it. The prompt currently
spends 77 characters asking a model to remember this.

NO SEARCH AND NO COST MODEL YET. Inversion is unique for these shapes, so there is nothing
to choose between; when tiles overlap — several ways to reach one state — this is where the
reward-cost engine plugs in, and the honest note is that it is not needed to pass rung 3.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from orchestrator.ai.planner.ir import effects


class Unsolvable(Exception):
    """No tile makes a goal true — the writer's honest failure.

    It is DELIBERATELY not a fallback. A writer that improvises when it cannot find a tile
    is a writer that can produce a program nothing vouches for, and the entire reason to
    move generation out of the model is that this component does not guess.
    """


def cover(goals: List[Dict[str, Any]],
          holds: Callable,
          depth: int = 0) -> List[Tuple[str, Dict[str, Any]]]:
    """The tool calls that make every goal hold, in an order that can actually run.

    `holds` is the same predicate evaluator the language uses — the seam, not a private
    copy. A solver that judged the world through its own reader could satisfy itself while
    the program failed against the real one, which is the stale-twin defect this codebase
    has now found three times.
    """
    if depth > 8:
        raise Unsolvable("chain too deep — a precondition probably depends on itself")
    plan: List[Tuple[str, Dict[str, Any]]] = []
    for goal in goals:
        ok, _ = holds(goal, {})
        if ok:
            # ALREADY SATISFIED. Not an optimisation — the cheapest correct program for a
            # goal that already holds is the empty one, and only a postcondition can say so.
            continue
        tile = effects.invert(goal)
        if tile is None:
            raise Unsolvable(f"no tile makes this true: {goal}")
        tool, args = tile
        # PRECONDITIONS FIRST, and recursively — this is the only thing that orders the
        # program. `holds` is re-consulted inside the recursion, so a precondition already
        # met costs nothing and one met by an earlier tile in THIS plan is not re-emitted.
        for need in effects.precondition(tool, args):
            for call in cover([need], holds, depth + 1):
                if call not in plan:
                    plan.append(call)
        if (tool, args) not in plan:
            plan.append((tool, args))
    return plan


def as_program(plan: List[Tuple[str, Dict[str, Any]]],
               goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The plan as a Medusa program, GROUNDED — every goal becomes a closing ENSURE.

    The grounding is not requested from anyone. It is the goal itself, restated as the
    program's own witness, which is what makes the program checkable by the same rule that
    produced it. Measured 2026-07-31: asking a model for this yielded 60 of 78 programs with
    no witness at all, and demanding it in the prompt made the score WORSE. Here it costs a
    list comprehension.
    """
    body: List[Dict[str, Any]] = [{"op": "call", "tool": t, "args": a} for t, a in plan]
    body += [{"op": "ensure", "predicate": g} for g in goals]
    return {"body": body}
