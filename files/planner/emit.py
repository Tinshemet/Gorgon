"""emit.py — ONE COMPUTATIONAL MODEL, TWO TARGETS. The portability claim, made checkable.

⇒⇒ **THE SECOND EMITTER IS THE ENTIRE POINT OF THE MIDDLE LAYER, SO IT SHIPS WITH THE FIRST.**

The operator's reason for the layer: *"this way today it's Medusa, tomorrow it's Python."* A
middle layer with ONE emitter is not portable, it is indirection — and nothing would reveal the
difference until the day somebody tried to add the second and found the first had leaked into
the model. **Writing both now is what proves the model is language-independent**, and it costs
almost nothing while the model is five nodes.

⇒ **NEITHER EMITTER MAY LOOK AT ANYTHING BUT THE MODEL.** No manifest, no world, no request. If
  an emitter needs to ask a question, the answer belonged in the model and the layer above owes
  it — that is the test this file applies on every call, not a principle it states.

⇒ **PYTHON IS NOT A TOY HERE.** It emits calls to the SAME executor by the SAME operation names,
  because a domain operation is opaque to the model: `create_vm` is a string in both targets. A
  target that had to re-map operation names would be evidence the model had baked in Medusa's
  vocabulary.
"""
from typing import List

from .cmodel import DO, EACH, HOLD, MAKE, TELL, Model, Node


def _args(node: Node) -> str:
    inner = [f"{k}={v!r}" for k, v in sorted((node.args or {}).items())]
    return ", ".join(inner)


# ── Medusa ────────────────────────────────────────────────────────────────────────────────

def to_medusa(model: Model, indent: int = 0) -> str:
    """The model as Medusa source. Today's target."""
    pad = " " * indent
    out: List[str] = []
    for n in model.steps:
        if n.kind == MAKE:
            # ⇒ AMOUNT(1) IS NOISE. One is what NEW means with nothing said.
            amount = f" AMOUNT({n.count})" if n.count and int(n.count) > 1 else ""
            var = f"STORE ${n.bind} = " if n.bind else ""
            out.append(f"{pad}{var}NEW {n.of.upper()}{amount} CALL {n.op}({_args(n)});")
        elif n.kind == DO:
            out.append(f"{pad}CALL {n.op}({_args(n)});")
        elif n.kind == EACH:
            body = to_medusa(Model(tuple(n.body)), indent + 2)
            out.append(f"{pad}FOREACH ${n.item} IN ${n.over} {{\n{body}\n{pad}}}")
        elif n.kind == HOLD:
            out.append(f"{pad}ENSURE {n.must};")
        elif n.kind == TELL:
            out.append(f"{pad}PUBLISH({n.fact});")
    return "\n".join(out)


# ── Python ────────────────────────────────────────────────────────────────────────────────

def to_python(model: Model, indent: int = 0) -> str:
    """The model as Python calling the same executor. Tomorrow's target, written today.

    ⇒ IT CALLS `run(op, **args)` RATHER THAN A GENERATED FUNCTION PER TOOL, because the model
      holds an OPAQUE operation name and inventing a Python identifier from it would be this
      emitter deciding something the model did not say.
    """
    pad = " " * indent
    out: List[str] = []
    for n in model.steps:
        if n.kind == MAKE:
            times = f" for _ in range({n.count})" if n.count and int(n.count) > 1 else ""
            lhs = f"{n.bind} = " if n.bind else ""
            call = f"run({n.op!r}, {_args(n)})"
            out.append(f"{pad}{lhs}[{call}{times}]" if times else f"{pad}{lhs}{call}")
        elif n.kind == DO:
            out.append(f"{pad}run({n.op!r}, {_args(n)})")
        elif n.kind == EACH:
            body = to_python(Model(tuple(n.body)), indent + 4) or f"{pad}    pass"
            out.append(f"{pad}for {n.item} in {n.over}:\n{body}")
        elif n.kind == HOLD:
            out.append(f"{pad}assert holds({n.must!r}), {n.must!r}")
        elif n.kind == TELL:
            out.append(f"{pad}publish({n.fact!r})")
    return "\n".join(out)


EMITTERS = {"medusa": to_medusa, "python": to_python}


# ── the IR the engine already runs ────────────────────────────────────────────────────────

def to_ir(model: Model) -> dict:
    """The model as a Medusa IR program — `{"body": [...]}`, which `ir.execute.run` takes as is.

    ⇒⇒ **THIS IS HOW THE ENGINE CONSUMES THE MODEL, AND IT REQUIRED NO CHANGE TO THE ENGINE.**
      The obvious wiring — emit `to_medusa` text and hand it to the parser — would serialise a
      structure we already hold and then pay a parser to rebuild it, with every lossy step in
      between. `execute.run` never wanted source; it wanted statements. So the engine is reached
      by a THIRD EMITTER rather than by a bridge, and `engines/medusa` is untouched.

    ⇒ **AND THAT IS THE MIDDLE LAYER EARNING ITS KEEP IMMEDIATELY.** Three targets now — Medusa
      source for a person to read, Python for the portability claim, IR for the machine to run —
      and all three are ~30 lines because none of them may ask a question. Adding a fourth is the
      same shape of work, which is the property the layer exists to buy.

    ⇒ A REFERENCE BECOMES `$name`, WHICH IS THE IR's OWN SPELLING. `_Ref` marks a name rather
      than a value in the model; here it acquires the sigil, and in `to_python` it did not. That
      one difference is the whole reason references are typed in the model instead of being
      spelled at the point of creation.
    """
    from .cmodel import _Ref

    def _val(v):
        return f"${v}" if isinstance(v, _Ref) else v

    def _args(node: Node) -> dict:
        return {k: _val(v) for k, v in (node.args or {}).items()}

    def _one(n: Node) -> dict:
        if n.kind == MAKE:
            st = {"op": "new", "kind": n.of, "tool": n.op, "args": _args(n)}
            if n.count and int(n.count) > 1:
                st["amount"] = int(n.count)
            if n.bind:
                st["var"] = n.bind
            return st
        if n.kind == DO:
            return {"op": "call", "tool": n.op, "args": _args(n)}
        if n.kind == EACH:
            return {"op": "foreach", "in": f"${n.over}",
                    "do": [_one(k) for k in n.body]}
        if n.kind == HOLD:
            return {"op": "ensure", "predicate": n.must}
        return {"op": "publish", "fact": n.fact}

    return {"body": [_one(n) for n in model.steps]}


EMITTERS["ir"] = to_ir
