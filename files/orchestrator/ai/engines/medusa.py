"""medusa.py — the MEDUSA engine: the ghost writer plus the runtime.

Medusa is bash for Gorgon. The executor is only for machines; this is the engine for the
SYSTEM ITSELF — the way to write code for Gorgon inside Gorgon. Meaningless outside it, and
inside it the way things are done. Which is why every other engine must be Medusa-compatible:
they all speak this one's vocabulary or the orchestrator cannot plan across them.

MODEL-FREE, and that is a verified fact rather than an aspiration: `planner/ir/` is fifteen
modules with ZERO model calls. Handed components, this engine plans, grounds, corrects and
runs with nothing probabilistic in the loop. The model sits OUTSIDE it — turning English into
components on the way in, and findings into English on the way out.

WHAT IT ASKS FOR RATHER THAN TAKES. When the writer returns `Unsolvable`, or `derive()`
cannot compute a gap, this engine sets `promote` on its result. It does not open a tree
session itself: a tree runs until resolved or abandoned with cost accruing, and whoever owns
the budget must be able to say no.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..planner import ghost_writer as _gw
from ..planner.ir import config as _config
from ..planner.ir import consent as _consent
from ..planner.ir import render as _render
from ..planner.ir import run as _run
from ..planner.ir import effects as _effects
from ..planner.ir import validate as _validate
from .base import Engine


class MedusaEngine(Engine):
    name = "medusa"
    description = ("write and run a Gorgon program — plan several steps against the lab, "
                   "in order, and check the result")
    intents = ("fetch", "ensure", "achieve")

    def __init__(self, world, execute=None):
        """`world` carries `kinds`, `seams` and `execute` — the mount contract, nothing else.

        `execute` may be supplied separately when the world reads state but something else
        is authorised to change it. That split is the whole reason a program's statements are
        not a trusted region: they reach the world through the caller's guarded executor, the
        same gauntlet a single tool call meets.
        """
        self._world = world
        self._execute = execute or world.execute
        # A world whose kinds are NOT the default manifest needs the override below. Asking
        # once, here, keeps the default target — the actual Gorgon lab — on the untouched
        # path it has always used.
        self._foreign = (getattr(world, "kinds", None) or None) not in (None, _config.KINDS)

    @property
    def manifest(self) -> Dict[str, Any]:
        return getattr(self._world, "kinds", {}) or {}

    def world(self):
        return self._world

    def claims(self, request: str) -> bool:
        """Medusa claims anything about the kinds it knows — it is the general engine.

        Over-claiming on purpose: this is the fallback when nothing more specific fits, and
        an engine never tried is worse than one tried and refused. `Unsolvable` is a cheap no.
        """
        return bool(self.manifest)

    def run(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        # THE WHOLE OPERATION RUNS UNDER THIS ENGINE'S MANIFEST, not just the validate call.
        # `run()` re-validates internally — correctly, since a program reaching the world is
        # the last place to check it — so scoping only the outer validate produced a program
        # that passed inspection and was then refused as "invalid" by a validator reading a
        # different manifest. One scope, the whole engine operation, or the halves disagree.
        with _config.use_kinds(self.manifest if self._foreign else None):
            return self._run_scoped(components, session)

    def _run_scoped(self, components: List[Dict[str, Any]], session=None) -> Dict[str, Any]:
        world = self._world
        try:
            plan = _gw.cover(components, world)
        except _gw.Unsolvable as e:
            # THE PROMOTION REQUEST. Built as an honest refusal — no tile, no rule, will not
            # improvise — and under the engine architecture that is exactly what asking for
            # a regime looks like. The orchestrator decides; this engine only reports that it
            # has run out of things it can compute.
            return {"ok": False, "promote": "tree", "why": str(e),
                    "calls": [], "program": None}

        program = _gw.as_program(plan, components, world)
        if not program["body"]:
            # NOTHING OWED. The correct answer to a finished world is the empty program, and
            # `validate` rejects an empty body — right for something a model wrote, wrong for
            # a writer that looked and found nothing to do.
            return {"ok": True, "calls": [], "program": program, "rendered": "",
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
            return {"ok": False, "why": f"writer produced an invalid program: {problems[:1]}",
                    "calls": [], "program": program}

        select, holds = _gw._seams_of(world)
        result = _run(program, self._execute, select=select, holds=holds,
                      known_names=world.names(),
                      known_tools=_effects.tools_of(self.manifest) or None,
                      consent=True, intent="achieve")
        survey = _consent.survey(program)
        return {"ok": bool(result.get("ok")),
                "calls": result.get("calls") or [],
                "program": program,
                "rendered": _render(program),
                "grounded": survey["grounded"],
                "vacuous": survey["vacuous"],
                "why": result.get("why") or result.get("failed")}
