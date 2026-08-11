"""conftest.py — keep the suite out of the operator's storage home.

THE OPERATOR'S LOG DIRECTORY IS THEIR GROUND TRUTH ABOUT WHAT THIS SYSTEM DID. Every
session close now writes a ledger there automatically, which is correct for a real run and
catastrophic for a test suite: the first full run after wiring it left **1,285 files** in
`~/.gorgon/logs`, every one of them a fixture with a name like `do-it` or `alpha-running`.
A grounding record you have to sift for the real entries is not a grounding record.

So the whole suite runs with `GORGON_HOME` pointed at a temporary directory. `EventLog.save`
already reads that variable — it was written to be redirectable — and this is the one place
that redirection has to happen, because a test that forgets is a test that pollutes silently.

IT COVERS THE PROCEDURE STORE TOO, which resolves under the same home. A suite that wrote
procedures into the operator's library would make the writer reach for fixtures.

SESSION-SCOPED AND AUTOUSE, deliberately: no test opts in, and there is no way to write a
new test that quietly escapes it.
"""
from __future__ import annotations

import os
import tempfile

import pytest


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
    with tempfile.TemporaryDirectory(prefix="gorgon-tests-") as tmp:
        was = os.environ.get("GORGON_HOME")
        os.environ["GORGON_HOME"] = tmp
        try:
            yield tmp
        finally:
            if was is None:
                os.environ.pop("GORGON_HOME", None)
            else:
                os.environ["GORGON_HOME"] = was
