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

from planner import ghost_writer as _gw
import os as _os

from planner import dry_run as _dry
from planner import reading_gate as _gate
from planner import refine as _refine
from planner import tree_keeper as _keeper
from planner.ir import lower as _lower
from planner.ir import observe as _observe
from planner.ir import config as _config
from planner.ir import consent as _consent
from planner.ir import render as _render
from planner.ir import run as _run
from planner.ir import effects as _effects
from planner.ir import validate as _validate
from ._shared import _MAX_OPENINGS, _MAX_WAITS, _findings_of, _prose_of


def _assistant(request: str, plan, world=None) -> List[str]:
    """The CONTEXT ASSISTANT, asked about a PROGRAM instead of a single tool call.

    ## IT LIVES HERE AND NOT IN `planner`, AND THAT IS THE LAYERING SPEAKING

    `planner` is layer 0 — THE LANGUAGE — and the context assistant is chat-layer
    domain knowledge: trigger words, high-stakes field names, a tool catalogue. The
    language must not reach up for that. `engines` is layer 2 and already carries
    declared upward edges (`channel.py` for the model, `rig.py` for the library), so the
    call belongs on this side and `reading_gate.judge` just takes the warnings.

    ## THE DETERMINISTIC CHECK THE ENGINE PATH NEVER GOT

    `orchestrator/ai/chat/context_assistant.check_context` has run in production on the chat
    path for a long time — no model call, vocabulary derived from the tool catalogue — and
    the engine path never called it once. The gate above ported its GRADING; this ports the
    assistant itself.

    ## ONLY TWO OF ITS FOUR CHECKS TRAVEL, and the other two would do harm

        contradictory intent   PORTED — "create dev-box and delete dev-box" is a request
                               nobody should serve, whichever half is meant
        high-stakes flags      PORTED — `delete_vm.delete_disks`, `stop_vm.force`. Set
                               without the operator saying so, on a program they have not
                               read yet
        hallucinated field     NOT PORTED. It fires when a required argument's value is
                               absent from the prompt — and THE WRITER MINTS NAMES. "create
                               5 vms" produces vm1..vm5, none of which the operator ever
                               said, so this would accuse every request that does not name
                               its machines. `extract.invented` already asks the same
                               question one layer up, where the model's own names live.
        tool mismatch          NOT PORTED. It second-guesses which tool answers a request,
                               and here the WRITER picks tools deterministically from the
                               manifest — a mismatch would be the writer disagreeing with a
                               word list, which is not evidence about the operator's meaning.

    NEVER RAISES. A world or a plan it cannot read yields no warnings, which is the same
    posture every other reader here takes: with nothing established, say nothing.
    """
    try:
        from orchestrator.ai.chat.context_assistant import check_context
    except Exception:
        return []
    known = None
    try:
        rows = getattr(world, "vms", None) or getattr(world, "_vms", None)
        if isinstance(rows, dict):
            known = set(rows)
    except Exception:
        known = None
    out, seen = [], set()
    for call in plan or ():
        tool = call[0] if isinstance(call, (list, tuple)) and call else getattr(call, "tool", None)
        args = (call[1] if isinstance(call, (list, tuple)) and len(call) > 1
                else getattr(call, "args", {})) or {}
        try:
            hint = check_context(request, str(tool), dict(args), known_names=known)
        except Exception:
            continue
        # ONLY THE TWO THAT TRAVEL. Selected by their message text because `check_context`
        # returns one string and the chat gate reads it the same way — see its own
        # `if "never mentioned it" in hint`.
        if not hint or not ("high-stakes" in hint or "contradictory" in hint):
            continue
        if hint not in seen:
            seen.add(hint)
            out.append(hint)
    return out


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
        from planner.ir import intent as _intent
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
        # THE REHEARSAL, AND IT COSTS NOTHING. `cover` already executes every placed tile on
        # a scratch copy — that is how it knows what is already satisfied — so the predicted
        # end state is a by-product of planning that was thrown away until 2026-08-06. Asking
        # for it back is what lets the reading be GRADED before anything runs, which is the
        # property the program regime was chosen over the tree FOR:
        #
        #     "its artifact is complete and INERT before anything runs — so it can be graded
        #      at every granularity at once, corrected, and resubmitted, at zero risk."
        before = _dry.snapshot(world)
        predicted: List = []
        try:
            plan = _gw.cover(components, world, temps=temps, acting=corrects,
                             without=getattr(session, 'authoring', None),
                             predicted=predicted)
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
        from planner.ir import intent as _intent
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

        # ── THE READING GATE ────────────────────────────────────────────────────────────
        #
        # DID WE UNDERSTAND THE REQUEST? Everything above this line asks whether the PROGRAM
        # is well formed; nothing asked whether it answers the question that was put. That is
        # what a `DONE_BUT_FALSE` is, and until now production had no check for it at all —
        # the word appears in this codebase only in comments and in the bench, because the
        # bench catches it with a hand-written checker per rung and production has no oracle.
        #
        # THE COMPARISON IS AGAINST THE REQUEST, never against the goals. Checking the
        # predicted world against the goals passes BY CONSTRUCTION: a false success already
        # agrees with itself, which is what makes it invisible. `clause_ledger` enumerates
        # demands from the ENGLISH, so reconciling a world diff against those is the one
        # piece of evidence available that is not derived from the thing being judged.
        #
        # AND THE GATE IS THE MEASUREMENT. The ladder needs an oracle per rung and can only
        # ever measure fourteen requests; this fires or does not on every real one, and what
        # it catches is the metric. That argument was already in `chat/config.json` — the
        # chat path ships because it is gated, this one did not because it was not.
        #
        # OFF WITH `GORGON_NO_GATE=1`, for measuring it against itself and nothing else. It
        # is ON by default because a mechanism nobody calls is this codebase's dominant
        # defect, and four were added in one day before this line was written.
        verdict = None
        if _os.environ.get("GORGON_NO_GATE") != "1":
            asked_for = str(getattr(session, "request", "") or "")
            # ONE BUILDER — `refine.judged`. This assembled a `Rehearsal` by hand because
            # `cover` has already run and must not run twice, and within the hour it had
            # drifted from `refine.rehearse`: `probed` was added there and not here, so every
            # PROBING program read as "does work, changes nothing" and the gate refused
            # rung 13. A thing with several constructors has no invariants.
            rehearsal = _refine.judged(
                components, plan, program, before,
                _dry.snapshot(predicted[0]) if predicted else before,
                predicted[0] if predicted else world, asked_for,
                asked_before=_dry.observations(world))
            # THE CONTEXT ASSISTANT, over the whole program. Deterministic, no model call,
            # and the engine path had never called it — see `reading_gate.assistant` for
            # which of its four checks travel and why the other two would do harm.
            verdict = _gate.judge(asked_for, rehearsal,
                                  warnings=_assistant(asked_for, plan, world))
            if session is not None:
                session.record(f"reading gate: {verdict.outcome}"
                               + (f" ({verdict.caught})" if verdict.caught else ""),
                               filed_by="reading_gate", caught_by="operator",
                               level="warn" if verdict.outcome != _gate.PROCEED else "info")
            if verdict.outcome != _gate.PROCEED:
                # IT IS A QUESTION AND NOT A CRASH. The rehearsal found something it cannot
                # settle alone, so the run stops with the question rather than acting on a
                # reading nobody confirmed — and `promote` is deliberately absent, because
                # this is not a gap another engine could close.
                return {"ok": False, "asked": verdict.question or verdict.detail,
                        "caught": verdict.caught, "calls": [], "program": program,
                        "why": verdict.question or verdict.detail}

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
        from planner.ir import derive as _derive
        from planner.ir import execute as _exec

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

