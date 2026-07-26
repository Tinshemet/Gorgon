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
    """A program as readable text.

    SQL keywords in upper case, C-family braces for blocks. The braces are not decoration:
    every construct coming next — IF/ELSE, IFAILS — carries a statement LIST, and
    DO … END does not nest legibly. Getting the shape right before those land is cheaper
    than migrating procedures that were already written.
    """
    body = coerce_body(program) or []
    out = []
    named = isinstance(program, dict) and bool(program.get("name"))
    if named:
        out.append(_signature(program) + " {")
    if isinstance(program, dict):
        pre = []
        for imp in (program.get("imports") or []):
            v = f" @{imp['version']}" if isinstance(imp, dict) and imp.get("version") else ""
            pkg = imp.get("package") if isinstance(imp, dict) else imp
            pre.append(f"{'  ' if named else ''}IMPORT {pkg}{v};")
        if pre:
            out += pre + [""]

    indent = "  " if named else ""
    for st in body:
        out += _statement(st, indent)
    if named:
        out.append("}")
    return "\n".join(out)


def _statement(st: Any, indent: str) -> list:
    """One statement, as one or more lines. Blocks recurse, so nesting indents itself."""
    if not isinstance(st, dict):
        return [f"{indent}<not a statement: {st!r}>"]
    op = st.get("op")

    if op == "new":
        n = st.get("amount", 1)
        # "NEW 5 vm(...)" reads the way the request does — "create 5 vms". A trailing
        # multiplier had to be decoded, and a $parameter one silently vanished entirely.
        many = (f"{n} " if (isinstance(n, str) and n.startswith(config.SIGIL))
                or (isinstance(n, int) and n > 1) else "")
        extra = _args(st.get("args")) if st.get("args") else ""
        return [f"{indent}LET {st.get('var')} = NEW {many}{st.get('kind')}"
                f"{f'({extra})' if extra else ''};"]

    if op == "call":
        # A grafted result reads as a binding, the same LET that binds a resource —
        # because naming a result and naming a resource are the same act.
        lead = f"LET {st['graft']} = " if st.get("graft") else ""
        return [f"{indent}{lead}{st.get('tool')}({_args(st.get('args'))});"]

    if op == "foreach":
        inner = st.get("call") if isinstance(st.get("call"), dict) else {}
        src = (_select(st.get("select")) if st.get("select") is not None
               else _setlit(st.get("in")))
        # The loop variable is printed as what it IS. It used to print `x` while the body
        # referenced $item — two names for one thing, in the one place a reader most needs
        # to follow the binding.
        member = f"{config.SIGIL}{config.LOOP_VAR}"
        par = " ASYNC" if st.get("async") else ""
        return ([f"{indent}FOREACH {member} IN {src}{par} {{"]
                + _statement({"op": "call", **inner}, indent + "  ")
                + [f"{indent}}}"])

    if op == "ensure":
        return [f"{indent}ENSURE {_pred(st.get('predicate'))};"]

    if op == "if":
        out = [f"{indent}IF {_pred(st.get('cond'))} {{"]
        for inner in (st.get("then") or []):
            out += _statement(inner, indent + "  ")
        if st.get("else"):
            out.append(f"{indent}}} ELSE {{")
            for inner in st["else"]:
                out += _statement(inner, indent + "  ")
        out.append(f"{indent}}}")
        return out

    return [f"{indent}<unknown op {op!r}>"]


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
    # No trailing AS: the brace already opens the block, and two openers is one
    # more thing to get wrong when writing by hand.
    return f"PROCEDURE {name}({args})"


def _setlit(src) -> str:
    """A bound reference prints as itself; a literal list prints as a list."""
    if isinstance(src, (list, tuple)):
        return "[" + ", ".join(str(x) for x in src) + "]"
    return str(src)


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
