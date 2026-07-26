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
    if isinstance(program, dict):
        for imp in (program.get("imports") or []):
            v = f" @{imp['version']}" if isinstance(imp, dict) and imp.get("version") else ""
            pkg = imp.get("package") if isinstance(imp, dict) else imp
            out.append(f"IMPORT {pkg}{v};")
        if out:
            out.append("")
    for st in body:
        if not isinstance(st, dict):
            out.append(f"<not a statement: {st!r}>")
            continue
        op = st.get("op")
        if op == "new":
            n = st.get("count", 1)
            many = f" x{n}" if isinstance(n, int) and n > 1 else ""
            out.append(f"LET {st.get('var')} = NEW {st.get('kind')}{many};")
        elif op == "call":
            out.append(f"{st.get('tool')}({_args(st.get('args'))});")
        elif op == "foreach":
            inner = st.get("call") if isinstance(st.get("call"), dict) else {}
            out.append(f"FOREACH x IN ({_select(st.get('select'))})")
            out.append(f"  DO {inner.get('tool')}({_args(inner.get('args'))}); END")
        elif op == "ensure":
            out.append(f"ENSURE {_pred(st.get('predicate'))};")
        else:
            out.append(f"<unknown op {op!r}>")
    return "\n".join(out)


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
    used = next((c for c in spec["comparators"] if c in p), None)
    sym = {"eq": "=", "gte": ">=", "lte": "<=", "min": ">="}.get(used, "?")
    return f"{shape.upper()}({_select(p.get('select'))}) {sym} {p.get(used)}"
