"""Re-export — the manifest-driven world model is PRODUCTION now, at `planner/model_world.py`.

It lived here while it was a CLAIM: that the writer was domain-free, provable by running a
kitchen manifest through it. The claim held, and then the QEMU mount started using it as its
PLANNING SCRATCH — at which point a production code path was importing a test fixture on
every request.

The ghost writer made this same move on 2026-08-01 for the same reason, recorded there in the
same words: nothing in `tests/` may quietly become the authority for a production component.
This shim exists so the bench's own suites keep importing one name.
"""
from orchestrator.ai.planner.model_world import (  # noqa: F401
    Ledger, World, seams, _single,
)
