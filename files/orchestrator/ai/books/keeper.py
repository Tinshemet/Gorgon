"""keeper.py — the book keeper. It updates the map, never the territory.

THE OPERATOR'S FRAMING, and it settles the design: THE BOOK KEEPER IS A DETERMINISTIC,
WORLD-REGIME ENSURE. An ENSURE reads, reports a verdict and changes nothing; this reads the
world, reports drift and changes nothing.

    the book keeper is the ENSURE half of the world; programs are the ACHIEVE half.

IT MAY NEVER ACT ON THE WORLD, and that is structural rather than a rule someone remembers.
A missing machine is marked MISSING, never recreated — recreating is a MAKE, and MAKEs
belong to programs with consent and a contract tier behind them. A keeper that fixed things
would be a background process quietly doing high-impact work with nobody asking, which is
the one shape this codebase refuses everywhere.

IT OWNS RECONCILIATION ONLY. The stores keep their own behaviour; this compares and corrects
THE RECORD. It is an auditor, not a manager, and that is the guard against the god object
the design note asked for.

TRIGGERS AND A TIMER ARE DIFFERENT JOBS. A trigger writes through what a call CLAIMED —
instant, and a claim. A sweep reads the world and compares — periodic, and the truth. THE
TIMER IS THE GUARANTEE; TRIGGERS ARE ONLY LATENCY, because a trigger-only system cannot see
what fires no trigger: a dead PENDING, an out-of-band delete, a tool that acted and then
died. Silence looks exactly like nothing-happened, and this codebase has learned that twice
in writing.

AND `reconcile` IS CALLABLE ON DEMAND, never only on a tick. Otherwise the only way to test
it is to sleep, and an untestable thing stays broken.

WHO READS THE REPORT — named before building, because an ENSURE nobody reads is exactly how
`disjoint` sat declared-and-never-evaluated for weeks, answering false in every world. The
reader is the OPERATOR, through the `books` shortcut. There is no daemon and this does not
claim one.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .ledger import (CLAIMED, DELETED, EXIST, FAILED, LEDGER, MISSING, PENDING, SEEN,
                     Ledger)

# HOW LONG BEFORE A CREATION NOBODY HEARD BACK FROM IS CALLED DEAD. Ten minutes, and the
# number is deliberately not the sweep interval — see `Ledger.pending`.
LEASE = 600.0


class Keeper:
    """Reads the world, compares it to the books, and says where they disagree."""

    def __init__(self, ledger: Optional[Ledger] = None,
                 select: Optional[Callable] = None):
        self.ledger = ledger or LEDGER
        # `select(query) -> names` — the SAME seam every query in the language uses. A keeper
        # with its own way of reading the world would be auditing against a second world.
        self._select = select

    def reconcile(self, now: float, lease: float = LEASE) -> Dict[str, Any]:
        """What the books say versus what the world holds. Changes nothing in the world.

        THREE KINDS OF DRIFT, and they are not the same event:

            EXPIRED   still PENDING past its lease — a creation that never reported back.
                      Only reachable BECAUSE the record precedes the object; without the
                      placeholder there is nothing to sweep.
            MISSING   the books say it exists and the world does not show it. The INDEX no
                      longer resolves; the identity is untouched, which is what makes the
                      word honest.
            UNTRACKED the world holds something the books never recorded — made out of band,
                      or made before this ledger existed.

        THE RECORD IS CORRECTED, THE WORLD IS NOT. An expired PENDING is settled FAILED and
        a vanished EXIST is settled MISSING, both stamped `seen` rather than `claimed`,
        because the keeper looked. Nothing is created, deleted or restarted.
        """
        rows = self.ledger.rows()
        expired = [r for r in rows
                   if r.get("status") == PENDING and now - float(r.get("at") or 0) > lease]
        for r in expired:
            self.ledger.settle(r["uid"], FAILED, now, how=SEEN,
                               why=f"still pending {int(now - float(r.get('at') or 0))}s "
                                   f"after it was reserved, past a {int(lease)}s lease")

        missing: List[Dict[str, Any]] = []
        untracked: List[Dict[str, Any]] = []
        if self._select is not None:
            live: Dict[str, set] = {}
            for r in rows:
                kind = r.get("kind")
                if kind and kind not in live:
                    try:
                        live[kind] = set(self._select({"kind": kind}) or ())
                    except Exception:
                        # A KIND THE WORLD CANNOT ENUMERATE IS NOT AN EMPTY KIND. Reading an
                        # empty answer as "there are none" would mark every record of that
                        # kind MISSING and report a healthy lab as gone.
                        live[kind] = None
            for r in rows:
                kind, name = r.get("kind"), r.get("name")
                if r.get("status") != EXIST or live.get(kind) is None:
                    continue
                if name not in live[kind]:
                    missing.append(r)
                    self.ledger.settle(r["uid"], MISSING, now, how=SEEN,
                                       why=f"no {kind} named {name!r} in the world")
            known = {(r.get("kind"), r.get("name")) for r in rows
                     if r.get("status") in (PENDING, EXIST)}
            for kind, names in live.items():
                for name in sorted(names or ()):
                    if (kind, name) not in known:
                        untracked.append({"kind": kind, "name": name})

        return {"checked": len(rows), "expired": expired, "missing": missing,
                "untracked": untracked,
                "verdict": "clear" if not (expired or missing or untracked) else "drift"}

    @staticmethod
    def report(drift: Dict[str, Any]) -> str:
        """The drift, as sentences. Read by the operator, and by nothing else.

        NAMED, NOT COUNTED, for the reason the destructive-step report gives: "7 missing" and
        "vm-orchestrator is missing" are different sentences and only one of them stops a
        person.
        """
        lines = [f"book keeper · {drift['checked']} slot(s) · verdict {drift['verdict']}"]
        for r in drift.get("expired") or ():
            lines.append(f"   [expired ] {r.get('kind')} {r.get('name')!r}  <- {r.get('why')}"
                         if r.get("why") else
                         f"   [expired ] {r.get('kind')} {r.get('name')!r}")
        for r in drift.get("missing") or ():
            lines.append(f"   [missing ] {r.get('kind')} {r.get('name')!r}  "
                         f"<- the books say it exists and the world does not show it")
        for r in drift.get("untracked") or ():
            lines.append(f"   [untracked] {r.get('kind')} {r.get('name')!r}  "
                         f"<- in the world, in no record")
        if drift["verdict"] == "clear":
            lines.append("   NOTHING DRIFTED — and that is a statement about the RECORD, "
                         "not a promise about the lab.")
        return "\n".join(lines)
