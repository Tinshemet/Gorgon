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

IT HAS NO `steps()`, DELIBERATELY. `insession.drive` already says an engine that offers no
in-session simply runs — "one call, one answer, no exchange. The protocol has to accommodate
the floor or it stops being the floor." This is the engine that proves that clause was not
decoration.

WHY IT DOES NOT BUILD ITS OWN EXECUTOR. The same reason `LabWorld` does not: a program's
statements and a single tool call reach the world through ONE door — legal filter, commit
gate, contract tier, watchdog, killswitch. A second door here would be a second door.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..planner.ir import config as _config
from ..planner.ir import effects as _effects
from .base import Engine


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

    def run(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        """Every goal that is already ONE call, run. Anything else, handed back.

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

        for goal in components or ():
            tile = self._one_call(goal, kinds, holds)
            if tile is None:
                return {"ok": False, "promote": "translation", "calls": calls,
                        "findings": findings,
                        "why": "this needs a program, not a call — some goal here is not "
                               "one already-reachable operation"}
            tool, args = tile
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
