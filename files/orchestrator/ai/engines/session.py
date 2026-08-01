"""session.py — a request in flight, and the regime it is being served in.

THE THREE REGIMES ARE THE INTENT LADDER SEEN FROM THE SESSION'S SIDE:

    FETCH    tell me           TOOL         one call, one answer, close
    ENSURE   confirm it is so  TRANSLATION  components -> program -> run -> close
    ACHIEVE  make it so        TREE         autonomous, corrects, cost accrues

GRAVITY POINTS DOWN. Most requests should end at the floor, and a session promotes only on a
SIGNAL — never because a request looks complicated. Rung 4 looks like it needs autonomy and
does not: 21 calls, computed, no model. And the evidence for the ordering is blunt — the tree
scores 30/78 when a model drives it, the ghost writer 13/13 when code does.

THE TWO SIGNALS ALREADY EXISTED BEFORE THIS FILE:
    `Unsolvable`        the writer: no tile, no rule, will not improvise
    `derive() -> None`  the gap is not arithmetic
Both were built as honest refusals. Under the engine architecture a refusal from an engine IS
a promotion request, and this is the component that hears it.

THE ENGINE ASKS; THE ORCHESTRATOR DECIDES. A tree session runs until resolved or abandoned
with cost accruing, so whoever owns the budget must be able to refuse. A declined promotion
is a real outcome and reaches the operator as one: *this needs more than I am allowed to
spend.*
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Ordered, lowest first. The index IS the rank, so "outranks" is a comparison rather than a
# table someone has to keep in step with the intent ladder.
REGIMES = ("tool", "translation", "tree")

# Which regime an intent starts in. The correspondence is the whole design and is written
# once, here, rather than re-decided per call site.
INTENT_REGIME = {"fetch": "tool", "ensure": "translation", "achieve": "translation"}


def rank(regime: str) -> int:
    return REGIMES.index(regime) if regime in REGIMES else 0


class Session:
    """One request, one engine, one regime — plus what it has spent and been told.

    NOT A CONVERSATION. A session is bounded work with a cost and a verdict; the back-and-
    forth of a tree lives INSIDE one, as nodes. Keeping that distinction means "close" is a
    decision about work rather than about a chat window.
    """

    def __init__(self, request: str, engine, intent: str = "fetch",
                 budget: Optional[int] = None):
        self.request = request
        self.engine = engine
        self.intent = intent
        self.regime = INTENT_REGIME.get(intent, "tool")
        self.budget = budget
        self.calls: List = []
        self.findings: List[Dict[str, Any]] = []
        self.log: List[str] = []
        self.closed = False
        self.outcome: Optional[str] = None
        self.promotions = 0

    # ── the ledger of this session ────────────────────────────────────────────────────
    def record(self, note: str) -> None:
        self.log.append(note)

    def spent(self) -> int:
        return len(self.calls)

    def afford(self, more: int = 1) -> bool:
        return self.budget is None or self.spent() + more <= self.budget

    # ── promotion ─────────────────────────────────────────────────────────────────────
    def may_promote(self, to: str) -> bool:
        """Is promotion legal AND affordable? Two separate questions, both required.

        Legality is the ladder: a session may only go UP, and only into a regime the engine
        actually serves. Affordability is the budget, and it is why the orchestrator holds
        this rather than the engine — an engine asked to do more will always say yes.
        """
        if to not in REGIMES or rank(to) <= rank(self.regime):
            return False
        if to == "tree" and "achieve" not in getattr(self.engine, "intents", ()):
            return False
        return self.afford(1)

    def promote(self, to: str, why: str = "") -> bool:
        if not self.may_promote(to):
            self.record(f"promotion to {to} DECLINED ({why or 'not permitted'})")
            return False
        self.record(f"promoted {self.regime} -> {to} ({why})")
        self.regime = to
        self.promotions += 1
        return True

    def rounds_left(self, cap: int = 3) -> int:
        """How many more in-session rounds this session may take.

        A tree runs until resolved or ABANDONED, and abandonment needs a number. Three is
        chosen for one reason: the ghost writer's own fixpoint gives up after four passes
        that will not settle, and a session that out-loops its writer is chasing a gap the
        writer has already said it cannot close.
        """
        return max(0, cap - self.promotions)

    def close(self, outcome: str, why: str = "") -> Dict[str, Any]:
        self.closed = True
        self.outcome = outcome
        self.record(f"closed {outcome} ({why})" if why else f"closed {outcome}")
        return {"outcome": outcome, "why": why, "regime": self.regime,
                "engine": getattr(self.engine, "name", "?"), "calls": self.calls,
                "findings": self.findings, "log": self.log}
