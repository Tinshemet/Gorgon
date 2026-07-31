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
from typing import Sequence

import argparse
import os
import json
import sys
import urllib.request

from orchestrator.ai.planner.ir import (config, consent, derive, evaluate, gate,
                                       master, observe, refs, render, run, validate)
from orchestrator.ai.planner import clause_ledger
from orchestrator.ai.planner.ir import intent as _intent
from orchestrator.ai.planner.score import _first_tool_call
from orchestrator.ai.planner.ir import schema as _ir_schema
from orchestrator.ai.planner.ir.validate import _one_of_groups

from orchestrator.ai.planner.ir.sanitize import kinds as _sanitize_kinds
from orchestrator.ai.planner.ir.sanitize import sanitize_text as _sanitize_text
from orchestrator.ai.planner.ir.sanitize import sanitize as _sanitize
from . import pinned
from .ladder import BENCH_MODEL
from .mutate import MUTATIONS, apply as _mutate
from .rungs import RUNGS
from orchestrator.ai.planner.ir import execute as _ir_execute
from .sim_world import SimWorld
# THE SEAMS LIVE IN `seams.py` — one authority. They were defined here and, in a
# weaker form, a second time in `run_program`, where the missing `not`/`in`/`any`/
# `all` meant a carve-out was silently ignored and `disjoint` was never evaluated.
# Imported under the old private name so every call site here, and the re-export
# `tree_probe` relies on, keep working.
from .seams import seams as _seams

_TOOLS = SimWorld.tools()

def _decode_failure(err: str) -> str:
    """Which KIND of non-reply this was — one classifier, shared by author and repair.

    The three are different bugs wearing one exception. `Extra data` is a VALID program
    with prose after it: the model answered correctly and a strict reader threw the answer
    away, which is ours. An empty body is the model declining to emit. Anything else is a
    decoder that produced non-JSON under a schema that forbids it, which is the channel.
    Collapsing them hid a correct rung-11 repair inside a bucket labelled "no result" for
    a day.
    """
    if "Extra data" in err:
        return "trailing_prose"
    if "Expecting value: line 1 column 1" in err:
        return "empty"
    return "malformed"


# Every artifact removed this run. A pass that cleans without counting makes the
# artifact rate unmeasurable, which is precisely how it would get worse unnoticed.
_SANITISED = []

# THE CONTEXT THE PROBE ASKS FOR. It sent none, so every authoring, repair and revision
# call ran at ollama's DEFAULT — measured at 4096 on this host — while the config declares
# 8192 and ladder.py has always sent it. Two harnesses measuring the same model at
# different context sizes is not a comparison, and a repair prompt already reaches ~2700
# tokens before the program is written.
from orchestrator.ai.chat.ollama_client import _OLLAMA as _OLLAMA_CFG
_OLLAMA_CTX = _OLLAMA_CFG["num_ctx"]
from collections import Counter as _Counter
_OLLAMA = "http://localhost:11434/api/chat"


def _call_spec():
    return {"type": "object",
            "properties": {"tool": {"type": "string", "enum": list(_TOOLS)},
                           "args": {"type": "object"}},
            "required": ["tool", "args"]}


def _select_spec(depth: int = 1):
    """DELEGATED to `ir/schema.select_spec` since 2026-07-29 — this is now one line.

    It lived here, and ONLY here, for its whole life. `ir/schema.py` serves production and
    `lower.leaf_schema`, and on both of them `select` stayed the bare object the field
    catalogue declares — so the tree path could not write a select that named anything
    while this probe wrote them perfectly well, and rung 4 died on *"reach needs
    `select`"* three times over. The reasoning, and the four defects that shaped it, moved
    with the code.

    `from` was already delegated in this direction, for the reason given at its call site:
    the two surfaces cannot be allowed to answer differently. An invariant now holds them
    to it rather than trusting that nobody edits one copy.
    """
    return _ir_schema.select_spec(depth)


def _field_schema(name: str, known=None):
    """DELEGATED to `ir/schema._field` since 2026-07-30 (H2) — this is now one line.

    It was the RICHER of the two builders for its whole life, and that was the defect. Six
    constructs lived only here — `amount`'s minus form, `call`'s tool enum, block arrays and
    their minItems, `cond`, the var/graft name pattern, `in` — each earned by a measured
    failure in this probe, and none of them ever reached `ir/schema.py`, which serves
    production AND `lower.leaf_schema`. So the ladder measured a language the other two
    surfaces could not write, which is H2 stated as a consequence rather than a worry.

    Two things differ between the surfaces and both are now PARAMETERS rather than forks:
    `refs` (constrained decoding names a `$defs` entry; a tool-call schema inlines) and
    `tools` (this probe enumerates its SimWorld, production the live registry).
    """
    return _ir_schema._field(name, known, refs=_ir_schema.DEFS, tools=list(_TOOLS))


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
            props["select"] = {"$ref": "#/$defs/sel"}
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


def program_schema(want: str = None, known=None, quantifier: str = None):
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
    for op in master.ops(want, quantifier):
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
    # A PLACE TO LOOK BEFORE WRITING, and it comes FIRST on purpose.
    #
    # The schema had ONE property — `body` — so the decoder forced statement 1 before the
    # model had emitted a single token about the lab it was given. That is the documented
    # failure mode of constrained decoding: format restriction costs 10-30% of reasoning
    # accuracy, and the mechanism is ORDERING — the model is made to produce answer fields
    # before it can finish reasoning ("Let Me Speak Freely?", arXiv 2408.02442; the
    # structured-output survey at arXiv 2501.10868 recommends reasoning fields BEFORE
    # conclusion fields for exactly this reason).
    #
    # RUNG 13 IS THAT FAILURE IN ONE LINE. The lab already holds five machines, the goal
    # says "TAKE 5 vms" — reworded 2026-07-28 so neither column says create — and the model
    # writes `NEW AMOUNT(5) vm` anyway. The validator objects precisely ("the lab already
    # holds 5 vm(s) — AMOUNT makes 5 MORE") and TWO repair rounds return the same program.
    # It is not refusing the correction; it never had anywhere to notice the lab at all.
    #
    # Property ORDER is the whole mechanism, so this is not cosmetic: JSON is generated in
    # order, so a field declared first is written first, and the tokens spent on it are
    # available to everything after.
    # OFF BY DEFAULT so the enforcement fix is measured alone. This field was added while
    # the grammar was dead and never once emitted; now that `from`'s pattern is gone it
    # would arrive in the same run, and two changes in one measurement attribute to
    # neither. MEDUSA_READING=1 is its own arm.
    if os.environ.get("MEDUSA_READING") == "1":
        props_top = {
            "reading": {
                "type": "string",
                "description": ("FIRST, one short sentence: what does the lab ALREADY hold "
                                "that this goal asks for? Name what exists so you do not "
                                "make it a second time. If nothing relevant exists, say so."),
            },
            "body": {"type": "array", "items": {"$ref": "#/$defs/stmt"}},
        }
        required = ["reading", "body"]
    else:
        props_top = {"body": {"type": "array", "items": {"$ref": "#/$defs/stmt"}}}
        required = ["body"]
    return {
        "$defs": {"stmt": {"oneOf": branches}, "pred": _pred_spec(),
                  # ONE `select`, referenced rather than inlined six times.
                  "sel": _select_spec()},
        "type": "object",
        "properties": props_top,
        "required": required,
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



def _blinded(names, offered, whole):
    """The prompt fragments worth sending, joined. `ir.methods.wanted` owns the rule, so
    the bench and production builders cannot read the same tag two ways."""
    out = [config.PROMPT[n] for n in names if config.wanted(n, offered, whole)]
    return ("\n".join(out) + "\n\n") if out else ""


def _system(want: str = None, ops: Sequence[str] = None) -> str:
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
    # BLINDERS. `ops` is what THIS call can emit — on the staged path the decomposer
    # already decided it, so narrowing costs no extra call. Intersected with the
    # master, never replacing it, so a blinder can only narrow and can never offer an
    # op the operator's intent forbids.
    # `ops` is rebound below to the joined doc text, so capture the blinder first.
    # `_whole` is False exactly when this call was narrowed to fewer ops than the intent
    # allows — i.e. a single leaf — which is what decides the whole-program-only fragments.
    _blind = None if ops is None else set(ops)
    _offer = master.ops(want)
    if _blind is not None:
        _offer = [o for o in _offer if o in _blind]
    _whole = _blind is None or len(_offer) > 1
    ops = "\n".join(f"  {op:8}— {config.OPS[op]['doc']}" for op in _offer)
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
            + _blinded(("reference", "ordering", "grounding", "shape"), _offer, _whole)
            + f"Tools, with the arguments each one REQUIRES:\n{_tool_lines()}\n\n"
            f"NEW supplies the resource's own name; pass everything else the creator "
            f"needs in args, e.g. NEW vm(os_type: linux)."
            + (f"\n\n{_intent.instruction(want)}" if want else ""))


def _messages(goal: str, shots: bool, world=None, want=None, ops=None):
    """The author's prompt. `world` is optional and was, for a long time, absent.

    That absence was an ASYMMETRY with no justification: revise() has always been handed
    the lab state, and the author never was. A blind author cannot notice that a goal
    already holds, so rung 13 — re-entry against a satisfied world — was not measuring
    idempotence at all. It was measuring whether a model can guess what it has not been
    shown. No operator writes a procedure without knowing what is in their lab.
    """
    msgs = [{"role": "system", "content": _system(want, ops)}]
    if shots:
        for g, prog in SHOTS:
            msgs.append({"role": "user", "content": g})
            msgs.append({"role": "assistant", "content": json.dumps(prog)})
    msgs.append({"role": "user", "content":
                 f"{world_state(world)}\n\n{goal}" if world is not None else goal})
    return msgs


# THE QUANTIFIER ROUTER, in front of authoring. Off unless MEDUSA_ROUTE=1, because it
# costs an extra model call per authoring call and its value is unproven on this path.
#
# MEASURED BEFORE WIRING (`quantifier_probe`, n=3): the router answers 15/16 on hand-cut
# clauses. And routing every ladder GOAL first showed the first quantifier table would have
# STARVED FOUR RUNGS — that check cost one call per rung instead of a 25-minute sweep, and
# the table was corrected before anything ran.
#
# WHAT THIS CANNOT DO, stated so the result is not over-read: the quantifier is a per-CLAUSE
# property and this narrows a per-PROGRAM schema. Rung 8 carries three clauses (all / not /
# single) and routes as `not`, which licenses everything — so this cannot fix rung 8. Only
# `single` goals narrow at all, and they narrow by exactly one op: `foreach`. The value
# appears with per-leaf emission (staged lowering); this is the seam that will feed it.
_ROUTE = os.environ.get("MEDUSA_ROUTE") == "1"


def _route_quantifier(goal: str, model: str, timeout: int = 120):
    """all/any/single/not for a goal, or None if the router did not answer. NEVER raises:
    a router that fails must leave authoring exactly as it was, not take the cell down.

    THE DETERMINISTIC RULE ANSWERS FIRST, and only what it can. `quantifier_rule` reads the
    SHAPE of the clause — an exclusion marker, or a universal quantifier with or without a
    modifier on its head noun — and returns None for everything else. Measured 2026-07-30:

        tuning corpus    model alone 15/16 · rule+model 16/16 · 9 of 16 calls saved
        HELD-OUT corpus  model alone  8/10 · rule+model 10/10 · 7 of 10 calls saved

    The held-out ten were written and committed BEFORE the rule was tuned, and the rule
    fired 7 times with 0 wrong on clauses it had never seen. It fixed exactly the two the
    model got wrong, and both were the same shape: a filter written as an ADJECTIVE
    ("restart every stopped machine", "archive every red vm"), where the model reads the
    adjective as part of the kind. The relative-clause form it already handled.

    So this is cheaper AND more accurate, which is not the usual trade. It is safe in the
    direction that matters because the rule declines rather than guesses — a wrong
    deterministic answer would narrow the schema and make a correct program
    unrepresentable, and there is no such answer in 26 scored clauses.
    """
    from . import quantifier_rule
    by_shape = quantifier_rule.classify(goal)
    if by_shape is not None:
        return by_shape
    from .quantifier_probe import _tool as _q_tool, _system as _q_system, _recover as _q_rec
    try:
        req = {"model": model, "stream": False, "tools": [_q_tool()],
               "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(),
               "messages": [{"role": "system", "content": _q_system()},
                            {"role": "user", "content": goal}]}
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        reply = json.loads(r.read())
        name, args = _first_tool_call(reply)
        q = (args or {}).get("quantifier") if name == "quantify" else None
        return q or _q_rec(reply)
    except Exception as exc:
        # NEVER SILENT. A bare swallow here hid a NameError for the whole first wiring
        # attempt — `_first_tool_call` was used and never imported, the router returned
        # None every time, and authoring carried on looking exactly as if the flag were
        # off. A fallback that cannot be distinguished from "nothing to do" is the
        # false-success class this project refuses everywhere else.
        print(f"          [route] UNAVAILABLE ({type(exc).__name__}: {exc}) "
              f"— authoring unnarrowed")
        return None


def author(goal: str, model: str, temp: float, shots: bool, timeout: int = 600,
           known_names=None, world=None, want=None):
    quantifier = _route_quantifier(goal, model) if _ROUTE else None
    if quantifier:
        print(f"          [route] {quantifier}")
    req = {"model": model, "stream": False,
           "format": program_schema(want, known_names, quantifier=quantifier),
           "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(temp), "messages": _messages(goal, shots, world, want)}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        # THE TEXT STAGE FIRST. The sanitiser's reach used to stop at a parsed program,
        # so the most common residue there is — prose after the closing brace — killed the
        # parse and the whole answer was discarded before the instrument could see it.
        # `sanitize_text` reads ONE value and returns what follows as an artifact.
        prog, _artifacts = _sanitize_text(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    # THEN THE PROGRAM STAGE, the same order production uses. The removals are stashed
    # rather than returned, so the three authoring loops keep their two-value signature
    # and the caller still gets the account.
    prog, _more = _sanitize(prog)
    _artifacts = _artifacts + _more
    if _artifacts:
        _SANITISED.extend(_artifacts)
    ok, problems = validate(prog, known_names=known_names,
                            census=world.census() if world is not None else None)
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
           "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(temp), "messages": msgs}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        # THE TEXT STAGE FIRST. The sanitiser's reach used to stop at a parsed program,
        # so the most common residue there is — prose after the closing brace — killed the
        # parse and the whole answer was discarded before the instrument could see it.
        # `sanitize_text` reads ONE value and returns what follows as an artifact.
        prog, _artifacts = _sanitize_text(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    # THEN THE PROGRAM STAGE, the same order production uses. The removals are stashed
    # rather than returned, so the three authoring loops keep their two-value signature
    # and the caller still gets the account.
    prog, _more = _sanitize(prog)
    _artifacts = _artifacts + _more
    if _artifacts:
        _SANITISED.extend(_artifacts)
    ok, probs = validate(prog, known_names=known_names,
                         census=world.census() if world is not None else None)
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
           "keep_alive": pinned.KEEP_ALIVE, "options": pinned.options(temp), "messages": msgs}
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            _OLLAMA, json.dumps(req).encode(), {"Content-Type": "application/json"}),
            timeout=timeout)
        # THE TEXT STAGE FIRST. The sanitiser's reach used to stop at a parsed program,
        # so the most common residue there is — prose after the closing brace — killed the
        # parse and the whole answer was discarded before the instrument could see it.
        # `sanitize_text` reads ONE value and returns what follows as an artifact.
        prog, _artifacts = _sanitize_text(json.loads(r.read())["message"]["content"])
    except Exception as e:
        return None, [f"{type(e).__name__}: {e}"]
    # THEN THE PROGRAM STAGE, the same order production uses. The removals are stashed
    # rather than returned, so the three authoring loops keep their two-value signature
    # and the caller still gets the account.
    prog, _more = _sanitize(prog)
    _artifacts = _artifacts + _more
    if _artifacts:
        _SANITISED.extend(_artifacts)
    ok, problems = validate(prog, known_names=known_names,
                            census=world.census() if world is not None else None)
    return prog, ([] if ok else problems)


def main(argv=None, sink=None) -> int:
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
    p.add_argument("--no-gate", action="store_true",
                   help="skip the SCHEMA GATE. It sits between validate and run, exactly "
                        "where production puts it, and re-asks the author when a program "
                        "is coherent but does not answer what was asked. Off is the "
                        "control column — with no run to compare against, a gated score "
                        "cannot be attributed to the gate.")
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
    # The gate's own tally, kept separate from `valid` so its cost and its benefit are
    # both visible: how many programs it re-asked for, how many that fixed, how many it
    # refused outright. A gate reported only through the pass count could suppress as much
    # as it saves and read as neutral.
    gate_rounds = gate_fixed = gate_refused = 0
    # Programs the EXECUTOR could not run at all. Counted separately from a
    # failed goal: a validated program that raises is a harness defect, and
    # folding it into the ordinary miss count would hide one behind the other.
    crashed = 0
    for rung in rungs:
        # ONE PIPELINE, TWO READERS. `sink` collects a structured outcome per cell so a
        # regression gate can read WHY a cell failed without a second implementation of
        # authoring, repair, revision and gating. A parallel harness would make 'the
        # test' its own failure point, which is exactly what the reason codes exist to
        # separate out.
        cell = {"rung": rung.n, "name": rung.name,
                "column": "para" if a.paraphrase else "lit",
                "mutate": a.mutate, "outcome": None, "detail": None,
                "calls": None, "artifacts": 0, "repair_rounds": 0,
                "revisions": 0}
        _n0 = len(_SANITISED)
        def _land(outcome, detail=None, **kw):
            if cell["outcome"] is None:      # FIRST verdict wins — the earliest stage
                cell.update(outcome=outcome,  # that failed is the one to attribute to
                            detail=detail, **kw)
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
        # THE CLAUSE LEDGER JOINS THE OBJECTIONS. The validator answers "is this a legal
        # program"; the ledger answers "does it still contain everything the goal asked
        # for". Those are different questions and only the first was ever being put to the
        # author — so para:8 spent both repair rounds on `select must name a kind` while
        # the demand it had actually dropped (`db`) went unmentioned, 3/3.
        #
        # IT ONLY EVER ADDS. A ledger objection never suppresses a validator one, because
        # a program can be both illegal and incomplete and the author needs to see both —
        # the same argument `_both_objections` already makes for goal-shortfall versus
        # rejected-call: one names the symptom, the other the cause.
        #
        # UNVERIFIED IS NOT REPORTED, only UNACCOUNTED. Telling an author about a demand
        # nothing could check would be noise it cannot act on, and would make the
        # objection budget carry uncertainty instead of complaints.
        if prog is not None and rung.demands:
            _led = clause_ledger.reconcile(
                clause_ledger.open_ledger(goal, rung.demands), prog.get("body") or [])
            _missing = clause_ledger.unaccounted(_led)
            if _missing:
                problems = list(problems or []) + [
                    f"the goal asks for {m['text']!r} and nothing in the program does it "
                    f"({m['why']})" for m in _missing]
                print(f"          [ledger] {len(_missing)} demand(s) unaccounted for")
        if prog is None:
            # A NON-RESULT IS NOT A FAILURE. A model call that timed out says nothing
            # about the language, and folding it into the score quietly deflates every
            # column it lands in — rung 13 timed out twice today and was counted as a
            # miss both times. Same distinction run_all.py already draws for suites:
            # NO-RESULT fails the run and is REPORTED as no-result, never as a failure.
            noresult += 1
            # THE CHANNEL, NOT THE MODEL'S REASONING — and the two kinds are different
            # bugs. `Extra data` is a valid program with prose after it, recoverable in
            # principle; anything else is a decoder that emitted non-JSON under a schema
            # that forbids it. Folding them together hid a correct rung-11 repair inside
            # a bucket labelled "no result".
            _e = problems[0]
            _kind = _decode_failure(_e)
            _land("NO_EMISSION" if _kind == "empty" else f"BAD_JSON:{_kind}", _e)
            print(f"   [NO RESULT] {problems[0]} — not counted as a failure\n")
            if sink is not None:
                sink.append(cell)      # SAME EXIT as every other path — see below
            continue
        if problems and a.revisions:
            for attempt in range(a.revisions):
                fixed_prog, problems2 = repair(goal, prog, problems, a.model, a.temp,
                                               shots, known_names=world.names(),
                                               want=want,
                                               world=None if a.blind_author else world)
                if fixed_prog is None:
                    # THE DISTINCTION THAT WAS INVISIBLE. Rung 11's repair produced the
                    # correct program and said so in prose; json.loads threw on the
                    # trailing sentence and the fix was discarded. That read as a model
                    # that could not act on an objection. It is a reader defect.
                    # SAME SPLIT ON THE REPAIR CHANNEL. `lit:13` is trailing prose —
                    # a correct fix discarded by our reader — while `lit:7` is the model
                    # emitting broken JSON. Identical code, opposite owners, and fixing
                    # one would otherwise take credit for the other.
                    _re = (problems2 or [""])[0]
                    _land(f"REPAIR_UNDELIVERED:{_decode_failure(_re)}", _re)
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
        # ── THE SCHEMA GATE, in the same position it holds in production ──────────
        #
        # After validate, before anything runs — `make_run_program` puts it exactly
        # there, and a benchmark that gated somewhere else would be measuring a
        # different system. It had been built, tested deterministically, wired into the
        # planner, and never once shown a model; every part of this language that stayed
        # unreached stayed broken, so this is the measurement that says whether it helps.
        #
        # `--no-gate` exists because a column with the gate on and no column with it off
        # cannot attribute anything. The two runs are the comparison.
        ok = not problems
        gate_note = ""
        if ok and not a.no_gate:
            def _reauthor(program, reasons):
                """Re-ask the author with the gate's objections, via the repair path.

                Returns None — which `clarify()` reads as STALE — when the answer does
                not come back clean. A malformed correction is not an improved program,
                and handing one to the gate would have it score structure the validator
                has already refused."""
                fixed, probs = repair(goal, program, reasons, a.model, a.temp, shots,
                                      known_names=world.names(), want=want,
                                      world=None if a.blind_author else world)
                return None if (fixed is None or probs) else fixed

            said = []
            verdict = gate.clarify(prog, goal, want, _reauthor, say=said.append)
            for line in said:
                print(f"          #| {line}")
            gate_rounds += verdict.get("attempts", 0)
            if verdict["band"] == gate.PROCEED:
                if verdict.get("attempts"):
                    gate_fixed += 1
                    gate_note = f" (gate: clarified in {verdict['attempts']})"
                prog = verdict["program"]
            else:
                # A REFUSAL ENDS THE RUNG. Production falls back to a primitive; the
                # bench has no fallback, because here the program IS the answer. Counted
                # as a failure rather than a no-result: the gate reached a verdict, and
                # a harness declining to run its own author's program is a real outcome,
                # not a missing measurement.
                gate_refused += 1
                _land("GATE_REFUSED", f"{verdict['band']} @ {verdict['score']:.2f}")
                ok = False
                gate_note = f" (GATE {verdict['band'].upper()} @ {verdict['score']:.2f})"
                problems = list(verdict["reasons"])

        ok = ok and not problems
        # STILL REJECTED AFTER EVERY ROUND. The objection reached the author and the
        # author could not act on it — a REASONING outcome, and the detail carries the
        # rule that refused it so a run can be read for whether the LANGUAGE is the thing
        # being argued with.
        if not ok:
            _land("UNRECOVERED", (problems or [None])[0])
        cell["repair_rounds"] = repairs
        cell["artifacts"] = len(_SANITISED) - _n0
        valid += ok
        print(f"   [{'VALID' if ok else 'INVALID'}]{gate_note} "
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
            # A CRASHING PROGRAM FAILS ITS OWN RUNG AND NOTHING ELSE.
            #
            # It used to take the whole column with it. A rung-4 program wrote
            # `FOREACH $item IN [$vms]`, bound $item to the entire set, handed a list to a
            # scalar tool argument, and the TypeError out of the executor ended the
            # process — costing rungs 5 through 13 of measurement, twice, on two
            # paraphrase runs that were otherwise fine.
            #
            # Nine rungs of silence is not a neutral outcome: it reads as though they were
            # never attempted, when in fact one unrelated program crashed. This is the
            # honesty rule the probe already applies to an author timeout — report it as
            # what it is rather than let it deflate every column it lands in — arriving at
            # the other end of the same run.
            #
            # Deliberately CAUGHT AND NAMED rather than suppressed: an executor that
            # raises on a validated program is a real defect, and the run says so loudly
            # while continuing.
            try:
                res = run(prog, world.execute, select=sel, holds=holds,
                          known_names=world.names(), consent=True, intent=want)
            except Exception as exc:
                crashed += 1
                _land("CRASHED", f"{type(exc).__name__}: {exc}")
                print(f"          !! EXECUTOR CRASHED on a VALIDATED program: "
                      f"{type(exc).__name__}: {exc}")
                print(f"          !! this rung fails; the column continues")
                res = {"ok": False, "failed": "executor_crash", "why": f"{type(exc).__name__}: {exc}",
                       "calls": [], "failures": []}
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
            # ONE AUTHORITY, in `intent.standing_goal`. This rule was written out here and
            # again in `tree_probe`, whose docstring says so — and it is exactly the kind of
            # fact the 07-30 sweep found diverging four times in a day. The reasoning above
            # is kept because it is why the rule has the shape it does; the implementation
            # is not kept twice.
            _standing = _intent.standing_goal(prog)
            goal_pred = _standing["predicate"] if _standing else None

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
                           # THE OPERATOR'S INTENT REACHES THE DERIVER. Without it
                           # derive() is conservative and will not correct downward, so a
                           # goal that needs removal silently fell back to asking the model
                           # — the loop rung 7 was built to take off it.
                           else derive(goal_pred, sel, res.get("scope"), want))
                if derived:
                    # THE FIX, THEN THE WORK THAT NEVER RAN. A failed predicate returns
                    # from `run` and abandons every statement after it, so replaying only
                    # the correction leaves that work undone while the predicate reports
                    # the goal as held. para:4 is the case: `ACHIEVE REACH(...)` sat before
                    # the `add_label(... fleet)` loop, the ACHIEVE failed on the probe
                    # requirement, the tagging never happened, and the derived fix closed
                    # the predicate over an untagged fleet. `follow_up` appends the
                    # abandoned tail, resolved against the scope the aborted run held.
                    fix, fix_problems = _ir_execute.follow_up(res, derived), []
                    tail = len(res.get("remaining") or [])
                    print(f"          d{rounds}| (derived"
                          + (f" + {tail} statement(s) that never ran)" if tail else ")"))
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
            cell["revisions"] = rounds
            cell["calls"] = len(world.calls)
            if passed:
                # OVER_BUDGET needs a VERIFIED baseline, not an observed one: a baseline
                # learned from what the model did certifies whatever the model does.
                # rung.best is declared, and several are stale in the loose direction, so
                # this is reported and never counted as a failure until they are re-earned.
                _land("OVER_BUDGET" if (rung.best and len(world.calls) > rung.best)
                      else "PASS",
                      f"{len(world.calls)} calls vs best {rung.best}" if rung.best else None)
            elif res.get("ok"):
                # THE HARNESS ACCUSING ITSELF. The program's own ENSURE/ACHIEVE vouched
                # for the end state and the rung's checker disagrees. One of them is
                # wrong, and which is not knowable from here — but a run that reports
                # only the checker hides the possibility that the CHECKER is the defect,
                # and that is one of the four things this taxonomy exists to separate.
                _land("CHECKER_DISPUTE", res.get("why") or "program ok, checker false")
            else:
                _land("GOAL_UNMET", res.get("failed"))
            correct += passed
            if rounds:
                revised += 1
                fixed += passed
            print(f"          -> RUNG CHECKER: {'PASS' if passed else 'FAIL'}"
                  f"   world: {world.summary()}")
        print()

        if cell["outcome"] is None:
            _land("GOAL_UNMET", "not executed")
        if sink is not None:
            sink.append(cell)

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
    # THE ARTIFACT RATE, ALWAYS PRINTED — including when it is zero. A sanitiser that
    # cleans without counting makes its own workload invisible, and "it got quietly worse"
    # is the failure this whole instrument exists to prevent. Zero is a measurement;
    # silence is not. The severity line names what is NOT screened for, because reporting
    # only what was looked for reads as an all-clear the pass has not earned — the same
    # unknown-is-not-false rule the observed attributes are built on.
    by_kind = _Counter(x["kind"] for x in _SANITISED)
    print(f"   ARTIFACTS REMOVED  : {len(_SANITISED)}"
          + (f"  ({', '.join(f'{k}×{n}' for k, n in by_kind.most_common())})"
             if by_kind else ""))
    unscreened = [s for s in {"dangerous"}
                  if not any(v.get("severity") == s
                             for v in _sanitize_kinds().values())]
    if unscreened:
        print(f"   NOT SCREENED FOR   : {', '.join(unscreened)} "
              f"— no kind carries that severity yet")
    # THE SYMPTOM LINE — benign to clean, diagnostic in rate. `trailing_prose` is entirely
    # safe to remove and its presence is a SCHEMA VIOLATION, so the run stays coherent
    # BECAUSE the artifact was cleaned while the rate says the decoder is not holding.
    # Reporting only the removal count would hide exactly that.
    _sym = _Counter(_sanitize_kinds().get(x["kind"], {}).get("symptom_of")
                    for x in _SANITISED)
    _sym.pop(None, None)
    for layer, n in _sym.most_common():
        print(f"   SYMPTOM OF {layer.upper():8}: {n} removal(s) — cleaned safely, but "
              f"their presence indicates the {layer} is not holding")
    # BOTH SIDES OF THE GATE'S LEDGER, always together. A gate reported only through the
    # pass count can suppress exactly as much as it saves and still read as neutral, so
    # what it fixed and what it refused are printed side by side with what it cost.
    if crashed:
        print(f"   EXECUTOR CRASHES    : {crashed}  <== validated programs that could not "
              f"be run at all")
    if not a.no_gate and (gate_rounds or gate_refused):
        print(f"   SCHEMA GATE        : {gate_fixed} clarified, {gate_refused} refused"
              f"  ({gate_rounds} re-author round(s) spent)")
    print("\n   Validity is structure + grounding only. Whether a program MEANS its goal\n"
          "   is for a human reading the rendered forms above — scoring that needs a\n"
          "   second definition of every goal, which is a benchmark grading itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
