#!/usr/bin/env python3
"""
test_translator.py — the goal-normalisation front-end.

Covers the three things that decide whether this module is safe to ship:

  * it NEVER makes things worse — every failure path returns the original goal, so a
    dead model or a malformed answer costs nothing;
  * it may reword but NOT re-plan — clauses come back joined into one goal string, so
    the ordinary planner still does the decomposition. Handing the clauses through as
    sub-goals would seed the plan, which is the benchmark-gaming the standing principle
    in tests/bench/rungs.py forbids;
  * its vocabulary is DERIVED from the command catalog, so it cannot become the 34th
    hand-maintained word list.

No model is called: `call_model` is a stub returning the shapes ollama returns.

Run:  PYTHONPATH=. python3 tests/test_translator.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner.translator import (
    RESTATE_TOOL, canonical_examples, join_clauses, normalize_goal, _system_prompt,
)

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  \033[32mok\033[0m   {label}")
    else:
        _FAIL += 1
        print(f"  \033[31mFAIL\033[0m {label}")


def _answer(clauses, name="restate_goal"):
    """A model that calls restate_goal with these clauses."""
    def call_model(messages, tools):
        return {"message": {"tool_calls": [
            {"function": {"name": name, "arguments": {"clauses": clauses}}}]}}
    return call_model


def _raw(resp):
    """A model returning an arbitrary raw response."""
    return lambda messages, tools: resp


def main():
    print("the happy path: a paraphrase becomes canonical wording")
    # The measured failure this module exists for: `set up` is not in _CARDINAL_CREATE_RE,
    # so this phrasing created ZERO vms while 'create 3 vms labelled alpha' worked.
    g, clauses = normalize_goal(
        "set up three machines tagged alpha and make sure they can reach each other",
        _answer(["create 3 vms labelled alpha", "make sure they all ping each other"]))
    check("goal is restated", g == "create 3 vms labelled alpha, and make sure they all ping each other")
    check("clauses come back for the after-pass", clauses == [
        "create 3 vms labelled alpha", "make sure they all ping each other"])

    print("\nit rewords, it does not re-plan")
    # The clauses are JOINED, never returned as a step list. This is the mechanism that
    # keeps the planner doing the decomposition — see the module docstring.
    check("clauses are joined into ONE goal string", isinstance(g, str))
    check("joined with the conjunction the compound splitter already reads",
          ", and " in g)
    # Commas between, `and` only before the LAST — the shape the benchmark's own
    # hand-written goals use. Putting `and` before every clause would hand the splitter
    # N-1 clauses each beginning with a stray conjunction instead of one.
    check("joined the way a hand-written goal reads",
          join_clauses(["a", "b", "c"]) == "a, b, and c")
    check("two clauses take the plain form", join_clauses(["a", "b"]) == "a, and b")
    check("a single clause stays a single clause (no conjunction invented)",
          join_clauses(["create a vm named alpha"]) == "create a vm named alpha")
    check("no clauses is the empty string, not a stray conjunction", join_clauses([]) == "")

    # The join is only useful if the EXISTING splitter recovers the clauses from it —
    # otherwise translation would quietly flatten a multi-action goal into one blob.
    from orchestrator.ai.autonomous import make_compound_splitter
    _split = make_compound_splitter()
    _clauses = ["create 5 vms", "put them all in a network",
                "give them all the 'fleet' label"]
    _parts = _split(join_clauses(_clauses), []) or []
    check("the ordinary compound splitter recovers every clause", len(_parts) == 3)
    check("and recovers them in order, unmangled",
          [p.removeprefix("and ").strip() for p in _parts] == _clauses)

    print("\nevery failure path returns the ORIGINAL goal — never worse than today")
    original = "spin up five boxes"
    for label, model in [
        ("model raises",                    lambda m, t: (_ for _ in ()).throw(RuntimeError("ollama down"))),
        ("model returns None",              _raw(None)),
        ("model returns prose, no call",    _raw({"message": {"content": "sure!"}})),
        ("model calls the WRONG tool",      _answer(["x"], name="decompose")),
        ("clauses missing",                 _raw({"message": {"tool_calls": [
                                                {"function": {"name": "restate_goal", "arguments": {}}}]}})),
        ("clauses empty",                   _answer([])),
        ("clauses all blank",               _answer(["", "   "])),
        ("clauses not a list",              _raw({"message": {"tool_calls": [
                                                {"function": {"name": "restate_goal",
                                                              "arguments": {"clauses": "nope"}}}]}})),
        ("clauses hold non-strings",        _answer([1, None, {}])),
    ]:
        g2, c2 = normalize_goal(original, model)
        check(f"{label} → goal unchanged, clauses None", g2 == original and c2 is None)

    print("\na serialised LIST is not a clause — the example-echo failure")
    # Observed for real on rung 9: the model answered an unrelated goal by echoing a
    # worked example out of the tool description, rendered as one string containing the
    # whole list. It is not a restatement of anything, and planning against it would act
    # on names the operator never mentioned — so the translation is discarded entirely.
    for bad in ["['create 3 vms labelled alpha', 'make sure they all ping each other']",
                '["create 3 vms", "launch them"]']:
        gb, cb = normalize_goal("sort out the mesh between n1 and n2", _answer([bad]))
        check("a stringified list is rejected outright",
              gb == "sort out the mesh between n1 and n2" and cb is None)
    # …and one bad clause poisons the batch: a partially-echoed answer is not salvageable.
    g7, c7 = normalize_goal("do the thing",
                            _answer(["create a vm named alpha", "['a', 'b']"]))
    check("one serialised clause discards the whole translation",
          g7 == "do the thing" and c7 is None)
    check("the tool description no longer carries an echoable example",
          "alpha" not in RESTATE_TOOL["function"]["parameters"]["properties"]["clauses"]["description"])

    print("\nnon-goals and no-ops")
    g3, c3 = normalize_goal("", _answer(["anything"]))
    check("an empty goal is left alone (no model call needed)", g3 == "" and c3 is None)
    g4, c4 = normalize_goal("create a vm named alpha", _answer(["create a vm named alpha"]))
    check("an already-canonical goal reports no change", g4 == "create a vm named alpha" and c4 is None)
    g5, c5 = normalize_goal("Create A VM Named Alpha", _answer(["create a vm named alpha"]))
    check("a case-only difference counts as no change", c5 is None)
    g6, c6 = normalize_goal("make a box called beta", _answer(["  create a vm named beta  "]))
    check("whitespace is stripped from clauses", g6 == "create a vm named beta")

    print("\nthe vocabulary is DERIVED from the catalog, not written here")
    ex = canonical_examples()
    check("examples come back", len(ex) > 0)
    check("they are the catalog's own ai_example strings",
          any("create a Ubuntu VM called dev" in e for e in ex))
    prompt = _system_prompt()
    check("the prompt carries them", "create a Ubuntu VM called dev" in prompt)
    check("the prompt states the no-planning limit", "NOT planning" in prompt)
    check("the prompt forbids dropping", "Never drop" in prompt)
    check("the prompt forbids inventing", "Never invent" in prompt)
    check("examples are bounded (a weak model's context is finite)",
          len(canonical_examples(limit=3)) == 3)

    print("\nthe tool schema is constrained output, so there is nothing to parse")
    fn = RESTATE_TOOL["function"]
    check("named restate_goal", fn["name"] == "restate_goal")
    params = fn["parameters"]
    check("clauses is the one required field", params["required"] == ["clauses"])
    check("clauses is an array of strings",
          params["properties"]["clauses"]["type"] == "array"
          and params["properties"]["clauses"]["items"]["type"] == "string")
    check("the description tells the model not to plan",
          "Do NOT plan" in fn["description"])

    print("\nthe collective expander must not eat a preposition (found via this module)")
    # The phrase is replaced by a member name IN PLACE, so an arm that swallows the
    # following preposition turns "attach all TO a network" into "attach fleet1 a
    # network" — _ANON_NET_RE then cannot see the unnamed shared network, none is minted,
    # and every member attaches to nothing. Rung 4 built 5 VMs and 0 networks that way.
    # Not translator-specific: an operator typing this has always hit it.
    from orchestrator.ai.autonomous import make_collective_expander
    _vms = {f"fleet{i}": {"status": "stopped"} for i in range(1, 6)}
    _exp = make_collective_expander(lambda: _vms)
    _steps = _exp("attach all to a private network", []) or []
    check("the shared network is minted first",
          bool(_steps) and _steps[0] == "create a network called net1")
    check("the preposition survives into every member step",
          all(" to the network called net1" in s for s in _steps[1:]))
    check("one step per member", len(_steps) == 1 + len(_vms))
    # The forms that already worked must keep working — this arm is load-bearing for rungs 4-7.
    for phrase, expect_net in [("put them all in a network", True),
                               ("give them all the 'fleet' label", False),
                               ("stop each of them", False)]:
        out = _exp(phrase, []) or []
        minted = bool(out) and out[0].startswith("create a network")
        check(f"{phrase!r} unchanged", len(out) == len(_vms) + (1 if expect_net else 0)
              and minted == expect_net)

    print("\nwired into run_autonomous: the PLANNER sees the canonical goal")
    from orchestrator.ai.autonomous import run_autonomous

    seen = {"planner_goals": []}

    def model(messages, tools):
        names = {t["function"]["name"] for t in tools}
        if names == {"restate_goal"}:                       # the translation call
            return {"message": {"tool_calls": [{"function": {
                "name": "restate_goal",
                "arguments": {"clauses": ["create a vm named alpha"]}}}]}}
        g = next((m["content"][6:] for m in messages
                  if m["role"] == "user" and m["content"].startswith("Goal: ")), "")
        seen["planner_goals"].append(g)
        return {"message": {"tool_calls": [{"function": {
            "name": "create_vm", "arguments": {"name": "alpha"}}}]}}

    tools = [{"type": "function", "function": {"name": "create_vm", "parameters": {}}}]
    r = run_autonomous("spin up a machine and call it alpha", call_model=model,
                       execute=lambda t, a: {"success": True}, tools=tools,
                       max_retries=0, max_depth=1, translate=True)
    check("the planner was given the RESTATED goal",
          any("create a vm named alpha" in g for g in seen["planner_goals"]))
    check("the planner never saw the original wording",
          not any("spin up a machine" in g for g in seen["planner_goals"]))
    check("the result reports the ORIGINAL goal", r["goal"] == "spin up a machine and call it alpha")
    check("the result shows what it was translated to",
          r["goal_translated"]["planned"] == "create a vm named alpha")
    check("and the clauses it was built from",
          r["goal_translated"]["clauses"] == ["create a vm named alpha"])

    print("\ntranslate is OFF BY DEFAULT — measured as a wash, see the module docstring")
    seen["planner_goals"] = []
    # No `translate=` argument at all: the DEFAULT must leave the goal alone. This is the
  # assertion that would fail if someone flipped it back on without re-measuring.
    r2 = run_autonomous("spin up a machine and call it alpha", call_model=model,
                        execute=lambda t, a: {"success": True}, tools=tools,
                        max_retries=0, max_depth=1)
    check("by DEFAULT the planner gets the goal verbatim",
          any("spin up a machine" in g for g in seen["planner_goals"]))
    check("by default nothing is reported as translated", "goal_translated" not in r2)
    check("the original goal is still reported", r2["goal"] == "spin up a machine and call it alpha")

    print("\na dead translator leaves the run exactly as it was")
    seen["planner_goals"] = []

    def half_dead(messages, tools):
        names = {t["function"]["name"] for t in tools}
        if names == {"restate_goal"}:
            raise RuntimeError("ollama down")
        return model(messages, tools)

    r3 = run_autonomous("spin up a machine and call it alpha", call_model=half_dead,
                        execute=lambda t, a: {"success": True}, tools=tools,
                        max_retries=0, max_depth=1, translate=True)
    check("the run still happens on the original goal",
          any("spin up a machine" in g for g in seen["planner_goals"]))
    # Any normal close will do — the point is that a dead translator does not crash the
    # run or change its shape. (This stub closes `skipped/not_worth_it`: no reward is
    # passed, so the CE gate declines. That is the worth-it gate, nothing to do with
    # translation, and it is identical with translate=False.)
    check("and it still closes normally", isinstance(r3["root"].get("status"), str))
    check("a dead translator changes nothing about the outcome",
          r3["root"]["status"] == r2["root"]["status"])

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
