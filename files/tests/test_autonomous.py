#!/usr/bin/env python3
"""
test_autonomous.py — the autonomous execution loop (autonomous.run_autonomous).

Drives the FULL loop against a stub "world" (VMs the stub executor mutates and the
Library-backed verifier reads), with a scripted model — no Ollama, no real executor.
Proves the loop end-to-end: decompose → execute → verify against reality → backtrack →
halt, all with no human.

Run:  PYTHONPATH=files python3 files/tests/test_autonomous.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.autonomous import run_autonomous, make_library_verifier
from orchestrator.ai.mission.mission import Mission

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


class World:
    """A tiny stateful world: the executor mutates it, the verifier reads it — so
    verification is real (against reality), not a stub that always says yes."""
    def __init__(self, lie=False):
        self.vms = {}
        self.lie = lie   # when True, create_vm reports success but doesn't change the world

    def execute(self, tool, args):
        n = args.get("name") or args.get("new_name")
        if tool == "create_vm" and not self.lie:
            self.vms[n] = {"status": "stopped"}
        elif tool == "launch_vm" and n in self.vms:
            self.vms[n]["status"] = "running"
        elif tool == "stop_vm" and n in self.vms:
            self.vms[n]["status"] = "stopped"
        elif tool == "delete_vm":
            self.vms.pop(n, None)
        return {"success": True}


def scripted(script):
    def _call(messages, tools):
        goal = messages[-1]["content"].replace("Goal: ", "")
        entry = script.get(goal)
        if entry is None:
            return {"message": {"tool_calls": []}}
        name, args = entry
        return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}
    return _call


_TOOLS = [{"type": "function", "function": {"name": n, "parameters": {}}}
          for n in ("create_vm", "launch_vm", "stop_vm", "delete_vm")]
# A wider set for the steering tests, which need the real network tool names.
_TOOLS2 = [{"type": "function", "function": {"name": n, "parameters": {}}}
           for n in ("create_vm", "launch_vm", "create_network", "add_vm_to_network",
                     "list_vms", "clarify", "check_system")]


def main():
    print("happy path: decompose → execute → verify against reality → done")
    w = World()
    model = scripted({
        "set up dev":  ("decompose", {"steps": ["create dev", "launch dev"]}),
        "create dev":  ("create_vm", {"name": "dev", "os_type": "linux"}),
        "launch dev":  ("launch_vm", {"name": "dev"}),
    })
    seen = []
    r = run_autonomous("set up dev", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, on_event=lambda e: seen.append(e["tool"]))
    check("root done", r["root"]["status"] == "done" and r["ok"] is True)
    check("both primitives executed in order", [e["tool"] for e in r["events"]] == ["create_vm", "launch_vm"])
    check("events streamed via on_event", seen == ["create_vm", "launch_vm"])
    check("world actually changed (dev running)", w.vms.get("dev", {}).get("status") == "running")
    check("summary counts", r["summary"]["executed"] == 2 and r["summary"]["unverified"] == 0)

    print("\nverified-completion is LIVE: a lying executor is caught")
    w = World(lie=True)   # create_vm returns success but never adds the VM
    model = scripted({"make dev": ("create_vm", {"name": "dev", "os_type": "linux"})})
    # reward=5 clears the whole-goal worth-it gate (a single create_vm nets negative at
    # the bare default R=1.0 and would be refused up-front) so verified-completion runs.
    r = run_autonomous("make dev", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, max_retries=1, reward=5.0)
    check("phantom success → not done", r["ok"] is False)
    check("summary flags unverified", r["summary"]["unverified"] >= 1 and r["root"]["status"] == "unverified")

    print("\ncontract HALT: an autonomous red line stops the loop")
    w = World()
    model = scripted({"wipe dev": ("delete_vm", {"name": "dev"})})
    # reward=5 clears the whole-goal worth-it gate so the run reaches the red-line gate
    # (a lone delete_vm nets negative at the bare default R=1.0 and would be refused first).
    r = run_autonomous("wipe dev", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, reward=5.0,
                       gate=lambda t, a: "halt" if t == "delete_vm" else "proceed")
    check("halted node blocked", r["root"]["status"] == "blocked" and r["root"].get("reason") == "contract_halt")
    check("nothing executed past the red line", r["events"] == [])
    check("summary records the halt", r["summary"]["halted"] == 1 and r["summary"]["executed"] == 0)

    print("\ncommit gate: an irreversible leaf not worth committing is blocked (reversible steps spared)")
    w = World()
    # A decompose root is unpriced at α=0, so the whole-goal gate passes and the per-leaf
    # commit gate is what's exercised: create_vm (reversible) always commits; delete_vm
    # (irreversible, cost 1.6) at R=1.0 has a negative simulated CE → blocked, not run.
    model = scripted({
        "risky plan": ("decompose", {"steps": ["note dev", "wipe dev"]}),
        "note dev":   ("create_vm", {"name": "dev", "os_type": "linux"}),
        "wipe dev":   ("delete_vm", {"name": "dev"}),
    })
    r = run_autonomous("risky plan", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, reward=1.0, max_revisions=0)
    kids = {c["goal"]: c for c in r["root"].get("children", [])}
    check("irreversible leaf blocked as not worth committing",
          kids.get("wipe dev", {}).get("status") == "blocked"
          and kids.get("wipe dev", {}).get("reason") == "not_worth_committing")
    check("the reversible step still committed (only the irreversible one was gated)",
          kids.get("note dev", {}).get("status") == "done" and "dev" in w.vms)

    print("\ndisposition is reported")
    check("result carries the active disposition", "disposition" in r)

    print("\nverifier unit: criteria checked against the registry")
    v = make_library_verifier(lambda: {"web": {"status": "running"}})
    check("present true", v("present", "create_vm", {"name": "web"}, {}) is True)
    check("absent true", v("absent", "delete_vm", {"name": "gone"}, {}) is True)
    check("running true", v("running", "launch_vm", {"name": "web"}, {}) is True)
    check("running false when absent", v("running", "launch_vm", {"name": "db"}, {}) is False)
    check("unknown criterion passes", v("mystery", "x", {"name": "web"}, {}) is True)

    print("\nMISSION end-to-end: declared sub_goals seed the tree, α credits them, verbose economics")
    w = World()
    # NOTE: the model script has NO decompose for the goal — the mission's sub_goals must
    # drive the decomposition (via the method-cache hard-seed), proving it's guaranteed.
    model = scripted({
        "create web": ("create_vm", {"name": "web", "os_type": "linux"}),
        "launch web": ("launch_vm", {"name": "web"}),
    })
    m = Mission({"title": "stand up web", "goal": "stand up web",
                 "sub_goals": ["create web", "launch web"],
                 "reward": 10.0, "importance": 2.0,
                 "reward_cost": {"alpha": 0.5}}, agent="barenboim")
    r = run_autonomous("stand up web", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, mission=m, verbose=True)
    kids = r["root"].get("children", [])
    check("mission sub_goals became the tree's top level (hard-seeded, not model-decomposed)",
          [c.get("goal") for c in kids] == ["create web", "launch web"])
    check("root closed and world changed", r["root"]["status"] == "done" and w.vms["web"]["status"] == "running")
    check("mission reward = base×importance flows into economics (R=20)", r["economics"]["reward"] == 20.0)
    check("verbose adds a PER-NODE economics tree", "economics_tree" in r
          and [c["goal"] for c in r["economics_tree"]["children"]] == ["create web", "launch web"])
    check("each closed sub-goal carries its own worth-it CE (α partial credit)",
          all("ce" in c for c in r["economics_tree"]["children"]))
    check("non-verbose run omits the per-node tree",
          "economics_tree" not in run_autonomous("stand up web", call_model=model, execute=World().execute,
                                                  tools=_TOOLS, vms_getter=lambda: {}, mission=m))

    print("\nwhole-goal worth-it gate: a not-worth-it goal is refused UP FRONT (nothing runs)")
    w = World()
    model = scripted({"make dev": ("create_vm", {"name": "dev", "os_type": "linux"})})
    seen = []
    # R=1.0 (bare default): create_vm's cost (~1.3) exceeds p·R, so the priced whole-goal
    # CE is ≤ θ → skip before executing. Contrast the reward=5 run above, which proceeds.
    r = run_autonomous("make dev", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, reward=1.0, on_event=lambda e: seen.append(e["tool"]))
    check("root skipped as not worth it (whole-goal gate)",
          r["root"]["status"] == "skipped" and r["root"].get("reason") == "not_worth_it"
          and r["root"].get("mode") == "whole_goal")
    check("nothing executed and world untouched", seen == [] and w.vms == {})
    check("the refusal carries the priced CE", "ce_est" in r["root"])

    print("\ncompound decomposition (Track 2): the HARNESS splits a fused 'do X and do Y' sub-goal")
    from orchestrator.ai.autonomous import make_compound_splitter
    sp = make_compound_splitter()
    check("an action-conjunction splits into its clauses",
          sp("create a vm named a and put it on lab network", []) == ["create a vm named a", "put it on lab network"])
    check("an atomic goal is NOT split", sp("create a vm named beta", []) is None)
    check("a noun-conjunction ('a and b') is NOT split (one action over a set)",
          sp("create two vms named alpha and beta", []) is None)
    check("a SHARED-VERB conjunction is NOT split (create a net AND a vm — the vm has no verb)",
          sp("create a network called lab and a vm named web, then put web on lab network", []) is None)
    # END-TO-END: the model fuses create+attach into one sub-goal; the harness splits it.
    class CompWorld:
        def __init__(self): self.vms = {}; self.nets = set()
        def execute(self, t, a):
            n = a.get("name") or a.get("vm_name"); net = a.get("net_name")
            if t == "create_vm": self.vms[n] = {"nets": set()}; return {"success": True}
            if t == "create_network": self.nets.add(net); return {"success": True}
            if t == "add_vm_to_network":
                if n in self.vms and net in self.nets: self.vms[n]["nets"].add(net); return {"success": True}
                return {"success": False, "error": "missing"}
            return {"success": True}
    cw = CompWorld()
    ctools = [{"type": "function", "function": {"name": x, "parameters": {}}}
              for x in ("create_vm", "create_network", "add_vm_to_network")]
    cmodel = scripted({
        "set up web": ("decompose", {"steps": ["make lab net", "create web and put web on lab network"]}),
        "make lab net": ("create_network", {"net_name": "lab"}),
        # "create web and put web on lab network" is DELIBERATELY unscripted — the harness must split it
        "create web": ("create_vm", {"name": "web"}),
        "put web on lab network": ("add_vm_to_network", {"vm_name": "web", "net_name": "lab"}),
    })
    r = run_autonomous("set up web", call_model=cmodel, execute=cw.execute, tools=ctools,
                       vms_getter=lambda: {k: {"status": "stopped"} for k in cw.vms}, reward=10.0)
    check("harness split the fused sub-goal → BOTH create and attach ran",
          "web" in cw.vms and cw.vms.get("web", {}).get("nets") == {"lab"})

    print("\ncollective decomposition (Track 1.1): the HARNESS loops a distributive op over the live set")
    from orchestrator.ai.autonomous import make_collective_expander
    ex = make_collective_expander(lambda: {"a": 1, "b": 1, "c": 1})
    check("distributive collective → one atomic step per member",
          ex("put them all on the lab network", []) ==
          ["put a on the lab network", "put b on the lab network", "put c on the lab network"])
    check("inherently-collective (ping each other) is NOT expanded", ex("make them all ping each other", []) is None)
    check("no collective phrase → None (atomic goal untouched)", ex("create a vm named web", []) is None)
    check("<2 members → None", make_collective_expander(lambda: {"solo": 1})("label them all", []) is None)

    print("\ncardinal creation (Track 1.1b): 'create N vms' mints N STABLE names deterministically")
    cx = make_collective_expander(lambda: {})   # no live entities — cardinal doesn't need them
    check("'create 5 vms' → 5 atomic creates with stable minted names",
          cx("create 5 vms", []) == [f"create a vm named vm{i}" for i in range(1, 6)])
    check("number-word count works ('create three machines' → vm1..vm3)",
          cx("create three machines", []) == ["create a vm named vm1", "create a vm named vm2", "create a vm named vm3"])
    check("deterministic/stable — the SAME call mints the SAME names (idempotent re-entry)",
          cx("create 5 vms", []) == cx("create 5 vms", []))
    check("explicit names are NOT overridden ('create two vms named alpha and beta' → not cardinal)",
          cx("create two vms named alpha and beta", []) is None)
    check("non-provisionable noun is ignored ('create 5 reports' → None)", cx("create 5 reports", []) is None)
    check("count of 1 is not a collective ('create 1 vm' → None)", cx("create 1 vm", []) is None)
    check("absurd count is bounded ('create 500 vms' → None, no detonation)", cx("create 500 vms", []) is None)
    check("'create 3 networks' generalizes → network1..network3",
          cx("create 3 networks", []) == ["create a network named network1", "create a network named network2", "create a network named network3"])
    # END-TO-END: the model NEVER scripts the loop; the harness expands "put them all on net0".
    class NetWorld:
        def __init__(self): self.vms = {}; self.nets = set()
        def execute(self, tool, a):
            n = a.get("name") or a.get("vm_name") or a.get("new_name"); net = a.get("net_name") or a.get("network")
            if tool == "create_vm": self.vms[n] = {"nets": set()}; return {"success": True}
            if tool == "create_network": self.nets.add(net); return {"success": True}
            if tool == "add_vm_to_network":
                if n in self.vms and net in self.nets: self.vms[n]["nets"].add(net); return {"success": True}
                return {"success": False, "error": "missing"}
            return {"success": True}
    nw = NetWorld()
    ntools = [{"type": "function", "function": {"name": x, "parameters": {}}}
              for x in ("create_vm", "create_network", "add_vm_to_network")]
    nmodel = scripted({
        "wire the lab": ("decompose", {"steps": ["create alpha", "create beta", "make net0", "put them all on net0"]}),
        "create alpha": ("create_vm", {"name": "alpha"}),
        "create beta":  ("create_vm", {"name": "beta"}),
        "make net0":    ("create_network", {"net_name": "net0"}),
        "put alpha on net0": ("add_vm_to_network", {"vm_name": "alpha", "net_name": "net0"}),
        "put beta on net0":  ("add_vm_to_network", {"vm_name": "beta", "net_name": "net0"}),
        # NOTE: "put them all on net0" is DELIBERATELY unscripted — the harness must loop it.
    })
    r = run_autonomous("wire the lab", call_model=nmodel, execute=nw.execute, tools=ntools,
                       vms_getter=lambda: {k: {"status": "stopped"} for k in nw.vms}, reward=10.0)
    check("harness looped the attach over BOTH members (the model never scripted the loop)",
          nw.vms.get("alpha", {}).get("nets") == {"net0"} and nw.vms.get("beta", {}).get("nets") == {"net0"})

    print("\nstate grounding: the planner context names the GROUPS, at parity with the chat digest")
    from orchestrator.ai.autonomous import render_state
    _s = render_state({"vm1": {"status": "stopped", "labels": ["fleet"], "flags": []},
                       "vm2": {"status": "running", "labels": ["fleet"], "flags": ["stealth"]},
                       "solo": {"status": "stopped"}})
    check("a VM's tags are shown, not just its status", "vm1(stopped tags=fleet)" in _s)
    check("labels and auto-flags are both tags", "vm2(running tags=fleet,stealth)" in _s)
    # The (B) defect: with no label anywhere in the context, a goal about a GROUP left the
    # model to invent an identifier for it — and it reached for the network name it had
    # just used. A group is addressed by its label, so the label must be in the context.
    check("the fleet groupings are named (label → members)",
          "FLEETS (label/flag → members): fleet=[vm1, vm2]; stealth=[vm2]" in _s)
    check("an untagged VM is still listed, with no tags clause", "solo(stopped)" in _s)
    check("no tags at all → no FLEETS line",
          "FLEETS" not in render_state({"a": {"status": "stopped"}}))
    check("no VMs → the unchanged empty-state warning",
          render_state({}).startswith("CURRENT STATE: no VMs exist yet"))

    print("\nstate check: is a leaf goal's effect ALREADY in place? (state answers, not the model)")
    from orchestrator.ai.autonomous import make_state_check
    _vms = {"web": {"status": "running", "labels": ["fleet"], "flags": []},
            "db":  {"status": "stopped", "labels": [], "flags": ["stealth"]}}
    _nets = {"success": True, "networks": [{"name": "lab", "members": ["web"]},
                                           {"name": "empty", "members": []}]}
    sat = make_state_check(lambda: _vms, lambda t, a: _nets if t == "list_networks" else {})
    check("create a vm that EXISTS → satisfied", sat("create a vm named web") is True)
    check("create a vm that does NOT exist → not satisfied", sat("create a vm named ghost") is False)
    check("create a network that exists → satisfied", sat("create a network called lab") is True)
    check("create a network that doesn't → not satisfied", sat("create a network called nope") is False)
    check("attach that already holds → satisfied", sat("put web in the network called lab") is True)
    check("attach that does NOT hold → not satisfied", sat("put db in the network called lab") is False)
    check("'<net> network' phrasing works too", sat("add web to the lab network") is True)
    check("a label already carried → satisfied", sat("give web the 'fleet' label") is True)
    check("a label NOT carried → not satisfied", sat("give db the 'fleet' label") is False)
    check("an auto-FLAG counts as a tag", sat("give db the 'stealth' label") is True)
    check("label phrasing variants", sat("add the label fleet to web") is True and sat("label web as fleet") is True)
    check("launch of a RUNNING vm → satisfied", sat("launch web") is True)
    check("launch of a stopped vm → not satisfied", sat("launch db") is False)
    check("stop of a STOPPED vm → satisfied", sat("stop db") is True)
    check("stop of a running vm → not satisfied", sat("stop web") is False)
    # The safety direction: never claim a satisfaction the state doesn't show.
    # A COMPOUND goal is not satisfied because ONE of its clauses is — the rules match a
    # clause, so without this guard "create a vm named web and launch it" would report
    # satisfied off the create alone, claiming done for work that never happened.
    check("a compound goal is not satisfied by one finished clause",
          sat("create a vm named web and launch it") is False
          and sat("create a vm named web, then launch it") is False)
    check("...while each clause on its own still answers",
          sat("create a vm named web") is True and sat("launch web") is True)
    check("an unrecognized goal shape is NEVER 'already done'",
          sat("make sure they all ping each other") is False and sat("do the thing") is False)
    check("'launch a vm named X' is NOT answered by mere existence (launch = start, not create)",
          sat("launch a vm named db") is False)
    check("DELETION is deliberately not answered (absent ≠ done; could be a mis-aimed target)",
          sat("delete web") is False and sat("delete ghost") is False)
    check("no executor → network questions are UNKNOWN, which reads as not-satisfied",
          make_state_check(lambda: _vms)("create a network called lab") is False)
    check("a failing executor can't crash the check",
          make_state_check(lambda: _vms, lambda t, a: (_ for _ in ()).throw(RuntimeError("down")))
          ("create a network called lab") is False)

    print("\ncardinal QUALIFIERS are carried, never dropped")
    # The bug this guards: "create 3 vms labelled 'red'" minted three bare creates and
    # threw the label away. Each create then succeeded, so the clause closed `done` having
    # labelled nothing — the harness manufacturing a false success.
    from orchestrator.ai.autonomous import _cardinal_create_steps as _card
    check("a label qualifier becomes real steps",
          _card("create 3 vms labelled 'red'") ==
          ["create a vm named red1", "create a vm named red2", "create a vm named red3",
           "give red1 the 'red' label", "give red2 the 'red' label", "give red3 the 'red' label"])
    check("the group NAMES itself after the label, so two groups can't collide",
          [s for s in _card("create 2 vms labelled 'blue'") if s.startswith("create")]
          == ["create a vm named blue1", "create a vm named blue2"])
    check("a plain cardinal is unchanged", _card("create 5 vms")
          == [f"create a vm named vm{i}" for i in range(1, 6)])
    check("an UNPARSEABLE qualifier stands the whole thing down (never drop meaning)",
          _card("create 3 vms with 8gb ram") is None)

    print("\na verbless parallel clause inherits its verb instead of being orphaned")
    # "create 3 vms labelled 'red' and 2 vms labelled 'blue'" — the second half is an
    # object, not an action. Splitting it off strands work no step will ever do.
    _sp = make_compound_splitter()
    got = _sp("create 3 vms labelled 'red' and 2 vms labelled 'blue', "
              "put the red ones together on their own network, "
              "and put the blue ones on a different network", [])
    check("the fragment becomes a real action", got and got[1] == "create 2 vms labelled 'blue'")
    check("and all four clauses survive", got and len(got) == 4)
    check("a non-parallel fragment is NOT invented into a step (goal stays whole)",
          _sp("create a vm with 4 cores and 8gb ram", []) is None)

    print("\nattach-steer must not hijack a node that says CREATE")
    from planner.score.ledger_util import _attach_steer
    _led = [{"tool": "create_network", "args": {"net_name": "rednet"}, "ok": True}]
    _t2, steered = _attach_steer(_TOOLS2, "create a network called bluenet", _led, _TOOLS2)
    check("a create node is left alone (it needs the creator tool)",
          steered is False and "create_network" in [t["function"]["name"] for t in _t2])
    _t3, steered3 = _attach_steer(_TOOLS2, "put blue1 on the network called bluenet", _led, _TOOLS2)
    check("a real attach node is still steered", steered3 is True
          and "add_vm_to_network" in [t["function"]["name"] for t in _t3])

    print("\nanonymous-network prereq (Track 1.4b): an UNNAMED shared network is named + created FIRST")
    ax = make_collective_expander(lambda: {"a": 1, "b": 1})
    check("'put them all in a network' → create net1 first, every member threaded to it",
          ax("put them all in a network", []) ==
          ["create a network called net1",
           "put a in the network called net1", "put b in the network called net1"])
    check("the preposition is preserved ('connect them all to a network')",
          ax("connect them all to a network", [])[1] == "connect a to the network called net1")
    check("determiner variants collapse to ONE net ('on the same private network')",
          ax("put them all on the same private network", []) ==
          ["create a network called net1",
           "put a on the network called net1", "put b on the network called net1"])
    check("a NAMED network is left alone (the prereq completer's job, no create prepended)",
          ax("put them all on the lab network", []) ==
          ["put a on the lab network", "put b on the lab network"])
    check("stable — the same collective threads the SAME net (idempotent re-entry)",
          ax("put them all in a network", []) == ax("put them all in a network", []))
    check("no collective, no threading ('put a in a network' stays the model's atomic job)",
          ax("put a in a network", []) is None)
    # END-TO-END: the cannibalization the fix targets — a sim where an attach either creates
    # OR attaches (one action), so a member whose step must do both ends up OFF the network.
    class AnonWorld:
        def __init__(self): self.vms = {"a": {"nets": set()}, "b": {"nets": set()}}; self.nets = set()
        def execute(self, t, ar):
            n = ar.get("name") or ar.get("vm_name"); net = ar.get("net_name") or ar.get("network")
            if t == "create_vm": self.vms[n] = {"nets": set()}; return {"success": True}
            if t == "create_network": self.nets.add(net); return {"success": True}
            if t == "add_vm_to_network":
                if n in self.vms and net in self.nets: self.vms[n]["nets"].add(net); return {"success": True}
                return {"success": False, "error": f"no network {net}"}
            return {"success": True}
    aw = AnonWorld()
    amodel = scripted({
        "network the fleet": ("decompose", {"steps": ["put them all in a network"]}),
        "create a network called net1": ("create_network", {"net_name": "net1"}),
        "put a in the network called net1": ("add_vm_to_network", {"vm_name": "a", "net_name": "net1"}),
        "put b in the network called net1": ("add_vm_to_network", {"vm_name": "b", "net_name": "net1"}),
        # "put them all in a network" is unscripted — the harness must name, create, and loop it.
    })
    r = run_autonomous("network the fleet", call_model=amodel, execute=aw.execute, tools=ntools,
                       vms_getter=lambda: {k: {"status": "stopped"} for k in aw.vms}, reward=10.0)
    check("BOTH members landed on the SAME minted network (no attach was cannibalized)",
          aw.vms.get("a", {}).get("nets") == {"net1"} and aw.vms.get("b", {}).get("nets") == {"net1"})

    print("\ndependency completion (Track 1.4): the harness injects a dropped prerequisite (create the network)")
    from orchestrator.ai.autonomous import make_prereq_completer
    pc = make_prereq_completer()
    check("plan references 'lab' but no step creates it → prepend the create",
          pc("g", ["create a vm named a and put it on lab network"])
          == ["create a network called lab", "create a vm named a and put it on lab network"])
    check("network already created in-plan → no duplicate",
          pc("g", ["create a network called lab", "add a to lab network"])
          == ["create a network called lab", "add a to lab network"])
    check("no network referenced → untouched", pc("g", ["create a vm named web", "launch web"])
          == ["create a vm named web", "launch web"])
    # END-TO-END: the model plans attach-to-network but FORGETS to create it; the harness completes it.
    class DepWorld:
        def __init__(self): self.vms = {}; self.nets = set()
        def execute(self, t, a):
            n = a.get("name") or a.get("vm_name"); net = a.get("net_name") or a.get("network")
            if t == "create_vm": self.vms[n] = {"nets": set()}; return {"success": True}
            if t == "create_network": self.nets.add(net); return {"success": True}
            if t == "add_vm_to_network":
                if n in self.vms and net in self.nets: self.vms[n]["nets"].add(net); return {"success": True}
                return {"success": False, "error": f"no network {net}"}
            return {"success": True}
    dw = DepWorld()
    dtools = [{"type": "function", "function": {"name": x, "parameters": {}}}
              for x in ("create_vm", "create_network", "add_vm_to_network")]
    dmodel = scripted({
        # the model's plan has NO create-network step — the harness must inject it
        "set up web on lab": ("decompose", {"steps": ["create a vm named web", "put web on lab network"]}),
        "create a network called lab": ("create_network", {"net_name": "lab"}),   # the INJECTED step
        "create a vm named web": ("create_vm", {"name": "web"}),
        "put web on lab network": ("add_vm_to_network", {"vm_name": "web", "net_name": "lab"}),
    })
    r = run_autonomous("set up web on lab", call_model=dmodel, execute=dw.execute, tools=dtools,
                       vms_getter=lambda: {k: {"status": "stopped"} for k in dw.vms}, reward=10.0)
    check("harness created the network the model forgot → the attach then SUCCEEDED",
          "lab" in dw.nets and dw.vms.get("web", {}).get("nets") == {"lab"})

    print("\nreference grounding (Track 1.2): bind a bare reference in a step to the parent's named entity")
    from orchestrator.ai.autonomous import make_step_grounder
    gr = make_step_grounder()
    check("bare 'vm' bound to the parent's single named entity",
          gr("create a vm named a and put it on lab network", ["create a vm named a", "add vm to lab network"])
          == ["create a vm named a", "add a to lab network"])
    check("bare 'it' bound too", gr("launch vm named web", ["start web", "ping it"]) == ["start web", "ping web"])
    check("two named entities → no binding (ambiguous)",
          gr("wire web and db", ["start the vm", "stop the vm"]) == ["start the vm", "stop the vm"])

    print("\nthrashing bound (Track 1.5): max_steps stops a non-converging run instead of burning calls")
    from planner.score import run_score as _run_score
    from planner.engine import Engine as _Engine
    calls = []
    def _fail_exec(t, a): calls.append(t); return {"success": False, "error": "nope"}
    # No estimator (so CE-abandon can't save us) + a leaf that always fails + a big retry
    # budget: only max_steps stops the backtrack runaway.
    r = _run_score("loop", call_model=scripted({"loop": ("create_vm", {"name": "x"})}),
                   execute=_fail_exec, tools=_TOOLS, engine=_Engine(legal_filter=lambda *a: False),
                   max_retries=50, max_steps=5)
    check("the run TERMINATED under the step budget (bounded calls, no runaway)", len(calls) <= 6)
    check("a node closed blocked:step_budget", "step_budget" in str(r["root"]))

    print("\ngoal-level honesty END-TO-END: a structurally-complete assurance goal with a broken mesh → unverified")
    # A world whose fleet ping reports NOT all-reachable → the engine records mesh(fleet)=False.
    class FleetWorld:
        def __init__(self): self.labeled = set()
        def execute(self, tool, a):
            if tool == "add_label": self.labeled.add(a.get("name")); return {"success": True}
            if tool == "fleet" and a.get("action") == "ping":
                return {"success": True, "all_reachable": False}   # ran fine, but the mesh is BROKEN
            return {"success": True}
    fw = FleetWorld()
    ftools = [{"type": "function", "function": {"name": n, "parameters": {}}} for n in ("add_label", "fleet")]
    fmodel = scripted({
        "make sure they all ping each other": ("decompose", {"steps": ["label web fleet", "ping the fleet"]}),
        "label web fleet": ("add_label", {"name": "web", "label": "fleet"}),
        "ping the fleet":  ("fleet", {"label": "fleet", "action": "ping"}),
    })
    r = run_autonomous("make sure they all ping each other", call_model=fmodel, execute=fw.execute,
                       tools=ftools, vms_getter=lambda: {}, reward=10.0)
    check("every step ran (structurally complete)", r["summary"]["executed"] >= 2)
    check("but the goal closes UNVERIFIED, not done (mesh is broken, honesty rule fired)",
          r["root"]["status"] == "unverified" and r["ok"] is False)
    check("the broken mesh is on the record", r["findings"].get("mesh(fleet)") is False)

    print("\ngoal-level honesty rule: an assurance goal must be GROUNDED, or it closes unverified")
    from planner.findings import Findings
    from orchestrator.ai.autonomous import make_goal_verifier
    f = Findings()
    vg = make_goal_verifier(lambda: {}, findings=f)
    check("an ordinary goal keeps structural acceptance (None)",
          vg("create a vm named web", [], []) is None)
    check("assurance goal with NOTHING verified → not done (False)",
          vg("make sure they all ping each other", [], []) is False)
    f.record("mesh(fleet)", False, source="fleet")            # plan RAN but the mesh is broken
    check("assurance goal with a recorded-FALSE mesh → still not done",
          vg("make sure they all ping each other", [], []) is False)
    f2 = Findings(); f2.record("mesh(fleet)", True, source="fleet")
    vg2 = make_goal_verifier(lambda: {}, findings=f2)
    check("assurance goal with a USABLE mesh → done (True)",
          vg2("make sure they all ping each other", [], []) is True)
    check("generic assurance ('ensure') with no findings → not done",
          vg("ensure the database is migrated", [], []) is False)

    print("\np_self forward-feed loop: dials persist durably (no hand-fed prior=)")
    import tempfile
    import shared.bundle as _bundle
    from planner import findings_store as _store
    from orchestrator.ai.agent.contract import active_agent_key as _agent_key
    _bundle.AGENTS_ROOT = tempfile.mkdtemp()       # isolate the durable stores from ~/.gorgon
    w = World()
    model = scripted({
        "set up dev":  ("decompose", {"steps": ["create dev", "launch dev"]}),
        "create dev":  ("create_vm", {"name": "dev", "os_type": "linux"}),
        "launch dev":  ("launch_vm", {"name": "dev"}),
    })
    agent = _agent_key()
    check("no persisted dials before the first run", _store.load_reliability(agent) == {})
    r = run_autonomous("set up dev", call_model=model, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, persist_claims=True)
    stored = _store.load_reliability(agent)
    check("a persist_claims run WRITES the p_self dials",
          stored and stored.get("theta") == r["reliability"]["theta"]
          and stored.get("D_max") == r["reliability"]["D_max"])
    check("the dials store holds NO tool_counts (toolstats stays their SSOT)", "tool_counts" not in stored)
    # A fresh run with NO prior= must inherit the stored stance through the durable store.
    r2 = run_autonomous("set up dev", call_model=model, execute=World().execute, tools=_TOOLS,
                        vms_getter=lambda: {}, persist_claims=True)
    check("a later run (no prior=) still closes the loop and re-persists", _store.load_reliability(agent) != {})

    print("\nstructural memory: a PROVEN decomposition outlives the process")
    from planner import method_store as _mstore
    _mstore.clear(agent)
    def _goal_of(messages):
        return next((x["content"][6:] for x in messages
                     if x["role"] == "user" and x["content"].startswith("Goal: ")), "")
    def _steps_model(plans):
        """Decomposes the goals in `plans`; executes any 'create/launch … named <x>' leaf for
        ANY name — the leaves must work for a name the script never saw, since that's what a
        generalized method produces."""
        def _call(messages, tools):
            g = _goal_of(messages)
            if g in plans:
                return {"message": {"tool_calls": [{"function": {
                    "name": "decompose", "arguments": {"steps": plans[g]}}}]}}
            if g.startswith("create a vm named"):
                return {"message": {"tool_calls": [{"function": {
                    "name": "create_vm", "arguments": {"name": g.split()[-1], "os_type": "linux"}}}]}}
            if g.startswith("launch the vm named"):
                return {"message": {"tool_calls": [{"function": {
                    "name": "launch_vm", "arguments": {"name": g.split()[-1]}}}]}}
            return {"message": {"tool_calls": []}}
        return _call
    w = World()
    m1 = _steps_model({"prepare the rig xyz": ["create a vm named xyz", "launch the vm named xyz"]})
    r = run_autonomous("prepare the rig xyz", call_model=m1, execute=w.execute, tools=_TOOLS,
                       vms_getter=lambda: w.vms, reward=10.0, persist_claims=True)
    check("the run's plan closed done via the MODEL", r["root"]["status"] == "done"
          and r["root"].get("method") == "model")
    check("the decomposition was proven and persisted",
          [m["source"] for m in r["methods_learned"]] == ["prepare the rig xyz"]
          and [m["source"] for m in _mstore.load(agent)] == ["prepare the rig xyz"])
    # The claim under test: a LATER process inherits the skill. The model is given a goal of
    # the same shape but a new name, and CANNOT plan it — only the store can.
    w2 = World()
    m2 = _steps_model({})                    # no plan for ANY goal — the model cannot decompose
    def _cant_plan(msgs, tools):
        return m2(msgs, tools)
    r2 = run_autonomous("prepare the rig abc", call_model=_cant_plan, execute=w2.execute,
                        tools=_TOOLS, vms_getter=lambda: w2.vms, reward=10.0, persist_claims=True)
    check("a later run decomposes it from the STORE, with no model plan",
          r2["root"].get("method") == "cache" and r2["root"]["status"] == "done")
    check("and the steps really ran, generalized to the new name",
          [c["goal"] for c in r2["root"]["children"]]
          == ["create a vm named abc", "launch the vm named abc"] and "abc" in w2.vms)
    # The guard: an UNPROVEN method (its plan didn't close) must never reach the store.
    _mstore.clear(agent)
    w3 = World()
    m3 = _steps_model({"botch the rig q": ["create a vm named q", "do the impossible q"]})
    # "do the impossible q" matches no leaf rule → that child can't close → composite partial
    r3 = run_autonomous("botch the rig q", call_model=m3, execute=w3.execute, tools=_TOOLS,
                        vms_getter=lambda: w3.vms, reward=10.0, persist_claims=True)
    check("a plan that did NOT close is learned in-run but never persisted",
          r3["root"]["status"] != "done" and r3["methods_learned"] == []
          and _mstore.load(agent) == [])

    print("\nfailure memory: the next run is WARNED about a plan shape that already failed")
    _mstore.clear(agent); _mstore.clear_failures(agent)
    class BrokenAttach:
        def __init__(self): self.vms = {}
        def execute(self, tool, args):
            if tool == "create_vm":
                self.vms[args.get("name")] = {"status": "stopped"}; return {"success": True}
            return {"success": False, "error": "attach: no such network"}
    _ATOOLS = [{"type": "function", "function": {"name": n, "parameters": {}}}
               for n in ("create_vm", "attach")]
    def _wire_model(msgs, tools):
        g = _goal_of(msgs)
        if g == "wire up q":
            return {"message": {"tool_calls": [{"function": {"name": "decompose", "arguments": {
                "steps": ["create a vm named q", "attach q to netX"]}}}]}}
        if g.startswith("create a vm named"):
            return {"message": {"tool_calls": [{"function": {"name": "create_vm", "arguments":
                    {"name": g.split()[-1]}}}]}}
        if g.startswith("attach"):
            return {"message": {"tool_calls": [{"function": {"name": "attach", "arguments": {"name": "q"}}}]}}
        return {"message": {"tool_calls": []}}
    bw = BrokenAttach()
    r = run_autonomous("wire up q", call_model=_wire_model, execute=bw.execute, tools=_ATOOLS,
                       vms_getter=lambda: bw.vms, reward=10.0, persist_claims=True, max_revisions=1)
    check("the failed PLAN was harvested with its concrete post-mortem",
          r["root"]["status"] != "done"
          and any("no such network" in f["why"] for f in r["plans_failed"]))
    check("and persisted for the next run", len(_mstore.load_failures(agent)) == 1)
    seen = []
    def _watched(msgs, tools):
        seen.append(next((x["content"] for x in msgs if x["role"] == "system"), ""))
        return _wire_model(msgs, tools)
    bw2 = BrokenAttach()
    run_autonomous("wire up q", call_model=_watched, execute=bw2.execute, tools=_ATOOLS,
                   vms_getter=lambda: bw2.vms, reward=10.0, persist_claims=True, max_revisions=1)
    check("the NEXT run's planner is told it was tried before",
          any("TRIED BEFORE AND FAILED" in p and "no such network" in p for p in seen))
    check("a repeat is counted, not duplicated",
          [f["n"] for f in _mstore.load_failures(agent)] == [2])
    check("it is ADVISORY — the run still proceeded rather than being blocked",
          "q" in bw2.vms)
    # A plan that WORKS leaves no failure record.
    _mstore.clear_failures(agent)
    okw = World()
    r = run_autonomous("prepare the rig xyz", call_model=m1, execute=okw.execute, tools=_TOOLS,
                       vms_getter=lambda: okw.vms, reward=10.0, persist_claims=True)
    check("a successful plan records no failure",
          r["root"]["status"] == "done" and r["plans_failed"] == []
          and _mstore.load_failures(agent) == [])

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
