"""executor.py — THE EXECUTOR AS AN ENGINE. One call, one answer, close.

THE OPERATOR'S SPLIT, MADE CONCRETE: *"the executor provides the box, and medusa translates
the prompt into action either on the host or inside the vms."* Two load-bearing host engines,
and until now only one of them existed — every request, however small, went to the thing that
writes programs.

IT IS THE TOOL REGIME, WHICH WAS DESCRIBED AND NEVER BUILT. `session.py` has said since the
day it was written:

    FETCH    tell me           TOOL         one call, one answer, close
    ENSURE   confirm it is so  TRANSLATION  components -> program -> run -> close
    ACHIEVE  make it so        TREE         autonomous, corrects, cost accrues

The floor had no engine, so `rank("tool") == 0` was a number nothing could occupy. That is
the shape of a ladder whose bottom rung is a diagram.

WHAT MAKES IT THE FLOOR IS WHAT IT REFUSES TO DO. It does not plan, order, or decompose. A
goal that inverts to exactly ONE tool call whose preconditions already hold is run; anything
else is handed back with `promote: translation`, which is the engine saying "this needs a
program" rather than half-writing one. GRAVITY POINTS DOWN: most requests should end here,
and the ones that cannot should leave quickly and cheaply.

IT OFFERS ONE STEP PER CALL, AND THE FIRST VERSION DID NOT — that was a safety hole, found
by pointing `plan --dry` at the real lab with an executor that refuses to act. `drive` falls
back to `engine.run()` for an engine with no in-session, so this engine ACTED WITH NO VERDICT
EVER ASKED FOR. `delete_vm alpha` is exactly one call and irreversible.

"One call, one answer, no exchange" meant no BACK-AND-FORTH — no decomposing, no re-planning,
no promotion. It never meant acting unasked. So the floor still asks, once per call, and a
dry run can preview it and a policy can refuse it, while nothing here plans anything.

WHY IT DOES NOT BUILD ITS OWN EXECUTOR. The same reason `LabWorld` does not: a program's
statements and a single tool call reach the world through ONE door — legal filter, commit
gate, contract tier, watchdog, killswitch. A second door here would be a second door.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from planner.ir import config as _config
from planner.ir import consent as _consent
from planner.ir import effects as _effects
from .base import Engine


_NEEDS_A_PROGRAM = ("this needs a program, not a call — some goal here is not one "
                    "already-reachable operation")


class ExecutorEngine(Engine):
    """The box: one declared tool call at a time, against the real lab."""

    name = "executor"
    description = ("run ONE machine operation directly — create, launch, stop, label, "
                   "attach or delete a single thing, with no plan around it")
    # FETCH AND NOTHING ABOVE IT. An engine that declared `achieve` would be claiming it can
    # pursue a goal, and pursuing is exactly what it refuses to do. `may_promote` reads this,
    # so declaring more would let a session be granted a regime this cannot serve.
    intents = ("fetch",)

    def __init__(self, library, execute, findings=None):
        self._library = library
        self._execute = execute
        self._findings = findings

    @property
    def manifest(self) -> Dict[str, Any]:
        return _config.KINDS or {}

    def world(self):
        # THE SAME WORLD THE LAB MOUNT USES, for one reason: two engines over one lab that
        # disagreed about what is in it would be two labs. Imported here rather than at
        # module load so mounting this does not drag the planner in.
        from .qemu import LabWorld
        return LabWorld(self._library, self._execute, self._findings)

    @staticmethod
    def _procedure_covers(goal) -> bool:
        """Does a stored procedure claim this exact goal?

        FAILS OPEN, DELIBERATELY. If the library cannot be read, the executor serves the goal
        as it always did — a broken store must not stop the lab from running one call.
        """
        try:
            from planner.procedures import LIBRARY
            return LIBRARY.covering(goal) is not None
        except Exception:
            return False

    def _red_line(self, components, kinds, holds) -> Optional[str]:
        """The first RED-LINED tool this request would call, or None — asked before any of it.

        THE OPERATOR'S RULING IS ABOUT THE WHOLE, 2026-08-02: *"not be ran at all, not just
        the tools but also the entire program."* A request this engine serves is several
        goals and one call each, so the equivalent of refusing the program is refusing
        BEFORE THE FIRST CALL rather than at the goal that names the banned tool — otherwise
        two of five goals have already changed the lab when the third is refused.

        IT SWEEPS THE TILES AGAINST THE WORLD AS IT IS NOW, which is a real approximation:
        a tile is chosen partly by what already holds, so a later goal could in principle
        resolve differently once an earlier call has run. That is why the check is here AND
        at the call — this one gives the all-or-nothing property in the ordinary case, and
        the one at the call is the backstop that cannot be dodged. Same function, one
        standard; two gates only matter when they can DISAGREE.
        """
        legal = self._legal()
        if not callable(legal):
            return None
        for goal in components or ():
            try:
                tile = self._one_call(goal, kinds, holds)
            except Exception:
                # A GOAL THIS ENGINE CANNOT EVEN TILE IS NOT ITS WORK — `steps` will promote
                # it. Refusing here on an exception would turn a routing decision into a
                # security verdict.
                continue
            # THE ARGS WERE ALWAYS HERE AND THIS LINE READ PAST THEM. `_one_call` returns
            # (tool, args) and the red line asked about the tool alone, which is exactly
            # the gap K5 names: the law could ban `delete_vm` and could not say WHICH
            # machines it may touch. `consent.ask` puts the question to whatever arity the
            # injected filter was written with.
            tool, args = tile or (None, None)
            if tool and _consent.ask(legal, tool, args):
                return tool
        return None

    @staticmethod
    def _refused(tool: str) -> Dict[str, Any]:
        return {"ok": False, "failed": "forbidden", "forbidden": [tool],
                "calls": [], "findings": [],
                "why": f"{tool} is a red line for this agent, so nothing here runs. "
                       f"It takes the operator's password to lift"}

    @staticmethod
    def _lifted(banned: str, session) -> bool:
        """Has the operator lifted this red line, in person?

        THE SAME SEAM AND THE SAME READER AS THE PROGRAM REGIME — `consent.permitted` off
        `session.permit`. A second way to lift a ban, worded differently here, is how the two
        regimes come to disagree about what the operator actually authorised.
        """
        from planner.ir import consent as _consent
        return _consent.permitted([banned], getattr(session, "permit", None))

    def steps(self, components: List[Dict[str, Any]], session=None):
        """ONE STEP PER CALL. Not a tree — there is no decomposing here and no second round.

        The step declares its cost and what it would destroy, exactly as the planner's does,
        because the operator's protection cannot depend on WHICH engine happened to serve
        the request.
        """
        from .insession import RUN, STOP, Publish, Step

        world = self.world()
        kinds = self.manifest
        _select, holds = world.seams
        calls, findings = [], []

        # THE RED LINES FIRST, before a step is even proposed — a forbidden tool is not
        # something to ask the operator about, and a decider that never sees it cannot be
        # talked into it.
        legal = self._legal()
        banned = self._red_line(components, kinds, holds)
        if banned and not self._lifted(banned, session):
            return self._refused(banned)

        for goal in components or ():
            tile = self._one_call(goal, kinds, holds)
            # A STORED PROCEDURE OUTRANKS THE PRIMITIVE, and this is the only place that can
            # say so. Gravity points down — try the cheapest regime first — and that rule was
            # right until the library existed. A procedure covering this exact goal is the
            # OPERATOR'S OWN DECLARED ANSWER for it: they wrote it, signed it, and it does
            # things the one call cannot. Serving the primitive instead is not cheaper, it is
            # WRONG, and silently so.
            #
            # MEASURED 2026-08-02: `crawl_golden` cloned a 12G windows template, labelled the
            # result and checked the templates list. The executor served `create_vm` instead
            # and produced a BLANK LINUX MACHINE, closing DONE. The procedure was never
            # consulted, because the request never reached the engine that consults it.
            #
            # IT IS A PROMOTION, NOT A REFUSAL. The goal goes to the regime that can write a
            # program, which is where `covering()` is asked — so this engine stays ignorant of
            # what a procedure IS, and only has to know that one exists.
            if tile is None or self._procedure_covers(goal):
                return {"ok": False, "promote": "translation", "calls": calls,
                        "findings": findings, "why": _NEEDS_A_PROGRAM}
            tool, args = tile
            if not tool:
                continue                      # already true — zero calls is a real answer
            # THE BACKSTOP. `_red_line` swept the tiles before anything ran; this is the same
            # question asked of the tile that is ACTUALLY about to run, so a tool that only
            # became the answer after an earlier call cannot slip through.
            if callable(legal) and legal(tool) and not self._lifted(tool, session):
                return {**self._refused(tool), "calls": calls, "findings": findings}
            destroys = [(tool, args)] if tool in _effects.deleters(kinds) else []
            # AND WHETHER IT CHANGES ANYTHING AT ALL, which is a wider question than whether it
            # destroys something and the one the intent ladder asks. This engine declares
            # `intents = ("fetch",)` and, until the in-session could read this, ran `create_vm`
            # and `delete_vm` on request — the FLOOR, which `floor_first` routes to before
            # anything else. Declaring the ladder and enforcing it are different things.
            acts = [(tool, args)] if tool in _effects.actors(kinds) else []
            verdict = yield Step(RUN, {"tool": tool, "args": args}, f"one call: {tool}",
                                 cost=1, divisible=False, destroys=destroys, acts=acts)
            if verdict is None or verdict.action == STOP:
                return {"ok": False, "refused": True, "calls": calls, "findings": findings,
                        "why": verdict.why if verdict is not None else "no verdict given"}
            result = self._execute(tool, args)
            calls.append((tool, args))
            if not (result or {}).get("success", True):
                return {"ok": False, "calls": calls, "findings": findings,
                        "why": f"{tool} failed: {(result or {}).get('error')}"}
            findings.append({"fact": f"did:{tool}", "value": args})
            yield Publish(f"did:{tool}", args)
        return {"ok": True, "calls": calls, "findings": findings, "why": None}

    def run(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        """Every goal that is already ONE call, run. Anything else, handed back.

        FOR AN UNMOUNTED CALLER. Mounted, `steps()` is what the in-session drives, and it
        asks before each call; this path exists for code holding the engine directly and
        does not pretend to a verdict nobody gave.

        NO ORDERING, WHICH IS THE HARD PART TO LEAVE OUT. Two goals that each invert to a
        single call may still need one to happen before the other, and deciding that is
        planning. So a goal whose preconditions are not ALREADY MET is not this engine's
        work, even though it could name the tool — naming a tool and knowing when to call it
        are different jobs, and the second one is what Medusa is for.
        """
        world = self.world()
        kinds = self.manifest
        select, holds = world.seams
        calls, findings = [], []

        # THE SAME SWEEP THE MOUNTED PATH DOES. An unmounted caller holding the engine
        # directly gets no in-session and no decider, so it needs this MORE, not less.
        banned = self._red_line(components, kinds, holds)
        if banned and not self._lifted(banned, session):
            return self._refused(banned)

        for goal in components or ():
            tile = self._one_call(goal, kinds, holds)
            if tile is None:
                return {"ok": False, "promote": "translation", "calls": calls,
                        "findings": findings, "why": _NEEDS_A_PROGRAM}
            tool, args = tile
            if not tool:
                continue
            result = self._execute(tool, args)
            calls.append((tool, args))
            if not (result or {}).get("success", True):
                # A FAILED CALL IS REPORTED AS ITSELF. It is not a reason to escalate: the
                # tool ran and the world said no, which a program would not have changed.
                return {"ok": False, "calls": calls, "findings": findings,
                        "why": f"{tool} failed: {(result or {}).get('error')}"}
            findings.append({"fact": f"did:{tool}", "value": args})

        return {"ok": True, "calls": calls, "findings": findings, "why": None}

    @staticmethod
    def _one_call(goal: Dict[str, Any], kinds, holds) -> Optional[tuple]:
        """The single call that closes this goal, or None if it takes more than one.

        THREE WAYS TO BE MORE THAN ONE CALL and all of them mean the same thing here — go
        ask Medusa: nothing inverts the goal, something must be forbidden first, or something
        must be true first that is not.
        """
        try:
            ok_now, _ = holds(goal, {})
        except Exception:
            ok_now = False
        if ok_now:
            # ALREADY TRUE IS ZERO CALLS, and that is a legitimate answer at the floor —
            # the same reading `already_satisfied` gives one level up.
            return ("", {})
        tile = _effects.invert(goal, kinds)
        if not tile:
            return None
        tool, args = tile
        for no in _effects.forbids(tool, args, kinds):
            held, _ = holds(no, {})
            if not held:
                return None
        for need in _effects.precondition(tool, args, kinds):
            held, _ = holds(need, {})
            if not held:
                return None
        return tool, args
