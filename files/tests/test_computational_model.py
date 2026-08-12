"""test_computational_model.py — ONE MODEL, TWO TARGETS, AND THE LEAKS THAT WOULD END THAT.

The operator, 2026-08-13: *"the scaffold is high level code points … it should first be computed
to a COMPUTATIONAL MODEL — this way today it's Medusa, tomorrow it's Python."*

⇒ **A MIDDLE LAYER WITH ONE EMITTER IS INDIRECTION, NOT PORTABILITY**, and nothing reveals the
  difference until somebody adds the second and finds the first has leaked into the model. So
  both emitters ship together and the tests below are mostly about the LEAKS: an emitter that
  needed the manifest, a model that spoke Medusa, a loop that bound nothing.
"""
from planner import cmodel, emit
from planner.cmodel import DO, EACH, HOLD, MAKE, TELL, Model, Node

_FAIL = 0


def check(label, ok):
    global _FAIL
    if not ok:
        _FAIL += 1
    print(f"    {'ok  ' if ok else 'FAIL'}  {label}")


SCAFFOLD = [("create_vm", "vms", None),
            ("create_network", "network", None),
            ("add_vm_to_network", "vms", "network"),
            ("add_label", "vms", "fleet")]
DECL = {"vms": {"count": 5}, "network": {"count": None}}
MAKERS = {"create_vm": "vm", "create_network": "network"}


def _model():
    return cmodel.from_scaffold(SCAFFOLD, DECL, MAKERS, {"vms"})


def test_the_same_model_emits_to_both_targets():
    print("\n[cmodel] one model, two languages")
    m = _model()
    med, py = emit.to_medusa(m), emit.to_python(m)
    check("Medusa comes out", "FOREACH" in med and "NEW VM" in med)
    check("Python comes out", "for it in vms:" in py)
    check("and the OPERATION NAME is identical in both — it is opaque to the model",
          "add_vm_to_network" in med and "add_vm_to_network" in py)


def test_a_loop_binds_its_member():
    """THE BUG THE SECOND EMITTER CAUGHT ON ITS FIRST RUN.

    The first cut emitted `FOREACH $it IN $vms { CALL add_vm_to_network(on='vms') }` — iterating
    the set while still naming the SET inside the body, so every pass did the same thing to the
    whole collection. **A model you can only inspect as a dataclass hides that**; reading emitted
    source does not.
    """
    print("\n[cmodel] the loop variable actually reaches the body")
    med, py = emit.to_medusa(_model()), emit.to_python(_model())
    check("Medusa acts on the member", "add_vm_to_network(on=it" in med)
    check("Python acts on the member", "run('add_vm_to_network', on=it" in py)
    check("and neither acts on the set inside the loop",
          "add_vm_to_network(on='vms'" not in med and "on='vms')" not in py.split("for it")[-1])


def test_an_emitter_may_read_nothing_but_the_model():
    """If an emitter needs to ask a question, the answer belonged in the model.

    Asserted structurally rather than by inspection: neither emitter imports the manifest, the
    world, or anything from the seam above. The day one does, this fails.
    """
    print("\n[cmodel] the emitters are closed over the model alone")
    import ast
    import pathlib
    # ⇒ CHECKED ON THE IMPORTS, NOT THE TEXT. The first cut grepped the whole file and failed on
    #   `emit.py`'s own docstring, which mentions the manifest and the world precisely to say it
    #   does not read them. A test that cannot tell prose from code is not checking the property.
    tree = ast.parse(pathlib.Path(emit.__file__).read_text())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            imported.add(n.module or "")
    check(f"emit.py imports only the model and typing ({sorted(imported)})",
          all(m in ("typing", ".cmodel", "cmodel") for m in imported))


def test_a_creator_is_a_make_and_everything_else_is_a_do():
    """The distinction is not cosmetic: a language with constructors wants it, and MAKE is the
    only node that may bind a name nobody declared."""
    print("\n[cmodel] creators are distinguished from ordinary operations")
    m = _model()
    kinds = [n.kind for n in m.steps]
    check(f"two makes, two loops ({kinds})", kinds == [MAKE, MAKE, EACH, EACH])
    check("a make binds its result", m.steps[0].bind == "vms")


def test_amount_one_is_not_said():
    """`AMOUNT(1)` is what NEW means with nothing said — noise in both targets."""
    print("\n[cmodel] one is the default, not a quantity")
    med = emit.to_medusa(_model())
    check("no AMOUNT(1) in the Medusa", "AMOUNT(1)" not in med)
    check("but AMOUNT(5) survives", "AMOUNT(5)" in med)


def test_holds_and_tells_emit():
    """The two nodes the rung corpus does not exercise, pinned so they cannot rot unnoticed."""
    print("\n[cmodel] assertions and reports reach both targets")
    m = Model((Node(HOLD, must={"shape": "count", "select": {"kind": "vm"}, "eq": 2}),
               Node(TELL, fact="done")))
    med, py = emit.to_medusa(m), emit.to_python(m)
    check("Medusa: ENSURE + PUBLISH", "ENSURE" in med and "PUBLISH(done)" in med)
    check("Python: assert + publish", "assert holds(" in py and "publish('done')" in py)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{_FAIL} failed")


# ── the engine ────────────────────────────────────────────────────────────────────────────

def test_the_engine_runs_the_model_and_the_world_changes():
    """THE WHOLE POINT: scaffold -> model -> IR -> the REAL executor, and a world that moved.

    ⇒ **NO CHANGE TO THE ENGINE WAS NEEDED.** `execute.run` never wanted source, it wanted
      statements — so the engine is reached by a THIRD EMITTER rather than by a bridge, and
      `engines/medusa` is untouched.

    ⇒ **AND RUNNING IT FOR REAL CAUGHT THREE BUGS A MOCK WOULD NOT HAVE.** A `MAKE` passed
      `on=<handle>` as a creator argument (the handle is what it BINDS); a creator's arguments
      are the declaration's `where`, being what the request SAID about the thing; and the
      scaffold speaks in handles while tools take named parameters. Each was found by the layer
      below refusing to run something wrong.
    """
    print("\n[cmodel] the engine consumes the model and the world moves")
    from planner.ir import config, execute
    from planner.model_world import World

    world = World(kinds=config.KINDS)
    makers, params = {}, {}
    for kind, spec in config.KINDS.items():
        for c in (spec.get("creators") or {}).values():
            if isinstance(c, dict) and c.get("tool"):
                makers[c["tool"]] = kind
        for tool, s in (spec.get("setters") or {}).items():
            params[tool] = (s.get("member_arg") or "name", s.get("value_arg") or "value")

    decl = {"alpha": {"where": {"name": "alpha", "os_type": "linux"}},
            "core": {"where": {"net_name": "core"}}}
    ops = [("create_vm", "alpha", None), ("create_network", "core", None),
           ("add_vm_to_network", "alpha", "core"), ("launch_vm", "alpha", None)]
    m = cmodel.from_scaffold(ops, decl, makers, set(), params)
    # ⇒ A PROGRAM MUST VOUCH FOR SOMETHING. Without a HOLD the engine refuses it before running:
    #   *"nothing in this program produces a VERDICT — it fetches and acts but never asserts."*
    #   That is the language's rule, and `HOLD` is the node that satisfies it.
    m = Model(tuple(m.steps) + tuple(cmodel.holds(
        [{"shape": "count", "select": {"kind": "vm"}, "eq": 1}])))

    execute.run(emit.to_ir(m), world.execute)
    called = [c[0] for c in world.calls]
    check(f"every step reached the executor ({called})",
          called == ["create_vm", "create_network", "add_vm_to_network", "launch_vm"])
    check("the machine exists", "alpha" in (world.state.get("vm") or {}))
    check("the network exists", "core" in (world.state.get("network") or {}))
    alpha = (world.state.get("vm") or {}).get("alpha") or {}
    check(f"it is on the network and running ({alpha})",
          alpha.get("status") == "running" and "core" in (alpha.get("network") or set()))
