"""
ledger_util.py — stateless helpers for the Score: node factory, goal normaliser,
ledger carry-forward, ledger-aware attach steering, and tool-call extraction.

These are the genuinely top-level (state-free) helpers the recursive engine calls;
they hold no engine state, so they live outside the closure in engine_core.
"""

import re
from typing import Any, Dict, List

from ._deps import _post_create_attach, _narrow_core_tools


def _node(goal: str, status: str, **kw) -> Dict[str, Any]:
    return {"goal": goal, "status": status, **kw}


def _norm(s: str) -> str:
    """Normalize a goal string for no-progress comparison."""
    return " ".join(str(s).lower().split())


def _progress_summary(ledger: List[Dict[str, Any]]) -> str:
    """What earlier steps in THIS plan already did — so a later step ('launch probe')
    knows the entity it references was just created, and uses its exact name instead
    of re-discovering (and mis-picking) it. This is the ledger's carry-forward.
    """
    if not ledger:
        return ""
    lines = []
    for e in ledger:
        a = e.get("args", {})
        name = a.get("name") or a.get("new_name") or a.get("net_name") or a.get("label") or ""
        mark = "" if e.get("ok") else "  (FAILED)"
        lines.append(f"- {e['tool']}: {name}{mark}" if name else f"- {e['tool']}{mark}")
    return ("PLAN PROGRESS — steps ALREADY done (use these EXACT names; do NOT re-create "
            "or re-discover them):\n" + "\n".join(lines))


# Tools that only OBSERVE. Needed because a set-valued goal can legitimately be answered
# by a single read ("list all vms"), while a single MUTATION cannot discharge one. Listed
# explicitly rather than inferred from the risk table, which is populated for only a
# handful of tools — create_network, add_vm_to_network and add_label all carry no risk
# entry, and those are exactly the calls a bogus set-goal close hides behind.
_OBSERVER_TOOLS = frozenset({
    "list_vms", "list_networks", "list_labels", "list_profiles", "list_templates",
    "snapshot_list", "vm_status", "show_config", "check_system", "check_disk",
    "check_profile_compatibility", "scan_isos", "get_vm_logs", "guest_probe",
    "local_probe", "guest_ping", "fingerprint_vm", "monitor_vm", "print_command",
    "clarify", "claim_finding",
})

# A goal that addresses a GROUP rather than one named entity. Such a node cannot be
# reduced to a single attach, however tempting the narrowed tool set makes it look.
_SET_VALUED_RE = re.compile(
    r"\b(?:ones|them|they|all|each|every|both|either|vms|machines|boxes|servers|"
    r"instances|nodes|members|group)\b", re.I)


def _attach_steer(base: List[Dict], node_goal: str, ledger: List[Dict[str, Any]],
                  tools: List[Dict]) -> tuple:
    """Ledger-aware tool steering (data-driven from POST_CREATE_ATTACH).

    Once a creator (e.g. create_network) has run in THIS plan, a later node that
    references the created entity should ATTACH to it, not re-create it. So we
    return a TIGHT set — the attach tool + always-available core — with the creator
    dropped, removing the re-create temptation that made 'put probe on the new
    network' resolve to create_network again. VERIFIED to flip that node (and
    'add probe to labnet') to add_vm_to_network with correct args, 4/4 (2026-07-17).

    Returns (tools, steered). When steered is True the node is an attach-to-existing,
    which is inherently ONE primitive — the caller drops decompose so the weak model
    can't over-decompose it into a spurious 're-create then attach'. When nothing is
    referenced, returns (base, False) unchanged.
    """
    attach_spec = _post_create_attach()
    if not attach_spec:
        return base, False
    low = node_goal.lower()
    by_name = {t.get("function", {}).get("name"): t for t in tools}
    for creator, spec in attach_spec.items():
        made = [e["args"].get(spec["name_arg"]) for e in ledger
                if e.get("tool") == creator and e.get("ok")]
        made = [n for n in made if n]
        if not made:
            continue
        # A node that explicitly says CREATE one of these is not "referencing the entity we
        # just made" — it is asking for a DIFFERENT one. Steering it drops the creator from
        # the offered tools, so the model cannot do what the step says and returns nothing.
        # That was the whole failure of a two-network partition: the second network was never
        # created, so every attach to it failed, repeated, and got throttled as a loop.
        if re.search(rf"\b(?:create|make|provision|set\s*up)\s+(?:a\s+|an\s+|the\s+)?"
                     rf"(?:new\s+|isolated\s+|private\s+|separate\s+|different\s+|second\s+)*"
                     rf"{re.escape(spec['keyword'])}\b", low):
            continue
        referenced = spec["keyword"] in low or any(str(n).lower() in low for n in made)
        attach = by_name.get(spec["attach"])
        if referenced and attach is not None:
            core = [t for t in tools if t.get("function", {}).get("name") in _narrow_core_tools()]
            tight = [attach] + [t for t in core if t is not attach]
            # "steered" claims the node is ONE primitive, and the caller drops `decompose`
            # on the strength of that. True for "put red1 on rednet"; FALSE for a SET —
            # "put the red ones on their own network" needs a network made and three
            # separate attaches, none of which one add_vm_to_network call can express. With
            # the tool narrowed AND decompose withdrawn, the model has no legal way to say
            # what the step requires, so it says nothing and the node dies `no_action`.
            # A set-valued attach keeps decompose: narrowed tools, but still able to plan.
            return tight, not _SET_VALUED_RE.search(low)
    return base, False


def _first_tool_call(resp: Any) -> tuple:
    """Extract (name, args) of the model's first tool call, or (None, None)."""
    msg = (resp or {}).get("message", {}) if isinstance(resp, dict) else {}
    tcs = msg.get("tool_calls") or []
    if not tcs:
        return None, None
    fn = tcs[0].get("function", {})
    args = fn.get("arguments", {})
    if isinstance(args, str):
        import json
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    return fn.get("name"), (args or {})
