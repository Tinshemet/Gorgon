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
    """`plan create a vm named alpha` — the engine path, one request.

    `plan --dry <request>` plans and shows, WITHOUT ACTING. It exists because this path is
    pointed at a real lab: the first thing it did against one was compute that "exactly two
    machines" needs seven deletions, naming vm-orchestrator and vm-executor among them. That
    is a fine thing to be told and a poor thing to discover. A dry run answers the only
    question worth asking first — WHAT WOULD THIS DO — and the in-session already knows,
    because every step declares its cost and what it would destroy before the verdict.
    """

    def matches(self, ui: str) -> bool:
        return ui.strip().lower().startswith(_PREFIX) and len(ui.strip()) > len(_PREFIX)

    def run(self, ui: str, messages: List[dict], runtime_drift_count: int,
            verbose: bool) -> None:
        request = ui.strip()[len(_PREFIX):].strip()
        dry = False
        for flag in ("--dry", "-n"):
            if request.lower().startswith(flag + " "):
                dry, request = True, request[len(flag):].strip()

        # IMPORTED HERE, NOT AT MODULE LOAD. A shortcut registers itself at class-definition
        # time, so every import in this file is paid by every chat session that never types
        # `plan`. The engine layer pulls in the planner, the manifest and the tool registry;
        # none of that should cost a session that is not using it.
        from orchestrator.ai.active_library import LIBRARY
        from orchestrator.ai.engines import (Channel, ExecutorEngine, Orchestrator,
                                             QemuEngine, Registry)
        from orchestrator.ai.engines.channel import Answer
        from orchestrator.pipeline import execute_tool

        def guarded(tool, args):
            # THE SAME DOOR. A program's statements reach the world through the gauntlet a
            # single tool call meets — legal filter, commit gate, contract tier, watchdog,
            # killswitch. Building a second executor here would quietly create a second door,
            # and the whole point of the engine layer is that there is one.
            return execute_tool(tool, args, verbose=verbose)

        def translate(gap, world=None):
            # STILL IN THE BENCH, AND DELIBERATELY. The extractor is the one component of
            # this path that is NOT measured well enough to be production — 9/39 — and the
            # `plan` shortcut exists precisely to earn it evidence. Moving it out would say
            # it had arrived. The world model made the opposite journey the same day, for
            # the opposite reason: it was measured, and a production mount depended on it.
            from tests.bench import extract as _extract
            try:
                raw = _extract.extract(str(gap))
            except Exception as e:
                return Answer(None, "extractor", f"{type(e).__name__}: {e}")
            got = _extract.to_goals(raw, str(gap))
            return Answer(got, "extractor", "") if got else Answer(None, "extractor",
                                                                   "no usable goal")
        translate.name = "extractor"

        from orchestrator.ai.engines import insession as _insession

        offered = []

        def decide(step, session):
            offered.append(step)
            if dry:
                # STOPPING AT THE FIRST STEP IS THE WHOLE POINT. A dry run that granted the
                # first node and refused the second would have ACTED — half a program is not
                # a preview of one, it is a program.
                return _insession.Verdict(_insession.STOP, "dry run — nothing was done")
            return _insession.Verdict(step.kind)

        # STAGED LOWERING'S TWO SEAMS, so a PROMOTION CAN ACTUALLY BUY SOMETHING. Without
        # them the engine asks for the tree regime, is granted it, and reaches for a
        # decomposer that is not there — a recorded-but-inert escalation, which is the exact
        # shape this project has found in three separate places.
        #
        # THEY LIVE IN THE BENCH FOR THE SAME REASON THE EXTRACTOR DOES, and it is a
        # measurement rather than an accident: the model-driven tree scores 4/13 where the
        # deterministic writer scores 13/13. Moving them into production would say they had
        # arrived. They are the FALLBACK for a goal the writer refuses, reached only after
        # `Unsolvable` and only inside a granted tree session, so their cost is paid by
        # whoever holds the budget.
        def _staged_seams():
            try:
                from tests.bench.ladder import BENCH_MODEL
                from tests.bench.sim_world import SimWorld
                from tests.bench.tree_probe import make_emit, make_route
            except Exception:
                return None, None
            stats = {"route_calls": 0, "emit_calls": 0, "route_channel": 0,
                     "emit_channel": 0}
            # THE PROMPTS THOSE BUILDERS WRITE DESCRIBE A WORLD, and the one they describe
            # here is a MODEL of the lab rather than the lab — the same scratch the writer
            # plans against. A decomposer that could reach the real executor would be a
            # second door.
            model_world = SimWorld()
            return (make_emit(BENCH_MODEL, model_world, None, stats),
                    make_route(BENCH_MODEL, model_world, stats))

        author, route = _staged_seams()
        registry = Registry()
        # BOTH LOAD-BEARING ENGINES, floor first. The executor provides the box — one call,
        # one answer — and Medusa turns a prompt into a program when one call is not enough.
        # Mounting only the planner meant every request, however small, went to the thing
        # that writes programs; the rerouting handles the handover with nobody watching.
        registry.mount(ExecutorEngine(LIBRARY, guarded))
        registry.mount(QemuEngine(LIBRARY, guarded, author=author, route=route))
        # TRY THE FLOOR FIRST. `route` is the one decision a model makes here and there is
        # no model in this path yet, so the rule is the ladder's own: gravity points down,
        # and an engine that cannot serve a request says so cheaply.
        floor_first = lambda req, menu, engines: next(
            (e.name for e in engines if e.name == "executor"),
            engines[0].name if engines else None)
        # THE ANSWER IN ENGLISH, with every claim checked against the findings. Skipped for
        # a dry run: there is nothing to describe, and asking a model to narrate a preview
        # would invite it to describe work that did not happen.
        from orchestrator.ai.engines import reporter as _reporter
        result = Orchestrator(registry, Channel([translate]), decide=decide,
                              route=floor_first,
                              narrate=None if dry else _reporter.narrator()).handle(request)

        if offered:
            console.print("\n[bold]what it would do[/bold]" if dry
                          else "\n[bold]what it did[/bold]")
            for st in offered:
                mark = f"  · {st.why or 'node'}: {st.cost} call(s)"
                if st.destroys:
                    # NAMED, NOT COUNTED. "7 deletions" and "deletes vm-orchestrator" are
                    # different sentences, and only one of them stops a person.
                    gone = ", ".join(sorted(str(list(a.values())[0]) if a else "?"
                                            for _, a in st.destroys))
                    mark += f"  [warn]DESTROYS {len(st.destroys)}: {gone}[/warn]"
                console.print(mark)

        outcome = result.get("outcome")
        colour = {"DONE": "ok", "REFUSED": "warn"}.get(outcome, "warn")
        console.print(f"[{colour}]{outcome}[/{colour}]  {result.get('why') or ''}")

        # THE LEDGER, NOT A SUMMARY. This path exists to be READ — it is where a wrong
        # answer gets traced to the stage that caused it — and a list of sentences cannot
        # say who asked whom. Every line names both ends, the program goes at the end whole,
        # and `-v` attaches the evidence each line carries.
        ledger = result.get("events")
        if ledger is not None:
            for line in ledger.render(show_data=verbose).splitlines():
                console.print(f"  [dim]{line}[/dim]" if line.startswith("2") else f"  {line}")
        else:
            for line in result.get("log", []):
                console.print(f"  [dim]{line}[/dim]")
        if result.get("rendered") and result.get("events") is None:
            # ONLY WHEN THERE IS NO LEDGER. The ledger already prints the program in full at
            # the end; printing it twice would teach the reader to skip one of them.
            console.print("\n[bold]the program it wrote[/bold]")
            for line in result["rendered"].splitlines():
                console.print(f"  {line}")
        tree = result.get("tree")
        if tree and tree.get("verdict") != "clear":
            # ONLY WHEN IT IS NOT CLEAR. A book keeper that printed a clean tree on every
            # request would train the reader to skip the line it exists to be read on.
            console.print(f"\n[warn]the tree was served against a moving world[/warn]  "
                          f"{tree['infected']} of {tree['nodes']} node(s)")
            for line in (result.get("tree_report") or "").splitlines()[1:]:
                console.print(f"  [dim]{line}[/dim]")
        if result.get("answer"):
            console.print(f"\n[bold]{result['answer']}[/bold]")
            if result.get("answer_grounded") is False:
                # RETURNED, BUT NEVER CLEAN. Suppressing it leaves silence where there was an
                # answer; returning it silently is the hallucination the reporter exists for.
                console.print(f"  [warn]unsupported by any finding: "
                              f"{result.get('answer_unsupported')}[/warn]")
        if result.get("grounded") is not None:
            console.print(f"\n  grounded: {result['grounded']} · "
                          f"{len(result.get('calls') or [])} call(s)")
        if outcome == "UNCLAIMED":
            console.print(f"  mounted: {result.get('mounted')} · "
                          f"callable capabilities: {result.get('capabilities')}")
