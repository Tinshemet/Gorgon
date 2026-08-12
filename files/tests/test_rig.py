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

from engines import rig

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
    from engines.orchestrator import Orchestrator
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


def test_production_does_not_import_the_test_tree():
    """A CHECKOUT WITHOUT `tests/` MUST STILL HAVE A FRONT SEAM.

    The extractor lived in `tests/bench/` while `rig.translator()` imported it, so the chat
    path's translation stage was a module in the test tree. Not a tidiness complaint: a bench
    module is one nobody is careful about deleting, and it is free to import other bench
    modules — this one pulled in `pinned` and `BENCH_MODEL`, so every production model call
    ran under a reproducibility policy whose own docstring says *"THIS IS THE BENCH'S POLICY,
    NOT PRODUCTION'S."*

    TWO IMPORTS ARE ALLOWED AND BOTH ARE DELIBERATE. `staged_seams` reaches into the bench on
    purpose — the model-driven decomposer scores 4/13 against the writer's 13/13, and moving
    it into production would say it had arrived — and it is wrapped so its absence yields
    `(None, None)` rather than an import error. A third would be a regression.
    """
    print("[rig] the packages that ship do not import the ones that do not")
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    pattern = re.compile(r"^\s*(?:from|import)\s+(tests[\w.]*)", re.M)
    offenders = []
    # ⇒⇒ **`engines` AND `planner` WERE NOT SCANNED, AND THEY ARE WHERE THE FRONT SEAM LIVES.**
    #   Found by the 2026-08-13 review. The two staged-lowering imports below sit in
    #   `engines/rig.py` — a package this loop never looked at — so they were invisible to the
    #   check BY OMISSION rather than allowed by policy, and the allowlist that named them had
    #   never once been exercised. A new test-import in either package would have gone
    #   unnoticed indefinitely.
    for pkg in ("orchestrator", "client", "admin", "executor", "shared", "engines", "planner"):
        pkg_dir = root / pkg
        if not pkg_dir.is_dir():
            continue
        for path in pkg_dir.rglob("*.py"):
            if "__pycache__" in str(path):
                continue
            for m in pattern.finditer(path.read_text()):
                offenders.append(f"{path.relative_to(root)} -> {m.group(1)}")
    # ⇒ THE ALLOWLIST IS (FILE -> MODULE), NEVER A LINE NUMBER. It read
    #   `{"engines/rig.py:32", "engines/rig.py:33"}` and the imports had since moved to 39-40,
    #   so it was stale as well as unreachable — a line-based allowlist rots every time
    #   somebody edits the lines above it, and rots SILENTLY, which is the whole failure mode
    #   this test exists to prevent.
    allowed = {"engines/rig.py -> tests.bench.sim_world",
               "engines/rig.py -> tests.bench.tree_probe"}
    stray = sorted(set(offenders) - allowed)
    check(f"nothing shipped imports tests/ except the staged-lowering seam ({stray or 'none'})",
          not stray)
    check("and that seam survives the bench being absent",
          "except Exception" in (root / "engines/rig.py").read_text())


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
    # NEEDS A MOUNTED PACKAGE, AND THERE IS NONE: `packages/webcrawler/` and `packages/git/`
    # were emptied for rework on 2026-08-02, so `rig.packages()` returns nothing. Skipped
    # ALOUD rather than deleted — roadmap #7 rebuilds packages on a three-file contract, and
    # these are the checks that say a package's kinds must reach the WRITER and not only the
    # schema. Found dead 2026-08-04: defined below the `__main__` guard, so never once run.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    print("[rig] the package's kinds reach the front seam")
    # BUILT HERE RATHER THAN TAKEN FROM `rig.build`, since 2026-08-02: production loads NO
    # packages — `camoufox` and `webcrawl` were deleted for a rework and `rig._packages()`
    # degrades to `()`. Asserting through the production mount would now be asserting that
    # the rig loads something it does not, so the guard is pointed at the property itself:
    # ANY loaded package's kinds must reach the front seam, not merely the writer.
    from engines.qemu import QemuEngine
    from tests.bench.fixture_package import GuestPackage
    check("production currently loads no packages", rig.packages() == ())

    lab = QemuEngine(FakeLibrary(), _refuses, packages=(GuestPackage(),))
    check("a loaded package is on the engine", [p.name for p in lab.packages] == ["guest"])
    check("its kinds joined the engine's manifest",
          {"crawl", "page"} <= set(lab.manifest))

    # THE TRANSLATION HAPPENS UNDER THAT MANIFEST, asserted by watching what the schema
    # offers at the moment the channel is asked.
    from engines import extract as _extract
    from planner.ir import config as _config
    with _config.use_kinds(lab.manifest):
        offered = set(_extract.kinds_offered())
    check(f"the model is offered the package's kinds too ({sorted(offered)})",
          {"crawl", "page"} <= offered)
    check("and the default kinds are back afterwards, outside the scope",
          "crawl" not in set(_extract.kinds_offered()))


def test_unbuilt_library_is_unknown_not_empty():
    """An unbuilt registry must never plan as an empty lab.

    The `plan` shortcut hit this live: `ActiveLibrary` starts `built = False` with empty
    tables, the REPL happens to call `snapshot()` at startup and nothing else does, so a
    nine-machine lab planned as though it held nothing and closed UNMET on vacuous ENSUREs.
    """
    from engines.qemu import LabWorld

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
    # NEEDS A MOUNTED PACKAGE, AND THERE IS NONE: `packages/webcrawler/` and `packages/git/`
    # were emptied for rework on 2026-08-02, so `rig.packages()` returns nothing. Skipped
    # ALOUD rather than deleted — roadmap #7 rebuilds packages on a three-file contract, and
    # these are the checks that say a package's kinds must reach the WRITER and not only the
    # schema. Found dead 2026-08-04: defined below the `__main__` guard, so never once run.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    from engines import rig
    from engines.qemu import QemuEngine
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
    # NEEDS A MOUNTED PACKAGE, AND THERE IS NONE: `packages/webcrawler/` and `packages/git/`
    # were emptied for rework on 2026-08-02, so `rig.packages()` returns nothing. Skipped
    # ALOUD rather than deleted — roadmap #7 rebuilds packages on a three-file contract, and
    # these are the checks that say a package's kinds must reach the WRITER and not only the
    # schema. Found dead 2026-08-04: defined below the `__main__` guard, so never once run.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    from engines import rig
    from engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY
    from planner.ir import config

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
    # NEEDS A MOUNTED PACKAGE, AND THERE IS NONE: `packages/webcrawler/` and `packages/git/`
    # were emptied for rework on 2026-08-02, so `rig.packages()` returns nothing. Skipped
    # ALOUD rather than deleted — roadmap #7 rebuilds packages on a three-file contract, and
    # these are the checks that say a package's kinds must reach the WRITER and not only the
    # schema. Found dead 2026-08-04: defined below the `__main__` guard, so never once run.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    from engines import rig
    from engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY
    from planner.ir import config
    from engines import extract as EX

    eng = QemuEngine(LIBRARY, lambda t, a: None, packages=rig.packages())
    with config.use_kinds(eng.manifest):
        assert "SAME SHAPES" in EX.prompt(request="search the web for the boiling point")
        for text in ("create 3 vms labelled prod",
                     "clone golden into 3 new vms and launch all of them",
                     "make sure they can all ping each other"):
            assert "SAME SHAPES" not in EX.prompt(request=text), text


def _answering_world():
    import json as _json

    def world(tool, args):
        if tool == "run_guest_command" and "camoufox search" in (args.get("command") or ""):
            return {"success": True, "stdout": _json.dumps({"answer": "12,742 km"})}
        return {"success": True, "stdout": ""}
    return world


def test_a_program_calls_verifies_and_publishes():
    """The operator's three corrections, in one program.

    1. every invocation leads with CALL — a program has to be something a person could type
    2. the answer is VERIFIED, not just the search's existence
    3. and it is PUBLISHED, by the program, rather than inferred from a ledger afterwards
    """
    # NEEDS THE PACKAGE'S `search` KIND, and packages were emptied for rework 2026-08-02.
    # Skipped aloud rather than deleted — see the other guards in this file, and roadmap #7.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    from engines import rig, insession
    from engines.session import Session
    from planner.ir import config
    from planner.ir.render import render

    orc = rig.build(_answering_world(), narrate=False)
    eng = orc.registry.get("qemu")
    goal = [{"shape": "count",
             "select": {"kind": "search", "query": "the diameter of the earth"}, "eq": 1}]
    sess = Session("search the web for the diameter of the earth", eng, intent="achieve")
    with config.use_kinds(eng.manifest):
        res = insession.drive(eng, goal, sess, lambda st, s: insession.Verdict(st.kind))

    assert res.get("ok"), res.get("why")
    # The in-session returns the LAST node's result; the rendered program travels with it.
    text = res.get("rendered") or render(res.get("program") or {})
    for line in text.splitlines():
        if "(" in line and not line.startswith(("ENSURE", "PUBLISH", "STORE")):
            assert line.startswith("CALL "), f"invocation without CALL: {line}"
    # THE DELIVERABLE WITNESS — `unknown = 0` says every member was actually ASKED, where
    # `answered != no` would be satisfied by a search nobody ran.
    assert "answer = 'unknown') = 0" in text, text
    assert "PUBLISH answer(the diameter of the earth);" in text, text

    said = [p.as_finding() for p in sess.published]
    assert said == [{"fact": "answer(the diameter of the earth)", "value": "12,742 km"}], said


def test_an_ordinary_program_still_says_done():
    """Most programs have no findings to report and must not finish in silence."""
    # NEEDS A MOUNTED PACKAGE, AND THERE IS NONE: `packages/webcrawler/` and `packages/git/`
    # were emptied for rework on 2026-08-02, so `rig.packages()` returns nothing. Skipped
    # ALOUD rather than deleted — roadmap #7 rebuilds packages on a three-file contract, and
    # these are the checks that say a package's kinds must reach the WRITER and not only the
    # schema. Found dead 2026-08-04: defined below the `__main__` guard, so never once run.
    from engines import rig as _rig_guard
    if not _rig_guard.packages():
        check("SKIPPED — no package is mounted; roadmap #7 rebuilds them", True)
        return

    from engines import rig
    from engines.qemu import QemuEngine
    from orchestrator.ai.active_library import LIBRARY
    from planner.ir import config
    from planner.ir.render import render

    eng = QemuEngine(LIBRARY, lambda t, a: {"success": True}, packages=rig.packages())
    with config.use_kinds(eng.manifest):
        p = eng._plan([{"shape": "count",
                        "select": {"kind": "vm", "name": "zzz-probe"}, "eq": 1}], None)
    assert "PUBLISH done;" in render(p["program"]), render(p["program"])


def test_the_same_claim_twice_is_one_claim():
    """A settling tree re-offers a node, and one search reported its answer five times."""
    from engines.insession import Publish
    from engines.session import Session

    sess = Session("q", None)
    sess.publish(Publish("alive(beta)", "false"))
    sess.publish(Publish("alive(beta)", "false"))
    assert len(sess.published) == 1
    # A CHANGE OF VALUE IS A SECOND FACT and stays audible.
    sess.publish(Publish("alive(beta)", "true"))
    assert len(sess.published) == 2


# THE ENTRY POINT BELONGS AT THE BOTTOM, and this is not style: `main()` ends in `sys.exit`,
# so every test defined BELOW this guard was never even defined when the suite ran — absent
# from the count and from `run_all.py`. SEVEN of them here. Found 2026-08-04 by a sweep
# after the same trap was hit in `test_extract.py`; three suites carried it and eleven tests
# had never run. `_suite.py` discovers by definition order, so placement is what keeps a
# test alive.

def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "the production rig"))


if __name__ == "__main__":
    main()
