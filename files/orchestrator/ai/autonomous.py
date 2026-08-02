"""
autonomous.py — the autonomous execution loop: run an agent to a goal, no human.

This is the driver that actually RUNS the Score tree for an autonomous agent (a
Conductor). Everything the tree needs was built already — this wires it together and
turns it loose: the model proposes, the tree decomposes to primitives, the CONTRACT
gates each leaf (halt a red line / checkpoint a destructive one), a leaf is DONE only
if VERIFIED against reality, a soft-failed branch BACKTRACKS with a different approach,
and a checkpointed dead branch ROLLS BACK first. No human backstop — the agent's
disposition (from its .grgn) drives handling.

Dependency-injected like run_score, so the whole loop is testable with stubs:
  run_autonomous(goal, call_model=…, execute=…, tools=…, vms_getter=…)
and a live convenience that wires the real Ollama + executor + Active Library:
  run_autonomous_live(goal)

The Library-backed `verify` here is what ACTIVATES verified-completion: it evaluates
the contract's per-tool success criterion (present / absent / running / stopped /
restored) against the live VM registry, catching a tool that reports success but didn't
actually change the world.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .planner.score import run_score, _first_tool_call, _NODE_SYSTEM, DECOMPOSE_TOOL
from .agent import contract as _contract
from .planner.method_cache import MethodCache as _MethodCache, seeded as _seeded_cache
from .planner.ir import EMIT_PROGRAM_TOOL as _EMIT_PROGRAM_TOOL
from .planner.program import make_run_program as _make_run_program
from .planner.translator import normalize_goal as _normalize_goal
from .planner.findings import Findings, DEFAULT_SCHEMA
from .planner.reward_cost import (economics as _economics, p_self_estimate as _p_self, dials as _dials,
                          cfg_with as _cfg_with, leaf_cost as _leaf_cost, ce as _ce,
                          tool_counts as _tool_counts, merge_counts as _merge_counts,
                          p_world_estimate as _p_world_estimate, p_world_lookup as _p_world_lookup,
                          compound_ce as _compound_ce, economics_tree as _economics_tree,
                          should_commit as _should_commit)
from .planner.watchdog import Watchdog
from .planner.engine import Engine
from .planner.killswitch import KillSwitch, DeadMansSwitch


def _is_running(rec: Optional[Dict[str, Any]]) -> bool:
    return bool(rec) and "run" in str(rec.get("status", "")).lower()


def _tags(rec: Optional[Dict[str, Any]]) -> set:
    """A VM's tags — labels ∪ flags, the same union `fleets()` groups by."""
    return set((rec or {}).get("labels") or ()) | set((rec or {}).get("flags") or ())


def _criterion_holds(criterion: str, name: Optional[str], vms: Dict[str, Dict[str, Any]],
                     args: Optional[Dict[str, Any]] = None,
                     networks: Optional[Dict[str, set]] = None) -> bool:
    """Does a success criterion hold for `name` against the live registry?

    The shared vocabulary used by BOTH the per-leaf verifier (verified-completion) and
    the goal verifier (the contract root predicate). Unknown criteria pass — never block
    on the uncheckable.

    THE VOCABULARY IS THE LIMIT ON COVERAGE, which is why it grew. Nine of thirty-three
    contract entries carried a `verify` because there was no word for what most tools do:
    `add_label` sets a label, `add_vm_to_network` joins a network, and neither is
    expressible as present/absent/running/stopped. A tool with no success definition is a
    tool whose "done" means only that the call returned — the conflation this codebase
    refuses everywhere else, and the design note's own position: p_world measures P(the
    tool does what it CLAIMS), so a tool that claims nothing corrupts the estimate rather
    than informing it.

    `args` and `networks` are what the new words need: the label being set is an ARGUMENT,
    and membership lives in the network compartment rather than on the VM record.
    """
    args = args or {}
    if criterion == "present":  return name in vms
    if criterion == "absent":   return name not in vms
    if criterion == "running":  return _is_running(vms.get(name))
    if criterion == "stopped":  return name in vms and not _is_running(vms.get(name))
    if criterion == "restored": return name in vms
    if criterion in ("labelled", "unlabelled"):
        # UNREADABLE IS NOT FALSE. A VM the registry cannot show us is not a VM whose
        # label is missing — it is one we cannot see, and the same rule governs the
        # network criteria below and the `unknown` value of an observed attribute. Getting
        # this wrong turns every registry gap into a failed leaf: the honesty rule firing
        # on the absence of evidence rather than on evidence of absence.
        label = args.get("label")
        if not label or name not in vms:
            return True
        carried = label in _tags(vms.get(name))
        return carried if criterion == "labelled" else not carried
    if criterion in ("attached", "detached"):
        # Membership is READ, not inferred. `networks` is None when the registry could
        # not be read at all, and that is not evidence either way — an unreadable
        # registry must never turn into "it did not happen", which is the same
        # unknown-is-not-false rule the observed attributes are built on.
        if networks is None:
            return True
        net = args.get("net_name") or args.get("network")
        vm  = args.get("vm_name") or args.get("name")
        joined = vm in networks.get(net, set())
        return joined if criterion == "attached" else not joined
    return True


def make_library_verifier(vms_getter: Callable[[], Dict[str, Dict[str, Any]]],
                          networks_getter=None):
    """A verify(criterion, tool, args, result) that checks the contract's success
    criterion against the live VM registry (`vms_getter() -> {name: {status,…}}`).

    Unknown criteria pass (don't block on something we can't check). This is the
    "how" that pairs with the contract's "what" (contract.success_criterion).
    """
    def verify(criterion: str, tool: str, args: Dict[str, Any], result: Any) -> bool:
        name = args.get("name") or args.get("new_name") or args.get("net_name")
        nets = networks_getter() if networks_getter else None
        return _criterion_holds(criterion, name, vms_getter() or {}, args, nets)
    return verify


def make_probe(execute: Callable[[str, Dict], Any]):
    """A probe(spec) -> Optional[bool] that verifies a `probe:` predicate clause with a real
    read-only probe. spec is "scope:assertion:target[:value]":
      • a VM name in the scope slot (e.g. "web01:port_listening:443") → guest_probe (in-VM);
      • the sentinel "local" or "host" (e.g. "local:file_exists:out.csv") → local_probe, which
        verifies run_command's effects in the host workspace.
    Returns the assertion's truth, or None when it can't be verified (malformed spec, or the
    probe itself failed) — the caller treats None as "unverifiable", never as "done"."""
    def probe(spec: str) -> Optional[bool]:
        parts = (spec or "").split(":", 3)            # scope:assertion:target[:value]
        if len(parts) < 3 or not all(parts[:3]):
            return None
        scope, assertion, target = parts[0], parts[1], parts[2]
        value = parts[3] if len(parts) == 4 and parts[3] else None
        if scope in ("local", "host"):
            tool, pargs = "local_probe", {"assertion": assertion, "target": target}
        else:
            tool, pargs = "guest_probe", {"name": scope, "assertion": assertion, "target": target}
        if value is not None:                         # file_contains/matches/user_in_group operand
            pargs["value"] = value
        res = execute(tool, pargs)
        if isinstance(res, dict) and res.get("success"):
            return bool(res.get("holds"))
        return None                                   # channel/probe failure → unverifiable
    return probe


# ALREADY-SATISFIED LEAVES. When a step's effect is ALREADY in place, the right move is to
# make no tool call — and the weak model often gets this right. But the engine reads "no
# call" as `no_action`, a failure, which poisons the enclosing composite to `partial`
# forever: it can never close, so revision re-runs it, and the re-run declines again. That
# loop is what turns an idempotent re-entry into wasted passes.
#
# The fix is to ask STATE, never the model: does the goal's effect already hold? Only goal
# shapes that can be read UNAMBIGUOUSLY off the live registry are answered; everything else
# is False. An unrecognized goal is never "already done" — claiming a satisfaction the
# state doesn't show is exactly the false-success failure mode this system refuses.
#
# Deliberately NOT covered: deletion. "delete X" when X is absent looks satisfied, but it's
# indistinguishable from the model targeting the wrong name — and no benefit is worth
# teaching the harness to call a mis-aimed destructive step done.
_SAT_NAME = r"['\"]?(?P<name>[a-z][\w.-]*)['\"]?"
_SAT_VM = r"(?:vm|virtual machine|machine|instance|node|box|server)"
_SAT_CREATE_VM_RE = re.compile(
    # NOT "launch": in this tool vocabulary launch means START an existing VM, so
    # "launch a vm named X" must be answered by the status rule below (or not at all),
    # never by mere existence — a stopped X would score satisfied.
    rf"\b(?:create|make|provision|spin\s*up|deploy|add)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+)?"
    rf"{_SAT_VM}\s+(?:named|called)\s+{_SAT_NAME}", re.I)
_SAT_CREATE_NET_RE = re.compile(
    rf"\b(?:create|make|provision|set\s*up|add)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+|isolated\s+|private\s+)*"
    rf"network\s+(?:named|called)\s+{_SAT_NAME}", re.I)
# An adverb may sit between the entity and the preposition ("put red1 TOGETHER on …") —
# the harness's own collective expansion produces exactly that, and without tolerating it
# the reader cannot recognise work it just did and the step is redone.
_SAT_ATTACH_RE = re.compile(
    r"\b(?:put|add|attach|connect|move|join)\s+['\"]?(?P<vm>[a-z][\w.-]*)['\"]?\s+"
    r"(?:(?:together|directly|also|now|straight|immediately|as\s+well)\s+)*"
    r"(?:to|on|onto|into|in|in\s+to)\s+(?:the\s+)?"
    r"(?:network\s+(?:named|called)\s+['\"]?(?P<net1>[a-z][\w.-]*)|"
    r"['\"]?(?P<net2>[a-z][\w.-]*)['\"]?\s+network)", re.I)
_SAT_LABEL_RES = (
    re.compile(r"\bgive\s+['\"]?(?P<vm>[a-z][\w.-]*)['\"]?\s+the\s+['\"]?(?P<label>[\w.-]+)['\"]?\s+label\b", re.I),
    re.compile(r"\b(?:add|apply)\s+(?:the\s+)?(?:label|tag)\s+['\"]?(?P<label>[\w.-]+)['\"]?\s+to\s+['\"]?(?P<vm>[a-z][\w.-]*)", re.I),
    re.compile(r"\blabel\s+['\"]?(?P<vm>[a-z][\w.-]*)['\"]?\s+(?:as|with)\s+['\"]?(?P<label>[\w.-]+)", re.I),
)
# Words that describe a network rather than name it.
# Words that DESCRIBE a network rather than name it. One list, used by both the state
# reader (an adjective is not a name, so "the NEW network" is unreadable, not absent) and
# the prerequisite completer (an article is not a network to go and create).
_NET_ADJECTIVES = frozenset({
    "new", "same", "different", "other", "another", "isolated", "private", "own",
    "second", "third", "shared", "common", "virtual", "a", "an", "the", "one", "this",
    "that", "its", "their",
})
_SAT_LAUNCH_RE = re.compile(rf"\b(?:launch|start|boot|power\s*on)\s+(?:the\s+)?(?:{_SAT_VM}\s+)?{_SAT_NAME}\s*$", re.I)
_SAT_STOP_RE = re.compile(rf"\b(?:stop|shut\s*down|power\s*off|halt)\s+(?:the\s+)?(?:{_SAT_VM}\s+)?{_SAT_NAME}\s*$", re.I)


def make_state_verdict(vms_getter: Callable[[], Dict[str, Dict[str, Any]]],
                       execute: Optional[Callable[[str, Dict], Any]] = None,
                       stamp: Optional[List[int]] = None):
    """A verdict(goal) -> True / False / None(unrecognized): does live state show this
    goal's effect?

    TRI-STATE, and the third value is the important one. "Not satisfied" and "I cannot
    read this goal" are different facts: the first can refuse a bogus `done`, the second
    must never do so. Collapsing them would make every unparseable goal unverifiable and
    stall the tree. The harness mints its own steps in a fixed canonical form ("create a
    vm named red1", "give red1 the 'red' label"), so for those the parse is exact — this
    is the intended effect of a generated step, read back off the phrasing that generated
    it rather than authored a second time in a place that could drift.

    VM facts come from the registry (`vms_getter`). Network facts need a read-only
    `list_networks` through `execute` — the same "verify with a real read-only call"
    pattern make_probe uses — because the VM registry doesn't carry membership. No
    executor, or a failed call, means the network question is UNKNOWN, which reads as
    not-satisfied: the conservative direction.
    """
    _net_stamp = stamp if stamp is not None else [0]
    _net_cache: Dict[str, Any] = {"stamp": None, "value": None}

    def _networks() -> Optional[Dict[str, set]]:
        """{network name: {member vm names}} from the executor, or None when the registry
        cannot be READ. None and {} are different answers: an empty registry means no
        networks exist (so an attach definitely did not happen), while an unreadable one
        means we know nothing — and a reader that confuses them will refuse a `done` that
        was perfectly good. Readability is judged by the SHAPE of the reply, since an
        executor with no networks still returns the key."""
        if execute is None:
            return None
        # The verdict is asked at EVERY node closure, and each ask was a fresh registry
        # read — real HTTP against the executor in a live run. Memoized against a stamp the
        # caller bumps when the world changes, so a burst of closures over unchanged state
        # costs one read instead of twenty.
        stamp = _net_stamp[0]
        if _net_cache["stamp"] == stamp:
            return _net_cache["value"]
        try:
            raw = execute("list_networks", {})
        except Exception:
            _net_cache.update(stamp=stamp, value=None)
            return None
        if isinstance(raw, list):
            rows = raw
        elif isinstance(raw, dict) and "networks" in raw:
            rows = raw.get("networks") or []
        else:
            _net_cache.update(stamp=stamp, value=None)
            return None                        # no networks key at all → not a real reply
        out: Dict[str, set] = {}
        for r in rows:
            if isinstance(r, dict) and r.get("name"):
                out[str(r["name"]).lower()] = {str(m).lower() for m in (r.get("members") or [])}
            elif isinstance(r, str):
                out[r.lower()] = set()
        _net_cache.update(stamp=stamp, value=out)
        return out

    def _tags(rec: Dict[str, Any]) -> set:
        return {str(t).lower() for t in (list(rec.get("labels") or []) + list(rec.get("flags") or []))}

    def verdict(goal: str) -> Optional[bool]:
        g = goal or ""
        # ATOMIC GOALS ONLY. The rules below match a clause, so a COMPOUND goal ("create a
        # vm named web AND launch it") would report satisfied on the strength of its first
        # clause alone — claiming done for work that never happened. Reuse the compound
        # splitter's own atomicity test: two or more parts that each name an action means
        # this goal is not one effect, and one satisfied clause says nothing about the rest.
        try:
            from .chat.context_assistant import scan_tool_hints
            parts = [p.strip() for p in _COORD_RE.split(g) if p and p.strip()]
            if len(parts) > 1 and sum(1 for p in parts if scan_tool_hints(p)) > 1:
                return None                    # compound: not one effect to read
        except Exception:
            pass
        vms = {str(k).lower(): v for k, v in (vms_getter() or {}).items()}

        m = _SAT_CREATE_VM_RE.search(g)
        if m:
            return m.group("name").lower() in vms

        m = _SAT_CREATE_NET_RE.search(g)
        if m:
            nets = _networks()
            return None if nets is None else m.group("name").lower() in nets

        m = _SAT_ATTACH_RE.search(g)
        if m:
            net = (m.group("net1") or m.group("net2") or "").lower()
            # "the NEW network", "a DIFFERENT network" — the adjective is not the network's
            # name. Checking membership of a network called "new" answers False for a VM
            # that is correctly attached, and a False here REFUSES a node that succeeded.
            # An unnamed reference is unreadable, which is what None is for.
            if net in _NET_ADJECTIVES:
                return None
            nets = _networks()
            if nets is None:
                return None
            return m.group("vm").lower() in nets.get(net, set())

        for rx in _SAT_LABEL_RES:
            m = rx.search(g)
            if m:
                rec = vms.get(m.group("vm").lower())
                return bool(rec) and m.group("label").lower() in _tags(rec)

        m = _SAT_LAUNCH_RE.search(g)
        if m:
            return _is_running(vms.get(m.group("name").lower()))

        m = _SAT_STOP_RE.search(g)
        if m:
            rec = vms.get(m.group("name").lower())
            return rec is not None and not _is_running(rec)

        return None           # unrecognized shape → no opinion, never a refusal
    return verdict


def make_state_check(vms_getter: Callable[[], Dict[str, Dict[str, Any]]],
                     execute: Optional[Callable[[str, Dict], Any]] = None):
    """The boolean view of make_state_verdict: satisfied(goal) -> bool. Only a definite
    True counts as satisfied, so an unreadable goal is never "already done"."""
    verdict = make_state_verdict(vms_getter, execute)
    return lambda goal: verdict(goal) is True


# An ASSURANCE goal asserts a checkable end-state the plan must actually establish —
# not merely a set of steps to run. Detecting that intent lets the ephemeral (no-
# predicate) path apply a goal-level honesty rule instead of closing on structure alone.
_ASSURANCE_RE = re.compile(
    r"\b(make sure|ensure|verify|confirm|guarantee|prove|check that|validate|"
    r"ping each other|ping one another|reach each other|reach one another|"
    r"can (?:all |each )?(?:ping|reach)|all (?:can )?(?:ping|reach|connect)|"
    r"connectivity|all connected|mutually reachable)\b", re.I)
_CONNECTIVITY_RE = re.compile(r"\b(ping|reach|connect|connectivity|mesh)\b", re.I)


def _has_assurance_intent(goal: str) -> bool:
    return bool(_ASSURANCE_RE.search(goal or ""))


# A COUNTED state assertion — "make sure exactly 3 vms carry the 'prod' label", "all vms
# are running". The generic assurance rule demands a FINDING, which is right for a claim
# about connectivity (you cannot see reachability in a registry) and wrong for a claim
# about state: the registry IS the evidence. Without this a goal reaches the exact world
# it asked for and still closes `unverified`, because it looked for the proof in the one
# place that could never hold it.
_COUNT_ASSERT_RE = re.compile(
    r"\b(?P<qual>exactly|at\s+least|at\s+most|no\s+more\s+than|no\s+fewer\s+than)?\s*"
    r"(?P<n>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:vms?|virtual machines?|machines?|boxes|servers?|instances?|nodes?)\s+"
    r"(?:carry|carries|have|has|hold|with|are\s+labell?ed|are\s+tagged|labell?ed|tagged)\s+"
    r"(?:the\s+)?['\"]?(?P<label>[\w.-]+)['\"]?", re.I)
_ALL_STATUS_RE = re.compile(
    r"\b(?:all|every|each)\s+(?:the\s+)?(?:vms?|virtual machines?|machines?|boxes|servers?)\s+"
    r"(?:is|are|be)\s+(?P<status>running|stopped)\b", re.I)


def _state_assertion(goal: str, vms: Dict[str, Dict[str, Any]]) -> Optional[bool]:
    """True/False for a goal that asserts a COUNTABLE fact about live state; None when the
    goal asserts nothing this can read. Never guesses — an unreadable assertion falls
    through to the findings rule exactly as before."""
    m = _COUNT_ASSERT_RE.search(goal or "")
    if m:
        raw = m.group("n").lower()
        want = int(raw) if raw.isdigit() else _NUMWORDS.get(raw)
        if not want:
            return None
        label = m.group("label").lower()
        have = sum(1 for r in (vms or {}).values()
                   if label in {t.lower() for t in _vm_tags(r)})
        qual = re.sub(r"\s+", " ", (m.group("qual") or "").strip().lower())
        if qual == "exactly":
            return have == want
        if qual in ("at most", "no more than"):
            return have <= want
        return have >= want          # "at least", "no fewer than", or a bare count
    m = _ALL_STATUS_RE.search(goal or "")
    if m:
        if not vms:
            return None              # nothing to be true OF
        want_running = m.group("status").lower() == "running"
        return all(_is_running(r) == want_running for r in vms.values())
    return None


def make_goal_assessor(vms_getter: Callable[[], Dict[str, Dict[str, Any]]], findings=None, probe=None,
                       predicate=None):
    """An assess(goal, children, ledger) -> (verdict, complaint) — the CONTRACT ROOT
    PREDICATE plus, when it REJECTS, the reason in one line.

    The verdict alone is what acceptance needs; the complaint is what SELF-CORRECTION
    needs. A goal that ran to completion and was then rejected is the case with the most
    diagnostic information available — "mesh(fleet) is not confirmed" says exactly what a
    corrective re-plan has to fix — and throwing that away left the loop re-planning blind.
    verify_goal below is the verdict-only view, unchanged for its existing callers.

    Checks the active contract's structured goal predicate (contract.goal_predicate(),
    a list of {criterion, target} clauses). Two kinds of clause:
      • STATE clauses (present/absent/running/stopped/restored) → checked against the
        live VM registry (what IS).
      • EPISTEMIC clauses (`mesh` → the fact mesh(target); `reachable` → reachable(target))
        → checked against the FINDINGS ledger (what was LEARNED). This is how a
        connectivity goal ("all ping each other") is accepted: the ping's recorded
        result must be truthy — NOT the tool merely returning success.

    The root goal is accepted only if EVERY clause holds — so a plan that ran cleanly
    but did not actually achieve the goal (a broken mesh) books no reward. Returns None
    when the contract declares no structured predicate (no clauses, no gate).
    """
    def _finding_true(fact: str) -> bool:
        # `usable` excludes a PENDING claim — an unverified fact can't close a goal
        # until a human confirms it (see findings.usable / gorgon claim confirm).
        return findings is not None and findings.usable(fact)

    def assess(goal: str, children: list, ledger: list) -> Tuple[Optional[bool], str]:
        # Acceptance clauses come from the MISSION (what you tasked) when one is given;
        # otherwise fall back to the contract's legacy goal_predicate (pre-split). No
        # clauses → None, so acceptance falls to the Library (state) + findings grounding.
        clauses = predicate if predicate is not None else _contract.goal_predicate()
        if not clauses:
            # GOAL-LEVEL HONESTY RULE (the composite twin of the leaf `unverifiable`
            # rule): a plain goal falls to structural acceptance — EXCEPT an ASSURANCE
            # goal ("make sure they all ping each other", "ensure/verify X") that asserts
            # a checkable end-state. Such a goal must be affirmatively GROUNDED in the
            # findings ledger, or a plan that merely RAN closes `unverified`, never `done`
            # (false success is the worst failure mode for a corrigible agent). No
            # assurance intent → None, so ordinary goals keep structural acceptance.
            if findings is None or not _has_assurance_intent(goal):
                return None, ""
            # A claim about STATE is settled by state — before falling back to findings,
            # which are the right evidence only for what a registry cannot show.
            st = _state_assertion(goal, vms_getter() or {})
            if st is True:
                return True, ""
            if st is False:
                return False, ("the goal states a countable end-state that does NOT hold in "
                               "the live registry — count what is actually there and change "
                               "only the difference.")
            facts = list(findings.facts())
            if _CONNECTIVITY_RE.search(goal or ""):
                # A connectivity assurance needs at least one USABLE mesh/reachable
                # finding — a recorded-but-false mesh (the "plan ran, mesh is broken"
                # case) does NOT count, so the goal can't falsely close on it.
                conn = [f for f in facts if f.startswith("mesh(") or f.startswith("reachable(")]
                if any(_finding_true(f) for f in conn):
                    return True, ""
                return False, ("connectivity was never CONFIRMED — no usable mesh/reachable "
                               "finding (a recorded-but-false mesh does not count). Find which "
                               "members cannot reach each other and fix that, then re-check.")
            # Generic assurance → at least one usable (probe-grounded or human-vouched)
            # finding; a plan that learned nothing verifiable can't claim assurance.
            if any(_finding_true(f) for f in facts):
                return True, ""
            return False, ("the goal asserts an end-state but nothing verifiable was learned — "
                           "OBSERVE the result (probe/ping/check) instead of assuming it.")
        vms = vms_getter() or {}
        for c in clauses:
            crit, target = c.get("criterion"), c.get("target")
            if crit == "mesh":
                if not _finding_true(f"mesh({target})"):
                    return False, (f"mesh({target}) is not confirmed — the '{target}' members are "
                                   f"not known to reach each other. Check they share one network.")
            elif crit == "reachable":
                if not _finding_true(f"reachable({target})"):
                    return False, f"reachable({target}) is not confirmed — {target} was never reached."
            elif crit == "found":
                # Generic epistemic acceptance: the target IS the fact key
                # (e.g. found:ip(web01)) — accept only if the ledger learned it.
                # Generalizes mesh/reachable to any registered yield-schema fact.
                if not _finding_true(target):
                    return False, f"the fact {target} was never learned — go and establish it."
            elif crit == "probe":
                # Grounded: verify the assertion with an actual read-only probe.
                # Unverifiable (no probe fn, or the probe failed) → NOT done.
                if probe is None or probe(target) is not True:
                    return False, f"the probe {target} does not hold (or could not be run)."
            elif not _criterion_holds(crit, target, vms):
                return False, f"{target} is not {crit} — the required end-state does not hold."
        return True, ""
    return assess


def make_goal_verifier(vms_getter: Callable[[], Dict[str, Dict[str, Any]]], findings=None, probe=None,
                       predicate=None):
    """The verdict-only view of make_goal_assessor: verify_goal(goal, children, ledger)
    -> True / False / None(no predicate declared). What ACCEPTANCE needs."""
    assess = make_goal_assessor(vms_getter, findings, probe, predicate)

    def verify_goal(goal: str, children: list, ledger: list) -> Optional[bool]:
        return assess(goal, children, ledger)[0]
    return verify_goal


def make_ce_estimator(call_model, tools, cost_of, cfg=None, reward=None, p_of=None, compound_p=None):
    """A per-alternative CE estimator for OR ordering/pruning (gauntlet C).

    For an alternative sub-goal, PEEK at which primitive the model would use (a model
    call with NO execution) and price THAT tool deterministically: CE = μ − (λ/2)σ²
    with μ = p·R − cost, cost = leaf_cost(cost_of(tool)). The model proposes the tool;
    the HARNESS prices the value — no p_self self-rating (the design's firewall). Reward
    is the goal-closing payoff, common to all alternatives, so ranking prefers the cheaper
    / more-reliable route to the SAME goal.

    A COMPOUND alternative (the model would DECOMPOSE) is priced by its α-credited backed-
    up CE from the peeked step count — so a deep-but-reliable route competes on merit
    instead of being fizzled to ~0 (this is how superadditive α steers LIVE planning, not
    just the post-run economics). Only when α > 0: at α = 0 a compound route stays unpriced
    (kept, never pruned) — the original act-observe-correct default. A nested-OR
    (`alternatives`) peek is still unpriced (too deep to cost cheaply here).
    """
    c = _cfg_with(cfg)
    R = c.get("R", 1.0) if reward is None else reward

    def estimate(alt_goal: str, depth: int) -> Optional[float]:
        msgs = [{"role": "system", "content": _NODE_SYSTEM},
                {"role": "user", "content": f"Goal: {alt_goal}"}]
        name, args = _first_tool_call(call_model(msgs, list(tools) + [DECOMPOSE_TOOL]))  # PEEK, no execute
        if not name or name == "alternatives":
            return None                                   # no-op / nested OR → don't price, don't prune
        if name == "decompose":
            n_steps = len([s for s in (args.get("steps") or []) if s])
            if c["alpha"] <= 0 or n_steps <= 0:
                return None                               # α off → keep the old unpriced default
            # price the deep route with per-step partial credit. Unknown sub-tools → the
            # LEARNED-AVERAGE p_world (`compound_p`, the mean of this env's observed tool
            # reliability) when available, else the static default; plus a nominal per-step cost.
            # compound_p may be a live callable (recomputed per read) or a plain float.
            _cp = compound_p() if callable(compound_p) else compound_p
            return _compound_ce(n_steps, c, reward=R, p=_cp, cost=_leaf_cost(None, c))
        cost = _leaf_cost(cost_of(name), c)
        p = p_of(name) if p_of else c["p_world"]
        mu = p * R - cost
        var = p * (1 - p) * R * R
        return _ce(mu, var, c)
    return estimate


def _reason_target(args: Dict[str, Any]) -> Optional[str]:
    """The entity an action operates on (for the reason-vs-action check)."""
    for k in ("name", "vm_name", "new_name", "net_name", "target", "vm"):
        v = (args or {}).get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _response_text(resp: Any) -> str:
    """The free-text content of a model response (no tool call)."""
    msg = (resp or {}).get("message", {}) if isinstance(resp, dict) else {}
    c = msg.get("content")
    return c.strip() if isinstance(c, str) else ""


# Present-state vocabulary → canonical status. Used to catch a reason that asserts a
# FALSE current state to justify an action (grounded reason-check, mitigation A).
_STATUS_CANON = {
    "running": "running", "up": "running", "on": "running", "active": "running",
    "live": "running", "started": "running", "online": "running",
    "stopped": "stopped", "down": "stopped", "off": "stopped", "inactive": "stopped",
    "halted": "stopped", "offline": "stopped", "shut down": "stopped", "not running": "stopped",
}
_STATUS_ALT = "|".join(sorted((re.escape(w) for w in _STATUS_CANON), key=len, reverse=True))


def _canon_status(status: Any) -> Optional[str]:
    s = str(status or "").lower()
    if "run" in s:  return "running"
    if "stop" in s or "shut" in s or "off" in s: return "stopped"
    return None


def _asserted_status(reason: str, target: str) -> Optional[str]:
    """A PRESENT-state claim the reason makes about the NAMED target — "<target> is
    [currently|already|still] <status>". Requires the target name + a present "is", and is
    blind to DESIRED outcomes ("to make it running", "so it's up"): those don't match
    "<target> is …", so a legit launch/stop is never mis-flagged. Returns the canonical
    asserted status, or None."""
    m = re.search(rf"\b{re.escape(target)}\b\s+(?:is|was|'s)\s+(?:currently\s+|already\s+|still\s+)?({_STATUS_ALT})\b",
                  reason, re.I)
    return _STATUS_CANON.get(m.group(1).lower()) if m else None


def make_reason_gate(call_model, state_getter=None):
    """A reason_gate(goal, tool, args) -> {"reason": str, "problem": tag|None} (the D1 gate).

    STAGE 1 — validate the reason: elicit the model's ONE-sentence justification for THIS
    action (a free-text call, no tools). An action it can't justify fails ("no_reason").
    STAGE 2a — action vs stated intent: the entity the action TARGETS must appear in that
    reason ("target_absent" — acting on X while the reason only mentions Y).
    STAGE 2b — reason vs REALITY (mitigation A, the deception-resistant half): if the reason
    asserts a present STATE for the target that CONTRADICTS the live registry (e.g. "web is
    running" when the Library shows it stopped), flag "reason_contradicts_state". A liar
    can't satisfy this without the world actually matching — the fact-check the pure
    consistency check couldn't do. Needs `state_getter()` → {name: {status}}; without it,
    2b is skipped (structural-only, as before).

    Deliberately STRUCTURAL, never a model-judge (the p_self firewall: a weak model grading
    its own reasoning is a second bad draw). Conservative — only clear divergence /
    contradiction is flagged. The elicited reason is RETURNED (mitigation B) so the harness
    can record it on the ledger + surface it in the live tree, making even a passed lie
    auditable after."""
    import json as _json

    def gate(goal: str, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            payload = _json.dumps(args, sort_keys=True)
        except Exception:
            payload = str(args)
        msgs = [{"role": "system", "content":
                 "State in ONE short sentence WHY this action serves the goal, naming the "
                 "specific thing you are acting on. Reply with the sentence only — no tool call."},
                {"role": "user", "content": f"Goal: {goal}\nAbout to call: {tool}({payload})"}]
        reason = _response_text(call_model(msgs, []))
        if not reason:
            return {"reason": "", "problem": "no_reason"}
        target = _reason_target(args)
        if target and target.lower() not in reason.lower():
            return {"reason": reason, "problem": "target_absent"}
        if target and state_getter is not None:                 # STAGE 2b — ground vs reality
            rec = (state_getter() or {}).get(target)
            if rec:
                asserted = _asserted_status(reason, target)
                actual = _canon_status(rec.get("status"))
                if asserted and actual and asserted != actual:
                    return {"reason": reason, "problem": "reason_contradicts_state"}
        return {"reason": reason, "problem": None}
    return gate


# COLLECTIVE (distributive) decomposition — Track 1.1. The benchmark's cliff: the weak
# model nails atomic steps and dependency chains but CANNOT expand "do X to all/them/each"
# over a set into per-member steps (0/3 at N=3). So the HARNESS does the loop: a collective
# sub-goal is expanded deterministically against the LIVE entity set into one atomic
# sub-goal per member — playing to the model's strength (each atomic step) and covering its
# weakness (the loop). No model call, no variance.
# The `all|each|every <word>` arms must NOT swallow a following PREPOSITION. The phrase is
# replaced by a member name in place, so eating one turns "attach all TO a private network"
# into "attach fleet1 a private network" — and with the preposition gone _ANON_NET_RE can no
# longer see the unnamed shared network, so no network is ever minted and every member
# attaches to nothing. Found 2026-07-26: the goal translator emitted exactly that phrasing
# and rung 4 built five VMs with zero networks. Nothing about it is translator-specific —
# an operator typing "attach all to a network" has always hit it.
_PREPS = r"to|in|into|on|onto|at|with|from|for|by|over|under|across|through|inside|within"
_COLLECTIVE_RE = re.compile(
    rf"\b(them all|all of them|all the \w+|all (?!(?:{_PREPS})\b)\w+|each of them|"
    rf"each (?!(?:{_PREPS})\b)\w+|every (?!(?:{_PREPS})\b)\w+|them|all|each)\b", re.I)
# Inherently-collective operations are NOT distributive — "ping each other" / mesh is one
# fact over the whole set, not a per-member step. Never expand these (they're the assurance
# clause the goal-honesty rule + mesh acceptance already handle).
_INHERENT_COLLECTIVE_RE = re.compile(r"\b(each other|one another|ping all|connectivity|mesh|reachable)\b", re.I)

# CARDINAL CREATION (Track 1.1b). "create 5 vms" instantiates a NEW set of size N — the
# collective expander below distributes over EXISTING entities, so it can't touch this, and
# the weak model handles a bare cardinal inconsistently (wrong count, ad-hoc names, and on
# any re-plan a FRESH batch — the duplication cascade). The harness mints N STABLE,
# deterministic names (vm1..vmN) and emits one atomic create each: the count is exact, and a
# re-entry is naturally idempotent (same names → the executor no-ops instead of duplicating).
# Fires ONLY when no explicit names are given ("...named a, b" stays the model's job) and the
# noun is a known provisionable resource (so the minted step routes to the right tool).
_NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_CARDINAL_NOUNS = {  # surface form → canonical singular (drives the minted name + tool routing)
    "vm": "vm", "vms": "vm", "virtual machine": "vm", "virtual machines": "vm",
    "machine": "vm", "machines": "vm", "instance": "vm", "instances": "vm",
    "node": "vm", "nodes": "vm", "box": "vm", "boxes": "vm", "server": "vm", "servers": "vm",
    "network": "network", "networks": "network", "container": "container", "containers": "container",
}
_CARDINAL_CREATE_RE = re.compile(
    r"\b(?:create|make|spin\s*up|provision|launch|deploy|add|start)\s+"
    r"(?P<count>\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:new\s+|identical\s+|separate\s+)*"
    r"(?P<noun>virtual machines?|vms?|machines?|instances?|nodes?|boxes|servers?|networks?|containers?)\b",
    re.I)
_CARDINAL_MAX = 25   # a bound so "create 1000 vms" can't detonate the planner


# A cardinal phrase may carry a QUALIFIER — "create 3 vms labelled 'red'". Minting three
# bare creates would drop it silently, and because each create then succeeds the clause
# closes `done` having never labelled anything: the harness manufacturing a false success.
# A label qualifier is understood and expanded into real steps; anything else we can't
# faithfully carry means the whole optimization stands down and the model keeps the goal.
_CARD_LABEL_RE = re.compile(
    r"^\s*(?:that\s+are\s+|which\s+are\s+)?(?:labell?ed|tagged|with\s+the\s+label|"
    r"with\s+label|labelled\s+as)\s+['\"]?(?P<label>[\w.-]+)['\"]?\s*$", re.I)


def _cardinal_create_steps(goal: str):
    """['create a <noun> named <noun><i>' for i in 1..N] for a bare "create N <noun>", plus
    one labelling step per member when the phrase carries a label qualifier. None when the
    goal isn't a bare cardinal create. Deterministic + stable so a re-entry mints the SAME
    names (idempotent). Bails when explicit names are present (the model owns those), when
    the count is out of [2, _CARDINAL_MAX], or when a trailing qualifier is present that
    this cannot faithfully express — dropping meaning is worse than not firing."""
    g = goal or ""
    if re.search(r"\b(?:named|called)\b", g, re.I):     # explicit names → the model's job
        return None
    m = _CARDINAL_CREATE_RE.search(g)
    if not m:
        return None
    raw = m.group("count").lower()
    n = int(raw) if raw.isdigit() else _NUMWORDS.get(raw)
    noun = _CARDINAL_NOUNS.get(m.group("noun").lower())
    if not n or not noun or not (2 <= n <= _CARDINAL_MAX):
        return None
    label = None
    tail = g[m.end():].strip(" ,.;")
    if tail:                                            # something qualifies the cardinal
        lm = _CARD_LABEL_RE.match(tail)
        if not lm:
            return None                                 # unknown qualifier → don't fire at all
        label = lm.group("label")
    # Name from the QUALIFIER when there is one. Two cardinal clauses in one goal ("3 vms
    # labelled red and 2 labelled blue") would otherwise both mint vm1, vm2… — the blue
    # creates would no-op onto the red VMs and the second group would never exist. `red1,
    # blue1` keeps the groups distinct while staying just as stable across a re-entry.
    stem = re.sub(r"[^a-z0-9]", "", label.lower())[:12] if label else noun
    names = [f"{stem or noun}{i}" for i in range(1, n + 1)]
    steps = [f"create a {noun} named {nm}" for nm in names]
    if label:                                           # carry the qualifier, don't drop it
        steps += [f"give {nm} the '{label}' label" for nm in names]
    return steps


# COMPOUND DECOMPOSITION (Track 2). The benchmark's last cliff: the weak model fuses two
# actions into one sub-goal ("create a vm named a AND put it on lab network") and then, at
# depth > 0 (where decompose-first is off), can't split it — it returns TEXT. The harness
# splits a CONJUNCTION of ACTIONS into its clauses deterministically. Crucially it uses the
# tool matcher to tell an action-conjunction ("create X and put X on net" → two actions)
# from a noun-conjunction ("create vms a and b" → one action over a set) so it never
# over-decomposes an atomic goal — the exact failure decompose-first-at-every-level had.
_COORD_RE = re.compile(r"\s+(?:and then|and afterwards|then|and|;)\s+|,\s+(?=\w)", re.I)

# A conjunction can leave a clause SHARING the earlier verb: "create 3 vms labelled 'red'
# and 2 vms labelled 'blue'" — the second half is an object, not an action. The tool-hint
# test alone waves it through (a bare "2 vms" hints the VM tools), and the orphan then
# closes `done` having run nothing. Where the fragment is unmistakably parallel to what
# came before — a COUNT of a known provisionable noun — the verb is inherited so it becomes
# a real step; anything less obvious is left alone and the goal stays whole for the model.
_BARE_CARDINAL_RE = re.compile(
    r"^(?:\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:new\s+|identical\s+|separate\s+)*"
    r"(?:virtual machines?|vms?|machines?|instances?|nodes?|boxes|servers?|networks?|containers?)\b",
    re.I)
_LEAD_VERB_RE = re.compile(
    r"^(?:and\s+|then\s+|also\s+)*(?P<verb>create|make|spin\s*up|provision|launch|start|deploy|"
    r"add|put|attach|connect|join|move|give|label|tag|stop|shut|delete|destroy|remove|clone|"
    r"ping|check|verify|ensure|make\s+sure|configure|set|run|list|show)\b", re.I)


def _inherit_verbs(parts: List[str]) -> List[str]:
    """Give a verbless parallel fragment the verb of the clause before it, so a shared-verb
    conjunction splits into real actions instead of an orphan."""
    out, last_verb = [], None
    for p in parts:
        vm = _LEAD_VERB_RE.match(p)
        if vm:
            last_verb = vm.group("verb")
            out.append(p)
        elif last_verb and _BARE_CARDINAL_RE.match(p):
            out.append(f"{last_verb} {p}")
        else:
            out.append(p)
    return out


def make_compound_splitter():
    """A split_compound(goal, path) -> [clause] | None. Splits a sub-goal that JOINS two or
    more ACTIONS ("do X and do Y") into one atomic clause per action; None for an atomic
    goal or a mere noun-conjunction. Reuses scan_tool_hints so only clauses that name a real
    action count — a part that hints no tool ('named a', 'b') is not a step."""
    from .chat.context_assistant import scan_tool_hints
    def split(goal: str, path: List[str]) -> Optional[List[str]]:
        parts = [p.strip() for p in _COORD_RE.split(goal or "") if p and p.strip()]
        if len(parts) < 2:
            return None
        # Split ONLY a clean conjunction where EVERY part independently names an action (hints
        # a tool). If any part doesn't — a bare object sharing an earlier verb ("create a net
        # AND a vm named web"), or "b" in "a and b" — the split would drop/mangle it, so leave
        # the goal whole for the model. This is what keeps a shared-verb or noun conjunction
        # (which the model handles fine) from being wrongly torn apart.
        parts = _inherit_verbs(parts)
        # Every part must name an action: hint a tool AND lead with a verb. The tool hint
        # alone is not enough — "2 vms labelled 'blue'" hints the VM tools while being a
        # bare object, and splitting it off strands work no step will ever do.
        if all(scan_tool_hints(p) and _LEAD_VERB_RE.match(p) for p in parts):
            return parts
        return None
    return split


# ANONYMOUS-NETWORK PREREQ (Track 1.4b). A collective can carry an IMPLICIT shared
# prerequisite: "put them all in a network" names no network, so every per-member step reads
# "put <m> in a network" — and the FIRST member's step spends its one action CREATING the
# net instead of attaching, leaving that member off it (the attach is cannibalized) while the
# rest attach to a net the goal never named. The prereq completer can't see this: it keys on
# a network NAME, and there isn't one. So the harness names it — mint ONE stable name up
# front, prepend its creation, and thread that name through every member step. Stable, so a
# re-entry threads the SAME net (the executor no-ops the create) instead of minting another.
# `net1` rather than `network1` so it can't collide with a cardinal "create N networks" set.
# NB "the network" is deliberately NOT a determiner here: a definite reference points at
# an existing network, and minting a new one would be the wrong reading. "their own" and
# "a different" ARE — both assert a net that doesn't exist yet, which is exactly the case
# a partition depends on.
_ANON_NET_RE = re.compile(
    r"\b(?P<prep>in|into|on|onto|to|inside|within)\s+"
    r"(?:a|an|one|the\s+same|a\s+single|a\s+shared|a\s+common|their\s+own|its\s+own)\s+"
    r"(?:new\s+|single\s+|shared\s+|common\s+|isolated\s+|private\s+|virtual\s+|own\s+|"
    r"different\s+|separate\s+|dedicated\s+|second\s+)*"
    # …and NOT when the very next words name it. "a network called core" is a NAMED
    # network that merely reads like an indefinite one; threading it would rename the
    # operator's network to a minted one and mangle the step into "the network called
    # net1 called core".
    r"network\b(?!\s+(?:called|named)\b)", re.I)
_ANON_NET_NAME = "net1"


def _thread_anonymous_network(steps: List[str]) -> Optional[List[str]]:
    """['create a network called <net>'] + `steps` rewritten to name that network, when the
    steps attach to an UNNAMED one; None when they don't (nothing to thread). Deterministic
    — the same collective always threads the same name.

    (A `stem` parameter naming the net after its group once lived here, for the case of two
    groups each needing their own network. Its only caller was the label-scoped collective
    expansion, removed as benchmark-shaped; dropped rather than left dangling.)"""
    if not any(_ANON_NET_RE.search(s or "") for s in steps):
        return None
    net = _ANON_NET_NAME
    named = [_ANON_NET_RE.sub(lambda m: f"{m.group('prep')} the network called {net}",
                              s or "", count=1) for s in steps]
    return [f"create a network called {net}"] + named


def make_collective_expander(entities_getter: Callable[[], Dict[str, Any]]):
    """An expand_collective(goal, path) -> [per-member sub-goal] | None. Fires when a
    sub-goal applies a DISTRIBUTIVE operation to a collective of live entities ("put them
    all on the network"); resolves the collective to the current entity set and substitutes
    each member in, yielding one atomic sub-goal per member. Skips inherently-collective ops
    (mesh/ping-each-other) and no-ops when there are <2 entities or no collective phrase."""
    def expand(goal: str, path: List[str]) -> Optional[List[str]]:
        g = goal or ""
        if _INHERENT_COLLECTIVE_RE.search(g):
            return None
        # CARDINAL CREATION first: "create N <noun>" mints a NEW set (no live members to read).
        cardinal = _cardinal_create_steps(g)
        if cardinal:
            return cardinal
        ents = entities_getter() or {}
        m = _COLLECTIVE_RE.search(g)
        if not m:
            return None
        members = list(ents.keys())
        if len(members) < 2:
            return None
        # replace the collective phrase with each member name → per-member atomic sub-goals
        steps = [(g[:m.start()] + e + g[m.end():]).strip() for e in members]
        # …then name any UNNAMED shared network the members attach to, and create it FIRST,
        # so no member's attach is spent creating it (Track 1.4b).
        return _thread_anonymous_network(steps) or steps
    return expand


# REFERENCE GROUNDING (Track 1.2). The weak model often decomposes "create a vm named a
# and put it on the network" into ["create a vm named a", "add VM to the network"] — the
# second step DROPS which vm ("a"). An un-grounded step targets the wrong/no entity and
# fails. When the parent goal names exactly ONE entity, bind a bare reference ("the vm",
# "it") in a child step back to that entity — so "add vm to the network" → "add a to the
# network". Deterministic; only fires on an unambiguous single-entity parent.
_NAMED_ENTITY_RE = re.compile(r"\b(?:named|called)\s+([a-z][\w-]*)", re.I)
_BARE_REF_RE = re.compile(r"\b(?:the\s+|this\s+|that\s+)?(?:vm|virtual machine|machine|instance|node|box|it)\b", re.I)


def make_step_grounder():
    """A ground_steps(parent_goal, steps) -> steps that binds bare entity references in
    decomposed steps to the parent's single named entity (Track 1.2). No-op unless the
    parent names EXACTLY ONE entity (so binding is unambiguous) and a step both omits that
    name and carries a bare reference."""
    def ground(parent_goal: str, steps: List[str]) -> List[str]:
        ents = list(dict.fromkeys(_NAMED_ENTITY_RE.findall(parent_goal or "")))
        if len(ents) != 1:
            return steps
        e = ents[0]
        present = re.compile(rf"\b{re.escape(e)}\b", re.I)     # word-boundary (a 1-char name isn't a substring hit)
        out = []
        for s in steps:
            if present.search(s or "") or not _BARE_REF_RE.search(s or ""):
                out.append(s)                       # already grounded, or nothing to bind
            else:
                out.append(_BARE_REF_RE.sub(e, s, count=1))
        return out
    return ground


# DEPENDENCY COMPLETION (Track 1.4). The benchmark's real blocker: the weak model plans
# "put a/b/c on the lab network" but NEVER creates `lab` — it assumes the shared
# prerequisite exists, so every attach fails and it can't recover from "no such network".
# The harness completes the plan: if a decomposition REFERENCES a network that no step
# CREATES, prepend its creation. Deterministic; the model's plausible-but-incomplete plan
# is made whole. (Networks are the first prerequisite; the rule set is extensible.)
_NET_NAMED_RE = re.compile(r"\bnetwork\s+(?:called|named)\s+([a-z][\w-]*)", re.I)   # "network called lab"
_NET_ADJ_RE   = re.compile(r"\b([a-z][\w-]*)\s+network\b", re.I)                   # "lab network"
_NET_CREATE_RE = re.compile(r"\b(?:create|make|provision|set\s*up|add)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+|isolated\s+|private\s+)*network\b", re.I)
_NET_ARTICLES = _NET_ADJECTIVES        # same concept; kept as an alias for its readers


def _network_names(text: str):
    """The network name(s) a step names — 'network called lab' or 'lab network' → {'lab'}.
    Two ordered passes so 'a network called lab' yields 'lab', not the article 'a'."""
    t = text or ""
    out = {m.group(1).lower() for m in _NET_NAMED_RE.finditer(t)}
    for m in _NET_ADJ_RE.finditer(t):
        nm = m.group(1).lower()
        if nm not in _NET_ARTICLES:
            out.add(nm)
    return out


def make_prereq_completer(networks_getter: Optional[Callable[[], Any]] = None):
    """A complete_steps(parent_goal, steps) -> steps that PREPENDS a creation step for any
    network the plan REFERENCES but never CREATES (and that isn't already in state, if a
    networks_getter is given) — the dropped-prerequisite the weak model can't recover from.
    A step 'create a vm named a and put it on lab network' references `lab` but doesn't
    create it; with no 'create ... network' step for `lab`, prepend 'create a network
    called lab'. No-op when every referenced network is created or already exists."""
    def complete(parent_goal: str, steps: List[str]) -> List[str]:
        referenced, created = set(), set()
        for s in steps:
            names = _network_names(s)
            if _NET_CREATE_RE.search(s or ""):
                created |= names                     # this step creates a network
            else:
                referenced |= names
        existing = {str(n).lower() for n in (networks_getter() or [])} if networks_getter else set()
        missing = referenced - created - existing
        if not missing:
            return steps
        return [f"create a network called {m}" for m in sorted(missing)] + steps
    return complete


def make_grant_handler(agent: Optional[str] = None, prompt=None):
    """The engine's per-leaf GRANT hook (wired as `referendum=`). A destructive-but-legal
    action the contract would HALT is offered to the operator ONCE via `prompt(tool, args,
    consequence) -> granted?`; a grant downgrades the halt to a revertible checkpoint. A
    DENIAL — or no prompt at all (an unattended run) — auto-DRAFTS a durable referendum
    proposing to lift that gate (delegation → tier 'normal'), filed for later review. So a
    live y/N keeps the mission moving, and the pattern of asking becomes a rule proposal
    the operator weighs later. Draft once per tool per run (no proposal spam)."""
    drafted: set = set()

    def grant(tool: str, args: Dict[str, Any], consequence: str) -> bool:
        if prompt is not None:
            try:
                if prompt(tool, args, consequence):
                    return True                       # granted this once
            except Exception:
                pass
        if tool not in drafted:                       # denied or unattended → draft a referendum
            drafted.add(tool)
            try:
                from .agent import proposals as _proposals
                a = agent or _contract.active_agent_key()
                _proposals.propose(
                    a, kind="delegation", origin="ai", proposed_weight=2,
                    text=f"Allow {tool} with a confirmation instead of a hard stop — it keeps blocking the goal.",
                    effect={"tier": "normal", "tools": [tool]},
                    prompted_by=f"the contract gate halted {tool} during a mission")
            except Exception:
                pass
        return False
    return grant


def make_tool_selector(cap: int = 14):
    """Per-node tool NARROWING for the weak model (the autonomous twin of the chat path's
    round-0 narrowing). Offered all ~50 tools at once, llama3.1 degrades to emitting text
    instead of tool-calls; narrowed to a node's sub-goal it tool-calls correctly. This
    closes that gap for run_autonomous.

    Narrows at COMMAND granularity: scan the node goal for trigger hints (the SAME matcher
    the context assistant uses — scan_tool_hints) then expand each hinted tool to its whole
    command's toolset, so a per-tool tag gap can't strand a sibling (hint 'network' → the
    network command's create/delete/list/attach, not just one). Adds a small always-on
    read-only kit so the model can always ground against state. A vague goal that hints
    NOTHING (already surfaced upstream) falls back to a default lab kit — never the full
    50 (which is what muted the model). Width is capped below the degradation cliff, with
    the hinted tools kept first so the cap never drops them. Meta-tools (decompose/
    alternatives) are appended by the engine, not here."""
    from orchestrator.ai.chat.context_assistant import scan_tool_hints
    from executor.command_catalog import COMMAND_CATALOG
    siblings: Dict[str, set] = {}                    # tool → every tool sharing a command with it
    for e in COMMAND_CATALOG:
        ts = set(e.get("tools") or [])
        for t in ts:
            siblings.setdefault(t, set()).update(ts)
    ALWAYS   = ["list_vms", "list_networks", "list_labels", "vm_status"]   # grounding, always offered
    DEFAULT  = ["create_vm", "launch_vm", "stop_vm", "create_network",
                "add_vm_to_network", "add_label", "fleet"]                 # vague-goal fallback kit

    def select(goal: str, tools: List[Dict]) -> List[Dict]:
        by_name = {t["function"]["name"]: t for t in tools}
        core: set = set()
        for h in scan_tool_hints(goal or ""):
            core |= siblings.get(h, {h})
        ordered: List[str] = []
        def _add(names):
            for n in names:
                if n in by_name and n not in ordered:
                    ordered.append(n)
        _add(sorted(core))                          # hinted commands' tools FIRST (cap-safe)
        if not core:
            _add(DEFAULT)                            # vague → the lab kit, not all 50
        _add(ALWAYS)                                 # read-only grounding, last
        return [by_name[n] for n in ordered[:cap]]
    return select


def render_mission_plan(steps: List[str]) -> str:
    """The mission's declared sub_goals as an intended ROOT decomposition. Injected into
    planning context so the plan tree forms along these steps — which is what makes them
    reward-bearing: reward-cost's α books each CLOSED step its share of the mission reward
    (vs. the model decomposing however it likes and α crediting emergent branches)."""
    lines = "\n  ".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
    return ("MISSION PLAN — decompose the goal along these steps; each step you CLOSE "
            f"earns its share of the reward:\n  {lines}")


def render_failure_warnings(records: List[Dict[str, Any]]) -> str:
    """Planning context for plan shapes that have FAILED before (cross-run memory).

    Advisory, never a block: a plan that failed for a transient reason must stay
    retryable, so this warns and lets the model decide. It is the durable form of the
    same post-mortem that makes in-run revision corrective."""
    if not records:
        return ""
    lines = ["TRIED BEFORE AND FAILED (earlier runs — do NOT re-derive these):"]
    for r in records[:5]:
        again = f" (failed {r['n']}×)" if int(r.get("n", 1)) > 1 else ""
        steps = " → ".join(r.get("steps") or [])
        lines.append(f"- {steps or r.get('source', '?')}{again}: {r.get('why', '')}")
    return "\n".join(lines)


def _harvest_failures(root: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The PLANS this run tried that did not close, generalized for reuse. Composites
    only: a plan is the reusable unit, while a leaf's failure ("no network lab") is a
    fact about that moment's state, not about the approach."""
    from .planner.method_cache import _generalize
    out: List[Dict[str, Any]] = []

    def walk(n: Dict[str, Any]) -> None:
        kids = n.get("children") or []
        if kids and n.get("status") != "done" and n.get("mode") != "or":
            steps = [c.get("goal", "") for c in kids]
            why = next((t for t in reversed(n.get("tried") or []) if t), None) \
                or f"the plan closed {n.get('status')}"
            meth = _generalize(n.get("goal", ""), steps)
            out.append({"pattern": meth["pattern"].pattern if meth else re.escape(n.get("goal", "")),
                        "source": n.get("goal", ""),
                        "steps": (meth["steps"] if meth else steps), "why": why})
        for c in kids:
            walk(c)
    walk(root or {})
    return out


def _vm_tags(rec: Dict[str, Any]) -> List[str]:
    """A VM's groupings: user labels ∪ auto-flags, the same union LIBRARY.fleets uses."""
    return sorted(set(rec.get("labels") or []) | set(rec.get("flags") or []))


def render_state(vms: Dict[str, Dict[str, Any]]) -> str:
    """Compact current-state grounding from the VM registry — so the model plans
    against reality (won't act on VMs that don't exist) and, on a retry, SEES why the
    last approach failed. The live loop grounds against LIBRARY.ai_digest the same way.

    Shows TAGS and the FLEET groupings, not just status, at PARITY with the chat path's
    ai_digest. The autonomous planner used to be grounded strictly weaker than chat: a
    goal about a group ("make sure they all ping each other") was planned against a
    context that never named a single label, so the model had to invent an identifier for
    the group — and reached for the most recent name it had seen, the NETWORK. A group is
    addressed by its label, so the label has to be in the context.
    """
    if not vms:
        return "CURRENT STATE: no VMs exist yet — do not act on VMs that don't exist."
    items = ", ".join(
        f"{n}({r.get('status', '?')}" + (f" tags={','.join(t)}" if (t := _vm_tags(r)) else "") + ")"
        for n, r in sorted(vms.items()))
    lines = ["CURRENT STATE (resolve references against this; never act on a VM not "
             "listed here):", f"  known VMs: {items}"]
    fleets: Dict[str, List[str]] = {}
    for n, r in sorted(vms.items()):
        for tag in _vm_tags(r):
            fleets.setdefault(tag, []).append(n)
    if fleets:
        lines.append("  FLEETS (label/flag → members): "
                     + "; ".join(f"{k}=[{', '.join(v)}]" for k, v in sorted(fleets.items())))
    return "\n".join(lines)


def _summarize(result: Dict[str, Any]) -> Dict[str, Any]:
    """Walk the tree for the headline counts an operator wants after a run."""
    halted = unverified = rolled = forbidden = aborted = 0

    def walk(n: Dict[str, Any]) -> None:
        nonlocal halted, unverified, rolled, forbidden, aborted
        if n.get("status") == "blocked" and n.get("reason") in ("contract_halt", "consent_denied"):
            halted += 1
        if n.get("status") == "forbidden":
            forbidden += 1
        if n.get("status") == "aborted":
            aborted += 1
        if n.get("status") == "unverified":
            unverified += 1
        rolled += int(n.get("rolled_back", 0))
        for c in n.get("children", []):
            walk(c)

    walk(result["root"])
    return {"status": result["root"].get("status"), "ok": result.get("ok"),
            "executed": len(result.get("ledger", [])),
            "halted": halted, "forbidden": forbidden, "aborted": aborted,
            "unverified": unverified, "rolled_back": rolled}


def run_autonomous(
    goal: str,
    *,
    call_model:  Callable[[List[Dict], List[Dict]], Dict],
    execute:     Callable[[str, Dict], Any],
    tools:       List[Dict],
    vms_getter:  Optional[Callable[[], Dict[str, Dict[str, Any]]]] = None,
    gate:        Optional[Callable[[str, Dict], str]] = None,
    build_context: Optional[Callable[[str, List[str]], str]] = None,
    select_tools:  Optional[Callable[[str, List[Dict]], List[Dict]]] = None,
    on_event:    Optional[Callable[[Dict[str, Any]], None]] = None,
    on_node:     Optional[Callable[[Dict[str, Any]], None]] = None,
    decompose_first: bool = True,
    method_cache=None,
    findings=None,
    findings_schema=None,
    reward=None,
    referendum=None,
    watchdog=None,
    killswitch=None,
    prior=None,
    max_retries: int = 2,
    max_revisions: int = 1,
    max_depth:   int = 3,
    max_steps:   int = 60,
    # THE PROGRAM REGIME, off by default and deliberately so. A program is the third
    # answer at a node — beside a primitive and a decomposition — for a goal whose shape
    # is a set, an ordering and a postcondition. It is measured on the bench (13 rungs,
    # several columns) and has never run in production, so it opts IN until it has.
    use_programs: bool = False,
    library=None,
    validate_reasons: bool = False,
    persist_claims: bool = False,
    # OFF by default — measured, not assumed. See translator.py: it swaps rungs rather
    # than winning them (literal stayed 7/10, trading rung 4 for rung 8), and the effect
    # is smaller than the run-to-run noise. Switchable because the module is the phase-2
    # skeleton: the same call emits IR instead of English.
    translate: bool = False,
    agent_key: Optional[str] = None,
    mission=None,
    verbose: bool = False,
    # THE SCHEMA GATE'S OPERATOR SURFACE. A program the gate suppresses is re-asked
    # automatically, and a suppression nobody hears about is indistinguishable from a
    # harness that simply understood the request. Injected rather than printed, so a CLI,
    # the chat and a headless run each decide for themselves what "telling the operator"
    # means. None is honest for an unattended run — the gate then still refuses, still
    # re-asks, and only the announcement goes nowhere.
    notify: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Run `goal` autonomously with the active agent's contract. No human in the loop.

    Wires run_score with the contract's gate + success criteria (defaults), a Library-
    backed verifier (when `vms_getter` is given → verified-completion is live), and NO
    confirm backstop. Returns run_score's {root, ledger, ok} plus `events` (one per
    executed tool call), `disposition`, and a `summary` (executed / halted / unverified
    / rolled_back). `gate` defaults to the active agent's contract.gate_action, so an
    autonomous .grgn halts red lines and checkpoints destructive leaves for real.

    Also returns the reward-cost outputs: `economics` (μ/σ²/CE/cost priced with the
    LEARNED per-tool p_world), `reliability` (the p_self dials to feed the next run as
    `prior=`), and `tool_counts` / `p_world` (the accumulated tallies and learned world-
    success rates). `prior=` feeds a previous run's reliability + tool_counts forward;
    tool_counts also persist durably in the findings store when `persist_claims`.
    """
    events: List[Dict[str, Any]] = []

    # TRANSLATE THE GOAL FIRST — before the toolkit, the context or the tree, because
    # everything downstream reads this string. The planner understands goals by pattern,
    # and the patterns were written against one phrasing: the ladder scores 7/10 on its
    # own wording and 2/10 on paraphrases of the SAME capability. Restating the goal in
    # canonical vocabulary is what makes the existing readers fire again.
    #
    # ONE model call per run, not per node. It may reword; it may NOT re-plan — the
    # clauses come back joined into a single goal string, so the ordinary decomposition
    # still happens below (see translator.py; feeding them in as sub_goals would seed the
    # plan, which the benchmark principle forbids). Every failure returns `goal`
    # untouched, so the worst case here is the behaviour we already had.
    original_goal, goal_clauses = goal, None
    if translate:
        goal, goal_clauses = _normalize_goal(goal, call_model)

    # A MISSION narrows the agent to this tasking: restrict the toolkit to the
    # mission's whitelist minus its (agent∪mission) blacklist before the model ever
    # sees them. The agent's own red lines still apply as a hard backstop in the gate.
    if mission is not None:
        tools = mission.filter_tools(tools)

    _world_stamp = [0]      # bumped on every executed tool → invalidates cached state reads
    _net_names: Dict[str, Any] = {"stamp": None, "value": []}

    def _exec(tool: str, args: Dict[str, Any]) -> Any:
        r = execute(tool, args)
        _world_stamp[0] += 1
        ev = {"tool": tool, "args": args,
              "ok": not (isinstance(r, dict) and (r.get("success") is False or r.get("error")))}
        events.append(ev)
        if on_event:
            on_event(ev)
        return r

    verify = make_library_verifier(vms_getter) if vms_getter else None
    # Ground planning in current state (the Active Library's job): inject the live VM
    # registry into every planning call so the model won't plan/retry on VMs that
    # don't exist. The live loop uses LIBRARY.ai_digest the same way.
    if findings is None:
        findings = Findings()
    if findings_schema is None:
        findings_schema = DEFAULT_SCHEMA
    # Seed the ledger from the per-agent claim store: confirmed claims come back as
    # USABLE facts (a human already vouched for them) and prior pending claims stay
    # pending (so they aren't re-surfaced as brand-new). Best-effort — a bad/missing
    # store must never brick a run.
    if persist_claims:
        try:
            from .agent.contract import active_agent_key as _agent_key
            from .planner import findings_store as _store
            agent_key = agent_key or _agent_key()
            findings.merge(_store.load(agent_key))
        except Exception:
            pass
    # Built AFTER findings exists: the root predicate reads epistemic clauses (mesh /
    # reachable) from the findings ledger, not just VM state.
    # ONE assessor, two views: the VERDICT accepts (or refuses) the goal, and the
    # COMPLAINT tells self-correction what the predicate objected to — so a plan that ran
    # in full and still missed can be re-planned against the actual objection instead of
    # blind. Same clause evaluation behind both; the complaint is only asked for on the
    # revision path.
    _assess = make_goal_assessor(
        vms_getter, findings, probe=make_probe(execute),
        predicate=(mission.predicate() if mission is not None else None),
    ) if vms_getter else None
    verify_goal    = (lambda g, c, l: _assess(g, c, l)[0]) if _assess else None
    goal_complaint = (lambda g, c, l: _assess(g, c, l)[1]) if _assess else None
    # Ground planning in BOTH state (what is) and findings (what's known) — the two
    # externalized memories that stop the weak model acting on the nonexistent or
    # re-discovering what it already learned. A mission's declared sub_goals seed the ROOT
    # decomposition so the plan tree forms ALONG them — which is how they become reward-
    # bearing: reward-cost's α then books each closed step its share of the mission reward.
    if build_context is None:
        _steps = mission.sub_goals if mission is not None else []
        def build_context(goal, path):
            parts = []
            if _steps and not path:                       # root only — guide the decomposition
                parts.append(render_mission_plan(_steps))
            if vms_getter:
                parts += [s for s in (render_state(vms_getter()), findings.render()) if s]
            if _prior_failures:      # what this shape of plan cost us last time
                warn = render_failure_warnings(_mstore.warnings_for(_prior_failures, goal))
                if warn:
                    parts.append(warn)
            return "\n\n".join(parts)
    if method_cache is None:
        # STRUCTURAL MEMORY: load what this agent has already learned to decompose, over
        # the seed library. Without this the cache is rebuilt empty every run and the
        # system re-asks the model the same planning questions forever — it can only
        # "un-reason over time" if the methods outlive the process. Best-effort: a bad
        # store must degrade to seeds-only, never brick a run.
        _stored = []
        if persist_claims:
            try:
                from .planner import method_store as _mstore
                from .agent.contract import active_agent_key as _agent_key
                agent_key = agent_key or _agent_key()
                _stored = _mstore.load(agent_key)
            except Exception:
                _stored = []
        method_cache = _MethodCache.from_records(_stored) if _stored else _seeded_cache()
    # The NEGATIVE twin of the method cache: plan shapes that failed in earlier runs, so
    # the planner is warned before re-deriving one. Advisory context, never a block.
    _prior_failures = []
    if persist_claims:
        try:
            from .planner import method_store as _mstore
            from .agent.contract import active_agent_key as _agent_key
            agent_key = agent_key or _agent_key()
            _prior_failures = _mstore.load_failures(agent_key)
        except Exception:
            _prior_failures = []
    # HARD-seed the root decomposition from a mission's declared sub_goals: score.py's
    # depth-0 method-cache path (a known goal shape decomposes DETERMINISTICALLY, no model)
    # then forces the plan tree to form along those exact steps — so they are GUARANTEED
    # reward-bearing under α, not merely nudged by the planning-context hint. Needs ≥2 steps
    # (a single step is atomic, not a decomposition).
    if mission is not None and len(mission.sub_goals) >= 2:
        method_cache.remember(goal, list(mission.sub_goals))
    if watchdog is None:
        watchdog = Watchdog()
    if killswitch is None:                        # arm the safeword kill-switch from the contract
        killswitch = KillSwitch(safeword=_contract.safeword())
    # UNATTENDED backstop: if the contract declares a dead-man's timeout, arm a timer that
    # aborts the run if it goes that long without a sign of life (the engine checks in at
    # each step). None (default) = off — the safeword is the attended stop.
    deadman = None
    _dm_timeout = _contract.deadman_timeout()
    if _dm_timeout:
        deadman = DeadMansSwitch(killswitch, _dm_timeout).start()
    # Reward-cost constants come from the active contract (.grgn). A PRIOR run's
    # reliability feeds FORWARD (the global p_self control): a shakier last run →
    # higher θ/λ this run + a shallower depth budget D_max.
    rc_cfg = _contract.reward_cost_cfg()
    if mission is not None:                  # a tasking may LAYER reward-shaping knobs (alpha,
        rc_cfg = {**rc_cfg, **mission.reward_cost_overrides()}   # H, …) over the contract policy
    if reward is None:                       # payoff for closing the goal
        # A mission's resolved reward (its own, importance-scaled, or the agent default)
        # when tasked via a mission; otherwise the agent's default payoff.
        reward = mission.reward() if mission is not None else _contract.campaign_reward()
    prior_counts: Dict[str, Dict[str, int]] = {}
    # Reliability dials (p_self → θ/λ/D_max) feed FORWARD so the harness self-tightens
    # run-to-run: an explicit in-memory `prior=` wins; otherwise the durable per-agent
    # reliability store closes the loop, so the live drivers inherit last run's stance
    # WITHOUT hand-threading `prior=` (mirrors the p_world/toolstats durability).
    prior_dials = dict(prior) if prior else None
    if prior_dials is None and persist_claims:
        try:
            from .agent.contract import active_agent_key as _agent_key
            from .planner import findings_store as _store
            agent_key = agent_key or _agent_key()
            prior_dials = _store.load_reliability(agent_key) or None
        except Exception:
            prior_dials = None
    if prior_dials:
        rc_cfg = {**rc_cfg, "theta": prior_dials.get("theta", rc_cfg.get("theta", 0.0)),
                  "lambda": prior_dials.get("lambda", rc_cfg.get("lambda", 0.5))}
        if prior_dials.get("D_max"):
            max_depth = min(max_depth, prior_dials["D_max"])
        prior_counts = prior_dials.get("tool_counts") or {}   # only an in-memory prior= carries these
    if not prior_counts and persist_claims:       # no in-memory forward-feed → the durable
        try:                                       # per-agent store IS the cross-run p_world memory
            from .agent.contract import active_agent_key as _agent_key
            from .planner import findings_store as _store
            agent_key = agent_key or _agent_key()
            prior_counts = _store.load_tool_counts(agent_key)
        except Exception:
            pass
    # LEARNED p_world, updated LIVE as the mission runs: price each primitive by its
    # measured success rate from prior runs' tallies PLUS this mission's events so far
    # (smoothed toward the static default). Recomputed per call against the growing
    # `events` log, so a tool that starts failing mid-mission has its p_world fall and OR
    # ranking routes around it AS THE RUN PROCEEDS — not just between runs.
    # Shared with run_score so p_of reads the SAME ledger the persisted p_world is
    # learned from (score.py records the VERIFIED verdict there). Counting `events`
    # instead would raise a tool's live p_world on a bare tool-return success while
    # the ledger — and the next run — lower it after verification fails: the learned
    # parameter would contradict itself. One source, no contradiction.
    run_ledger: List[Dict[str, Any]] = []
    def p_of(tool: str) -> float:
        counts = _merge_counts(prior_counts, _tool_counts(run_ledger))
        return _p_world_lookup(_p_world_estimate(counts, rc_cfg or None), rc_cfg or None)(tool)
    # Learned-AVERAGE p_world (mean of tool reliability) — the estimator prices a
    # COMPOUND route's unknown sub-tools with this data-grounded prior instead of the
    # static default. LIVE, mirroring p_of: recomputed over prior + this run's ledger
    # each time it's read, so a tool degrading mid-run lowers deep-route pricing too —
    # a frozen-at-start value would contradict the live-p_world design above. None (no
    # history) → compound_ce falls back to the static p_world. (The per-tool Beta prior
    # in _p_world_estimate already pins sparse-data tools near p₀, so this unweighted
    # mean isn't dominated by 1-observation outliers.)
    def compound_p() -> Optional[float]:
        live = _p_world_estimate(_merge_counts(prior_counts, _tool_counts(run_ledger)), rc_cfg or None)
        return (sum(live.values()) / len(live)) if live else None
    # OR worth-it: rank alternatives by CE and prune the ones below θ. The estimator
    # prices the tool each alternative would use (contract risk = cost); θ from rc_cfg.
    estimate = make_ce_estimator(call_model, tools, _contract.tool_risk,
                                 cfg=rc_cfg or None, reward=reward, p_of=p_of, compound_p=compound_p)
    # Per-leaf commit gate (deliberation scales with irreversibility): a reversible leaf
    # always commits (act-observe-correct); an IRREVERSIBLE one only if its simulated CE
    # — priced at the goal reward and the leaf's LEARNED p_world — clears the worth-it bar.
    def commit_gate(tool: str, args: Dict[str, Any]) -> bool:
        return _should_commit(_contract.tool_risk(tool), rc_cfg or None,
                              reward=reward, p=p_of(tool))
    # Reason-validation gate (opt-in — an extra model call per leaf): capture the model's
    # stated reason and check the action against it structurally + against the LIVE STATE
    # (never a self-graded score). state_getter grounds the reason vs reality.
    reason_gate = make_reason_gate(call_model, state_getter=vms_getter) if validate_reasons else None
    # Collective decomposition (Track 1.1): the harness deterministically loops a
    # distributive "do X to all/them" sub-goal over the live entity set — covers the weak
    # model's proven inability to expand a collective operation itself. On whenever we can
    # see the entity set (vms_getter); the per-member steps are atomic, the model's strength.
    # Compound splitting (Track 2): split a "do X and do Y" sub-goal into its action
    # clauses — the harness does what the weak model can't at depth. Always on; deterministic.
    expand_compound = make_compound_splitter()
    expand_collective = make_collective_expander(vms_getter) if vms_getter else None
    # Reference grounding (Track 1.2): bind bare entity references in the model's decomposed
    # steps to the parent's single named entity — deterministic, always on.
    ground_steps = make_step_grounder()
    # Dependency completion (Track 1.4): inject a missing prerequisite (create the network a
    # step attaches to) the weak model drops. Always on; deterministic, plan-level.
    def _live_networks():
        """Network names from the executor, for the prerequisite completer's existence
        check. Without it the completer prepends "create a network called X" for a network
        that is already there — its guard was written but never armed. Cached against the
        same world stamp as the state reader, so a burst of nodes costs one read."""
        if _net_names["stamp"] == _world_stamp[0]:
            return _net_names["value"]
        names = []
        try:
            raw = execute("list_networks", {})
            rows = raw if isinstance(raw, list) else (raw or {}).get("networks") or []
            names = [r.get("name") if isinstance(r, dict) else r for r in rows]
            names = [n for n in names if n]
        except Exception:
            names = []
        _net_names.update(stamp=_world_stamp[0], value=names)
        return names

    complete_steps = make_prereq_completer(_live_networks)
    engine = Engine(
        gate=gate, verify=verify, verify_goal=verify_goal, referendum=referendum,
        watchdog=watchdog, killswitch=killswitch, findings=findings,
        findings_schema=findings_schema, method_cache=method_cache,
        decompose_first=decompose_first, estimate=estimate,
        ce_floor=(rc_cfg or {}).get("theta", 0.0),
        retry_penalty=(rc_cfg or {}).get("H", 0.0),   # each wasted retry raises the abandon bar
        whole_goal_gate=True,   # refuse a not-worth-it whole goal up-front (α-priced compound/leaf roots)
        max_revisions=max_revisions,   # plan-level self-correction: re-plan a partial composite
        commit_gate=commit_gate,   # per-leaf simulated-ĈE gate for irreversible commits
        reason_gate=reason_gate,   # opt-in two-stage reason validation (validate_reasons)
        on_node=on_node,           # live node-lifecycle events for a streaming tree view
        expand_compound=expand_compound,       # Track 2: split a "do X and do Y" sub-goal
        expand_collective=expand_collective,   # Track 1.1: harness-driven collective decomposition
        ground_steps=ground_steps,             # Track 1.2: bind bare references in decomposed steps
        complete_steps=complete_steps,         # Track 1.4: inject a dropped prerequisite (create network)
        # "no tool call" is only a failure when something was left to do — an already-in-
        # place effect (idempotent re-entry) closes done on STATE, not on the model's word.
        # ONE reader, two uses: `already_satisfied` pre-empts finished work during a
        # correction (True only), `goal_effect` refuses a `done` the state contradicts
        # (False only). The tri-state keeps "unreadable" from ever becoming a refusal.
        already_satisfied=(make_state_check(vms_getter, execute) if vms_getter else None),
        goal_effect=(make_state_verdict(vms_getter, execute, _world_stamp) if vms_getter else None),
        goal_complaint=goal_complaint,   # why the predicate rejected a fully-executed plan
        # Both hooks or neither: the engine offers the tool only where it can also run
        # what comes back, so there is no state in which the model is invited to write a
        # program nothing will execute.
        program_tool=(_EMIT_PROGRAM_TOOL if (use_programs and library is not None)
                      else None),
        run_program=(_make_run_program(
            library, findings,
            known_names=(library.known_names() if hasattr(library, "known_names")
                         else None),
            say=notify)
            if (use_programs and library is not None) else None),

    )   # criterion_of/legal_filter default to the active contract inside run_score
    # MISSION-SCOPED LAW: layer the mission's own rules over the contract for this run only
    # (the human's per-tasking answer to a referendum). Restored in the finally, so the
    # active contract is never left mutated — and the contract's red lines stay inviolable.
    _mission_rules = mission.rules() if mission is not None else []
    if _mission_rules:
        _contract.push_rules(_mission_rules)
    try:
        result = run_score(
            goal,
            call_model=call_model, execute=_exec, tools=tools, engine=engine,
            build_context=build_context, select_tools=select_tools,
            max_retries=max_retries, max_depth=max_depth, max_steps=max_steps, ledger=run_ledger,
        )
    finally:
        if _mission_rules:
            _contract.pop_rules()
        if deadman is not None:               # disarm the timer no matter how the run ends
            deadman.stop()
    result["events"] = events
    result["disposition"] = _contract.disposition()
    # What the operator ASKED versus what the planner was given. Reported even when
    # nothing changed, because "the goal was translated" is exactly the kind of silent
    # rewriting an operator must be able to see — and it is what the coverage check
    # (next increment) compares the finished tree against.
    result["goal"] = original_goal
    if goal_clauses is not None:
        result["goal_translated"] = {"planned": goal, "clauses": goal_clauses}
    result["findings"] = {f: findings.get(f) for f in findings.facts()}
    # Unverified claims the run recorded — what no probe could confirm, plus the
    # operator's evidence pointer for each, so a human can close the loop by hand.
    result["claims_for_review"] = findings.claims_for_review()
    # Persist this run's claims (pending + confirmed) back to the per-agent store so
    # a human can review/confirm them AFTER the run — and the next run inherits them.
    if persist_claims:
        try:
            from .planner import findings_store as _store
            _store.merge_into(agent_key, findings.persistable())
        except Exception:
            pass
    # Accumulate per-tool world-reliability tallies (prior runs + this run) and learn
    # p_world from them. Fed forward two ways: in-memory via `result["tool_counts"]` (pass
    # as the next run's prior) AND durably via the per-agent findings store below, so
    # p_world survives process restarts. p_world is now DATA-GROUNDED, not a static knob.
    run_counts = _tool_counts(result.get("ledger", []))
    all_counts = _merge_counts(prior_counts, run_counts)
    result["tool_counts"] = all_counts
    result["p_world"] = _p_world_estimate(all_counts, rc_cfg or None)
    if persist_claims:                            # persist THIS run's OWN counts (not the merged
        try:                                       # total — the store already holds the prior)
            from .planner import findings_store as _store
            _store.merge_tool_counts(agent_key, run_counts)
        except Exception:
            pass
    # Reward-cost economics: price the run (μ, σ², CE, cost, reward) using the contract's
    # per-tool risk as the cost source and the LEARNED p_world per tool. Makes the tree
    # reward-cost-aware, with sub-goal closures credited (superadditive, if α > 0).
    _econ_p_of = _p_world_lookup(result["p_world"], rc_cfg or None)
    result["economics"] = _economics(result["root"], cost_of=_contract.tool_risk,
                                      reward=reward, cfg=rc_cfg or None, p_of=_econ_p_of)
    if verbose:
        # PER-NODE economics for the verbose debug view — the caller (CLI) renders it; the
        # loop stays headless. Shows μ/CE/worth_it at every sub-goal so an operator sees
        # WHERE value and uncertainty sit across the plan, not just the run total.
        result["economics_tree"] = _economics_tree(result["root"], cost_of=_contract.tool_risk,
                                                    reward=reward, cfg=rc_cfg or None, p_of=_econ_p_of)
    result["watchdog"] = watchdog.status()
    result["aborted"] = killswitch.tripped
    if killswitch.tripped:
        result["kill_reason"] = killswitch.reason
    # Reliability: measure p_self from this run's ledger → the dials it implies (θ, λ,
    # depth budget), plus the accumulated per-tool tallies for learned p_world. Pass this
    # whole dict as `prior=` to the NEXT run to feed both the dials and p_world forward.
    result["reliability"] = _dials(_p_self(result.get("ledger", [])), rc_cfg or None)
    result["reliability"]["tool_counts"] = all_counts
    if persist_claims:                            # durably chain the p_self dials forward too, so
        try:                                       # the live drivers self-tighten without prior=
            from .planner import findings_store as _store
            _store.save_reliability(agent_key, result["reliability"])
        except Exception:
            pass
    # STRUCTURAL MEMORY (the durable half of the method cache): fold the decompositions
    # this run PROVED — the ones whose composite closed done — into the agent's store, so
    # the next run decomposes them without asking the model. Unproven learning is dropped
    # with the process on purpose; only what worked is worth inheriting.
    result["methods_learned"] = method_cache.proven() if hasattr(method_cache, "proven") else []
    if persist_claims and result["methods_learned"]:
        try:
            from .planner import method_store as _mstore
            _mstore.merge_into(agent_key, result["methods_learned"])
        except Exception:
            pass
    # …and the negative half: the plans that did NOT close. Remembering only successes
    # meant the next run re-derived the same broken plan and re-paid to discover it.
    result["plans_failed"] = _harvest_failures(result.get("root") or {})
    if persist_claims and result["plans_failed"]:
        try:
            from .planner import method_store as _mstore
            _mstore.record_failures(agent_key, result["plans_failed"])
        except Exception:
            pass
    result["summary"] = _summarize(result)
    return result


def run_autonomous_live(goal: str, **kw) -> Dict[str, Any]:
    """Convenience: wire the REAL Ollama model + executor + Active Library and run.

    Imports are local so this module stays importable (and unit-testable) without the
    runtime. Requires a running Ollama and executor; the active agent is whatever
    GORGON_AGENT points at (a Conductor .grgn for a real autonomous run).
    """
    from .chat.ollama_client import _call_ollama
    from .tools import TOOLS
    from .active_library import LIBRARY
    from orchestrator.executor_client import execute_tool

    kw.setdefault("persist_claims", True)              # the real runtime persists claims
    kw.setdefault("select_tools", make_tool_selector())  # narrow the ~50 tools per node, or the weak model goes mute
    return run_autonomous(
        goal,
        call_model=_call_ollama,                       # prepends the active agent's system prompt
        execute=lambda t, a: execute_tool(t, a),
        tools=TOOLS,
        vms_getter=LIBRARY.vms,
        **kw,
    )
