"""translation_cache.py — remember what a request MEANT, not what it produced.

#22 asked whether the method cache should cache PROGRAMS. Under the engine layer the answer
is no, and the reason is a measurement: the ghost writer is DETERMINISTIC — same request,
same world, same program, verified over four runs on all thirteen rungs — and it plans in
microseconds. Caching a program saves nothing and costs a staleness problem, because a
program is only correct for the world it was planned against.

THE EXPENSIVE STEP IS THE TRANSLATION. English into components is the one model call on the
path, it takes seconds, and its answer does NOT depend on the world: "create a vm named
alpha" means the same thing whether or not alpha already exists — what changes is the plan,
and the plan is free. So the cache belongs at the front seam, and what it stores is meaning.

THAT SPLIT IS ALSO WHY IT IS SAFE TO CACHE AT ALL. A program cached across a changed world is
wrong; a MEANING cached across a changed world is still the meaning. The writer re-plans it
against whatever is there now, and `already_satisfied` handles the rest.

IT IS A CHANNEL PARTICIPANT (#63), not a special case. `answerer()` returns something the
channel calls before the model — free, instant, and it declines rather than guessing, so a
miss falls through exactly as if it were not there.

KEYED BY REQUEST AND MANIFEST. The same words mean different components under a different
manifest — `page` is a kind in one engine and nothing in another — so a cache shared across
engines without the manifest in its key would answer confidently for the wrong world.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional


def _normalise(request: str) -> str:
    """Fold the differences that never change meaning: case, spacing, trailing stops.

    DELIBERATELY SHALLOW. It would be easy to strip more — articles, filler, plurals — and
    every step of that trades a higher hit rate for the chance of collapsing two requests
    that differ in a way that matters. A cache that answers the wrong question quickly is
    worse than one that misses.
    """
    return re.sub(r"\s+", " ", (request or "").strip().lower()).rstrip(".!?")


def _key(request: str, manifest: Optional[Dict[str, Any]]) -> str:
    kinds = sorted((manifest or {}).keys())
    stamp = hashlib.sha1(json.dumps(kinds).encode()).hexdigest()[:12]
    return f"{stamp}:{_normalise(request)}"


class TranslationCache:
    """Request -> components. Small, exact, and honest about a miss."""

    def __init__(self, limit: int = 512):
        self._rows: Dict[str, List[Dict[str, Any]]] = {}
        self._hits = 0
        self._misses = 0
        self._limit = limit

    def get(self, request: str, manifest=None) -> Optional[List[Dict[str, Any]]]:
        got = self._rows.get(_key(request, manifest))
        if got is None:
            self._misses += 1
            return None
        self._hits += 1
        # A COPY, always. A caller that mutated a cached list would poison every later hit
        # with an edit nobody could trace back to here.
        return json.loads(json.dumps(got))

    def put(self, request: str, manifest, components: List[Dict[str, Any]]) -> None:
        """Remember a translation. AN EMPTY ONE IS NEVER STORED.

        A request that translated to nothing is either noise or a failure, and caching that
        would make one bad answer permanent — the next identical request would be refused
        instantly without the model ever being asked again. Failures must stay retryable.
        """
        if not components:
            return
        if len(self._rows) >= self._limit:
            # Oldest out. A smarter policy would need usage tracking, and the honest reason
            # not to build one is that nothing has yet measured this cache filling up.
            self._rows.pop(next(iter(self._rows)))
        self._rows[_key(request, manifest)] = json.loads(json.dumps(components))

    @property
    def stats(self) -> Dict[str, int]:
        return {"hits": self._hits, "misses": self._misses, "held": len(self._rows)}

    def answerer(self, manifest=None):
        """A channel participant. Answers free, or declines and lets the model be asked."""
        from .channel import Answer

        def answer(gap, world=None):
            kinds = getattr(world, "kinds", None) if world is not None else manifest
            got = self.get(str(gap), kinds or manifest)
            return Answer(got, "cache", "seen before") if got else None
        answer.name = "cache"
        return answer

    def learn(self, manifest=None):
        """A wrapper that records what the next answerer returns.

        Separate from `answerer` on purpose: reading and writing a cache are different
        rights, and an engine that may consult it is not automatically one that may teach it.
        """
        def wrap(inner):
            def answer(gap, world=None):
                got = inner(gap, world)
                if got and getattr(got, "components", None):
                    kinds = getattr(world, "kinds", None) if world is not None else manifest
                    self.put(str(gap), kinds or manifest, got.components)
                return got
            answer.name = f"learn({getattr(inner, 'name', '?')})"
            return answer
        return wrap
