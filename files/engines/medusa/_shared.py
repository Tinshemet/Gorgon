"""_shared.py — what more than one part of the engine needs.

PLACEMENT FOLLOWS DEPS, which is the standing bar. `_findings_of` is read by the in-session
and by the executing half; the two caps are read by the in-session alone but belong with the
constant they are twinned with. Leaving them in `engine.py` would have made every mixin
import the class module they are mixed INTO — a cycle, and a false statement about who
depends on whom.
"""
from __future__ import annotations

from typing import Any, Dict, List

def _prose_of(components) -> str:
    """The sentence a set of components came from, if one travelled with them.

    STAGED LOWERING OPENS PROSE; the writer covers structure. A component that carries no
    `_goal` has no sentence to open, and manufacturing one from the structure would be
    writing the request rather than serving it — the decomposer that split prose to BUILD is
    the mistake #55 already recorded.
    """
    for c in components or ():
        text = (c or {}).get("_goal")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _findings_of(world, result) -> List[Dict[str, Any]]:
    """What the run OBSERVED — the ledger, never the call list.

    A finding is something the world told us; a call is something we asked it. Conflating
    them would let a reporter say "beta was unreachable" because a probe was ISSUED, which is
    exactly the inference decision 6 forbids and the reason `reach` demands an answer rather
    than a success flag.
    """
    ledger = getattr(world, "findings", None)
    # THREE LEDGER SHAPES AND THE PRODUCTION ONE WAS MISSING. `Findings` is neither a dict
    # nor a list — it is the object the real runtime records into — so an engine over the VM
    # sim fell straight through to listing its own CALLS, and reported "I asked alpha" where
    # it had been told "alpha answered". Exactly the conflation `_findings_of` was written to
    # prevent, in the one world that matters most.
    if hasattr(ledger, "facts") and callable(ledger.facts):
        got = [{"fact": f, "value": ledger.get(f)} for f in sorted(ledger.facts())]
        if got:
            return got
    if isinstance(ledger, dict) and ledger:
        return [{"fact": k, "value": v} for k, v in sorted(ledger.items())]
    if isinstance(ledger, list) and ledger:
        return list(ledger)
    # NO OBSERVATIONS IS NOT NO ANSWER. A program that only acted has findings of a
    # different kind — what it changed — and saying so is better than silence.
    return ([{"did": tool, **(args or {})} for tool, args in (result.get("calls") or [])]
            if result.get("ok") else [])


# HOW MANY TIMES ONE IN-SESSION MAY BE TOLD TO OPEN A NODE INSTEAD OF RUNNING IT. Twelve
# matches the writer's own lowering depth, for one reason: a session that out-opens its writer
# is refining a goal the writer already knows how to reach.
_MAX_OPENINGS = 12

# HOW MANY TIMES ONE NODE MAY BE TOLD TO WAIT. The same twelve, for the same reason: a node
# re-offered a thirteenth time is not waiting for something, it is being refused by a
# decider that will not say so.
_MAX_WAITS = 12
