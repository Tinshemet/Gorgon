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
    for branch in program_schema()["$defs"]["stmt"]["oneOf"]:
        props = branch.get("properties", {})
        if "select" in props and props["select"].get("properties"):
            return props["select"]["properties"]
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
    check("a $reference is still expressible",
          any("pattern" in b for b in field["anyOf"]))

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


def main():
    for fn in (test_every_predicate_shape_has_an_evaluator,
               test_every_predicate_shape_renders_legibly,
               test_every_predicate_shape_declares_whether_it_can_be_derived,
               test_every_op_is_accounted_for,
               test_the_visitor_does_not_silently_ignore_a_statement,
               test_every_queryable_attribute_is_offered_to_the_author,
               test_every_closed_vocabulary_is_both_offered_and_policed,
               test_every_predicate_shape_is_offered_to_the_author,
               test_every_kind_names_real_tools,
               test_every_observed_attribute_is_actually_learnable,
               test_bindable_names_are_exactly_readable_names,
               test_the_surface_spells_every_word_it_owns,
               test_the_two_selects_answer_the_same_question,
               test_every_mutating_tool_says_what_done_means,
               test_the_offer_never_exceeds_the_authority,
               test_a_copy_source_is_offered_only_from_what_exists):
        print(f"\n── {fn.__name__}")
        fn()
    print(f"\n{_PASS}/{_PASS + _FAIL} passed")
    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
