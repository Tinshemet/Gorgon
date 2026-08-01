#!/usr/bin/env python3
"""
test_books.py — the record precedes the object, and the keeper never touches the territory.

Today "it exists" is a CLAIM IN A RETURN VALUE. This makes it a FACT IN THE REGISTRY, and
that is the failure class this project has fought harder than any other: `create_vm` returns
`success: True` and the harness believes it; `guest_ping` returned `success: True` for dead
machines and three consumers believed it.

THE TWO PROPERTIES WORTH TESTING ARE BOTH ABOUT ORDER AND ABOUT RESTRAINT:

    the slot is taken BEFORE the creator runs — otherwise the window where work is in
    flight and unaccounted for is exactly as wide as it was, and a sweep still has nothing
    to sweep because there is nothing there to find

    the keeper corrects the RECORD and never the WORLD — a keeper that fixed things would
    be a background process quietly doing high-impact work with nobody asking

Run:  PYTHONPATH=. python3 -m tests.test_books
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.books import keeper as _keeper
from orchestrator.ai.books import ledger as _ledger
from orchestrator.ai.books.ledger import (CLAIMED, DELETED, EXIST, FAILED, MISSING,
                                          PENDING, SEEN, Ledger, index)
from orchestrator.ai.planner.ir import run as ir_run
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class _Books:
    """A ledger in a temp directory, installed as THE ledger for the duration.

    THE MODULE SINGLETON IS SWAPPED, for the reason `test_procedures` gives: the executor
    reserves against `LEDGER` and a test that built its own would prove a Ledger works while
    leaving the seam production actually uses untested.
    """

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="gorgon-books-")
        self.prior = _ledger.LEDGER
        _ledger.LEDGER = Ledger(self.dir)
        return _ledger.LEDGER

    def __exit__(self, *exc):
        _ledger.LEDGER = self.prior
        shutil.rmtree(self.dir, ignore_errors=True)


def test_identity_and_index_are_two_fields():
    """THE ONE PLACE A DERIVED VALUE WOULD QUIETLY HAVE BECOME AN IDENTITY. `where` is the
    CURRENT location and it moves, so recomputing your way back to an object fails precisely
    when the object is most broken."""
    print("[books] the uid is who it is; the hash is where to look")
    with _Books() as lib:
        uid = lib.reserve("web", "vm", at=100.0, where="lab")
        row = lib.get(uid)
        check("the hash is recomputable by anyone, without a lookup",
              row["hash"] == index("web", "vm", "lab"))
        check("and moving it would change the hash",
              index("web", "vm", "lab") != index("web", "vm", "dmz"))
        check("while the identity is not derived from anything",
              len(uid) == 32 and uid != row["hash"])
        check("two reservations of the same thing are two slots",
              lib.reserve("web", "vm", at=101.0, where="lab") != uid)


def test_a_slot_is_born_pending_and_settles_once():
    print("[books] PENDING is a real state because the record came first")
    with _Books() as lib:
        uid = lib.reserve("web", "vm", at=100.0)
        check("it starts PENDING", lib.get(uid)["status"] == PENDING)
        lib.settle(uid, EXIST, at=101.0)
        check("and settles", lib.get(uid)["status"] == EXIST)
        check("the fold keeps the reservation's facts",
              lib.get(uid)["name"] == "web" and lib.get(uid)["kind"] == "vm")
        try:
            lib.settle(uid, "SORT-OF", at=102.0)
            check("a state nobody declared is refused", False)
        except ValueError:
            check("a state nobody declared is refused", True)


def test_the_log_survives_a_line_written_by_a_process_that_died():
    """An append-only log written by something that can die mid-write will eventually have a
    torn line, and refusing to read the ledger because of its last byte would lose the very
    history it exists to keep."""
    print("[books] a torn line costs one row, not the book")
    with _Books() as lib:
        good = lib.reserve("web", "vm", at=100.0)
        with open(os.path.join(lib.path, "creations.jsonl"), "a") as fh:
            fh.write('{"uid": "half-writ')
        later = lib.reserve("db", "vm", at=101.0)
        names = {r["name"] for r in lib.rows()}
        check("both real rows survive", names == {"web", "db"})
        check("and they are still addressable",
              lib.get(good) is not None and lib.get(later) is not None)


def test_the_slot_is_taken_before_the_creator_runs():
    """THE WHOLE DESIGN IS THIS ORDERING. Reserving afterwards would leave the window
    exactly as wide as before while adding a file nobody needs."""
    print("[books] the record precedes the object")
    with _Books() as lib:
        world = SimWorld()
        seen = []

        def watching(tool, args):
            # AT THE MOMENT THE CREATOR RUNS, the slot must already be there and PENDING.
            seen.append([(r["status"], r["name"]) for r in lib.rows()])
            return world.execute(tool, args)

        select, holds = seams(world)
        program = {"body": [{"op": "new", "var": "alpha", "kind": "vm",
                             "args": {"os_type": "linux"}},
                            {"op": "ensure", "predicate": {
                                "shape": "count", "select": {"kind": "vm"}, "eq": 1}}]}
        res = ir_run(program, watching, select=select, holds=holds,
                     known_names=set(), consent=True, intent="achieve")
        check(f"the program runs ({res.get('why')})", res["ok"])
        check("the slot existed while the creator was in flight",
              seen and seen[0] == [(PENDING, "alpha")])
        check("and it settled EXIST afterwards",
              [r["status"] for r in lib.rows()] == [EXIST])
        check("recorded as CLAIMED, because a tool's word is what settled it",
              lib.rows()[0]["how"] == CLAIMED)


def test_a_creator_that_failed_settles_failed():
    print("[books] a refused creation is a fact too")
    with _Books() as lib:
        def refuses(tool, args):
            return {"success": False, "error": "no capacity"}

        program = {"body": [{"op": "new", "var": "alpha", "kind": "vm",
                             "args": {"os_type": "linux"}},
                            {"op": "ensure", "predicate": {
                                "shape": "count", "select": {"kind": "vm"}, "eq": 1}}]}
        ir_run(program, refuses, select=lambda q, s=None: [],
               holds=lambda p, s: (False, "empty"), known_names=set(),
               consent=True, intent="achieve")
        rows = lib.rows()
        check("the slot is FAILED, not absent", [r["status"] for r in rows] == [FAILED])
        check("and it says why", "no capacity" in rows[0]["why"])


def test_a_ledger_that_cannot_be_written_never_breaks_a_run():
    """A record that governs the world instead of describing it would be the wrong way
    round. Refusing to create a machine because a log file is read-only is that."""
    print("[books] book-keeping failure is not a lab failure")
    with _Books() as lib:
        lib.path = "/proc/nonexistent-and-unwritable"
        lib._at = os.path.join(lib.path, "creations.jsonl")
        world = SimWorld()
        select, holds = seams(world)
        program = {"body": [{"op": "new", "var": "alpha", "kind": "vm",
                             "args": {"os_type": "linux"}},
                            {"op": "ensure", "predicate": {
                                "shape": "count", "select": {"kind": "vm"}, "eq": 1}}]}
        res = ir_run(program, world.execute, select=select, holds=holds,
                     known_names=set(), consent=True, intent="achieve")
        check("the machine is still made", res["ok"] and "alpha" in world.vms)


def test_the_keeper_reads_the_world_and_touches_nothing():
    print("[books] it updates the map, never the territory")
    with _Books() as lib:
        world = SimWorld()
        world.execute("create_vm", {"name": "kept", "os_type": "linux"})
        lib.settle(lib.reserve("kept", "vm", at=1.0), EXIST, at=2.0)
        gone = lib.reserve("vanished", "vm", at=1.0)
        lib.settle(gone, EXIST, at=2.0)

        select, _holds = seams(world)
        before = len(world.calls)
        drift = _keeper.Keeper(lib, select=select).reconcile(now=10.0)

        check("the vanished one is reported MISSING",
              [r["name"] for r in drift["missing"]] == ["vanished"])
        check("and the record is corrected", lib.get(gone)["status"] == MISSING)
        check("stamped SEEN, because the keeper looked", lib.get(gone)["how"] == SEEN)
        check("THE WORLD IS UNTOUCHED — nothing recreated, nothing deleted",
              set(world.vms) == {"kept"} and len(world.calls) == before)
        check("the verdict names drift", drift["verdict"] == "drift")


def test_a_kind_the_world_cannot_enumerate_is_not_an_empty_kind():
    """Reading an empty answer as "there are none" would mark every record of that kind
    MISSING and report a healthy lab as gone — decision 6, applied to the auditor."""
    print("[books] unknown is not empty, here too")
    with _Books() as lib:
        lib.settle(lib.reserve("kept", "vm", at=1.0), EXIST, at=2.0)

        def blind(query):
            raise RuntimeError("this world cannot list vms")

        drift = _keeper.Keeper(lib, select=blind).reconcile(now=10.0)
        check("nothing is called missing", drift["missing"] == [])
        check("and the record is untouched", lib.get(lib.rows()[0]["uid"])["status"] == EXIST)


def test_a_pending_nobody_heard_back_from_expires():
    """ONLY REACHABLE BECAUSE THE RECORD PRECEDES THE OBJECT. Without the placeholder a
    creation that died mid-flight is indistinguishable from one that never started, and
    there is nothing for a sweep to find."""
    print("[books] a dead creation is catchable at all")
    with _Books() as lib:
        stuck = lib.reserve("half_made", "vm", at=100.0)
        drift = _keeper.Keeper(lib).reconcile(now=200.0, lease=600.0)
        check("inside its lease it is left alone", drift["expired"] == []
              and lib.get(stuck)["status"] == PENDING)
        drift = _keeper.Keeper(lib).reconcile(now=1000.0, lease=600.0)
        check("past it, it is expired", [r["name"] for r in drift["expired"]]
              == ["half_made"])
        check("settled FAILED and said why", lib.get(stuck)["status"] == FAILED
              and "lease" in lib.get(stuck)["why"])


def test_something_the_books_never_recorded_is_reported_as_untracked():
    print("[books] made out of band, and said so")
    with _Books() as lib:
        world = SimWorld()
        world.execute("create_vm", {"name": "stranger", "os_type": "linux"})
        lib.settle(lib.reserve("known", "vm", at=1.0), EXIST, at=2.0)
        select, _holds = seams(world)
        drift = _keeper.Keeper(lib, select=select).reconcile(now=10.0)
        check("the stranger is named",
              {r["name"] for r in drift["untracked"]} == {"stranger"})
        check("and nothing was done about it", set(world.vms) == {"stranger"})


def test_the_report_is_read_by_somebody():
    """AN ENSURE NOBODY READS is how `disjoint` sat declared-and-never-evaluated for weeks.
    The keeper is a world-regime ENSURE, so its consumer is part of the build."""
    print("[books] the drift report has a reader")
    from orchestrator.ai.chat import shortcuts

    names = {type(s).__name__ for s in shortcuts._REGISTRY}
    check("the `books` shortcut is registered", "Books" in names)
    reader = next(s for s in shortcuts._REGISTRY if type(s).__name__ == "Books")
    check("and it answers to the word", reader.matches("books"))
    check("a clear reconciliation says what it is a statement ABOUT",
          "not a promise about the lab" in _keeper.Keeper.report(
              {"checked": 0, "verdict": "clear"}))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "books"))


if __name__ == "__main__":
    main()
