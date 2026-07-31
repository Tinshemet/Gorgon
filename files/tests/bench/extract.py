"""extract.py — English into goal components. THE ONLY PLACE A MODEL IS CALLED.

The translation half of the operator's design (#60). The ghost writer proved that code alone
can write every rung once the goal is expressed as components; this is the question that was
left open — whether a model can produce those components from a sentence.

WHY THIS SHOULD BE EASIER THAN AUTHORING. Every field is a CLOSED SET drawn from the
manifest: seven kinds of goal, three kinds, the attributes of each, the legal values of the
enumerated ones. There is no program to get wrong, no ordering to remember, no grounding to
add, no `$reference` to bind. A wrong answer here is DETECTABLE — it names a kind or an
attribute that does not exist — where a wrong program merely fails later, for one of two
reasons nobody could tell apart.

THE SCHEMA IS BUILT FROM THE MANIFEST, never written out. A kind added to `ir.defaults.json`
is extractable the same day, and a schema that listed the kinds by hand would be the second
authority this codebase keeps deleting.

AND IT CARRIES NO `pattern`. On 2026-07-31 a single `pattern: "^\\$"` silently disabled
constrained decoding for the whole authoring path — ollama returned 200 and generated free
text. There is nothing here that needs one: the fields are enums, integers and plain
strings. `assert_enforced` proves the grammar actually applies before any number from this
module is believed.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from orchestrator.ai.chat.ollama_client import OLLAMA_URL
from orchestrator.ai.planner.ir import config

from . import pinned
from .ladder import BENCH_MODEL


def _kinds() -> List[str]:
    return sorted((config.KINDS or {}).keys())


def _attrs(kind: str = None) -> List[str]:
    """Every queryable attribute, aliases included — the operator's words, not ours."""
    out = set()
    for k, spec in (config.KINDS or {}).items():
        if kind and k != kind:
            continue
        out |= set(spec.get("attrs") or ())
        out |= set((spec.get("aliases") or {}).keys())
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out)


def _facts() -> List[str]:
    out = set()
    for spec in (config.KINDS or {}).values():
        out |= set((spec.get("observed") or {}).keys())
    return sorted(out) or ["alive"]


_WHERE = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "attr": {"type": "string", "enum": _attrs(),
                     "description": "which property to match on"},
            "value": {"type": "string",
                      "description": "the value it must have, as written by the operator"},
        },
        "required": ["attr", "value"],
        "additionalProperties": False,
    },
}

_SELECT = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": _kinds()},
        "where": _WHERE,
        "except": {**_WHERE,
                   "description": "members to EXCLUDE — 'every vm except db' puts db here"},
    },
    "required": ["kind"],
    "additionalProperties": False,
}

# ONE BRANCH PER SHAPE OF GOAL, and the set is closed. A request that fits none of these is
# one the writer could not build anyway, so the honest outcome is a refusal at this step
# rather than a program nobody can trust.
SCHEMA = {
    "type": "object",
    "properties": {
        "goals": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "enum": ["count", "reach", "every", "per", "observe"],
                        "description": (
                            "count: how many members must match. "
                            "reach: these must be able to reach each other. "
                            "every: every member of a set must get a property. "
                            "per: make one new thing for each member of a set. "
                            "observe: ask each member something, without requiring an answer"
                        ),
                    },
                    "select": _SELECT,
                    "amount": {"type": "integer",
                               "description": "for count: how many. for reach: how few is too few"},
                    "attr": {"type": "string", "enum": _attrs(),
                             "description": "for every: which property to give them"},
                    "value": {"type": "string",
                              "description": "for every: what to set that property to"},
                    "make": {"type": "string", "enum": _kinds(),
                             "description": "for per: what kind of thing to make"},
                    "link": {"type": "string", "enum": _attrs(),
                             "description": "for per: the property tying the new thing to the member"},
                    "fact": {"type": "string", "enum": _facts(),
                             "description": "for observe: what to ask"},
                },
                "required": ["goal", "select"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["goals"],
    "additionalProperties": False,
}

PROMPT = """You read an operator's request about virtual machines and say WHAT MUST BE TRUE
when it is done. You do NOT write any program, choose any tool, or decide any order —
something else does all of that.

Break the request into goals. Each goal is one thing that must be true at the end.

  count    a number of members must match     "3 vms labelled prod"  -> count, amount 3
  reach    members must reach each other      "make sure they can all ping each other"
  every    every member of a set gets a       "put them all on network lab"
           property                            -> every, attr network, value lab
  per      one new thing per member           "snapshot every running vm"
                                               -> per, make snapshot, link vm
  observe  ask each member something          "ping every vm" -> observe, fact alive

`select` names the members a goal is about. `where` narrows it; `except` carves members out.
Say what the operator asked for and nothing more."""


def _to_select(raw: Dict[str, Any]) -> Dict[str, Any]:
    """The extractor's `select` into the writer's — flat filters, alias-resolved.

    `where`/`except` lists exist because a LIST OF PAIRS constrains cleanly and an object
    with arbitrary keys does not. The writer wants flat filters, so the conversion happens
    here, once, at the boundary where the two shapes meet.
    """
    kind = raw.get("kind")
    alias = ((config.KINDS or {}).get(kind) or {}).get("aliases") or {}
    out: Dict[str, Any] = {"kind": kind}
    for pair in raw.get("where") or []:
        out[alias.get(pair["attr"], pair["attr"])] = _coerce(pair["value"])
    carve = {}
    for pair in raw.get("except") or []:
        carve[alias.get(pair["attr"], pair["attr"])] = _coerce(pair["value"])
    if carve:
        out["not"] = carve
    return out


def _coerce(v: str) -> Any:
    """`"false"` is not `False`, and an observed attribute compared against a string never
    matches. The extractor emits strings because a grammar cannot type a free value."""
    low = str(v).strip().lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    return v


def to_goals(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The model's answer, in the shape `ghost_writer.cover` takes.

    Anything malformed is DROPPED rather than repaired. A goal missing the field its own
    shape requires is a goal the model did not actually state, and inventing the missing
    half here would put this module back in the business of deciding what the operator
    meant — which is the job it exists to not have.
    """
    out: List[Dict[str, Any]] = []
    for g in (raw or {}).get("goals") or []:
        shape, sel = g.get("goal"), _to_select(g.get("select") or {})
        if not sel.get("kind"):
            continue
        if shape == "count" and g.get("amount") is not None:
            out.append({"shape": "count", "select": sel, "eq": int(g["amount"])})
        elif shape == "reach":
            out.append({"shape": "reach", "select": sel,
                        "min": int(g.get("amount") or 2)})
        elif shape == "every" and g.get("attr") and g.get("value") is not None:
            alias = ((config.KINDS or {}).get(sel["kind"]) or {}).get("aliases") or {}
            out.append({"every": sel,
                        "must": {alias.get(g["attr"], g["attr"]): _coerce(g["value"])}})
        elif shape == "per" and g.get("make") and g.get("link"):
            out.append({"per": sel, "make": g["make"], "link": g["link"]})
        elif shape == "observe":
            out.append({"observe": sel, "fact": g.get("fact") or "alive"})
    return out


def extract(request: str, model: str = None, temp: float = 0.0,
            timeout: int = 300) -> Dict[str, Any]:
    """Call the model once. Returns the raw parsed answer (use `to_goals` to convert)."""
    import urllib.request
    body = {
        "model": model or BENCH_MODEL,
        "stream": False,
        "format": SCHEMA,
        "keep_alive": pinned.KEEP_ALIVE,
        "options": pinned.options(temp),
        "messages": [{"role": "system", "content": PROMPT},
                     {"role": "user", "content": request}],
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", method="POST",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        reply = json.loads(r.read())
    return json.loads((reply.get("message") or {}).get("content") or "{}")


def assert_enforced(model: str = None) -> bool:
    """Is the grammar actually applied? Ask something that would never produce JSON.

    THE CHECK THAT WOULD HAVE SAVED A MONTH. `pattern: "^\\$"` made ollama accept a schema,
    return HTTP 200, and generate completely unconstrained — so every result measured on that
    path was really measuring few-shot imitation. A schema that parses is not a schema that
    constrains, and the only way to know is to send a prompt whose answer cannot be JSON and
    see whether JSON comes back anyway.
    """
    try:
        got = extract("Say hello in one word.", model)
    except Exception:
        return False
    return isinstance(got, dict) and "goals" in got
