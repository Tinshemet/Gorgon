"""test_rig.py — every injectable seam has somebody behind it.

FOUR CAPABILITIES SHIPPED THIS SESSION WITH THEIR SEAM LEFT AT `None`: the reporter had no
narrator, staged lowering had no author or router, publications never reached the findings,
and the tree keeper recorded nothing. Every one looked finished — the code was there, the
tests were green, and the thing it hung on was empty.

THEY SHARE A SHAPE, AND IT IS WHY NO EXISTING TEST CAUGHT ANY OF THEM. An injectable seam
that defaults to `None` is INVISIBLE when nobody injects it: the feature does not fail, it
does not run, and nothing distinguishes "granted a tree session and decomposed it" from
"granted a tree session and found no decomposer". A test of the FEATURE passes, because the
feature works when you hand it its dependency — which every unit test does.

WHAT THIS CAN AND CANNOT PROVE. It cannot prove a seam works; only a measurement does that.
It proves nobody shipped a `None` and called it done, which is the failure that actually kept
happening.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.engines import rig

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class FakeLibrary:
    _vms = {}
    _networks = {}

    def vms(self):
        return {}

    def by_network(self):
        return {}

    def known_names(self):
        return set()


def _refuses(tool, args):
    raise AssertionError(f"the rig test may not act: {tool}({args})")


def test_both_load_bearing_engines_are_mounted():
    """The executor provides the box; Medusa turns a prompt into action. Mounting only the
    planner sent every request, however small, to the thing that writes programs."""
    print("[rig] the mount is what production actually builds")
    orch = rig.build(_refuses, library=FakeLibrary(), narrate=False)
    names = {e.name for e in orch.registry.engines}
    check(f"both engines are mounted ({sorted(names)})", names == {"executor", "qemu"})
    check("and the floor is tried first",
          rig.floor_first("x", None, list(orch.registry.engines)) == "executor")


def test_every_seam_has_a_provider():
    """THE ONE THAT WOULD HAVE CAUGHT ALL FOUR."""
    print("[rig] nothing is left at None")
    orch = rig.build(_refuses, library=FakeLibrary(), narrate=True)

    check("the channel has an answerer", bool(orch.channel._answerers))
    check("the reporter has a narrator", orch._narrate is not None)
    from orchestrator.ai.engines.orchestrator import Orchestrator
    check("the router is a real choice, not the first-claimant fallback",
          callable(orch._route) and orch._route is not Orchestrator._first_claimant)
    check("a verdict-giver exists", callable(orch._decide))
    check("and a publication policy exists", callable(orch._forward))

    lab = next(e for e in orch.registry.engines if e.name == "qemu")
    check("staged lowering has an author", lab._author is not None)
    check("and a router", lab._route is not None)


def test_the_translator_is_the_one_that_is_measured():
    """The front seam is the wall, and the rig must not quietly stub it."""
    print("[rig] the translator is the real extractor")
    translate = rig.translator()
    check("it names itself", getattr(translate, "name", None) == "extractor")


def test_building_the_rig_touches_nothing():
    """A mount that acted while being assembled would make every test that builds one a run
    against the operator's lab."""
    print("[rig] assembling is not acting")
    orch = rig.build(_refuses, library=FakeLibrary(), narrate=False)
    check("no engine acted during mount", orch is not None)
    world = next(e for e in orch.registry.engines if e.name == "qemu").world()
    check("and the world is readable without acting", world.names() == set())


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the production rig"))


if __name__ == "__main__":
    main()
