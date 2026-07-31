"""channel.py — the one place a model is asked anything. `ask(gap, world) -> components`.

Three seams need a model and they are the same interface, so there is one thing to stub and
one thing to measure:

    front    English   -> components      the extractor
    middle   a gap     -> components      when derive() cannot compute it
    back     findings  -> English         the reporter

THE STUB ALREADY PASSES, which is the evidence this interface is right rather than merely
tidy. The 13/13 rungs and the kitchen both ran with every gap answered BY HAND — that is a
stubbed channel, and it means the coupling was never to AN AI, only to AN ANSWER.

SO THE MODEL IS ONE PARTICIPANT AMONG SEVERAL. `derive()` computes a gap when the gap is
arithmetic; the method cache answers free when it has seen one before; a model is asked last
because it costs most and is trusted least. `Answerer` is that ordering, made explicit rather
than hidden in an if-statement.

DELIBERATELY SYNCHRONOUS. A stream implies asynchrony and nothing here is async — the ghost
writer plans against a deep-copied virtual world, which is exactly what makes it reproducible
(same request, same world, same program). If a session could suspend mid-plan that world would
have to survive the wait, and two suspended plans over one world is a correctness problem
rather than plumbing. A synchronous `ask()` is a channel too, and it keeps the property that
makes the whole design debuggable.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional


class Answer:
    """What came back, and WHO answered — because the second part is the diagnosis.

    A wrong answer from `derive` is a bug in arithmetic; the same answer from a model is a
    misreading; from the cache it is a stale entry. Recording the source costs one field and
    turns "the plan was wrong" into a question with three separable answers.
    """

    def __init__(self, components: Optional[List[Dict[str, Any]]], source: str, why: str = ""):
        self.components = components or []
        self.source = source
        self.why = why

    def __bool__(self) -> bool:
        return bool(self.components)

    def __repr__(self) -> str:
        return f"<Answer {self.source} n={len(self.components)} {self.why[:40]}>"


class Channel:
    """Ordered answerers. The first that speaks wins; silence falls through to the next."""

    def __init__(self, answerers: Optional[List] = None):
        self._answerers: List = list(answerers or [])

    def add(self, answerer) -> "Channel":
        """`answerer(gap, world) -> Answer | None`. None means "not mine", not "no"."""
        self._answerers.append(answerer)
        return self

    def ask(self, gap: Dict[str, Any], world=None) -> Answer:
        for a in self._answerers:
            try:
                got = a(gap, world)
            except Exception as e:
                # AN ANSWERER THAT RAISES IS SKIPPED, NOT FATAL. A model timing out must not
                # take down a session that `derive` could still have served, and the reason
                # rides along so a silent fall-through is never mistaken for "nobody knew".
                got = Answer(None, getattr(a, "name", type(a).__name__),
                             f"raised {type(e).__name__}: {e}")
            if got:
                return got
        return Answer(None, "none", "no answerer could supply components")


def stub(table: Dict[str, List[Dict[str, Any]]]) -> Callable:
    """An answerer backed by written-down components. The first implementation of the channel.

    Not a toy: the hand-written goals in `test_ghost_writer` pass 13/13 through the same
    writer production uses, so this stub validates the interface BEFORE a model is attached
    to it. Every later answerer is measured against a baseline that already works, and a
    regression can only be the answerer.
    """
    def answer(gap, world=None):
        key = gap if isinstance(gap, str) else str(gap)
        got = table.get(key)
        return Answer(got, "stub", "written down") if got else None
    answer.name = "stub"
    return answer
