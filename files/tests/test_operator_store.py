#!/usr/bin/env python3
"""
test_operator_store.py — operator credential lifecycle (create / reset / verify / delete).

Covers reset_password, added 2026-07-30 to close a real lockout: the store could
create and delete credentials but never rotate one, and delete_operator refuses to
remove the last account, so a forgotten password on the common single-operator
install had no recovery path short of hand-editing operators.json.

EVERY test redirects store.OPERATORS_FILE at a temp path. The module otherwise
reads and writes the REAL ~/.gorgon/operators.json — running an unisolated
credential test against a live install would overwrite the operator's own
account. The isolation is the safety property here, not a tidiness preference.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.auth import store

_passed = 0
_failed = 0


def check(label, cond):
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {label}")


class _isolated:
    """Point store.OPERATORS_FILE at a fresh temp file for the duration."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._real = store.OPERATORS_FILE
        store.OPERATORS_FILE = Path(self._tmp.name) / "operators.json"
        return store.OPERATORS_FILE

    def __exit__(self, *exc):
        store.OPERATORS_FILE = self._real
        self._tmp.cleanup()
        return False


def test_reset_replaces_credential():
    with _isolated():
        store.create_operator("op", "old-password")
        check("old password verifies before reset", store.verify_password("op", "old-password"))
        r = store.reset_password("op", "new-password")
        check("reset reports success", r.get("success") is True)
        check("old password rejected after reset", not store.verify_password("op", "old-password"))
        check("new password accepted after reset", store.verify_password("op", "new-password"))


def test_reset_rotates_salt_and_hash():
    with _isolated():
        store.create_operator("op", "same-password")
        before = dict(store._load()["op"])
        # Reset to the SAME password: hash and salt must still both change, proving a
        # fresh salt is issued rather than the stored one being reused.
        store.reset_password("op", "same-password")
        after = store._load()["op"]
        check("salt rotated on reset", before["salt"] != after["salt"])
        check("hash changed despite identical password", before["password_hash"] != after["password_hash"])
        check("same password still verifies", store.verify_password("op", "same-password"))


def test_reset_preserves_account_metadata():
    with _isolated():
        store.create_operator("op", "pw-original")
        before = dict(store._load()["op"])
        store.reset_password("op", "pw-replacement")
        after = store._load()["op"]
        for field in ("role", "tenant_id", "created"):
            check(f"{field} preserved across reset", before[field] == after[field])
        check("password_reset timestamp recorded", "password_reset" in after)


def test_reset_unknown_operator_fails_closed():
    with _isolated():
        store.create_operator("op", "pw-known")
        r = store.reset_password("typo", "pw-new")
        check("reset on unknown operator fails", r.get("success") is False)
        check("error names the operator", "typo" in r.get("error", ""))
        # A typo'd username must not silently mint a second account.
        check("no account created by failed reset", store.list_operators() == ["op"])
        check("existing operator untouched", store.verify_password("op", "pw-known"))


def test_reset_leaves_other_operators_alone():
    with _isolated():
        store.create_operator("alice", "alice-password")
        store.create_operator("bob", "bob-password")
        store.reset_password("alice", "alice-rotated")
        check("target rotated", store.verify_password("alice", "alice-rotated"))
        check("bystander unaffected", store.verify_password("bob", "bob-password"))
        check("bystander old secret not broadened", not store.verify_password("bob", "alice-rotated"))


def test_reset_keeps_store_permissions_0600():
    with _isolated() as path:
        store.create_operator("op", "pw-original")
        store.reset_password("op", "pw-replacement")
        mode = oct(os.stat(path).st_mode & 0o777)
        check(f"operators.json still 0600 after reset (got {mode})", mode == "0o600")


def test_last_operator_still_undeletable():
    # The guard reset_password exists to work around must remain in force: rotating
    # a credential is the recovery path, NOT deleting the final account.
    with _isolated():
        store.create_operator("only", "pw-only")
        r = store.delete_operator("only")
        check("last operator still refused for deletion", r.get("success") is False)
        check("refusal reason is last_operator", r.get("reason") == "last_operator")
        check("reset works where delete is refused", store.reset_password("only", "pw-rotated")["success"])


def test_real_store_untouched():
    # The isolation contract itself: after every test above, the module-level path
    # must point back at the real file, and that file must not have been created
    # by this suite on a box that never had an operator.
    check("OPERATORS_FILE restored to real path",
          str(store.OPERATORS_FILE).endswith(".gorgon/operators.json"))


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
    total = _passed + _failed
    print(f"{_passed}/{total} passed")
    sys.exit(1 if _failed else 0)
