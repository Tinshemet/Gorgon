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

from orchestrator.ai.planner.ir import (config, consent, derive, evaluate, master,
                                       observe, refs, render, run, validate)
from orchestrator.ai.planner.ir import intent as _intent
from orchestrator.ai.planner.ir import schema as _ir_schema
from orchestrator.ai.planner.ir.validate import _one_of_groups

from .ladder import BENCH_MODEL
from .mutate import MUTATIONS, apply as _mutate
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
    # EVERY ATTRIBUTE WITH A CLOSED VOCABULARY IS OFFERED AS AN ENUM, so the decoder
    # cannot invent a value. It did, repeatedly, and each time it looked like a model
    # failure: `status = 'not running'` matched nobody and ran zero calls (rung 5), and
    # `label = 'up'` was reached for because nothing said what `status` could be (rung
    # 12). `values_for` covers registry attributes and observed ones alike, so a new
    # constrained attribute is offered here by adding a manifest row and nothing else.
    for kind, k in config.KINDS.items():
        observed = config.observed(kind)
        for attr in list(k["attrs"]) + list(observed):
            if attr in props:
                continue
            spec = {"type": "string"}
            values = config.values_for(kind, attr)
            if values:
                spec["enum"] = values
            obs = observed.get(attr)
            if obs:
                # Observed attributes say where their answer comes from, because the
                # third value is only usable if the author knows what fills it in.
                spec["description"] = (
                    f"{obs.get('doc', attr)} '{config.OBSERVED_UNKNOWN}' means nothing "
                    f"has asked yet — call {obs.get('by', 'a probe')} first.")
            props[attr] = spec
    # MEMBERSHIP, offered on every attribute. Without it a PREDICATE can never speak
    # about particular machines — `foreach` has `IN [a, b]` and a predicate takes a select
    # and nothing else — so "make sure n1, n2 and n3 can all ping each other" had no
    # expression, and the author invented four different syntaxes for it across one day.
    for attr in [a for a in props if a != "kind"]:
        scalar = props[attr]
        props[attr] = {"anyOf": [
            scalar,
            {"type": "object",
             "properties": {"in": {"anyOf": [
                 {"type": "array", "items": {"type": "string"}, "minItems": 1},
                 {"type": "string", "description": "a $set bound by fetch"}]}},
             "required": ["in"],
             "description": f"{attr} is ANY of these — written INCLUDE {attr} = [a, b, c]"}]}
    if depth > 0:
        inner = {a: v for a, v in props.items() if a != "kind"}
        props["not"] = {"type": "object", "properties": inner,
                        "minProperties": 1,
                        "description": "EXCLUDE members matching these filters, e.g. "
                                       "{\"name\": \"db\"} for 'every vm except db'"}
        # GROUPS: OR and an explicit AND over whole filter sets. Depth-limited for the
        # same reason the carve-out is — a group inside a group inside a group is not a
        # query anyone should have to read.
        for group, word in (("any", "OR"), ("all", "AND")):
            props[group] = {"type": "array", "minItems": 2,
                            "items": {"type": "object", "properties": inner,
                                      "minProperties": 1},
                            "description": f"filter sets combined with {word}"}
    return {"type": "object", "properties": props, "required": ["kind"]}


def _field_schema(name: str, known=None):
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
    if name == "from":
        # THE ONE IDENTIFIER SLOT THAT IS GENUINELY CLOSED — you cannot copy what does not
        # exist. The validator has always said so and could only say it afterwards; the
        # master says it to the decoder. `_from_field` is shared with the ir schema so the
        # two surfaces cannot answer differently.
        return _ir_schema._from_field(doc, known)
    if name in ("select", "count"):
        # `count` is a select in counting position — same query, different answer. Giving
        # it the select schema is what lets the author say FETCH COUNT(...) at all.
        return _select_spec()
    if name == "amount":
        return {"anyOf": [
            {"type": "integer", "minimum": 0},
            {"type": "string", "description": "a $parameter"},
            {"type": "object", "properties": {
                "minus": {"type": "array", "minItems": 2, "maxItems": 2,
                          "description": "[target, \"$have\"] — create only the shortfall"}},
             "required": ["minus"]}],
            "description": doc}
    if name == "call":
        return _call_spec()
    if name in ("then", "else", "ifails", "do"):
        # minItems, so the decoder cannot emit an EMPTY branch. It did: rung 11 wrote a
        # perfectly correct `IF ... = false { stop_vm }` and preceded it with a dead
        # `IF ... = true { }`, which the validator rejected and which sank an otherwise
        # right program. Constraints belong where the decoder sees them; discovering an
        # empty block afterwards only lets you complain about it.
        return {"type": "array", "items": {"$ref": "#/$defs/stmt"},
                "minItems": 1, "description": doc}
    if name in ("cond", "predicate"):
        return {"$ref": "#/$defs/pred"}
    if name == "in":
        return {"anyOf": [{"type": "string"},
                          {"type": "array", "items": {"type": "string"}}],
                "description": doc}
    if name in ("var", "graft"):
        # CONSTRAIN THE DECODER, don't diagnose afterwards. A binding name has to be one
        # a reference can pronounce, and `-` cannot appear in one because it composes
        # names ($item-snap). Rung 6's paraphrase bound `red-net` in all three samples and
        # then could not read it back. A constraint the decoder sees cannot be violated;
        # a constraint only the validator knows costs a repair round to discover.
        return {"type": "string", "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
                "description": doc + " Letters, digits and underscores only — a name with "
                                     "'-' cannot be referred to."}
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
            if arity == "value":
                props["of"] = {"type": "string",
                               "description": "a $grafted.value, e.g. $answer.alive"}
            elif arity == "one":
                # A SINGLE CHECK, not an array of one. This offered an array for every
                # non-value arity, so the decoder wrote `NOT(of=[{...}])` exactly as
                # instructed and the validator — which follows the manifest's `arity:
                # one` — threw it out. Rung 8 (literal) and rung 5 (paraphrase) both died
                # on programs the executor would have run correctly. The manifest is the
                # authority; the schema now agrees with it, and `one_check` forgives the
                # old shape so nothing already written breaks.
                props["of"] = {"$ref": "#/$defs/pred",
                               "description": "the check this inverts"}
            else:
                props["of"] = {"type": "array", "items": {"$ref": "#/$defs/pred"},
                               "minItems": 2,
                               "description": "the checks this combines"}
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


def program_schema(want: str = None, known=None):
    """The full schema, assembled from the manifest so it cannot fall behind the language.

    Statement branches come from `ops`, their fields from the field catalogue, predicates
    from `predicates`. Adding a construct to the JSON offers it here with no edit — the
    claim the manifest makes everywhere else, applied to the one place that had quietly
    stopped honouring it.

    `want` is the operator's intent, and it reaches the DECODER here rather than only the
    prompt. `_system()` has told the author its rung in prose since the day intent was
    wired in, and prose is advisory: under `ensure:` the model could still emit `new`,
    write a program that creates machines, and have the whole thing thrown away by
    `intent.violations()` afterwards. Offering only the permitted branches makes that
    program unrepresentable instead of rejected — the same fact, moved from description to
    constraint.
    """
    branches = []
    for op in master.ops(want):
        spec = config.OPS[op]
        props = {"op": {"type": "string", "const": op, "description": spec["doc"]}}
        for f in spec["fields"]:
            props[f] = _field_schema(f, known)
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
    # THERE IS DELIBERATELY NO `FETCH` SHOT, and that is a MEASURED decision — do not add
    # one back without repeating the measurement.
    #
    # The reasoning for adding one was sound: FETCH + AMOUNT(N - $have) is the newest
    # construct and the only one with no worked example, and rung 13 needs exactly that
    # shape. So a shot was added on a non-rung goal ("bring the number of machines tagged
    # 'edge' up to four") and both columns were re-run. It made things WORSE:
    #
    #   rung 13 paraphrase   PASS (5 vms, 16 calls)  ->  FAIL (10 vms, 31 calls)
    #   rung 7  paraphrase   PASS (3 calls)          ->  PASS (8 calls, 3 junk vms
    #                                                     named extra1..3)
    #   rung 13 literal      FAIL                    ->  FAIL (never used FETCH at all)
    #
    # The shot taught topping a count UP, and rung 7 needs trimming DOWN (six prod vms,
    # wants three) — so the model matched the shot's SHAPE and created three machines it
    # had no use for, while the rung it was meant to help ignored it. This is the "shots
    # beat the prompt" effect pointed the wrong way, and it is the same reason the shots
    # are chosen as carefully as they are.
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


def _system(want: str = None) -> str:
    """The author's standing instructions.

    `want` is the OPERATOR'S INTENT — fetch, ensure or achieve — and supplying it is not
    a hint, it is the one fact decision 5 says the author cannot derive. "Make sure
    exactly three carry the prod label" is a verification if the operator wants to KNOW
    and a command if they want it TRUE, and nothing in the sentence, the world or the
    model decides which.

    MEASURED, and this is why it is wired in: rung 9 asks "make SURE n1, n2 and n3 can
    all ping each other". The model read it as a verification, wrote ENSURE, and a failed
    ENSURE routes to "the model rethinks" — so `derive()` never fired, and
    `_derive_reach`, which creates a network and attaches every member, is exactly rung
    9's fix sitting unreachable. The paraphrase of the same rung says "sort out whatever
    is stopping that", reads as a command, gets ACHIEVE, and passes in three calls. The
    PHRASING was choosing the engine. That is the failure decision 5 exists to remove,
    and the benchmark had never supplied the fact that removes it.
    """
    # Narrowed by the master, so the listing and the decoder agree. Describing `new` under
    # an `ensure:` and then refusing to decode it is the disagreement in miniature: the
    # model reasons its way to a construct it has no branch for, and the failure surfaces
    # as a malformed program rather than as the authority refusal it actually is.
    ops = "\n".join(f"  {op:8}— {config.OPS[op]['doc']}" for op in master.ops(want))
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
        # An attribute with a fixed vocabulary shows it. Naming `status` without saying
        # it is running-or-stopped is what let the author write 'not running' and match
        # nobody — the schema constrains the decoder, but the prompt is where a reader
        # learns what the words mean.
        + ", queryable on " + ", ".join(
            a + (f" ({'|'.join(config.values_for(k, a))})"
                 if config.values_for(k, a) else "")
            for a in v["attrs"])
        # Observed attributes are named SEPARATELY and with the tool that learns them,
        # because they behave differently: they read 'unknown' until something asks. A
        # flat list beside the registry attributes would invite exactly the mistake the
        # third value exists to prevent — selecting on one without probing first.
        + (f"; observed by asking: "
           + ", ".join(f"{a} (via {s.get('by', 'a probe')}, "
                       f"'{config.OBSERVED_UNKNOWN}' until then)"
                       for a, s in config.observed(k).items())
           if config.observed(k) else "")
        for k, v in config.KINDS.items())
    preds = "\n".join(f"  {name}: {spec['doc']}" for name, spec in config.PREDICATES.items())
    return (f"Express the operator's goal as a PROGRAM — statements run top to bottom.\n\n"
            f"{ops}\n\n"
            f"Resource kinds:\n{kinds}\n\n"
            f"ENSURE predicates — the ONLY things a postcondition may be built from. A "
            f"predicate is a check, never a loop or a call:\n{preds}\n\n"
            f"{config.PROMPT['reference']}\n{config.PROMPT['ordering']}\n"
            f"{config.PROMPT['grounding']}\n\n"
            f"{config.PROMPT['shape']}\n\n"
            f"Tools, with the arguments each one REQUIRES:\n{_tool_lines()}\n\n"
            f"NEW supplies the resource's own name; pass everything else the creator "
            f"needs in args, e.g. NEW vm(os_type: linux)."
            + (f"\n\n{_intent.instruction(want)}" if want else ""))


def _messages(goal: str, shots: bool, world=None, want=None):
    """The author's prompt. `world` is optional and was, for a long time, absent.

    That absence was an ASYMMETRY with no justification: revise() has always been handed
    the lab state, and the author never was. A blind author cannot notice that a goal
    already holds, so rung 13 — re-entry against a satisfied world — was not measuring
    idempotence at all. It was measuring whether a model can guess what it has not been
    shown. No operator writes a procedure without knowing what is in their lab.
    """
    msgs = [{"role": "system", "content": _system(want)}]
    if shots:
        for g, prog in SHOTS:
            msgs.append({"role": "user", "content": g})
            msgs.append({"role": "assistant", "content": json.dumps(prog)})
    msgs.append({"role": "user", "content":
                 f"{world_state(world)}\n\n{goal}" if world is not None else goal})
    return msgs


def author(goal: str, model: str, temp: float, shots: bool, timeout: int = 600,
           known_names=None, world=None, want=None):
    req = {"model": model, "stream": False,
           "format": program_schema(want, known_names),
           "options": {"temperature": temp}, "messages": _messages(goal, shots, world, want)}
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
        # What has been ASKED about this machine, beside what is stored about it. Omitted
        # while it reads `unknown`, so the line says "probed, and the answer was no"
        # rather than padding every machine with the absence of an observation — and so a
        # corrective program can tell the two apart, which is the distinction the whole
        # third value exists for.
        seen = [f"{attr}={observe.value(world.findings, 'vm', attr, name)}"
                for attr in config.observed("vm")
                if observe.value(world.findings, "vm", attr, name) != observe.unknown()]
        lines.append(f"  {name}: status={vm['status']}"
                     + (f" labels={','.join(tags)}" if tags else "")
                     + (f" networks={','.join(nets)}" if nets else "")
                     + (f" observed: {' '.join(seen)}" if seen else ""))
    return ("CURRENT STATE:\n" + ("\n".join(lines) if lines else "  (no vms)")
            + f"\n  networks: {', '.join(sorted(world.nets)) or '(none)'}")


def _distinct(problems):
    """The objections, deduplicated, each carrying how many statements hit it.

    THE REPAIR BUDGET IS SIX LINES and it was being spent on repetition. Rung 4 under the
    `verbose` mutation came back with the SAME objection four times — one per statement
    that made the same mistake — so four of six slots said one thing and every other
    problem the model needed to see was cut off. It then re-emitted an identical program
    twice and the rung was lost. Collapsing them keeps the budget carrying six DISTINCT
    complaints, and the count is worth more than the repetition: "in 4 statements" tells
    the model this is systematic, which one instance does not.
    """
    seen, out = {}, []
    for p in problems:
        # Objections are prefixed with the statement they belong to; the COMPLAINT is
        # what repeats, so group on that and keep the first location as the example.
        body = p.split(": ", 1)[1] if ": " in p else p
        if body in seen:
            seen[body][1] += 1
            continue
        seen[body] = [p, 1]
        out.append(body)
    return [f"{first} (in {n} statements)" if n > 1 else first
            for first, n in (seen[b] for b in out)]


def repair(goal, program, problems, model, temp, shots, known_names=None, timeout=600,
           want=None, world=None):
    """Re-author a program that did not validate, given the validator's objections.

    Revision only ever fired on a failed ENSURE, so a program rejected before it ran got
    a precise, actionable objection — "there is no vm named 'golden'" — and no chance to
    answer it. That is a strange asymmetry: the structural objection is the SHARPER of
    the two, since it names the exact statement and the exact rule, while a failed
    postcondition only reports that the end state is wrong.

    Distinct from revise() because nothing has run: no work to avoid repeating, and the
    whole program is in scope rather than the remaining difference. This is a rewrite,
    not a correction.

    IT SEES THE LAB. This said "there is no world to diff against" and passed no world —
    but the world EXISTS, it simply has not been modified yet, and knowing what is in it
    is exactly what turns a guess into a fix. Measured: a program reaching for
    `$item.networks[0]`, then `$item.net_name`, was iterating toward a network it could
    not name because nothing had told it one was there. Shown the lab it can write
    `SELECT network` or name `mesh0` outright.

    This is the THIRD time this same asymmetry has cost rungs. The author was blind while
    revise() was not (fixed earlier today, and it is what recovered rung 13); repair was
    blind while both of the others could see. Whenever a component here has to guess at
    something the harness already knows, that is the bug — not the guess.

    It matters more than it looks, because a validation rejection routes here rather than
    to revise(), and revise() is the better-equipped loop: it sees the world, the rejected
    calls, AND the harness can compute the fix through derive(). Catching a defect earlier
    is only an improvement if the loop that receives it can act on it.
    """
    msgs = _messages(goal, shots, want=want)[:-1]
    msgs.append({"role": "user", "content": goal})
    msgs.append({"role": "assistant", "content": json.dumps(program)})
    msgs.append({"role": "user", "content":
                 "That program was REJECTED before running:\n"
                 + "\n".join(f"  - {p}" for p in _distinct(problems)[:6])
                 + (f"\n\n{world_state(world)}" if world is not None else "")
                 + f"\n\nThe goal was: {goal}\n"
                 "Write the whole program again, fixing exactly those objections and "
                 "changing nothing else. Nothing has run yet — the world is untouched."})
    req = {"model": model, "stream": False,
           "format": program_schema(want, known_names),
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
           reason="its own check REJECTED the result", failures=None, want=None):
    """Author a CORRECTIVE program, given what the last one did and what went wrong.

    The correction runs against the world the first program left behind — it does not
    start over. That is the whole point: a convergence goal can only be met by acting on
    the difference between what IS and what was asked for, and the difference only exists
    after the first attempt.

    THE LAB IS TAKEN FROM THE WORLD IT WAS HANDED, and it had to be added: author() and
    repair() both name-check their output against `known_names` and revise() checked
    against nothing — so the one loop that runs when a world already exists was the one
    loop that could invent a `FROM` source with nobody objecting. It has the world right
    there in its arguments; the omission was that nobody asked it for the names.
    """
    known_names = world.names() if hasattr(world, "names") else None
    msgs = _messages(goal, shots, want=want)[:-1]
    msgs.append({"role": "user", "content": goal})
    msgs.append({"role": "assistant", "content": json.dumps(program)})
    # BOTH objections, when there are both. Measured, not assumed: a goal shortfall names
    # the SYMPTOM ("count is 0, wanted >= 3") while a rejected call names the CAUSE ("no
    # network named core"). Given only the shortfall the model kept re-attaching to a
    # network that did not exist, three rounds running; given the rejection it created the
    # network immediately. Withholding the failures because a postcondition was present
    # was throwing away the more actionable half.
    detail = why
    if failures:
        seen, lines = set(), []
        for f in failures:
            msg = f.get("error") or "call failed"
            if msg not in seen:
                seen.add(msg)
                lines.append(f"  - {f.get('tool')}: {msg}")
        detail = f"{why}\n\nCalls the world REJECTED:\n" + "\n".join(lines)
    msgs.append({"role": "user", "content":
                 f"That program ran, and {reason}: {detail}\n\n"
                 f"{world_state(world)}\n\n"
                 f"The goal was: {goal}\n"
                 "Write a program that fixes ONLY the difference between the state above "
                 "and the goal. Do not repeat work already done — the state above is "
                 "what your last program left behind."})
    req = {"model": model, "stream": False,
           "format": program_schema(want, known_names),
           "options": {"temperature": temp}, "messages": msgs}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        prog = json.loads(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    ok, problems = validate(prog, known_names=known_names)
    return prog, ([] if ok else problems)


def _seams(world):
    """Registry query + predicate evaluation, backed by the sim — the same two seams the
    orchestrator fills with the Active Library and the findings ledger."""
    def select(sel, scope=None):
        kind = sel.get("kind")
        alias = (config.KINDS.get(kind) or {}).get("aliases") or {}

        def _matches(name, vm, filters, scope=None):
            """One member against one set of filters. The SAME function answers both the
            include and the exclude side, so a carve-out cannot drift from the selection
            it carves out of — the exact bug that made `iso_lab` match `id=iso_lab2` in
            the network attach, arriving in a second place."""
            # GROUPS FIRST — `any` is OR, `all` an explicit AND, each branch a filter
            # set answered by this same function, so a group can never mean something the
            # flat form does not.
            for group, combine in (("any", any), ("all", all)):
                kids = filters.get(group)
                if isinstance(kids, list) and kids:
                    if not combine(_matches(name, vm, k, scope) for k in kids):
                        return False
            f = {alias.get(k, k): v for k, v in filters.items()
                 if k not in ("not", "any", "all")}
            # MEMBERSHIP — the attribute is ANY of these. Resolved through the same refs
            # the rest of the language uses, so a bound set works beside a literal list.
            for attr in list(f):
                spec = f[attr]
                if isinstance(spec, dict) and "in" in spec:
                    want = spec["in"]
                    if isinstance(want, str):
                        want = refs.resolve(want, scope or {})
                    want = want if isinstance(want, (list, tuple, set)) else [want]
                    got = (name if attr == "name" else vm.get(attr))
                    if attr == "label":
                        carried = vm["labels"] | vm.get("flags", set())
                        if not (carried & set(want)):
                            return False
                    elif attr == "network":
                        if not (vm.get("nets", set()) & set(want)):
                            return False
                    elif got not in want:
                        return False
                    f.pop(attr)
            # A NON-SCALAR FILTER CANNOT MATCH, and must not raise. The validator now
            # refuses `label = '$vms'` where $vms holds a set, but a value can still
            # arrive non-scalar at run time — a parameter supplied at invocation is not
            # knowable statically. Before this, `f["label"] not in {...}` hit a list, and
            # an unhashable type took down a 13-rung run at rung 9 with a TypeError
            # instead of failing one program. A seam that crashes destroys the
            # measurement around it, which is the same reason render.py may not raise.
            if any(isinstance(v, (list, dict, set, tuple)) for v in f.values()):
                return False
            # OBSERVED attributes are read out of the findings ledger, never off the
            # record — that is the whole of decision 6. Delegated to `observe.matches` so
            # the rule that `unknown` matches neither `true` nor `false` lives in one
            # place: a seam that reimplemented it would be free to get it wrong, and the
            # way it gets it wrong is by treating unprobed as dead.
            for attr, wanted in f.items():
                if observe.matches(world.findings, kind or "vm", attr, name, wanted) is False:
                    return False
            if "label" in f and f["label"] not in (vm["labels"] | vm.get("flags", set())):
                return False
            if "status" in f and vm["status"] != f["status"]:
                return False
            if "name" in f and name != f["name"]:
                return False
            if "os_type" in f and vm.get("os_type") != f["os_type"]:
                return False
            # Membership, not equality: a machine sits on a SET of networks. Written as
            # equality (`network = 'core'`) because that is how the operator says it —
            # "is it on core" — and the query language should not make a reader learn
            # which attributes happen to be multi-valued.
            if "network" in f and f["network"] not in vm.get("nets", set()):
                return False
            return True

        if kind == "network":
            return sorted(world.nets)
        carve = sel.get("not") or {}
        return [n for n, vm in sorted(world.vms.items())
                if _matches(n, vm, sel, scope)
                and not (carve and _matches(n, vm, carve, scope))]

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
        if shape == "disjoint":
            # DECLARED SINCE DAY ONE, NEVER EVALUABLE. The manifest lists it, the schema
            # offers it, the validator accepts it and the renderer prints it — and this
            # seam fell through to "unevaluated shape disjoint", which a postcondition
            # then counts as FAILED. So `ACHIEVE DISJOINT($reds, $blues)` — a correct
            # statement of rung 6's goal — could not hold in any world, and burned three
            # revision rounds saying so. Exactly the shape of the composite-predicate bug
            # found earlier, in a third predicate, because nothing asserts that every
            # declared shape has an evaluator.
            #
            # Its operand is `sets`: names of sets the program bound, not a query. Each
            # resolves through the same refs the rest of the language uses, so a set built
            # by `new` (a list) and one bound by `fetch` both work.
            raw = pred.get("sets") or []
            resolved, unknown = [], []
            for ref in raw:
                val = refs.resolve(ref, scope) if isinstance(ref, str) else ref
                if isinstance(val, str) and refs.names(val):
                    unknown.append(ref)          # never bound — still a $token
                    continue
                resolved.append({val} if isinstance(val, str) else set(val or ()))
            if unknown or len(resolved) < 2:
                return False, (f"disjoint needs two or more bound sets; "
                               f"{', '.join(unknown) or 'too few'} not in scope")
            overlap = set()
            for i, a in enumerate(resolved):
                for b in resolved[i + 1:]:
                    overlap |= (a & b)
            return (not overlap), (f"disjoint over {len(resolved)} sets -> "
                                   + ("no shared member"
                                      if not overlap else
                                      f"shared: {', '.join(sorted(overlap))}"))
        return False, f"unevaluated shape {shape}"
    return select, holds


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Constrained decoding + few-shot authoring")
    p.add_argument("-r", "--rung", type=int, action="append", help="default 4-7")
    # THE AUTHOR SEES THE LAB, and this is no longer opt-in. The docstring on _messages
    # has argued since it was written that a blind author is "an ASYMMETRY with no
    # justification" and that rung 13 "was not measuring idempotence at all" without it —
    # and then left the flag off by default, so every ladder run measured the thing that
    # comment says is not worth measuring. It is the same defect as the 07-25 grounding
    # parity fix: the planner was grounded strictly weaker than the chat path, invented an
    # identifier, and looked like a weak model. No operator writes a procedure without
    # knowing what is in their lab. Kept as an ABLATION so the contribution stays
    # measurable, which is what the flag was actually good for.
    p.add_argument("--blind-author", action="store_true",
                   help="ablate the lab state the author is shown — the old default, "
                        "which made rung 13 measure guesswork rather than idempotence")
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
    # THE OPERATOR'S INTENT, supplied rather than inferred (decision 5). Every rung in
    # this ladder is a COMMAND — each one's checker measures a CHANGED lab, so "the
    # operator wants it done" is simply true of all thirteen. Withholding it makes the
    # model guess a fact that lives in a person's head, and rung 9 measured the cost of
    # that guess: the literal wording reads as a verification and fails, the paraphrase
    # reads as a command and passes in three calls. `--intent` overrides, and `--no-intent`
    # ablates it back to guessing so the contribution stays measurable.
    p.add_argument("--intent", default=_intent.ACHIEVE,
                   choices=[_intent.FETCH, _intent.ENSURE, _intent.ACHIEVE],
                   help="what the operator wants back (default: achieve — every rung "
                        "here is a command)")
    p.add_argument("--no-intent", action="store_true",
                   help="ablate the operator's intent — the author must guess, which is "
                        "what decision 5 says it cannot do")
    # THE THIRD COLUMN, mechanical rather than written. The two hand-written columns are
    # not equal-difficulty — measured — and an author cannot audit their own paraphrases
    # for leakage, because the leak is the part they thought was clarity. A mutation has
    # no authorial intent: whatever it does to rung 9 it does to rung 3. See mutate.py
    # for the meaning-preservation rules that keep it from corrupting the goal.
    p.add_argument("--mutate", choices=sorted(MUTATIONS),
                   help="perturb each goal by this rule before authoring")
    p.add_argument("--no-shots", action="store_true",
                   help="ablate the few-shot examples — isolates what they contribute")
    a = p.parse_args(argv)

    rungs = [r for r in RUNGS if r.n in (a.rung or [4, 5, 6, 7])]
    shots = not a.no_shots
    want = None if a.no_intent else a.intent
    print(f"author probe · model={a.model} temp={a.temp} · constrained decoding"
          f"{' · few-shot' if shots else ' · NO shots'}"
          f"{' · PARAPHRASE' if a.paraphrase else ''}"
          f"{' · MUTATED:' + a.mutate if a.mutate else ''}"
          f"{' · intent=' + want if want else ' · NO intent'}\n")

    valid = correct = revised = fixed = repairs = ungrounded = 0
    noresult = 0
    for rung in rungs:
        goal = (rung.paraphrase or rung.goal) if a.paraphrase else rung.goal
        unmutated = False
        if a.mutate:
            mutated = _mutate(goal, a.mutate)
            unmutated = mutated == goal
            goal = mutated
        print(f"── rung {rung.n} ({rung.name})\n   goal: {goal}")
        if unmutated:
            # SAY SO, and say it UNDER the rung it belongs to — this printed before the
            # header, so it read as a note about the previous rung and I misattributed it
            # once already. A mutation that does not apply contributes nothing, and a
            # column silently made of unmutated goals would read as robustness.
            print(f"   [{a.mutate}] does not apply to this goal — unchanged")
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
                                known_names=world.names(),
                                world=None if a.blind_author else world, want=want)
        if prog is None:
            # A NON-RESULT IS NOT A FAILURE. A model call that timed out says nothing
            # about the language, and folding it into the score quietly deflates every
            # column it lands in — rung 13 timed out twice today and was counted as a
            # miss both times. Same distinction run_all.py already draws for suites:
            # NO-RESULT fails the run and is REPORTED as no-result, never as a failure.
            noresult += 1
            print(f"   [NO RESULT] {problems[0]} — not counted as a failure\n")
            continue
        if problems and a.revisions:
            for attempt in range(a.revisions):
                fixed_prog, problems2 = repair(goal, prog, problems, a.model, a.temp,
                                               shots, known_names=world.names(),
                                               want=want,
                                               world=None if a.blind_author else world)
                if fixed_prog is None:
                    break
                repairs += 1
                print(f"          x{attempt + 1}| (rejected: {problems[0]})")
                # AN IDENTICAL REPAIR CANNOT MAKE PROGRESS. At temp 0 the same program
                # plus the same objection deterministically yields the same program — so
                # a second identical round is a 600-second model call spent re-deriving
                # text we already hold. Rung 3 burned both rounds that way, emitting the
                # duplicate-creation program twice verbatim. Stopping is not giving up: it
                # is declining to pay for an answer already known, and saying so out loud
                # so the run does not read as though two attempts were made.
                if fixed_prog == prog:
                    print(f"          x{attempt + 1}| repair returned the SAME program — "
                          f"nothing further to try at this temperature")
                    prog, problems = fixed_prog, problems2
                    break
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
            # `intent=` reaches the runtime too, so the authority check in run() —
            # built, enforced, and never once exercised by this benchmark — actually
            # runs against every program the ladder produces.
            res = run(prog, world.execute, select=sel, holds=holds,
                      known_names=world.names(), consent=True, intent=want)
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
            # NESTED BLOCKS INCLUDED, BUT NOT LOOP-LOCAL ONES — and the second half of
            # that sentence was learned the hard way, by breaking it.
            #
            # Searching only the TOP level meant a program whose one verdict sat inside a
            # loop had `goal_pred = None`, `_goal_holds()` returned True unconditionally,
            # and every revision "passed" against nothing (rung 9: `goal=HOLDS` while the
            # checker said FAIL). Walking nested blocks fixed that and immediately broke
            # rung 11 the opposite way: it picked up an in-loop
            # `ENSURE COUNT(SELECT vm WHERE name = '$item') = 1` as the STANDING goal, and
            # outside its loop `$item` resolves to nothing, so the predicate matched zero
            # rows and no correction could ever satisfy it. A perfectly correct revision
            # was reported `goal=unmet`.
            #
            # The rule that covers both: the standing goal must be re-evaluable in the
            # program's OUTER scope. A predicate mentioning the loop variable is a
            # per-iteration check and cannot stand for the program.
            member = f"{config.SIGIL}{config.LOOP_VAR}"
            candidates = [st for st in consent._walk(prog.get("body", []))
                          if st.get("predicate") is not None
                          and member not in json.dumps(st["predicate"])]
            goal_pred = next((st["predicate"] for st in candidates
                              if st.get("op") == "achieve"), None)
            if goal_pred is None:
                goal_pred = next((st["predicate"] for st in reversed(candidates)
                                  if st.get("op") == "ensure"), None)

            def _goal_holds():
                # `evaluate`, not the raw leaf reader. Calling `holds` directly here lost
                # composites and IS() — an ACHIEVE built from AND(...) came back
                # "unevaluated shape all" and was counted as FAILED, so a goal that
                # actually held kept the revision loop running. The visitor had the right
                # logic; this path was reaching around it.
                if goal_pred is None:
                    return True, ""
                return evaluate(goal_pred, {}, holds)

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
                                if res.get("failed") in ("unsatisfied", "unachieved")
                                else "the world REJECTED its calls, so it did nothing"),
                        failures=res.get("failures"), want=want)
                # A REVISION can be invalid too, and rung 8's was — rejected for
                # inventing a clone of a network. Repair applied to first authoring and
                # not to corrections, which left the sharpest objection in the run
                # unanswered at exactly the point the loop was trying to recover.
                for _ in range(a.revisions if fix_problems and fix is not None else 0):
                    fix2, fix_problems2 = repair(goal, fix, fix_problems, a.model,
                                                 a.temp, shots,
                                                 known_names=world.names(), want=want,
                                                 world=None if a.blind_author else world)
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
                             known_names=world.names(), consent=True, intent=want)
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

    scored = len(rungs) - noresult
    print(f"── summary\n   structurally valid : {valid}/{len(rungs)}"
          + (f"  (after {repairs} repair round(s))" if repairs else ""))
    if a.execute:
        print(f"   ACHIEVES THE GOAL  : {correct}/{scored}"
              + (f"   ({noresult} NOT SCORED — no result)" if noresult else ""))
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
