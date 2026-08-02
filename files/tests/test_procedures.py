#!/usr/bin/env python3
"""
test_procedures.py — a named program, kept, and REACHED FOR again.

THE OPERATOR'S TEST, and it is a better one than "can it write a snippet": *"the reason I
want to build this snippet is to also test if it can call those snippets when it's done."*
Writing an artifact proves the writer works. Using one later proves the system has a memory
made of its own code.

WHY THIS FILE EXISTS AT ALL. `procedures.py` shipped at 22894d7 with ZERO tests and the
store had never been written to — `save`, `covering` and `_unify` had not executed once, in
any process. The commit said so and named task #78 as the decision to finish or revert. This
is the finishing: every claim in that module is asserted here, and the last test is the
operator's, end to end.

WHAT IS NOT HERE, deliberately: no model. A procedure is chosen by a STRUCTURAL match
between what it declares it achieves and what the goal asks for, so the whole feature is
deterministic and this suite runs in under a second.

Run:  PYTHONPATH=. python3 -m tests.test_procedures
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planner import ghost_writer as gw
from planner import procedures as procs
from planner.ir import render, validate
from planner.ir import run as ir_run
from tests.bench.seams import seams
from tests.bench.sim_world import SimWorld

_PASS = _FAIL = 0


def check(label, ok):
    global _PASS, _FAIL
    if ok:
        _PASS += 1
        print(f"  ok   {label}")
    else:
        _FAIL += 1
        print(f"  FAIL {label}")


class _Library:
    """A store in a temp directory, installed as THE library for the duration.

    THE MODULE SINGLETON IS SWAPPED, not a second store handed around. `LIBRARY` is what the
    writer and the runtime both reach for, and a test that built its own would prove a Store
    works while leaving the seam those two actually use untested — which is precisely how
    this module came to have a save path nothing had ever run.
    """

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="gorgon-procs-")
        self.prior = procs.LIBRARY
        procs.LIBRARY = procs.Store(self.dir)
        return procs.LIBRARY

    def __exit__(self, *exc):
        procs.LIBRARY = self.prior
        shutil.rmtree(self.dir, ignore_errors=True)


# The snippet the operator asked for, in the language: make a machine from a template.
def _builder(name="vm_disk_builder"):
    return {"name": name,
            "params": {"box": "string"},
            "achieves": {"shape": "count",
                         "select": {"kind": "vm", "name": "$box"}, "eq": 1},
            "body": [{"op": "call", "tool": "create_vm",
                      "args": {"name": "$box", "os_type": "linux"}},
                     {"op": "ensure",
                      "predicate": {"shape": "count",
                                    "select": {"kind": "vm", "name": "$box"}, "eq": 1}}]}


def test_a_named_program_is_kept_in_ONE_file():
    """ONE FILE, and the operator's question was the right one: *"why are there two files?
    shouldnt it be 1?"*

    It was two, and the second was a symptom: the `.medusa` was what a person read and the
    `.json` was what RAN, and nothing in production ever read the `.medusa`. So the file the
    operator was invited to read, edit and share was not the file that ran. That is worse
    than duplication — it is an artifact that looks live.
    """
    print("[procedures] one file: the text a person reads, and the program it runs")
    with _Library() as lib:
        at = lib.save(_builder(), render(_builder()))
        check("the readable artifact is written", os.path.exists(at))
        check("and it is the .medusa", at.endswith(".medusa"))
        text = lib.text("vm_disk_builder")
        check("it renders as a PROCEDURE with its parameter",
              text.startswith("PROCEDURE vm_disk_builder(STRING box)"))
        got = lib.get("vm_disk_builder")
        check("the IR round-trips", got and got["body"] == _builder()["body"])
        check("ONE FILE, not two", os.listdir(lib.path) == ["vm_disk_builder.medusa"])
        check("and an untouched program has not drifted",
              lib.drifted("vm_disk_builder") is False)
        check("and the library names it", lib.names() == ["vm_disk_builder"])


def test_a_name_that_is_not_an_identifier_is_refused():
    """A procedure name is written INTO programs, so it has to survive being read back."""
    print("[procedures] the name has to be sayable in a program")
    with _Library() as lib:
        for bad in ("My Thing", "2fast", "has-a-dash", "", None, "drop table"):
            check(f"{bad!r} is refused", not procs.legal_name(bad))
        check("an ordinary one is not", procs.legal_name("vm_disk_builder"))
        try:
            lib.save({"name": "My Thing", "body": []})
            check("saving an illegal name raises", False)
        except ValueError as e:
            check("saving an illegal name raises, and says why", "identifier" in str(e))


def test_the_operator_declares_an_authoring_request():
    """DECLARE, DON'T INFER — the replacement for a word blinder that fired on 5 of 7.

    The blinder looked for {save, store, keep, reuse, …} and switched the extractor's prompt
    on a hit, so "save a snapshot of web" read as a request to write a snippet. What it
    bought was a schema field the model filled 0 times in 2. The prefix cannot do either.
    """
    print("[procedures] the operator says it, nobody guesses")
    name, rest = procs.declared_in("procedure build_box: make a machine from a template")
    check("the name is taken", name == "build_box")
    check("and the request is what is left", rest == "make a machine from a template")
    check("case does not matter", procs.declared_in("PROCEDURE b: x")[0] == "b")
    for ordinary in ("save a snapshot of web", "keep the vm running",
                     "store the iso on disk", "reuse the golden image",
                     "create a procedure for later"):
        got, rest = procs.declared_in(ordinary)
        check(f"{ordinary!r} is an ordinary request", got is None and rest == ordinary)
    bad, _ = procs.declared_in("procedure My Thing: x")
    check("a declaration with an unusable name is not silently an ordinary request",
          bad is None or not procs.legal_name(bad))


def test_a_stored_procedure_is_reached_for_by_the_writer():
    """THE POINT. A macro is expanded because somebody named it; this is chosen because it
    makes the goal true, and the operator is not in the room."""
    print("[procedures] the writer reaches for the operator's own snippet")
    with _Library() as lib:
        world = SimWorld()
        goal = {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}

        plain = gw.cover([goal], world)
        check("without a library it plans the primitive",
              [t for t, _ in plain] == ["create_vm"])

        lib.save(_builder(), render(_builder()))
        with_lib = gw.cover([goal], SimWorld())
        check("with one, it plans the PROCEDURE instead",
              [t for t, _ in with_lib] == ["vm_disk_builder"])
        check("binding the parameter from the goal",
              with_lib[0][1] == {"box": "web"})


def test_the_scratch_advances_by_the_procedures_own_body():
    """A later goal must be planned against the world the CALL will actually leave behind."""
    print("[procedures] planning sees what the call would do")
    with _Library() as lib:
        lib.save(_builder(), render(_builder()))
        goals = [{"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1},
                 {"every": {"kind": "vm", "name": "web"}, "must": {"label": "prod"}}]
        plan = gw.cover(goals, SimWorld())
        check("the procedure is placed first",
              plan and plan[0][0] == "vm_disk_builder")
        check("and the label lands on the machine it created",
              ("add_label", {"name": "web", "label": "prod"}) in plan)


def test_calling_one_runs_its_body_through_the_same_visitor():
    """Storing a program does not bless it — every statement meets the same executor."""
    print("[procedures] a procedure is a tool you wrote")
    with _Library() as lib:
        lib.save(_builder(), render(_builder()))
        world = SimWorld()
        program = {"body": [{"op": "call", "tool": "vm_disk_builder",
                             "args": {"box": "web"}},
                            {"op": "ensure",
                             "predicate": {"shape": "count",
                                           "select": {"kind": "vm", "name": "web"},
                                           "eq": 1}}]}
        ok, problems = validate(program, known_names=world.names(),
                                known_tools={"create_vm"} | set(lib.names()))
        check(f"a call to a stored procedure validates ({problems[:1]})", ok)
        select, holds = seams(world)
        result = ir_run(program, world.execute, select=select, holds=holds,
                        known_names=world.names(), known_tools={"create_vm"},
                        consent=True, intent="achieve")
        check("it runs", result["ok"])
        check("the body's calls actually happened", "web" in world.vms)
        check("and they are the caller's calls, listed",
              ("create_vm", {"name": "web", "os_type": "linux"}) in result["calls"])


def test_a_body_that_could_not_run_is_not_kept():
    """KEEPING IT IS ALSO ACCEPTING IT, and nothing checked that before.

    Scope isolation was already correct — the callee sees its arguments and nothing else —
    and the consequence was worse than a leak, not better: an unbound `$outer` inside a
    procedure body is not an error at run time, it is a TEMPLATE that resolves to itself, so
    the procedure created a machine literally called `$outer` and reported success. The
    isolation working is what turned a reference into garbage.

    `params` IS THE SCOPE and `validate` already reads it, so the rule needs no new
    machinery: a procedure may refer to what it declares and to what it binds.
    """
    print("[procedures] a procedure that cannot run is refused at the door")
    with _Library() as lib:
        leaky = _builder("leaky")
        leaky["body"] = [{"op": "call", "tool": "create_vm",
                          "args": {"name": "$outer", "os_type": "linux"}}]
        try:
            lib.save(leaky, render(leaky))
            check("a body referring to an unbound name is refused", False)
        except ValueError as e:
            check("a body referring to an unbound name is refused, and named",
                  "$outer" in str(e))
        check("and nothing was written", lib.names() == [])
        check("its own parameter is legitimately in scope",
              lib.save(_builder(), render(_builder())).endswith("vm_disk_builder.medusa"))


def test_the_callers_bindings_do_not_leak_into_the_callee():
    """A procedure whose meaning depended on where it was called from is not reusable."""
    print("[procedures] the arguments are the whole scope")
    with _Library() as lib:
        lib.save(_builder(), render(_builder()))
        world = SimWorld()
        # `box` IS BOUND IN THE CALLER TOO, to something else. The callee must see the
        # ARGUMENT, never the caller's binding of the same name.
        program = {"body": [{"op": "new", "var": "box", "kind": "vm",
                             "args": {"name": "decoy", "os_type": "linux"}},
                            {"op": "call", "tool": "vm_disk_builder",
                             "args": {"box": "web"}},
                            {"op": "ensure",
                             "predicate": {"shape": "count",
                                           "select": {"kind": "vm", "name": "web"},
                                           "eq": 1}}]}
        select, holds = seams(world)
        result = ir_run(program, world.execute, select=select, holds=holds,
                        known_names=world.names(), known_tools={"create_vm"},
                        consent=True, intent="achieve")
        check(f"it runs ({result.get('why') or result.get('failed') or ''})", result["ok"])
        check("the callee used its ARGUMENT", "web" in world.vms)
        check("and the caller's binding of the same name survives it",
              "decoy" in world.vms)


def test_one_damaged_file_does_not_take_down_the_writer():
    """`all()` propagated `get`'s exception, so ONE bad file crashed planning for EVERY goal
    — including every request that needs no procedure at all."""
    print("[procedures] a corrupt entry is skipped and named, never raised")
    with _Library() as lib:
        lib.save(_builder(), render(_builder()))
        with open(os.path.join(lib.path, "wrecked.medusa"), "w") as fh:
            # DAMAGED IN THE TEXT, because the text is now the only thing there is. This used
            # to be a well-formed block with broken JSON stapled under it — which stopped
            # being damage the moment the trailer became a comment, so the fixture was
            # asserting resilience against a file that loads perfectly well.
            fh.write("PROCEDURE wrecked( {\n  WOBBLE;\n")
        got = lib.all()
        check("the good one is still found", [p["name"] for p in got] == ["vm_disk_builder"])
        check("and the damaged one is named", lib.broken == ["wrecked"])
        goal = {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}
        check("the writer still plans", bool(gw.cover([goal], SimWorld())))
        try:
            lib.get("wrecked")
            check("but asking for it BY NAME still raises", False)
        except Exception:
            check("but asking for it BY NAME still raises", True)


def test_the_library_is_read_once_per_change_not_once_per_goal():
    """`covering()` is asked about every goal the writer covers, and it swept the whole
    directory each time — file reads on the writer's hot path, for a feature most requests
    never touch."""
    print("[procedures] reading is cached, and an edit is seen")
    with _Library() as lib:
        lib.save(_builder(), render(_builder()))
        reads = {"n": 0}
        real_open = open

        import builtins
        def counting(path, *a, **kw):
            if str(path).endswith(".medusa"):
                reads["n"] += 1
            return real_open(path, *a, **kw)

        builtins.open = counting
        try:
            for _ in range(20):
                lib.all()
            check(f"twenty sweeps cost one read ({reads['n']})", reads["n"] == 1)
            # AN EDIT IS SEEN, which is why the cache is stamped rather than held. These
            # files are the readable artifact; an operator editing one and getting
            # yesterday's behaviour would be the worst of both.
            edited = _builder()
            edited["body"].append({"op": "call", "tool": "add_label",
                                   "args": {"name": "$box", "label": "edited"}})
            at = os.path.join(lib.path, "vm_disk_builder.medusa")
            os.utime(at, (0, 0))
            # WRITTEN AS TEXT, because that is now the only thing a file holds. This fixture
            # used to write a signature with the real program stapled underneath in JSON —
            # which was a faithful simulation of an operator's edit only while the JSON was
            # what ran. Now an edit IS an edit to the text, which is the whole point of the
            # change, and the fixture says so.
            with real_open(at, "w") as fh:
                fh.write(render(edited) + "\n")
            got = lib.get("vm_disk_builder")
            check("an edited procedure is re-read", len(got["body"]) == 3)
        finally:
            builtins.open = real_open


def test_an_empty_library_costs_a_stat():
    """Most requests will never involve a procedure. The feature must be free for them."""
    print("[procedures] a library nobody has written to is free")
    with _Library() as lib:
        shutil.rmtree(lib.path, ignore_errors=True)
        goal = {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}
        check("covering answers None without listing anything",
              lib.covering(goal) is None)
        check("and the writer plans the primitive",
              [t for t, _ in gw.cover([goal], SimWorld())] == ["create_vm"])


def test_write_it_then_use_it():
    """THE OPERATOR'S TEST, END TO END, through the orchestrator both times.

        1. `procedure vm_disk_builder: a machine called web`   -> written and kept, NOTHING RUNS
        2. a later request for the same thing                  -> the writer reaches for it

    The second half is what makes this a memory rather than a macro: nobody named the
    procedure in the second request, and the plan contains it because it was the better move.
    """
    print("[procedures] write it, then use it — nobody naming it the second time")
    from engines import Channel, MedusaEngine, Orchestrator, Registry
    from engines.channel import Answer

    with _Library() as lib:
        goal = {"shape": "count", "select": {"kind": "vm", "name": "web"}, "eq": 1}

        def translate(request, world=None):
            return Answer([goal], "table", "")
        translate.name = "table"

        world = SimWorld()

        class LabEngine(MedusaEngine):
            def claims(self, request):
                return True

        reg = Registry()
        reg.mount(LabEngine(world))
        orch = Orchestrator(reg, Channel([translate]))

        out = orch.handle("a machine called web", intent="achieve",
                          regime="translation", procedure="vm_disk_builder")
        check("it closes DONE", out["outcome"] == "DONE")
        check("and says it was kept", "kept" in (out.get("why") or ""))
        check("NOTHING RAN — the point of authoring", not world.vms and not out["calls"])
        check("the artifact is on disk", os.path.exists(out["procedure"]["at"]))
        check("and it is the program that would have worked",
              "create_vm" in out["procedure"]["rendered"])

        # AND NOW THE HALF THAT MATTERS. A fresh world, the same goal, nobody naming the
        # procedure — and the writer reaches for it because it makes the goal true.
        plan = gw.cover([goal], SimWorld())
        check("the second request plans the operator's own snippet",
              [t for t, _ in plan] == ["vm_disk_builder"])


def test_a_span_is_read_or_refused_and_never_guessed():
    """A schedule nobody can read must not become "every zero seconds"."""
    print("[routines] a span, in the form the manifest already declares")
    for text, want in (("30s", 30), ("15m", 900), ("1h", 3600), ("7d", 604800),
                       (" 2 h ", 7200)):
        check(f"{text!r} -> {want}", procs.seconds(text) == want)
    for junk in ("", None, "hourly", "1", "1w", "-5m", "1.5h", "soon"):
        check(f"{junk!r} is refused, not guessed", procs.seconds(junk) is None)


def test_the_clock_calls_a_routine_and_only_when_it_is_due():
    print("[routines] every 1h means every 1h")
    with _Library() as lib:
        sweep = _builder("hourly_sweep")
        sweep["every"] = "1h"
        lib.save(sweep, render(sweep))

        due = lib.due(1000.0)
        check("a routine that has never run is due", [d["name"] for d in due]
              == ["hourly_sweep"])
        check("and it says why", "never run" in due[0]["why"])

        lib.remember("hourly_sweep", last_run=1000.0)
        check("just-run is not due", lib.due(1000.0) == [])
        check("and neither is it 59 minutes later", lib.due(1000.0 + 3540) == [])
        check("an hour later it is", len(lib.due(1000.0 + 3600)) == 1)

        # `now` IS SUPPLIED, NEVER READ. A module that reached for the clock could not be
        # tested without waiting, and the caller is what knows what time it is.
        check("nothing here reads a clock", "time" not in dir(procs))


def test_a_trigger_fires_on_becoming_true_and_not_on_being_true():
    """LEVEL-TRIGGERED IS THE BUG. "When a machine stops answering, snapshot it" run as a
    level rule snapshots forever, and the operator learns to ignore it."""
    print("[routines] a trigger fires on the edge, once per becoming")
    with _Library() as lib:
        watch = _builder("on_empty")
        watch["when"] = {"shape": "count", "select": {"kind": "vm"}, "eq": 0}
        lib.save(watch, render(watch))

        world = SimWorld()
        _select, holds = seams(world)

        check("an empty lab fires it once", len(lib.due(1.0, holds=holds)) == 1)
        check("and not again while it stays empty", lib.due(2.0, holds=holds) == [])

        world.execute("create_vm", {"name": "a", "os_type": "linux"})
        check("a lab that filled up does not fire it", lib.due(3.0, holds=holds) == [])
        world.execute("delete_vm", {"name": "a"})
        check("emptying it again is a new edge", len(lib.due(4.0, holds=holds)) == 1)


def test_a_condition_nobody_can_evaluate_is_not_a_firing():
    """UNKNOWN IS NOT FALSE, which means it is not the far side of an edge either — the
    becoming is still ahead of us rather than behind."""
    print("[routines] an unanswerable condition moves nothing")
    with _Library() as lib:
        watch = _builder("on_mystery")
        watch["when"] = {"shape": "count", "select": {"kind": "vm"}, "eq": 0}
        lib.save(watch, render(watch))

        def cannot(pred, scope):
            raise RuntimeError("the world cannot answer that")

        check("it does not fire", lib.due(1.0, holds=cannot) == [])
        check("and nothing was remembered about it",
              lib.state("on_mystery").get("last_seen") is None)
        world = SimWorld()
        _select, holds = seams(world)
        check("so the first real answer is still an edge",
              len(lib.due(2.0, holds=holds)) == 1)


def test_being_scheduled_earns_a_program_nothing():
    """A due routine is served by the ordinary path. If a schedule could license work the
    same program could not do when typed, the schedule would be a way around every gate."""
    print("[routines] due is about WHEN, never about what is allowed")
    with _Library() as lib:
        watch = _builder("nightly")
        watch["every"] = "1d"
        at = lib.save(watch, render(watch))
        check("it is kept like any other procedure", at.endswith("nightly.medusa"))
        check("it is callable by name", lib.get("nightly") is not None)
        check("and it is still reachable by the writer, because it says what it achieves",
              lib.covering({"shape": "count",
                            "select": {"kind": "vm", "name": "web"}, "eq": 1}) is not None)
        # THE STATE IS NOT THE PROGRAM. Writing `last_run` into the artifact would rewrite
        # the operator's own file every sweep and invalidate the read cache each time.
        lib.remember("nightly", last_run=5.0)
        check("run state is kept beside it, not inside it",
              "last_run" not in (lib.text("nightly") or ""))
        check("and the program is IN the .medusa, which is now the only file",
              sorted(f.rsplit(".", 1)[1] for f in os.listdir(lib.path))
              == ["medusa", "state"])
        check("and the IR is untouched", "last_run" not in json.dumps(lib.get("nightly")))


def test_a_due_routine_runs_through_the_ordinary_engine():
    """THE SEAM THAT WOULD OTHERWISE BE LEFT AT None. A schedule nobody sweeps is a feature
    that does not fail because it does not run — the shape `rig.py` exists to prevent."""
    print("[routines] and the sweep actually runs one")
    from engines import Channel, MedusaEngine, Orchestrator, Registry

    with _Library() as lib:
        lib.save(_builder("nightly_box"), render(_builder("nightly_box")))
        world = SimWorld()

        class LabEngine(MedusaEngine):
            def claims(self, request):
                return True

        reg = Registry()
        reg.mount(LabEngine(world))
        out = Orchestrator(reg, Channel()).handle(
            "nightly_box", intent="achieve", regime="translation",
            components=[{"_call": ("nightly_box", {"box": "web"})}])
        check(f"it closes DONE ({out.get('why')})", out["outcome"] == "DONE")
        check("the procedure's body actually ran", "web" in world.vms)


def _network_setup():
    """The operator's own example, at the size they wrote it.

        NetworkSetup.medusa
          attach(vms, net_name)   ·  add(vm, net_name)
    """
    member = {"shape": "count", "eq": 1,
              "select": {"kind": "vm", "name": "$vm", "network": "$net_name"}}
    return {"name": "NetworkSetup", "methods": {
        "attach": {"params": {"vms": "set", "net_name": "string"},
                   "body": [{"op": "foreach", "in": "$vms",
                             "call": {"op": "call", "tool": "add_vm_to_network",
                                      "args": {"vm_name": "$item",
                                               "net_name": "$net_name"}}},
                            {"op": "ensure", "predicate": {
                                "shape": "count", "eq": 0,
                                "select": {"kind": "vm", "network": "none"}}}]},
        "add": {"params": {"vm": "string", "net_name": "string"},
                "achieves": member,
                "body": [{"op": "call", "tool": "add_vm_to_network",
                          "args": {"vm_name": "$vm", "net_name": "$net_name"}},
                         {"op": "ensure", "predicate": member}]}}}


def test_a_set_is_declarable_at_last():
    """EVERY PARAM TYPE WAS A SCALAR, and that was a limit rather than a gap nobody reached:
    `attach(vms, net_name)` could not declare its first argument at all."""
    print("[classes] a parameter may be a set")
    from planner.ir import config

    check("the manifest declares it", "set" in config.PARAM_TYPES)
    loop = {"name": "over", "params": {"vms": "set"},
            "body": [{"op": "foreach", "in": "$vms",
                      "call": {"op": "call", "tool": "add_label",
                               "args": {"name": "$item", "label": "seen"}}},
                     {"op": "ensure", "predicate": {
                         "shape": "count", "select": {"kind": "vm", "label": "seen"},
                         "gte": 1}}]}
    ok, problems = validate(loop)
    check(f"a FOREACH over a declared set validates ({problems[:1]})", ok)
    scalar = {**loop, "params": {"vms": "string"}}
    ok2, problems2 = validate(scalar)
    check(f"and the same loop over a STRING does not ({problems2[:1]})", not ok2)


def test_a_class_is_a_file_with_several_entry_points():
    print("[classes] one file, several procedures")
    with _Library() as lib:
        at = lib.save(_network_setup())
        check("it is kept under the class's name", at.endswith("NetworkSetup.medusa"))
        check("and the methods are what is CALLABLE",
              lib.names() == ["NetworkSetup.add", "NetworkSetup.attach"])
        check("the class itself is not callable — it has no body",
              "NetworkSetup" not in lib.names())
        got = lib.get("NetworkSetup.add")
        check("a method comes back as an ordinary program",
              got and got["name"] == "NetworkSetup.add" and got["body"])
        check("a method nobody defined is absent, not an error",
              lib.get("NetworkSetup.teleport") is None)
        text = lib.text("NetworkSetup")
        check("the artifact renders every method",
              text.count("PROCEDURE") == 2 and "NetworkSetup.attach(SET vms" in text)


def test_a_method_that_vouches_for_nothing_is_not_kept():
    """THE LINE BETWEEN A CLASS AND A BAG OF MACROS. A method that expands into tool calls
    and asserts nothing inherits the false-success class the system refuses everywhere, and
    its caller cannot trust the result without re-checking — which is the work a class exists
    to have done ONCE."""
    print("[classes] verified once means verified")
    with _Library() as lib:
        bare = _network_setup()
        bare["methods"]["add"]["body"] = [
            {"op": "call", "tool": "add_vm_to_network",
             "args": {"vm_name": "$vm", "net_name": "$net_name"}}]
        try:
            lib.save(bare)
            check("an ungrounded method is refused", False)
        except ValueError as e:
            check("an ungrounded method is refused, and named",
                  "NetworkSetup.add" in str(e) and "vouches for nothing" in str(e))
        check("and nothing was written", lib.names() == [])


def test_a_class_method_is_reached_for_and_run_like_anything_else():
    """NOTHING DOWNSTREAM LEARNS A NEW WORD. That is the whole design: `covering`, `validate`
    and the visitor keep asking the one question they already asked."""
    print("[classes] the rest of the system does not know it is a class")
    with _Library() as lib:
        lib.save(_network_setup())
        world = SimWorld()
        world.execute("create_vm", {"name": "web", "os_type": "linux"})
        world.execute("create_network", {"net_name": "dmz"})

        goal = {"shape": "count", "eq": 1,
                "select": {"kind": "vm", "name": "web", "network": "dmz"}}
        found = lib.covering(goal)
        check("the writer can reach for a METHOD",
              found and found["name"] == "NetworkSetup.add")
        check("binding both of its parameters",
              found["params"] == {"vm": "web", "net_name": "dmz"})

        program = {"body": [{"op": "call", "tool": "NetworkSetup.add",
                             "args": {"vm": "web", "net_name": "dmz"}},
                            {"op": "ensure", "predicate": goal}]}
        ok, problems = validate(program, known_names=world.names(),
                                known_tools={"add_vm_to_network"})
        check(f"a call to a method validates ({problems[:1]})", ok)
        select, holds = seams(world)
        res = ir_run(program, world.execute, select=select, holds=holds,
                     known_names=world.names(), known_tools={"add_vm_to_network"},
                     consent=True, intent="achieve")
        check(f"and it runs ({res.get('why')})", res["ok"])
        check("the method's body reached the world",
              "dmz" in world.vms["web"]["nets"])


def main():
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "procedures"))


if __name__ == "__main__":
    main()
