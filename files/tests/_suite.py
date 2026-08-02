"""_suite.py — run every `test_*` in a module, in definition order. DISCOVERED, not listed.

THE LIST WAS THE BUG, THREE TIMES, AND THE FIX WAS THE BUG TWICE. A hand-maintained tuple
of test functions costs nothing to write and silently drops whatever nobody remembered to
add:

  2026-07-29  `test_medusa_invariants` — two invariants added, neither ran. Under pytest
              `check()` only PRINTS, so they could not fail there either.
  2026-07-30  `test_ladder_gate` — three checks added for the goal comparison, none ran.
              The file reported 55/55 and looked green.
  2026-07-30  `test_medusa` — a test added for the intent promotion did not run, and the
              suite reported the SAME 415/415 it had before the test existed. Caught only
              because the total was expected to move and did not.

The first two were each fixed by pasting a discovery loop into that one file, which is why
there was a third. An identical count before and after adding a test is the only symptom,
and nothing was watching for it — so the mechanism, not the file, is what had to change.

*A suite that stopped being mentioned stopped being run* is this codebase's oldest failure
mode; `run_all.py` exists for it at the file level, and this exists for it at the function
level. Both remove a step a human has to remember rather than asking them to remember it.

Every suite keeps its own `check()` and its own `_PASS`/`_FAIL`, because the counters are
what `check()` closes over. This only finds the functions and reports the total.
"""
import os
import shutil
import tempfile
from typing import Optional


def run(module, unit: str = "tests", extra: Optional[str] = None) -> int:
    """Call every `test_*` in `module` in definition order; return an exit code.

    `module` is the suite itself — `sys.modules[__name__]` from inside it. Definition order
    matters: these suites are written to be read top to bottom, and a failure is easier to
    place when the output follows the file.

    AND IT SANDBOXES `GORGON_HOME`, WHICH IS THE LAST DOOR THAT WAS OPEN. `run_all.py`
    points every suite it spawns at a disposable home, and `conftest.py` does the same for
    the pytest bucket — so both of the ways the suite is run IN BULK were covered, and
    `python3 -m tests.test_whatever` was not. That is the way a person runs a suite while
    DEBUGGING one, which is to say: often, and while paying attention to something else.

    MEASURED 2026-08-02: a few direct runs put **164 files** of fixture named
    `a-risotto`, `nightly-box`, `make-a-dish-somehow` into the operator's real
    `~/.gorgon/logs` — the directory whose whole purpose is to be the grounding record of
    what this system actually did. The same escape at a larger scale is what put 329,111
    files there on 2026-07-30. `eventlog` reads the variable at WRITE time, so setting it
    here covers everything the tests go on to import.

    THE SANDBOX IS KEPT ON FAILURE and named, because the artifacts a failing suite wrote
    are usually the evidence.
    """
    found = [v for k, v in vars(module).items()
             if k.startswith("test_") and callable(v)]
    found.sort(key=lambda f: f.__code__.co_firstlineno)

    home = tempfile.mkdtemp(prefix="gorgon-suite-")
    prior = os.environ.get("GORGON_HOME")
    os.environ["GORGON_HOME"] = home
    try:
        for fn in found:
            print(f"\n── {fn.__name__}")
            fn()
    finally:
        if prior is None:
            os.environ.pop("GORGON_HOME", None)
        else:
            os.environ["GORGON_HOME"] = prior

    passed = getattr(module, "_PASS", 0)
    failed = getattr(module, "_FAIL", 0)
    print(f"\n{passed}/{passed + failed} passed  ({len(found)} {unit})"
          + (f"  {extra}" if extra else ""))
    if failed:
        print(f"   what it wrote: {home}")
    else:
        shutil.rmtree(home, ignore_errors=True)
    return 1 if failed else 0
