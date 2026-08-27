"""mask_run.py — running a PROCEDURE mask by its word.

A verb mask can point at a saved procedure (`define contain as the quarantine procedure`,
ratified with `masks ratify contain`). An operation mask expands in the seam and re-reads; a
PROCEDURE mask cannot — a procedure is a compiled program, run by the engine — so its word is
caught here and handed to the SAME gated runner `procedures run` uses. Being named by a mask
earns the procedure nothing: it meets consent, the destroy question and the ban check exactly
as it would if typed by hand.

    contain              run the procedure `contain` masks
    contain k=v          ... binding its parameters

Only a RATIFIED procedure mask matches — an unsigned one does nothing, the archive's rule.
"""
from typing import List

from shared.display import console

from .base import Shortcut


class MaskRun(Shortcut):
    """A ratified procedure-mask word → run the procedure it points at, gated."""

    def _name(self, ui: str):
        head = ui.strip().split()
        if not head:
            return None, None
        from orchestrator.languages.english.seam.verb_alias import procedure_for
        return head[0], procedure_for(head[0].lower())

    def matches(self, ui: str) -> bool:
        _, name = self._name(ui)
        return name is not None

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        from planner import procedures as _procs
        from .procedures import Procedures

        parts = ui.strip().split()
        word, name = self._name(ui)
        # ⇒ only `k=v` tokens are procedure parameters; a bare trailing word (a pronoun) has no
        #   parameter to bind yet — noted as a refinement, not guessed at here.
        given = [a for a in parts[1:] if "=" in a]
        console.print(f"[dim]mask[/dim] [bold]{word}[/bold] [dim]→ procedure[/dim] {name}")
        Procedures._run_one(_procs.LIBRARY, name, given, verbose)
