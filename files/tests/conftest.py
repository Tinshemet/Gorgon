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
