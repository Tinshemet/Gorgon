#!/usr/bin/env python3
"""
test_scope.py — is a CALL inside the context a scope permits? (K5, the matching half)

Proves the three things a scope has to get right to be a scope rather than a ban wearing a
new name: an in-scope call RUNS, an out-of-scope call is REFUSED, and an UNBOUND target is
refused because nothing proved it inside — which is rung 14, the call that passed every
check this system had (`delete_vm` over the unfiltered set of every machine).

And the deferral rule: a caller never refuses on a binding it cannot read, because under
the union ruling another scope it cannot see might be the one that admits.

Run:  PYTHONPATH=files python3 files/tests/test_scope.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.agent.contract import scope as S
from orchestrator.ai.agent.contract.rules import RuleSet

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


# The law under test, written the way an operator would write it.
LAW = [
    {"w": 1, "kind": "access", "text": "recon is confined to the lab network",
     "effect": {"scope": {"tools": ["scan_network"], "args": {"net_name": "lab"}}}},
    {"w": 1, "kind": "access", "text": "and to the dmz",
     "effect": {"scope": {"tools": ["scan_network"], "args": {"net_name": "dmz"}}}},
    {"w": 0, "kind": "access", "text": "deletes only ever touch scratch machines",
     "effect": {"scope": {"tools": ["delete_vm"], "object": {"kind": "vm", "label": "scratch"}}}},
]
RS = RuleSet(LAW)
RECON = RS.scopes("scan_network")
DELETE = RS.scopes("delete_vm")


def main():
    print("THE CONTROL — the same law must say YES to one call and NO to another")
    inside = S.outside("scan_network", RECON, args={"net_name": "lab"})
    out = S.outside("scan_network", RECON, args={"net_name": "prod"})
    check("an IN-SCOPE call is admitted", inside is None)
    check("an OUT-OF-SCOPE call is refused", isinstance(out, str) and out)
    check("...and the refusal names the rule that refused it, not just 'forbidden'",
          "recon is confined to the lab network" in (out or ""))
    check("A MATCHER THAT REFUSED BOTH WOULD BE A TOOL BAN IN NEW CLOTHES — it does not",
          inside is None and out is not None)

    print("\nARGS binding — a literal, which is what the tree and the executors hold")
    check("present and equal → inside", S.outside("scan_network", RECON, args={"net_name": "lab"}) is None)
    check("a different value → outside", S.outside("scan_network", RECON, args={"net_name": "prod"}) is not None)
    check("ABSENT IS OUTSIDE, NOT INSIDE — a missing argument proves nothing",
          S.outside("scan_network", RECON, args={"deep": True}) is not None)
    check("arguments the scope does not name are unconstrained",
          S.outside("scan_network", RECON, args={"net_name": "lab", "deep": True, "ports": "all"}) is None)
    check("UNION (ruling c) — the second scope admits what the first refuses",
          S.outside("scan_network", RECON, args={"net_name": "dmz"}) is None)

    print("\nOBJECT binding — a selector, which is all the front seam ever holds")
    check("an exactly-matching selector is inside",
          S.outside("delete_vm", DELETE, selector={"kind": "vm", "label": "scratch"}) is None)
    check("a NARROWER selector is inside (it asserts everything the scope requires)",
          S.outside("delete_vm", DELETE,
                    selector={"kind": "vm", "label": "scratch", "os_type": "linux"}) is None)
    check("a different value is outside",
          S.outside("delete_vm", DELETE, selector={"kind": "vm", "label": "prod"}) is not None)
    check("another kind is outside",
          S.outside("delete_vm", DELETE, selector={"kind": "network", "label": "scratch"}) is not None)

    print("\n  ⇒ RUNG 14 — the call that passed every check this system had")
    check("AN UNBOUND SET IS REFUSED — nothing narrows it, so nothing proved it inside",
          S.outside("delete_vm", DELETE, selector={"kind": "vm"}) is not None)
    # AN EMPTY DICT IS "I HAVE NO SELECTOR", NOT "I SELECT EVERYTHING" — and it cannot come
    # from a real one: `schema.select_of` always emits at least `{"kind": …}`. So it defers
    # rather than refusing, and the unbound case that DOES arise is the one above.
    check("an empty selector is NO selector, so it defers rather than refusing",
          S.outside("delete_vm", DELETE, selector={}) is None)
    check("and the refusal is about INCLUSION, not about catching a bad target",
          "nothing shows this call is inside one"
          in (S.outside("delete_vm", DELETE, selector={"kind": "vm"}) or ""))

    print("\n  ⇒ a carve-out only NARROWS, so it cannot take a call out of scope")
    check("a nested `not` on top of an in-scope base stays inside",
          S.outside("delete_vm", DELETE,
                    selector={"kind": "vm", "label": "scratch", "not": {"name": "db"}}) is None)
    check("`all` of `not`s (what select_of emits for several carve-outs) stays inside",
          S.outside("delete_vm", DELETE,
                    selector={"kind": "vm", "label": "scratch",
                              "all": [{"not": {"name": "db"}}, {"not": {"name": "log"}}]}) is None)
    check("a group can never rescue an out-of-scope base",
          S.outside("delete_vm", DELETE,
                    selector={"kind": "vm", "label": "prod", "not": {"name": "db"}}) is not None)
    check("a MEMBERSHIP value is refused — conservative, and two scopes union to express it",
          S.outside("delete_vm", DELETE,
                    selector={"kind": "vm", "label": {"in": ["scratch"]}}) is not None)

    print("\nTHE CONTAINMENT RULE — one authored scope must not ban the world")
    check("a tool NO scope names is ungoverned, not refused",
          S.outside("launch_vm", RS.scopes("launch_vm"), args={"name": "anything"}) is None)
    check("...and that holds with no args and no selector either",
          S.outside("launch_vm", RS.scopes("launch_vm")) is None)

    print("\nTHE DEFERRAL RULE — never refuse on information this caller does not have")
    check("a caller holding only ARGS defers on an object-bound scope",
          S.outside("delete_vm", DELETE, args={"name": "web1"}) is None)
    check("a caller holding only a SELECTOR defers on an args-bound scope",
          S.outside("scan_network", RECON, selector={"kind": "network", "name": "prod"}) is None)
    check("a caller holding NEITHER defers (chat's toolkit filter has only a name)",
          S.outside("scan_network", RECON) is None and S.outside("delete_vm", DELETE) is None)
    mixed = RS.scopes("scan_network") + RS.scopes("delete_vm")
    check("MIXED bindings defer as a whole — an unreadable scope may be the one that admits",
          S.outside("x", mixed, args={"net_name": "prod"}) is None)

    print("\nadmits() — the single-scope predicate the callers compose")
    check("an args scope admits its own context",
          S.admits(RECON[0], args={"net_name": "lab"}) is True)
    check("an object scope admits a narrower selector",
          S.admits(DELETE[0], selector={"kind": "vm", "label": "scratch", "x": 1}) is True)
    check("a scope with an unknown binding admits nothing",
          S.admits({"bind": "wat", "context": {"a": 1}}, args={"a": 1}) is False)

    print("\nCALLER 1 — the CONTRACT: `is_forbidden` stops discarding the args it accepts")
    import json
    from orchestrator.ai.agent.contract.core import Contract
    _files = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    g = json.load(open(os.path.join(_files, "orchestrator/ai/agent/doorman.grgn")))
    g["contract"]["rules"] = LAW
    g["contract"]["forbidden"] = []
    c = Contract(g, "doorman", "signed")
    check("an IN-SCOPE call is permitted", c.is_forbidden("scan_network", {"net_name": "lab"}) is False)
    check("an OUT-OF-SCOPE call is FORBIDDEN — the law can now ban a TARGET",
          c.is_forbidden("scan_network", {"net_name": "prod"}) is True)
    check("the refusal names the rule, not just 'forbidden'",
          "recon is confined to the lab network" in (c.refusal("scan_network", {"net_name": "prod"}) or ""))
    check("NAME-ONLY still answers (chat's toolkit filter) and defers the scope",
          c.is_forbidden("scan_network") is False)
    check("an unscoped tool is untouched", c.is_forbidden("launch_vm", {"name": "x"}) is False)
    g["contract"]["forbidden"] = ["scan_network"]
    check("ruling (b) in the live contract: a ban beats the scope that grants a context",
          Contract(g, "doorman", "signed").is_forbidden("scan_network", {"net_name": "lab"}) is True)

    print("\nCALLER 2 — the PROGRAM REGIME: each call judged with its own target")
    from planner.ir import consent as C
    ok_prog = {"body": [{"op": "call", "tool": "scan_network", "args": {"net_name": "lab"}}]}
    bad_prog = {"body": [{"op": "call", "tool": "scan_network", "args": {"net_name": "prod"}}]}
    both = {"body": [{"op": "call", "tool": "scan_network", "args": {"net_name": "lab"}},
                     {"op": "call", "tool": "scan_network", "args": {"net_name": "prod"}}]}
    check("a program that stays in scope may run", C.forbidden(ok_prog, c.is_forbidden) == [])
    check("a program that leaves it is stopped", C.forbidden(bad_prog, c.is_forbidden) == ["scan_network"])
    check("ONE OUT-OF-SCOPE CALL AMONG GOOD ONES IS STILL CAUGHT — the reason calls_named "
          "does not de-duplicate", C.forbidden(both, c.is_forbidden) == ["scan_network"])
    ref_prog = {"body": [{"op": "call", "tool": "scan_network", "args": {"net_name": "$target"}}]}
    check("an unresolved $reference DEFERS — missing information is not evidence",
          C.forbidden(ref_prog, c.is_forbidden) == [])
    check("calls_named keeps every call, in order",
          [t for t, _ in C.calls_named(both)] == ["scan_network", "scan_network"]
          and [a["net_name"] for _, a in C.calls_named(both)] == ["lab", "prod"])
    check("tools_named still answers the MEMBERSHIP question with a set of one",
          C.tools_named(both) == ["scan_network"])

    print("\n  ⇒ arity: an injected filter written either way must still be asked")
    check("a 1-ARG filter is asked the 1-arg question (it cannot see a target)",
          C.ask(lambda tool: True, "scan_network", {"net_name": "lab"}) is True
          and C.forbidden(ok_prog, lambda tool: False) == []
          and C.forbidden(ok_prog, lambda tool: True) == ["scan_network"])
    check("a 2-ARG filter receives the target", C.ask(lambda t, a: a == {"net_name": "lab"},
                                                      "scan_network", {"net_name": "lab"}) is True)
    check("a *args filter works", C.ask(lambda *a: True, "x", {}) is True)
    check("a non-callable is not forbidden", C.ask(None, "x", {}) is False)
    check("empty args are NO args, so a 2-arg filter is handed None (defer)",
          C.ask(lambda t, a: a is None, "x", {}) is True)

    print("\n3b — A TARGET THAT IS ONLY KNOWN AT INVOCATION IS STILL KNOWN BEFORE THE FIRST CALL")
    from planner.ir import execute as X
    # A REAL REGISTERED TOOL, because `run` validates against the executor's registry before
    # any of this — a program the validator refuses would make every check below vacuous.
    g["contract"]["rules"] = [
        {"w": 1, "kind": "access", "text": "pings stay on the bench machine",
         "effect": {"scope": {"tools": ["guest_ping"], "args": {"name": "bench1"}}}}]
    pc = Contract(g, "doorman", "signed")
    par = {"params": {"target": "string"},
           "body": [{"op": "call", "tool": "guest_ping", "args": {"name": "$target"}}]}
    check("PRE-FLIGHT: bound at invocation, the reference resolves and an out-of-scope "
          "program is refused whole",
          C.forbidden(par, pc.is_forbidden, scope={"target": "prod1"}) == ["guest_ping"])
    check("...and the same program with an IN-SCOPE argument runs",
          C.forbidden(par, pc.is_forbidden, scope={"target": "bench1"}) == [])
    check("an UNBOUND reference still defers — resolve leaves the token alone",
          C.forbidden(par, pc.is_forbidden, scope={"unrelated": "prod1"}) == [])
    check("no scope at all behaves exactly as before (the caller that passes nothing)",
          C.forbidden(par, pc.is_forbidden) == [])

    print("  ⇒ and the whole program is refused BEFORE anything runs, not halfway")
    ran = []
    out = X.run(par, lambda t, a: ran.append((t, a)) or {"success": True},
                params={"target": "prod1"}, legal=pc.is_forbidden, consent=True)
    check("run() refuses the parameterised program", out["ok"] is False
          and out.get("failed") == "forbidden" and out.get("forbidden") == ["guest_ping"])
    check("NOTHING RAN — the lab is untouched, which is what a pre-flight is for", ran == [])
    ok_out = X.run(par, lambda t, a: ran.append((t, a)) or {"success": True},
                   params={"target": "bench1"}, legal=pc.is_forbidden, consent=True)
    check("CONTROL: the in-scope invocation of the SAME program is not refused",
          ok_out.get("failed") != "forbidden" and ran == [("guest_ping", {"name": "bench1"})])

    print("  ⇒ AND WHAT A PERSON LIFTS STAYS LIFTED — the backstop must not overturn it")
    ran = []
    lift = X.run(par, lambda t, a: ran.append((t, a)) or {"success": True},
                 params={"target": "prod1"}, legal=pc.is_forbidden, consent=True,
                 permit=lambda banned: True)
    check("re-authentication lifts a scope refusal at the pre-flight",
          lift.get("failed") != "forbidden")
    check("...and the RUNTIME check does not then refuse the same call one line later — "
          "the password would have bought nothing",
          ran == [("guest_ping", {"name": "prod1"})])

    print("  ⇒ THE BACKSTOP — a target no pre-flight could have known (a loop variable)")
    from planner.ir import config as _c
    loop = {"body": [
        {"op": "foreach", "in": ["bench1", "prod1"],
         "call": {"tool": "guest_ping", "args": {"name": f"${_c.LOOP_VAR}"}}}]}
    ran = []
    check("the pre-flight cannot see a loop variable, so it permits the program",
          C.forbidden(loop, pc.is_forbidden) == [])
    out = X.run(loop, lambda t, a: ran.append((t, a)) or {"success": True},
                legal=pc.is_forbidden, consent=True)
    check("the RUN stops at the out-of-scope iteration", out.get("failed") == "forbidden"
          and out.get("forbidden") == ["guest_ping"])
    check("the in-scope iteration had already run, and the refusal REPORTS it rather than "
          "hiding it", [a["name"] for _t, a in ran] == ["bench1"]
          and len(out.get("calls") or []) == 1)

    print("\nCALLER 3 — the EXECUTOR ENGINE: the args were in tile[1] and it read past them")
    from engines import ExecutorEngine
    from planner.ir import config as _cfg
    eng = ExecutorEngine(None, None)
    kinds = _cfg.KINDS or {}
    doomed = {"shape": "count", "select": {"kind": "vm", "name": "doomed"}, "eq": 0}
    spared = {"shape": "count", "select": {"kind": "vm", "name": "scratch1"}, "eq": 0}
    # THE GOAL ITSELF DOES NOT HOLD (so it needs its call); everything else does — the
    # machine exists and is stopped. Answering False to the PRECONDITION too makes
    # `_one_call` return None, which would make every check below pass on an empty sweep.
    never = lambda goal, _s: (goal not in (doomed, spared), None)
    # The tile for these goals is delete_vm(name=…) — the engine's own inversion, not a stub.
    tiles = [eng._one_call(g, kinds, never) for g in (doomed, spared)]
    check("the engine really does invert both goals to a delete with a target",
          all(t and t[0] == "delete_vm" and t[1].get("name") for t in tiles))
    eng.legal_filter = staticmethod(lambda tool, args=None: bool(args) and args.get("name") == "doomed")
    check("a goal whose TARGET is red-lined is refused before anything runs",
          eng._red_line([doomed], kinds, never) == "delete_vm")
    check("the SAME TOOL on a permitted target is not refused — the target is what decides",
          eng._red_line([spared], kinds, never) is None)
    eng.legal_filter = staticmethod(lambda tool: False)
    check("a 1-arg filter on the engine still answers (test_engines.py has one)",
          eng._red_line([doomed], kinds, never) is None)

    print("\nCALLER 4 — THE FRONT SEAM: rung 14 finally has something to fail")
    from orchestrator.seam import gate4, schema as SC
    from orchestrator.seam.effects import Operation
    from planner.formula.legal import Board

    g["contract"]["rules"] = [
        {"w": 1, "kind": "access", "text": "deletes only ever touch scratch machines",
         "effect": {"scope": {"tools": ["delete_vm"], "object": {"kind": "vm", "label": "scratch"}}}}]
    sc = Contract(g, "doorman", "signed")
    board = Board()

    class _Sym:                       # the shape gate4 reads: .handle and .row
        def __init__(self, handle, row):
            self.handle, self.row = handle, row

    def _row(**where):
        # THE SET FORM — `vm_set` is "all the vms", which is rung 14's shape. A bare `vm`
        # would be one named machine and would not be the case that has never been caught.
        return SC.declare_from("them", "vm" + SC.SET_SUFFIX, where, SC.EXISTING)

    unbound = [_Sym("them", _row())]                       # "delete all the vms" — rung 14
    scoped = [_Sym("them", _row(label="scratch"))]
    ops = [Operation("delete_vm", "them", None)]

    check("the seam really does build a selector from the row, and it IS a set",
          SC.select_of(_row(label="scratch"), board) == {"kind": "vm", "label": "scratch"}
          and _row().is_set and SC.select_of(_row(), board) == {"kind": "vm"})
    check("AN UNFILTERED DELETE IS REFUSED AT THE SEAM — nothing narrows it, so nothing "
          "proved it inside",
          gate4.forbidden_tools(ops, sc.is_forbidden, unbound, board) == ["delete_vm"])
    check("THE CONTROL: the same operation over a scoped set is permitted",
          gate4.forbidden_tools(ops, sc.is_forbidden, scoped, board) == [])
    check("without a table the seam asks the BAN alone and defers the scope",
          gate4.forbidden_tools(ops, sc.is_forbidden) == [])
    check("a tool no scope governs is untouched at the seam",
          gate4.forbidden_tools([Operation("launch_vm", "them", None)],
                                sc.is_forbidden, unbound, board) == [])
    g["contract"]["forbidden"] = ["delete_vm"]
    check("and a BAN still refuses it whatever the target is (ruling b, at the seam)",
          gate4.forbidden_tools(ops, Contract(g, "doorman", "signed").is_forbidden,
                                scoped, board) == ["delete_vm"])

    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
