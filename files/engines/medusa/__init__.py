"""medusa — the engine for the SYSTEM ITSELF, in the pieces it is actually made of.

Medusa is bash for Gorgon. The executor is only for machines; this is the way to write code
for Gorgon inside Gorgon — meaningless outside it, and inside it the way things are done.

    engine     the mount contract: who this engine is, what it claims, what it knows
    _tree      the in-session — nodes, verdicts, the witness re-visit, the keeper's rows
    _staged    staged lowering, and what a node opens into
    _run       plan and correct, which is where the intent ladder decides what gets written
    _execute   running a plan that has already been granted

ONE NAME OUT, so nothing that imports this had to change: `MedusaEngine` is where it was.
"""
from .engine import MedusaEngine, _findings_of, _prose_of

__all__ = ["MedusaEngine"]
