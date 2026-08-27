"""masks.py — `masks`: the verb aliases the lab has been TAUGHT, and what waits to be.

    masks                  every mask — what expands, and what is proposed
    masks ratify <word>    sign it. From now on the word expands to its operation
    masks reject <word>    refuse the PENDING proposals for it
    masks forget <word>    withdraw one already in force. It stops expanding; the record stays

⇒ THE VERB-SIDE MIRROR OF `words`. `define relab as reset the lab` files a PENDING mask; this is
  its audit-and-ratification door. The safety property is the archive's: `AliasStore.known`
  returns ratified-and-told masks only, so a proposal describes and never permits — and that rule
  is worth nothing without a door for a person to sign one. A mask expands to a REAL operation the
  authority gate still checks, so ratifying one grants no authority a plain call would not.
"""
from typing import List

from shared.display import console

from .base import Shortcut


class Masks(Shortcut):
    """`masks` — the verb-alias store, and the ratification door."""

    def matches(self, ui: str) -> bool:
        said = ui.strip().lower()
        return said == "masks" or said.startswith("masks ")

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        from orchestrator.languages.english.seam.verb_alias import ALIASES

        rest = ui.strip()[len("masks"):].strip()

        if rest.lower().startswith("ratify "):
            word = rest[len("ratify"):].strip()
            entry = ALIASES.ratify(word, who="operator")
            ALIASES.save()
            if entry:
                console.print(f"[bold green]ratified[/bold green] {entry.word!r} — "
                              f"expands to {entry.operation!r}")
            else:
                console.print(f"[warn]nothing pending for {word!r}[/warn]")
            return

        # ⇒ WITHDRAWING A SIGNED MASK — the half a signature needs to not be a trapdoor.
        if rest.lower().startswith("forget "):
            word = rest[len("forget"):].strip()
            gone = ALIASES.retract(word)
            ALIASES.save()
            console.print(f"[bold]withdrawn[/bold] {gone.word!r} — it no longer expands "
                          f"[dim](the record is kept)[/dim]" if gone
                          else f"[warn]nothing in force for {word!r}[/warn]")
            return

        if rest.lower().startswith("reject "):
            word = rest[len("reject"):].strip()
            n = ALIASES.reject(word)
            ALIASES.save()
            console.print(f"[dim]refused {n} proposal(s) for {word!r}[/dim]" if n
                          else f"[warn]nothing pending for {word!r}[/warn]")
            return

        known, waiting = ALIASES.ratified(), ALIASES.pending()
        if not known and not waiting:
            console.print("[dim]no masks yet. `define relab as reset the lab` proposes one, "
                          "and nothing expands until you `masks ratify <word>`.[/dim]")
            return

        if known:
            console.print(f"[bold]{len(known)} mask(s) in force[/bold]")
            for e in known:
                tag = "  [dim](procedure)[/dim]" if e.target == "procedure" else ""
                console.print(f"    {e.word:16} -> {e.operation[:44]:44}{tag}")

        if waiting:
            console.print(f"\n[bold yellow]{len(waiting)} waiting for you[/bold yellow] "
                          f"[dim](these do NOT expand)[/dim]")
            for e in waiting:
                tag = " (procedure)" if e.target == "procedure" else ""
                console.print(f"    {e.word:16} -> {(e.operation+tag)[:40]:40} "
                              f"[dim]from: {e.said[:24]}[/dim]")
            console.print("[dim]    `masks ratify <word>` to sign one, "
                          "`masks reject <word>` to refuse it[/dim]")
