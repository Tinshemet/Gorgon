"""_tree.py — THE IN-SESSION, and the tree grain that drives it.

    engine:        here is a node. DECOMPOSE it, or RUN it?
    orchestrator:  run it / decompose it / stop

Split out of `medusa.py` at 1039 lines because this ONE GENERATOR was 305 of them — the
queue, the verdict handling, the witness re-visit, the settling loop and the book keeper's
rows. It is cohesive and it is not small, and a reader looking for "what does the engine do
with a verdict" was reading past the mount contract, the writer seam and the correction loop
to find it.

A MIXIN, WHICH IS THE IDIOM `executor/api/` ALREADY USES for exactly this (three splits,
eleven files). The alternative — a collaborator object — would need the world, the manifest,
the packages and the session threaded into it, which is every field the engine has.
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


class _TreeMixin:
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
        from ..insession import DECOMPOSE, RUN, STOP, YIELD, Publish as _Publish, Step

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
            # WHAT EACH CHILD WAS SPLIT UNDER, keyed by the child's path and stashed
            # SEPARATELY from the rows. A premise is recorded when the PARENT is opened,
            # which is before the child is ever popped — writing it into `rows` there would
            # leave a half-built row that `setdefault` then refuses to complete, and the
            # report would read a node with a premise and no goal.
            premises: Dict[str, Dict[str, Any]] = {}
            settling: Dict[str, int] = {}
            while queue:
                goals, label, path = queue.pop(0)
                rows.setdefault(path, {
                    "goal": _gw._short(goals[0]) if len(goals) == 1 else label,
                    "path": path, "op": label,
                    "premise": premises.get(path),
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
                        from ..session import rank as _rank
                        here = getattr(session, "regime", "translation")
                        if _rank(planned["promote"]) <= _rank(here):
                            return {k: v for k, v in planned.items() if k != "promote"} | {
                                "calls": calls, "partial": done}
                        return {**planned, "calls": calls}
                    if not staged.get("ok"):
                        return {**staged, "calls": calls, "partial": done}
                    planned = staged
                # `ok` BEFORE `done`, AND THE ORDER WAS THE BUG. `_plan` marks an INVALID
                # program `done: True` so the caller stops rather than running it — and this
                # read `done` first, so a program the validator refused was folded into the
                # satisfied pile and the session closed DONE with an empty rendering. The
                # operator was told their request needed nothing doing because the writer had
                # produced something unrunnable.
                if not planned.get("ok", True):
                    return {**planned.get("result", planned), "calls": calls}
                if planned.get("done"):
                    done += goals
                    continue

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
                    # THE PREMISE THIS SPLIT WAS MADE UNDER, recorded so it can be
                    # RE-EVALUATED later. It is the design note's own answer to "what marks
                    # a node infected": a child is built on the assumption that the set its
                    # parent was split over still has the membership it had at the split, and
                    # `_lower` resolved exactly that set to produce the children.
                    #
                    # A MEDUSA PREDICATE, NEVER PROSE, so `holds` re-checks it through the
                    # same seam an ENSURE uses — a keeper whose verdict came from a model
                    # would be the second bad draw on the one number this exists to make
                    # trustworthy.
                    premise = self._premise_of(goals, len(finer))
                    if premise is not None:
                        for i in range(len(finer)):
                            premises[f"{path}.{i}"] = premise
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
            #
            # AND THE RECORDED PREMISES ARE RE-CHECKED, which is the half that was built and
            # never wired: `with_premise` and `inspect` existed while the engine assigned
            # states from the witness alone. The witness is the STRONGER check — it re-plans
            # the goal and asks whether work remains — so `inspect` leaves a node it already
            # judged and fills in the ones that had NO witness available, which is exactly
            # where the engine's own method is silent.
            _, holds = _gw._seams_of(self._world)
            judged = _keeper.inspect(list(rows), holds)
            out["tree"] = _keeper.drift(judged)
            out["tree_report"] = _keeper.report(judged)
        return out

