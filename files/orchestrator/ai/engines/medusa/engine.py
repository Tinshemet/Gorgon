"""engine.py — the MEDUSA engine: the mount contract, and who it is.

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
from ..base import Engine


from ._execute import _ExecuteMixin
from ._run import _PlanMixin
from ._staged import _StagedMixin
from ._shared import _findings_of, _prose_of  # noqa: F401  (re-exported)
from ._tree import _TreeMixin


class MedusaEngine(_TreeMixin, _StagedMixin, _PlanMixin, _ExecuteMixin,
                   Engine):
    name = "medusa"
    description = ("write and run a Gorgon program — plan several steps against the lab, "
                   "in order, and check the result")
    intents = ("fetch", "ensure", "achieve")

    def __init__(self, world, execute=None, packages=(), author=None, route=None):
        """`world` carries `kinds`, `seams` and `execute` — the mount contract, nothing else.

        `execute` may be supplied separately when the world reads state but something else
        is authorised to change it. That split is the whole reason a program's statements are
        not a trusted region: they reach the world through the caller's guarded executor, the
        same gauntlet a single tool call meets.

        `author` and `route` ARE THE STAGED-LOWERING SEAM, and they are optional because the
        engine must work without a model at all — 13/13 rungs with neither.

            author(prompt, schema) -> dict      one leaf, one operator's schema
            route(goal) -> {atomic, op, steps}  is this one statement, or several?

        WHERE THEY ARE USED IS THE WHOLE POINT. NOT as a first choice: the ghost writer is
        deterministic and covers every rung, and handing a model the job it already does
        would be trading a measured 13/13 for a measured 4/13. They are what happens when
        the writer says `Unsolvable` — no tile, no rule, will not improvise. That refusal is
        already the promotion signal, and staged lowering is what a promotion BUYS: the goal
        is opened until every leaf is one operator, each leaf is emitted against ONE branch
        (the regime where grammar enforcement was observed to hold), and the assembled
        artifact is GRADED BEFORE ANYTHING RUNS.
        """
        self._world = world
        self._author = author
        self._route = route
        self._execute = execute or world.execute
        # PACKAGES ARE LOADED, NOT MOUNTED. Their kinds join this engine's manifest so a
        # program can plan over them, and their tools become callable — but EXECUTION STAYS
        # HERE. A package that held its own executor would be a second door into the world,
        # and the point of the engine layer is that there is one.
        self.packages = tuple(packages)
        self._execute = self._with_packages(self._execute)
        # A world whose kinds are NOT the default manifest needs the override below. Asking
        # once, here, keeps the default target — the actual Gorgon lab — on the untouched
        # path it has always used.
        # DOES THIS ENGINE HAVE A MANIFEST OF ITS OWN? Asked of `manifest` rather than of the
        # world, because a package is the other way an engine's kinds can differ and the world
        # knows nothing about packages. The lab's world declares the DEFAULT kinds — literally
        # the same object — so this read False with Camoufox loaded, the engine never entered
        # its own scope, and the writer planned a search request against a manifest with no
        # search in it.
        self._foreign = (self.manifest or None) not in (None, _config.KINDS)

    def _with_packages(self, execute):
        """One executor that also knows what a loaded package's tools mean.

        THE SECOND HALF OF LOADING, and it was missing. A package's kinds joined the manifest,
        the writer planned the entire chain in the right order — create the machine, launch it
        headless, start the browser on it, run the search — and then the world answered
        `Unknown tool: camoufox_launch`, because the tool registry is the executor's and a
        package is not an executor. Measured on the lab, with a real machine created and
        launched to host a browser that could never start.

        DISPATCH BY OWNERSHIP, decided once at construction. A tool belongs to exactly one
        package — `merge` already refuses two packages defining the same kind — so the map is
        built here rather than searched per call, and a tool nobody claims falls through to
        the engine's own executor untouched.

        THE PACKAGE'S HANDS ARE BUILT FROM THIS ENGINE'S EXECUTOR, so a search reaches the
        world through the same gauntlet a `create_vm` does. That is the difference between
        loading a capability and opening a second door for it.
        """
        owner = {}
        for p in self.packages:
            hands = None
            try:
                hands = p.hands(execute)
            except Exception:
                hands = None
            if hands is None:
                continue
            for tool in (p.tools() or ()):
                owner[tool] = hands
        if not owner:
            return execute

        def dispatch(tool: str, args: Dict[str, Any]):
            return (owner.get(tool) or execute)(tool, args)

        return dispatch

    @property
    def manifest(self) -> Dict[str, Any]:
        """This engine's kinds, plus every loaded package's — merged, collisions refused.

        A WORLD THAT DECLARES NO KINDS IS ON THE DEFAULT MANIFEST, not on an empty one.
        `{}` means "nothing of my own to say", and reading it as "there are no kinds" is a
        trap that bit FOUR TIMES in one day: `effects._K` answered every question with
        silence, the lab mount's row translation matched nothing, `deleters` reported that
        nothing was destructive, and `claims` had the GENERAL ENGINE claim nothing at all.
        Each was patched at the call site until it became obvious the call sites were not
        the problem. Answered once, here, where the question is actually asked.
        """
        from ...packages.base import merge
        own = getattr(self._world, "kinds", None) or _config.KINDS or {}
        return merge(own, *(p.manifest for p in self.packages))

    def world(self):
        return self._world

    def claims(self, request: str) -> bool:
        """Medusa claims anything about the kinds it knows — it is the general engine.

        Over-claiming on purpose: this is the fallback when nothing more specific fits, and
        an engine never tried is worse than one tried and refused. `Unsolvable` is a cheap no.

        THIS OVERRIDES THE BASE, WHICH MATCHES THE MANIFEST'S NOUNS. Medusa is the fallback
        when nothing more specific fits, and a fallback that only answers when it recognises
        a noun is not a fallback. The base's noun match is right for a SPECIFIC engine; this
        is the general one, and widening is a decision rather than a duplicated regex.
        """
        return bool(self.manifest)

