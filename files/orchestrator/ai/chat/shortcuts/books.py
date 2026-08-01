"""books.py — `books`: what the record says, and where it disagrees with the world.

THE READER, NAMED BEFORE THE KEEPER WAS BUILT. The design note asked for exactly this and
gave the reason: an ENSURE nobody reads is how `disjoint` sat declared-and-never-evaluated
for weeks, answering false in every world. The book keeper is a world-regime ENSURE, so it
needs a consumer or it is a mechanism that cannot fail because nothing looks at it.

    books           the ledger, and a reconciliation against the lab right now

IT CHANGES NOTHING IN THE LAB, and that is structural rather than a promise. A missing
machine is marked MISSING; it is never recreated. Recreating is a MAKE and MAKEs belong to
programs with consent and a contract tier behind them — a keeper that fixed things would be
a background process quietly doing high-impact work with nobody asking.

NO DAEMON. The sweep runs when a person asks for it, exactly as `routines` does, and the
report says what it is a statement about: the RECORD, not a promise about the lab.
"""
import time
from typing import List

from shared.display import console

from .base import Shortcut


class Books(Shortcut):
    """`books` — the creation ledger and today's drift."""

    def matches(self, ui: str) -> bool:
        return ui.strip().lower() == "books"

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        from orchestrator.ai.active_library import LIBRARY
        from orchestrator.ai.books import LEDGER, Keeper
        from orchestrator.ai.planner.program import seams as _seams

        rows = LEDGER.rows()
        if not rows:
            console.print("[dim]the books are empty. A slot is reserved the moment a "
                          "program's NEW starts — nothing has created anything yet.[/dim]")
            return

        console.print(f"[bold]{len(rows)} slot(s)[/bold]")
        for r in rows[-20:]:
            # HOW IT IS KNOWN, SHOWN. An EXIST that came from a tool's return value and one
            # the keeper saw with its own eyes are not the same fact.
            console.print(f"  {r.get('status',''):<9} {str(r.get('kind','')):<9} "
                          f"{str(r.get('name','')):<20} [dim]{r.get('how','')}"
                          f"{'  ' + r['why'] if r.get('why') else ''}[/dim]")
        if len(rows) > 20:
            console.print(f"  [dim]… {len(rows) - 20} older[/dim]")

        select, _holds = _seams(LIBRARY)
        drift = Keeper(LEDGER, select=select).reconcile(time.time())
        console.print()
        colour = "ok" if drift["verdict"] == "clear" else "warn"
        for line in Keeper.report(drift).splitlines():
            console.print(f"[{colour}]{line}[/{colour}]" if line.startswith("book")
                          else f"  {line}")
