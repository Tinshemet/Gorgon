#!/usr/bin/env python3
"""
test_mission.py — the Mission model (contracts create agents · agents consume missions).

A mission is a tasking; unset fields INHERIT the agent's defaults. Covers required-field
validation, default inheritance, importance-scaled reward, blacklist union (a mission
adds limits, never removes the agent's), and whitelist/blacklist tool filtering.

Run:  PYTHONPATH=files python3 files/tests/test_mission.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.mission import Mission, validate
from orchestrator.ai import contract as c

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
    print("validation: title + goal are required, the rest optional")
    check("missing goal is flagged", validate({"title": "x"}) == ["missing required field: goal"])
    check("missing title is flagged", validate({"goal": "y"}) == ["missing required field: title"])
    check("title + goal is enough", validate({"title": "x", "goal": "y"}) == [])

    print("\nephemeral: only the goal is set, everything inherits the agent")
    m = Mission.ephemeral("find the billing email")
    check("goal set", m.goal == "find the billing email")
    check("reward inherits the agent default", m.reward() == c.default_reward())
    check("no predicate (acceptance falls to Library + findings)", m.predicate() is None)
    check("whitelist inherits the agent toolkit", m.whitelist() == c.default_toolkit())
    check("blacklist inherits the agent red lines", m.blacklist() == sorted(set(c.default_blacklist())))

    print("\nexplicit: importance SCALES reward; mission values override defaults")
    m2 = Mission({"title": "Recon", "goal": "map web01", "reward": 2.0, "importance": 3.0})
    check("reward = base × importance (2 × 3 = 6)", m2.reward() == 6.0)
    check("importance surfaced", m2.importance() == 3.0)

    print("\nblacklist union: a mission ADDS limits, never removes the agent's")
    m3 = Mission({"title": "t", "goal": "g", "tool_blacklist": ["delete_vm"]})
    check("mission red line present", "delete_vm" in m3.blacklist())
    check("agent red lines still present", set(c.default_blacklist()) <= set(m3.blacklist()))

    print("\ntool filtering: whitelist keeps, blacklist drops")
    tools = [{"function": {"name": n}} for n in ("create_vm", "delete_vm", "list_vms")]
    m4 = Mission({"title": "t", "goal": "g",
                  "tool_whitelist": ["create_vm", "delete_vm"], "tool_blacklist": ["delete_vm"]})
    kept = [t["function"]["name"] for t in m4.filter_tools(tools)]
    check("whitelisted-and-not-blacklisted survives", kept == ["create_vm"])

    print("\npredicate: a mission supplies its own acceptance clauses")
    m5 = Mission({"title": "t", "goal": "g",
                  "success_predicate": [{"criterion": "found", "target": "ip(web01)"}]})
    check("predicate returned", m5.predicate() == [{"criterion": "found", "target": "ip(web01)"}])

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
