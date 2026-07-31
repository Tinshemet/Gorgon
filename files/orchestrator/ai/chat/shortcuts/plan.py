"""plan.py — `plan <request>`: route one request through the ENGINE ARCHITECTURE.

OPT-IN, AND DELIBERATELY NOT THE DEFAULT. The architecture behind this is measured — the
ghost writer covers 13/13 rungs and 1932/2000 generated cases, across two unrelated domains,
with no model in the loop. What is NOT measured is the front seam: the extractor turns
English into components at 6/39, so making this the default would replace a chat flow that
works with one that mistranslates two requests in three.

That is the "if everything works" clause not being met, and shipping anyway would be the
exact failure of 2026-07-31 — a mechanism believed good because the parts around it were.

SO IT SITS HERE, WHERE IT CAN EARN THE SWAP. Typing `plan …` exercises the whole pipeline
against real requests and prints what each stage did, which is how the extractor gets real
evidence instead of thirteen rungs. The default path stays exactly as it was.

WHAT IT SHOWS, and why the printing matters as much as the running: each stage is named, so a
wrong answer says WHICH half was wrong. Under the old path a bad program could mean the goal
was misread or the writing fumbled and nothing distinguished them — a day went into that
ambiguity. Here `UNTRANSLATED` and `UNMET` are different words.
"""
from typing import List

from shared.display import console

from .base import Shortcut

_PREFIX = "plan "


class Plan(Shortcut):
    """`plan create a vm named alpha` — the engine path, one request."""

    def matches(self, ui: str) -> bool:
        return ui.strip().lower().startswith(_PREFIX) and len(ui.strip()) > len(_PREFIX)

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        request = ui.strip()[len(_PREFIX):].strip()

        # IMPORTED HERE, NOT AT MODULE LOAD. A shortcut registers itself at class-definition
        # time, so every import in this file is paid by every chat session that never types
        # `plan`. The engine layer pulls in the planner, the manifest and the tool registry;
        # none of that should cost a session that is not using it.
        from orchestrator.ai.active_library import LIBRARY
        from orchestrator.ai.engines import Channel, Orchestrator, QemuEngine, Registry
        from orchestrator.ai.engines.channel import Answer
        from orchestrator.pipeline import execute_tool

        def guarded(tool, args):
            # THE SAME DOOR. A program's statements reach the world through the gauntlet a
            # single tool call meets — legal filter, commit gate, contract tier, watchdog,
            # killswitch. Building a second executor here would quietly create a second door,
            # and the whole point of the engine layer is that there is one.
            return execute_tool(tool, args, verbose=verbose)

        def translate(gap, world=None):
            from tests.bench import extract as _extract
            try:
                raw = _extract.extract(str(gap))
            except Exception as e:
                return Answer(None, "extractor", f"{type(e).__name__}: {e}")
            got = _extract.to_goals(raw, str(gap))
            return Answer(got, "extractor", "") if got else Answer(None, "extractor",
                                                                   "no usable goal")
        translate.name = "extractor"

        registry = Registry()
        registry.mount(QemuEngine(LIBRARY, guarded))
        result = Orchestrator(registry, Channel([translate])).handle(request)

        outcome = result.get("outcome")
        colour = {"DONE": "ok"}.get(outcome, "warn")
        console.print(f"[{colour}]{outcome}[/{colour}]  {result.get('why') or ''}")
        for line in result.get("log", []):
            console.print(f"  [dim]{line}[/dim]")
        if result.get("rendered"):
            console.print("\n[bold]the program it wrote[/bold]")
            for line in result["rendered"].splitlines():
                console.print(f"  {line}")
        if result.get("grounded") is not None:
            console.print(f"\n  grounded: {result['grounded']} · "
                          f"{len(result.get('calls') or [])} call(s)")
        if outcome == "UNCLAIMED":
            console.print(f"  mounted: {result.get('mounted')} · "
                          f"callable capabilities: {result.get('capabilities')}")
