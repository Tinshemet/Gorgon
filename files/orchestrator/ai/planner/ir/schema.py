"""
schema.py — the tool the model fills in to produce a program.

BUILT FROM THE MANIFEST, not written out. The op names come from `ops`, the predicate
shapes from `predicates`, every sentence from `prompt`. Adding an op or a predicate to
the JSON changes what the model is offered, with no edit here.

There is no parser anywhere in this package, and that is the point: the model CALLS this
tool and the statements arrive as validated JSON arguments. `DECOMPOSE_TOOL` is the
working precedent — one schema instead of a lexer and a grammar.
"""

from typing import Any, Dict

from . import config


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
    comparators = sorted({c for p in config.PREDICATES.values() for c in p["comparators"]})
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


def emit_program_tool() -> Dict[str, Any]:
    """The tool schema, assembled from the manifest."""
    return {
        "type": "function",
        "function": {
            "name": "emit_program",
            "description": config.PROMPT["tool_description"],
            "parameters": {
                "type": "object",
                "properties": {
                    "body": {
                        "type": "array",
                        "description": "The statements, in order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "op":     {"type": "string", "enum": list(config.OPS)},
                                "var":    {"type": "string", "description": "new: the name to bind"},
                                "kind":   {"type": "string", "enum": list(config.KINDS),
                                           "description": "new: the resource type"},
                                "count":  {"type": "integer", "description": "new: how many (default 1)"},
                                "tool":   {"type": "string", "description": "call: the tool name"},
                                "args":   {"type": "object", "description": "call: the tool's arguments"},
                                "select": {"type": "object", "description": config.PROMPT["select_hint"]},
                                "call":   {"type": "object",
                                           "description": "foreach: the call to apply to each member"},
                                "predicate": _predicate_property(),
                            },
                            "required": ["op"],
                        },
                    },
                },
                "required": ["body"],
            },
        },
    }


def system_prompt(tools) -> str:
    """What the model needs to know to write a program — ops, kinds, predicates, tools.

    Assembled from the manifest so the prompt cannot drift from what validate() accepts:
    both read the same table.
    """
    p = config.PROMPT
    lines = [p["intro"], "", p["statements_header"]]
    for op, spec in config.OPS.items():
        lines.append(f"  {op:8}— {spec['doc']}")
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
