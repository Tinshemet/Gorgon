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

    def __init__(self, components: Optional[List[Dict[str, Any]]], source: str, why: str = "",
                 procedure: Optional[str] = None):
        self.components = components or []
        self.source = source
        # AN AUTHORING REQUEST NAMES WHAT TO KEEP. `None` is an ordinary request: do it now.
        self.procedure = procedure
        self.why = why

    def __bool__(self) -> bool:
        return bool(self.components)

    def __repr__(self) -> str:
        return f"<Answer {self.source} n={len(self.components)} {self.why[:40]}>"


def constrained(prompt: str, payload: Any, schema: Dict[str, Any],
                model: str = None, temp: float = 0.0, timeout: int = 300) -> Dict[str, Any]:
    """ONE CONSTRAINED MODEL CALL. Every AI seam in the system goes through here.

    THE DUPLICATION THIS ENDS was real and I had just added to it. `extract` built its own
    call, `reporter.narrator` built a second, `author_probe` a third, and the staged-lowering
    author would have been a fourth — four places deciding what a model call IS. Two of them
    already differed on `keep_alive` and on how a decode failure surfaces, which is #26's
    defect (two prompt paths that had silently diverged) reappearing one layer down.

    `format=schema` IS THE GRAMMAR AND IT IS NOT OPTIONAL HERE. The whole of 2026-07-31 was a
    grammar accepted and ignored — one bad `pattern` silently disabling constrained decoding
    across the entire authoring path — and a caller that forgot to pass a schema would be
    free generation wearing a schema's name. Passing it is the only way to call this.

    A DECODE FAILURE RAISES rather than returning `{}`. An empty answer and a broken one are
    different events, and a seam that cannot tell them apart reports "the model had nothing
    to say" for what was actually a malformed response.
    """
    import json as _json
    import urllib.request

    from orchestrator.ai.chat.ollama_client import OLLAMA_URL
    from tests.bench import pinned

    body = {"model": model or _bench_model(), "stream": False, "format": schema,
            "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(temp),
            "messages": [{"role": "system", "content": prompt},
                         {"role": "user", "content": payload if isinstance(payload, str)
                          else _json.dumps(payload, default=str)}]}
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", method="POST",
                                 data=_json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        reply = _json.loads(fh.read())
    return _json.loads((reply.get("message") or {}).get("content") or "{}")


def _bench_model() -> str:
    """One model name, not several. The bench's, unless a caller names another."""
    try:
        from tests.bench.ladder import BENCH_MODEL
        return BENCH_MODEL
    except Exception:
        return "llama3.1:8b"


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
