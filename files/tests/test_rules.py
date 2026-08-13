#!/usr/bin/env python3
"""
test_rules.py — deterministic precedence + coherence for a contract's weighted rules (E1).

Proves: rules resolve to a deterministic precedence order (lowest weight first, 0 =
inviolable, ties broken by declaration index — so precedence is never ambiguous/cyclic),
and the coherence checker flags the ways a rule set silently contradicts itself (a rule
at two weights, a duplicate, a bad weight), which review() then refuses before signing.

Run:  PYTHONPATH=files python3 files/tests/test_rules.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.agent.contract.rules import resolve, conflicts
from orchestrator.ai.agent.forge import assemble

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def main():
    print("resolve: strongest-first, 0 = inviolable, stable tie-break")
    rules = [
        {"text": "prefer stealth", "weight": 2},
        {"text": "never touch prod", "weight": 0},
        {"text": "log everything", "weight": 1},
        {"text": "clean up after", "weight": 1},     # same weight as 'log' → tie-break by index
    ]
    r = resolve(rules)
    check("ordered by weight ascending", [x["weight"] for x in r] == [0, 1, 1, 2])
    check("weight-0 rule is first and flagged inviolable", r[0]["text"] == "never touch prod" and r[0]["inviolable"])
    check("equal weights keep declaration order (deterministic tie-break)",
          [x["text"] for x in r if x["weight"] == 1] == ["log everything", "clean up after"])
    check("ranks are a dense total order (no ambiguity/cycle)", [x["rank"] for x in r] == [0, 1, 2, 3])

    print("\nconflicts: a coherent rule set is clean")
    check("no problems for well-formed rules", conflicts(rules) == [])
    check("empty/None rules are fine", conflicts([]) == [] and conflicts(None) == [])

    print("\nconflicts: the SAME rule at two weights is a silent contradiction")
    dbl = [{"text": "avoid noise", "weight": 1}, {"text": "Avoid  noise", "weight": 3}]
    probs = conflicts(dbl)
    check("flagged as a two-weight contradiction (case/space-insensitive match)",
          any("two weights" in p for p in probs))

    print("\nconflicts: duplicates and bad weights")
    check("exact duplicate flagged",
          any("duplicate" in p for p in conflicts([{"text": "x", "weight": 1}, {"text": "x", "weight": 1}])))
    check("negative weight flagged", any("negative" in p for p in conflicts([{"text": "x", "weight": -1}])))
    check("non-numeric weight flagged", any("non-numeric" in p for p in conflicts([{"text": "x", "weight": "hi"}])))
    check("empty text flagged", any("empty text" in p for p in conflicts([{"text": "   ", "weight": 1}])))

    print("\nreview() refuses a self-contradictory rule set (sign gate)")
    grgn = {"persona": {"name": "tester"},
            "contract": {"tools": {}, "forbidden": [], "toolkit": ["scan_network"], "tool_mode": "whitelist",
                         "rules": [{"text": "be careful", "weight": 0}, {"text": "be careful", "weight": 2}]}}
    issues = assemble.review(grgn)
    check("review surfaces the rule contradiction", any("two weights" in i for i in issues))
    try:
        assemble.sign(grgn, "banana")
        signed_ok = True
    except ValueError:
        signed_ok = False
    check("sign() refuses the incoherent rule set", signed_ok is False)

    print("\nRuleSet resolver — the unified law drives enforcement")
    from orchestrator.ai.agent.contract.rules import RuleSet
    law = [
        {"w": 0, "kind": "access",     "text": "never delete prod",  "effect": {"forbid": ["delete_vm"]}},
        {"w": 2, "kind": "access",     "text": "may recon",          "effect": {"allow": ["scan_network"]}},
        {"w": 1, "kind": "delegation", "text": "destructive irrev → double",
         "effect": {"tier": "double", "when": {"reversible": False, "destructiveness": ">=0.7"}}},
        {"w": 2, "kind": "delegation", "text": "decoy deletes → y/n", "effect": {"tier": "normal", "tools": ["delete_vm"]}},
        {"w": 1, "kind": "provisions", "text": "more stealth effort", "effect": {"reward_cost": {"alpha": 0.4}}},
        {"w": 1, "kind": "decree",     "text": "fleet reachable",     "effect": {"success_predicate": [{"criterion": "mesh", "target": "fleet"}]}},
    ]
    rs = RuleSet(law)
    check("ACCESS w:0 forbid wins (the blacklist)", rs.forbids("delete_vm") is True)
    check("ACCESS allow surfaces the tool", "scan_network" in rs.allowed_tools())
    check("a tool no rule mentions falls to the base forbidden list",
          rs.forbids("wipe_disk", base_forbidden=["wipe_disk"]) is True and rs.forbids("launch_vm") is False)
    check("DELEGATION: risky delete → 'when' rule (w:1) beats the tools rule (w:2) → double",
          rs.tier_for("delete_vm", {"reversible": False, "destructiveness": 1.0}, "name") == "double")
    check("DELEGATION: reversible delete → w:1 when misses, w:2 tools rule → normal",
          rs.tier_for("delete_vm", {"reversible": True, "destructiveness": 0.1}, "name") == "normal")
    check("DELEGATION: an unruled tool keeps its substrate tier", rs.tier_for("create_vm", {}, "normal") == "normal")
    check("PROVISIONS override the reward-cost knobs", rs.reward_cost_overrides() == {"alpha": 0.4})
    check("DECREE extends the goal predicate", rs.decrees() == [{"criterion": "mesh", "target": "fleet"}])
    check("by_weight groups the law into tiers", sorted(rs.by_weight().keys()) == [0, 1, 2])

    print("\nSCOPE (K5) — an allowlist WITH A BINDING. This step carries the law; matching comes later")
    scoped = [
        {"w": 0, "kind": "access", "text": "recon is confined to the lab network",
         "effect": {"scope": {"tools": ["scan_network"], "args": {"net_name": "lab"}}}},
        {"w": 1, "kind": "access", "text": "and to the dmz",
         "effect": {"scope": {"tools": ["scan_network"], "args": {"net_name": "dmz"}}}},
        {"w": 1, "kind": "access", "text": "deletes only touch scratch machines",
         "effect": {"scope": {"tools": ["delete_vm"],
                              "object": {"kind": "vm", "label": "scratch"}}}},
    ]
    ss = RuleSet(scoped)
    check("a scoped tool comes back with the context it is confined to",
          [s["context"] for s in ss.scopes("scan_network")] == [{"net_name": "lab"}, {"net_name": "dmz"}])
    check("BOTH scopes on one tool come back — a union, not a first-match cut (ruling c)",
          len(ss.scopes("scan_network")) == 2)
    check("scopes arrive strongest-first", [s["w"] for s in ss.scopes("scan_network")] == [0, 1])
    check("an ARGS binding is marked as a literal", ss.scopes("scan_network")[0]["bind"] == "args")
    check("an OBJECT binding is carried whole, not flattened into args",
          ss.scopes("delete_vm")[0]["bind"] == "object"
          and ss.scopes("delete_vm")[0]["context"] == {"kind": "vm", "label": "scratch"})
    check("a scope carries its rule text, so a refusal can name what refused it",
          ss.scopes("delete_vm")[0]["text"] == "deletes only touch scratch machines")

    print("  the containment rule — one authored scope must not ban the world")
    check("A TOOL NO SCOPE NAMES IS UNGOVERNED, NOT REFUSED",
          ss.scopes("launch_vm") == [] and ss.forbids("launch_vm") is False)
    check("a scope is not a ban: scoping scan_network does not forbid scan_network",
          ss.forbids("scan_network") is False)
    check("an empty/None law has no scopes", RuleSet([]).scopes("x") == [] and RuleSet(None).scopes("x") == [])

    print("  ruling (b) — a scope CANNOT lift a ban, and the ban answers first")
    check("delete_vm stays forbidden even though a scope grants it a context",
          RuleSet(law + scoped).forbids("delete_vm") is True)
    check("CONTROL: adding the scope law changes NO existing ban verdict",
          all(RuleSet(law + scoped).forbids(t) == RuleSet(law).forbids(t)
              for t in ("delete_vm", "scan_network", "launch_vm", "clone_vm", "wipe_disk"))
          and RuleSet(law + scoped).allowed_tools() == RuleSet(law).allowed_tools())

    print("\nSCOPE coherence — an unreadable scope is refused at SIGN, never resolved at run")
    def _one(effect):
        return conflicts([{"w": 1, "kind": "access", "text": "x", "effect": effect}])
    check("a scope naming no tools is flagged",
          any("binds nothing to nothing" in p for p in _one({"scope": {"args": {"net_name": "lab"}}})))
    check("a scope with no context is flagged — that is an allow, not a scope",
          any("not a scope" in p for p in _one({"scope": {"tools": ["scan_network"]}})))
    check("a scope binding BOTH args and object is flagged (union is not an AND)",
          any("BOTH args and object" in p for p in
              _one({"scope": {"tools": ["t"], "args": {"a": 1}, "object": {"kind": "vm"}}})))
    check("a scope that is not an object at all is flagged",
          any("must be an object" in p for p in _one({"scope": ["scan_network"]})))
    check("an OBJECT binding carrying a group is flagged — a scope is a conjunction",
          any("write a set of permitted targets as two scopes" in p for p in
              _one({"scope": {"tools": ["delete_vm"],
                              "object": {"kind": "vm", "any": [{"label": "a"}, {"label": "b"}]}}})))
    check("an OBJECT binding with no kind is flagged — a select without one denotes nothing",
          any("names no kind" in p for p in
              _one({"scope": {"tools": ["delete_vm"], "object": {"label": "scratch"}}})))
    check("an OBJECT binding narrowing nothing beyond the kind is flagged (admits every member)",
          any("narrows nothing beyond the kind" in p for p in
              _one({"scope": {"tools": ["delete_vm"], "object": {"kind": "vm"}}})))
    check("a well-formed scope law is clean", conflicts(scoped) == [])
    check("DEAD LAW: a scope on a tool the same law BANS is flagged",
          any("can never admit anything" in p for p in conflicts(law + scoped)))
    check("...and lifting the ban clears it (the control — the check tracks the ban, not the name)",
          not any("can never admit anything" in p for p in
                  conflicts([r for r in law if (r.get("effect") or {}).get("forbid") != ["delete_vm"]] + scoped)))

    print("\ncoherence + backward-compat")
    check("clean law → no conflicts", conflicts(law) == [])
    check("unknown kind flagged", any("unknown kind" in p for p in conflicts([{"w": 1, "kind": "wat", "text": "x", "effect": {"a": 1}}])))
    check("effect-bearing kind with no effect flagged",
          any("no effect" in p for p in conflicts([{"w": 1, "kind": "delegation", "text": "x"}])))
    check("legacy {text, weight} rules still resolve (no kind → documentary)",
          [r["weight"] for r in resolve([{"text": "old rule", "weight": 3}])] == [3])
    check("empty ruleset is inert", RuleSet([]).forbids("anything") is False and RuleSet(None).decrees() == [])

    print("\nintegration: the LAW drives the live Contract accessors (law over physics)")
    import json
    from orchestrator.ai.agent.contract.core import Contract
    _files = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    g = json.load(open(os.path.join(_files, "orchestrator/ai/agent/doorman.grgn")))
    g["contract"]["rules"] = [
        {"w": 0, "kind": "access",     "text": "clone is a red line",   "effect": {"forbid": ["clone_vm"]}},
        {"w": 1, "kind": "delegation", "text": "create needs YES+name", "effect": {"tier": "double", "tools": ["create_vm"]}},
        {"w": 1, "kind": "provisions", "text": "more effort",           "effect": {"reward_cost": {"alpha": 0.5}}},
        {"w": 1, "kind": "decree",     "text": "fleet reachable",       "effect": {"success_predicate": [{"criterion": "mesh", "target": "fleet"}]}},
    ]
    c = Contract(g, "doorman", "signed")
    check("ACCESS rule forbids clone_vm (was allowed by physics)", c.is_forbidden("clone_vm") is True)
    check("DELEGATION lifts create_vm's tier normal → double", c.resolve_tier("create_vm") == "double")
    check("an unruled tool keeps its substrate tier", c.resolve_tier("stop_vm") == "normal")
    check("PROVISIONS override the reward-cost cfg", c.reward_cost_cfg().get("alpha") == 0.5)
    check("DECREE extends the goal predicate", {"criterion": "mesh", "target": "fleet"} in (c.goal_predicate() or []))
    g["contract"]["forbidden"] = ["delete_vm"]
    check("legacy `forbidden` still enforced (migrated to a w:0 access rule)",
          Contract(g, "doorman", "signed").is_forbidden("delete_vm") is True)

    print("\nMISSION-SCOPED rules — the human's per-run law (tighten/adjust, never waive a red line)")
    from orchestrator.ai.mission.mission import Mission
    g2 = json.load(open(os.path.join(_files, "orchestrator/ai/agent/doorman.grgn")))
    g2["contract"]["rules"] = [{"w": 0, "kind": "access", "text": "never delete", "effect": {"forbid": ["delete_vm"]}}]
    g2["contract"]["forbidden"] = []
    cc = Contract(g2, "lab", "signed")
    check("baseline: campaign forbids delete_vm; create_vm is normal",
          cc.is_forbidden("delete_vm") is True and cc.resolve_tier("create_vm") == "normal")
    cc.push_rules([
        {"w": 1, "kind": "delegation", "text": "create is silent this mission", "effect": {"tier": "none", "tools": ["create_vm"]}},
        {"w": 0, "kind": "access",     "text": "allow delete this mission",      "effect": {"allow": ["delete_vm"]}},
    ])
    check("a mission rule ADJUSTS a weaker gate (create_vm → none for this run)", cc.resolve_tier("create_vm") == "none")
    check("a mission rule CANNOT waive the campaign w:0 red line (delete_vm still forbidden)",
          cc.is_forbidden("delete_vm") is True)
    cc.pop_rules()
    check("after the run the campaign's own law is restored (create_vm → normal)", cc.resolve_tier("create_vm") == "normal")
    m = Mission({"goal": "x", "rules": [{"w": 1, "kind": "delegation", "text": "t", "effect": {"tier": "none", "tools": ["stop_vm"]}}]}, agent="lab")
    check("Mission.rules() exposes the mission's own law", len(m.rules()) == 1 and m.rules()[0]["kind"] == "delegation")

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
