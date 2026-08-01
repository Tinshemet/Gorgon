"""ledger.py — the creation ledger. A slot is reserved BEFORE the thing exists.

THE REGISTRY INJECTION, and it is the core of the design rather than a detail. The
operator's analogy: *"its basically reserving memory space but in registry form."* It is
`malloc` for the world — you reserve the slot, with a stable address, before the object.

WHAT IT FIXES: today there is a WINDOW in which work is in flight and unaccounted for.
Between "NEW starts" and "the creator returns" the object exists in no record at all, and in
that window a concurrent reader cannot tell "not started" from "being built"; if the process
dies there is NO TRACE IT WAS EVER ATTEMPTED; and `ACHIEVE` has nothing to watch because
there is nothing to point at. Note the trap in the last one — a sweep cannot catch a dead
creation either, because there is nothing to sweep. The injection is what makes the
guarantee reachable at all.

IT INVERTS THE ORDERING EVERY OTHER RECORD IN GORGON USES. The event log, the findings, the
library's tool-effect updates — all written AFTER the thing happened. This one is written
BEFORE, so there is never a moment when something is happening that nothing knows about.
It is also what makes PENDING a real state rather than a label: you cannot have a "pending"
without a record created before completion.

IDENTITY AND INDEX ARE TWO FIELDS, and this is the one place a derived value would quietly
have become an identity. `hash(name, kind, where)` is the operator's original creation ID —
what it is and where it is, *"kind of like a pointer to it"* — and `where` is the CURRENT
location, which moves. Recomputing your way back to an object fails precisely when the
object is most broken. So the uid is the identity and the hash is the index: a move updates
the index and every existing reference still resolves, and MISSING becomes honest — it means
*the index no longer resolves*, not *the name changed*.

APPEND-ONLY, FOLDED ON READ. A crash halfway through a write leaves every earlier record
intact, and the history of a slot is readable rather than overwritten — a PENDING that
became EXIST and the EXIST alone are different evidence.

PROVENANCE IS PART OF THE FACT. An EXIST that came from a tool's return value and an EXIST
the keeper saw with its own eyes are not the same claim, which is the distinction `p_world`
already measures.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Any, Dict, List, Optional

# `PENDING → EXIST | FAILED`, plus DELETED and MISSING. PENDING is the same win as
# `alive = unknown`: "not finished" stops being confused with "not there", which is
# decision 6 generalised from reachability to existence.
PENDING = "PENDING"
EXIST = "EXIST"
FAILED = "FAILED"
DELETED = "DELETED"
MISSING = "MISSING"

STATES = (PENDING, EXIST, FAILED, DELETED, MISSING)

# WHO SAID SO. `claimed` is a tool's return value; `seen` is the keeper's own reading of the
# world. Kept because they are not the same fact and a reconciliation that conflated them
# would be taking the tool's word again, one layer up.
CLAIMED = "claimed"
SEEN = "seen"


def _home() -> str:
    base = os.environ.get("GORGON_HOME") or os.path.expanduser("~/.gorgon")
    return os.path.join(base, "books")


def index(name: str, kind: str, where: Any = None) -> str:
    """`hash(name, kind, where)` — the operator's creation ID, recomputable by anyone.

    RECOMPUTABLE WITHOUT A LOOKUP is the whole reason it is a hash and not a counter: a
    caller holding the three facts can address the slot without asking anybody. That is also
    why it must not be the identity — `where` moves.
    """
    raw = f"{kind}\x00{name}\x00{'' if where is None else where}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class Ledger:
    """Every creation this system has started, and what became of it."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or _home()
        self._at = os.path.join(self.path, "creations.jsonl")

    # ── writing ──────────────────────────────────────────────────────────────
    def _append(self, row: Dict[str, Any]) -> None:
        os.makedirs(self.path, exist_ok=True)
        with open(self._at, "a") as fh:
            # A TORN LINE MUST COST ONE ROW, NOT TWO. A process that dies mid-write leaves a
            # line with no newline, and appending straight onto it fuses the next record to
            # the wreckage — so the crash takes the row AFTER it as well, which is the row
            # written by whoever came along to fix things.
            if fh.tell() and not self._ends_clean():
                fh.write("\n")
            fh.write(json.dumps(row, default=str) + "\n")

    def _ends_clean(self) -> bool:
        try:
            with open(self._at, "rb") as fh:
                fh.seek(-1, os.SEEK_END)
                return fh.read(1) == b"\n"
        except OSError:
            return True

    def reserve(self, name: str, kind: str, at: float, where: Any = None,
                by: str = "") -> str:
        """Take the slot. Returns the uid, minted once and durable.

        CALLED BEFORE THE CREATOR RUNS. Everything about this design follows from that one
        ordering, and calling it afterwards would leave the window exactly as wide as before
        while adding a file nobody needs.
        """
        uid = uuid.uuid4().hex
        self._append({"uid": uid, "hash": index(name, kind, where), "status": PENDING,
                      "name": name, "kind": kind, "where": where, "at": at,
                      "by": by, "how": CLAIMED})
        return uid

    def settle(self, uid: str, status: str, at: float, how: str = CLAIMED,
               why: str = "") -> None:
        """What became of a reserved slot. Appended, never overwritten."""
        if status not in STATES:
            raise ValueError(f"{status!r} is not a lifecycle state ({', '.join(STATES)})")
        self._append({"uid": uid, "status": status, "at": at, "how": how, "why": why})

    # ── reading ──────────────────────────────────────────────────────────────
    def rows(self) -> List[Dict[str, Any]]:
        """Every slot, folded to its latest state, in the order they were reserved.

        A DAMAGED LINE IS SKIPPED. An append-only log written by a process that can die
        mid-line will eventually have one, and refusing to read the whole ledger because of
        its last byte would lose the very history it exists to keep.
        """
        by_uid: Dict[str, Dict[str, Any]] = {}
        try:
            with open(self._at) as fh:
                lines = fh.readlines()
        except OSError:
            return []
        for line in lines:
            try:
                row = json.loads(line)
            except Exception:
                continue
            uid = row.get("uid")
            if not uid:
                continue
            if uid in by_uid:
                by_uid[uid] = {**by_uid[uid], **row}
            else:
                by_uid[uid] = row
        return list(by_uid.values())

    def get(self, uid: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.rows() if r.get("uid") == uid), None)

    def pending(self, now: float, lease: float) -> List[Dict[str, Any]]:
        """Slots still PENDING past their lease — creations nobody ever heard back from.

        THE LEASE IS A SEPARATE NUMBER FROM THE SWEEP INTERVAL, because "how long before I
        call a creation dead" and "how often do I check the books" are different questions
        and answering them with one number means tuning either breaks the other.
        """
        return [r for r in self.rows()
                if r.get("status") == PENDING and now - float(r.get("at") or 0) > lease]


# ONE LEDGER, so the executor that reserves a slot and the keeper that reconciles it are
# writing to the same book. A second instance pointed elsewhere is how a creation comes to
# exist for the thing that made it and not for the thing that audits it.
LEDGER = Ledger()
