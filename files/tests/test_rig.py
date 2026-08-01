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


def test_a_loaded_package_is_askable_not_just_runnable():
    """"A CAPABILITY THAT CANNOT BE REQUESTED IS NOT MOUNTED."

    Loading a package joins its KINDS to the engine's manifest. That is only half: the
    extractor builds its schema and its prompt from the manifest IN FORCE, so a translation
    asked outside the routed engine's scope offers the model the DEFAULT kinds — and the
    package's stay invisible. The writer could plan a search, the engine could run one, and
    the model could not say the word.
    """
    print("[rig] the package's kinds reach the front seam")
    orch = rig.build(_refuses, library=FakeLibrary(), narrate=False)
    lab = next(e for e in orch.registry.engines if e.name == "qemu")
    check("the package is loaded", [p.name for p in lab.packages] == ["camoufox"])
    check("its kinds joined the engine's manifest",
          {"search", "browser"} <= set(lab.manifest))

    # THE TRANSLATION HAPPENS UNDER THAT MANIFEST, asserted by watching what the schema
    # offers at the moment the channel is asked.
    from orchestrator.ai.engines.channel import Answer
    from tests.bench import extract as _extract
    seen = {}

    def spy(request, world=None):
        seen["kinds"] = set(_extract.schema()["properties"]["goals"]["items"]
                            ["properties"]["select"]["properties"]["kind"]["enum"])
        return Answer(None, "spy", "not translating, just looking")
    spy.name = "spy"

    from orchestrator.ai.engines.channel import Channel
    orch.channel = Channel([spy])
    orch.handle("search the web for something", intent="ensure")
    check(f"the model is offered the package's kinds too ({sorted(seen.get('kinds', ()))})",
          {"search", "browser"} <= seen.get("kinds", set()))
    check("and the default kinds are back afterwards, outside the scope",
          "search" not in set(_extract.schema()["properties"]["goals"]["items"]
                              ["properties"]["select"]["properties"]["kind"]["enum"]))


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the production rig"))


if __name__ == "__main__":
    main()


def test_unbuilt_library_is_unknown_not_empty():
    """An unbuilt registry must never plan as an empty lab.

    The `plan` shortcut hit this live: `ActiveLibrary` starts `built = False` with empty
    tables, the REPL happens to call `snapshot()` at startup and nothing else does, so a
    nine-machine lab planned as though it held nothing and closed UNMET on vacuous ENSUREs.
    """
    from orchestrator.ai.engines.qemu import LabWorld

    class Lib:
        def __init__(self):
            self.built, self.rows = False, {}

        def snapshot(self):
            self.built = True
            self.rows = {"alpha": {"name": "alpha", "state": "running"}}
            return self

        def vms(self):
            return self.rows

        def by_network(self):
            return {}

        def known_names(self):
            return set(self.rows)

    lib = Lib()
    world = LabWorld(lib, lambda t, a: None)
    assert world.scratch().state.get("vm", {}), "planned against an unbuilt library as if empty"
    assert lib.built

    class Broken(Lib):
        def snapshot(self):
            return self          # stays unbuilt — a lab that will not answer

    try:
        LabWorld(Broken(), lambda t, a: None).scratch()
    except RuntimeError:
        pass
    else:
        raise AssertionError("an unreachable library read as an empty lab")


def test_package_tools_are_callable_through_the_engines_own_door():
    """Loading a package must make its tools RUN, not merely nameable.

    Measured on the lab: the writer planned the whole chain — create the machine, launch it
    headless, start the browser on it, search — and the world answered `Unknown tool:
    camoufox_launch`. A real machine was created and launched to host a browser that could
    never start.
    """
    from orchestrator.ai.engines import rig
    from orchestrator.ai.engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY

    seen = []
    eng = QemuEngine(LIBRARY, lambda t, a: seen.append((t, a)) or {"success": True},
                     packages=rig.packages())
    eng._execute("camoufox_launch", {"browser_name": "b1", "vm": "vm1"})
    eng._execute("camoufox_search", {"browser": "b1", "query": "the diameter of the earth"})
    eng._execute("create_vm", {"name": "x"})

    tools = [t for t, _ in seen]
    assert tools[:2] == ["run_guest_command", "run_guest_command"], tools
    # THE BROWSER'S MACHINE IS REMEMBERED FROM ITS LAUNCH — a search names no machine.
    assert seen[1][1]["name"] == "vm1", seen[1]
    # AND THE OPERATOR'S WORDS ARE QUOTED, never spliced into a shell line.
    assert "'the diameter of the earth'" in seen[1][1]["command"], seen[1]
    # A tool nobody claims goes to the engine's own executor untouched.
    assert seen[2][0] == "create_vm"


def test_a_packages_kinds_reach_the_planner_not_only_the_schema():
    """`use_kinds` is a dynamic scope; a manifest captured before it is a different world.

    The lab world assigned `self.kinds = config.KINDS` in `__init__`, so a loaded package's
    kinds reached the schema and the prompt and never the writer: the model could name a
    search and the planner had never heard of one.
    """
    from orchestrator.ai.engines import rig
    from orchestrator.ai.engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY
    from orchestrator.ai.planner.ir import config

    eng = QemuEngine(LIBRARY, lambda t, a: None, packages=rig.packages())
    assert eng._foreign, "an engine with packages has a manifest of its own"
    with config.use_kinds(eng.manifest):
        assert "search" in eng.world().kinds
        # A PACKAGE IS THE AUTHORITY FOR ITS OWN KINDS — it knows it holds none, where the
        # library merely has no idea. Only the latter is unenumerable.
        assert "search" not in eng.world().unseeded
        assert "snapshot" in eng.world().unseeded


def test_the_worked_example_is_blinded_to_the_request():
    """Rendering every loaded kind's example cost five rungs at n=3 to buy one search."""
    from orchestrator.ai.engines import rig
    from orchestrator.ai.engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY
    from orchestrator.ai.planner.ir import config
    from tests.bench import extract as EX

    eng = QemuEngine(LIBRARY, lambda t, a: None, packages=rig.packages())
    with config.use_kinds(eng.manifest):
        assert "SAME SHAPES" in EX.prompt(request="search the web for the boiling point")
        for text in ("create 3 vms labelled prod",
                     "clone golden into 3 new vms and launch all of them",
                     "make sure they can all ping each other"):
            assert "SAME SHAPES" not in EX.prompt(request=text), text
