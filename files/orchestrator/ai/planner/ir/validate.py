"""
validate.py — is this program WELL-FORMED and GROUNDED?

Three questions are kept separate on purpose, because a run needs to know which failed:

    well-formed  right shape?                        here
    grounded     real tools, real kinds, no dangling refs?   here
    satisfiable  could this hold in ANY world?        here
    meaningful   does it say what the goal meant?     nowhere in code

The last is a human's job, or the ladder's. Answering it would need a second definition
of every goal, which is how a benchmark starts measuring its own grader.

`satisfiable` is separate from `meaningful` and much narrower — it asks only whether a
statement contradicts ITSELF, which needs no knowledge of the goal and no world. Rung 9
is why it exists: the author wrote REACH(SELECT vm WHERE name = 'n1') >= 3 three times.
A name identifies at most one machine, so a floor of three over it cannot hold in any
world that could ever exist — and the world happened to end up right, so the rung checker
said PASS over a program that did not mean its goal. A check that cannot pass is not a
weak check; it is a broken one, and it is exactly the false assurance this system refuses
everywhere else.

Every problem names the statement and what specifically was wrong, because this message
is not a log line — it is fed BACK to the model on a retry, and the design treats a
rejected program as a plan failure routed to revision, not a crash. A vague complaint
wastes the correction.

The rules come from ir/config, never from literals here: required fields per op, known
kinds, predicate shapes and their operands.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from . import config, refs

try:
    from executor.command_catalog import (KNOWN_TOOLS as _KNOWN_TOOLS,
                                          REQUIRED_FIELDS as _REQUIRED_FIELDS)
except ImportError:                                        # pragma: no cover
    _KNOWN_TOOLS, _REQUIRED_FIELDS = frozenset(), {}


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


def validate(program: Any, known_tools=None, known_names=None,
             bound: Optional[set] = None) -> Tuple[bool, List[str]]:
    """(ok, problems).

    `bound` is what is already in scope — passed when validating a nested block, so the
    block can see the names its enclosing statements bound. It is a COPY at every level,
    which gives block scoping for nothing: a name grafted inside a loop is not visible
    after it. That is the right rule and it is also the one rung 11 needed, from both
    sides — the body could not see `$item` (reported "never created" for the loop's own
    member), and the statement after the loop could see a per-iteration result it has no
    business reading.

    `known_names` is what the world already contains. Optional, because well-formedness
    must be answerable without a world — but when a caller HAS one, `FROM` can be
    grounded against it, and that is worth having: a program that read the label 'red' as
    a machine to clone from validated cleanly and then made fifteen failing calls.
    """
    tools = _KNOWN_TOOLS if known_tools is None else known_tools
    body = coerce_body(program)
    if body is None:
        return False, ["program has no statements"]

    problems: List[str] = []
    # A $reference resolves against PARAMS first, then names bound by `new`. Params are
    # AUTHORED — only the author knows what varies per invocation — where `imports` are
    # DERIVED by the harness. Different provenance, so different halves of the header.
    params = program.get("params") if isinstance(program, dict) else None
    bound = set(bound or ())        # a COPY — see the docstring on scoping
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
        # A field this op does not declare is an ERROR, not something to ignore. Renaming
        # `count` to `amount` showed why: the old spelling was silently dropped and `new`
        # quietly created ONE resource instead of three — a program that looks right,
        # validates, and does a fifth of what it says. Any stale or mistyped field now
        # names itself instead.
        # `one_of` is a list of GROUPS, because an op can hold more than one either/or:
        # a foreach chooses its set (select | in) AND its body (call | do), and the two
        # choices are independent.
        groups = _one_of_groups(spec)
        known = set(spec["fields"]) | {f for g in groups for f in g} | {"op"}
        for extra in sorted(set(st) - known):
            problems.append(f"{where}: {op} has no field {extra!r} "
                            f"(it takes {', '.join(sorted(known - {'op'}))})")
        for alts in groups:
            present = [f for f in alts if st.get(f) not in (None, "", {})]
            if not present:
                problems.append(f"{where}: {op} needs one of "
                                f"{' or '.join(repr(f) for f in alts)}")
            elif len(present) > 1:
                problems.append(f"{where}: {op} says it twice "
                                f"({', '.join(present)}) — use one")

        if op == "new":
            kind = st.get("kind")
            if kind is not None and kind not in config.KINDS:
                problems.append(f"{where}: unknown kind {kind!r} "
                                f"(known: {', '.join(sorted(config.KINDS))})")
            n = st.get("amount", 1)
            if isinstance(n, str) and n.startswith(config.SIGIL):
                # "create X vms" — the count is a parameter, resolved at invocation.
                if n[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: amount {n} is not a declared parameter")
            elif not isinstance(n, int) or n < 1:
                problems.append(f"{where}: amount must be a positive integer or a "
                                f"$parameter, got {n!r}")
            if st.get("var"):
                bound.add(str(st["var"]).lstrip(config.SIGIL))
            # The creator's OWN required fields are checked, read from the live catalog.
            # This is the extensibility claim paying off: the manifest names the creator,
            # the catalog declares what it needs, and `new` is validated for any kind
            # with no language code. It also catches a real hole — `NEW vm` was passing
            # only the name, while create_vm requires os_type, so a program that
            # validated could not have built a VM against the real executor.
            src = st.get("from")
            if src is not None:
                creators = config.KINDS.get(kind, {}).get("creators") or {}
                by_copy = next((c for c in creators.values() if c.get("from")), None)
                if by_copy is None:
                    problems.append(f"{where}: {kind} cannot be created by copying "
                                    f"(no creator takes a source)")
                elif not isinstance(src, str) or not src.strip():
                    problems.append(f"{where}: `from` names the resource to copy, got {src!r}")
                elif (known_names is not None and not refs.names(src)
                        and src not in known_names):
                    # A literal source has to EXIST. `NEW vm FROM red` — red being a
                    # label, not a machine — is the mistake worth catching, and it is
                    # only catchable here: `from` is the one field naming something the
                    # program does not create and cannot bind.
                    problems.append(
                        f"{where}: `from` copies an EXISTING {kind} — there is no {kind} "
                        f"named {src!r}. A label is not a source.")
            a = st.get("args")
            if a is not None and not isinstance(a, dict):
                problems.append(f"{where}: args must be an object")
            elif kind in config.KINDS:
                creator, supplied = _creator_for(kind, st, with_supplied=True)
                # The executor supplies the key and, when copying, the source — so those
                # are not the author's to pass. Demanding them would make every clone
                # statement carry two arguments the language already knows.
                need = set(_REQUIRED_FIELDS.get(creator) or []) - supplied
                missing = sorted(need - set((a or {}).keys()))
                if missing:
                    problems.append(f"{where}: {creator} also requires "
                                    f"{', '.join(repr(m) for m in missing)} — pass them in args")
        elif op == "call":
            problems += _check_call(st, where, tools, bound)
        elif op == "foreach":
            if st.get("select") is not None:
                problems += _check_select(st.get("select"), where)
            src = st.get("in")
            if isinstance(src, list):
                # A literal set — the members are named outright. This is what a
                # CORRECTION needs: it acts on specific things the previous attempt left
                # behind, which no query describes and no earlier statement bound.
                bad = [x for x in src if not isinstance(x, str) or not x.strip()]
                if bad or not src:
                    problems.append(f"{where}: foreach `in` list must be non-empty names, "
                                    f"got {src!r}")
            elif isinstance(src, str) and src.startswith(config.SIGIL):
                if src[len(config.SIGIL):] not in bound:
                    problems.append(f"{where}: foreach in {src} refers to something "
                                    f"never created")
            elif src is not None:
                problems.append(f"{where}: foreach `in` must be a ${'{'}name{'}'} "
                                f"reference or a list of names, got {src!r}")
            inner = st.get("call")
            if inner is not None and not isinstance(inner, dict):
                problems.append(f"{where}: foreach call must be an object")
            elif isinstance(inner, dict):
                # the loop binds its member, so it is in scope inside the body
                problems += _check_call(inner, f"{where} (foreach body)", tools,
                                        bound | {config.LOOP_VAR})
            block = st.get("do")
            if block is not None:
                if not isinstance(block, list) or not block:
                    problems.append(f"{where}: `do` is a list of statements, got {block!r}")
                else:
                    _, sub = validate({"body": block}, tools, known_names,
                                      bound | {config.LOOP_VAR})
                    problems += [f"{where} (foreach body) → {x}" for x in sub]
        elif op == "ensure":
            problems += _check_predicate(st.get("predicate"), where, bound)
        elif op == "if":
            problems += _check_predicate(st.get("cond"), where, bound)
            for branch in ("then", "else"):
                kids = st.get(branch)
                if kids is None:
                    continue
                if not isinstance(kids, list) or not kids:
                    problems.append(f"{where}: `{branch}` is a list of statements, got {kids!r}")
                else:
                    ok2, sub = validate({"body": kids}, tools, known_names, bound)
                    problems += [f"{where} ({branch}) → {x}" for x in sub]
        # A grafted name is in scope from here on, and IFAILS carries statements wherever
        # it appears — both checked once, for every acting op, rather than per branch.
        if st.get("graft"):
            bound.add(str(st["graft"]).lstrip(config.SIGIL))
        recov = st.get("ifails")
        if recov is not None:
            if not isinstance(recov, list) or not recov:
                problems.append(f"{where}: `ifails` is a list of statements, got {recov!r}")
            else:
                _, sub = validate({"body": recov}, tools, known_names, bound)
                problems += [f"{where} (ifails) → {x}" for x in sub]
    return (not problems), problems


def _creator_for(kind: str, st: Dict[str, Any], with_supplied: bool = False):
    """Which tool creates this resource — chosen by whether `from` is present.

    A kind may be made more than one way (a machine built fresh, or cloned). Selecting
    between them by the presence of a field rather than a keyword keeps the choice out of
    the language: adding a third way to create something stays a manifest row.
    """
    spec = config.KINDS.get(kind) or {}
    creators = spec.get("creators") or {}
    chosen, supplied = None, {spec.get("key")}
    if st.get("from"):
        chosen = next((c for c in creators.values() if c.get("from")), None)
    if chosen is None:
        chosen = creators.get("create") or {"tool": spec.get("create")}
    if chosen.get("key"):
        supplied.add(chosen["key"])
    if chosen.get("from"):
        supplied.add(chosen["from"])
    tool = chosen.get("tool") or spec.get("create")
    return (tool, {x for x in supplied if x}) if with_supplied else tool


def _one_of_groups(spec: Dict[str, Any]) -> List[List[str]]:
    """An op's either/or groups, normalised.

    Accepts the old flat form (`["select", "in"]`) as a single group so a manifest
    written either way means the same thing — this is the shape the schema generator
    reads too, and the two must not disagree about it.
    """
    alts = spec.get("one_of") or []
    if alts and isinstance(alts[0], str):
        return [list(alts)]
    return [list(g) for g in alts]


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
    spec = config.KINDS[kind]
    legal = set(spec["attrs"]) | set(spec.get("aliases") or {})
    # `not` holds another set of filters — the carve-out. Checked with the same rules, so
    # an excluded attribute is validated exactly like an included one.
    out = []
    if "not" in sel:
        if not isinstance(sel["not"], dict) or not sel["not"]:
            out.append(f"{where}: `not` takes the filters to EXCLUDE, e.g. {{'name':'db'}}")
        else:
            out += _check_select({"kind": kind, **sel["not"]}, where)
    unknown = [k for k in sel if k not in ("kind", "not") and k not in legal]
    # Aliases are accepted, not just tolerated: the harness has its own synonyms (`tag`
    # for a label, `os` for os_type) and a program written either way means the same
    # thing. Rejecting one spelling of one concept is the vocabulary problem in miniature.
    return out + [f"{where}: {kind} has no attribute {k!r} "
                  f"(queryable: {', '.join(sorted(spec['attrs']))})" for k in unknown]


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
    # A call's REQUIRED arguments, read off the live catalog — the same check `new`
    # already got, and its absence here was an inconsistency: rung 12 emitted
    # snapshot_create without snap_name, validated, and both calls were rejected by the
    # world. Catching it before execution beats discovering it after.
    for miss in sorted(set(_REQUIRED_FIELDS.get(tool) or []) - set(st.get("args") or {})):
        out.append(f"{where}: {tool} requires {miss!r}")
    args = st.get("args")
    if args is not None and not isinstance(args, dict):
        return out + [f"{where}: args must be an object"]
    for k, v in (args or {}).items():
        # Every name the argument mentions, not just a whole-string one: `$item-snap`
        # refers to `item`, and rejecting it as a reference to `item-snap` blamed the
        # author for the language's missing composition.
        for ref in refs.names(v):
            if ref not in bound:
                out.append(f"{where}: {k}={v} refers to {config.SIGIL}{ref}, "
                           f"which is never created")
    return out


def _at_most_one(sel: Any) -> bool:
    """Does this select match at most one member, whatever the world contains?

    True when it pins the kind's KEY to a literal — `name` for a vm, `net_name` for a
    network. A `$reference` does not count: it may resolve to a whole set.
    """
    if not isinstance(sel, dict):
        return False
    key = (config.KINDS.get(sel.get("kind")) or {}).get("key")
    val = sel.get(key) if key else None
    return isinstance(val, str) and bool(val) and not refs.names(val)


def _check_predicate(pred: Any, where: str, bound: Optional[set] = None) -> List[str]:
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
    if spec.get("arity") == "value":
        # IS($answer.reachable) = false — reads a grafted result, not the world.
        if not isinstance(value, str) or not value.startswith(config.SIGIL):
            return [f"{where}: {shape} reads a grafted value, e.g. "
                    f"{config.SIGIL}answer.reachable — got {value!r}"]
        if not (set(pred) & set(spec["comparators"])):
            return [f"{where}: {shape} needs "
                    f"{'/'.join(spec['comparators'])} to compare against"]
        # And the name it reads has to BE in scope. Predicates were the one place a
        # reference went unchecked, which mattered the moment loops got block scoping:
        # a result grafted inside a loop is gone after it, so `ENSURE IS($answers.alive)`
        # following the loop reads nothing. It validated silently — the exact shape of
        # someone reaching for "collect every answer, then check them", which is a
        # feature the language does not have. Better to say so than to pass.
        if bound is not None:
            for ref in refs.names(value):
                if ref not in bound:
                    return [f"{where}: {shape} reads {config.SIGIL}{ref}, which is not in "
                            f"scope here — a result grafted inside a loop does not "
                            f"outlive it"]
        return []
    if operand == "of":
        # A composite's operand is other predicates, checked recursively — so a malformed
        # child names itself rather than the parent looking wrong.
        kids = [value] if spec.get("arity") == "one" else value
        if spec.get("arity") == "one":
            if not isinstance(value, dict):
                return [f"{where}: {shape} takes one check under `of`, got {value!r}"]
        elif not isinstance(value, (list, tuple)) or len(value) < 2:
            return [f"{where}: {shape} takes two or more checks under `of`, got {value!r}"]
        for kid in kids:
            out += _check_predicate(kid, where, bound)
        return out
    if operand == "select":
        if not isinstance(value, dict):
            out.append(f"{where}: {shape} needs `select` — the set to measure, "
                       f"e.g. {{'kind':'vm','tag':'prod'}}")
        else:
            out += _check_select(value, where)
    elif operand == "sets":
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            out.append(f"{where}: {shape} needs `sets` — two or more, got {value!r}")
    # A floor above one over a set that can hold at most one member is unsatisfiable by
    # construction. Reported as a problem, not a warning: the whole contract of ENSURE is
    # that passing it means something.
    if operand == "select" and _at_most_one(value):
        key = (config.KINDS.get(value.get("kind")) or {}).get("key")
        for c, floor in (("min", 1), ("gte", 1), ("eq", 1)):
            n = pred.get(c)
            if isinstance(n, int) and n > floor:
                out.append(
                    f"{where}: {shape} over {key} = {value.get(key)!r} can never reach "
                    f"{n} — a {value.get('kind')} {key} names ONE resource. Select the "
                    f"whole set (e.g. a shared label), or drop the floor.")
                break

    if (spec["comparators"] and not spec.get("comparators_optional")
            and not (set(pred) & set(spec["comparators"]))):
        # `reach` opts out. Its own doc reads "the members can reach each other" and the
        # deriver has always defaulted (`min`, 2) — only this check ever demanded a
        # number, so REACH(SELECT vm WHERE label='fleet') meaning ALL of them was
        # intended everywhere except the one place that rejected it. An author asked for
        # "make sure they all ping each other" has no N to supply and had to invent one.
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
