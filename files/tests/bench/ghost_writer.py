"""Re-export — the ghost writer is PRODUCTION now, at `planner/ghost_writer.py`.

It lived here while it was a claim. It is measured (13/13 rungs, 1932/2000 fuzz, two
domains) so it belongs beside the runtime it plans for. This shim exists so the bench's
own suites keep importing one name, and so nothing in `tests/` quietly becomes the
authority for a production component.
"""
from planner.ghost_writer import (  # noqa: F401
    Call, Loop, Unsolvable, as_program, cover, _achieve, _fresh_names, _ground, _holds,
    _lower, _short, groundable,
)
