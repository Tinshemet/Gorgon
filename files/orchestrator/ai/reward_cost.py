"""
reward_cost.py — the certainty-equivalent (μ, σ²) decision layer (reward-cost step 2).

Cost-only planning has a trivial optimum: inaction (a skipped branch costs ~0, so
avoidance always wins). This layer flips it to **reward − cost** so ACTION is preferred
when a goal is worth it, and passivity has a price (forgone reward).

The design (per gorgon-reward-cost-tree):
    cost(ℓ) = w_r·resource + w_t·time + κ·¬rev        # catalog/contract facts
    μ(g)    = P(g)·R_g − Σcost − H·open_steps         # reward books on branch CLOSURE
    σ²(g)   = P(g)(1−P(g))·R_g² + Σ child-variance
    CE(g)   = μ(g) − (λ/2)·σ²(g)                      # certainty-equivalent (mean-variance)
    P(g)    = Π p_world(leaf)                         # world-noise; p_self is a global dial (step 5)
    AND = all children needed (gate on Π p);  OR = the max-CE alternative.

Key invariants the math enforces:
- Reward is GOAL-RELATIVE (books only on closing a branch), never intrinsic to a tool —
  so "solve branches beats spawn leaves" is a theorem, not a rule, and reward-hacking a
  tool for points is impossible.
- Destructiveness is NOT in this scalar (that would make the tree passive / afraid to do
  necessary irreversible work) — it is the CONSENT gate (step 3). Only a small
  reversibility route-bias κ lives in cost.
- Value BACKUP fixes the horizon effect: a locally-costly leaf under a high-reward parent
  has positive BACKED-UP CE, so it isn't greedily pruned.

Pure and config-driven — the constants (θ, λ, H, κ, weights, p_world, R) are the real
calibration risk, so they're all in DEFAULTS and overridable per call.
"""
from typing import Any, Callable, Dict, List, Optional

# The calibration knobs. Structure is designed; VALUES are not — tune per deployment.
DEFAULTS: Dict[str, float] = {
    "theta":      0.0,   # worth-it threshold on CE (act iff CE > θ)
    "lambda":     0.5,   # risk aversion; risk_appetite = −λ (CE = μ − (λ/2)σ²)
    "H":          0.05,  # holding / WIP cost per open step on a branch
    "kappa":      0.2,   # irreversibility route-bias in a leaf's cost
    "w_resource": 1.0,   # weight on resource commitment
    "w_time":     0.3,   # weight on time
    "time":       1.0,   # default per-leaf time estimate
    "p_world":    0.9,   # default per-leaf world-success probability
    "R":          1.0,   # default signed reward for closing the ROOT goal (contract sets this)
    "beta":       1.0,   # how hard p_self raises the worth-it threshold θ
    "gamma":      1.0,   # how hard p_self raises risk-aversion λ
    "rho_min":    0.5,   # min acceptable branch success prob (sets the depth budget)
}


def cfg_with(overrides: Optional[Dict[str, float]]) -> Dict[str, float]:
    c = dict(DEFAULTS)
    if overrides:
        c.update(overrides)
    return c


def leaf_cost(risk: Optional[Dict[str, Any]], cfg: Dict[str, float]) -> float:
    """cost(ℓ) = w_r·resource + w_t·time + κ·¬rev. From the tool's risk facts
    (resource ≈ commitment; reversibility = a small route-bias). Destructiveness is
    deliberately NOT here — it's the consent gate, not a cost."""
    r = risk or {}
    resource = float(r.get("commitment", 0.0))
    irr = 0.0 if r.get("reversible", True) else 1.0
    return cfg["w_resource"] * resource + cfg["w_time"] * cfg["time"] + cfg["kappa"] * irr


def ce(mu: float, var: float, cfg: Dict[str, float]) -> float:
    """Certainty-equivalent: mean penalized by variance × risk-aversion."""
    return mu - (cfg["lambda"] / 2.0) * var


def worth_it(node_ce: float, cfg: Dict[str, float]) -> bool:
    """The worth-it gate: pursue iff backed-up CE clears θ. A reward-less goal has
    CE ≤ θ (skip — nothing to gain); a goal whose reward beats its cost clears it."""
    return node_ce > cfg["theta"]


def backup(node: Dict[str, Any], cfg: Dict[str, float]) -> Dict[str, float]:
    """Back up (mu, var, p, ce) through an abstract plan node.

    node = {"kind": "leaf", "cost": c, "p": p, "reward": r}
         | {"kind": "and"|"or", "children": [...], "reward": R_close}
    AND gates on all children (P = Π p, sum μ/σ²) and books R_close·P at closure, minus
    the WIP holding cost. OR takes the single max-CE alternative.
    """
    kind = node.get("kind", "leaf")
    if kind == "leaf":
        p = float(node.get("p", cfg["p_world"]))
        r = float(node.get("reward", 0.0))
        cost = float(node.get("cost", 0.0))
        mu = p * r - cost
        var = p * (1 - p) * r * r
        return {"mu": mu, "var": var, "p": p, "ce": ce(mu, var, cfg)}

    kids = [backup(c, cfg) for c in node.get("children", [])]
    R = float(node.get("reward", 0.0))
    if kind == "or":
        if not kids:
            return {"mu": 0.0, "var": 0.0, "p": 1.0, "ce": 0.0}
        # OR = the single best alternative. The node's closure reward rides on the CHOSEN
        # alternative succeeding, so book R·p PER alternative BEFORE the max — a higher-p
        # option can win on total value even with lower standalone CE (the reward term
        # R·p rewards reliability). Booking after the max would pick the wrong branch.
        def closed(k: Dict[str, float]) -> Dict[str, float]:
            P = k["p"]
            mu = k["mu"] + R * P
            var = k["var"] + P * (1 - P) * R * R
            return {"mu": mu, "var": var, "p": P, "ce": ce(mu, var, cfg)}
        return max((closed(k) for k in kids), key=lambda x: x["ce"])

    # AND
    P = 1.0
    sum_mu = sum_var = 0.0
    for k in kids:
        P *= k["p"]
        sum_mu += k["mu"]
        sum_var += k["var"]
    open_steps = len(kids)
    mu = sum_mu + R * P - cfg["H"] * open_steps
    var = sum_var + P * (1 - P) * R * R
    return {"mu": mu, "var": var, "p": P, "ce": ce(mu, var, cfg)}


import math


def p_self_estimate(ledger, default: float = 0.9) -> float:
    """The weak model's aggregate reliability `p̂_self`, measured BACKWARD from the
    ledger (fraction of executed leaves that succeeded). p_self is forward-UNmeasurable
    per-move (asking the model to self-rate is a second bad draw), so it's a GLOBAL
    control, never priced per-node. Empty ledger → `default`."""
    outs = [1.0 if e.get("ok") else 0.0 for e in (ledger or []) if e.get("tool")]
    return sum(outs) / len(outs) if outs else default


def dials(p_self: float, cfg: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Turn measured p_self into the decision constants (the design's p_self dials):
        θ = θ₀ + β(1−p̂),  λ = λ₀ + γ(1−p̂),  D_max = ⌊ln(ρ_min)/ln(p̂)⌋.
    A shakier model → higher worth-it bar, more risk-aversion, and a SHALLOWER depth
    budget (depth = a self-noise budget: brittle deep plans are cut)."""
    c = cfg_with(cfg)
    p = min(max(p_self, 0.01), 0.99)
    return {
        "p_self": round(p, 4),
        "theta":  round(c["theta"] + c["beta"] * (1 - p), 4),
        "lambda": round(c["lambda"] + c["gamma"] * (1 - p), 4),
        "D_max":  max(1, int(math.floor(math.log(c["rho_min"]) / math.log(p)))),
    }


def should_commit(risk: Optional[Dict[str, Any]], cfg: Optional[Dict[str, float]] = None,
                  *, reward: float = 0.0, p: Optional[float] = None) -> bool:
    """Deliberation scales with IRREVERSIBILITY (the corrigibility principle). A
    REVERSIBLE step just acts — reality is a free, perfect oracle (act-observe-correct),
    so no simulation. An IRREVERSIBLE/expensive step (can't course-correct) is gated on
    its SIMULATED certainty-equivalent: commit only if it's worth it."""
    c = cfg_with(cfg)
    if (risk or {}).get("reversible", True):
        return True                                  # act-observe-correct
    pw = c["p_world"] if p is None else p
    mu = pw * reward - leaf_cost(risk, c)
    var = pw * (1 - pw) * reward * reward
    return worth_it(ce(mu, var, c), c)


def economics(root: Dict[str, Any], *,
              cost_of: Callable[[str], Optional[Dict[str, Any]]],
              cfg: Optional[Dict[str, float]] = None,
              reward: Optional[float] = None,
              p_of: Optional[Callable[[str], float]] = None) -> Dict[str, Any]:
    """Turn a RESOLVED score.py tree into reward-cost economics.

    Walks the tree, prices each executed leaf via `cost_of(tool) -> risk`, books the
    root `reward` on the root closing (status done), and backs up (μ, σ², CE). Returns
    {mu, var, ce, cost, reward, worth_it} — the tree made reward-cost-aware.
    """
    c = cfg_with(cfg)
    R = c["R"] if reward is None else reward

    def to_plan(n: Dict[str, Any], is_root: bool) -> Dict[str, Any]:
        kids = n.get("children")
        if kids:
            kind = "or" if n.get("mode") == "or" else "and"
            # an OR node's untried alternatives (skipped) never ran — drop them so they
            # don't dilute the max-over-alternatives backup with 0-cost phantom leaves.
            if kind == "or":
                kids = [k for k in kids if k.get("status") != "skipped"] or kids
            return {"kind": kind,
                    "reward": R if (is_root and n.get("status") == "done") else 0.0,
                    "children": [to_plan(k, False) for k in kids]}
        tool = n.get("tool")
        risk = cost_of(tool) if tool else None
        cost = leaf_cost(risk, c) if tool else 0.0
        p = (p_of(tool) if (p_of and tool) else c["p_world"])
        # a bare root leaf that's done also earns the reward (single-step goal)
        r = R if (is_root and n.get("status") == "done") else 0.0
        return {"kind": "leaf", "cost": cost, "p": p, "reward": r}

    plan = to_plan(root, True)
    b = backup(plan, c)

    total_cost = [0.0]
    def walk_cost(n):
        t = n.get("tool")
        if t and not n.get("children"):
            total_cost[0] += leaf_cost(cost_of(t), c)
        for k in n.get("children", []):
            walk_cost(k)
    walk_cost(root)

    return {"mu": round(b["mu"], 4), "var": round(b["var"], 4), "ce": round(b["ce"], 4),
            "cost": round(total_cost[0], 4), "reward": R if root.get("status") == "done" else 0.0,
            "worth_it": worth_it(b["ce"], c)}
