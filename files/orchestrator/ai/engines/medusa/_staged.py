"""_staged.py — staged lowering, and what a node opens INTO.

The fallback for a goal the deterministic writer REFUSES: the goal is opened until every
leaf is one operator, each leaf is emitted against one branch, and the assembled artifact is
GRADED BEFORE ANYTHING RUNS. Reached only after `Unsolvable`, only inside a granted tree
session, so its cost falls on whoever holds the budget.

Beside it live the two questions about a node's SHAPE — what it would open into (`_open`)
and what its split assumed (`_premise_of`) — because both are answered from the writer's own
lowering rules and neither touches the world.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ...planner import ghost_writer as _gw
from ...planner import tree_keeper as _keeper
from ...planner.ir import lower as _lower
from ...planner.ir import observe as _observe
from ...planner.ir import config as _config
from ...planner.ir import consent as _consent
from ...planner.ir import render as _render
from ...planner.ir import run as _run
from ...planner.ir import effects as _effects
from ...planner.ir import validate as _validate
from ._shared import _MAX_OPENINGS, _MAX_WAITS, _findings_of, _prose_of


class _StagedMixin:
    def _staged(self, components, session) -> Optional[Dict[str, Any]]:
        """STAGED LOWERING — one operator per leaf, fused upward, graded before it runs.

        RETURNS A PLAN, NEVER A RESULT. An earlier version of this ran the program it built,
        from inside `_plan` — the function whose whole contract is "everything up to the
        first side effect". So a staged program ACTED WITHOUT A STEP EVER BEING OFFERED, and
        the one invariant the in-session exists to keep was broken by the mechanism added to
        serve it. Building and running are separate here for the same reason they are
        separate everywhere else in this file.

        Returns None when it does not apply, which keeps the default path exactly as it was:
        no author, no tree grant, or a goal with no prose to open all fall through to the
        ordinary promotion request.

        THE GRADE IS THE POINT AND IT HAPPENS BEFORE EXECUTION. `review` is deterministic and
        reads the assembled artifact — grounded, repeated statements, clauses unaccounted
        for. That is the program regime's whole advantage over the tree regime, kept here:
        an inert artifact can be refused for free, and this one is refused rather than run
        when it cannot vouch for itself.
        """
        if self._author is None or self._route is None:
            return None
        if getattr(session, "regime", "translation") != "tree":
            return None
        goal = _prose_of(components)
        if not goal:
            # NOTHING TO OPEN. The goals arrived as structure with no sentence behind them,
            # and inventing prose to decompose would be authoring the request rather than
            # serving it.
            return None
        # `log` IS A CALLABLE IN THAT MODULE, not a list. Passing a list would have raised
        # on the first thing worth logging, which is the moment you most want the log.
        def say(line):
            session.record(f"staged: {line}")

        try:
            tools = _effects.tools_of(self.manifest) or None
            root = _lower.decompose(goal, self._route, log=say)
            tree = _lower.lower_tree(root, self._author, known=set(self._world.names()),
                                     log=say, route=self._route, known_tools=tools)
        except (_lower.DecompositionError, _lower.LoweringError, _lower.FusionError) as e:
            return {"ok": False, "calls": [], "program": None,
                    "why": f"staged lowering could not build it either: {e}"}

        if not _lower.review(tree)["grounded"]:
            # ASK FOR A CLOSING VERDICT BEFORE REFUSING. `ground` exists for exactly this —
            # a tree that acts and asserts nothing gets one more call, for the statement that
            # says what must hold at the end. Refusing without asking would throw away a
            # program the author could have finished, and the writer's own rule is that
            # every goal it plans closes with a witness.
            tree = _lower.ground(tree, self._author, goal, known=set(self._world.names()),
                                 log=say, known_tools=tools)
        program = _lower.assemble(tree)
        report = _lower.review(tree)
        session.record(f"staged: {report['statements']} statement(s), "
                       f"grounded={report['grounded']}, repeated={len(report['repeated'])}")
        if not report["grounded"]:
            # AN ARTIFACT THAT VOUCHES FOR NOTHING IS REFUSED WHILE IT IS STILL INERT. The
            # writer grounds every goal it plans; a model-authored program that does not is
            # the exact thing #54 made a scored outcome, and it costs nothing to refuse now
            # and everything to discover afterwards.
            return {"ok": False, "calls": [], "program": program,
                    "why": "staged lowering produced a program that vouches for nothing"}
        # AND DECORATIVE GROUNDING IS NOT GROUNDING. `review` asks whether an assertion
        # EXISTS, never whether one could FAIL. Measured on the first staged program ever
        # built here: it closed with `ACHIEVE COUNT(dish) >= 1` over a world that ALREADY
        # HELD ONE — true before the program ran, and so a witness to nothing about it.
        #
        # `consent.vacuous` does not catch this and SHOULD NOT: it is deliberately narrow,
        # and it refused a relevance test on the grounds that a false accusation of vacuity
        # is worse than a missed one. That reasoning stands. But this is not a heuristic —
        # THE ENGINE HAS THE WORLD AS IT IS BEFORE THE PROGRAM RUNS, which nothing reading
        # the artifact alone can have, so it can COMPUTE the answer and decline nothing.
        #
        # It does not fire on the case that check was worried about: a program creating five
        # machines and closing with `count == 5` starts from a world where the count is
        # zero, so the assertion does not already hold and nothing is flagged.
        _, holds = _gw._seams_of(self._world)
        witnesses = [st for st in program.get("body") or []
                     if st.get("op") in ("ensure", "achieve") and st.get("predicate")]
        already = []
        for st in witnesses:
            try:
                ok_now, _why = holds(st["predicate"], {})
            except Exception:
                ok_now = False          # a predicate the world cannot answer is not vacuous
            if ok_now:
                already.append(_gw._short(st["predicate"]))
        if witnesses and len(already) == len(witnesses):
            return {"ok": False, "calls": [], "program": program,
                    "why": f"staged lowering grounded itself only with assertion(s) that "
                           f"ALREADY HOLD before it runs, so nothing it does is witnessed: "
                           f"{already[:2]}"}
        problems = _validate(program, known_names=self._world.names(),
                             known_tools=_effects.tools_of(self.manifest) or None)[1]
        if problems:
            return {"ok": False, "calls": [], "program": program,
                    "why": f"staged lowering produced an invalid program: {problems[:1]}"}
        return {"ok": True, "plan": [], "program": program}

    def _premise_of(self, goals: List[Dict[str, Any]],
                    members: int) -> Optional[Dict[str, Any]]:
        """What a split assumed: the set it was split over still has this many members.

        ROOT POISONING IS EXACTLY THIS ASSUMPTION BREAKING. "Every stopped machine" resolves
        to three, three children act on those three, a fourth machine stops, and every child
        is locally correct while the parent goal is false. Nothing about a child says so;
        the parent's own count does.

        None WHEN THERE IS NOTHING TO ASSUME. A node holding several goals was split one per
        goal — no set was resolved, so no membership was relied on — and a node whose goal
        names no selector has nothing to count. Inventing a premise for those would produce a
        check that passes however the world behaves, which is the decorative grounding this
        codebase refuses.
        """
        if len(goals) != 1:
            return None
        goal = goals[0]
        sel = next((goal[k] for k in ("every", "observe", "per", "select")
                    if isinstance(goal.get(k), dict)), None)
        if not sel or not sel.get("kind"):
            return None
        return {"shape": "count", "select": dict(sel), "eq": members}

    def _open(self, goals: List[Dict[str, Any]]) -> Optional[List]:
        """One node into finer ones, or None when the node is already atomic.

        TWO WAYS A NODE IS FINER THAN ITS PARENT and they are tried in that order: a node
        holding SEVERAL goals splits into one node per goal, and a node holding ONE goal is
        lowered by the writer's own rules — the same `_lower` that plans, so a decomposition
        never disagrees with a plan.
        """
        if len(goals) > 1:
            return [([g], "one goal") for g in goals]
        select, _ = _gw._seams_of(self._world)
        try:
            subs = _gw._lower(goals[0], select, self._world)
        except Exception:
            # A LOWERING THAT RAISES IS NOT A DECOMPOSITION. It is answered as "atomic",
            # because the alternative is reporting a crash as a tree structure.
            return None
        return [([s], "sub-goal") for s in subs] if subs else None

