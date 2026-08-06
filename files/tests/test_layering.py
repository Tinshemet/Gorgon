#!/usr/bin/env python3
"""
test_layering.py — the dependency arrow points ONE WAY: orchestrator -> engines -> planner.

WHY THIS EXISTS. `planner/` is THE LANGUAGE (Medusa's IR, writer, validator, procedure
store) and `engines/` is its main consumer; `orchestrator/` sits above both. That order
was true by intention and enforced by nothing — one `from orchestrator.ai.agent.contract
import gate_action` at module level in `planner/score/_deps.py` pointed the arrow back up
and made the package unimportable on its own. A grep finds those on the day somebody
looks; this suite finds them on the day they land.

THREE PROPERTIES, AND THE LAST TWO ARE THE SUBTLE ONES:

  1. NO IMPORT-TIME UPWARD EDGE, read off the AST of every module in the four packages.
     This is the whole rule, stated once and enforced. An import inside a FUNCTION BODY
     is allowed — it costs nothing at import time and the layering it breaks is a
     call-time one somebody chose — but the exact set of those is pinned below, so a new
     one is a DECISION somebody records rather than a drift nobody notices.
  2. LAYERING, OBSERVED — importing the lower package does not pull in the higher one.
     The AST check says what the source declares; this says what the interpreter does.
     Checked in a SUBPROCESS, because the property is about what an import PULLS IN and
     this process has already imported everything.
  3. THE DEGRADED PATH — `_deps` resolves its optional bundle lazily now, and a lazy
     wrapper is a FUNCTION, which is always truthy. `engine.gate or _gate_default()` is
     read for truthiness, so a wrapper where `None` belonged would silently turn "no
     gate" into "a gate that raises at call time" — in the legal filter and the consent
     gate, in the one path nobody exercises. So the sparse-checkout arm is asserted to
     yield None/empty, not merely to not crash.

WHAT THIS SUITE CANNOT SEE, and it cost a debugging round on the day of the move: a
dependency that is a FILESYSTEM PATH rather than an import. `clause_ledger._verbs()`
found the chat config by walking up from `__file__`, which stopped resolving when the
package changed depth, and a bare `except` turned the miss into an empty set. Nothing
here would have caught that. `test_clause_ledger` did.

Run:  PYTHONPATH=. python3 tests/test_layering.py
"""
import ast
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


# THE LAYERS, low number = lower layer. A package may import DOWN and SIDEWAYS freely;
# importing UP at module level is the thing this file forbids. `shared` and `executor`
# are placed low because they are what everything reads (a bundle format, a tool
# registry) and they import none of these back.
_LAYERS = {
    "shared":       0,
    "planner":      0,   # the language
    "executor":     1,   # the tool registry / the executor server
    "packages":     1,   # camoufox, webcrawl
    "engines":      2,   # medusa, executor+qemu adapters, the rig, the engine-of-engines
    "orchestrator": 3,   # the run loop, chat, the agent contract, the books
    "client":       4,
    "admin":        4,
    "tests":        9,
}

# THE UPWARD EDGES THAT EXIST, ALL LAZY, EACH ONE A DECISION. Pinned as (package, module,
# target) so adding one is an edit here — "declare, don't infer" applied to the dependency
# graph itself. Line numbers are deliberately NOT pinned; they move for reasons nobody
# should have to re-approve.
_ALLOWED_LAZY = {
    # The language reaching for the tool registry to check a tool exists / its fields.
    ("planner", "planner/ir/derive.py",      "executor.command_catalog"),
    ("planner", "planner/ir/validate.py",    "executor.command_catalog"),
    ("planner", "planner/translator.py",     "executor.command_catalog"),
    ("planner", "planner/score/_deps.py",    "executor.command_catalog"),
    # The creation ledger sits ABOVE the language — see `ir/execute.py:_books`.
    ("planner", "planner/ir/execute.py",     "orchestrator.ai.books"),
    # The contract / consent gate defaults, resolved on first call — see `score/_deps.py`.
    ("planner", "planner/score/_deps.py",    "orchestrator.ai.chat.context_assistant"),
    ("planner", "planner/score/_deps.py",    "orchestrator.ai.agent.contract"),
    # The engines ask the chat layer where the model lives, and the orchestrator's library.
    ("engines",  "engines/channel.py",       "orchestrator.ai.chat.ollama_client"),
    ("engines",  "engines/rig.py",           "orchestrator.ai.active_library"),
    # The reading gate asks the CONTEXT ASSISTANT about a whole program — the deterministic
    # check the chat path has run for a long time and this one never called. It sits in
    # `engines` and not in `planner` on purpose: the assistant is chat-layer domain knowledge
    # (trigger words, high-stakes fields, a tool catalogue), and the LANGUAGE must not reach
    # up for that.
    ("engines",  "engines/medusa/_run.py",   "orchestrator.ai.chat.context_assistant"),
    # PRODUCTION REACHING INTO THE BENCH, deliberately — `staged_seams` says why: the
    # model-driven tree scores 4/13 against the writer's 13/13, so moving those builders
    # into production would claim they had arrived. Noted here because it is the kind of
    # edge that should stay uncomfortable to look at.
    ("engines",  "engines/rig.py",           "tests.bench.sim_world"),
    ("engines",  "engines/rig.py",           "tests.bench.tree_probe"),
}

_PACKAGES = ("planner", "packages", "engines", "orchestrator")


def _edges():
    """Every cross-package import in the four packages -> (pkg, relpath, target, lazy)."""
    found = []
    for pkg in _PACKAGES:
        for dirpath, dirs, names in os.walk(os.path.join(_ROOT, pkg)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in names:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, _ROOT)
                tree = ast.parse(open(path).read(), filename=rel)
                top_level = set(map(id, tree.body))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.level:            # relative — stays inside the package
                            continue
                        targets = [node.module or ""]
                    elif isinstance(node, ast.Import):
                        targets = [a.name for a in node.names]
                    else:
                        continue
                    for target in targets:
                        head = target.split(".")[0]
                        if head == pkg or head not in _LAYERS:
                            continue
                        if _LAYERS[head] > _LAYERS[pkg]:
                            found.append((pkg, rel, target, id(node) not in top_level,
                                          node.lineno))
    return found


def test_no_import_time_upward_edge():
    up = _edges()
    eager = [e for e in up if not e[3]]
    check("no package imports a higher layer at module level",
          not eager,
          "; ".join(f"{e[1]}:{e[4]} -> {e[2]}" for e in eager))

    seen = {(e[0], e[1], e[2]) for e in up if e[3]}
    surprise = sorted(seen - _ALLOWED_LAZY)
    check("every lazy upward edge is one that was written down",
          not surprise,
          "undeclared: " + "; ".join(f"{s[1]} -> {s[2]}" for s in surprise))
    gone = sorted(_ALLOWED_LAZY - seen)
    check("no declared upward edge has silently disappeared",
          not gone,
          "stale entries: " + "; ".join(f"{s[1]} -> {s[2]}" for s in gone))


# The higher layers, named as module paths for the observed-import check below.
_UPPER = [
    "orchestrator.ai.agent.contract",
    "orchestrator.ai.chat.context_assistant",
    "orchestrator.ai.autonomous",
    "engines.medusa",
    "engines.orchestrator",
]


def test_planner_does_not_import_upward():
    rc, out = _run(f"""
        import sys
        import planner.score          # the engine core + its deps
        import planner.procedures     # the store
        import planner.ir             # the language itself
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

        from planner.score import _deps
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
    from planner.score import _deps

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
    print("\n--- layering: no import-time upward edge, anywhere ---")
    test_no_import_time_upward_edge()
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
