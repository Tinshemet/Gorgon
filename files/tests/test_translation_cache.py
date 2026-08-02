#!/usr/bin/env python3
"""
test_translation_cache.py — remember what a request MEANT, not what it produced.

#22 asked whether the method cache should cache PROGRAMS. Measured answer: no. The ghost
writer is deterministic and plans in microseconds, so a cached program saves nothing and
buys a staleness problem — a program is only correct for the world it was planned against.

The expensive step is the TRANSLATION, and its answer does not depend on the world: "create a
vm named alpha" means the same thing whether or not alpha exists. That asymmetry is what
makes caching safe here and unsafe one layer down, and most of this suite is about the edges
where a cache would otherwise be confidently wrong.

Run:  PYTHONPATH=. python3 -m tests.test_translation_cache
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines import TranslationCache
from engines.channel import Answer, Channel

_PASS = 0
_FAIL = 0


def check(label, cond):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


VM = {"vm": {"key": "name"}}
KITCHEN = {"dish": {"key": "dish_name"}}
GOALS = [{"shape": "count", "select": {"kind": "vm", "name": "alpha"}, "eq": 1}]


def test_a_repeat_request_is_free():
    print("[hit] the same meaning, twice")
    c = TranslationCache()
    check("a cold cache misses", c.get("create a vm named alpha", VM) is None)
    c.put("create a vm named alpha", VM, GOALS)
    check("and then hits", c.get("create a vm named alpha", VM) == GOALS)
    check("stats are honest", c.stats["hits"] == 1 and c.stats["misses"] == 1)


def test_only_meaning_preserving_differences_are_folded():
    """Shallow on purpose: every extra normalisation trades hit rate for the chance of
    collapsing two requests that differ in a way that matters."""
    print("[keys] case and spacing fold; words do not")
    c = TranslationCache()
    c.put("Create a VM named alpha.", VM, GOALS)
    check("case, spacing and a full stop fold",
          c.get("create  a vm named alpha", VM) == GOALS)
    check("but a different NAME does not",
          c.get("create a vm named beta", VM) is None)


def test_the_manifest_is_part_of_the_key():
    """The same words mean different components under a different manifest.

    `page` is a kind in one engine and nothing in another, so a cache shared across engines
    without the manifest in its key would answer confidently for the wrong world.
    """
    print("[keys] one request, two worlds")
    c = TranslationCache()
    c.put("make one", VM, GOALS)
    check("a different manifest misses", c.get("make one", KITCHEN) is None)
    check("the original still hits", c.get("make one", VM) == GOALS)


def test_a_failed_translation_is_never_remembered():
    """Caching an empty answer makes one bad result permanent.

    The next identical request would be refused instantly and the model never asked again —
    so failures must stay retryable, which matters most for the requests that are hardest to
    translate and therefore most likely to fail once.
    """
    print("[honesty] failures stay retryable")
    c = TranslationCache()
    c.put("something it could not read", VM, [])
    check("nothing was stored", c.stats["held"] == 0)
    check("and it still misses", c.get("something it could not read", VM) is None)


def test_a_caller_cannot_poison_the_cache_by_mutating_what_it_got():
    """A returned list that a caller edits would corrupt every later hit, with an edit
    nobody could trace back to here."""
    print("[safety] hits are copies")
    c = TranslationCache()
    c.put("x", VM, GOALS)
    got = c.get("x", VM)
    got[0]["eq"] = 99
    check("the cache is unchanged", c.get("x", VM)[0]["eq"] == 1)


def test_it_is_a_channel_participant_that_declines_cleanly():
    """#63: one protocol. A miss falls through exactly as if the cache were not there."""
    print("[channel] answers or declines")
    c = TranslationCache()
    model_calls = []

    def model(gap, world=None):
        model_calls.append(gap)
        return Answer(GOALS, "model", "")

    chan = Channel([c.answerer(VM), c.learn(VM)(model)])
    first = chan.ask("create a vm named alpha")
    check("a miss reaches the model", first.source == "model" and len(model_calls) == 1)
    second = chan.ask("create a vm named alpha")
    check("the repeat is served by the cache", second.source == "cache")
    check("and the model was not asked again", len(model_calls) == 1)
    check("with the same components", second.components == GOALS)


def test_reading_and_teaching_are_separate_rights():
    """An engine that may CONSULT the cache is not automatically one that may TEACH it."""
    print("[design] answerer and learn are different wrappers")
    c = TranslationCache()
    read_only = Channel([c.answerer(VM), lambda g, w=None: Answer(GOALS, "model", "")])
    read_only.ask("create a vm named alpha")
    check("consulting alone teaches nothing", c.stats["held"] == 0)


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "translation cache"))


if __name__ == "__main__":
    main()
