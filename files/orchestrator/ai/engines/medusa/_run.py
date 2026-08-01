"""_run.py — plan, correct, and the two questions the intent ladder decides.

    _plan       everything up to the first side effect
    _corrects   may this session CLOSE a gap, or only report one?
    _correct    ACHIEVE's FIRST engine — derive(), and the doorway to its second

Split from the in-session because these answer "what would we do" where `_tree` answers
"who said we may". The division is the same one the architecture draws everywhere else: the
engine decomposes and plans; the orchestrator rules on it.
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


class _PlanMixin:
    def run(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        # THE WHOLE OPERATION RUNS UNDER THIS ENGINE'S MANIFEST, not just the validate call.
        # `run()` re-validates internally — correctly, since a program reaching the world is
        # the last place to check it — so scoping only the outer validate produced a program
        # that passed inspection and was then refused as "invalid" by a validator reading a
        # different manifest. One scope, the whole engine operation, or the halves disagree.
        with _config.use_kinds(self.manifest if self._foreign else None):
            return self._run_scoped(components, session)

    def _run_scoped(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        planned = self._plan(components, session)
        if planned.get("promote") or planned.get("done") or not planned.get("ok", True):
            return {k: v for k, v in planned.items() if k not in ("plan", "done", "ok")} \
                if planned.get("promote") else planned.get("result", planned)
        return self._execute_plan(planned, components, session)

    @staticmethod
    def _corrects(session) -> bool:
        """May this session CLOSE a gap, or only report one?

        ONE READING OF THE LADDER, ASKED TWICE — once by `_plan`, to decide what to write,
        and once by `_execute_plan`, to decide whether a false assertion is a failure or an
        answer. Written here so the two cannot drift: they are the same question about the
        same session, and a version where the writer planned a check while the reader
        expected a correction would report every verdict as a broken run.
        """
        from ...planner.ir import intent as _intent
        want = getattr(session, "intent", None)
        return want is None or _intent.permits(want)

    def _plan(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        """Everything up to the first side effect. Returns a plan, or the reason there
        cannot be one.

        SPLIT FROM EXECUTION so the in-session can offer a program for a verdict BEFORE any
        of it happens. A budget holder shown the bill afterwards is not holding a budget, and
        an operator asked to consent after the fact is being informed rather than asked.
        """
        world = self._world
        # A KIND THE WORLD CANNOT SEE IS NOT A KIND WITH NOTHING IN IT.
        #
        # Decision 6 applied to planning: unprobed is not healthy, and unseeded is not empty.
        # A world that cannot enumerate a kind will answer every question about it with an
        # empty set, and the writer's next move is to CREATE what is missing — so a goal
        # about restore points would plan to make every one of them again. The lab mount
        # declares `unseeded` for exactly this; a world that declares nothing is unaffected.
        blind = set(getattr(world, "unseeded", ()) or ())
        if blind:
            touched = set()
            for g in components:
                touched |= _gw.kinds_of(g)
            hidden = sorted(touched & blind)
            if hidden:
                return {"ok": False, "promote": "tree",
                        "why": f"nothing here can enumerate {', '.join(hidden)}, and an "
                               f"empty answer would be read as 'there are none'",
                        "calls": [], "program": None}
        # THE COLLECTOR FOR EVERY MEMBER THIS PLAN MINTS AS A PRECONDITION, and without it the
        # writer's teardown could never fire. `cover` fills the list, `as_program` turns it
        # into the closing deletes — and this engine called both and passed neither, so the
        # list was built inside `cover` and dropped on the floor.
        #
        # MEASURED ON THE LAB, NOT REASONED: the search request derived `create_vm(vm1)` and
        # `launch_vm(vm1, display: none)` correctly, ran them, and emitted no `delete_vm`. The
        # machine is still there. The whole provenance rule — a machine the operator never
        # named is the program's own and goes away after the witness — was implemented, tested
        # in the writer, and unreachable from production.
        # WHAT THE OPERATOR GRANTED DECIDES WHAT IS WRITTEN, not only what is allowed to run.
        #
        # `cover` is the ACHIEVE engine — it closes whatever gap it finds — and it was called
        # for every intent. So an ENSURE request became a program that CREATES machines and
        # was then refused for exceeding its authority: the operator asked whether something
        # was so and was told they were not allowed to ask. Measured, on "are there nine
        # machines?" against a lab holding four: REFUSED, `a ensure may not change the lab`.
        #
        # A check is not a correction with the acting removed afterwards; it is a different
        # program, and it has to be written as one. The gate stays where it is — two readings
        # of the same rule, one shaping the plan and one refusing what escapes it.
        want = getattr(session, "intent", None)
        corrects = self._corrects(session)
        temps: List = []
        try:
            plan = _gw.cover(components, world, temps=temps, acting=corrects,
                             without=getattr(session, 'authoring', None))
        except _gw.Unsolvable as e:
            # THE PROMOTION REQUEST. Built as an honest refusal — no tile, no rule, will not
            # improvise — and under the engine architecture that is exactly what asking for
            # a regime looks like. The orchestrator decides; this engine only reports that it
            # has run out of things it can compute.
            return {"ok": False, "promote": "tree", "why": str(e),
                    "calls": [], "program": None}

        # A FETCH ANSWERS WITH DATA AND NEVER WITH A VERDICT — `intent._PERMITS` does not
        # license it an `ensure`, because judging is the rung above reading. So the bottom
        # rung writes probes and a PUBLISH, and the findings carry what was seen.
        from ...planner.ir import intent as _intent
        program = _gw.as_program(plan, components, world, temps=temps,
                                 witness=want != _intent.FETCH)
        if not program["body"]:
            # NOTHING OWED. The correct answer to a finished world is the empty program, and
            # `validate` rejects an empty body — right for something a model wrote, wrong for
            # a writer that looked and found nothing to do.
            return {"done": True, "ok": True, "calls": [], "program": program,
                    "rendered": "", "findings": [],
                    "result": {"ok": True, "calls": [], "program": program, "rendered": "",
                               "findings": [],
                               "why": "already satisfied — nothing to do"},
                    "why": "already satisfied — nothing to do"}

        # THE ENGINE'S OWN TOOLS, not Gorgon's. `validate` checks statements against known
        # tools, and the default is the VM executor's registry — correct for the executor
        # engine and wrong for every other, which is the coupling that only shows up once a
        # second engine exists.
        # ITS OWN TOOLS TOO — `validate` checks statements against known tools and the
        # default is the VM executor's registry, which is right for the executor engine and
        # wrong for every other. A coupling that only appears once a second engine exists.
        ok, problems = _validate(program, known_names=world.names(),
                                 known_tools=_effects.tools_of(self.manifest) or None)
        if not ok:
            # THE WRITER'S OWN FAULT, and it must never read as the model's. Nothing
            # probabilistic produced this program.
            bad = {"ok": False,
                   "why": f"writer produced an invalid program: {problems[:1]}",
                   "calls": [], "program": program}
            return {**bad, "done": True, "result": bad}

        return {"ok": True, "plan": plan, "program": program}

    # HOW MANY TIMES A GOAL MAY BE CORRECTED BEFORE THE GAP IS CALLED UNCLOSABLE. Three,
    # which is `Session.rounds_left`'s number for the same reason: `cover`'s own fixpoint
    # gives up after four passes that will not settle, and a corrector that out-loops the
    # writer is chasing a gap the writer already declined.
    _MAX_CORRECTIONS = 3

    def _correct(self, program, result, select, holds, execute, session):
        """ACHIEVE'S FIRST ENGINE, and until now it was not connected to anything.

        `derive()` computes the difference between what a goal asked for and what the world
        holds — "six exist, three wanted" closes in one line — and the model provably cannot:
        it oscillated 6->5->7->5 with the state and the objection in hand. It has been the
        deterministic half of ACHIEVE since it was written, `ir/__init__` exports it, and NO
        PRODUCTION MODULE CALLED IT. Only the two bench probes did, so the correction loop the
        ladder measures was a property of the bench rather than of the system.

        ONLY FOR `unachieved`. `unsatisfied` means a ground check was false — the program
        assumed something about the world that was not true — and computing a diff there would
        paper over the wrong assumption instead of rethinking it. That is the model's to
        answer, which is why the two words exist.

        THE FIX AND THEN THE TAIL. A failed predicate returns from `run` and abandons every
        statement after it, so replaying only the correction leaves that work undone while the
        predicate now reports the goal as held — a green verdict over an unfinished program.
        `follow_up` appends what never ran, resolved against the scope the aborted run held.

        WHERE DERIVE RETURNS None THE GAP IS NOT ARITHMETIC, and that is the doorway to the
        second engine: the result keeps `promote: tree`, which the orchestrator may grant or
        refuse. This function never opens one — a tree accrues cost, and the thing asking for
        more is never the thing that should approve it.
        """
        from ...planner.ir import derive as _derive
        from ...planner.ir import execute as _exec

        # EVERY CALL, ACROSS EVERY ROUND. `run` reports the calls IT made, so replacing the
        # result with the correction's would drop the ones the first pass made — the operator
        # is shown three creations where four happened, and the cost the budget already
        # charged for vanishes from the record. Measured the first time the corrector fired.
        made = list(result.get("calls") or [])
        rounds = 0
        while (result.get("failed") == "unachieved"
               and rounds < self._MAX_CORRECTIONS):
            rounds += 1
            goal = result.get("predicate")
            fix = _derive(goal, select, result.get("scope"),
                          getattr(session, "intent", None)) if goal else None
            if fix is None:
                # NOT ARITHMETIC. Said plainly and handed upward rather than retried — the
                # ninth `return None` in `derive.py` is a refusal, not a failure, and asking
                # it again gets the same answer.
                result = {**result, "calls": made, "promote": "tree",
                          "why": f"the gap is not arithmetic: {result.get('why') or ''}"}
                break
            if fix == []:
                break                       # already satisfied; nothing to close
            if session is not None:
                session.record(f"derived a correction ({len(fix)} statement(s)) for "
                               f"{_gw._short(goal)}", filed_by=self.name,
                               caught_by="orchestrator", executed="derive()")
            result = _run(_exec.follow_up(result, fix), execute, select=select, holds=holds,
                          known_names=self._world.names(),
                          known_tools=_effects.tools_of(self.manifest) or None,
                          # THE CORRECTION IS THE SAME PROGRAM CONTINUING, so it meets the
                          # same AUTHORITY. Deriving a fix that reached above the rung the
                          # operator granted would be the escalation the ladder exists to
                          # prevent, arriving through the one door nobody was watching.
                          #
                          # CONSENT IS NOT RE-ASKED, and that is not the same relaxation.
                          # The question `consent.py` asks is about a PROGRAM — "this changes
                          # the world and nothing checks it" — and this body is a fragment of
                          # one that already passed it. A fix plus an abandoned tail carries
                          # no witness by construction, so asking would refuse every
                          # correction under an unattended run and prompt on every round
                          # under an attended one.
                          consent=True, intent=getattr(session, "intent", None),
                          acting_tools=_effects.actors(self.manifest))
            made += list(result.get("calls") or [])
            result = {**result, "calls": made}
        return result

