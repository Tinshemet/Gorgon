"""
engine.py — the Engine: one bundle for the planner's policy dependencies.

`run_score` grew ~18 parameters as the reward-cost brain landed (gate, verify,
criterion_of, legal_filter, referendum, watchdog, findings, method_cache, …). That
is real debt: hard to read, hard to thread, easy to mis-wire. The Engine collects the
POLICY deps into one object so `run_score(goal, engine=…)` stays legible and
run_autonomous constructs the bundle once.

Only the POLICY deps live here. The three CORE deps a run can't run without —
`call_model`, `execute`, `tools` — stay explicit on run_score, as do the plan LIMITS
(max_retries/max_depth) and the two grounding hooks (build_context/select_tools).

(The old `is_destructive`/`confirm` backstop is retired — it was superseded by the
split gate: the legal filter (A) + the consent referendum (D).)
"""
from dataclasses import dataclass, fields
from typing import Any, Callable, Dict, Optional


@dataclass
class Engine:
    gate:            Optional[Callable[[str, Dict], str]] = None            # contract → handling action
    verify:          Optional[Callable[[str, str, Dict, Any], bool]] = None  # verified-completion check (leaf)
    verify_goal:     Optional[Callable[[str, list, list], Optional[bool]]] = None  # contract ROOT predicate
    criterion_of:    Optional[Callable[[str], Optional[str]]] = None        # per-tool success criterion
    legal_filter:    Optional[Callable[[str, Dict], bool]] = None           # hard red line (gauntlet A)
    referendum:      Optional[Callable[[str, Dict, str], bool]] = None      # consent surface (gauntlet D)
    watchdog:        Any = None                                             # farming/loop monitor
    killswitch:      Any = None                                             # safeword abort (infrastructural)
    findings:        Any = None                                             # Findings ledger
    findings_schema: Optional[Dict[str, Dict[str, str]]] = None             # per-tool yield-schema
    method_cache:    Any = None                                             # decomposition cache
    decompose_first: bool = False                                           # force the atomicity pre-gate
    estimate:        Optional[Callable[[str, int], Optional[float]]] = None  # per-alternative CE estimate (OR ordering/pruning)
    ce_floor:        float = 0.0                                            # worth-it threshold θ — prune alts with CE ≤ this
    retry_penalty:   float = 0.0                                            # holding cost H per wasted retry (CE-based backtrack-abandon)
    whole_goal_gate: bool = False                                           # refuse the ROOT goal up-front if its priced CE ≤ ce_floor
    max_revisions:   int = 0                                                # plan-level self-correction: re-plan a partial composite this many times
    commit_gate:     Optional[Callable[[str, Dict], bool]] = None           # per-leaf simulated-ĈE gate for IRREVERSIBLE commits (deliberation scales with irreversibility)
    reason_gate:     Optional[Callable[[str, str, Dict], Optional[str]]] = None  # (goal,tool,args)→problem tag|None: validate the action against its stated reason
    on_node:         Optional[Callable[[Dict], None]] = None                    # live node-lifecycle events (enter/plan/leaf/close) for a streaming tree view
    expand_compound: Optional[Callable[[str, list], Optional[list]]] = None     # split a "do X and do Y" sub-goal into its action clauses (Track 2)
    expand_collective: Optional[Callable[[str, list], Optional[list]]] = None   # deterministically expand a distributive "do X to all/them" sub-goal into per-member steps
    ground_steps:    Optional[Callable[[str, list], list]] = None               # bind bare entity references in decomposed steps to the parent's named entity
    complete_steps:  Optional[Callable[[str, list], list]] = None               # inject a missing prerequisite (e.g. create the network a step attaches to)
    already_satisfied: Optional[Callable[[str], bool]] = None                   # (goal)→bool: live state already shows this leaf's effect, so "no tool call" is correct, not a failure
    goal_effect:     Optional[Callable[[str], Optional[bool]]] = None           # (goal)→True/False/None: does live state show THIS goal's effect? None = unreadable, no opinion
    goal_complaint:  Optional[Callable[[str, list, list], str]] = None          # (goal,children,ledger)→why the root predicate REJECTED a fully-executed plan, so revision can correct it
    # A MEDUSA program as the third regime, beside a primitive and a decomposition. Both
    # injected, so the engine never imports the language and programs are simply OFF where
    # they are not wired — which is the right default until the regime has been measured
    # in production. `program_tool` is the schema offered at a node; `run_program` takes
    # (args, node_goal, call) and returns the run's result, where `call` is the engine's
    # own guarded executor. It is handed IN rather than taken, so a program's statements
    # cannot reach the world by any path a leaf does not.
    program_tool:    Optional[Dict[str, Any]] = None
    # `run_program` also takes a fourth argument, `reauthor` — the closure the engine
    # builds to re-ask the SAME model with the schema gate's objections. It is keyword-
    # optional rather than part of the type above because a caller with nobody to re-ask
    # is a legitimate configuration: the gate then announces and proceeds instead of
    # suppressing a program it has no way to improve. The gate's OPERATOR surface is
    # injected where run_program is built, not carried here — a field the Engine never
    # reads would be one more thing to keep in step for nothing.
    run_program:     Optional[Callable[[Dict, str, Callable], Dict]] = None

    @classmethod
    def from_kwargs(cls, kw: Dict[str, Any]) -> "Engine":
        """Build an Engine from a loose kwargs dict, ignoring anything not a field
        (a transitional shim so legacy `run_score(gate=…, verify=…)` calls still work)."""
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in kw.items() if k in names})
