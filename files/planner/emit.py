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
