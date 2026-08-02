#!/usr/bin/env python3
"""
test_layering.py — the dependency arrow points ONE WAY: orchestrator -> engines -> planner.

WHY THIS EXISTS. `planner/` is THE LANGUAGE (Medusa's IR, writer, validator, procedure
store) and `engines/` is its main consumer; `orchestrator/` sits above both. That order
was true by intention and enforced by nothing — one `from orchestrator.ai.agent.contract
import gate_action` at module level in `planner/score/_deps.py` pointed the arrow back up
and made the package unimportable on its own. A grep finds those on the day somebody
looks; this suite finds them on the day they land.

TWO PROPERTIES, AND THE SECOND IS THE SUBTLE ONE:

  1. LAYERING — importing the lower package does not import the higher one. Checked in a
     SUBPROCESS, because the property is about what an import PULLS IN and this process
     has already imported everything.
  2. THE DEGRADED PATH — `_deps` resolves its optional bundle lazily now, and a lazy
     wrapper is a FUNCTION, which is always truthy. `engine.gate or _gate_default()` is
     read for truthiness, so a wrapper where `None` belonged would silently turn "no
     gate" into "a gate that raises at call time" — in the legal filter and the consent
     gate, in the one path nobody exercises. So the sparse-checkout arm is asserted to
     yield None/empty, not merely to not crash.

Run:  PYTHONPATH=. python3 tests/test_layering.py
"""
import os
import subprocess
import sys
import textwrap

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

_PASS = 0
_FAIL = 0


def check(label, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  \033[32mok\033[0m   {label}")
    else:
        _FAIL += 1
        print(f"  \033[31mFAIL\033[0m {label}" + (f"\n       {detail}" if detail else ""))


def _run(source: str):
    """Run a snippet in a fresh interpreter rooted at the project. Returns (rc, out)."""
    env = dict(os.environ, PYTHONPATH=_ROOT)
    proc = subprocess.run([sys.executable, "-c", textwrap.dedent(source)],
                          cwd=_ROOT, env=env, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


# The layers, low to high. A module in an earlier group may not pull in a later one AT
# IMPORT TIME. Reaching up from inside a function body is allowed and deliberate — see
# `ir/execute.py:_books`, which documents why the creation ledger sits above the language.
_UPPER = [
    "orchestrator.ai.agent.contract",
    "orchestrator.ai.chat.context_assistant",
    "orchestrator.ai.autonomous",
    "orchestrator.ai.engines.medusa",
    "orchestrator.ai.engines.orchestrator",
]


def test_planner_does_not_import_upward():
    rc, out = _run(f"""
        import sys
        import orchestrator.ai.planner.score          # the engine core + its deps
        import orchestrator.ai.planner.procedures     # the store
        import orchestrator.ai.planner.ir             # the language itself
        leaked = [m for m in {_UPPER!r} if m in sys.modules]
        print("LEAKED:" + ",".join(leaked))
    """)
    check("planner imports cleanly on its own", rc == 0, out)
    if rc == 0:
        leaked = out.rsplit("LEAKED:", 1)[-1].strip()
        check("planner pulls in nothing from the layers above it",
              leaked == "", f"leaked: {leaked}")


def test_deps_degrades_to_none():
    """A checkout without `executor` / the agent contract: every optional dep degrades."""
    rc, out = _run("""
        import sys
        BLOCKED = ("executor.command_catalog",
                   "orchestrator.ai.chat.context_assistant",
                   "orchestrator.ai.agent.contract")

        class Blocker:
            def find_spec(self, name, path=None, target=None):
                if name in BLOCKED or any(name.startswith(b + ".") for b in BLOCKED):
                    raise ImportError("sparse checkout: " + name)
                return None

        sys.meta_path.insert(0, Blocker())

        from orchestrator.ai.planner.score import _deps
        bad = []
        # The three read for TRUTHINESS by `engine.<x> or <default>()`. These must be None.
        for name in ("_gate_default", "_criterion_default", "_legal_default"):
            if getattr(_deps, name)() is not None:
                bad.append(name + " is not None")
        if _deps._post_create_attach() != {}:
            bad.append("_post_create_attach")
        if _deps._narrow_core_tools() != frozenset():
            bad.append("_narrow_core_tools")
        # The wrappers stay callable and keep their no-op meaning.
        if _deps._consent_verb("create_vm") != "create_vm":
            bad.append("_consent_verb is not identity")
        if _deps._tool_risk("delete_vm") is not None:
            bad.append("_tool_risk is not None")
        if _deps._yield_fact("t", {}, {}) is not None:
            bad.append("_yield_fact")
        sentinel = object()
        if _deps._extract_value(sentinel, {}) is not sentinel:
            bad.append("_extract_value is not passthrough")
        if _deps._finding_probe_spec("t", {}, {}) is not None:
            bad.append("_finding_probe_spec")
        print("BAD:" + ",".join(bad))
    """)
    check("the engine still imports without executor / the contract", rc == 0, out)
    if rc == 0:
        bad = out.rsplit("BAD:", 1)[-1].strip()
        check("every optional dep degrades to its documented default",
              bad == "", f"wrong: {bad}")


def test_deps_wired_in_a_full_checkout():
    """The other arm: with everything present, the defaults ARE the contract's."""
    from orchestrator.ai.agent import contract
    from orchestrator.ai.planner.score import _deps

    check("_gate_default() is contract.gate_action",
          _deps._gate_default() is contract.gate_action)
    check("_criterion_default() is contract.success_criterion",
          _deps._criterion_default() is contract.success_criterion)
    check("_legal_default() is contract.is_forbidden",
          _deps._legal_default() is contract.is_forbidden)
    check("_consent_verb reaches the contract",
          _deps._consent_verb("delete_vm") == contract.consent_verb("delete_vm"))
    check("_tool_risk reaches the contract",
          _deps._tool_risk("delete_vm") == contract.tool_risk("delete_vm"))
    check("_post_create_attach() is the registry's, not empty",
          _deps._post_create_attach() != {})


def main():
    print("\n--- layering: planner does not import upward ---")
    test_planner_does_not_import_upward()
    print("\n--- _deps: the degraded (sparse checkout) arm ---")
    test_deps_degrades_to_none()
    print("\n--- _deps: the wired (full checkout) arm ---")
    test_deps_wired_in_a_full_checkout()

    total = _PASS + _FAIL
    print(f"\n{_PASS}/{total} passed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
