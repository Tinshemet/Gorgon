"""
validate.py — is this program WELL-FORMED and GROUNDED?

Three questions are kept separate on purpose, because a run needs to know which failed:

    well-formed  right shape?                        here
    grounded     real tools, real kinds, no dangling refs?   here
    meaningful   does it say what the goal meant?     nowhere in code

The third is a human's job, or the ladder's. Answering it would need a second definition
of every goal, which is how a benchmark starts measuring its own grader.

Every problem names the statement and what specifically was wrong, because this message
is not a log line — it is fed BACK to the model on a retry, and the design treats a
rejected program as a plan failure routed to revision, not a crash. A vague complaint
wastes the correction.

The rules come from ir/config, never from literals here: required fields per op, known
kinds, predicate shapes and their operands.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from . import config

try:
    from executor.command_catalog import KNOWN_TOOLS as _KNOWN_TOOLS
except ImportError:                                        # pragma: no cover
    _KNOWN_TOOLS = frozenset()


def coerce_body(raw: Any) -> Optional[List[Any]]:
    """The statement list out of whatever the model actually handed back, or None.

    Not defensive clutter — it is what this model class DOES. Asked for `body` as an
    array, llama3.1 frequently returns the array SERIALISED:

        {"body": "[{\\"op\\": \\"foreach\\", ...}]"}

    `_first_tool_call` already unwraps a stringified `arguments`; this is the same trick
    one level deeper, on the field. Rejecting it scored three of four perfectly good
    programs as "emitted nothing" before this existed. Fix the reader, not the model.
    """
    if isinstance(raw, dict):
        raw = raw.get("body")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, dict):            # a lone statement, not wrapped in a list
        raw = [raw]
    return raw if isinstance(raw, list) and raw else None


def validate(program: Any, known_tools=None) -> Tuple[bool, List[str]]:
    """(ok, problems)."""
    tools = _KNOWN_TOOLS if known_tools is None else known_tools
    body = coerce_body(program)
    if body is None:
        return False, ["program has no statements"]

    problems: List[str] = []
    # A $reference resolves against PARAMS first, then names bound by `new`. Params are
    # AUTHORED — only the author knows what varies per invocation — where `imports` are
    # DERIVED by the harness. Different provenance, so different halves of the header.
    params = program.get("params") if isinstance(program, dict) else None
    bound = set()
    for name, typ in (params or {}).items():
        if typ not in config.PARAM_TYPES:
            problems.append(f"parameter {name!r}: unknown type {typ!r} "
                            f"(known: {', '.join(sorted(config.PARAM_TYPES))})")
        bound.add(str(name))
    for i, st in enumerate(body):
        where = f"statement {i + 1}"
        if not isinstance(st, dict):
            problems.append(f"{where}: not an object")
            continue
        op = st.get("op")
        spec = config.OPS.get(op)
        if spec is None:
            problems.append(f"{where}: unknown op {op!r} "
                            f"(expected one of {', '.join(config.OPS)})")
            continue
        for field in spec["required"]:
            if st.get(field) in (None, "", {}):
                problems.append(f"{where}: {op} is missing {field!r}")
        alts = spec.get("one_of")
        if alts:
            present = [f for f in alts if st.get(f) not in (None, "", {})]
            if not present:
                problems.append(f"{where}: {op} needs one of "
                                f"{' or '.join(repr(f) for f in alts)}")
            elif len(present) > 1:
                problems.append(f"{where}: {op} names its set twice "
                                f"({', '.join(present)}) — use one")

        if op == "new":
            kind = st.get("kind")
            if kind is not None and kind not in config.KINDS:
                problems.append(f"{where}: unknown kind {kind!r} "
                                f"(known: {', '.join(sorted(config.KINDS))})")
            n = st.get("count", 1)
            if isinstance(n, str) and n.startswith(config.SIGIL):
                # "create X vms" — the count is a parameter, resolved at invocation.
                if n[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: count {n} is not a declared parameter")
            elif not isinstance(n, int) or n < 1:
                problems.append(f"{where}: count must be a positive integer or a "
                                f"$parameter, got {n!r}")
            if st.get("var"):
                bound.add(str(st["var"]).lstrip(config.SIGIL))
        elif op == "call":
            problems += _check_call(st, where, tools, bound)
        elif op == "foreach":
            if st.get("select") is not None:
                problems += _check_select(st.get("select"), where)
            src = st.get("in")
            if isinstance(src, str) and src.startswith(config.SIGIL):
                if src[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: foreach in {src} refers to something "
                                    f"never created")
            elif src is not None:
                problems.append(f"{where}: foreach `in` must be a ${'{'}name{'}'} "
                                f"reference, got {src!r}")
            inner = st.get("call")
            if inner is not None and not isinstance(inner, dict):
                problems.append(f"{where}: foreach call must be an object")
            elif isinstance(inner, dict):
                # the loop binds its member, so it is in scope inside the body
                problems += _check_call(inner, f"{where} (foreach body)", tools,
                                        bound | {config.LOOP_VAR})
        elif op == "ensure":
            problems += _check_predicate(st.get("predicate"), where)
    return (not problems), problems


def _check_select(sel: Any, where: str) -> List[str]:
    """A select names a known kind and filters on attributes that kind declares."""
    if sel is None:
        return []
    if not isinstance(sel, dict):
        return [f"{where}: select must be an object"]
    kind = sel.get("kind")
    if kind and kind not in config.KINDS:
        return [f"{where}: selects unknown kind {kind!r} "
                f"(known: {', '.join(sorted(config.KINDS))})"]
    if not kind:
        return [f"{where}: select must name a kind"]
    legal = set(config.KINDS[kind]["attrs"])
    unknown = [k for k in sel if k != "kind" and k not in legal]
    return [f"{where}: {kind} has no attribute {k!r} "
            f"(queryable: {', '.join(sorted(legal))})" for k in unknown]


def _check_call(st: Dict[str, Any], where: str, tools, bound) -> List[str]:
    """A call names a REAL tool, carries args, and references only what exists.

    `args` is checked here rather than left to the per-op required-field pass so it
    applies inside a `foreach` too: the first valid-looking program the model produced
    was a foreach calling `launch_vm()` with no arguments — it validated, and would have
    failed at execution against a tool that needs a name.
    """
    out = []
    tool = st.get("tool")
    if tool and tools and tool not in tools:
        out.append(f"{where}: no such tool {tool!r}")
    if not st.get("args"):
        out.append(f"{where}: call to {tool or '?'} has no args")
    args = st.get("args")
    if args is not None and not isinstance(args, dict):
        return out + [f"{where}: args must be an object"]
    for k, v in (args or {}).items():
        if isinstance(v, str) and v.startswith(config.SIGIL):
            ref = v[len(config.SIGIL):]
            if ref not in bound:
                out.append(f"{where}: {k}={v} refers to something never created")
    return out


def _check_predicate(pred: Any, where: str) -> List[str]:
    """A predicate names its `shape` and supplies that shape's operand."""
    if pred is None:
        return []
    if not isinstance(pred, dict):
        return [f"{where}: predicate must be an object"]
    shape = pred.get("shape")
    spec = config.PREDICATES.get(shape)
    if spec is None:
        return [f"{where}: predicate shape must be one of "
                f"{', '.join(config.PREDICATES)}, got {shape!r}"]
    out, operand = [], spec["operand"]
    value = pred.get(operand)
    if operand == "select":
        if not isinstance(value, dict):
            out.append(f"{where}: {shape} needs `select` — the set to measure, "
                       f"e.g. {{'kind':'vm','tag':'prod'}}")
        else:
            out += _check_select(value, where)
    elif operand == "sets":
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            out.append(f"{where}: {shape} needs `sets` — two or more, got {value!r}")
    if spec["comparators"] and not (set(pred) & set(spec["comparators"])):
        out.append(f"{where}: {shape} needs one of "
                   f"{'/'.join(spec['comparators'])} to compare against")
    return out


def kinds_used(body: List[Any]) -> List[str]:
    """Every resource kind a program touches — what `imports` is derived from."""
    seen = []
    for st in body or []:
        if not isinstance(st, dict):
            continue
        for k in (st.get("kind"), (st.get("select") or {}).get("kind")
                  if isinstance(st.get("select"), dict) else None):
            if k and k not in seen:
                seen.append(k)
    return seen
