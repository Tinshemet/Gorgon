"""words.py — `words`: what the lab has been TAUGHT, and what is waiting to be.

    words                  every entry — what routes, and what is proposed
    words ratify <word>    sign it. From now on it settles readings
    words reject <word>    refuse the PENDING proposals for it
    words forget <word>    withdraw one already in force. It stops routing; the record stays

⇒ CHANGING a word needs no special verb: state the new fact, ratify it, and the old entry is
  superseded. REMOVING one is `forget`, and it existed nowhere until the operator asked how
  you would do it — the store could be overwritten and not unsaid.

# ⇒⇒ THE AUDIT SURFACE IS PART OF THE DESIGN, NOT A CONVENIENCE

[[gorgon-encyclopedia]] names it and gives the reason: *"it needs an audit surface — a `words`
shortcut beside `books` — because the real risk is one misspoken answer becoming permanent and
silent."* A knowledge store you cannot read back is how a wrong fact lives forever.

**AND RATIFICATION IS THE WHOLE SAFETY PROPERTY, SO IT HAS TO HAVE A DOOR.** `Archive.known`
returns ratified-and-told entries only, which means a proposal describes and never permits.
That rule is worth nothing if there is no way for a person to sign one — the store would fill
with proposals nothing could ever act on, which is a different failure from the same family:
a mechanism that cannot be exercised.

⇒ IT CHANGES NOTHING IN THE LAB, structurally: an entry says what a WORD means. The most it can
  do once ratified is let a later request settle a row it would otherwise have asked about.
"""
from typing import List

from shared.display import console

from .base import Shortcut


class Words(Shortcut):
    """`words` — the knowledge archive, and the ratification door."""

    def matches(self, ui: str) -> bool:
        said = ui.strip().lower()
        return said == "words" or said.startswith("words ")

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        from orchestrator.seam.archive import ARCHIVE

        rest = ui.strip()[len("words"):].strip()

        if rest.lower().startswith("ratify "):
            word = rest[len("ratify"):].strip()
            entry = ARCHIVE.ratify(word, who="operator")
            ARCHIVE.save()
            if entry:
                console.print(f"[bold green]ratified[/bold green] {entry.word!r} — "
                              f"{entry.description!r}"
                              + (f"  -> kind {entry.kind}" if entry.kind else ""))
            else:
                console.print(f"[warn]nothing pending for {word!r}[/warn]")
            return

        # ⇒ WITHDRAWING A SIGNED ENTRY. `reject` refuses something PENDING; this takes back
        #   something already in force, which is the half that was missing — a signature you
        #   cannot take back is a trapdoor rather than a signature.
        if rest.lower().startswith("forget "):
            word = rest[len("forget"):].strip()
            gone = ARCHIVE.retract(word)
            ARCHIVE.save()
            console.print(f"[bold]withdrawn[/bold] {gone.word!r} — it no longer settles "
                          f"anything [dim](the record is kept)[/dim]" if gone
                          else f"[warn]nothing in force for {word!r}[/warn]")
            return

        if rest.lower().startswith("reject "):
            word = rest[len("reject"):].strip()
            n = ARCHIVE.reject(word)
            ARCHIVE.save()
            console.print(f"[dim]refused {n} proposal(s) for {word!r}[/dim]" if n
                          else f"[warn]nothing pending for {word!r}[/warn]")
            return

        known, waiting = ARCHIVE.ratified(), ARCHIVE.pending()
        if not known and not waiting:
            console.print("[dim]the archive is empty. A statement teaches it — "
                          "`plan --seam a jumpbox is a vm` — and nothing routes until you "
                          "`words ratify <word>`.[/dim]")
            return

        if known:
            console.print(f"[bold]{len(known)} entr(ies) in force[/bold]")
            for e in known:
                # ⇒ A NEGATIVE ENTRY IS PRINTED AS ONE. *"routers are not a thing this lab
                #   keeps"* is an ANSWER, and a reader who cannot see it would ask again.
                shape = f"-> {e.kind}" if e.kind else ("NOT a thing this lab keeps"
                                                       if not e.holds else "")
                console.print(f"    {e.word:16} {e.description[:44]:44} [dim]{shape}[/dim]")

        if waiting:
            console.print(f"\n[bold yellow]{len(waiting)} waiting for you[/bold yellow] "
                          f"[dim](these do NOT route)[/dim]")
            for e in waiting:
                console.print(f"    {e.word:16} {e.description[:44]:44} "
                              f"[dim]from: {e.said[:36]}[/dim]")
            console.print("[dim]    `words ratify <word>` to sign one, "
                          "`words reject <word>` to refuse it[/dim]")
