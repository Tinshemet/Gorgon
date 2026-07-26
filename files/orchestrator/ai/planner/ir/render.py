"""
render.py — the operator's view: SQL-shaped text, one direction only.

The model never sees this and nothing parses it back. It exists so a human can READ a
program before signing it — which is what makes a signed procedure reviewable rather
than a blob of JSON. Kept small on purpose (design note §02: "about fifty lines, one
direction"); a reader comes later, and only if operators want to type programs by hand.

It renders UNVALIDATED model output, so nothing here may raise. A renderer that crashes
on a malformed program hides the very thing you opened it to look at — it did exactly
that once, on a predicate holding a number where a set belonged.
"""

from typing import Any

from . import config
from .validate import coerce_body


def render(program: Any) -> str:
    """A program as readable text."""
    body = coerce_body(program) or []
    out = []
    named = isinstance(program, dict) and bool(program.get("name"))
    if isinstance(program, dict):
        sig = _signature(program)
        if sig:
            out.append(sig)
        for imp in (program.get("imports") or []):
            v = f" @{imp['version']}" if isinstance(imp, dict) and imp.get("version") else ""
            pkg = imp.get("package") if isinstance(imp, dict) else imp
            out.append(f"IMPORT {pkg}{v};")
        if out:
            out.append("")
    indent = "  " if named else ""
    for st in body:
        if not isinstance(st, dict):
            out.append(f"<not a statement: {st!r}>")
            continue
        op = st.get("op")
        if op == "new":
            n = st.get("count", 1)
            # A $parameter count has to SHOW — it silently vanished, so `create X vms`
            # rendered as `NEW vm`, i.e. one. The operator reads this to decide whether
            # to sign it; a dropped multiplier is the worst thing it could hide.
            many = (f" x{n}" if (isinstance(n, str) and n.startswith(config.SIGIL))
                    or (isinstance(n, int) and n > 1) else "")
            out.append(f"{indent}LET {st.get('var')} = NEW {st.get('kind')}{many};")
        elif op == "call":
            out.append(f"{indent}{st.get('tool')}({_args(st.get('args'))});")
        elif op == "foreach":
            inner = st.get("call") if isinstance(st.get("call"), dict) else {}
            src = (f"({_select(st.get('select'))})" if st.get("select") is not None
                   else str(st.get("in")))
            out.append(f"{indent}FOREACH x IN {src}")
            out.append(f"{indent}  DO {inner.get('tool')}({_args(inner.get('args'))}); END")
        elif op == "ensure":
            out.append(f"{indent}ENSURE {_pred(st.get('predicate'))};")
        else:
            out.append(f"<unknown op {op!r}>")
    if named:
        out.append("END")
    return "\n".join(out)


def _signature(program: dict) -> str:
    """`PROCEDURE name(p TYPE, ...) AS` — only for a NAMED program.

    A bare goal renders as plain statements, because that is what an ad-hoc run is. The
    signature appears once there is something to store and sign, which is the point at
    which the parameters matter.
    """
    name = program.get("name")
    if not name:
        return ""
    args = ", ".join(f"{k} {config.PARAM_TYPES.get(v, {}).get('sql', str(v).upper())}"
                     for k, v in (program.get("params") or {}).items())
    return f"PROCEDURE {name}({args}) AS"


def _args(args) -> str:
    if not isinstance(args, dict):
        return f"<not args: {args!r}>" if args is not None else ""
    return ", ".join(f"{k}: {v}" for k, v in args.items())


def _select(sel) -> str:
    if not isinstance(sel, dict):
        return f"<not a set: {sel!r}>"
    kind = sel.get("kind", "?")
    where = " AND ".join(f"{k} = '{v}'" for k, v in sel.items() if k != "kind")
    return f"SELECT {kind}" + (f" WHERE {where}" if where else "")


def _pred(p) -> str:
    """Rendered from the manifest, so a predicate added to JSON prints without an edit."""
    if not isinstance(p, dict):
        return f"<not a predicate: {p!r}>"
    shape = p.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return f"<unknown check {shape!r}>"
    if spec["operand"] == "sets":
        return f"{shape.upper()}({', '.join(str(x) for x in (p.get('sets') or []))})"
    # The symbol comes from the manifest beside the comparator it belongs to. It used to
    # be a dict here, so a comparator added to the JSON rendered as "?" — the language
    # extended in one place and printed wrong in another.
    used = next((c for c in spec["comparators"] if c in p), None)
    sym = spec["comparators"].get(used, "?")
    return f"{shape.upper()}({_select(p.get('select'))}) {sym} {p.get(used)}"
