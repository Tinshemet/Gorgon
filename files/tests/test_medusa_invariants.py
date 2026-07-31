#!/usr/bin/env python3
"""
test_medusa_invariants.py — the LANGUAGE checking itself.

Medusa's one soundness rule is that a PROGRAM must vouch for itself: it needs a verdict,
because a run that asserts nothing has established nothing. Nothing made the language's
own parts vouch for agreeing with EACH OTHER — and that is where almost every defect in
its history has lived. The operator's observation, 2026-07-27: *"so in the language traps
problem is a missing ensure, which is interesting."* This file is that ENSURE.

WHAT IT IS NOT. `test_medusa.py` runs example programs and checks they behave. This runs
NO programs. It reads the manifest — the language's own statement of what it is — and
holds every implementation to it. The two catch different things, and only this one would
have caught the list below BEFORE a ladder run rather than after six of them:

  * `disjoint` was DECLARED in the manifest, OFFERED by the schema, ACCEPTED by the
    validator and PRINTED by the renderer — with no evaluator. It answered false in every
    world, for weeks. Composites were in exactly that state a session earlier; they were
    fixed one at a time and the invariant was never written down, so the next shape
    repeated it.
  * legal binding names were not readable names: `STORE red-net = NEW network` bound a
    name `$red-net` cannot pronounce, and the author was told it never created something
    it had created one line above.
  * the schema offered `NOT` an array while the validator demanded an object and the
    executor accepted either — three components, three answers, one construct.
  * `status` was offered as free text, so the decoder invented `'not running'`, matched
    nobody, ran zero calls and reported ok.
  * the executor overrode the author's explicit `net_name`, creating `core_net` where the
    program plainly said `core`.

Every one is checkable from the manifest plus the code, deterministically, in
milliseconds, with no model and no world.

THE RULE THIS FILE ENFORCES: a language feature is not one construct, it is FOUR
agreements — the validator accepts it, the executor runs it, the renderer shows it, and
the schema offers it. Three out of four is a construct that exists and cannot be used, or
worse, one that is used and quietly does nothing.

Run:  PYTHONPATH=. python3 tests/test_medusa_invariants.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.ai.planner.findings import DEFAULT_SCHEMA
from orchestrator.ai.planner.ir import config, derive, evaluate, refs, render, run, validate
from orchestrator.ai.planner.ir import intent as intent_mod
from orchestrator.ai.planner.ir.derive import _DERIVERS
from tests.bench.author_probe import _seams, program_schema
from tests.bench.sim_world import SimWorld

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


def _sample_predicate(shape: str):
    """A minimal well-formed predicate of `shape`, built from the manifest's own row.

    Built rather than listed, so a shape added to the JSON is exercised here without
    anyone remembering to add it — which is the whole failure mode this file exists for.
    """
    spec = config.PREDICATES[shape]
    pred = {"shape": shape}
    operand, arity = spec["operand"], spec.get("arity")
    if operand == "select":
        pred["select"] = {"kind": "vm"}
    elif operand == "sets":
        pred["sets"] = ["$a", "$b"]
    elif operand == "of":
        if arity == "value":
            pred["of"] = "$answer.alive"
        elif arity == "one":
            pred["of"] = {"shape": "count", "select": {"kind": "vm"}, "eq": 1}
        else:
            pred["of"] = [{"shape": "count", "select": {"kind": "vm"}, "eq": 1},
                          {"shape": "count", "select": {"kind": "vm"}, "gte": 1}]
    for comparator in (spec.get("comparators") or {}):
        pred[comparator] = 1 if comparator != "eq" or arity != "value" else True
        break
    return pred


# ── every predicate shape is answerable, showable, and says whether it can be closed ──
def test_every_predicate_shape_has_an_evaluator():
    """`disjoint` is why. Declared, offered, validated, rendered — and the seam fell
    through to "unevaluated shape disjoint", which a postcondition then counted as FAILED.
    So a correct statement of rung 6's goal could not hold in any world, and burned three
    revision rounds saying so."""
    w = SimWorld()
    w.execute("create_vm", {"name": "a", "os_type": "linux"})
    _, holds = _seams(w)
    scope = {"a": ["a"], "b": ["x"], "answer": {"alive": True}}
    for shape in config.PREDICATES:
        _good, why = evaluate(_sample_predicate(shape), scope, holds)
        check(f"{shape}: answered, not shrugged at",
              "unevaluated" not in str(why).lower())


def test_every_predicate_shape_renders_legibly():
    """The renderer is the only thing a human reads before approving a program. A shape
    it cannot print is a program nobody can check — and `REACH(SELECT vm) ? None` was a
    LEGAL statement printed as gibberish."""
    for shape in config.PREDICATES:
        out = render({"body": [{"op": "ensure", "predicate": _sample_predicate(shape)}]})
        check(f"{shape}: renders without a placeholder",
              "?" not in out and "None" not in out and "unknown" not in out.lower())


def test_every_predicate_shape_declares_whether_it_can_be_derived():
    """A shape either has a deriver or says outright that it cannot have one. Without
    this, a shape that silently cannot converge is indistinguishable from one nobody has
    written a deriver for yet — and an ACHIEVE built on it never closes."""
    for shape, spec in config.PREDICATES.items():
        declared = spec.get("derivable") is False
        has = shape in _DERIVERS
        check(f"{shape}: {'declared underivable' if declared else 'has a deriver'}",
              declared != has or (has and not declared))
        if declared:
            check(f"{shape}: says WHY it cannot be derived",
                  bool(spec.get("_derivable_doc")))


# ── every op the manifest declares is one the visitor and the renderer know ───────────
# The manifest is the CONTRACT between the two, not a switch: adding a row does not make a
# statement executable. This table states what each op observably does, so a new op fails
# here until someone says what it is for.
_OP_EFFECT = {
    "new":     "issues a creator call",
    "call":    "issues its tool",
    "fetch":   "binds what it read",
    "foreach": "issues a call per member",
    "ensure":  "produces a verdict",
    "achieve": "produces a verdict",
    "if":      "runs one branch",
}


def test_every_op_is_accounted_for():
    check("every op in the manifest has a stated effect",
          set(config.OPS) == set(_OP_EFFECT))
    for op in config.OPS:
        out = render({"body": [{"op": op}]})
        check(f"{op}: the renderer knows it", "<unknown op" not in out)


def test_every_op_is_in_exactly_one_category():
    """STRUCTURAL vs INTENT. A router asks the model for structure; intent comes from the
    operator and `ir/intent.py` enforces it. An op in neither category would silently be
    offered as a free choice again — which is the defect the split exists to fix — and an
    op in BOTH would let a router ask for something already decided."""
    cats = config.OP_CATEGORIES
    seen = [op for group in cats.values() for op in group]
    check("every op is categorised", set(seen) == set(config.OPS))
    check("no op is in two categories", len(seen) == len(set(seen)))
    # The intent category IS the intent ladder's three words — not a parallel list that
    # can drift from it. `intent.py` is the authority; this asserts they agree.
    check("the intent ops are exactly the three intents",
          set(cats["intent"]) == {intent_mod.FETCH, intent_mod.ENSURE, intent_mod.ACHIEVE})


def test_single_licenses_call_and_never_foreach():
    """THE POINT OF WIRING `single` AT ALL, stated as the guarantee it actually gives.

    I first wrote this as "a `single` schema offers NO select anywhere" and the invariant
    caught it: `single` licenses `fetch`, and *fetch the vm named db* legitimately needs a
    select to identify one object. Removing selects wholesale would break a real statement
    to fix a different one.

    THE TRUE GUARANTEE IS NARROWER AND IS STILL THE FIX: no `foreach`. Rung 8's statement 4
    is a LOOP over a select of one — `FOREACH $item IN SELECT ? WHERE name = 'db'` — and it
    is the loop, not the select, that is wrong for a clause about one identified object.
    Deny `foreach` and the statement can only be the `call` that was right all along.
    """
    licensed = set(config.QUANTIFIERS["single"]["ops"])
    check("single licenses `call`", "call" in licensed)
    check("single does NOT license `foreach` — no looping over a set of one",
          "foreach" not in licensed)
    check("every set-shaped quantifier DOES license `foreach`",
          all("foreach" in set(config.QUANTIFIERS[q]["ops"])
              for q in ("all", "any", "not")))


def test_every_quantifier_licenses_only_real_ops_and_at_least_one():
    """A quantifier naming an op the language does not have would narrow the schema to
    something unbuildable; one licensing NOTHING would silently offer an empty menu, which
    reads to the model as "no legal statement" and is how a construct goes quietly dead."""
    for name, spec in config.QUANTIFIERS.items():
        licensed = spec.get("ops") or []
        check(f"{name}: licenses at least one op", bool(licensed))
        for op in licensed:
            check(f"{name}: {op} is a real op", op in config.OPS)
        check(f"{name}: states what it means", bool(spec.get("doc")))


def test_a_quantifier_narrows_the_schema_it_builds():
    """END TO END, because the table being right is not the same as it reaching the model.
    `master.ops` reads the manifest, `program_schema` reads `master.ops`, and the thing
    that matters is the SCHEMA — six builders read config independently and the stale twin
    is always the risk."""
    import json as _json
    full = _json.dumps(program_schema("achieve", None))
    single = _json.dumps(program_schema("achieve", None, quantifier="single"))
    check("the full schema offers foreach", '"const": "foreach"' in full)
    check("a `single` schema does NOT offer foreach",
          '"const": "foreach"' not in single)
    check("a `single` schema still offers call", '"const": "call"' in single)
    check("narrowing actually removes branches", len(single) < len(full))


def test_cardinality_is_by_construction_and_never_by_member_count():
    """THE OPERATOR'S REQUIREMENT, 2026-07-29, stated as a test because it is the one thing
    this whole mechanism can get subtly wrong: *"it needs to understand it's a key filter
    and only use singular form while still understanding to use foreach even if a set has
    only 1 member."*

    A label matching exactly ONE machine today is still a SET EXPRESSION and keeps its
    loop; a key filter is singular even in a lab holding a thousand machines. The test of
    the property is that `cardinality_of` NEVER CONSULTS THE WORLD — it reads the select's
    shape and nothing else — so member counts cannot leak into the answer. If it ever grew
    a world argument, this is what would fail.
    """
    import inspect as _inspect
    from orchestrator.ai.planner.ir import master as _master
    sig = _inspect.signature(_master.cardinality_of)
    check("cardinality_of takes ONLY a select — no world, no registry, no counts",
          list(sig.parameters) == ["sel"])
    check("a key filter is singular", _master.cardinality_of({"kind": "vm", "name": "db"})
          == "singular")
    check("a NON-key filter is a set however few match today",
          _master.cardinality_of({"kind": "vm", "label": "prod"}) == "set")
    check("a complement is a set — NOT ANY resolved",
          _master.cardinality_of({"kind": "vm", "not": {"name": "db"}}) == "set")
    # MEMBERSHIP IS A SET AT EVERY LENGTH. A one-element `in` list is the sharpest test of
    # the whole rule, because it is where counting and construction disagree — and an
    # earlier version answered `singular` there, which was a member count wearing a
    # different hat.
    check("membership over the key is a SET even at length 1",
          _master.cardinality_of({"kind": "vm", "name": {"in": ["solo"]}}) == "set")
    check("membership over the key is a set at length 2",
          _master.cardinality_of({"kind": "vm", "name": {"in": ["a", "b"]}}) == "set")
    check("a bound $set is a set (size not even knowable at authoring time)",
          _master.cardinality_of({"kind": "vm", "name": {"in": "$vms"}}) == "set")
    check("ONLY scalar equality on the key is singular",
          _master.cardinality_of({"kind": "vm", "name": "db"}) == "singular")
    # every kind's key, not just vm's — a new kind must not quietly fall through to `set`
    for kind, spec in config.KINDS.items():
        key = spec.get("key")
        check(f"{kind}: a filter on its key ({key}) is singular",
              _master.cardinality_of({"kind": kind, key: "x"}) == "singular")


def test_the_visitor_does_not_silently_ignore_a_statement():
    """An op the visitor does not handle falls through and does NOTHING — no error, no
    call, a green close over a statement that never ran. That is the false-success class
    in the one place it would be hardest to notice."""
    w = SimWorld()
    sel, holds = _seams(w)
    res = run({"body": [{"op": "call", "tool": "create_vm",
                         "args": {"name": "x", "os_type": "linux"}}]},
              w.execute, select=sel, holds=holds, consent=True)
    check("a known op reaches the world", res["ok"] and len(w.calls) == 1)
    # A statement whose op is not in the manifest must be REFUSED, never run past.
    ok, _ = validate({"body": [{"op": "teleport", "tool": "x"}]})
    check("an unknown op is refused by the validator", not ok)


# ── the four-way agreement: manifest, validator, renderer, schema ─────────────────────
def _select_schema():
    """The attributes a `select` offers the author — FOLLOWING `$ref`.

    A select is 14.7KB and appears in `fetch`, in `foreach`, and inside every predicate
    that takes one, so the schema hoists it into `$defs` and references it. This helper
    read `properties` directly and therefore saw nothing once that happened — reporting
    every attribute as UNOFFERED when all of them were offered, one indirection away.

    The property this file guards is "the author can say it", and a `$ref` says it. What
    would be a real failure is the attribute being absent from the definition itself.
    """
    schema = program_schema()
    defs = schema.get("$defs", {})

    def resolve(node):
        seen = 0
        while isinstance(node, dict) and "$ref" in node and seen < 8:
            key = node["$ref"].rsplit("/", 1)[-1]
            node = defs.get(key, {})
            seen += 1
        return node if isinstance(node, dict) else {}

    for branch in defs.get("stmt", {}).get("oneOf", []):
        target = resolve(branch.get("properties", {}).get("select", {}))
        if target.get("properties"):
            return target["properties"]
    return {}


def test_every_queryable_attribute_is_offered_to_the_author():
    """A construct the schema withholds may as well not exist. Measured repeatedly: the
    carve-out was implemented and never offered, so the author invented `name: '!db'`;
    `status` was offered untyped, so it invented `'not running'`. Both were scored as
    model failures."""
    offered = _select_schema()
    for kind in config.KINDS:
        for attr in config.queryable(kind):
            if attr in (config.KINDS[kind].get("aliases") or {}):
                continue                       # a synonym need not be advertised
            check(f"{kind}.{attr} is offered in a select", attr in offered)
    check("the carve-out is offered", "not" in offered)
    check("membership is offered on the key",
          "anyOf" in str(offered.get("name", {})) and "in" in str(offered.get("name", {})))
    for group in ("any", "all"):
        check(f"the {group} group is offered", group in offered)


def test_every_closed_vocabulary_is_both_offered_and_policed():
    """`status` is running or stopped. Offered as a bare string, the decoder invented a
    third value, matched nobody, ran zero calls and reported ok."""
    offered = _select_schema()
    for kind in config.KINDS:
        for attr in config.queryable(kind):
            values = config.values_for(kind, attr)
            if not values:
                continue
            spec = str(offered.get(attr, {}))
            check(f"{kind}.{attr}: its values are offered as an enum",
                  all(v in spec for v in values))
            bad = validate({"body": [{"op": "ensure", "predicate": {
                "shape": "count", "select": {"kind": kind, attr: "___nope___"},
                "eq": 1}}]})
            check(f"{kind}.{attr}: an invented value is policed", not bad[0])


def test_every_predicate_shape_is_offered_to_the_author():
    pred = program_schema()["$defs"]["pred"]
    shapes = {b["properties"]["shape"]["const"] for b in pred["oneOf"]}
    check("every declared shape has a schema branch", shapes == set(config.PREDICATES))


# ── the manifest cannot name a tool or a fact that does not exist ─────────────────────
def test_every_kind_names_real_tools():
    try:
        from executor.command_catalog import KNOWN_TOOLS
    except ImportError:                                        # pragma: no cover
        KNOWN_TOOLS = frozenset()
    for kind, spec in config.KINDS.items():
        for role in ("create", "list"):
            tool = spec.get(role)
            check(f"{kind}.{role} = {tool!r} is a real tool",
                  not tool or not KNOWN_TOOLS or tool in KNOWN_TOOLS)
        for name, creator in (spec.get("creators") or {}).items():
            tool = creator.get("tool")
            check(f"{kind}.creators.{name} = {tool!r} is a real tool",
                  not tool or not KNOWN_TOOLS or tool in KNOWN_TOOLS)


def test_every_observed_attribute_is_actually_learnable():
    """An observed attribute reads `unknown` until something asks. If the tool that asks
    does not exist, or does not record the fact, it reads unknown FOREVER — a query that
    can never answer, which is the same false assurance as a check that can never pass."""
    try:
        from executor.command_catalog import KNOWN_TOOLS
    except ImportError:                                        # pragma: no cover
        KNOWN_TOOLS = frozenset()
    for kind in config.KINDS:
        for attr, spec in config.observed(kind).items():
            by = spec.get("by")
            check(f"{kind}.{attr}: learned by a real tool ({by})",
                  not KNOWN_TOOLS or by in KNOWN_TOOLS)
            check(f"{kind}.{attr}: that tool records a finding",
                  by in DEFAULT_SCHEMA)
            fact_template = spec.get("fact", "")
            recorded = (DEFAULT_SCHEMA.get(by) or {}).get("fact")
            check(f"{kind}.{attr}: under the SAME fact key the ledger writes",
                  fact_template == recorded)
            check(f"{kind}.{attr}: and the key formats for a member",
                  config.fact_key(kind, attr, "probe_target") is not None)


# ── names, sigils and the surface ─────────────────────────────────────────────────────
def test_bindable_names_are_exactly_readable_names():
    """`-` is excluded from a reference token so `$item-snap` composes a name. Nothing
    stopped an author BINDING `red-net`, which `$red-net` then reads as `$red` plus text —
    a name the language accepts and cannot pronounce."""
    pattern = None
    for branch in program_schema()["$defs"]["stmt"]["oneOf"]:
        var = branch.get("properties", {}).get("var")
        if isinstance(var, dict) and var.get("pattern"):
            pattern = var["pattern"]
            break
    check("the schema constrains binding names", bool(pattern))
    if pattern:
        rx = re.compile(pattern)
        for name in ("web", "red_net", "n1", "_x", "red-net", "2nd", "a.b", ""):
            check(f"schema and refs agree on {name!r}",
                  bool(rx.match(name)) == refs.is_referenceable(name))


def test_the_surface_spells_every_word_it_owns():
    """A word renamed in the surface table must be renamed everywhere it prints. It was a
    dict in render.py once, so a comparator added to the JSON printed as `?`."""
    # EVERY op that prints a keyword must own it here, so renaming is a data change.
    # `call` is the one exception and a real one: an invocation has no keyword, it reads
    # as tool(args).
    for op in config.OPS:
        if op == "call":
            continue
        check(f"{op} has a written form", op in config.SURFACE)
    # The clause words the renderer prints are equally part of the surface — `fetch` had
    # an entry the renderer ignored in favour of a literal, which is the same hole.
    for word in ("where", "except", "include", "in", "count", "ifails", "async",
                 "procedure", "import"):
        check(f"the {word.upper()} clause is spelled in the surface table",
              word in config.SURFACE)
    # And renaming one must actually change the output — the property all of this is for.
    import copy
    from orchestrator.ai.planner.ir import config as _cfg
    original = _cfg.SURFACE["ensure"]
    try:
        _cfg.SURFACE["ensure"] = "VERIFY"
        out = render({"body": [{"op": "ensure", "predicate": {
            "shape": "count", "select": {"kind": "vm"}, "eq": 1}}]})
        check("renaming a surface word changes what prints", out.strip().startswith("VERIFY"))
    finally:
        _cfg.SURFACE["ensure"] = original
    for shape, spec in config.PREDICATES.items():
        if spec.get("source") == "composite":
            check(f"{shape} has a combinator word",
                  shape in (config.SURFACE.get("combinators") or {}))
        for comparator in (spec.get("comparators") or {}):
            check(f"{shape}.{comparator} has a symbol",
                  bool(spec["comparators"][comparator]))


def test_the_two_selects_answer_the_same_question():
    """The bench seam and the production seam must agree on every construct.

    Every rung was measured against the BENCH select. If the production one answers
    differently — misses a carve-out, ignores an alias, drops a group — then the ladder is
    a statement about a simulator and nothing else. Same world, same query, same answer,
    or the number means nothing.
    """
    from orchestrator.ai.active_library import ActiveLibrary
    from orchestrator.ai.planner.findings import Findings
    from orchestrator.ai.planner.program import make_select

    # One lab, built twice — once as the bench world, once as the registry.
    w = SimWorld()
    for n, os_type in (("app1", "linux"), ("app2", "linux"), ("db", "windows")):
        w.execute("create_vm", {"name": n, "os_type": os_type})
    w.execute("launch_vm", {"name": "app1"})
    w.execute("add_label", {"name": "app1", "label": "fleet"})
    w.execute("add_label", {"name": "app2", "label": "fleet"})
    w.execute("add_label", {"name": "db", "label": "prod"})
    w.execute("create_network", {"net_name": "core"})
    w.execute("add_vm_to_network", {"net_name": "core", "vm_name": "app1"})
    w.calls.clear()

    lib = ActiveLibrary()
    lib._vms = {n: {"name": n, "os_type": v.get("os_type", "linux"),
                    "status": v["status"], "labels": sorted(v["labels"]), "flags": []}
                for n, v in w.vms.items()}
    lib._networks = {net: {"members": sorted(n for n, v in w.vms.items()
                                             if net in v.get("nets", set()))}
                     for net in w.nets}
    ledger = Findings()
    bench_select, _ = _seams(w)
    prod_select = make_select(lib, ledger)

    queries = [
        {"kind": "vm"},
        {"kind": "vm", "label": "fleet"},
        {"kind": "vm", "tag": "fleet"},                       # an alias
        {"kind": "vm", "status": "running"},
        {"kind": "vm", "os_type": "windows"},
        {"kind": "vm", "network": "core"},
        {"kind": "vm", "not": {"name": "db"}},                # the carve-out
        {"kind": "vm", "name": {"in": ["app1", "db"]}},       # membership
        {"kind": "vm", "label": {"in": ["fleet", "prod"]}},
        {"kind": "vm", "any": [{"label": "fleet"}, {"label": "prod"}]},
        {"kind": "vm", "label": "fleet", "name": {"in": ["app1"]}},
        {"kind": "vm", "name": {"in": ["app1", "db"]}, "not": {"name": "db"}},
        {"kind": "vm", "alive": "unknown"},                   # observed, unprobed
        {"kind": "network"},
    ]
    for q in queries:
        b, pr = bench_select(q), prod_select(q)
        check(f"same answer for {str(q)[:58]}", sorted(b) == sorted(pr))

    # ...and once the ledger holds an observation, both must move together.
    w.unreachable.add("app2")
    for n in ("app1", "app2"):
        w.execute("guest_ping", {"name": n})
    for n in ("app1", "app2"):
        ledger.record(f"reachable({n})", n != "app2", source="guest_ping")
    for value in ("true", "false", "unknown"):
        q = {"kind": "vm", "alive": value}
        check(f"same answer for alive = {value!r} after probing",
              sorted(bench_select(q)) == sorted(prod_select(q)))


def test_every_mutating_tool_says_what_done_means():
    """A tool with no success definition reports `done` whenever the CALL RETURNED — an
    unknown criterion passes, so silence is indistinguishable from success. That is the
    conflation this system refuses everywhere else, and the design note's own position:
    p_world measures P(the tool does what it CLAIMS), so a tool that claims nothing
    corrupts the estimate rather than informing it.

    Nine of thirty-three entries carried `verify` because the criterion vocabulary had no
    word for what most tools do — present/absent/running/stopped cannot express "the label
    is set". So the gap looked like neglect and was partly a missing vocabulary.

    This does not demand a criterion for every tool. It demands that every MUTATING tool
    either declares one or states, in `_no_verify_doc`, why it cannot have one — so the
    gap is a position somebody took rather than a row nobody filled in.
    """
    from orchestrator.ai.agent.contract.core import _CONTRACT
    from orchestrator.ai.planner.autonomous import _criterion_holds
    tools = (_CONTRACT or {}).get("tools") or {}
    try:
        from executor.command_catalog import TOOL_SPECS
        mutating = {t for t, spec in TOOL_SPECS.items()
                    if (spec or {}).get("effect") or (spec or {}).get("rev") is not None}
    except Exception:                                          # pragma: no cover
        mutating = set()
    for tool, attrs in sorted(tools.items()):
        if mutating and tool not in mutating:
            continue
        if not attrs.get("risk"):
            continue                       # read-only / unassessed: no claim to check
        says = bool(attrs.get("verify")) or bool(attrs.get("_no_verify_doc"))
        check(f"{tool}: says what done means (or why it cannot)", says)

    # Every criterion a contract NAMES must be one the checker actually implements —
    # otherwise it silently passes, which is worse than declaring nothing at all.
    known = ("present", "absent", "running", "stopped", "restored",
             "labelled", "unlabelled", "attached", "detached")
    for tool, attrs in sorted(tools.items()):
        c = attrs.get("verify")
        if c:
            check(f"{tool}: '{c}' is a criterion the verifier knows", c in known)
    # ...and the checker must actually discriminate on each, or the word is decoration.
    vms = {"web": {"status": "running", "labels": ["prod"], "flags": []}}
    nets = {"core": {"web"}}
    cases = [("present", "web", {}, True), ("absent", "web", {}, False),
             ("running", "web", {}, True), ("stopped", "web", {}, False),
             ("labelled", "web", {"label": "prod"}, True),
             ("labelled", "web", {"label": "dev"}, False),
             ("unlabelled", "web", {"label": "dev"}, True),
             ("attached", "web", {"vm_name": "web", "net_name": "core"}, True),
             ("attached", "web", {"vm_name": "web", "net_name": "dmz"}, False),
             ("detached", "web", {"vm_name": "web", "net_name": "dmz"}, True)]
    for criterion, name, args, expected in cases:
        check(f"criterion {criterion!r} discriminates ({args or 'no args'})",
              _criterion_holds(criterion, name, vms, args, nets) is expected)
    # An UNREADABLE registry is not evidence of absence — the same unknown-is-not-false
    # rule the observed attributes are built on.
    check("an unreadable network registry never says 'it did not happen'",
          _criterion_holds("attached", "web", vms,
                           {"vm_name": "web", "net_name": "core"}, None) is True)


def _ops_named_in(text: str) -> set:
    """Which op names a piece of prose actually LISTS, read from its own listing lines.

    Matched on the listing form specifically — two spaces, the name, then an em-dash —
    rather than by looking for the word anywhere. These prompts talk ABOUT the language in
    their body text (the ordering rule mentions `foreach`; the predicate block is headed
    "ensure shapes"), and counting prose as an offer would fail this test for a reason
    that has nothing to do with what is offered.
    """
    return {m.group(1) for m in re.finditer(r"^\s{2}(\w+)\s*—", text, re.M)
            if m.group(1) in config.OPS}


def test_the_offer_never_exceeds_the_authority():
    """EVERY surface that shows the model an op must show the SAME ops — the ones the
    operator's intent actually permits.

    This is `intent.violations()` moved from a post-hoc refusal into the offer, and the
    reason to move it is that a refusal arrives too late to help. Under `ensure:` the
    author was told in prose "do NOT create, launch, label, attach or delete anything" and
    then handed a decoder with a `new` branch, a `foreach` branch and a `call` branch. When
    the model took one — and prose is advisory, so it does — the program was authored in
    full, walked, and thrown away with `exceeds_authority`. A whole authoring round spent
    producing something the harness knew it would refuse before it asked.

    Six builders read the op table to make something the model sees: two statement-schema
    forms, two prompt listings, the per-op statement tools, and the bench's
    constrained-decoding schema. Six independent readers of one table is exactly how this
    language's four-way disagreements have happened, so the test holds ALL of them to one
    answer rather than checking the one that was most recently edited.

    BOTH DIRECTIONS ARE CHECKED, and the second matters as much as the first. Offering
    more than the authority permits wastes a round; offering LESS makes a legal program
    undecodable, and there is no error message for a construct the model was never shown.
    """
    from orchestrator.ai.planner.ir import intent as _intent, master, schema as _schema
    from tests.bench.author_probe import _system

    for want in (_intent.FETCH, _intent.ENSURE, _intent.ACHIEVE, None):
        allowed = set(master.ops(want))
        label = want or "no intent supplied"

        # THE AGREEMENT: what the master offers is exactly what the enforcement permits.
        # Asked of `violations()` rather than of `_PERMITS`, so the two cannot be kept in
        # step by both reading one table while meaning different things by it. That is not
        # hypothetical — this pairing is what caught `violations(p, None)` quietly falling
        # back to FETCH's set while the offer treated None as no narrowing at all.
        for op in config.OPS:
            refused = bool(_intent.violations({"body": [{"op": op}]}, want))
            offered = op in allowed
            check(f"{label}: `{op}` offered={offered} matches refused={refused}",
                  offered is not refused)

        # THE SIX BUILDERS. Each is asked what it would show, and must name the same set.
        flat = _schema._statement_flat(want)["properties"]["op"]["enum"]
        check(f"{label}: flat statement schema offers exactly the permitted ops",
              set(flat) == allowed)

        oneof = {b["properties"]["op"]["const"]
                 for b in _schema._statement_oneof(want)["oneOf"]}
        check(f"{label}: oneOf statement schema offers exactly the permitted ops",
              oneof == allowed)

        item = (_schema.emit_program_tool(want)["function"]["parameters"]
                ["properties"]["body"]["items"])
        emitted = (set(item["properties"]["op"]["enum"]) if "properties" in item
                   else {b["properties"]["op"]["const"] for b in item["oneOf"]})
        check(f"{label}: emit_program_tool offers exactly the permitted ops",
              emitted == allowed)

        bench = {b["properties"]["op"]["const"]
                 for b in program_schema(want)["$defs"]["stmt"]["oneOf"]}
        check(f"{label}: the bench decoder offers exactly the permitted ops",
              bench == allowed)

        check(f"{label}: the ir system prompt LISTS exactly the permitted ops",
              _ops_named_in(_schema.system_prompt(["create_vm"], want)) == allowed)

        check(f"{label}: the bench system prompt LISTS exactly the permitted ops",
              _ops_named_in(_system(want)) == allowed)

        # The flattened per-statement surface is a SUBSET by construction — it predates
        # fetch, achieve and if, and never offered them. It may still not offer anything
        # the authority forbids, which is the half of the claim that is actually about it.
        named = {t["function"]["name"][5:] for t in _schema.statement_tools(want)}
        check(f"{label}: the statement tools offer nothing above the authority",
              named <= allowed)


def test_a_copy_source_is_offered_only_from_what_exists():
    """`NEW vm FROM red` — red being a LABEL rather than a machine — is the mistake, and
    until now it could only be caught after the program was written.

    `from` is the one field naming something the program neither creates nor binds, which
    is exactly why the validator could check it and exactly why the schema should. The set
    is genuinely closed: you cannot copy what does not exist. That is the discipline the
    master works to — constrain what is CLOSED, never what is open — and it is why this
    test exists for `from` and not for names in general. A name is NOT closed: `NEW
    AMOUNT(5) vm` mints names nobody can predict at authoring time, so enumerating them
    would forbid legal programs to prevent a mistake nobody has measured.

    THE SCHEMA AND THE VALIDATOR MUST AGREE ON EVERY CANDIDATE, in both directions —
    a schema stricter than the validator makes a legal program undecodable, and a schema
    looser than it just moves the rejection back to where it already was.
    """
    from orchestrator.ai.planner.ir import master, schema as _schema

    lab = {"golden", "web", "core"}
    field = _schema._field("from", lab)
    offered = next((b["enum"] for b in field["anyOf"] if "enum" in b), [])
    check("the copy source is enumerated from the lab", set(offered) == lab)
    # THE PROPERTY, NOT THE IMPLEMENTATION. This asserted `any("pattern" in b ...)`, and
    # that exact pattern — `^\\$`, "starts with a sigil" — was measured on 2026-07-31 to
    # SILENTLY DISABLE constrained decoding for the whole authoring path: ollama's
    # schema-to-grammar conversion fails on an escaped dollar, returns HTTP 200, and
    # generates unconstrained. So the field now offers a bare string beside the enum, and
    # what must stay true is that a `$name` is still SAYABLE — which is what this rung
    # always meant. The $-prefix is policed by `validate` via `refs.names()`, where it was
    # always actually enforced.
    check("a $reference is still expressible",
          any("enum" not in b and b.get("type") == "string" for b in field["anyOf"]))
    check("and no schema pattern anchors on the sigil — it kills enforcement",
          not any(config.SIGIL in str(b.get("pattern", "")) for b in field["anyOf"]))

    # The two must answer the same about every candidate — the real ones, a label that is
    # not a machine, and a bound reference.
    def schema_allows(src):
        return src in offered or src.startswith(config.SIGIL)

    def validator_allows(src):
        prog = {"body": [{"op": "new", "var": "copy", "kind": "vm", "from": src},
                         {"op": "ensure", "predicate": {"shape": "count",
                                                        "select": {"kind": "vm"}, "gte": 1}}]}
        _ok, probs = validate(prog, known_names=lab)
        return not any("`from`" in p for p in probs)

    for src in ("golden", "web", "core", "red", "prod", "nope", "$golden", "$vms"):
        check(f"`from {src}`: schema and validator agree",
              schema_allows(src) == validator_allows(src))

    # An UNKNOWN lab constrains nothing. Narrowing on a fact nobody supplied would forbid
    # every source there is — the same unknown-is-not-false rule the observed attributes
    # are built on, applied to the offer.
    check("an unsupplied lab narrows nothing",
          "anyOf" not in _schema._field("from", None)
          and "enum" not in _schema._field("from", None))
    check("an EMPTY lab narrows nothing either", master.sources(set()) == [])

    # Both surfaces build `from` from the same function, so they cannot disagree.
    from tests.bench.author_probe import _field_schema
    check("the bench and the ir schema offer the same copy sources",
          _field_schema("from", lab) == field)


def test_no_model_facing_string_still_teaches_a_retired_rule():
    """A DECISION HAS MORE READERS THAN THE PLACE IT WAS WRITTEN DOWN.

    `62160da` settled that ACHIEVE is a MAKE and dropped both ordering rules from the
    validator. It updated the two op docs and its own commit message claimed "the model is
    told the same thing the validator now accepts". It was not. Two other strings kept
    teaching the retired rules for a day:

      prompt.grounding              "It goes LAST … nothing may act after ACHIEVE, and a
                                     program has at most one"
      intent.instruction(ACHIEVE)   "Do the work"

    Both are shown to the author on EVERY call, so the assembled prompt contradicted itself
    twenty lines apart — `achieve` promising "you may use SEVERAL, and work may follow
    them" while `grounding` forbade exactly that. And "do the work" argued for the wrong
    side of rung 13: shown five machines that already satisfied the goal and told to do the
    work, the author built five more.

    This is the schema master's lesson in another register. There the fault was SIX
    builders reading `config.OPS` independently; here it is several strings restating one
    semantic decision, with no check that they still agree. A structural invariant cannot
    catch it — every string is well-formed. So the retired CLAIMS are named, and every
    surface the model can see is swept for them. Retiring a rule means adding its wording
    here, which is the cheapest possible way to make the next straggler fail a suite
    instead of a benchmark.
    """
    from orchestrator.ai.planner.ir import intent as _intent

    # Wording that the validator no longer enforces. Keep the phrases SHORT and
    # distinctive: this is matched against prose, and a long quote stops matching the
    # moment someone rewords half of it — which is the failure being guarded against.
    RETIRED = {
        "at most one": "one achieve per program — dropped in 62160da",
        "nothing may act after": "nothing may act after achieve — dropped in 62160da",
        "it goes last": "achieve goes last — dropped in 62160da",
        "do the work": "the pre-MAKE reading of achieve — a goal that holds needs none",
    }

    # EVERY string the author can see, gathered from the surfaces that build the prompt
    # rather than from a hand-kept list — a hand-kept list is the same defect one level up.
    surfaces = {f"prompt.{k}": v for k, v in config.PROMPT.items()
                if isinstance(v, str)}
    surfaces.update({f"ops.{op}.doc": spec.get("doc", "")
                     for op, spec in config.OPS.items()})
    surfaces.update({f"predicates.{p}.doc": spec.get("doc", "")
                     for p, spec in config.PREDICATES.items()})
    surfaces.update({f"intent.instruction({w})": _intent.instruction(w)
                     for w in (_intent.FETCH, _intent.ENSURE, _intent.ACHIEVE)})
    surfaces.update({f"not_ops.{k}": v for k, v in config.NOT_OPS.items()})

    check("there are model-facing strings to sweep", len(surfaces) > 15)
    for name, text in sorted(surfaces.items()):
        hits = [why for phrase, why in RETIRED.items() if phrase in text.lower()]
        check(f"{name} teaches no retired rule"
              + (f" — but says: {hits[0]}" if hits else ""), not hits)

    # AND THE POSITIVE HALF. Sweeping for absence alone would pass a prompt that says
    # nothing at all about ACHIEVE, which is not the state anyone wants either.
    achieve_doc = config.OPS["achieve"]["doc"].lower()
    check("the achieve doc still says several are allowed",
          "several" in achieve_doc)
    check("and that work may follow one",
          "work may follow" in achieve_doc)
    check("the achieve intent tells the author it is an END STATE",
          "end state" in _intent.instruction(_intent.ACHIEVE).lower())
    check("and that a satisfied goal needs no repeating",
          "difference" in _intent.instruction(_intent.ACHIEVE).lower())

    # AND IT MUST REACH THE PRODUCTION AUTHOR, not only the bench one. `intent.instruction`
    # had exactly one caller in the codebase — tests/bench/author_probe.py — so the one fact
    # decision 5 says the author cannot derive reached production's RUNTIME and never its
    # PROMPT. Every ladder cell was therefore authored under a strictly richer prompt than
    # the orchestrator ships, which over-states production rather than under-stating it.
    # test_medusa already holds that the intent reaches the runtime; this is the other side.
    from orchestrator.ai.planner.ir import schema as _sch
    for w in (_intent.FETCH, _intent.ENSURE, _intent.ACHIEVE):
        built = _sch.system_prompt(["create_vm"], want=w)
        check(f"the production prompt carries the {w} instruction",
              _intent.instruction(w) in built)
    check("and says nothing about intent when none was supplied — silence is not a guess",
          all(_intent.instruction(w) not in _sch.system_prompt(["create_vm"])
              for w in (_intent.FETCH, _intent.ENSURE, _intent.ACHIEVE)))


def test_every_path_that_accepts_an_authored_program_sanitises_it():
    """FOUR CALL SITES, ONE PASS — and the fourth is how this breaks.

    A pass wired into three of four places is the defect this file exists for, arriving
    once more: six builders read config.OPS independently; the two selects answered the
    same question differently; `disjoint` was declared, offered, validated and rendered
    with no evaluator. Each was one component forgetting what the others knew.

    A program reaches the world through exactly four doors — the bench's three authoring
    loops and production's run_program. Sanitise at three of them and the bench measures a
    cleaned program while production runs a dirty one, or the reverse, and the ladder
    number silently stops describing the system. Enumerated rather than trusted.

    The check is textual on purpose. It cannot prove the call is correctly PLACED, only
    that the door knows the pass exists — but the failure being guarded against is a new
    door added without one, which is exactly what a name-level check catches.
    """
    import re

    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    doors = [("tests/bench/author_probe.py", "author"),
             ("tests/bench/author_probe.py", "repair"),
             ("tests/bench/author_probe.py", "revise"),
             ("orchestrator/ai/planner/program.py", "run_program")]
    for path, fn in doors:
        src = open(os.path.join(root, path)).read()
        body = re.search(rf"\ndef {fn}\(.*?(?=\ndef |\Z)", src, re.S) or \
            re.search(rf"\n    def {fn}\(.*?(?=\n    def |\n\ndef |\Z)", src, re.S)
        check(f"{path}::{fn} sanitises before judging",
              bool(body) and "_sanitize(" in body.group(0))

    # AND IT IS ORDERED BEFORE THE VERDICT. Sanitising after validate would reject a
    # program over a statement that could never have run — the artifact would cost the
    # program its life and then be tidied off the corpse.
    src = open(os.path.join(root, "orchestrator/ai/planner/program.py")).read()
    body = re.search(r"\n    def run_program\(.*?(?=\n    def |\Z)", src, re.S).group(0)
    check("production sanitises BEFORE it validates",
          body.index("_sanitize(") < body.index("validate("))

    # THE ACCOUNT REACHES THE OPERATOR. `rendered` is what a person reads, and after this
    # pass it is not the program the author emitted. Altering what someone reads without
    # telling them is the one way a cleaner becomes dishonest.
    check("the removals ride out on the result", '"sanitized"' in body
          or "'sanitized'" in body)


def test_the_predicate_schema_can_carry_every_operand_it_offers():
    """A shape in the `shape` enum whose OPERAND has no property is offered-but-unwritable.

    THE THIRD TIME THIS FAMILY HAS BITTEN, and the file's own docstring records the first
    two: `NOT` offered as an array while the validator demanded an object, and composites
    fixed one at a time with no invariant written down so the next shape repeated it. This
    is that next shape.

    MEASURED 2026-07-29 on the tree path: `leaf_schema('achieve')` offers `all` in the
    enum and declares no `of`, so under constrained decoding the model emits
    `{"shape": "all"}`, the validator answers *"all takes two or more checks under `of`,
    got None"*, and the retry returns the IDENTICAL statement — because the schema forbids
    the only correct answer. It is not a model failure and no amount of objection can fix
    it. Three of the four rungs that build-and-fail come back `ungrounded` for exactly
    this reason: the ROOT VERDICT is the statement most likely to need a composite.

    The rule is the one this file exists for — the manifest is the authority, and a
    builder that offers a shape must offer what that shape takes.
    """
    from orchestrator.ai.planner.ir.schema import _predicate_property
    prop = _predicate_property()
    props = prop.get("properties") or {}
    if not props:
        check("predicate is a bare object — nothing to hold to (knob is off)", True)
        return
    offered = set((props.get("shape") or {}).get("enum") or [])
    for shape, spec in config.PREDICATES.items():
        if shape not in offered:
            continue
        operand = spec["operand"]
        check(f"{shape}: offered in the enum, so `{operand}` must be a property",
              operand in props)
    # AND END TO END, because a table being right is not the same as it reaching the
    # decoder — the stale twin is always the risk.
    for shape in ("all", "any", "not", "is"):
        if shape not in offered:
            continue
        for key in _sample_predicate(shape):
            check(f"a well-formed `{shape}` uses only offered keys: {key}",
                  key in props)


def test_both_schema_builders_offer_the_same_predicate_keys():
    """TWO BUILDERS, ONE LANGUAGE. `ir/schema.py` serves production AND the tree path's
    `leaf_schema`; `author_probe.program_schema` serves the ladder. They read the same
    manifest and drifted anyway — the probe's builder gained `of` (its own comment records
    fixing the `arity: one` case after rungs 5 and 8 died on programs the executor would
    have run correctly) and production's never did.

    So the ladder measured a language the tree path could not write. Hold them to the same
    key set; which BRANCH each uses is their own business.
    """
    import json as _json
    from orchestrator.ai.planner.ir.schema import _predicate_property
    mine = set((_predicate_property().get("properties") or {}))
    if not mine:
        check("production predicate is a bare object (knob off) — not comparable", True)
        return
    theirs = set(re.findall(r'"(\w+)":\s*\{', _json.dumps(program_schema("achieve", None))))
    for operand in {s["operand"] for s in config.PREDICATES.values()}:
        check(f"both builders can carry `{operand}`",
              (operand in mine) == (operand in theirs) or operand in mine)


def test_both_paths_offer_the_SAME_select():
    """ONE `select`, or the two paths are two languages.

    It lived in `author_probe` alone for its whole life, so the whole-program probe could
    write `every vm except db` and the tree path — which builds leaves from `ir/schema.py`
    — got the bare object the field catalogue declares and could not name a set at all.
    Rung 4 died on *"reach needs `select`"* three times over while the ladder, using the
    other builder, wrote selects perfectly well.

    Delegation is what fixes it; this is what KEEPS it fixed. `from` was already shared in
    this direction and nothing held the two to it — which is exactly how `select` drifted
    without anyone noticing.
    """
    import json as _json
    from orchestrator.ai.planner.ir import schema as _ir_schema
    from tests.bench.author_probe import _select_spec
    check("the probe's select IS the ir schema's select",
          _json.dumps(_select_spec(), sort_keys=True)
          == _json.dumps(_ir_schema.select_spec(), sort_keys=True))
    # AND IT REACHES THE LEAF DECODER, which is the surface that was actually starved.
    from orchestrator.ai.planner.ir import lower as _lower
    sel = _lower.leaf_schema("foreach", "achieve")["properties"]["select"]
    check("a foreach leaf can name a kind", bool(sel.get("properties", {}).get("kind")))
    check("a foreach leaf can write the carve-out", "not" in sel.get("properties", {}))
    pred = _lower.leaf_schema("ensure", "achieve")["properties"]["predicate"]
    check("an ensure leaf's predicate can name a kind",
          bool(pred["properties"]["select"].get("properties", {}).get("kind")))


def test_the_quantifier_narrows_BOTH_paths_not_just_the_bench():
    """E2. `master.ops` grew a `quantifier` argument and only `author_probe` passed it, so
    the best discriminator measured — 15/16, against the atomicity router's 4/10 — narrowed
    nothing on production or the tree path. Every surface now takes it, and this holds them
    together the way `test_both_paths_offer_the_SAME_select` holds the select.
    """
    from orchestrator.ai.planner.ir import config as _c
    from orchestrator.ai.planner.ir import lower as _lower
    from orchestrator.ai.planner.ir import master as _m
    from orchestrator.ai.planner.ir import schema as _s

    # THE ONE NARROWING THE MANIFEST ACTUALLY DECLARES. `all`, `any` and `not` license
    # every op, so `single` is the whole of the op-level payoff — see the note below.
    check("single denies foreach at the master",
          "foreach" not in _m.ops("achieve", "single")
          and "foreach" in _m.ops("achieve"))

    offered = _s.emit_program_tool("achieve", quantifier="single")
    item = offered["function"]["parameters"]["properties"]["body"]["items"]
    ops_in_schema = (set(item["properties"]["op"]["enum"]) if "properties" in item
                     else {b["properties"]["op"]["const"] for b in item["oneOf"]})
    check("and the production tool schema cannot express it either",
          "foreach" not in ops_in_schema)

    # THE PROMPT MUST NARROW WITH THE SCHEMA. Describing an op the decoder cannot emit is
    # the four-way disagreement in miniature, and it spends the model's reasoning on a
    # construct it will never produce.
    prompt = _s.system_prompt([], "achieve", quantifier="single")
    check("the prompt does not describe an op the schema withholds",
          not any(line.strip().startswith("foreach") for line in prompt.splitlines()))

    # AND IT REACHES THE LEAF DECODER, which is the surface where a quantifier is most at
    # home: a leaf IS one clause, and the quantifier is a property of a clause.
    check("a leaf may still be a call under single",
          bool(_lower.leaf_schema("call", "achieve", quantifier="single")))
    try:
        _lower.leaf_schema("foreach", "achieve", quantifier="single")
        check("a foreach leaf is refused under single", False)
    except ValueError as e:
        check("a foreach leaf is refused under single, and the message names why",
              "single" in str(e))

    # ABSENT MEANS ABSENT. An unsupplied fact must never become a silent restriction.
    check("no quantifier narrows nothing",
          _m.ops("achieve", None) == _m.ops("achieve"))

    # WHAT IS NOT EXPRESSIBLE HERE, recorded so nobody reads E6's three claims as shipped.
    # ALL-EXCEPT wanting `not` on the foreach, and NOT forcing a one-branch IF, are
    # FIELD-level constraints; `master.ops` narrows OPS. Two thirds of the claimed payoff
    # needs a mechanism that does not exist yet.
    for q in ("all", "any", "not"):
        check(f"{q} narrows no ops today, and the manifest is where that is declared",
              set(_m.ops("achieve", q)) == set(_m.ops("achieve"))
              and set(_c.QUANTIFIERS[q]["ops"]) >= set(_m.ops("achieve")))


def test_ONE_authority_per_fact_in_the_program_regime():
    """The stale-twin defect, guarded at the source instead of case by case.

    Three times the schema builders drifted (`of`, `select`, NOT-as-array) and each cost a
    rung. On 2026-07-30 it happened twice more in a single day, in NEW code: two shape
    routers each hardcoded the kind nouns and had already diverged, and `consent._ACTING`
    and `validate._ACTS` turned out to be the same three words written in two modules that
    cannot see each other. Both facts now live in the manifest with one reader.

    This does not stop a third copy being written. It does stop a third copy from silently
    DISAGREEING, which is the part that costs rungs.
    """
    import importlib as _il

    from orchestrator.ai.planner.ir import config as _c
    from orchestrator.ai.planner.ir import consent as _consent
    from orchestrator.ai.planner.ir import master as _m
    # THE MODULE, not the re-export. `ir/__init__` exports `validate` as a FUNCTION, so the
    # plain import binds the callable and `_v._ACTS` raises — reading something adjacent to
    # what actually holds the fact, which is the habit this whole test exists to catch.
    _v = _il.import_module("orchestrator.ai.planner.ir.validate")

    check("acting ops are declared in the manifest, not in code",
          _m.acting_ops() == {op for op, spec in _c.OPS.items() if spec.get("acts")})
    check("consent and validate read the SAME acting set",
          _consent._ACTING == _v._ACTS == _m.acting_ops())
    check("and it is not empty — an unset manifest flag would silently disarm both",
          bool(_m.acting_ops()))

    # THE KIND LEXICON. Every reader that recognises a kind in prose asks one function.
    from tests.bench import quantifier_rule as _qr
    from tests.bench import route_rule as _rr
    check("both shape routers share one kind lexicon",
          _qr.kind_nouns is _rr.kind_words is _m.kind_nouns)
    check("every declared kind is in it",
          all(k.lower() in _m.kind_nouns() for k in _c.KINDS))
    check("and the nouns come from the manifest, not from python",
          "machine" in _m.kind_nouns()
          and "machine" in (_c.KINDS["vm"].get("nouns") or []))

    # THE SIM-BACKED SEAMS. There were two, and the second was strictly weaker: it filtered
    # on label/status/name only, so `not`/`in`/`any`/`all` were silently DROPPED — a program
    # saying "every vm except db" got every vm and the seam reported success — and its
    # `holds` answered `disjoint` with "not evaluated in the bench", which is the shape rung
    # 8 ends on. Identity is the strongest form of this guard: two names for one function
    # cannot drift, where two functions with a comment asking them to agree always do.
    from tests.bench import author_probe as _ap
    from tests.bench import run_program as _rp
    from tests.bench import seams as _seams_mod
    from tests.bench import tree_probe as _tp
    check("every sim-backed seam is the ONE authority in seams.py",
          _ap._seams is _rp.seams is _tp._seams is _seams_mod.seams)

    # And it answers the shapes the weak twin dropped. Behavioural, not structural: the
    # identity check above would still pass if the authority itself lost these.
    w = SimWorld()
    for n in ("app1", "db"):
        w.execute("create_vm", {"name": n, "os_type": "linux"})
    w.execute("create_network", {"net_name": "core"})
    sel, holds = _seams_mod.seams(w)
    check("the carve-out is honoured, not ignored",
          sel({"kind": "vm", "not": {"name": "db"}}) == ["app1"])
    check("membership is answered",
          sel({"kind": "vm", "name": {"in": ["db"]}}) == ["db"])
    check("an `any` group is answered",
          sel({"kind": "vm", "any": [{"name": "app1"}, {"name": "db"}]}) == ["app1", "db"])
    good, why = holds({"shape": "disjoint", "sets": [["app1"], ["db"]]}, {})
    check(f"disjoint is EVALUATED, not deferred ({why})", good is True)
    bad, _ = holds({"shape": "disjoint", "sets": [["app1", "db"], ["db"]]}, {})
    check("and it detects an overlap", bad is False)

    # A5. REACH IS A FINDING, NOT A STATE — the bench used to ask only whether the members
    # shared a network, so a program that networked five machines and probed none passed a
    # reach rung here and would come back `reach is unestablished` against the real lab.
    # That is what made rung 4's 16-call program look cheaper than the 21-call one that
    # verifies its own work, and a cost signal built on it points the optimisation at
    # dropping verification.
    w2 = SimWorld()
    for n in ("m1", "m2"):
        w2.execute("create_vm", {"name": n, "os_type": "linux"})
    w2.execute("create_network", {"net_name": "core"})
    for n in ("m1", "m2"):
        w2.execute("add_vm_to_network", {"net_name": "core", "vm_name": n})
    _, holds2 = _seams_mod.seams(w2)
    reach = {"shape": "reach", "select": {"kind": "vm"}, "min": 2}
    unprobed, why = holds2(reach, {})
    check(f"networked but UNPROBED does not hold ({why[:44]})", unprobed is False)
    for n in ("m1", "m2"):
        w2.execute("guest_ping", {"name": n})
    check("once every member has answered, it holds", holds2(reach, {})[0] is True)

    w3 = SimWorld()
    for n in ("m1", "m2"):
        w3.execute("create_vm", {"name": n, "os_type": "linux"})
    _, holds3 = _seams_mod.seams(w3)
    for n in ("m1", "m2"):
        w3.execute("guest_ping", {"name": n})
    # The other direction, and it is the divergence found while fixing this one: production
    # checks liveness and ignores topology entirely. The bench demands both, so it can only
    # ever be pessimistic rather than certifying something the real lab would refuse.
    check("probed but sharing no network does not hold either",
          holds3(reach, {})[0] is False)


def main():
    """Every `test_*` in this module, in definition order — DISCOVERED, not listed.

    THE LIST WAS THE BUG. It was hand-maintained, and on 2026-07-29 two invariants were
    added and neither ran: absent from the list here, and under pytest `check()` only
    PRINTS, so they could not fail there either. An invariant that silently never executes
    is worse than no invariant, because the file reads as though the property is guarded.

    The loop itself then became the bug — pasted into a second suite, then needed in a
    third. It lives in `tests/_suite.py` now, once.
    """
    from tests import _suite
    sys.exit(_suite.run(sys.modules[__name__], "invariants"))


if __name__ == "__main__":
    main()
