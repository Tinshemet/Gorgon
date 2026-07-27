"""
engine_core.py — run_score, the recursive goal→primitive decomposition engine.

The irreducible core: run_score and its nested closures (_resolve ↔ _attempt and
the AND/OR closers) capture the injected policy bundle, so they stay one atomic
unit. The stateless helpers, meta-tool schemas, and injected-dep fallbacks are
imported from the sibling modules.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional

from .meta_tools import DECOMPOSE_TOOL, ALTERNATIVES_TOOL, _NODE_SYSTEM, _OPAQUE_TOOLS
from .ledger_util import (_node, _norm, _progress_summary, _attach_steer, _first_tool_call,
                          _SET_VALUED_RE, _OBSERVER_TOOLS)
from ._deps import (
    _default_gate, _default_criterion, _default_legal, _consent_verb, _tool_risk,
    _yield_fact, _extract_value, _finding_probe_spec,
)


def run_score(
    goal: str,
    *,
    call_model:     Callable[[List[Dict], List[Dict]], Dict],
    execute:        Callable[[str, Dict], Any],
    tools:          List[Dict],
    engine=None,
    build_context:  Optional[Callable[[str, List[str]], str]] = None,
    select_tools:   Optional[Callable[[str, List[Dict]], List[Dict]]] = None,
    max_retries:    int = 2,
    max_depth:      int = 3,
    max_steps:      int = 0,
    ledger:         Optional[List[Dict[str, Any]]] = None,
    **_legacy,
) -> Dict[str, Any]:
    """Reduce `goal` to primitive tool calls and execute them; return tree + ledger.

    call_model(messages, tools) -> model response dict (message.tool_calls).
    execute(tool_name, args)    -> result (dict with "success"/"error", ideally).
    tools                       -> the primitive tool schemas offered at every node
                                   (decompose is appended automatically).
    build_context(goal, path)   -> optional str prepended as system grounding
                                   (e.g. the Active Library digest). DETERMINISTIC.
    is_destructive(tool, args)  -> optional; when True + confirm given, ask first.
    confirm(tool, args)         -> optional human backstop; False skips the leaf.
    select_tools(goal, tools)   -> optional PER-NODE tool selection. Return a subset
                                   of `tools` to offer at this node (decompose is
                                   appended). VERIFIED necessary for llama3.1: with
                                   all ~46 tools the weak model replies with pseudo-
                                   code text instead of tool-calling; narrowed to the
                                   node's sub-goal it emits decompose/primitives
                                   correctly (2026-07-17). Default None = all tools.
    verify(criterion, tool,     -> the reality-check for VERIFIED completion. After a
      args, result)                leaf's execute reports success, the tree confirms
                                   the contract's success CRITERION actually holds
                                   (against the Active Library / event_log). Returns
                                   False → the node is `unverified`, NOT done (the
                                   "execute said ok but it didn't really happen" case).
                                   Default None = trust the execute result.
    criterion_of(tool)          -> the per-tool success criterion (what "done" means),
                                   e.g. create_vm -> "present". Default = the active
                                   agent's contract.success_criterion (the contract
                                   declares the criterion; `verify` checks it).
    gate(tool, args)            -> the CONTRACT bound: maps a proposed leaf's risk
                                   tier through the active agent's disposition to a
                                   handling action. "halt" blocks the leaf (a red
                                   line the tree cannot cross); "checkpoint" takes a
                                   savepoint before it; anything else executes. This
                                   is how the contract bounds the tree — dynamic
                                   replanning cannot escape it. Default = the active
                                   agent's contract.gate_action.
    decompose_first             -> DECOMPOSE-FIRST scaffolding. A weak model won't
                                   volunteer decomposition when it can grab a primitive,
                                   so before offering primitives at a node we FORCE the
                                   atomicity question by offering ONLY `decompose`. If
                                   it splits the goal into 2+ real steps → decompose; if
                                   it collapses to the goal itself → the goal is atomic,
                                   offer the primitive. Costs one extra model call per
                                   node. Default off (preserves the offer-both behavior).
    max_retries                 -> BACKTRACK budget per node. A leaf that soft-fails
                                   (failed / unverified) is re-attempted up to this
                                   many times, each time with the approaches that
                                   already failed here fed back so the model can't
                                   repeat them (failed-branch memory). Backtrack is
                                   LOCAL to the failing node, so already-succeeded
                                   siblings are never re-run. 0 = no backtracking.
    max_depth                   -> recursion bound (a node deeper than this is
                                   marked blocked rather than decomposed further).

    Returns {"root": <node>, "ledger": [<executed leaf records>], "ok": bool}.
    A node's status is one of: done / failed / partial / blocked / skipped /
    no_action / unverified. A recovered node carries retries/tried/recovered.
    """
    from orchestrator.ai.planner.engine import Engine
    if engine is None:                       # legacy kwargs (gate=…, verify=…) → Engine
        engine = Engine.from_kwargs(_legacy)
    # Unpack the policy bundle into the local names the body already uses (defaults
    # fall back to the active contract's functions), so the logic below is unchanged.
    gate            = engine.gate or _default_gate
    verify          = engine.verify
    verify_goal     = engine.verify_goal
    criterion_of    = engine.criterion_of or _default_criterion
    legal_filter    = engine.legal_filter or _default_legal
    referendum      = engine.referendum
    watchdog        = engine.watchdog
    killswitch      = engine.killswitch
    findings        = engine.findings
    findings_schema = engine.findings_schema
    method_cache    = engine.method_cache
    decompose_first = engine.decompose_first
    estimate        = engine.estimate
    ce_floor        = engine.ce_floor
    retry_penalty   = engine.retry_penalty
    whole_goal_gate = engine.whole_goal_gate
    max_revisions   = engine.max_revisions
    commit_gate     = engine.commit_gate
    reason_gate     = engine.reason_gate
    on_node         = engine.on_node
    expand_compound = engine.expand_compound
    expand_collective = engine.expand_collective
    ground_steps    = engine.ground_steps
    complete_steps  = engine.complete_steps
    already_satisfied = engine.already_satisfied
    program_tool    = engine.program_tool
    run_program     = engine.run_program
    goal_complaint    = engine.goal_complaint
    goal_effect       = engine.goal_effect

    def _refine_steps(parent_goal: str, steps: list) -> list:
        """Apply the harness's step-refinement passes to a model decomposition: bind bare
        references (1.2), then inject missing prerequisites (1.4) — so a plausible-but-
        incomplete plan is grounded and made whole before it runs."""
        if ground_steps:
            steps = ground_steps(parent_goal, steps)
        if complete_steps:
            steps = complete_steps(parent_goal, steps)
        return steps

    def _emit(kind: str, node_goal: str, depth: int, path: List[str], **extra) -> None:
        """Fire a live node-lifecycle event (enter/plan/leaf/close) for a streaming tree
        view. A no-op with zero overhead when no observer is attached. Never lets a
        renderer error break the run."""
        if on_node is None:
            return
        try:
            on_node({"kind": kind, "goal": node_goal, "depth": depth, "path": list(path), **extra})
        except Exception:
            pass

    # Caller may pass its own ledger list (so it can read verified verdicts LIVE
    # as the run proceeds — see autonomous.run_autonomous's p_of); default owns one.
    if ledger is None:
        ledger = []
    _RETRY_STATUS = {"failed", "unverified"}   # soft failures worth a different approach
    # Depth of the correction we're inside (backtrack retry / revision / escalation). Not a
    # mode flag: nested _resolve calls increment it, so it stays correct for sub-trees too.
    _correcting = {"n": 0}
    # THRASHING BOUND (Track 1.5): a broken decomposition can send backtrack × revision ×
    # re-decompose into a call explosion that never converges. `max_steps` caps the total
    # node attempts; once spent, planning stops and the offending node closes `blocked
    # (step_budget)` — the run fails FAST and honestly instead of burning the model. 0 = off.
    _budget = {"n": 0}

    def _approach_desc(node: Dict[str, Any]) -> str:
        """One-line summary of the attempt that just failed — for the retry prompt."""
        if node.get("tool"):
            return f"{node['tool']} → {node['status']}" + (f" ({node['reason']})" if node.get("reason") else "")
        if node.get("children"):
            return "decompose into [" + "; ".join(c["goal"] for c in node["children"]) + f"] → {node['status']}"
        return node.get("status", "?")

    def _fail_detail(node: Dict[str, Any]) -> str:
        """The CONCRETE reason a step failed — its status reason PLUS the executor's own
        error message (Track 1.3/1.4). Surfacing "no such network lab" (not just "failed")
        is what lets the model's re-plan actually FIX the plan (create the missing
        prerequisite) instead of re-emitting the same broken steps."""
        bits = []
        if node.get("reason"):
            bits.append(str(node["reason"]))
        res = node.get("result")
        if isinstance(res, dict) and res.get("error"):
            bits.append(str(res["error"]))
        return f" ({'; '.join(bits)})" if bits else ""

    def _plan_desc(node: Dict[str, Any]) -> str:
        """One-line post-mortem of a composite plan that came up short — for the REVISION
        prompt. Marks each step done (✓) or failed (✗ + CONCRETE error) so the model re-plans
        the CORRECTIVE remainder — creating a missing prerequisite, grounding a reference —
        instead of repeating the decomposition that fell short."""
        parts = []
        for c in node.get("children") or []:
            if c.get("status") == "done":
                parts.append(f"✓ {c['goal']}")
            else:
                parts.append(f"✗ {c['goal']}{_fail_detail(c)}")
        return "plan [" + "; ".join(parts) + f"] → {node.get('status')}"

    def _unmet_desc(node: Dict[str, Any], complaint: str) -> str:
        """Post-mortem for a plan that RAN IN FULL and was then rejected by the goal
        predicate. Every step is ✓, so a step-by-step tells the model nothing — what it
        needs is the predicate's own objection ("mesh(fleet) is not confirmed"). The plan
        wasn't incomplete, it was WRONG; the corrective plan has to target the objection."""
        ran = "; ".join(f"✓ {c['goal']}" for c in (node.get("children") or []))
        return (f"plan [{ran}] ran in FULL, but the goal is still NOT met: "
                f"{complaint or 'the goal predicate rejected the result'} "
                f"Do NOT simply repeat those steps — fix what is missing.")

    def _root_gate(node_goal: str, depth: int, children: List[Dict[str, Any]],
                   extra: Dict[str, Any]) -> Dict[str, Any]:
        """The CONTRACT ROOT PREDICATE (gauntlet E). A composite whose children satisfy
        it is 'done' — UNLESS it is the ROOT and the contract's goal predicate says the
        goal does not actually hold, in which case it is `unverified` (books NO reward:
        a clean-executing WRONG plan earns nothing). Gated to depth 0 on purpose —
        intermediate composites have no contract-declared end-state, and inventing one
        is the design's flagged soft-underbelly. verify_goal → True/False/None(no-op).
        """
        if depth == 0 and verify_goal is not None:
            if verify_goal(node_goal, children, ledger) is False:
                return _node(node_goal, "unverified", children=children,
                             reason="goal_predicate_unmet", **extra)
        return _node(node_goal, "done", children=children, **extra)

    def _correct(fn, *a, **kw):
        """Run a re-attempt inside the correction scope, so leaves below it may close on
        state alone instead of redoing work that is already finished."""
        _correcting["n"] += 1
        try:
            return fn(*a, **kw)
        finally:
            _correcting["n"] -= 1

    def _entities(args: Dict[str, Any]) -> set:
        return {str(v).lower() for k, v in (args or {}).items()
                if k in ("name", "vm_name", "new_name", "target", "net_name")
                and isinstance(v, str) and v}

    def _already_done_this_run(name: str, args: Dict[str, Any]) -> bool:
        """This exact call already SUCCEEDED in this run and nothing has touched its
        entities since — so running it again cannot change the world.

        A re-plan re-emits steps that already ran, and the state reader can only catch the
        ones it can parse; a step the MODEL phrased ("move blue1 to the new network")
        refers to its network by adjective and is unreadable by construction. The ledger
        does not have that problem — it records what was actually called. Bounded by
        invalidation: any later successful MUTATION touching the same entities means state
        may have moved on, so the call is allowed through. Observations are never
        suppressed; re-reading moving state is legitimate."""
        if name in _OBSERVER_TOOLS:
            return False
        ents, last = _entities(args), -1
        for i, e in enumerate(ledger):
            if e.get("tool") == name and e.get("args") == args and e.get("ok"):
                last = i
        if last < 0:
            return False
        for e in ledger[last + 1:]:
            if e.get("ok") and e.get("tool") not in _OBSERVER_TOOLS and _entities(e.get("args") or {}) & ents:
                return False              # something moved since; do it again
        return True

    def _strip_purpose(goal: str) -> str:
        """The goal without its trailing purpose phrase — "…for the red VMs", "…so the blue
        ones can talk". What remains is what the step actually does."""
        return re.split(r"\b(?:for|so that|so|to be used by|intended for|meant for)\b",
                        goal or "", maxsplit=1, flags=re.I)[0]

    def _touched(mark: int, node: Optional[Dict[str, Any]] = None) -> set:
        """The distinct entities this node's subtree accounted for.

        Two sources, because a call is not the only evidence an entity was handled:
          • the LEDGER slice this node produced — entities it actually acted on;
          • its `already`-satisfied children — steps that made no call precisely BECAUSE
            live state already showed their effect.

        The second source is not a concession, it is the stronger evidence: `already` is
        read off the world, whereas a ledger entry only says a call returned success.
        Omitting it made two correct mechanisms cancel each other out — the
        already-satisfied pre-emption erases exactly the ledger rows the group audit
        demands, so on any re-plan "create 5 vms" closed with all five children `done`
        and was still refused `set_goal_uncovered`. That refusal drove another re-plan,
        which was pre-empted again, until the step budget ran out and starved the final
        assurance clause. Measured on ladder rung 4: 17 calls/done became 35/partial.
        """
        seen = set()
        for e in ledger[mark:]:
            for k in ("name", "vm_name", "new_name", "target"):
                v = (e.get("args") or {}).get(k)
                if isinstance(v, str) and v:
                    seen.add(v.lower())
        for kid in ((node or {}).get("children") or []):
            if kid.get("status") == "done" and kid.get("satisfied") == "already":
                # One satisfied child = one entity accounted for. Keyed by the child's
                # goal, which is distinct per member for harness-minted steps and needs
                # no entity vocabulary to tell members apart.
                seen.add(f"already:{(kid.get('goal') or '').strip().lower()}")
        return seen

    def _group_scoped(mark: int) -> bool:
        """Did this subtree make a call that acts on a GROUP by construction?

        A collective goal is not always served by N per-entity calls: "make sure they all
        ping each other" is one `fleet(label=…, action=ping)`, which addresses every member
        at once. Counting entities in that ledger row finds one group name, or none at all,
        and the group audit then refuses a step that did exactly the right thing.

        The test needs no tool list and no vocabulary — it reads the ARGS the tool was
        actually called with. A call that names a GROUP (`label`) and does NOT name an
        individual (`name`/`vm_name`) is group-scoped: that is `fleet`, and it is not
        `add_label`, which carries both because it labels one VM at a time.
        """
        for e in ledger[mark:]:
            args = e.get("args") or {}
            if args.get("label") and not (args.get("name") or args.get("vm_name")):
                return True
        return False

    def _audit(node: Dict[str, Any], node_goal: str, mark: int) -> Dict[str, Any]:
        """Refuse a `done` the world does not support. A node is judged by its tool call
        succeeding, which leaves the middle of the tree unguarded: "put the red ones
        together on their own network" closed done because create_network succeeded, with
        not one red VM attached, and that false success propagated to a done ROOT.

        Two questions, in order of precision:
          • Can this goal's effect be READ off state? Then it must actually hold. Exact,
            and it covers every step the harness minted, since those are phrased by the
            same canonical grammar the reader parses.
          • Otherwise, is the goal about a GROUP? Then something must have happened to a
            group — at least two distinct entities acted on somewhere in its subtree. This
            asks nothing about WHICH members, so it needs no label vocabulary and cannot
            do the model's reasoning; it can only withhold a claim.
        Only ever downgrades done → unverified, and says nothing about an unreadable,
        non-collective goal."""
        if node.get("status") != "done":
            return node
        if goal_effect is not None:
            holds = goal_effect(node_goal)
            if holds is False:
                node["status"], node["reason"] = "unverified", "goal_effect_unmet"
                return node
            if holds is True:
                return node
        # …but only when the group is what the action ACTS ON. "create a new isolated
        # network FOR THE RED VMS" creates one network and correctly touches no VM — the
        # group names the network's purpose, not its object. Reading that as a group action
        # refuses a step that did exactly the right thing, which sends its parent into an
        # endless re-plan: measured as the entire convergence cost of the partition rung.
        if _SET_VALUED_RE.search(_strip_purpose(node_goal)) \
                and not _group_scoped(mark) and len(_touched(mark, node)) < 2:
            node["status"], node["reason"] = "unverified", "set_goal_uncovered"
        return node

    def _reattempt(node: Dict[str, Any], node_goal: str, depth: int,
                   path: List[str], failed: List[str]) -> Dict[str, Any]:
        """Re-attempt a not-done node — the shared body of the backtrack and revision
        loops. For an AND COMPOSITE, re-resolve ONLY the not-`done` children and re-close;
        completed steps stand, so a NON-IDEMPOTENT step ('create 5 vms') is never redone —
        the fix for the 5→10→15 duplication cascade (re-planning the whole node re-ran every
        clause, minting fresh vms each pass). The corrective remainder IS the un-done children.

        A LEAF (no children) or an OR node (mode='or', children are alternatives not steps)
        keeps the wholesale re-plan: a leaf wants a different approach to the same goal, and
        an OR must re-rank/try its alternatives, not splice them. An unverified AND whose
        children are ALL done re-resolves nothing — a genuine no-op, since re-running
        identical steps can't move a predicate the completed plan already failed (so it stops
        cleanly instead of duplicating work)."""
        kids = node.get("children")
        if not kids or node.get("mode") == "or":
            return _attempt(node_goal, depth, path, True, failed, use_cache=False)
        revised = [c if c.get("status") == "done"
                   else _resolve(c.get("goal"), depth + 1, path + [node_goal])
                   for c in kids]
        extra = {"method": node["method"]} if node.get("method") else {}
        return _close_and(node_goal, depth, revised, **extra)

    def _close_and(node_goal: str, depth: int, children: List[Dict[str, Any]],
                   **extra) -> Dict[str, Any]:
        """AND closure: every child is a REQUIRED step — all must be done, else partial.
        (all-done is necessary but, at the root, not sufficient — the predicate decides.)"""
        if not all(c.get("status") == "done" for c in children):
            return _node(node_goal, "partial", children=children, **extra)
        return _root_gate(node_goal, depth, children, extra)

    def _rank_alternatives(opts: List[str], depth: int) -> tuple:
        """WORTH-IT ordering + pruning for OR alternatives (gauntlet C/F). Price each
        alternative's CE (estimate → pre-execution guess from the tool it'd use), TRY
        the highest-CE first, and PRUNE any whose CE ≤ θ (the worth-it floor) — those
        are booked as forgone, never executed. Returns (to_try, pruned) as lists of
        (option, ce). No estimator → keep the model's given order, prune nothing (the
        act-observe-correct default)."""
        if estimate is None:
            return [(o, None) for o in opts], []
        scored = [(o, estimate(o, depth)) for o in opts]
        priced   = [(o, s) for o, s in scored if s is not None]
        unpriced = [(o, None) for o, s in scored if s is None]   # couldn't price → don't prune it
        keep   = sorted([(o, s) for o, s in priced if s > ce_floor], key=lambda x: x[1], reverse=True)
        pruned = [(o, s) for o, s in priced if s <= ce_floor]
        return keep + unpriced, pruned            # priced-best-first, then unpriced in order

    def _close_or(node_goal: str, depth: int, children: List[Dict[str, Any]],
                  satisfied: bool, **extra) -> Dict[str, Any]:
        """OR closure: children are ALTERNATIVES to the same goal — ONE done is enough.
        `satisfied` says an alternative succeeded; none → failed (a soft failure that
        backtracks). Carries mode='or' so the economics prices it as max-over-alts."""
        if not satisfied:
            return _node(node_goal, "failed", children=children, mode="or", **extra)
        return _root_gate(node_goal, depth, children, {"mode": "or", **extra})

    def _resolve(node_goal: str, depth: int, path: List[str],
                 best_alt: float = 0.0) -> Dict[str, Any]:
        _emit("enter", node_goal, depth, path)
        node = _resolve_inner(node_goal, depth, path, best_alt)
        _emit("close", node_goal, depth, path, status=node.get("status"),
              reason=node.get("reason"), revised=node.get("revised"))
        return node

    def _resolve_inner(node_goal: str, depth: int, path: List[str],
                       best_alt: float = 0.0) -> Dict[str, Any]:
        # WHOLE-GOAL WORTH-IT GATE (gauntlet F, top level): before touching the ROOT
        # goal, price it and refuse up-front if it isn't worth doing — the go/no-go the
        # OR gate already applies to alternatives, lifted to the whole goal. ROOT only
        # (depth 0): AND sub-steps are REQUIRED (you can't skip one and still claim the
        # goal), so only the whole goal and OR-alternatives carry a worth-it gate.
        # Unpriceable (no estimator, or a compound route the estimator won't cost at
        # α=0) → proceed, the act-observe-correct default. Books no reward and executes
        # nothing — the gate legitimately choosing inaction, surfaced not silently done.
        # Opt-in (whole_goal_gate): the autonomous driver turns it on; run_score's OR /
        # backtrack unit tests leave it off so their stub estimators aren't pre-empted.
        if whole_goal_gate and depth == 0 and estimate is not None:
            root_ce = estimate(node_goal, depth)
            if root_ce is not None and root_ce <= ce_floor:
                return _node(node_goal, "skipped", mode="whole_goal",
                             reason="not_worth_it", ce_est=round(root_ce, 4))
        # BACKTRACK: attempt the goal; on a SOFT failure (failed / unverified),
        # re-attempt with a DIFFERENT approach, feeding the model the approaches that
        # already failed HERE so it can't repeat them. Hard stops (done / skipped /
        # no_action / blocked, incl. contract_halt) never backtrack; and because we
        # retry the failing node itself (not its parent), succeeded siblings stand.
        #
        # CE-BASED ABANDON (gauntlet F): don't retry to the budget blindly — ABANDON as
        # soon as a fresh attempt is worth no more than the opportunity cost. Continue-
        # value = estimate(goal) − H·(retries so far): each wasted try raises the bar by
        # the holding cost, so a marginal goal is dropped early while a high-CE one keeps
        # its full budget. The floor is max(0, best_alt): 0 = the always-free do-nothing
        # option; best_alt = the next-best alternative's CE (passed by an OR parent), so
        # a failing alternative is abandoned in favour of a better sibling. No estimator
        # → the plain max_retries budget (backward compatible).
        floor = max(0.0, best_alt)
        failed: List[str] = []
        mark  = len(ledger)
        node  = _audit(_attempt(node_goal, depth, path, True, failed), node_goal, mark)
        tries = rolled = 0
        while node.get("status") in _RETRY_STATUS and tries < max_retries:
            # A fully-executed composite that closed `unverified` (every REQUIRED step done,
            # yet the ROOT predicate still rejects the result) cannot be helped by re-running
            # the SAME plan — identical steps yield an identical predicate, and re-running a
            # non-idempotent step ('create 5 vms') only DUPLICATES work (the 5→10→15 cascade).
            # It's an honest terminal miss, not a soft failure: stop retrying.
            if node.get("children") and node.get("mode") != "or" \
                    and all(c.get("status") == "done" for c in node["children"]):
                break
            give_up = False
            cont = None
            if estimate is not None:
                cont = estimate(node_goal, depth)
                if cont is not None:
                    cont -= retry_penalty * tries
                    give_up = cont <= floor
            # Rollback-on-backtrack: if the failed attempt was gate-checkpointed
            # (an autonomous destructive leaf), UNDO its side effects — restore the
            # savepoint and drop its now-stale ledger records — so the next step (retry
            # OR abandon) starts from clean state. Non-checkpointed leaves have nothing
            # to undo.
            if node.get("checkpoint"):
                execute("rollback", {"label": node["checkpoint"]})
                del ledger[mark:]
                rolled += 1
            if give_up:
                node["abandoned"] = True
                node["abandon"] = {"continue_ce": round(cont, 4), "floor": round(floor, 4)}
                break
            failed.append(_approach_desc(node))
            tries += 1
            # Backtrack is for LEAVES and OR nodes (a soft failure wanting a different
            # approach) — AND composites broke out above. A re-attempt SKIPS the method
            # cache: the cached decomposition is exactly the one that just failed (the
            # root-replan landmine), so re-planning must reach the model.
            node = _audit(_correct(_attempt, node_goal, depth, path, True, failed, use_cache=False),
                          node_goal, mark)
        if tries:
            node["retries"] = tries
            node["tried"]   = list(failed)
            if rolled:
                node["rolled_back"] = rolled
            if node.get("status") == "done":
                node["recovered"] = True

        # ROLLBACK POLICY, stated deliberately (it is a decision, not an omission): a
        # REVISION DOES NOT ROLL BACK. Backtrack does — it retries the SAME goal, so a
        # checkpointed destructive leaf must not retry from dirty state. Revision is the
        # opposite move: it keeps what worked and corrects the remainder, and targeted
        # revision is BUILT on completed children standing (undoing them is the 5→10→15
        # duplication cascade). Per-leaf undo still happens where it belongs — inside the
        # failing leaf's own backtrack loop above — so a checkpointed leaf is already clean
        # by the time its parent revises. What carries forward is on the record: `tried`
        # holds the post-mortem, and pre-empted steps are marked satisfied="already".
        #
        # PLAN-LEVEL REVISION (self-correction): an AND plan that came up `partial` — a
        # REQUIRED step failed for good — is not a dead branch. Re-PLAN the goal: the
        # model sees what's already done (progress summary, injected in _attempt) plus a
        # post-mortem of which steps failed, so it produces the CORRECTIVE remainder
        # rather than repeating the decomposition that fell short. Distinct from the leaf
        # backtrack above (same sub-goal, new approach) — this regenerates the PLAN. OR
        # nodes already re-plan via backtrack (a failed OR is a soft failure); leaves
        # can't be re-planned. Re-attempts skip the cache (same landmine). Off unless
        # max_revisions > 0 (the autonomous driver turns it on; run_score defaults off).
        revisions = 0
        while max_revisions and revisions < max_revisions and node.get("children"):
            # TWO correctable shapes, not one:
            #  • `partial` — a REQUIRED step failed; the corrective remainder is the
            #    un-done children (targeted revision handles it).
            #  • `unverified` — every step ran and the goal predicate STILL rejects the
            #    result. This used to be terminal, which had it backwards: it is the case
            #    with the MOST information (the predicate says exactly what is wrong), and
            #    the honesty rule produces it precisely when the agent knows it failed.
            #    Targeted revision is a no-op here (nothing is un-done), so it goes
            #    straight to a wholesale re-plan carrying the predicate's objection.
            status = node.get("status")
            unmet = (status == "unverified" and node.get("mode") != "or"
                     and all(c.get("status") == "done" for c in node["children"]))
            if status != "partial" and not unmet:
                break
            # WORTH-IT (the same discipline backtrack applies): a re-plan is the most
            # expensive move in the system, and it was the only loop here charging nothing
            # for it. Continue-value = estimate(goal) − H·(attempts so far); at or below the
            # floor, stop and keep the honest verdict instead of buying another pass.
            if estimate is not None:
                cont = estimate(node_goal, depth)
                if cont is not None:
                    cont -= retry_penalty * (tries + revisions)
                    if cont <= floor:
                        node["revision_abandoned"] = {"continue_ce": round(cont, 4),
                                                      "floor": round(floor, 4)}
                        break
            if unmet:
                complaint = goal_complaint(node_goal, node["children"], ledger) if goal_complaint else ""
                failed.append(_unmet_desc(node, complaint))
            else:
                failed.append(_plan_desc(node))
            revisions += 1
            if unmet:                      # nothing un-done to target — re-plan wholesale
                node = _audit(_correct(_attempt, node_goal, depth, path, True, failed, use_cache=False),
                              node_goal, mark)
                continue
            # TARGETED first: re-resolve only the not-done children (the corrective
            # remainder), leaving completed steps untouched — so a non-idempotent step that
            # already ran ('create 5 vms') is never redone. Often enough on its own: a step
            # that failed for a now-satisfied prerequisite (attach before the net existed)
            # succeeds on a clean second try.
            node = _audit(_correct(_reattempt, node, node_goal, depth, path, failed), node_goal, mark)
            # ESCALATE only if the same sub-goals still can't close the plan — then the
            # DECOMPOSITION itself was wrong, so re-plan wholesale and let the model choose
            # DIFFERENT steps (swap a broken tool for a fallback). This is the one path that
            # may re-touch done steps; it fires only when targeted correction was insufficient.
            if node.get("status") == "partial":
                node = _audit(_correct(_attempt, node_goal, depth, path, True, failed, use_cache=False),
                              node_goal, mark)
        if revisions:
            node["revisions"] = revisions
            # ON THE RECORD: what the re-plan was told (failed steps, or the predicate's
            # objection). Backtrack already records its `tried` list; revision fed the same
            # post-mortem to the model and then dropped it, so an operator reading the tree
            # could see THAT a plan was revised but never WHY.
            node["tried"] = list(failed)
            if node.get("status") == "done":
                node["revised"] = True
        return node

    def _guard(name, args, node_goal, depth=0, path=()):
        """May this call proceed? THE one authority, for leaves and for programs alike.

        Returns (action, info):
          "refuse"  info carries the node fields explaining why — a red line, a denied
                    referendum, a throttle, a tripped killswitch, an unworthy commit.
          "skip"    the effect is already in place (a known finding, or this exact call
                    already made this run). Not a failure: doing it again is the waste.
          "proceed" info carries the savepoint label and the stated rationale.

        EXTRACTED so a MEDUSA program's calls meet the same gauntlet a leaf does. The
        design note is explicit that "the program body is NOT a trusted region" — a
        `delete_vm` inside a program must meet the double confirmation it meets in chat.
        The alternative was to repeat this sequence at the program seam, which is how two
        security paths diverge: one of them gets a fix and the other does not.
        """
        # LEGAL FILTER (gauntlet A): a hard, categorical red line — dropped up front,
        # never costed, never surfaced. Distinct from the destructiveness/consent axis.
        if legal_filter and legal_filter(name, args):
            return "refuse", {"status": "forbidden", "reason": "legal_red_line"}

        # Anti-rediscovery (Findings ledger): if this call's finding is already
        # known, don't re-run the tool that would learn it — return the cached fact.
        fact = _yield_fact(name, args, findings_schema) if (findings is not None and findings_schema) else None
        if fact and findings.has(fact):
            return "skip", {"cached_finding": fact,
                            "result": {"finding": fact, "value": findings.get(fact),
                                       "cached": True}}

        # SIMULATED ĈE COMMIT GATE (deliberation scales with irreversibility): a
        # REVERSIBLE leaf just acts — reality is a free act-observe-correct oracle, no
        # simulation. An IRREVERSIBLE leaf commits only if its SIMULATED certainty-
        # equivalent clears the worth-it bar; otherwise it's blocked here, before any
        # savepoint or execution. Distinct from the whole-goal gate (prices the GOAL) and
        # the checkpoint path (revertibility): this is the per-leaf irreversible go/no-go.
        # commit_gate returns True for reversible/unknown risk (the default when unset).
        if commit_gate is not None and not commit_gate(name, args):
            return "refuse", {"status": "blocked", "reason": "not_worth_committing"}

        # REASON-VALIDATION GATE (two-stage, opt-in): capture the model's stated REASON for
        # this action, then check the ACTION against it as a spec — STRUCTURAL, not a
        # model-judge (the p_self firewall). Flags clear divergence (no reason; the target
        # absent from the justification; or — grounded — a reason that CONTRADICTS the live
        # state). The stated reason is RECORDED on the leaf (rationale) and streamed to the
        # live tree, so even a passed lie stays auditable after the run.
        rationale = None
        if reason_gate is not None:
            rg = reason_gate(node_goal, name, args)
            problem   = rg.get("problem") if isinstance(rg, dict) else rg
            rationale = rg.get("reason")  if isinstance(rg, dict) else None
            if problem:
                return "refuse", {"status": "blocked", "rationale": rationale,
                                  "reason": f"reason_mismatch:{problem}"}
        _rat = {"rationale": rationale} if rationale else {}

        if _already_done_this_run(name, args):
            _emit("leaf", node_goal, depth, path, tool=name, args=args, repeat="suppressed")
            return "skip", {"repeat": "already_done", **_rat}

        act = gate(name, args) if gate else "proceed"
        checkpoint_label = None
        if act == "halt":
            # CONSENT SURFACE (gauntlet D): destructive-but-legal → a referendum WITH
            # its consequence. Granted → proceed (kept revertible via checkpoint);
            # denied, or no referendum handler → blocked. (Was a categorical halt.)
            if referendum and referendum(name, args, _consent_verb(name)):
                act = "checkpoint"
            else:
                return "refuse", {"status": "blocked",
                                  "reason": "consent_denied" if referendum else "contract_halt"}
        if act == "checkpoint":
            checkpoint_label = f"pre_{name}_{len(ledger)}"
            cp    = execute("checkpoint", {"label": checkpoint_label})
            cp_ok = not (isinstance(cp, dict) and (cp.get("success") is False or cp.get("error")))
            ledger.append({"goal": node_goal, "tool": "checkpoint", "args": {"label": checkpoint_label},
                           "ok": cp_ok, "result": cp})
            if not cp_ok:               # can't make it revertible → don't do the irreversible thing
                return "refuse", {"status": "blocked", "reason": "checkpoint_failed"}

        # WATCHDOG (farming/loop): a signature throttled for zero-progress repetition
        # is blocked (reversibly) — the deterministic backstop once the tree acts.
        if watchdog is not None and watchdog.throttled(name, args):
            return "refuse", {"status": "blocked", "reason": "watchdog_throttle"}

        # Kill-switch may have tripped during planning — check once more before we ACT.
        if killswitch is not None and killswitch.tripped:
            return "refuse", {"status": "aborted", "reason": killswitch.reason}
        return "proceed", {"checkpoint": checkpoint_label, "rationale": rationale,
                           "fact": fact}

    def _attempt(node_goal: str, depth: int, path: List[str],
                 allow_decompose: bool, failed: List[str],
                 use_cache: bool = True) -> Dict[str, Any]:
        # SAFEWORD KILL-SWITCH (infrastructural): if the operator tripped it, stop the
        # tree HERE — no planning, no execution. The agent gets no say; the ledger so
        # far is preserved (suspend, not delete).
        if killswitch is not None and killswitch.tripped:
            return _node(node_goal, "aborted", reason=killswitch.reason)
        # THRASHING BOUND (Track 1.5): count every node attempt.
        # (Tried and REVERTED 2026-07-25: refunding the bound for FREE closures — an
        # already-satisfied goal, a suppressed repeat — on the reasoning that a node
        # costing no model call is not planning. Sound in principle, measurably worse in
        # practice: on the partition rung it bought the run more room without converging,
        # so it spent 106 model calls instead of 71 to reach the same `blocked`. The budget
        # is not what stops that rung — convergence is.)
        _budget["n"] += 1
        if max_steps and _budget["n"] > max_steps:
            return _node(node_goal, "blocked", reason="step_budget")
        if killswitch is not None:
            killswitch.checkin()          # a sign of life — resets any armed dead-man's timer
        # DON'T REDO FINISHED WORK WHILE CORRECTING. A wholesale re-plan may re-emit steps
        # that already succeeded — the one path that re-touches done work, and the reason a
        # correction used to cost a second full pass of tool calls. During a correction
        # only, close a step whose effect live state ALREADY shows, with no model call and
        # no tool call. Scoped deliberately: on a FIRST attempt the check needs the model's
        # agreement too (it fires on `no action`, two independent judgements), and this is
        # the one place it acts alone — so it is confined to re-work, where "already done"
        # is precisely the question. `already_satisfied` answers atomic goals only, so a
        # compound node falls through to normal decomposition.
        if _correcting["n"] and already_satisfied is not None and already_satisfied(node_goal):
            _emit("leaf", node_goal, depth, path, tool=None, satisfied="already")
            return _node(node_goal, "done", satisfied="already")
        # COMPOUND DECOMPOSITION (Track 2): a sub-goal that JOINS two actions ("create X AND
        # put X on net") is split into its clauses deterministically — the weak model fuses
        # them and then can't split at depth > 0 (decompose-first is root-only). Runs BEFORE
        # collective, so "create 5 vms and put them all on a net" splits into the two phases
        # first, then each phase collective-expands. Only fires on a real action-conjunction
        # (each clause names a tool), never an atomic goal or noun-conjunction.
        if expand_compound is not None and allow_decompose and depth < max_depth:
            xsteps = expand_compound(node_goal, path)
            if xsteps and len(xsteps) >= 2:
                _emit("plan", node_goal, depth, path, children=list(xsteps), mode="and", method="compound")
                children = [_resolve(s, depth + 1, path + [node_goal]) for s in xsteps]
                return _close_and(node_goal, depth, children, method="compound")
        # COLLECTIVE DECOMPOSITION (Track 1.1): a DISTRIBUTIVE "do X to all/them/each" over a
        # live set is expanded deterministically into one atomic sub-goal per member — the
        # HARNESS does the loop the weak model can't (the benchmark cliff). Runs after the
        # compound split, at any depth, taking precedence over attach-steer/decompose-first so
        # a collective goal is never collapsed to a single action or left to the model to loop.
        if expand_collective is not None and allow_decompose and depth < max_depth:
            csteps = expand_collective(node_goal, path)
            if csteps and len(csteps) >= 2:
                _emit("plan", node_goal, depth, path, children=list(csteps), mode="and", method="collective")
                children = [_resolve(s, depth + 1, path + [node_goal]) for s in csteps]
                return _close_and(node_goal, depth, children, method="collective")
        system = _NODE_SYSTEM
        if build_context:
            ctx = build_context(node_goal, path)
            if ctx:
                system += "\n\n" + ctx
        # Carry-forward: what earlier steps in this plan already produced, so late
        # steps ground references ("launch probe") to the real entity they created.
        prog = _progress_summary(ledger)
        if prog:
            system += "\n\n" + prog
        # Failed-branch memory: on a retry, the approaches already tried at THIS goal.
        if failed:
            system += ("\n\n═══ ALREADY TRIED HERE (failed — take a DIFFERENT approach, do NOT repeat) ═══\n"
                       + "\n".join(f"- {d}" for d in failed))
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": f"Goal: {node_goal}"}]
        base = select_tools(node_goal, tools) if select_tools else list(tools)
        # Ledger-aware: after a network (etc.) was created earlier in THIS plan, steer
        # a node referencing it to ATTACH, not re-create. An attach-to-existing is one
        # primitive, so when steered we drop decompose to stop over-decomposition.
        base, steered = _attach_steer(base, node_goal, ledger, tools)

        offer_decompose = allow_decompose and not steered
        # DECOMPOSE-FIRST scaffolding: force the atomicity question by offering ONLY
        # decompose (primitives off the table), so the model can't dodge a compound
        # goal into a one-shot. 2+ real steps → decompose; 0-1 (collapses to the goal)
        # → atomic, fall through to a primitive. ROOT ONLY (depth 0): forcing it at
        # every level makes the weak model OVER-decompose atomic sub-goals ("create a
        # vm named beta" → "create a vm" + "name it beta" = junk). Sub-goals use the
        # natural primitive-first path, which one-shots atomic goals correctly.
        # (Tried and REVERTED 2026-07-25: extending this to set-valued sub-goals. It
        # reproduced exactly that over-decomposition — "add red2 vms to the cluster" —
        # and lost one group's network entirely. The note above is right.)
        if decompose_first and offer_decompose and depth == 0:
            # METHOD CACHE first: a known goal shape decomposes DETERMINISTICALLY (no
            # model, no variance). Only a novel goal reaches the model, and a good
            # model decomposition is LEARNED back into the cache ("un-reasons over time").
            cached = method_cache.lookup(node_goal) if (method_cache and use_cache) else None
            if cached and len(cached) >= 2:
                _emit("plan", node_goal, depth, path, children=list(cached), mode="and", method="cache")
                children = [_resolve(s, depth + 1, path + [node_goal]) for s in cached]
                return _close_and(node_goal, depth, children, method="cache")
            plan_msgs = messages + [{"role": "user", "content": (
                "PLAN FIRST. Break this goal into the smallest ORDERED list of individual "
                "actions — one tool call each. If it is truly a single action, return just "
                "that one step. Call decompose with the steps.")}]
            pname, pargs = _first_tool_call(call_model(plan_msgs, [DECOMPOSE_TOOL]))
            if pname == "decompose":
                steps = [s for s in (pargs.get("steps") or []) if _norm(s) != _norm(node_goal)]
                steps = _refine_steps(node_goal, steps)           # Track 1.2 ground + 1.4 complete
                if len(steps) >= 2:
                    if method_cache:
                        method_cache.remember(node_goal, steps)   # learn this decomposition
                    _emit("plan", node_goal, depth, path, children=list(steps), mode="and", method="model")
                    children = [_resolve(s, depth + 1, path + [node_goal]) for s in steps]
                    node = _close_and(node_goal, depth, children, method="model")
                    # A method earns DURABILITY by working. `remember` above ran before a
                    # single child executed, so it captured a plan the model PROPOSED;
                    # only a decomposition that actually closed is worth handing to future
                    # runs (the store persists confirmed methods only). This branch is
                    # root-only, which is also the only depth `lookup` is consulted at.
                    if method_cache and depth == 0 and node.get("status") == "done":
                        method_cache.confirm(node_goal)
                    return node
            offer_decompose = False   # atomic (or the model refused) → let it pick a primitive

        # Both meta-tools ride with the primitives when decomposition is allowed:
        # `decompose` (AND, ordered steps) and `alternatives` (OR, one-of).
        # THE THIRD REGIME. `decompose` (AND, ordered steps) and `alternatives` (OR,
        # one-of) have always ridden with the primitives, and WHICH the model picks is the
        # atomicity judgment. A program is the third answer, for a goal whose shape is a
        # SET, an ORDERING and a POSTCONDITION — the case neither of the others states.
        # Offered only where it has been wired, so programs are off by default.
        offered = base + ([DECOMPOSE_TOOL, ALTERNATIVES_TOOL] if offer_decompose else [])
        if program_tool and run_program and offer_decompose:
            offered = offered + [program_tool]
        name, args = _first_tool_call(call_model(messages, offered))

        if name is None:
            # The model declined to act. That's a FAILURE only if something was left to do.
            # On an idempotent re-entry — a revision re-running a step whose effect is
            # already in place — making no call is the CORRECT answer, and scoring it
            # `no_action` poisons the enclosing composite to `partial` permanently: it can
            # never close, so revision re-runs it, and it declines again. Ask live state
            # (never the model's say-so): if the effect already holds, this leaf is done.
            if already_satisfied is not None and already_satisfied(node_goal):
                _emit("leaf", node_goal, depth, path, tool=None, satisfied="already")
                return _node(node_goal, "done", satisfied="already")
            return _node(node_goal, "no_action")

        if program_tool and run_program and name == program_tool.get(
                "function", {}).get("name"):
            # A program's statements reach the world through `_guard` and nothing else —
            # the same gauntlet a leaf meets, so the design note's "the program body is
            # NOT a trusted region" is enforced rather than asserted. A `delete_vm` inside
            # a program meets the double confirmation it meets in chat.
            def _call(tool: str, tool_args: Dict[str, Any]):
                action, info = _guard(tool, tool_args, node_goal, depth, path)
                if action == "refuse":
                    ledger.append({"goal": node_goal, "tool": tool, "args": tool_args,
                                   "ok": False, "result": {"blocked": info.get("reason")}})
                    return {"success": False, "error": info.get("reason", "refused")}
                if action == "skip":
                    return {"success": True, **{k: v for k, v in info.items()
                                                if k != "rationale"}}
                result = execute(tool, tool_args)
                ok_call = not (isinstance(result, dict)
                               and (result.get("success") is False or result.get("error")))
                # The run's own record, and the epistemic one. Without these a program's
                # calls would be invisible to p_world and to anti-rediscovery — which is
                # the whole reason for wiring this, not a side effect of it.
                ledger.append({"goal": node_goal, "tool": tool, "args": tool_args,
                               "ok": ok_call, "result": result})
                fact_key = info.get("fact")
                if ok_call and fact_key and findings is not None and findings_schema:
                    findings.record(fact_key,
                                    _extract_value(result, findings_schema[tool]),
                                    source=tool)
                return result

            def _reauthor(_program, reasons):
                """Ask the SAME model the same question, with the gate's objections.

                The author is re-asked rather than repaired by the harness, because the
                gate's objections are about what the program MEANS — a name the operator
                gave and the program never mentions, a goal with nothing that states when
                it is done — and none of those has a mechanical fix. `derive()` exists for
                the ones that do.

                Returns None when the model declines or answers with something that is not
                a program, which `clarify()` reads as STALE: an author with no answer is
                as stuck as one repeating itself, and pretending otherwise would spend the
                remaining rounds discovering it again.
                """
                again = messages + [
                    {"role": "assistant", "content": json.dumps(_program)},
                    {"role": "user", "content":
                     "That program was NOT run. Before anything happened, it was held "
                     "back for these reasons:\n"
                     + "\n".join(f"  - {r}" for r in reasons)
                     + f"\n\nThe goal was: {node_goal}\n"
                     "Write the whole program again, answering exactly those objections. "
                     "Nothing has run — the world is untouched."}]
                nm, na = _first_tool_call(call_model(again, [program_tool]))
                if nm != program_tool.get("function", {}).get("name"):
                    return None
                return na

            outcome = run_program(args, node_goal, _call, _reauthor)
            if not outcome or outcome.get("invalid"):
                # An unusable program is CHEAP: fall back to a primitive, exactly as a
                # non-progressing decomposition does. The regime being wrong costs one
                # re-ask; the path that works today is still there.
                _emit("plan", node_goal, depth, path, mode="program",
                      rejected=(outcome or {}).get("problems", ["no program"])[:3])
                if allow_decompose:
                    return _attempt(node_goal, depth, path, False, failed, use_cache)
                return _node(node_goal, "blocked", reason="invalid_program")
            _emit("plan", node_goal, depth, path, mode="program",
                  children=outcome.get("rendered", "").splitlines() or None)
            # A program's VERDICT is its own ENSURE/ACHIEVE — the language's soundness rule
            # decides this node, not the call count. `unverified` where it acted and
            # vouched for nothing, so the closure audit still has something to refuse.
            if outcome.get("ok"):
                status = "done" if outcome.get("asserted") else "unverified"
            else:
                status = "partial"
            return _node(node_goal, status, mode="program",
                         calls=len(outcome.get("calls") or []),
                         reason=outcome.get("failed"), why=outcome.get("why"))

        if name == "decompose":
            # Drop non-progressing steps — the weak model often "decomposes" an atomic
            # goal into itself. If nothing progresses (or we're too deep), re-ask WITHOUT
            # the meta-tools so the model MUST pick a primitive (the progress guard).
            steps = [s for s in (args.get("steps") or []) if _norm(s) != _norm(node_goal)]
            steps = _refine_steps(node_goal, steps)               # Track 1.2 ground + 1.4 complete
            if not steps or depth >= max_depth:
                if allow_decompose:
                    return _attempt(node_goal, depth, path, False, failed, use_cache)
                return _node(node_goal, "blocked", reason="no_progress")
            if method_cache:
                method_cache.remember(node_goal, steps)   # learn it here too — this is the
            # path a decomposition takes whenever plan-first didn't yield (and at every
            # depth > 0), so without this the cache only ever sees root plan-first goals.
            _emit("plan", node_goal, depth, path, children=list(steps), mode="and", method="model")
            children = [_resolve(s, depth + 1, path + [node_goal]) for s in steps]
            node = _close_and(node_goal, depth, children, method="model")
            # DURABLE only at the ROOT. Lookup happens at depth 0, so a sub-goal method
            # could never be reused — persisting them would just crowd the capped store and
            # evict the root shapes that DO recur across runs. In-run learning still
            # happens at every depth; it simply doesn't outlive the process.
            if method_cache and depth == 0 and node.get("status") == "done":
                method_cache.confirm(node_goal)
            return node

        if name == "alternatives":
            # OR goal: try each alternative in order, STOP at the first that's done, and
            # mark the untried rest `skipped` (they were never needed). A failed
            # alternative that took a savepoint is ROLLED BACK before the next one, so
            # each alternative starts from clean state (same discipline as backtrack).
            opts = [o for o in (args.get("options") or []) if _norm(o) != _norm(node_goal)]
            if len(opts) < 2 or depth >= max_depth:   # not real alternatives → force a primitive
                if allow_decompose:
                    return _attempt(node_goal, depth, path, False, failed, use_cache)
                return _node(node_goal, "blocked", reason="no_alternatives")
            # WORTH-IT: rank by CE, try best first, and prune the alternatives not worth trying.
            to_try, pruned = _rank_alternatives(opts, depth + 1)
            pruned_nodes = [_node(o, "skipped", reason="pruned_low_ce",
                                  ce_est=round(s, 4)) for o, s in pruned]
            if not to_try:
                # every alternative is below the worth-it floor → don't pursue this goal
                # (the gate legitimately choosing inaction; surfaced, not silently done).
                return _node(node_goal, "skipped", children=pruned_nodes, mode="or",
                             reason="not_worth_it")
            _emit("plan", node_goal, depth, path, mode="or",
                  children=[o for o, _ in to_try] + [o for o, _ in pruned])
            children: List[Dict[str, Any]] = []
            satisfied = False
            for i, (opt, est) in enumerate(to_try):
                mark = len(ledger)
                # Opportunity cost for abandoning this alternative's retries = the CE of
                # the next-best alternative still to try (0 if it's the last one).
                nxt = to_try[i + 1][1] if i + 1 < len(to_try) else None
                best_alt = float(nxt) if isinstance(nxt, (int, float)) else 0.0
                child = _resolve(opt, depth + 1, path + [node_goal], best_alt=best_alt)
                if est is not None:
                    child["ce_est"] = round(est, 4)
                children.append(child)
                if child.get("status") == "done":
                    satisfied = True
                    children += [_node(o, "skipped", reason="alt_satisfied") for o, _ in to_try[i + 1:]]
                    break
                # this alternative failed — undo any savepoint residue before the next
                cps = [e for e in ledger[mark:] if e.get("tool") == "checkpoint"]
                if cps:
                    execute("rollback", {"label": cps[0]["args"]["label"]})
                    del ledger[mark:]
            children += pruned_nodes
            return _close_or(node_goal, depth, children, satisfied)

        # A primitive → a leaf. The active agent's CONTRACT bounds what the tree may
        # do here: gate() maps the tool's risk tier through the agent's disposition.
        # HALT is a red line the tree cannot cross (blocked, never executed) — so
        # dynamic replanning can't escape the contract. CHECKPOINT takes a savepoint
        # FIRST, so a destructive-but-authorized leaf stays revertible (the
        # autonomous act-observe-correct default).
        action, info = _guard(name, args, node_goal, depth, path)
        if action == "refuse":
            return _node(node_goal, info["status"], tool=name, args=args,
                         **{k: v for k, v in info.items() if k != "status"})
        if action == "skip":
            return _node(node_goal, "done", tool=name, args=args, **info)
        checkpoint_label, rationale, fact = (info["checkpoint"], info["rationale"],
                                             info["fact"])
        _rat = {"rationale": rationale} if rationale else {}
        _cp = {"checkpoint": checkpoint_label} if checkpoint_label else {}

        _emit("leaf", node_goal, depth, path, tool=name, args=args, rationale=rationale)
        result = execute(name, args)
        ok = not (isinstance(result, dict) and (result.get("success") is False or result.get("error")))

        # Record what this call LEARNED into the Findings ledger (its epistemic
        # result), so acceptance can read it and the loop won't re-discover it.
        new_finding = bool(fact) and (findings is not None) and not findings.has(fact)
        if ok and fact:
            # Deterministic finding-validation: if the schema declares a `verify`
            # probe for this finding, an independent read-only guest_probe must
            # CONFIRM it before it's recorded. A value read from (possibly free-text)
            # output that a probe can't back up doesn't count — closes the "trust the
            # extracted value" hole. No `verify` → records as before.
            _confirmed = True
            _vspec = _finding_probe_spec(name, args, findings_schema)
            if _vspec:
                _p = _vspec.split(":", 3)             # vm:assertion:target[:value]
                if len(_p) >= 3 and all(_p[:3]):
                    _pargs = {"name": _p[0], "assertion": _p[1], "target": _p[2]}
                    if len(_p) == 4 and _p[3]:
                        _pargs["value"] = _p[3]
                    _pr = execute("guest_probe", _pargs)
                    _confirmed = isinstance(_pr, dict) and _pr.get("success") and bool(_pr.get("holds"))
                else:
                    _confirmed = False
            if _confirmed:
                # An unverified claim carries `evidence` (the operator's note on where
                # they found it) through the result — preserve it on the ledger entry
                # so a human can check what no probe could.
                _ev = result.get("evidence") if isinstance(result, dict) else None
                findings.record(fact, _extract_value(result, findings_schema[name]),
                                source=name, evidence=_ev)
            else:
                new_finding = False   # unconfirmed → not learned; don't credit anti-rediscovery
        # Staleness fix: a state-mutating call (a tool the contract assessed as risky)
        # invalidates findings ABOUT the entities it touched, so anti-rediscovery can't
        # hand back a stale fact after the world changed under it.
        if ok and fact is None and findings is not None and _tool_risk(name):
            for v in (args or {}).values():
                if isinstance(v, str):
                    findings.invalidate_about(v)
        if watchdog is not None:
            watchdog.observe(name, args, new_finding=new_finding, result=result)

        # Verified completion: a leaf is DONE only if the contract's success
        # criterion actually holds in reality — not just because execute returned
        # success. The contract declares the criterion (criterion_of); `verify`
        # checks it against ground truth. A criterion that fails → `unverified`.
        if ok and verify and criterion_of:
            crit = criterion_of(name)
            if crit and not verify(crit, name, args, result):
                ledger.append({"goal": node_goal, "tool": name, "args": args,
                               "ok": False, "verified": False, "result": result})
                return _node(node_goal, "unverified", tool=name, args=args,
                             result=result, reason=f"criterion_unmet:{crit}", **_cp, **_rat)

        # Honesty rule (foreign-command grounding): an OPAQUE command with no declared
        # post-condition can't be trusted on its exit flag — surface it as UNVERIFIABLE,
        # never silently `done`. It books no reward until a criterion or probe confirms
        # the effect. (If the contract DID declare a criterion, the block above verified
        # it, so criterion_of(name) is truthy here and this doesn't fire.)
        if ok and name in _OPAQUE_TOOLS and not (criterion_of and criterion_of(name)):
            ledger.append({"goal": node_goal, "tool": name, "args": args,
                           "ok": False, "verified": False, "result": result})
            return _node(node_goal, "unverified", tool=name, args=args,
                         result=result, reason="unverifiable", **_cp, **_rat)

        ledger.append({"goal": node_goal, "tool": name, "args": args, "ok": ok, "result": result})
        return _node(node_goal, "done" if ok else "failed", tool=name, args=args, result=result, **_cp, **_rat)

    root = _resolve(goal, 0, [])
    return {"root": root, "ledger": ledger, "ok": root.get("status") == "done"}
