"""test_owns_and_callers.py — the two tests I5's ledger said would have caught 11 of 12.

    *"every name in a gate's OWNS is emitted somewhere, and every gate function has a
    caller. All three are tests or a refactor — no new logic."*  (the open list, I-family)

⇒ **BOTH ARE COVERAGE-OF-DECLARATIONS TESTS**: a verdict name declared in OWNS that no code
  ever emits is a rule that CANNOT FIRE — worse than a missing rule, because it reads as
  handled ([[gorgon-grammar-was-never-enforced]], one layer down). A gate function nobody
  calls is built-and-never-called wearing its own name.
⇒ FIRST RUN'S OWN FINDING: the caller test flagged `bounces` — and the follow-up showed
  `report()` builds its output THROUGH bounces(), i.e. the detector was wrong, not the
  code. The detector is line-based now, and a gate exercised ONLY by tests is reported as
  such rather than failed silently.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PASS = _FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


def _blob(bases):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    for base in bases:
        for dirpath, _dirs, files in os.walk(os.path.join(root, base)):
            if "__pycache__" in dirpath:
                continue
            for f in files:
                if f.endswith(".py"):
                    out.append(open(os.path.join(dirpath, f),
                                    encoding="utf-8", errors="replace").read())
    return "\n".join(out)


def test_every_owned_verdict_is_emitted_somewhere():
    """A name in OWNS with no emitter is a rule that cannot fire."""
    import importlib
    src = _blob(("orchestrator",))
    for module in ("linguistics", "gate3", "gate4", "repair"):
        try:
            m = importlib.import_module(f"orchestrator.languages.english.seam.{module}")
        except ImportError:
            continue
        owned = getattr(m, "OWNS", None)
        if not owned:
            continue
        for name in sorted(owned):
            occurrences = src.count(name)
            check(f"{module}.OWNS {name!r} is emitted (seen {occurrences}x)",
                  occurrences >= 2)


def test_every_gate_entry_point_has_a_caller():
    """A gate function nobody calls is built-and-never-called wearing its own name."""
    code = _blob(("orchestrator", "planner", "engines"))
    tests = _blob(("tests",))
    gates = {"gates12": ("report", "bounces"), "gate3": ("check", "refused"),
             "gate4": ("destructive_goals", "confirmations"),
             "linguistics": ("findings",)}
    for module, functions in gates.items():
        for fn in functions:
            def callers(blob):
                return len([l for l in blob.split("\n")
                            if (fn + "(") in l
                            and not l.strip().startswith("def " + fn)])
            in_code, in_tests = callers(code), callers(tests)
            check(f"{module}.{fn}: {in_code} production / {in_tests} test caller(s)",
                  in_code + in_tests >= 1)
            if in_code == 0 and in_tests > 0:
                print(f"       ⚠ {module}.{fn} is exercised ONLY by tests")


def main(argv=None) -> int:
    from tests import _suite
    return _suite.run(sys.modules[__name__], "owns_and_callers")


if __name__ == "__main__":
    raise SystemExit(main())
