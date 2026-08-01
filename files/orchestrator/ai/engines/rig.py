"""rig.py — THE PRODUCTION MOUNT, in one place a test can build.

WHY THIS FILE EXISTS. Four times in one session a capability was BUILT AND NOT WIRED: the
reporter had no narrator, staged lowering had no author or router, publications never reached
the findings, and the tree keeper recorded nothing. Every one of them looked finished — the
code was there, the tests were green, and the seam it hung on was `None`.

They share a shape. An injectable seam that defaults to `None` is INVISIBLE when nobody
injects it: the feature does not fail, it does not run, and nothing distinguishes "granted a
tree session and decomposed it" from "granted a tree session and found no decomposer".

SO THE MOUNT IS ASSEMBLED HERE AND ASSERTED THERE. `tests/test_rig.py` builds exactly what
the chat shortcut builds and checks that every seam has somebody behind it. That cannot prove
a seam WORKS — only a measurement does that — but it does prove nobody shipped a `None` and
called it done, which is the failure that actually kept happening.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple


def staged_seams(model: str = None) -> Tuple[Optional[Callable], Optional[Callable]]:
    """`(author, route)` for staged lowering, or `(None, None)` if the bench is absent.

    THEY LIVE IN THE BENCH DELIBERATELY, and it is a measurement rather than an accident: the
    model-driven tree scores 4/13 where the deterministic writer scores 13/13. Moving them
    into production would say they had arrived. They are the FALLBACK for a goal the writer
    REFUSES — reached only after `Unsolvable`, only inside a granted tree session — so their
    cost is paid by whoever holds the budget rather than by every request.
    """
    try:
        from tests.bench.ladder import BENCH_MODEL
        from tests.bench.sim_world import SimWorld
        from tests.bench.tree_probe import make_emit, make_route
    except Exception:
        return None, None
    stats: Dict[str, int] = {"route_calls": 0, "emit_calls": 0,
                             "route_channel": 0, "emit_channel": 0}
    # THE WORLD THOSE BUILDERS DESCRIBE IS A MODEL OF THE LAB, never the lab. A decomposer
    # that could reach the real executor would be a second door.
    scratch = SimWorld()
    name = model or BENCH_MODEL
    return make_emit(name, scratch, None, stats), make_route(name, scratch, stats)


def translator() -> Callable:
    """English -> goals. The front seam, and the one still measured at the wall."""
    from tests.bench import extract as _extract

    from .channel import Answer

    def translate(gap, world=None):
        try:
            raw = _extract.extract(str(gap))
        except Exception as exc:
            return Answer(None, "extractor", f"{type(exc).__name__}: {exc}")
        goals = _extract.to_goals(raw, str(gap))
        return (Answer(goals, "extractor", "") if goals
                else Answer(None, "extractor", "no usable goal"))
    translate.name = "extractor"
    return translate


def floor_first(request, menu, engines):
    """Route to the executor when it is mounted. GRAVITY POINTS DOWN.

    The router is the one decision a model makes in this path and there is no model in it
    yet, so the rule is the ladder's own: try the cheapest regime, and let an engine that
    cannot serve a request say so cheaply.
    """
    return next((e.name for e in engines if e.name == "executor"),
                engines[0].name if engines else None)


def build(execute: Callable, library=None, narrate: bool = True,
          decide: Optional[Callable] = None) -> Any:
    """The whole production mount: two engines, a channel, a reporter, a router.

    `execute` is the caller's GUARDED executor — the same door a single tool call goes
    through. Building one here would be a second door, which is the thing the engine layer
    exists to prevent.
    """
    from orchestrator.ai.active_library import LIBRARY

    from . import reporter as _reporter
    from .channel import Channel
    from .executor import ExecutorEngine
    from .orchestrator import Orchestrator
    from .qemu import QemuEngine
    from .registry import Registry

    lib = LIBRARY if library is None else library
    author, route = staged_seams()

    registry = Registry()
    # BOTH LOAD-BEARING ENGINES. The executor provides the box — one call, one answer — and
    # Medusa turns a prompt into a program when one call is not enough. Mounting only the
    # planner sent every request, however small, to the thing that writes programs.
    registry.mount(ExecutorEngine(lib, execute))
    registry.mount(QemuEngine(lib, execute, author=author, route=route))

    return Orchestrator(registry, Channel([translator()]), decide=decide,
                        route=floor_first,
                        narrate=_reporter.narrator() if narrate else None)
