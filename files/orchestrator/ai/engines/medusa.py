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
from ..planner import tree_keeper as _keeper
from ..planner.ir import lower as _lower
from ..planner.ir import observe as _observe
from ..planner.ir import config as _config
from ..planner.ir import consent as _consent
from ..planner.ir import render as _render
from ..planner.ir import run as _run
from ..planner.ir import effects as _effects
from ..planner.ir import validate as _validate
from .base import Engine


def _prose_of(components) -> str:
    """The sentence a set of components came from, if one travelled with them.

    STAGED LOWERING OPENS PROSE; the writer covers structure. A component that carries no
    `_goal` has no sentence to open, and manufacturing one from the structure would be
    writing the request rather than serving it — the decomposer that split prose to BUILD is
    the mistake #55 already recorded.
    """
    for c in components or ():
        text = (c or {}).get("_goal")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _findings_of(world, result) -> List[Dict[str, Any]]:
    """What the run OBSERVED — the ledger, never the call list.

    A finding is something the world told us; a call is something we asked it. Conflating
    them would let a reporter say "beta was unreachable" because a probe was ISSUED, which is
    exactly the inference decision 6 forbids and the reason `reach` demands an answer rather
    than a success flag.
    """
    ledger = getattr(world, "findings", None)
    # THREE LEDGER SHAPES AND THE PRODUCTION ONE WAS MISSING. `Findings` is neither a dict
    # nor a list — it is the object the real runtime records into — so an engine over the VM
    # sim fell straight through to listing its own CALLS, and reported "I asked alpha" where
    # it had been told "alpha answered". Exactly the conflation `_findings_of` was written to
    # prevent, in the one world that matters most.
    if hasattr(ledger, "facts") and callable(ledger.facts):
        got = [{"fact": f, "value": ledger.get(f)} for f in sorted(ledger.facts())]
        if got:
            return got
    if isinstance(ledger, dict) and ledger:
        return [{"fact": k, "value": v} for k, v in sorted(ledger.items())]
    if isinstance(ledger, list) and ledger:
        return list(ledger)
    # NO OBSERVATIONS IS NOT NO ANSWER. A program that only acted has findings of a
    # different kind — what it changed — and saying so is better than silence.
    return ([{"did": tool, **(args or {})} for tool, args in (result.get("calls") or [])]
            if result.get("ok") else [])


# HOW MANY TIMES ONE IN-SESSION MAY BE TOLD TO OPEN A NODE INSTEAD OF RUNNING IT. Twelve
# matches the writer's own lowering depth, for one reason: a session that out-opens its writer
# is refining a goal the writer already knows how to reach.
_MAX_OPENINGS = 12

# HOW MANY TIMES ONE NODE MAY BE TOLD TO WAIT. The same twelve, for the same reason: a node
# re-offered a thirteenth time is not waiting for something, it is being refused by a
# decider that will not say so.
_MAX_WAITS = 12


class MedusaEngine(Engine):
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
        from ..packages.base import merge
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

    def steps(self, components: List[Dict[str, Any]], session=None):
        """THE IN-SESSION: what this engine wants a verdict on before it acts.

            engine:        this node — run it, or decompose it?
            orchestrator:  run it / decompose it / stop
            ...until the work is done or refused.

        THE ENGINE DECOMPOSES; THE ORCHESTRATOR ONLY SAYS WHETHER IT SHOULD. That division
        is deliberate. Decomposing needs the manifest, the world and the lowering rules — all
        of which belong to the engine — while the decision to spend another round on a node
        belongs to whoever holds the budget and the operator's consent, which is never the
        thing asking for more.

        THE REGIME DECIDES THE STARTING GRAIN, mechanically rather than by description:

            TRANSLATION  the writer plans the WHOLE request, so it opens with ONE exchange —
                         "here is the program, run it?" One question, one verdict.
            TREE         each goal is offered SEPARATELY, so the orchestrator rules on every
                         node. That is exactly why promotion COSTS: a tree is not a cleverer
                         regime, it is a more expensive conversation.

        BUT THE GRAIN IS NOT FIXED BY THE REGIME — a DECOMPOSE verdict refines it. A whole
        program told to decompose becomes its goals; a goal told to decompose becomes its
        sub-goals. That is what makes the verdict real: an earlier version accepted DECOMPOSE
        and ran the node anyway, which is the recorded-but-inert escalation this project has
        found in three separate places.

        A STOP is honoured and the work stops where it stopped — reported as partial rather
        than rolled back, because the calls already made are facts.
        """
        from .insession import DECOMPOSE, RUN, STOP, YIELD, Publish as _Publish, Step

        with _config.use_kinds(self.manifest if self._foreign else None):
            whole = getattr(session, "regime", "translation") != "tree"
            # THE QUEUE IS THE TREE, breadth-first and explicit. A node is (goals, label) —
            # the whole request is just the node whose goals are all of them, which is why
            # translation and tree are one loop rather than two code paths that drift.
            queue = [(list(components), "the whole program", "0")] if whole else \
                    [([g], "one goal", str(i)) for i, g in enumerate(components)]
            if not whole:
                # THE TOP-LEVEL WITNESS, and it is not optional.
                #
                # `cover` closes the whole request under a FIXPOINT — four rounds, because
                # goals interact and a later one can undo an earlier one. Serving the goals
                # as separate root nodes threw that away: each node closed, nothing re-read
                # the others, and the run reported success.
                #
                # MEASURED on the fuzz corpus: "every machine can reach the others, and end
                # up with exactly one machine" put three machines on a network, pinged them,
                # then DELETED TWO — and answered OK. Every node was locally correct and the
                # request was false. Without this the tree grain is not a more expensive way
                # to get the same answer, it is a cheaper way to get a wrong one.
                whole_goals = [g for g in components if _gw.groundable(g)]
                if whole_goals:
                    queue.append((whole_goals, "the request · witness", "*"))
            calls, done, opened, ran_nodes = [], [], 0, []
            # HOW MANY TIMES EACH NODE HAS BEEN TOLD TO WAIT, and how many verdicts in a row
            # have been waits. The second is the deadlock detector: a queue where everything
            # yields and nothing runs will never change, because the only thing that changes
            # the world here is running.
            waited: Dict[str, int] = {}
            stalled = 0
            # THE TREE, AS THE BOOK KEEPER WANTS IT — one row per node, keyed by path so a
            # parent's re-visit updates the parent's own row rather than adding a second.
            rows: Dict[str, Dict[str, Any]] = {}
            settling: Dict[str, int] = {}
            while queue:
                goals, label, path = queue.pop(0)
                rows.setdefault(path, {
                    "goal": _gw._short(goals[0]) if len(goals) == 1 else label,
                    "path": path, "op": label,
                    # UNKNOWN UNTIL SOMETHING ASKS. Decision 6's rule, and the keeper's own:
                    # a node nobody re-checked is not sound, it is unexamined.
                    "state": _keeper.UNKNOWN, "why": "no witness — nothing to re-check"})
                planned = self._plan(goals, session)
                if planned.get("promote"):
                    # THE WRITER REFUSED, AND THAT REFUSAL IS THE PROMOTION SIGNAL. What is
                    # new is that a promotion can now BUY something rather than asking the
                    # same question again — but only where the tree regime has already been
                    # GRANTED, so the cost falls on whoever holds the budget and not on the
                    # engine that wanted it.
                    staged = self._staged(goals, session)
                    if staged is None:
                        # DO NOT ASK FOR A REGIME YOU ALREADY HAVE. `_plan` returns
                        # `promote: tree` on every `Unsolvable`, which was right while
                        # `achieve` started in TRANSLATION and became nonsense the moment it
                        # started in TREE: the session asked to be promoted to where it
                        # already was, `may_promote` refused because a regime cannot outrank
                        # itself, and the operator read `promotion to tree DECLINED` on a
                        # session already running as a tree.
                        #
                        # THERE IS NOTHING ABOVE THE TREE. When the writer cannot build it
                        # and staged lowering is not available, the honest close is the
                        # WRITER'S OWN REASON — "nothing reaches this goal" — rather than a
                        # story about an escalation that was never possible.
                        from .session import rank as _rank
                        here = getattr(session, "regime", "translation")
                        if _rank(planned["promote"]) <= _rank(here):
                            return {k: v for k, v in planned.items() if k != "promote"} | {
                                "calls": calls, "partial": done}
                        return {**planned, "calls": calls}
                    if not staged.get("ok"):
                        return {**staged, "calls": calls, "partial": done}
                    planned = staged
                if planned.get("done"):
                    done += goals
                    continue
                if not planned.get("ok", True):
                    return {**planned.get("result", planned), "calls": calls}

                # PLANNED, SO IT IS ALREADY KNOWN. Computing this before the yield rather
                # than after a DECOMPOSE means the step can DECLARE its own grain, and a
                # decider that reads the declaration never asks for a split that cannot exist.
                finer = self._open(goals)
                verdict = yield Step(RUN, goals[0] if len(goals) == 1 else planned["program"],
                                     label, cost=len(planned["plan"]),
                                     # A NODE WITH NOTHING LEFT TO DO IS NOT DIVISIBLE. Its
                                     # whole content is the witness, and there is nothing
                                     # finer inside a verification — splitting one would
                                     # discard the very check it exists to make.
                                     divisible=finer is not None and bool(planned["plan"]),
                                     destroys=[c for c in planned["plan"]
                                               if c[0] in _effects.deleters(self.manifest)],
                                     # WHAT IT WOULD CHANGE, so the in-session can refuse a
                                     # node that reaches above the rung this session was
                                     # granted. The writer plans against the world as it is,
                                     # so this is the actual bill and not an estimate.
                                     acts=[c for c in planned["plan"]
                                           if c[0] in _effects.actors(self.manifest)])
                action = verdict.action if verdict is not None else STOP

                if action == YIELD:
                    waited[path] = waited.get(path, 0) + 1
                    stalled += 1
                    why = verdict.why or "no reason given"
                    session.record(f"waiting: {label} — {why}")
                    rows[path]["state"] = _keeper.UNKNOWN
                    rows[path]["why"] = f"waited for {why}"
                    if waited[path] > _MAX_WAITS:
                        return {"ok": False, "refused": True, "calls": calls, "partial": done,
                                "why": f"waited {waited[path]} times for {why} and it never "
                                       f"came"}
                    if stalled > len(queue) + 1:
                        # EVERY REMAINING NODE HAS YIELDED SINCE ANYTHING LAST RAN. Nothing
                        # in this session can change that, because running is the only thing
                        # that changes the world — so it is named as a deadlock rather than
                        # spun on until a counter runs out and blames the wrong node.
                        return {"ok": False, "refused": True, "calls": calls, "partial": done,
                                "why": f"deadlocked — every remaining node is waiting and "
                                       f"nothing can run; the last said: {why}"}
                    queue.append((goals, label, path))
                    continue
                stalled = 0

                if action == STOP:
                    return {"ok": False, "refused": True, "calls": calls, "partial": done,
                            "why": verdict.why if verdict is not None else "no verdict given"}

                if action == DECOMPOSE:
                    opened += 1
                    if opened > _MAX_OPENINGS:
                        # AN IN-SESSION THAT ONLY EVER OPENS NEVER ACTS. The cap is not a
                        # safety net for a bug; it is the point at which "decompose it again"
                        # has stopped being a decision and become a refusal that will not say
                        # so, and it is named as one here.
                        return {"ok": False, "refused": True, "calls": calls, "partial": done,
                                "why": f"decomposed {opened} times without ever being granted "
                                       f"a node to run"}
                    if finer is None:
                        # THE STEP SAID IT WAS ATOMIC AND WAS TOLD TO SPLIT ANYWAY. The engine
                        # will not invent a split to satisfy the ask — that is how a
                        # decomposer starts producing fragments — and it will not quietly run
                        # what was not granted either. It says which of the two happened.
                        return {"ok": False, "refused": True, "calls": calls, "partial": done,
                                "why": f"told to decompose a node declared atomic, and "
                                       f"nothing lowers it: {_gw._short(goals[0])}"}
                    # THE PARENT IS RE-QUEUED BEHIND ITS OWN CHILDREN, and this is not
                    # bookkeeping — it is the parent's WITNESS.
                    #
                    # MEASURED, not reasoned: opening every divisible node left 5 of 13 rungs
                    # reporting `grounded=False` while their own checkers still passed. The
                    # work was done and the run no longer proved it, because a decomposed
                    # goal's closing ENSURE is never written — each child vouches for itself
                    # and nobody vouches for the whole. Re-visiting the parent costs one
                    # exchange with an empty plan when the children did their job, and
                    # catches ROOT POISONING when they did not: the goal is re-planned
                    # against the world as it now is, so a set that changed underneath the
                    # split shows up as work still to do rather than as silent success.
                    # A NODE WITH NO WITNESS IS NOT RE-VISITED. `observe` and bare probes are
                    # things DONE, not things that become true, so returning to one would
                    # RE-ASK rather than verify — measured, and it took rung 11 from 6 calls
                    # to 44 while turning a passing run into a failing one.
                    # ONLY THE GOALS THAT HAVE A WITNESS COME BACK. Carrying an `observe`
                    # into the re-visit re-ASKS it — a probe is never "already done", so a
                    # node holding one always has work and never settles. Rung 11 opened
                    # thirteen times without ever being granted anything to run, because its
                    # whole-program witness dragged four pings around with it.
                    witnessed = [g for g in goals if _gw.groundable(g)]
                    back = [(witnessed, f"{label} · witness", path)] if witnessed else []
                    queue = [(g, l, f"{path}.{i}") for i, (g, l) in enumerate(finer)] \
                        + back + queue
                    continue

                ran = self._execute_plan(planned, goals, session)
                calls += ran.get("calls") or []
                # WHAT THIS NODE OBSERVED, SAID RATHER THAN LEFT LYING IN THE WORLD. The
                # orchestrator used to reach into the ledger and take what it found; an
                # engine whose world has no ledger was simply never heard. Saying it makes
                # any engine audible, including one whose world is somebody else's API.
                # WHAT THE PROGRAM ITSELF ASKED TO SUBMIT, first and by name. A `PUBLISH`
                # line is the program saying what it was FOR; the sweep below is this engine
                # noticing what else it happened to learn. The value comes from the ledger,
                # never from the statement — the program names the fact and the world says
                # what it is, so a program cannot report an answer it never obtained.
                #
                # AN UNOBSERVED FACT PUBLISHES AS `unknown`, which is a real answer and the
                # one this codebase keeps insisting on: a search nobody could run reports
                # that it has no answer, rather than reporting nothing at all and leaving the
                # operator to guess whether it worked.
                observed = {f.get("fact"): f.get("value")
                            for f in (ran.get("findings") or []) if "fact" in f}
                for fact in ran.get("published") or []:
                    yield _Publish(fact, observed.get(fact, _observe.unknown())
                                   if fact != "done" else "done")
                for finding in ran.get("findings") or []:
                    if "fact" in finding:
                        yield _Publish(finding["fact"], finding.get("value"))
                    elif "did" in finding:
                        # WHAT WAS DONE, WHEN NOTHING WAS OBSERVED. Said under its own name
                        # so nobody can mistake an intention for a result: "I asked alpha" is
                        # not "alpha answered", and the reporter is handed these too.
                        yield _Publish(f"did:{finding['did']}",
                                       {k: v for k, v in finding.items() if k != "did"})
                if not ran.get("ok"):
                    return {**ran, "calls": calls, "partial": done}
                ran_nodes.append((ran, goals))
                done += goals
                # THE WITNESS IS THE VERDICT ON THE SPLIT. A re-visited parent with an empty
                # plan means its children covered it — sound. A re-visited parent that STILL
                # HAD WORK means the set it was split over moved underneath it: every child
                # was locally correct and the parent goal was false anyway, which is the
                # whole shape of root poisoning. Nothing new is measured here; the plan
                # length already said it.
                if label.endswith("· witness"):
                    stale = bool(planned["plan"])
                    # ONCE INFECTED, IT STAYS INFECTED. The settling loop re-visits until the
                    # goals stop moving, and the LAST pass is sound by construction — writing
                    # that over the first pass's verdict would report a run served against a
                    # moving world as clear, which is the single thing this keeper exists to
                    # say. A correction that worked is still a correction that was needed.
                    if stale:
                        rows[path]["state"] = _keeper.INFECTED
                        rows[path]["why"] = (
                            f"the set it was split over changed — {len(planned['plan'])} "
                            f"further call(s) were needed after its children closed")
                    elif rows[path]["state"] != _keeper.INFECTED:
                        rows[path]["state"] = _keeper.SOUND
                        rows[path]["why"] = ("re-planned after its children and had nothing "
                                             "left to do")
                    # A WITNESS THAT HAD WORK HAS NOT SETTLED. It just changed the world, so
                    # the goals it shares a request with may have moved again — the same
                    # reason `cover` re-covers rather than passing once. Four rounds, and
                    # the number is `cover`'s: a witness that out-loops the writer's own
                    # fixpoint is chasing something the writer already gave up on.
                    if stale:
                        settling[path] = settling.get(path, 0) + 1
                        if settling[path] < 4:
                            queue.append((goals, label, path))
                        else:
                            rows[path]["why"] = (
                                "re-planned four times and never settled — the goals are "
                                "pulling against each other")
                else:
                    # A LEAF THAT RAN CARRIES ITS OWN CLOSING ENSURE, so it witnessed itself.
                    rows[path]["state"] = _keeper.SOUND
                    rows[path]["why"] = "ran with its own closing witness"
            return self._joined(ran_nodes, calls, list(rows.values()))

    def _joined(self, ran_nodes: List[Any], calls: List,
                rows: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Several executed nodes as one result.

        THE GRAIN OF THE IN-SESSION MUST NOT CHANGE THE ANSWER. A request served as one
        program and the same request served as four nodes have to come back saying the same
        things, or the orchestrator's verdicts would silently alter what the operator is told
        — and GROUNDING is where that bites: a whole program vouches for itself once, four
        nodes vouch four times, and reporting the last one's verdict would call a run grounded
        because its final quarter was.
        """
        # ONLY NODES THAT COULD BE GROUNDED GET A VOTE. A node carrying nothing but probes
        # has no witness available to it, and counting its `False` would report a run as
        # unvouched-for because part of it was an observation.
        vouched = [r.get("grounded") for r, gs in ran_nodes
                   if any(_gw.groundable(g) for g in gs) and r.get("grounded") is not None]
        # THE VERDICTS THE NODES REACHED, carried across the join. See `_execute_plan`.
        verdicts = [r["verdict"] for r, _ in ran_nodes if r.get("verdict")]
        # AND ITS REASON. "count is 4, wanted == 9" IS the answer to an ensure, and a join
        # that kept the verdict while dropping the sentence would report `holds: false` with
        # nothing saying what was found.
        said = next((v["why"] for v in verdicts if v.get("why")), None)
        out = {"ok": True, "calls": calls, "why": said,
               # THE WHOLE RUN'S CALLS, not one node's. `_findings_of` falls back to what was
               # done when the world observed nothing, and handing it a single node would
               # report a quarter of the work as all of it.
               "findings": _findings_of(self._world, {"ok": True, "calls": calls}) + verdicts,
               "rendered": "\n".join(r.get("rendered", "") for r, _ in ran_nodes).strip(),
               "grounded": all(vouched) if vouched else None}
        if len(ran_nodes) == 1:
            out["program"] = ran_nodes[0][0].get("program")
        if rows:
            # THE BOOK KEEPER READS AND REPORTS; IT DOES NOT ACT. The correcting already
            # happened — the parent was re-planned — so what is left is telling somebody it
            # was needed. A run served against a moving set succeeded and is not the same
            # thing as one served against a set that held still.
            out["tree"] = _keeper.drift(sorted(rows, key=lambda r: r["path"]))
            out["tree_report"] = _keeper.report(sorted(rows, key=lambda r: r["path"]))
        return out

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
        from ..planner.ir import intent as _intent
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
            plan = _gw.cover(components, world, temps=temps, acting=corrects)
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
        from ..planner.ir import intent as _intent
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
        from ..planner.ir import derive as _derive
        from ..planner.ir import execute as _exec

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

    def _execute_plan(self, planned: Dict[str, Any],
                      components: List[Dict[str, Any]],
                      session=None) -> Dict[str, Any]:
        """Run a plan that has already been granted. No decisions are made here.

        THE SESSION, NOT ITS EVENT LOG. This took `session_events` and therefore could not
        answer the two questions `run()` asks before it touches anything — what was the
        operator's INTENT, and have they CONSENTED — so it answered them itself, with
        `consent=True, intent="achieve"`. That is the maximum of both: every program granted
        the top of the ladder, and grounding waved through unasked, on the one path that
        reaches the real lab. The session has carried the real answers since it was written.
        """
        session_events = getattr(session, "events", None)
        world = self._world
        program = planned["program"]
        # DOES THIS PROGRAM CHANGE ANYTHING AT ALL — computed from the manifest, not read off
        # the op names.
        #
        # `consent.survey` counts a `CALL` as acting, and it is right to: it reads an artifact
        # alone and cannot know what the tool behind the word does. The ENGINE can, because it
        # holds the manifest, and the two answers differ exactly on a probe — a program of four
        # `guest_ping`s "acts" four times by the artifact's reading and changes nothing.
        #
        # MEASURED THE MOMENT CONSENT STOPPED BEING HARDCODED: rung 11 and every opened leaf of
        # rung 4 were refused for carrying no witness to work they never did. Asking a person
        # to consent to a program that only asks questions is how a consent prompt becomes
        # noise, which is the failure `consent.py`'s own docstring set out to avoid.
        changes = [c for c in planned.get("plan") or ()
                   if c[0] in _effects.actors(self.manifest)]
        select, holds = _gw._seams_of(world)
        if session_events is not None:
            session_events.program(f"{len(program.get('body') or ())} statement(s)",
                                   _render(program))

        def watched(tool, args):
            """The engine's executor, with a ledger line per call.

            WRAPPED RATHER THAN RECONSTRUCTED FROM THE RESULT. Filing these afterwards would
            give every call the same timestamp and lose the ones that ran before a failure —
            which are the calls you most want to see.
            """
            out = self._execute(tool, args)
            if session_events is not None:
                bad = not (out or {}).get("success", True)
                session_events.file(
                    self.name, "world",
                    f"{tool}({', '.join(f'{k}={v}' for k, v in (args or {}).items())})",
                    "call failed: " + str((out or {}).get("error")) if bad else "call",
                    level="error" if bad else "info")
            return out

        result = _run(program, watched, select=select, holds=holds,
                      known_names=world.names(),
                      known_tools=_effects.tools_of(self.manifest) or None,
                      # THE SESSION'S, NOT THIS ENGINE'S. `run()` re-checks the whole program
                      # statement by statement, which is finer than what the in-session can
                      # see: the step gate refuses a node that ACTS above its rung, and this
                      # also catches a FETCH that judges. Both read `intent._PERMITS`, so the
                      # two gates cannot disagree — a second gate judging by a different
                      # standard is worse than one, because the disagreement is silent.
                      # A PROGRAM THAT CHANGES NOTHING HAS NOTHING TO CONSENT TO, and that is
                      # computed above rather than assumed — the answer, not a bypass.
                      consent=(getattr(session, "consent", None) if changes else True),
                      intent=getattr(session, "intent", None),
                      # WHICH OF THE KNOWN TOOLS CHANGE SOMETHING. The engine holds the
                      # manifest, so the ladder gets the exact answer about a `CALL` rather
                      # than the safe one — which is the difference between a `fetch` that
                      # can ask a question and one that cannot.
                      acting_tools=_effects.actors(self.manifest))
        result = self._correct(program, result, select, holds, watched, session)
        survey = _consent.survey(program)
        # A CHECK THAT SAYS NO IS AN ANSWER, NOT A FAILURE.
        #
        # `run` reports an unsatisfied ENSURE as `failed: unsatisfied`, which is right for an
        # ACHIEVE — there the assertion is a precondition the plan was built on, and its
        # falsity means the plan was wrong. Under an `ensure` the assertion IS THE REQUEST,
        # and reporting "count is 4, wanted == 9" as a failed run tells the operator their
        # question broke rather than answering it.
        #
        # SOUND ONLY BECAUSE OF THE LINE ABOVE. This can be read as the verdict precisely
        # because a non-acting program contains nothing but the checks the operator asked
        # for — no preconditions, no corrections, nothing whose falsity would mean something
        # else. Under an ACHIEVE the two are genuinely indistinguishable from here, and the
        # branch is not taken.
        corrects = self._corrects(session)
        verdict = None
        if not corrects and result.get("failed") == "unsatisfied":
            verdict = {"fact": "holds", "value": False, "why": result.get("why") or ""}
        elif not corrects and result.get("ok") and survey["asserts"]:
            verdict = {"fact": "holds", "value": True, "why": result.get("why") or ""}
        if verdict is not None:
            return {"ok": True, "calls": result.get("calls") or [],
                    "findings": (_findings_of(world, {"ok": True, **result}) or []) + [verdict],
                    # NAMED, NOT LEFT TO BE RECOGNISED IN A LIST. `_joined` rebuilds findings
                    # from the world's LEDGER, which is right for observations and wrong for
                    # this: a verdict is something the engine DETERMINED, not something the
                    # world was asked. Without its own key it was dropped on every path that
                    # joins nodes — so an ENSURE answered correctly and reported nothing.
                    "verdict": verdict,
                    "published": result.get("published") or [],
                    "program": program, "rendered": _render(program),
                    "grounded": survey["grounded"], "vacuous": survey["vacuous"],
                    "why": verdict["why"]}
        return {"ok": bool(result.get("ok")),
                "calls": result.get("calls") or [],
                # WHAT WAS OBSERVED, kept apart from what was DONE. The reporter is handed
                # findings and nothing else, so an engine that returned its calls under this
                # name would be handing the narrator a list of INTENTIONS to describe as
                # results — which is the difference between "three machines answered" and
                # "I asked three machines".
                "findings": _findings_of(world, result),
                # WHAT THE PROGRAM ASKED TO SUBMIT, in its own words. The engine used to
                # decide on its own what was worth saying by scraping the findings ledger,
                # which meant the PROGRAM — the artifact an operator reads and could have
                # written — never mentioned the one thing they were waiting for. A `PUBLISH`
                # line makes the report part of the code rather than a side effect of it.
                "published": result.get("published") or [],
                "program": program,
                "rendered": _render(program),
                "grounded": survey["grounded"],
                "vacuous": survey["vacuous"],
                # THE PROMOTION REQUEST, IF THE CORRECTOR MADE ONE. `derive` returning None
                # is the doorway to ACHIEVE's second engine, and the orchestrator is the only
                # thing that may open it — dropping the key here would leave a refusal that
                # said "unmet" where the truth is "this needs a regime I was not granted".
                **({"promote": result["promote"]} if result.get("promote") else {}),
                "why": result.get("why") or result.get("failed")}
