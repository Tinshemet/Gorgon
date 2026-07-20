"""
mission.py — a Mission: what you TASK an agent to do.

The split: a **contract** (.grgn) creates the AGENT — who it is and its default
parameters. A **mission** is a tasking that agent consumes. Only ``title`` and
``goal`` are required; every other field is optional and, when omitted, INHERITS
the agent's default (contract.default_*). So a mission carries just what makes it
different from the agent's baseline.

    contracts create agents · agents consume missions

A signed, long-form mission is authored in the mission wizard and persisted; a
quick one-off task is an *ephemeral* mission (``Mission.ephemeral(goal)``) that
sets only the goal and inherits everything else. Either way, the reward-cost engine
and the goal verifier read the RESOLVED values here, so they never need to know
whether a value came from the mission or the agent.
"""
from typing import Any, Dict, List, Optional

from . import contract as _contract

# The mission fields, and which are required. Data-driven so the wizard, the
# validator, and this model agree on one list (mirrors the forge field schema).
REQUIRED_FIELDS = ("title", "goal")
OPTIONAL_FIELDS = ("sub_goals", "reward", "importance", "weight",
                   "tool_whitelist", "tool_blacklist", "scrutiny",
                   "success_predicate", "success_criteria")


class Mission:
    """A tasking for the active agent. Unset fields resolve to the agent's defaults."""

    def __init__(self, spec: Dict[str, Any], agent: Optional[str] = None):
        self._s = dict(spec or {})
        # The owning agent — a mission is a product of an agent's existence, so it's
        # scoped to (and disabled with) that agent. Defaults to the active one.
        self.agent = agent or self._s.get("agent") or _contract.active_agent_key()

    # ── identity ──────────────────────────────────────────────────────────────
    @property
    def title(self) -> str:
        return self._s.get("title") or "(untitled mission)"

    @property
    def goal(self) -> str:
        return self._s.get("goal") or ""

    @property
    def sub_goals(self) -> List[str]:
        return list(self._s.get("sub_goals") or [])

    # ── resolved parameters (mission value → else agent default) ────────────────
    def reward(self) -> float:
        """R for closing this mission — importance SCALES it (an important mission is
        worth more), so a 2× importance on a reward-1 mission books reward 2."""
        base = self._s.get("reward")
        base = float(base) if base is not None else _contract.default_reward()
        return base * self.importance()

    def importance(self) -> float:
        v = self._s.get("importance")
        return float(v) if v is not None else _contract.default_importance()

    def weight(self) -> float:
        v = self._s.get("weight")
        return float(v) if v is not None else _contract.default_weight()

    def scrutiny(self):
        return self._s.get("scrutiny") if self._s.get("scrutiny") is not None \
            else _contract.default_scrutiny()

    def whitelist(self) -> List[str]:
        """Tools this mission may use — its own whitelist, else the agent's toolkit."""
        return list(self._s.get("tool_whitelist") or _contract.default_toolkit())

    def blacklist(self) -> List[str]:
        """Red lines for this mission: the agent's blacklist UNION the mission's own —
        a mission can add limits, never remove the agent's (the agent bounds every
        mission it runs)."""
        return sorted(set(_contract.default_blacklist()) | set(self._s.get("tool_blacklist") or []))

    def predicate(self) -> Optional[list]:
        """The mission's structured acceptance clauses (the checkable 'done when'), or
        None — in which case acceptance falls to the Library (state) + findings
        grounding, no faked gate over prose."""
        return self._s.get("success_predicate") or None

    def filter_tools(self, tools: List[Dict]) -> List[Dict]:
        """Apply the mission's whitelist/blacklist to a tool list (OpenAI tool dicts):
        keep only whitelisted names (if a whitelist is set), then drop blacklisted."""
        wl, bl = set(self.whitelist()), set(self.blacklist())

        def _name(t):
            return (t.get("function") or {}).get("name") if "function" in t else t.get("name")
        out = tools
        if wl:
            out = [t for t in out if _name(t) in wl]
        if bl:
            out = [t for t in out if _name(t) not in bl]
        return out

    def to_spec(self) -> Dict[str, Any]:
        """The raw spec dict (for signing/persisting)."""
        d = dict(self._s)
        d["agent"] = self.agent
        return d

    # ── constructors ────────────────────────────────────────────────────────────
    @classmethod
    def ephemeral(cls, goal: str, title: Optional[str] = None,
                  agent: Optional[str] = None) -> "Mission":
        """A quick one-off task: only the goal is set, everything else inherits the
        agent's defaults. This is what `gorgon mission "<goal>"` runs (unsigned)."""
        return cls({"title": title or "(ad-hoc task)", "goal": goal}, agent=agent)


def validate(spec: Dict[str, Any]) -> List[str]:
    """Structural problems with a mission spec — the required fields, mainly. Returns
    a list of human-readable issues ([] when the spec is well-formed)."""
    issues: List[str] = []
    for f in REQUIRED_FIELDS:
        if not (spec or {}).get(f):
            issues.append(f"missing required field: {f}")
    return issues
