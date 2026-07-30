"""
schema.py — the tool the model fills in to produce a program.

BUILT FROM THE MANIFEST, not written out. The op names come from `ops`, the predicate
shapes from `predicates`, every sentence from `prompt`. Adding an op or a predicate to
the JSON changes what the model is offered, with no edit here.

There is no parser anywhere in this package, and that is the point: the model CALLS this
tool and the statements arrive as validated JSON arguments. `DECOMPOSE_TOOL` is the
working precedent — one schema instead of a lexer and a grammar.

WHAT IS OFFERED IS NOT THIS MODULE'S DECISION. Every builder here takes `want` — the
operator's intent — and asks `master.ops(want)` rather than reading `config.OPS` itself.
The manifest still says what the language HAS; the master says what this particular
request may be shown, and the two are different questions. `want=None` narrows nothing,
so an absent fact never becomes a silent restriction.
"""

from typing import Any, Dict, List, Optional, Sequence

from . import config, master
from . import methods as _methods


def select_spec(depth: int = 1) -> Dict[str, Any]:
    """A select: the kind, whichever attributes that kind declares queryable, membership,
    the `not` carve-out, and the `any`/`all` groups.

    MOVED HERE FROM `author_probe` 2026-07-29, because it was only ever offered on ONE of
    the two paths. `ir/schema.py` serves production AND `lower.leaf_schema`, and on both of
    them `select` was the bare object the field catalogue declares — no kind, no
    attributes, no enums, no carve-out. So the tree path could not write a select that
    named anything, and rung 4 died three times on *"reach needs `select` — the set to
    measure"* while the whole-program probe wrote selects perfectly well.

    `from` was already delegated the other way, with the reason stated: *"shared with the
    ir schema so the two surfaces cannot answer differently."* This is that seam widened.

    The history it carries, all of it earned the same way — the language HAD the construct
    and the schema withheld it, and the model got the blame:

      * `not` was implemented in the validator and never offered, so "every vm except db"
        could not be said; the author invented `name: '!db'` and was marked down for it.
      * closed vocabularies are ENUMS or the decoder invents values — `status = 'not
        running'` matched nobody and ran zero calls; `label = 'up'` was reached for
        because nothing said what `status` could be.
      * membership is offered on every attribute, or a predicate can never speak about
        particular machines and the author invents four syntaxes for it in one day.

    Depth-limited: a carve-out inside a carve-out is a double negative nobody should write.
    """
    props: Dict[str, Any] = {"kind": {"type": "string", "enum": list(config.KINDS)}}
    for kind, k in config.KINDS.items():
        observed = config.observed(kind)
        for attr in list(k["attrs"]) + list(observed):
            if attr in props:
                continue
            spec: Dict[str, Any] = {"type": "string"}
            values = config.values_for(kind, attr)
            if values:
                spec["enum"] = values
            obs = observed.get(attr)
            if obs:
                # An observed attribute says where its answer comes from, because the
                # third value is only usable if the author knows what fills it in.
                spec["description"] = (
                    f"{obs.get('doc', attr)} '{config.OBSERVED_UNKNOWN}' means nothing "
                    f"has asked yet — call {obs.get('by', 'a probe')} first.")
            props[attr] = spec
    for attr in [a for a in props if a != "kind"]:
        scalar = props[attr]
        props[attr] = {"anyOf": [
            scalar,
            {"type": "object",
             "properties": {"in": {"anyOf": [
                 {"type": "array", "items": {"type": "string"}, "minItems": 1},
                 {"type": "string", "description": "a $set bound by fetch"}]}},
             "required": ["in"],
             "description": f"{attr} is ANY of these — written INCLUDE {attr} = [a, b, c]"}]}
    if depth > 0:
        inner = {a: v for a, v in props.items() if a != "kind"}
        props["not"] = {"type": "object", "properties": inner,
                        "minProperties": 1,
                        "description": "EXCLUDE members matching these filters, e.g. "
                                       "{\"name\": \"db\"} for 'every vm except db'"}
        for group, word in (("any", "OR"), ("all", "AND")):
            props[group] = {"type": "array", "minItems": 2,
                            "items": {"type": "object", "properties": inner,
                                      "minProperties": 1},
                            "description": f"filter sets combined with {word}"}
    return {"type": "object", "properties": props, "required": ["kind"]}


def _predicate_property() -> Dict[str, Any]:
    """The `predicate` field's schema.

    MEASURED, and the reason `schema.predicate_properties` exists as a knob: with
    `predicate` typed only as a bare object the model returned it EMPTY every time,
    while `select` — which carries a worked example — filled correctly in the same
    programs. Declaring properties fixed that. Adding a nested `required` on top made it
    stop calling the tool AT ALL (3/4 emitting went to 0/4): this tool-call surface has a
    complexity ceiling, and the bake-off already found tool-calling fidelity, not
    reasoning, to be the binding constraint. Both knobs default accordingly.

    `of` WAS MISSING, AND FOUR OF SEVEN SHAPES WERE OFFERED-UNDESCRIBED (2026-07-29).
    `not`, `all`, `any` and `is` all take their operand under `of`; the `shape` enum
    offered every one of them and no `of` property existed. The model emitted
    `{"shape": "all"}`, the validator answered *"all takes two or more checks under `of`,
    got None"*, and the retry came back BYTE-IDENTICAL. It cost the tree path its ROOT
    VERDICT on three rungs, which is why they scored `ungrounded`. The probe's builder had
    grown `of` and this one had not — the stale twin, again.

    WHAT IS MEASURED IS THAT DECLARING IT FIXED IT — `ungrounded` cleared on two of the
    three rungs at n=3. WHY is NOT established, and the tempting explanation is wrong:
    an undeclared key is not necessarily ungrammatical here, since `select` is a bare
    object on this path and selects with contents do get emitted. So read this as *the
    schema never described the operand, so the model never wrote it*, not as *the grammar
    forbade it*. The distinction matters for the remaining `select` gap.

    NESTING STOPS AT ONE LEVEL, deliberately. A composite's children are the leaf shapes
    (`count`, `reach`, `disjoint`), which is every verdict the ladder actually needs;
    making `of` recursive would put a self-referencing branch inside the one construct
    already suspected of costing the decoder — and branch count is the measured mechanism
    behind the channel failures, so this is not the place to spend it.
    """
    prop: Dict[str, Any] = {"type": "object", "description": "ensure: what must hold at the end"}
    if not config.SCHEMA.get("predicate_properties"):
        return prop
    comparators = sorted({c for p in config.PREDICATES.values() for c in p["comparators"]})  # dict -> its keys
    props: Dict[str, Any] = {
        "shape":  {"type": "string", "enum": list(config.PREDICATES),
                   "description": "which check"},
        "select": dict(select_spec(),
                       description="the set to measure — same form as foreach's select"),
        "sets":   {"type": "array", "items": {"type": "string"},
                   "description": "disjoint: the sets to compare"},
    }
    for c in comparators:
        props[c] = {"type": "integer", "description": f"comparison: {c}"}
    # THE MANIFEST NAMES THE SHAPES, not this module — add a composite to the JSON and it
    # is described here without an edit, which is the claim every other builder makes.
    by_arity = {a: [s for s, p in config.PREDICATES.items()
                    if p["operand"] == "of" and p.get("arity") == a]
                for a in ("value", "one", "many")}
    if any(by_arity.values()):
        inner = {"type": "object", "properties": dict(props),
                 "description": "one check — a leaf shape such as count or reach"}
        forms: List[Dict[str, Any]] = []
        if by_arity["value"]:
            forms.append({"type": "string",
                          "description": f"{'/'.join(by_arity['value'])}: "
                                         f"a $grafted value, e.g. $answer.alive"})
        if by_arity["one"]:
            forms.append(dict(inner, description=f"{'/'.join(by_arity['one'])}: "
                                                 f"the single check this applies to"))
        if by_arity["many"]:
            forms.append({"type": "array", "items": inner, "minItems": 2,
                          "description": f"{'/'.join(by_arity['many'])}: "
                                         f"two or more checks to combine"})
        props["of"] = forms[0] if len(forms) == 1 else {"anyOf": forms}
    # THE RECEIVER, so a method can actually be WRITTEN. A construct the schema never
    # describes is one the model never emits — measured on `of`, whose absence cost the
    # tree path its root verdict on three rungs while every other layer accepted it fine.
    # Medusa classes would have landed in exactly that state: manifest, validator,
    # renderer and executor all agreeing about `$lab.reach()`, and no way to say it.
    #
    # Described from the manifest's own `receivers`, so a kind or method added to the JSON
    # is offered here without an edit.
    _owned = _methods.offered()
    if _owned:
        _spellings = "; ".join(f"a {k} answers {', '.join(ms)}"
                               for k, ms in _owned.items())
        props["on"] = {"type": "string", "pattern": r"^\$[A-Za-z_][A-Za-z0-9_]*$",
                       "description": ("ask this check OF one thing you bound, instead of "
                                       "over a select: {\"shape\":\"reach\",\"on\":\"$lab\"}"
                                       " is $lab.reach(). " + _spellings +
                                       ". A machine answers for itself; a network answers "
                                       "for all of its members.")}
    prop["properties"] = props
    if config.SCHEMA.get("predicate_required"):
        prop["required"] = ["shape"]
    return prop


# HOW A NESTED THING IS REFERRED TO — the ONE respect in which the two surfaces genuinely
# differ. Constrained decoding names a `$defs` entry; a tool-call schema has no `$defs` to
# point at and must inline. Everything else about a field is the same fact on both, which
# is why they are now one builder.
#
# THEY HAD DRIFTED BADLY AND IN ONE DIRECTION, exactly as H2 records. Before 2026-07-30 this
# module's `_field` knew nothing of `amount`'s minus form, `call`'s tool enum, block arrays
# and their minItems, `cond`, the var/graft name pattern, or `in` — SIX constructs the
# bench's builder had grown and production had not. Each was earned by a measured failure
# there and none of them reached the path production and the tree actually use.
DEFS = {"stmt": "#/$defs/stmt", "pred": "#/$defs/pred"}


def _field(name: str, known: Optional[set] = None,
           refs: Optional[Dict[str, str]] = None,
           tools: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """One field's JSON-Schema fragment, from the catalogue. ONE BUILDER, two surfaces.

    `refs` names the `$defs` entries for nested statements and predicates. Passing it gives
    the constrained-decoding form; omitting it inlines, which is what a tool-call schema
    needs. That parameter is the whole of the difference between the two builders that this
    codebase has paid for three times (`of`, `select`, NOT-as-array).
    """
    spec = dict(config.FIELDS[name])
    doc = spec.pop("doc", "")
    src = spec.pop("enum_from", None)

    if name == "from":
        # THE ONE IDENTIFIER SLOT THAT IS GENUINELY CLOSED — you cannot copy what does not
        # exist. The validator always said so and could only say it afterwards.
        return _from_field(doc, known)
    if name in ("select", "count"):
        # `count` is a select in COUNTING POSITION — same query, different answer. Without
        # it `FETCH COUNT(...)` cannot be said at all.
        return dict(select_spec(), description=doc)
    if name in ("cond", "predicate"):
        return {"$ref": refs["pred"]} if refs else _predicate_property()
    if name in ("then", "else", "ifails", "do"):
        # minItems, so the decoder cannot emit an EMPTY branch. It did: rung 11 wrote a
        # correct `IF ... = false { stop_vm }` and preceded it with a dead `IF ... = true
        # { }`, which the validator rejected and which sank an otherwise right program.
        item = {"$ref": refs["stmt"]} if refs else {"type": "object"}
        return {"type": "array", "items": item, "minItems": 1, "description": doc}
    if name == "call":
        # THE TOOL LIST IS INJECTED, not read from the manifest, and that is not an
        # oversight: the bench enumerates its SimWorld's tools while production enumerates
        # the live registry. Absent means an open string rather than an empty enum — an
        # empty one would offer the decoder nothing legal and read as a model failure.
        tool = ({"type": "string", "enum": list(tools)} if tools
                else {"type": "string", "description": "which tool"})
        return {"type": "object",
                "properties": {"tool": tool, "args": {"type": "object"}},
                "required": ["tool", "args"]}
    if name == "amount":
        return {"anyOf": [
            {"type": "integer", "minimum": 0},
            {"type": "string", "description": "a $parameter"},
            {"type": "object", "properties": {
                "minus": {"type": "array", "minItems": 2, "maxItems": 2,
                          "description": "[target, \"$have\"] — create only the shortfall"}},
             "required": ["minus"]}],
            "description": doc}
    if name == "in":
        return {"anyOf": [{"type": "string"},
                          {"type": "array", "items": {"type": "string"}}],
                "description": doc}
    if name in ("var", "graft"):
        # CONSTRAIN THE DECODER, don't diagnose afterwards. `-` cannot appear in a binding
        # name because it composes names ($item-snap); rung 6's paraphrase bound `red-net`
        # in all three samples and then could not read it back.
        return {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                "description": doc + " Letters, digits and underscores only — a name with "
                                     "'-' cannot be referred to."}
    if src:
        return {"type": "string", "enum": list(getattr(config, src.upper())),
                "description": doc}
    if "enum" in spec or not isinstance(spec.get("type"), str):
        t = spec.get("type")
        spec["type"] = t if isinstance(t, str) else "string"
    return {**spec, "description": doc}


def _from_field(doc: str, known: Optional[set]) -> Dict[str, Any]:
    """`from` names something that ALREADY EXISTS, so the lab is its enum.

    The `$ref` branch is not a loophole, it is the other legal form: `NEW vm FROM $golden`
    copies something an earlier statement bound, and `refs.names()` is what the validator
    checks it with. Enumerating without it would forbid the composable case and leave only
    the literal one.
    """
    names = master.sources(known)
    if not names:
        return {"type": "string", "description": doc}
    return {"anyOf": [{"type": "string", "enum": names},
                      {"type": "string", "pattern": f"^\\{config.SIGIL}"}],
            "description": doc + f" It must already exist — one of: {', '.join(names)}."}


def _statement_flat(want: Optional[str] = None, known: Optional[set] = None,
                    quantifier: Optional[str] = None) -> Dict[str, Any]:
    """One object, every field optional, only `op` required.

    Simple for the model to call and structurally useless: a `new` and an `ensure` are
    the same type, so nothing stops `{"op":"new","predicate":{...}}` and nothing prompts
    the model to supply `op` at all. Measured — qwen2.5:14b returned six of nine
    statements with no `op`. Kept as a knob because it is the SIMPLEST schema, and
    simplicity is what emission turned out to be sensitive to.
    """
    props = {"op": {"type": "string", "enum": master.ops(want, quantifier)}}
    for name in config.FIELDS:
        props[name] = _field(name, known)
    return {"type": "object", "properties": props, "required": ["op"]}


def _statement_oneof(want: Optional[str] = None, known: Optional[set] = None,
                     quantifier: Optional[str] = None) -> Dict[str, Any]:
    """One branch per op, so a statement's type determines its fields.

    `op` is a const per branch, which both forces the discriminator to be present and
    tells the model which fields go with it. Built from the same rows as the flat form,
    so the two cannot describe different languages.
    """
    import itertools

    from .validate import _one_of_groups

    branches = []
    for op in master.ops(want, quantifier):
        spec = config.OPS[op]
        props = {"op": {"type": "string", "const": op, "description": spec["doc"]}}
        for name in spec["fields"]:
            props[name] = _field(name, known)
        required = ["op"] + [f for f in spec["required"]]
        # EITHER/OR HAS TO REACH THE DECODER, not only the validator. This surface used to
        # emit ONE branch per op with every alternative optional, so a `foreach` could
        # carry `select` AND `in`, or neither, and mean nothing — the bench's builder
        # learned that the hard way (`FOREACH $item IN None`, five times in one program)
        # and this one never did. One branch per COMBINATION, each dropping the
        # alternatives it did not take, using the same `_one_of_groups` the validator reads
        # so the two cannot disagree about the manifest.
        groups = _one_of_groups(spec)
        if not groups:
            branches.append({"type": "object", "properties": props, "required": required})
            continue
        alternatives = {f for g in groups for f in g}
        for combo in itertools.product(*groups):
            sub = {k: v for k, v in props.items() if k not in alternatives - set(combo)}
            branches.append({"type": "object", "properties": sub,
                             "required": required + list(combo)})
    return {"oneOf": branches}


def emit_program_tool(want: Optional[str] = None, known: Optional[set] = None,
                      quantifier: Optional[str] = None) -> Dict[str, Any]:
    """The tool schema, assembled from the manifest and narrowed by the master.

    `quantifier` narrows the SAME way `want` does and for the same reason — it makes a
    wrong program unrepresentable rather than rejected. It reached only the bench's
    builder until 2026-07-30, so the best discriminator measured (15/16, against the
    atomicity router's 4/10) narrowed nothing on the path production actually uses.
    """
    form = config.SCHEMA.get("statement_form", "oneof")
    item = (_statement_oneof(want, known, quantifier) if form == "oneof"
            else _statement_flat(want, known, quantifier))
    return {
        "type": "function",
        "function": {
            "name": "emit_program",
            "description": config.PROMPT["tool_description"],
            "parameters": {
                "type": "object",
                "properties": {
                    "body": {"type": "array",
                             "description": "The statements, in order.",
                             "items": item},
                },
                "required": ["body"],
            },
        },
    }


def system_prompt(tools, want: Optional[str] = None,
                  quantifier: Optional[str] = None,
                  ops: Optional[Sequence[str]] = None) -> str:
    """What the model needs to know to write a program — ops, kinds, predicates, tools.

    Assembled from the manifest so the prompt cannot drift from what validate() accepts:
    both read the same table. The op LISTING is narrowed by the master for the same reason
    the schema is — a prompt that describes `new` while the decoder cannot emit it is the
    four-way disagreement in miniature, and the model spends its reasoning on a construct
    it will never be able to produce.

    BLINDERS — `ops` narrows the listing to what THIS CALL can actually emit.

    The argument is the one above, taken the rest of the way. Staged lowering already
    narrows the SCHEMA to a single operator (`lower.leaf_schema`), and measured
    2026-07-30 the two had drifted badly apart: a leaf that could only be a `call` got a
    642-character schema and a 7287-character prompt describing all seven operators and
    every predicate. Eleven times more context than the call could use, and six operators
    it had no branch for.

    The decomposer has ALREADY decided the leaf's operator, so this costs no extra model
    call and no guess — the same fact that makes the schema narrow makes the prompt narrow.
    The operator's framing: blinders on a racehorse.

    `None` narrows nothing, so a caller that does not know stays exactly as it was — the
    same rule `want=None` follows, and for the same reason: an absent fact must never
    become a silent restriction.
    """
    p = config.PROMPT
    lines = [p["intro"], "", p["statements_header"]]
    # NARROWED WITH THE SCHEMA, never apart from it. A prompt describing `new` while the
    # decoder cannot emit it is the four-way disagreement in miniature.
    #
    # `ops` is the BLINDER: what this particular call can emit, which the caller already
    # knows on the staged path. Intersected with the master rather than replacing it, so a
    # blinder can only ever narrow — it must not smuggle in an op the operator's intent
    # forbids, which is the one way this could become a hole instead of a saving.
    _offer = master.ops(want, quantifier)
    if ops is not None:
        _offer = [op for op in _offer if op in set(ops)]
    for op in _offer:
        lines.append(f"  {op:8}— {config.OPS[op]['doc']}")
    lines += ["", "  " + p["select_hint"], "",
              "  ensure shapes (each names its `shape` and takes its operand under "
              "`select`, exactly like foreach):"]
    for name, spec in config.PREDICATES.items():
        operand = spec["operand"]
        comps = "/".join(spec["comparators"])
        example = (f'{{"shape":"{name}","{operand}":["$a","$b"]}}' if operand == "sets"
                   else f'{{"shape":"{name}","select":{{"kind":"vm","tag":"x"}},"{comps.split("/")[0]}":N}}')
        lines.append(f"    {example}   — {spec['doc']}")
    # METHODS, or the schema offers a construct nothing tells the author about. That is the
    # `of` defect exactly — described nowhere, so never written, while every other layer
    # accepted it. Listed from the manifest, so a method added to the JSON is described
    # here with no edit.
    for kind, names in _methods.offered().items():
        for name in names:
            # `"on": "$the_network"` and not `"$network"`: a placeholder that looks like a
            # real variable gets COPIED. The doc beside it carries the worked spelling.
            lines.append(f"    a {kind} answers {name}(): "
                         f"{{\"shape\":\"{name}\",\"on\":\"$the_{kind}_you_bound\"}}"
                         f"   — {_methods.doc(kind, name)}")
    lines += ["", p["reference"], p["ordering"], "",
              f"{p['tools_header']} {', '.join(tools)}.", p["tools_footer"]]
    # THE OPERATOR'S INTENT, AND PRODUCTION WAS NOT BEING TOLD IT. `intent.instruction`
    # had exactly ONE caller in the whole codebase — the bench author — so the fact
    # decision 5 says the author CANNOT DERIVE reached production's runtime (`violations`,
    # and now `promote`) and never reached production's AUTHOR.
    #
    # That is the ladder measuring a prompt strictly richer than the shipped one, and it
    # over-states production rather than under-stating it: every recorded cell was authored
    # by a model told "THIS IS A COMMAND ... act on the DIFFERENCE", while the real
    # orchestrator asked for the same program without that sentence. `test_medusa` already
    # holds that the intent must reach the RUNTIME — written because `grep intent
    # tests/bench/` came back empty — and this is the same defect on the other side.
    #
    # Appended here rather than by each caller, so a second caller cannot forget it, which
    # is exactly how it came to be missing in the first place.
    if want:
        from . import intent as _intent
        lines += ["", _intent.instruction(want)]
    return "\n".join(lines)


# ── authoring mode: one tool per statement ──────────────────────────────────────
#
# The whole-program tool asks for an array of structured objects, and that is the shape
# emission fails on. These ask for what the model demonstrably CAN produce: a call with a
# handful of scalar arguments, exactly like create_vm(name=alpha). The harness assembles
# the program from the sequence of calls, so the IR is unchanged — only the way it is
# obtained differs.
#
# Nested objects are flattened for the same reason. `select {kind, label}` becomes three
# scalars, because a nested object inside a tool argument is the other thing that broke.

_STATEMENT_TOOLS = {
    "new": {
        "doc": "Create resources and bind a name to them. Use for 'create N vms'.",
        "props": {
            "var":   ("string",  "the name to bind, e.g. 'vms'"),
            "kind":  ("string",  "the resource type"),
            "amount": ("integer", "how many to create (omit for 1)"),
        },
        "required": ["var", "kind"],
    },
    "call": {
        "doc": "Invoke ONE tool once.",
        "props": {
            "tool": ("string", "the tool name"),
            "args": ("object", "the tool's arguments"),
        },
        "required": ["tool", "args"],
    },
    "foreach": {
        "doc": ("Apply one tool to EVERY member of a set. Name the set either by "
                "querying state (select_kind [+ select_attr/select_value]) or by a set "
                "you already bound (in_var). The member is $item."),
        "props": {
            "select_kind":  ("string", "query: the resource type, e.g. 'vm'"),
            "select_attr":  ("string", "query: attribute to filter on, e.g. 'label'"),
            "select_value": ("string", "query: the value it must have"),
            "in_var":       ("string", "or: a set already bound, e.g. '$vms'"),
            "tool":         ("string", "the tool to apply to each member"),
            "args":         ("object", "its arguments; use $item for the member"),
        },
        "required": ["tool", "args"],
    },
    "ensure": {
        "doc": "State something that must be TRUE at the end. A check, not an action.",
        "props": {
            "shape":        ("string", "count, reach or disjoint"),
            "select_kind":  ("string", "the resource type to measure"),
            "select_attr":  ("string", "attribute to filter on"),
            "select_value": ("string", "the value it must have"),
            "amount":       ("integer", "the number to compare against"),
            "compare":      ("string", "eq, gte, lte or min"),
            "sets":         ("string", "disjoint: comma-separated, e.g. '$a,$b'"),
        },
        "required": ["shape"],
    },
}


def statement_tools(want: Optional[str] = None,
                    quantifier: Optional[str] = None) -> List[Dict[str, Any]]:
    """One tool per op — flat, scalar, and small enough to actually get called.

    NOTE THE GAP, which narrowing by intent is what made visible: `_STATEMENT_TOOLS` above
    covers new/call/foreach/ensure and predates `fetch`, `achieve` and `if`. So a `fetch`
    intent narrows this surface to NOTHING. That is the honest answer — this surface cannot
    serve a retrieval — and a caller must read [] as "not offerable here", never as "no
    statements are permitted". Papering over it by handing back the unnarrowed set would
    offer `new` to an operator who asked to be told something.
    """
    offered = set(master.ops(want, quantifier))
    out = []
    for op, spec in _STATEMENT_TOOLS.items():
        if op not in offered:
            continue
        props = {n: {"type": t, "description": d} for n, (t, d) in spec["props"].items()}
        if op == "new":
            props["kind"]["enum"] = list(config.KINDS)
        if op == "ensure":
            props["shape"]["enum"] = list(config.PREDICATES)
        out.append({"type": "function", "function": {
            "name": f"stmt_{op}", "description": spec["doc"],
            "parameters": {"type": "object", "properties": props,
                           "required": spec["required"]}}})
    return out


def _select_from(args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Rebuild a nested select from the flattened scalars."""
    kind = args.get("select_kind")
    if not kind:
        return None
    sel = {"kind": kind}
    if args.get("select_attr"):
        sel[args["select_attr"]] = args.get("select_value")
    return sel


def statement_from(name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One `stmt_*` call -> one IR statement. None if it is not a statement tool.

    This is the only place the flattened surface and the stored IR meet, so the model's
    convenience never leaks into what gets signed, audited or replayed.
    """
    args = args or {}
    op = name[5:] if name.startswith("stmt_") else None
    if op not in config.OPS:
        return None
    if op == "new":
        st = {"op": "new", "var": args.get("var"), "kind": args.get("kind")}
        n = args.get("amount")
        # A count arrives as "3" as often as 3 — the schema says integer and the model
        # sends a string anyway. Rejecting that would fail a program for a JSON type,
        # not for meaning. A $parameter passes through untouched.
        if isinstance(n, str) and n.strip().lstrip(config.SIGIL).isdigit():
            n = n.strip() if n.strip().startswith(config.SIGIL) else int(n)
        if n not in (None, 1):
            st["amount"] = n
        return st
    if op == "call":
        return {"op": "call", "tool": args.get("tool"), "args": args.get("args") or {}}
    if op == "foreach":
        st = {"op": "foreach",
              "call": {"tool": args.get("tool"), "args": args.get("args") or {}}}
        if args.get("in_var"):
            st["in"] = args["in_var"]
        else:
            sel = _select_from(args)
            if sel is not None:
                st["select"] = sel
        return st
    if op == "ensure":
        shape = args.get("shape")
        pred: Dict[str, Any] = {"shape": shape}
        spec = config.PREDICATES.get(shape) or {}
        if spec.get("operand") == "sets":
            pred["sets"] = [s.strip() for s in str(args.get("sets") or "").split(",") if s.strip()]
        else:
            sel = _select_from(args)
            if sel is not None:
                pred["select"] = sel
            cmp_ = args.get("compare") or next(iter(spec.get("comparators") or {"eq": ""}), "eq")
            amount = args.get("amount")
            if isinstance(amount, str) and amount.strip().isdigit():
                amount = int(amount)
            if amount is not None:
                pred[cmp_] = amount
        return {"op": "ensure", "predicate": pred}
    return None
