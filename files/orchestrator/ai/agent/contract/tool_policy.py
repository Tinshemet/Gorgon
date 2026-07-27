"""
tool_policy.py — the per-tool contract data + tier resolution.

Holds the ``tools`` map ({risk, verb, verify, pin, field}), the fleet action→tier
map, and the tier resolution over them (pin > formula), plus the registry
cross-checks (orphans, pinned disagreements). Composes a RiskFormula.
"""

from typing import Any, Dict, Optional

from .registry import _TOOL_SPECS, _TOOL_NAME_ARG
from .risk_formula import RiskFormula


def _dig(args: Dict[str, Any], path: str) -> Any:
    """Read `a.b.c` out of a nested args dict, or None at the first missing step."""
    cur: Any = args
    for part in str(path).split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


class ToolPolicy:
    """The per-tool contract data: the ``tools`` map ({risk, verb, verify, pin, field}),
    the fleet action→tier map, and the tier resolution over them (pin > formula), plus
    the registry-cross-checks (orphans, pinned disagreements). Composes a RiskFormula.
    """

    def __init__(self, tools: Dict[str, Any], fleet_actions: Dict[str, str],
                 formula: RiskFormula):
        self.tools         = tools
        self.fleet_actions = fleet_actions
        self.formula       = formula

    def tool_risk(self, tool: str) -> Optional[Dict[str, Any]]:
        """The tool's risk facts as assessed by the active contract, or None (→ tier
        none). Risk is a contract JUDGMENT (lives in the .grgn), not a registry fact."""
        return (self.tools.get(tool) or {}).get("risk")

    def formula_tier(self, tool: str) -> Optional[str]:
        """The tier the FORMULA computes for a tool from its risk, ignoring any pin.
        'none' for an assessed-risk-free / unassessed tool; None for a tool absent
        from the registry."""
        if tool not in _TOOL_SPECS:
            return None
        risk = self.tool_risk(tool)
        return "none" if not risk else self.formula.to_tier(self.formula.score(risk))

    def resolve_tier(self, tool: str, args: Optional[Dict[str, Any]] = None) -> str:
        """The LIVE confirmation tier for a proposed tool call — the gate's answer.

        Resolution order: ``fleet`` is action-conditional; then ``arg_tiers`` escalate on
        a specific ARGUMENT VALUE; then a ``pin`` wins if set; otherwise the tier is
        COMPUTED from the contract's risk facts. A tool absent from the registry defaults
        to ``none``.
        """
        if tool == "fleet":
            action = ((args or {}).get("action") or "").strip().lower()
            return self.fleet_actions.get(action, "none")
        if tool not in _TOOL_SPECS:
            return "none"
        attrs = self.tools.get(tool) or {}
        # ARGUMENT-CONDITIONAL TIERS. The same tool can be routine or serious depending on
        # ONE argument, and `create_vm` is the case that forced this: creating an isolated
        # machine is ordinary lab work, while creating one on NAT or a bridge hands it
        # outbound internet or puts it on the real LAN. Pricing those identically is what
        # made the lab the widest hole in the system — run_command is bubblewrapped with
        # --unshare-net, but a VM created through the front door was not.
        #
        # Expressed as DATA in the contract ({arg: {value: tier}}), which generalises the
        # `fleet_actions` special case above rather than adding a second mechanism. The
        # HIGHEST tier among matching args wins: an escalation must not be cancelled by
        # another argument that happens to be tame.
        # The key may be a DOTTED PATH, because the argument that decides the tier is not
        # always top-level: `update_config` takes {name, updates}, and the network mode
        # that matters sits inside `updates`. Keying only on top-level args would have
        # left the after-the-fact change unpriced while pricing the creation — and
        # locking a machine's reach at creation is worth nothing if it can be changed for
        # free afterwards.
        arg_tiers = attrs.get("arg_tiers") or {}
        if arg_tiers and args:
            hits = [tier for path, table in arg_tiers.items()
                    for value, tier in table.items()
                    if str(_dig(args, path) or "").strip().lower() == value.lower()]
            if hits:
                order = getattr(self.formula, "_tiers", None) or []
                return max(hits, key=lambda t: order.index(t) if t in order else -1)
        pin = attrs.get("pin")
        if pin is not None:
            return pin
        risk = self.tool_risk(tool)
        return "none" if not risk else self.formula.to_tier(self.formula.score(risk))

    def success_criterion(self, tool: str) -> Optional[str]:
        """The contract's post-condition for a tool — what "done" means — or None."""
        return (self.tools.get(tool) or {}).get("verify")

    def confirm_meta(self, tool: str):
        """(field, verb) for a confirmable tool, or None. ``field`` names the target
        arg (registry-derived so it tracks the tool signature); ``verb`` is the
        contract's display verb, falling back to a humanized tool name."""
        if tool not in self.tools and tool not in _TOOL_SPECS:
            return None
        attr  = self.tools.get(tool) or {}
        field = attr.get("field") or self._registry_target_field(tool)
        return field, attr.get("verb") or tool.replace("_", " ")

    def _registry_target_field(self, tool: str) -> str:
        """Which arg names the tool's target, from the registry (default 'name')."""
        if tool in _TOOL_NAME_ARG:
            return _TOOL_NAME_ARG[tool]
        req = (_TOOL_SPECS.get(tool) or {}).get("req") or []
        return req[0] if req else "name"

    def orphan_entries(self) -> set:
        """Contract tool entries that name a tool absent from the registry — drift."""
        if not _TOOL_SPECS:
            return set()
        return set(self.tools) - set(_TOOL_SPECS)

    def pinned_disagreements(self) -> Dict[str, Dict[str, str]]:
        """Every pin that overrides the computed tier → {tool: {pin, formula}}."""
        out: Dict[str, Dict[str, str]] = {}
        for tool, attr in self.tools.items():
            pin = attr.get("pin")
            if pin is None:
                continue
            f = self.formula_tier(tool)
            if f is not None and f != pin:
                out[tool] = {"pin": pin, "formula": f}
        return out
