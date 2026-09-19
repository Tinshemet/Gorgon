"""conftest.py — keep the suite out of the operator's storage home.

THE OPERATOR'S LOG DIRECTORY IS THEIR GROUND TRUTH ABOUT WHAT THIS SYSTEM DID. Every
session close now writes a ledger there automatically, which is correct for a real run and
catastrophic for a test suite: the first full run after wiring it left **1,285 files** in
`~/.gorgon/logs`, every one of them a fixture with a name like `do-it` or `alpha-running`.
A grounding record you have to sift for the real entries is not a grounding record.

So the whole suite runs with `GORGON_HOME` pointed at a temporary directory. `EventLog.save`
already reads that variable — it was written to be redirectable — and this is the one place
that redirection has to happen, because a test that forgets is a test that pollutes silently.

⇒⇒ **IT DID NOT COVER THE PROCEDURE STORE, AND THIS FILE CLAIMED IT DID.** Until 2026-09-18
the sentence here read *"it covers the procedure store too, which resolves under the same
home"* — and it was false for two months. `planner/procedures.py` ends with
`LIBRARY = Store()` at MODULE SCOPE, and `_home()` reads `GORGON_HOME` **at import**. Test
modules are imported during COLLECTION, which happens BEFORE any session-scoped fixture
runs. So `LIBRARY` bound to `/home/tinshemet/.gorgon/procedures` — the operator's real
library — in every run this suite has ever made.

⇒ **IT COST 21 RED ITEMS THAT WERE NOT DEFECTS.** 8 failures and 13 errors across
  `test_ghost_writer` · `test_temp_lifecycle` · `test_engines` · `test_medusa_rungs` ·
  `test_intent_ladder` · `test_tree_sessions`, all caused by a procedure the operator saved
  on 2026-08-27 appearing in the planner's operation list:

      tests/test_temp_lifecycle.py:282: AssertionError: (['browser'], ['iwillhackyou', 'launch_vm'])

⇒⇒ **AND THE DIRECTION WE CANNOT SEE IS THE WORSE ONE.** We noticed because the leak made
  things RED. Nothing tells us what it made GREEN. Every pass in this suite was, until now, a
  sample of an undeclared variable — the same defect class as PYTHONHASHSEED, the empty
  marathon, and the builder divergence. That is four.

⇒ **SO THE BIND HAPPENS AT IMPORT, NOT IN A FIXTURE.** conftest is imported before collection,
  so setting the variable at module scope is early enough for a module-level singleton to see
  it. The session fixture below ADOPTS this same directory rather than making a second one —
  it exists now only to clean up and to restore whatever was set before.

⇒ FOUR SINGLETONS BIND THIS WAY, not one: `archive.ARCHIVE` · `verb_alias.ALIASES` ·
  `ledger.LEDGER` · `procedures.LIBRARY`. `test_harness_integrity` asserts all four land
  inside the sandbox, so the next one that does not turns the suite red instead of quietly
  changing what it measures. **A claim in a docstring is not a control; this one was wrong for
  two months because nothing executed it.**
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest


# ── THE BIND, AT IMPORT TIME ────────────────────────────────────────────────────────────────
# Module scope on purpose. A fixture — at ANY scope — runs after collection, and collection is
# when the singletons above read this variable. Do not move this into a fixture.
_PRIOR_GORGON_HOME = os.environ.get("GORGON_HOME")
SANDBOX_HOME = tempfile.mkdtemp(prefix="gorgon-tests-")
os.environ["GORGON_HOME"] = SANDBOX_HOME


# ── AND RECORD WHERE THE STORES ACTUALLY LANDED ─────────────────────────────────────────────
# ⇒⇒ **THE OBSERVATION HAS TO HAPPEN HERE, NOT IN A TEST.** Once the session fixture has run,
#   any module imported afterwards binds to the sandbox correctly — so a test that imports the
#   stores ITSELF can never see the bug, and will pass whether or not the bind above exists.
#   That exact mistake was made and caught by a control on 2026-09-18. `BOUND_AT_IMPORT` is the
#   only witness to collection-time state, and `test_harness_integrity` asserts against it.
#
#   REMOVING THE THREE LINES ABOVE WHILE KEEPING THIS BLOCK IS THE CONTROL: the stores then
#   bind to the operator's real home and the integrity check goes red, as it must.
BOUND_AT_IMPORT: "dict[str, str]" = {}

for _dotted, _attr in (
    ("orchestrator.languages.english.seam.archive", "ARCHIVE"),
    ("orchestrator.languages.english.seam.verb_alias", "ALIASES"),
    ("orchestrator.ai.books.ledger", "LEDGER"),
    ("planner.procedures", "LIBRARY"),
    ("orchestrator.auth.store", "OPERATORS_FILE"),
    ("orchestrator.auth.sessions", "SESSIONS_FILE"),
):
    try:
        _mod = __import__(_dotted, fromlist=[_attr])
        _obj = getattr(_mod, _attr)
        # a store exposes `.path`; a bare Path/str constant IS the path
        _p = _obj if isinstance(_obj, (str, os.PathLike)) else getattr(_obj, "path", None)
        if callable(_p) and not isinstance(_p, (str, os.PathLike)):
            _p = _p()
        if isinstance(_p, os.PathLike):
            _p = os.fspath(_p)
        if isinstance(_p, str) and _p:
            BOUND_AT_IMPORT[f"{_dotted}.{_attr}"] = _p
    except Exception:                     # a store that cannot import is not this file's problem
        pass


@pytest.fixture(autouse=True)
def _a_failed_check_fails_the_test(request):
    """A `check()` that prints FAIL must FAIL. Until 2026-08-11 it did not.

    ⇒⇒ **THE SUITE WAS NOT ASSERTING, AND THAT INVALIDATED EVERY CONTROL RUN.** 74 test modules
      keep a `_FAIL` counter that `check(label, cond)` increments and prints — and NOTHING ever
      read it. `tests/test_twopass_schema.py` was carrying **15 failing checks** while pytest
      reported *39 passed*, including behavioural ones:

          FAIL  a setter with its value omitted is caught
          FAIL  gate 3 is silent while the kinds are unsettled
          FAIL  it asks the operator to confirm
          FAIL  a worse retry is rejected and the first answer stands

    ⇒ **SO "674 PASSED" MEANT "NOTHING RAISED", NOT "NOTHING BROKE".** It was quoted as a
      regression control after every change made on 2026-08-11 and could not have caught one.
      A green suite that cannot go red is the most expensive kind of comfort.

    ⇒ **IT IS THE SESSION'S OWN DEFECT CLASS, IN THE TESTS THEMSELVES**: a check computed where
      nothing consumes it. Twelve instances were found in the product that day; this is the
      thirteenth, and it was in the instrument being used to find the other twelve.

    ⇒ THE FIXTURE IS AUTOUSE AND PER-TEST so no module opts in and none can quietly escape —
      the same reasoning the storage sandbox below is written with. It compares the module's
      counter across the test, so a module that fails on import is unaffected and a test that
      adds no failures stays green.
    """
    module = request.module
    before = getattr(module, "_FAIL", None)
    yield
    if before is None:
        return                      # this module does not use the check()/_FAIL idiom
    after = getattr(module, "_FAIL", 0)
    assert after == before, (
        f"{after - before} check(s) FAILED in {request.node.name} — see the FAIL lines in "
        f"the captured output (run with -s to read them)")


@pytest.fixture(scope="session", autouse=True)
def _sandbox_storage_home():
    """Adopt the import-time sandbox; clean it up; restore whatever was set before.

    ⇒ THIS FIXTURE NO LONGER CREATES THE SANDBOX — the module-level bind above does, because
      by the time any fixture runs the singletons have already read the variable. Keeping the
      fixture is still right: it owns teardown, and it re-asserts the variable in case a test
      changed it.
    """
    os.environ["GORGON_HOME"] = SANDBOX_HOME
    try:
        yield SANDBOX_HOME
    finally:
        if _PRIOR_GORGON_HOME is None:
            os.environ.pop("GORGON_HOME", None)
        else:
            os.environ["GORGON_HOME"] = _PRIOR_GORGON_HOME
        shutil.rmtree(SANDBOX_HOME, ignore_errors=True)
