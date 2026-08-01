"""routines.py — `routines`: what runs without being asked, and what is due right now.

A PROCEDURE IS A TOOL YOU WROTE. A ROUTINE is one the CLOCK calls; a TRIGGER is one the
WORLD calls. Same object, one extra field — `every: "1h"` or `when: <predicate>` — because
making them separate kinds would mean three stores, three validators and three places to
look, for a difference that is entirely about who decides to start it.

    routines            what is declared, and what is due
    routines run        run everything due, through the ordinary engine path

THE SWEEP IS OPERATOR-DRIVEN AND THAT IS SAID OUT LOUD. There is no daemon: `routines run`
is a person deciding this is a good moment. A background scheduler is a real thing to build
and it is not built, so this does not pretend to be one — a routine that claims to fire
hourly and fires when somebody remembers would be worse than no routine at all, because the
claim is what people plan around.

WHAT MAKES IT SAFE IS THAT IT IS THE ORDINARY PATH. A due routine is served by the same
orchestrator, the same guarded executor and the same intent ladder as anything typed by
hand. Being on a schedule earns a program nothing; it only decides when it is offered.
"""
import time
from typing import List

from shared.display import console

from .base import Shortcut

_WORD = "routines"


class Routines(Shortcut):
    """`routines` / `routines run` — the scheduled half of the procedure library."""

    def matches(self, ui: str) -> bool:
        return ui.strip().lower() in (_WORD, f"{_WORD} run")

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        # IMPORTED HERE for the reason `plan` states: a shortcut registers at class
        # definition, so every import in this file is paid by a session that never types it.
        from orchestrator.ai.planner import procedures as _procs
        from orchestrator.ai.planner.program import seams as _seams
        from orchestrator.ai.active_library import LIBRARY

        doing = ui.strip().lower().endswith(" run")
        declared = [p for p in _procs.LIBRARY.all() if p.get("every") or p.get("when")]
        if not declared:
            console.print("[dim]nothing runs on its own. A stored program becomes a "
                          "routine with `every: 1h` or a trigger with `when: <check>`.[/dim]")
            return

        console.print("[bold]what runs without being asked[/bold]")
        for p in declared:
            how = (f"every {p['every']}" if p.get("every") else "when the world says so")
            last = _procs.LIBRARY.state(p["name"]).get("last_run")
            when = (f"last ran {int(time.time() - last)}s ago" if last else "never run")
            console.print(f"  · {p['name']:<24} {how:<22} [dim]{when}[/dim]")

        # THE WORLD'S OWN SEAMS, so a trigger's condition is evaluated against the lab the
        # program would run against. A sweep that judged against anything else would fire on
        # a world nobody is looking at.
        _select, holds = _seams(LIBRARY)
        due = _procs.LIBRARY.due(time.time(), holds=holds)
        if not due:
            console.print("\n[dim]nothing is due.[/dim]")
            return

        console.print(f"\n[bold]{len(due)} due[/bold]")
        for item in due:
            console.print(f"  · {item['name']}  [dim]{item['why']}[/dim]")
        if not doing:
            console.print("[dim]`routines run` to run them.[/dim]")
            return

        from orchestrator.ai.engines import rig as _rig
        from orchestrator.pipeline import execute_tool

        def guarded(tool, args):
            # THE SAME DOOR, and the same bookkeeping — see `plan.py`, which explains why
            # both halves are needed and what broke when only the first was.
            result = execute_tool(tool, args, verbose=verbose)
            try:
                LIBRARY.apply(tool, args, result=result)
            except Exception:
                pass
            return result

        orch = _rig.build(guarded, narrate=True)
        for item in due:
            console.print(f"\n[bold]{item['name']}[/bold]  {item['why']}")
            # CALLED BY NAME, as a one-statement program. A stored procedure is a legal call
            # target and its body runs through the same visitor — being due does not let it
            # skip a gate it would otherwise meet.
            #
            # `achieve` BECAUSE A ROUTINE IS A STANDING COMMAND. The operator wrote it to
            # make something so and said when; the intent was granted at authoring time, and
            # asking again at 3am is not a question anybody can answer.
            out = orch.handle(item["name"], intent="achieve",
                              components=[{"_call": (item["name"], {})}])
            colour = {"DONE": "ok", "REFUSED": "warn"}.get(out.get("outcome"), "warn")
            console.print(f"  [{colour}]{out.get('outcome')}[/{colour}]  "
                          f"{out.get('why') or ''}")
            # RECORDED WHATEVER HAPPENED. A routine whose run failed has still RUN, and not
            # recording it would re-offer it on every sweep — a failing hourly job becoming a
            # continuous one, which is how a schedule turns into an outage.
            _procs.LIBRARY.remember(item["name"], last_run=time.time())
