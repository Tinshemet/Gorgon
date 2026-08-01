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
#
# ACHIEVE STARTS IN THE TREE, and it did not until now — this line said `translation` while
# the table eight lines above said TREE, and the comment on it claimed to be the one place
# the correspondence lived. A mapping that contradicts its own docstring is worse than
# either version alone, because both readers are entitled to believe it.
#
# THE FIX IS THE TABLE'S SIDE, because ACHIEVE MEANS "MAKE IT SO". An achieve session that
# started in translation got ONE program, ran it, and closed — so a goal the program did not
# reach came back UNMET rather than being corrected, which is precisely the difference
# between `ensure` and `achieve`. Correcting is the whole of what the third regime buys.
#
# GRAVITY STILL POINTS DOWN and this does not contradict it. Gravity is about which INTENT a
# request is granted — most should be `fetch` or `ensure` — not about overriding an intent
# once granted. A caller that asks for `achieve` has asked to pay for correction.
INTENT_REGIME = {"fetch": "tool", "ensure": "translation", "achieve": "tree"}


def rank(regime: str) -> int:
    return REGIMES.index(regime) if regime in REGIMES else 0


class Session:
    """One request, one engine, one regime — plus what it has spent and been told.

    THE IN-SESSION IS THE PART THE OPERATOR DOES NOT SEE. It is the back-and-forth between
    the orchestrator and an engine — the engine reports what it could and could not close,
    the orchestrator decides whether to grant more, and that repeats until the work is done
    or abandoned. A tree, in other words, and the operator sees only its result.

    THAT BOUNDARY IS WHY `log` AND `answer` ARE DIFFERENT FIELDS. The log is the internal
    record: routing, syncs, promotions, which answerer spoke. It exists so a wrong result can
    be traced to the stage that caused it, and showing it to an operator would be handing
    them the machinery instead of the outcome. `close()` returns both and marks which is
    which; anything user-facing reads `answer`.

    NOT A CONVERSATION either way. A session is bounded work with a cost and a verdict — so
    "close" is a decision about work, not about a chat window.
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
        # THE LEDGER IS THE LOG, not a second one beside it. `record()` files an event and
        # `log` renders those events as sentences, so the two cannot drift — an earlier
        # design would have had a structured ledger and a prose log recording different
        # things, which is how you end up trusting the one that happens to be wrong.
        from .eventlog import EventLog
        self.events = EventLog(request)
        # WHAT THE ENGINE SUBMITTED UPWARD, in order. Kept apart from `findings` until the
        # orchestrator has decided which of them the operator sees — a publication is a
        # thing an engine SAID, and a finding is a thing the operator is TOLD.
        self.published: List = []
        self.closed = False
        self.outcome: Optional[str] = None
        self.promotions = 0

    # ── the ledger of this session ────────────────────────────────────────────────────
    @property
    def log(self) -> List[str]:
        """The prose view, derived. Every existing caller keeps working."""
        return [e.note or e.executed for e in self.events.events]

    def record(self, note: str, filed_by: str = None, caught_by: str = None,
               executed: str = "", level: str = "info", data=None) -> None:
        """One interaction. `note` alone still works — the ends default to this session's
        two parties, which is what almost every existing call site meant anyway."""
        self.events.file(filed_by or getattr(self.engine, "name", "engine"),
                         caught_by or "orchestrator",
                         executed or note, note, level, data)

    def publish(self, pub) -> None:
        """An engine's claim, submitted. Recorded in the ledger too, so a publication that
        is later KEPT rather than forwarded still left a trace of having been made."""
        self.published.append(pub)
        self.record(f"claim: {pub.what} = {str(pub.value)[:40]}",
                    filed_by=getattr(self.engine, "name", "engine"),
                    caught_by="orchestrator", executed=f"PUBLISH {pub.what}",
                    data=pub.value)

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
        self.record(f"closed {outcome}" + (f" ({why})" if why else ""),
                    filed_by="orchestrator", caught_by="operator",
                    executed=f"close({outcome})",
                    level="error" if outcome not in ("DONE", "REFUSED") else "info")
        return {"outcome": outcome, "why": why, "regime": self.regime,
                "events": self.events,
                "engine": getattr(self.engine, "name", "?"), "calls": self.calls,
                "findings": self.findings,
                # INTERNAL. The back-and-forth that produced the result, kept under its own
                # key so nothing user-facing shows it by accident — a caller that renders
                # every field would otherwise narrate the machinery.
                "in_session": self.log,
                "log": self.log}
