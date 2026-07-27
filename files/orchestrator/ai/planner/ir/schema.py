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

from typing import Any, Dict, List, Optional

from . import config, master


def _predicate_property() -> Dict[str, Any]:
    """The `predicate` field's schema.

    MEASURED, and the reason `schema.predicate_properties` exists as a knob: with
    `predicate` typed only as a bare object the model returned it EMPTY every time,
    while `select` — which carries a worked example — filled correctly in the same
    programs. Declaring properties fixed that. Adding a nested `required` on top made it
    stop calling the tool AT ALL (3/4 emitting went to 0/4): this tool-call surface has a
    complexity ceiling, and the bake-off already found tool-calling fidelity, not
    reasoning, to be the binding constraint. Both knobs default accordingly.
    """
    prop: Dict[str, Any] = {"type": "object", "description": "ensure: what must hold at the end"}
    if not config.SCHEMA.get("predicate_properties"):
        return prop
    comparators = sorted({c for p in config.PREDICATES.values() for c in p["comparators"]})  # dict -> its keys
    props: Dict[str, Any] = {
        "shape":  {"type": "string", "enum": list(config.PREDICATES),
                   "description": "which check"},
        "select": {"type": "object",
                   "description": "the set to measure — same form as foreach's select"},
        "sets":   {"type": "array", "items": {"type": "string"},
                   "description": "disjoint: the sets to compare"},
    }
    for c in comparators:
        props[c] = {"type": "integer", "description": f"comparison: {c}"}
    prop["properties"] = props
    if config.SCHEMA.get("predicate_required"):
        prop["required"] = ["shape"]
    return prop


def _field(name: str, known: Optional[set] = None) -> Dict[str, Any]:
    """One field's JSON-Schema fragment, from the catalogue.

    `enum_from` points at another manifest table, so `kind`'s enum tracks the resource
    manifest — add a kind and the enum follows with no edit here. `known` is the lab, and
    the master decides what it narrows.
    """
    spec = dict(config.FIELDS[name])
    doc = spec.pop("doc", "")
    src = spec.pop("enum_from", None)
    if src:
        spec["enum"] = list(getattr(config, src.upper()))
    if name == "predicate":
        return _predicate_property()
    if name == "from":
        return _from_field(doc, known)
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


def _statement_flat(want: Optional[str] = None, known: Optional[set] = None) -> Dict[str, Any]:
    """One object, every field optional, only `op` required.

    Simple for the model to call and structurally useless: a `new` and an `ensure` are
    the same type, so nothing stops `{"op":"new","predicate":{...}}` and nothing prompts
    the model to supply `op` at all. Measured — qwen2.5:14b returned six of nine
    statements with no `op`. Kept as a knob because it is the SIMPLEST schema, and
    simplicity is what emission turned out to be sensitive to.
    """
    props = {"op": {"type": "string", "enum": master.ops(want)}}
    for name in config.FIELDS:
        props[name] = _field(name, known)
    return {"type": "object", "properties": props, "required": ["op"]}


def _statement_oneof(want: Optional[str] = None, known: Optional[set] = None) -> Dict[str, Any]:
    """One branch per op, so a statement's type determines its fields.

    `op` is a const per branch, which both forces the discriminator to be present and
    tells the model which fields go with it. Built from the same rows as the flat form,
    so the two cannot describe different languages.
    """
    branches = []
    for op in master.ops(want):
        spec = config.OPS[op]
        props = {"op": {"type": "string", "const": op, "description": spec["doc"]}}
        for name in spec["fields"]:
            props[name] = _field(name, known)
        required = ["op"] + [f for f in spec["required"]]
        branches.append({"type": "object", "properties": props, "required": required})
    return {"oneOf": branches}


def emit_program_tool(want: Optional[str] = None, known: Optional[set] = None) -> Dict[str, Any]:
    """The tool schema, assembled from the manifest and narrowed by the master."""
    form = config.SCHEMA.get("statement_form", "oneof")
    item = (_statement_oneof(want, known) if form == "oneof"
            else _statement_flat(want, known))
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


def system_prompt(tools, want: Optional[str] = None) -> str:
    """What the model needs to know to write a program — ops, kinds, predicates, tools.

    Assembled from the manifest so the prompt cannot drift from what validate() accepts:
    both read the same table. The op LISTING is narrowed by the master for the same reason
    the schema is — a prompt that describes `new` while the decoder cannot emit it is the
    four-way disagreement in miniature, and the model spends its reasoning on a construct
    it will never be able to produce.
    """
    p = config.PROMPT
    lines = [p["intro"], "", p["statements_header"]]
    for op in master.ops(want):
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
    lines += ["", p["reference"], p["ordering"], "",
              f"{p['tools_header']} {', '.join(tools)}.", p["tools_footer"]]
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


def statement_tools(want: Optional[str] = None) -> List[Dict[str, Any]]:
    """One tool per op — flat, scalar, and small enough to actually get called.

    NOTE THE GAP, which narrowing by intent is what made visible: `_STATEMENT_TOOLS` above
    covers new/call/foreach/ensure and predates `fetch`, `achieve` and `if`. So a `fetch`
    intent narrows this surface to NOTHING. That is the honest answer — this surface cannot
    serve a retrieval — and a caller must read [] as "not offerable here", never as "no
    statements are permitted". Papering over it by handing back the unnarrowed set would
    offer `new` to an operator who asked to be told something.
    """
    offered = set(master.ops(want))
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
