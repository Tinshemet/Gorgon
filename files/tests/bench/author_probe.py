"""
author_probe.py — constrained decoding + few-shot: can the model AUTHOR a program?

Eight experiments through the TOOL-CALL channel all hit the same wall: more schema
guidance bought less emission (oneOf -> 0/4, a nested required -> 0/4, a richer prompt ->
fewer calls). The model could only ever see the schema as advice.

This uses a different channel. Ollama's `format` takes a JSON Schema and CONSTRAINS THE
DECODER, so a violating token cannot be produced. Two consequences:

  * structural validity stops being something to hope for;
  * tightening the schema becomes FREE — there is no "will it call the tool" left to
    lose, which inverts the tradeoff every previous experiment was fighting.

The tool-call channel is not abandoned, it is reassigned. Routing (primitive vs decompose
vs program) is a tool call and scores 10/10; authoring is this; execution is neither —
the visitor issues the calls itself, through the gate. Each channel does what it measures
well at.

THE FEW-SHOT EXAMPLES ARE DELIBERATELY NOT LADDER RUNGS. They exercise the same
constructs — a counted `new`, a filtered `foreach`, a bound-set `foreach`, an `ensure` —
on goals that appear nowhere in the benchmark. Teaching the model the test would make the
ladder measure this file, which is the standing principle in rungs.py.

Run:  PYTHONPATH=. python3 -m tests.bench.author_probe
      PYTHONPATH=. python3 -m tests.bench.author_probe --no-shots   # ablate few-shot
      PYTHONPATH=. python3 -m tests.bench.author_probe -p           # paraphrase column
"""
import argparse
import json
import sys
import urllib.request

from orchestrator.ai.planner.ir import config, consent, derive, render, run, validate
from orchestrator.ai.planner.ir.validate import _one_of_groups

from .ladder import BENCH_MODEL
from .rungs import RUNGS
from .sim_world import SimWorld

_TOOLS = SimWorld.tools()
_OLLAMA = "http://localhost:11434/api/chat"


def _call_spec():
    return {"type": "object",
            "properties": {"tool": {"type": "string", "enum": list(_TOOLS)},
                           "args": {"type": "object"}},
            "required": ["tool", "args"]}


def _select_spec(depth: int = 1):
    """A select: the kind, plus whichever attributes that kind declares queryable, plus
    the `not` carve-out.

    `not` was implemented in the validator and never offered here, so rung 8 — "every vm
    except db" — could not be said. The author invented `name: '!db'`, a syntax that does
    not exist, and was marked down for it. That is the recurring shape of every defect in
    this probe: the language had the construct, the schema withheld it, and the model got
    the blame. Depth-limited because a carve-out inside a carve-out is a double negative
    nobody should write.
    """
    props = {"kind": {"type": "string", "enum": list(config.KINDS)}}
    for k in config.KINDS.values():
        for attr in k["attrs"]:
            props.setdefault(attr, {"type": "string"})
    if depth > 0:
        inner = {a: v for a, v in props.items() if a != "kind"}
        props["not"] = {"type": "object", "properties": inner,
                        "minProperties": 1,
                        "description": "EXCLUDE members matching these filters, e.g. "
                                       "{\"name\": \"db\"} for 'every vm except db'"}
    return {"type": "object", "properties": props, "required": ["kind"]}


def _field_schema(name: str):
    """One field's schema, from the manifest's field catalogue.

    Built rather than written out. This schema WAS hand-maintained and had already
    drifted: it still said `count` after the rename to `amount`, and knew nothing of
    `from`, `graft`, `if` or `ifails` — so the model could not reach constructs that
    exist. A probe that withholds half the language measures the wrong thing and reports
    it as a model failure.
    """
    spec = dict(config.FIELDS.get(name) or {"type": "string"})
    doc = spec.pop("doc", "")
    src = spec.pop("enum_from", None)
    if name == "select":
        return _select_spec()
    if name == "call":
        return _call_spec()
    if name in ("then", "else", "ifails", "do"):
        return {"type": "array", "items": {"$ref": "#/$defs/stmt"}, "description": doc}
    if name in ("cond", "predicate"):
        return {"$ref": "#/$defs/pred"}
    if name == "in":
        return {"anyOf": [{"type": "string"},
                          {"type": "array", "items": {"type": "string"}}],
                "description": doc}
    if src:
        return {"type": "string", "enum": list(getattr(config, src.upper())),
                "description": doc}
    t = spec.get("type")
    return {"type": t if isinstance(t, str) else "string", "description": doc}


def _pred_spec():
    """One branch PER SHAPE, each requiring the operand that shape actually takes.

    A single flat object with only `shape` required let the decoder emit
    `{"shape":"reach","min":5}` — a number and no set — which is precisely what rungs 4,
    9 and 13 produced. It is the same defect as a collapsed `one_of`, one level down: a
    requirement the validator knows about and the decoder does not is a requirement the
    author can still walk into. The manifest already records each shape's `operand`; this
    just stops throwing that away.
    """
    branches = []
    for shape, spec in config.PREDICATES.items():
        operand, arity = spec["operand"], spec.get("arity")
        props = {"shape": {"type": "string", "const": shape,
                           "description": spec["doc"]}}
        if operand == "select":
            props["select"] = _select_spec()
        elif operand == "sets":
            props["sets"] = {"type": "array", "items": {"type": "string"},
                             "minItems": 2,
                             "description": "two or more $names of sets"}
        elif operand == "of":
            props["of"] = ({"type": "string",
                            "description": "a $grafted.value, e.g. $answer.alive"}
                           if arity == "value" else
                           {"type": "array", "items": {"$ref": "#/$defs/pred"},
                            "minItems": 2 if arity == "many" else 1,
                            "description": "the check(s) this combines"})
        for c in spec.get("comparators") or {}:
            props[c] = {"type": ["integer", "boolean", "string"],
                        "description": f"compare with {spec['comparators'][c]}"}
        # A shape whose comparator is mandatory must REQUIRE one — COUNT with no number
        # is as meaningless as REACH with no set. Several comparators means several
        # branches, one per choice; requiring none of three is how `count` would have
        # kept slipping through. `reach` opts out by manifest.
        comps = list(spec.get("comparators") or {})
        if comps and not spec.get("comparators_optional"):
            for c in comps:
                branches.append({"type": "object", "properties": props,
                                 "required": ["shape", operand, c]})
        else:
            branches.append({"type": "object", "properties": props,
                             "required": ["shape", operand]})
    return {"oneOf": branches}


def program_schema():
    """The full schema, assembled from the manifest so it cannot fall behind the language.

    Statement branches come from `ops`, their fields from the field catalogue, predicates
    from `predicates`. Adding a construct to the JSON offers it here with no edit — the
    claim the manifest makes everywhere else, applied to the one place that had quietly
    stopped honouring it.
    """
    branches = []
    for op, spec in config.OPS.items():
        props = {"op": {"type": "string", "const": op, "description": spec["doc"]}}
        for f in spec["fields"]:
            props[f] = _field_schema(f)
        groups = _one_of_groups(spec)
        if groups:
            # `one_of` has to reach the DECODER, not just the validator. Collapsing it
            # into a single branch with both fields optional is what produced
            # `FOREACH $item IN None` five times in one program: nothing forced a set to
            # be named. One branch per alternative, each REQUIRING its own field.
            # One branch per COMBINATION of choices. `foreach` picks its set
            # (select | in) and its body (call | do) independently, so it has four —
            # and each branch must drop the alternatives it did not take, or the decoder
            # is free to supply both and mean neither.
            import itertools
            allfields = {f for g in groups for f in g}
            for combo in itertools.product(*groups):
                sub = {k: v for k, v in props.items()
                       if k not in allfields - set(combo)}
                branches.append({"type": "object", "properties": sub,
                                 "required": ["op"] + list(combo) + list(spec["required"])})
        else:
            branches.append({"type": "object", "properties": props,
                             "required": ["op"] + list(spec["required"])})
    return {
        "$defs": {"stmt": {"oneOf": branches}, "pred": _pred_spec()},
        "type": "object",
        "properties": {"body": {"type": "array", "items": {"$ref": "#/$defs/stmt"}}},
        "required": ["body"],
    }


# Worked pairs, none of which is a ladder rung. Between them they demonstrate every
# construct the rungs need, on goals the benchmark never asks about.
SHOTS = [
    ("create a vm called web and put it on a network called dmz",
     {"body": [
         {"op": "call", "tool": "create_vm", "args": {"name": "web", "os_type": "linux"}},
         {"op": "call", "tool": "create_network", "args": {"net_name": "dmz"}},
         {"op": "call", "tool": "add_vm_to_network",
          "args": {"net_name": "dmz", "vm_name": "web"}}]}),
    ("stop every vm that is currently running",
     {"body": [
         {"op": "foreach", "select": {"kind": "vm", "status": "running"},
          "call": {"tool": "stop_vm", "args": {"name": "$item"}}}]}),
    ("create 4 vms, label them all 'staging', and make sure at least 4 carry that label",
     {"body": [
         {"op": "new", "var": "boxes", "kind": "vm", "amount": 4,
          "args": {"os_type": "linux"}},
         {"op": "foreach", "in": "$boxes",
          "call": {"tool": "add_label", "args": {"name": "$item", "label": "staging"}}},
         # The GOAL of this program, so `achieve` — this example ended in `ensure` and was
         # therefore teaching the old single-word semantics while the prompt taught the
         # split. The examples always win that argument, and rung 7 lost it.
         {"op": "achieve", "predicate": {"shape": "count",
                                         "select": {"kind": "vm", "label": "staging"},
                                         "gte": 4}}]}),
    # GRAFT + IF, on a goal that is not any rung: rung 11 is ping-and-STOP, this is
    # ping-and-LABEL. Demonstrating that a construct exists is not teaching the test —
    # withholding it would measure whether the model can guess syntax it has never seen.
    ("check whether web answers and label it 'up' if it does",
     {"body": [
         {"op": "call", "tool": "guest_ping", "args": {"name": "web"}, "graft": "answer"},
         {"op": "if", "cond": {"shape": "is", "of": "$answer.alive", "eq": True},
          "then": [{"op": "call", "tool": "add_label",
                    "args": {"name": "web", "label": "up"}}]}]}),
    # ACHIEVE as the whole program: state the end, let the harness plan it. Not rung 7 —
    # that one is about the 'prod' label at exactly 3.
    ("make sure at least 2 vms are running",
     {"body": [
         {"op": "achieve", "predicate": {"shape": "count",
                                         "select": {"kind": "vm", "status": "running"},
                                         "gte": 2}}]}),
    # ENSURE as a PRECONDITION — the shape the operator described: check the world is as
    # you expect BEFORE touching it, then act, then state the goal.
    ("if there is a golden image, clone it once and make sure two vms exist",
     {"body": [
         {"op": "ensure", "predicate": {"shape": "count",
                                        "select": {"kind": "vm", "name": "golden"},
                                        "eq": 1}},
         {"op": "new", "var": "copy", "kind": "vm", "from": "golden"},
         {"op": "achieve", "predicate": {"shape": "count", "select": {"kind": "vm"},
                                         "gte": 2}}]}),
    # A BLOCK body — a loop doing more than one thing per member. Deliberately WITHOUT a
    # conditional: the shape being taught is "a body can hold several statements", not
    # rung 11's answer. Whether the model composes a block with graft+if, having seen
    # each separately, is the thing worth measuring.
    ("snapshot every running vm and label each one 'backed-up'",
     {"body": [
         {"op": "foreach", "select": {"kind": "vm", "status": "running"},
          "do": [{"op": "call", "tool": "snapshot_create",
                  "args": {"name": "$item", "snap_name": "$item-backup"}},
                 {"op": "call", "tool": "add_label",
                  "args": {"name": "$item", "label": "backed-up"}}]}]}),
    # The carve-out and creating by copying, again on a non-rung goal.
    ("copy golden twice, and label every vm except golden itself 'derived'",
     {"body": [
         {"op": "new", "var": "copies", "kind": "vm", "amount": 2, "from": "golden"},
         {"op": "foreach", "select": {"kind": "vm", "not": {"name": "golden"}},
          "call": {"tool": "add_label", "args": {"name": "$item", "label": "derived"}}}]}),
]


def _tool_lines() -> str:
    """Each tool with the arguments it REQUIRES, read off the live catalog.

    Listing bare names was not enough and it showed: the model wrote
    `NEW vm(name: alpha)` without os_type and `snapshot_create` without snap_name, then
    got rejected for omitting things nothing had told it about. Asking a model to guess a
    signature and then failing it for guessing wrong measures the prompt, not the model.
    """
    try:
        from executor.command_catalog import REQUIRED_FIELDS
    except ImportError:                                    # pragma: no cover
        REQUIRED_FIELDS = {}
    out = []
    for t in _TOOLS:
        req = REQUIRED_FIELDS.get(t) or []
        out.append(f"  {t}({', '.join(req)})" if req else f"  {t}()")
    return "\n".join(out)


def _system() -> str:
    ops = "\n".join(f"  {op:8}— {spec['doc']}" for op, spec in config.OPS.items())
    try:
        from executor.command_catalog import REQUIRED_FIELDS
    except ImportError:                                    # pragma: no cover
        REQUIRED_FIELDS = {}
    kinds = "\n".join(
        # The creator's REQUIRED arguments belong on this line. Naming only the creator
        # made the author join two separate lists to learn that a vm needs os_type — it
        # managed for `NEW vm` and forgot for `NEW AMOUNT(5) vm`, which is what a
        # join-two-lists task fails like.
        f"  {k}: created by {v['create']}"
        + (f"(needs {', '.join(a for a in (REQUIRED_FIELDS.get(v['create']) or []) if a != 'name')})"
           if [a for a in (REQUIRED_FIELDS.get(v['create']) or []) if a != 'name'] else "")
        + f", queryable on {', '.join(v['attrs'])}"
        for k, v in config.KINDS.items())
    preds = "\n".join(f"  {name}: {spec['doc']}" for name, spec in config.PREDICATES.items())
    return (f"Express the operator's goal as a PROGRAM — statements run top to bottom.\n\n"
            f"{ops}\n\n"
            f"Resource kinds:\n{kinds}\n\n"
            f"ENSURE predicates — the ONLY things a postcondition may be built from. A "
            f"predicate is a check, never a loop or a call:\n{preds}\n\n"
            f"{config.PROMPT['reference']}\n{config.PROMPT['ordering']}\n"
            f"{config.PROMPT['grounding']}\n\n"
            f"Tools, with the arguments each one REQUIRES:\n{_tool_lines()}\n\n"
            f"NEW supplies the resource's own name; pass everything else the creator "
            f"needs in args, e.g. NEW vm(os_type: linux).")


def _messages(goal: str, shots: bool):
    msgs = [{"role": "system", "content": _system()}]
    if shots:
        for g, prog in SHOTS:
            msgs.append({"role": "user", "content": g})
            msgs.append({"role": "assistant", "content": json.dumps(prog)})
    msgs.append({"role": "user", "content": goal})
    return msgs


def author(goal: str, model: str, temp: float, shots: bool, timeout: int = 600, known_names=None):
    req = {"model": model, "stream": False, "format": program_schema(),
           "options": {"temperature": temp}, "messages": _messages(goal, shots)}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        prog = json.loads(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    ok, problems = validate(prog, known_names=known_names)
    return prog, ([] if ok else problems)


def world_state(world) -> str:
    """The world as the model must see it to CORRECT a program.

    Without this a revision is blind: rung 7 fails at six prod VMs, and the fix is to
    REMOVE three labels — which is unguessable from the goal alone, because the goal
    describes an end state and says nothing about what already exists. This is the
    "observe" in act-observe-correct, and it is the same grounding the English planner
    gets from the Active Library digest.
    """
    lines = []
    for name, vm in sorted(world.vms.items()):
        tags = sorted(vm["labels"] | vm.get("flags", set()))
        nets = sorted(vm.get("nets", set()))
        lines.append(f"  {name}: status={vm['status']}"
                     + (f" labels={','.join(tags)}" if tags else "")
                     + (f" networks={','.join(nets)}" if nets else ""))
    return ("CURRENT STATE:\n" + ("\n".join(lines) if lines else "  (no vms)")
            + f"\n  networks: {', '.join(sorted(world.nets)) or '(none)'}")


def repair(goal, program, problems, model, temp, shots, known_names=None, timeout=600):
    """Re-author a program that did not validate, given the validator's objections.

    Revision only ever fired on a failed ENSURE, so a program rejected before it ran got
    a precise, actionable objection — "there is no vm named 'golden'" — and no chance to
    answer it. That is a strange asymmetry: the structural objection is the SHARPER of
    the two, since it names the exact statement and the exact rule, while a failed
    postcondition only reports that the end state is wrong.

    Distinct from revise() because nothing has run: there is no world to diff against, no
    work to avoid repeating, and the whole program is in scope rather than the remaining
    difference. This is a rewrite, not a correction.
    """
    msgs = _messages(goal, shots)[:-1]
    msgs.append({"role": "user", "content": goal})
    msgs.append({"role": "assistant", "content": json.dumps(program)})
    msgs.append({"role": "user", "content":
                 "That program was REJECTED before running:\n"
                 + "\n".join(f"  - {p}" for p in problems[:6])
                 + f"\n\nThe goal was: {goal}\n"
                 "Write the whole program again, fixing exactly those objections and "
                 "changing nothing else. Nothing has run yet — the world is untouched."})
    req = {"model": model, "stream": False, "format": program_schema(),
           "options": {"temperature": temp}, "messages": msgs}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        prog = json.loads(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    ok, probs = validate(prog, known_names=known_names)
    return prog, ([] if ok else probs)


def revise(goal, program, world, why, model, temp, shots, timeout=600,
           reason="its own check REJECTED the result"):
    """Author a CORRECTIVE program, given what the last one did and what went wrong.

    The correction runs against the world the first program left behind — it does not
    start over. That is the whole point: a convergence goal can only be met by acting on
    the difference between what IS and what was asked for, and the difference only exists
    after the first attempt.
    """
    msgs = _messages(goal, shots)[:-1]
    msgs.append({"role": "user", "content": goal})
    msgs.append({"role": "assistant", "content": json.dumps(program)})
    msgs.append({"role": "user", "content":
                 f"That program ran, and {reason}: {why}\n\n"
                 f"{world_state(world)}\n\n"
                 f"The goal was: {goal}\n"
                 "Write a program that fixes ONLY the difference between the state above "
                 "and the goal. Do not repeat work already done — the state above is "
                 "what your last program left behind."})
    req = {"model": model, "stream": False, "format": program_schema(),
           "options": {"temperature": temp}, "messages": msgs}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        prog = json.loads(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    ok, problems = validate(prog)
    return prog, ([] if ok else problems)


def _seams(world):
    """Registry query + predicate evaluation, backed by the sim — the same two seams the
    orchestrator fills with the Active Library and the findings ledger."""
    def select(sel):
        kind = sel.get("kind")
        alias = (config.KINDS.get(kind) or {}).get("aliases") or {}

        def _matches(name, vm, filters):
            """One member against one set of filters. The SAME function answers both the
            include and the exclude side, so a carve-out cannot drift from the selection
            it carves out of — the exact bug that made `iso_lab` match `id=iso_lab2` in
            the network attach, arriving in a second place."""
            f = {alias.get(k, k): v for k, v in filters.items() if k != "not"}
            if "label" in f and f["label"] not in (vm["labels"] | vm.get("flags", set())):
                return False
            if "status" in f and vm["status"] != f["status"]:
                return False
            if "name" in f and name != f["name"]:
                return False
            if "os_type" in f and vm.get("os_type") != f["os_type"]:
                return False
            return True

        if kind == "network":
            return sorted(world.nets)
        carve = sel.get("not") or {}
        return [n for n, vm in sorted(world.vms.items())
                if _matches(n, vm, sel) and not (carve and _matches(n, vm, carve))]

    def holds(pred, scope):
        shape = pred.get("shape")
        if shape == "count":
            n = len(select(pred.get("select") or {}))
            for c, op in (("eq", "=="), ("gte", ">="), ("lte", "<=")):
                if c in pred:
                    good = {"==": n == pred[c], ">=": n >= pred[c], "<=": n <= pred[c]}[op]
                    return good, f"count is {n}, wanted {op} {pred[c]}"
            return False, "no comparator"
        if shape == "reach":
            # Members come from the SAME select() the rest of the language uses. Reading
            # only `tag` meant REACH(SELECT vm) — no filter, every vm, a perfectly legal
            # set — looked up the label None and found nobody. A predicate that ignores
            # its own operand's filters answers a different question than it was asked.
            members = select(pred.get("select") or {})
            floor = int(pred.get("min", 2))
            shared = world.common_networks(members) if members else set()
            good = len(members) >= floor and bool(shared)
            return good, f"reach over {len(members)} member(s), floor {floor} -> {good}"
        return False, f"unevaluated shape {shape}"
    return select, holds


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Constrained decoding + few-shot authoring")
    p.add_argument("-r", "--rung", type=int, action="append", help="default 4-7")
    p.add_argument("-m", "--model", default=BENCH_MODEL)
    p.add_argument("-t", "--temp", type=float, default=0.0)
    p.add_argument("-p", "--paraphrase", action="store_true")
    p.add_argument("--no-derive", action="store_true",
                   help="ablate harness-derived convergence — corrections come only from "
                        "the model. This is the before/after for rung 7.")
    p.add_argument("--revisions", type=int, default=2,
                   help="how many corrective programs to allow after a failed ENSURE "
                        "(default 2). The English path gets retries and re-planning; "
                        "without this the comparison is not like-for-like.")
    p.add_argument("--execute", action="store_true",
                   help="RUN each program against the sim and apply the rung's own "
                        "checker. Validity is structure; this is whether the program "
                        "MEANS its goal — the only grade that matters.")
    p.add_argument("--no-shots", action="store_true",
                   help="ablate the few-shot examples — isolates what they contribute")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if r.n in (a.rung or [4, 5, 6, 7])]
    shots = not a.no_shots
    print(f"author probe · model={a.model} temp={a.temp} · constrained decoding"
          f"{' · few-shot' if shots else ' · NO shots'}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}\n")

    valid = correct = revised = fixed = repairs = ungrounded = 0
    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        print(f"── rung {rung.n} ({rung.name})\n   goal: {goal}")
        # Seed the world BEFORE authoring, not after. The program is validated against
        # what exists — `FROM golden` is only meaningful if golden is there — so the
        # world has to precede the verdict. It also removes a smaller dishonesty: the
        # probe used to print [VALID] and then have run() reject the same program,
        # because the two calls were answering the question against different worlds.
        world = SimWorld()
        if rung.setup:
            rung.setup(world)
            world.calls.clear()
        prog, problems = author(goal, a.model, a.temp, shots,
                                known_names=world.names())
        if prog is None:
            print(f"   [ERROR] {problems[0]}\n")
            continue
        if problems and a.revisions:
            for attempt in range(a.revisions):
                fixed_prog, problems2 = repair(goal, prog, problems, a.model, a.temp,
                                               shots, known_names=world.names())
                if fixed_prog is None:
                    break
                repairs += 1
                print(f"          x{attempt + 1}| (rejected: {problems[0]})")
                prog, problems = fixed_prog, problems2
                if not problems:
                    break
        ok = not problems
        valid += ok
        print(f"   [{'VALID' if ok else 'INVALID'}] "
              f"{len(prog.get('body', []))} statements")
        for why in problems[:5]:
            print(f"          - {why}")
        for line in render(prog).splitlines():
            print(f"          | {line}")
        if a.execute and ok:
            sel, holds = _seams(world)
            # The bench stands in for the operator and always says yes — but it SAYS so,
            # because "how many rungs write a program that vouches for nothing" is worth
            # knowing. Silently auto-consenting would hide the very thing the gate exists
            # to surface.
            if consent.question(prog):
                ungrounded += 1
                print(f"          ?| NO GROUNDING: {consent.survey(prog)['acts']} acting "
                      f"statement(s), no ENSURE — operator would be asked here")
            res = run(prog, world.execute, select=sel, holds=holds,
                      known_names=world.names(), consent=True)
            print(f"          -> ran {len(res['calls'])} calls, "
                  f"ensure={'ok' if res['ok'] else res.get('failed')}"
                  f"{'' if res['ok'] else ' (' + str(res.get('why','')) + ')'}")
            # REVISION. A failed ENSURE is a plan failure carrying its own objection, and
            # the correction is authored against the world the last attempt LEFT — the
            # same act-observe-correct loop the English path already gets. Comparing a
            # single IR attempt against a path that retries was never a fair fight.
            # THE ORIGINAL POSTCONDITION IS THE STANDING TEST. A corrective program is
            # not trusted to carry its own: revision 2 on rung 7 dropped its ENSURE
            # entirely, `run()` returned ok because nothing was checked, and the loop
            # believed it had converged at six prod VMs. `ok` from a program with no
            # postcondition means "nothing was asserted", not "the goal holds" — the same
            # false success the closure audit exists to refuse, arriving through the
            # correction path. So the goal's own predicate is re-evaluated after every
            # round, whatever the fix chose to include.
            # THE GOAL IS THE `achieve` WHEN THERE IS ONE. Falling back to the last
            # ensure keeps older programs working, but an ensure is a ground check — a
            # precondition at the top of a procedure is not what the program was FOR, and
            # re-testing it after every revision would grade the wrong thing.
            body_ = prog.get("body", [])
            goal_pred = next((st["predicate"] for st in body_
                              if st.get("op") == "achieve"), None)
            if goal_pred is None:
                goal_pred = next((st["predicate"] for st in reversed(body_)
                                  if st.get("op") == "ensure"), None)

            def _goal_holds():
                if goal_pred is None:
                    return True, ""
                return holds(goal_pred, {})

            if res["ok"] and goal_pred is not None:
                good, why = _goal_holds()
                if not good:
                    res = {**res, "ok": False, "failed": "unsatisfied", "why": why}

            rounds = 0
            # `calls_failed` is revisable too, and for the same reason `unsatisfied` is:
            # the run produced a specific, actionable objection. Rung 8 attached VMs to a
            # network it never created — every call was rejected by the world, the
            # program asserted nothing, and the loop simply stopped, because the trigger
            # only ever named one of the two failure modes. A program that made only
            # failing calls is the case MOST worth re-planning, not the one to give up on.
            while (not res["ok"] and res.get("failed") in ("unsatisfied", "unachieved",
                                               "calls_failed")
                   and rounds < a.revisions):
                rounds += 1
                # DERIVE FIRST. Where the fix is computable it is computed: the harness
                # closes "six exist, three wanted" in one line, and the model provably
                # cannot — it oscillated 6->5->7->5 with state and objection in hand. The
                # model is asked only when derivation returns None, meaning the gap is
                # genuinely not computable (which shapes those are is stated in derive.py,
                # not guessed at here).
                # DERIVE ONLY FOR A GOAL. `unsatisfied` means a ground check was false —
                # the program assumed something about the world that was not true, and
                # computing a diff would paper over the wrong assumption instead of
                # rethinking it. That one is the model's to answer.
                derived = (None if (a.no_derive or res.get("failed") != "unachieved")
                           else derive(goal_pred, sel, res.get("scope")))
                if derived:
                    fix, fix_problems = {"body": derived}, []
                    print(f"          d{rounds}| (derived)")
                elif derived == []:
                    print(f"          -> revision {rounds}: predicate already satisfied")
                    break
                else:
                    # Say which failure actually happened. "Its own check rejected the
                    # result" is false when no check ran and the CALLS were rejected —
                    # and the objection is the only thing the corrective author has.
                    fix, fix_problems = revise(
                        goal, prog, world, res.get("why", ""), a.model, a.temp, shots,
                        reason=("its own check REJECTED the result"
                                if res.get("failed") == "unsatisfied" else
                                "the world REJECTED its calls, so it did nothing"))
                # A REVISION can be invalid too, and rung 8's was — rejected for
                # inventing a clone of a network. Repair applied to first authoring and
                # not to corrections, which left the sharpest objection in the run
                # unanswered at exactly the point the loop was trying to recover.
                for _ in range(a.revisions if fix_problems and fix is not None else 0):
                    fix2, fix_problems2 = repair(goal, fix, fix_problems, a.model,
                                                 a.temp, shots,
                                                 known_names=world.names())
                    if fix2 is None:
                        break
                    repairs += 1
                    print(f"          x{rounds}| (revision rejected: {fix_problems[0]})")
                    fix, fix_problems = fix2, fix_problems2
                    if not fix_problems:
                        break
                if fix is None or fix_problems:
                    print(f"          -> revision {rounds}: "
                          f"{'error' if fix is None else 'INVALID'} "
                          f"{(fix_problems or ['?'])[0]}")
                    break
                res = run(fix, world.execute, select=sel, holds=holds,
                             known_names=world.names(), consent=True)
                for line in render(fix).splitlines():
                    print(f"          r{rounds}| {line}")
                # Re-assert the GOAL, not the fix's own opinion of itself.
                if res["ok"]:
                    good, why = _goal_holds()
                    if not good:
                        res = {**res, "ok": False, "failed": "unsatisfied", "why": why}
                print(f"          -> revision {rounds}: {len(res['calls'])} calls, "
                      f"goal={'HOLDS' if res['ok'] else 'unmet'}"
                      f"{'' if res['ok'] else ' (' + str(res.get('why','')) + ')'}")
            passed = bool(rung.check(world))
            correct += passed
            if rounds:
                revised += 1
                fixed += passed
            print(f"          -> RUNG CHECKER: {'PASS' if passed else 'FAIL'}"
                  f"   world: {world.summary()}")
        print()

    print(f"── summary\n   structurally valid : {valid}/{len(rungs)}"
          + (f"  (after {repairs} repair round(s))" if repairs else ""))
    if a.execute:
        print(f"   ACHIEVES THE GOAL  : {correct}/{len(rungs)}")
        if revised:
            print(f"   needed revision    : {revised}  (of which recovered: {fixed})")
        if ungrounded:
            print(f"   NO GROUNDING       : {ungrounded}  (would need operator consent)")
    print("\n   Validity is structure + grounding only. Whether a program MEANS its goal\n"
          "   is for a human reading the rendered forms above — scoring that needs a\n"
          "   second definition of every goal, which is a benchmark grading itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
